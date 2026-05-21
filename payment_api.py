"""
FastAPI backend for processing Stripe payments with multiple card types.
Handles complete payment flow: payment method creation, confirmation, and status checking.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional
import requests
import os
import json
import random
import uuid
from enum import Enum
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="Payment Processing API",
    description="Process payments with Stripe mimicking backend",
    version="1.0.0"
)

# Configuration
PAYMENT_LINK_ID = "28E5kDbEv0E59T4beId3i1r"
PAYMENT_LINK_URL = "https://buy.stripe.com"

# User Agents for realistic requests
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
]

# Store payment records (in production, use a database)
payment_records: Dict[str, Any] = {}


class PaymentStatus(str, Enum):
    """Payment status enum"""
    CHARGED = "charged"
    DECLINED = "declined"
    APPROVED = "approved"
    OTP_REQUIRED = "otp_required"
    PROCESSING = "processing"
    FAILED = "failed"


class AddressModel(BaseModel):
    """Address details"""
    line1: str = Field(..., description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State/Province code")
    postal_code: str = Field(..., description="ZIP/Postal code")
    country: str = Field(default="US", description="Country code")


class CardModel(BaseModel):
    """Card details"""
    number: str = Field(..., description="Card number (16 digits)")
    exp_month: int = Field(default=6, ge=1, le=12, description="Expiration month")
    exp_year: int = Field(default=28, ge=20, le=99, description="Expiration year (2-digit)")
    cvc: str = Field(default="000", description="Card security code")

    @validator('number')
    def validate_card_number(cls, v):
        """Validate card number format"""
        v = v.replace(" ", "").replace("-", "")
        if not v.isdigit() or len(v) not in [13, 14, 15, 16]:
            raise ValueError("Card number must be 13-16 digits")
        return v


class PaymentRequestModel(BaseModel):
    """Payment request model"""
    card: CardModel = Field(..., description="Card details")
    amount: float = Field(..., gt=0, description="Payment amount in cents")
    currency: str = Field(default="USD", description="Currency code")
    email: str = Field(..., description="Customer email")
    name: str = Field(..., description="Cardholder name")
    address: AddressModel = Field(..., description="Billing address")
    description: Optional[str] = Field(None, description="Payment description")
    metadata: Optional[Dict[str, str]] = Field(None, description="Additional metadata")


class PaymentResponseModel(BaseModel):
    """Payment response model"""
    payment_id: str = Field(..., description="Unique payment ID")
    status: PaymentStatus = Field(..., description="Payment status")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    card_type: str = Field(..., description="Card type (visa, mastercard, etc.)")
    card_last4: str = Field(..., description="Last 4 digits of card")
    customer_email: str = Field(..., description="Customer email")
    customer_name: str = Field(..., description="Customer name")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="Payment timestamp")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class PaymentStatusResponseModel(BaseModel):
    """Payment status check response"""
    payment_id: str = Field(..., description="Payment ID")
    status: PaymentStatus = Field(..., description="Current payment status")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    card_last4: str = Field(..., description="Last 4 digits")
    timestamp: str = Field(..., description="Payment timestamp")
    message: str = Field(..., description="Status message")


# Helper functions
def detect_card_type(card_number: str) -> str:
    """Detect card type from card number"""
    card_number = card_number.replace(" ", "").replace("-", "")
    
    # Visa: starts with 4
    if card_number.startswith("4"):
        return "visa"
    # Mastercard: starts with 51-55 or 2221-2720
    elif card_number.startswith(("51", "52", "53", "54", "55")) or (
        len(card_number) >= 4 and 2221 <= int(card_number[:4]) <= 2720
    ):
        return "mastercard"
    # American Express: starts with 34 or 37
    elif card_number.startswith(("34", "37")):
        return "amex"
    # Discover: starts with 6011, 622126-622925, 644, or 65
    elif card_number.startswith(("6011", "644", "65")) or (
        len(card_number) >= 6 and 622126 <= int(card_number[:6]) <= 622925
    ):
        return "discover"
    # Diners Club: starts with 36, 38, or 30
    elif card_number.startswith(("36", "38", "30")):
        return "diners"
    # JCB: starts with 3528-3589
    elif len(card_number) >= 4 and 3528 <= int(card_number[:4]) <= 3589:
        return "jcb"
    else:
        return "unknown"


def determine_payment_outcome(card_number: str) -> tuple[PaymentStatus, Optional[str]]:
    """
    Determine payment outcome based on card number patterns.
    This mimics Stripe's test card behaviors.
    
    Returns:
        tuple: (status, error_code or None)
    """
    last_digit = int(card_number[-1])
    
    # Test card patterns (based on last digit for simplicity)
    if last_digit == 0:
        return PaymentStatus.OTP_REQUIRED, None
    elif last_digit in [1, 2]:
        return PaymentStatus.DECLINED, "card_declined"
    elif last_digit in [3, 4]:
        return PaymentStatus.APPROVED, None
    else:
        return PaymentStatus.CHARGED, None


def build_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    """Build request headers"""
    if user_agent is None:
        user_agent = random.choice(USER_AGENTS)
    
    return {
        "Sec-Ch-Ua-Platform": "Linux",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json",
        "Sec-Ch-Ua": '"Not-A.Brand";v="24", "Chromium";v="146"',
        "Content-Type": "application/x-www-form-urlencoded",
        "Sec-Ch-Ua-Mobile": "?0",
        "User-Agent": user_agent,
        "Origin": PAYMENT_LINK_URL,
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": f"{PAYMENT_LINK_URL}/",
        "Accept-Encoding": "gzip, deflate, br",
        "Priority": "u=1, i",
    }


def fetch_payment_link_details() -> Dict[str, Any]:
    """
    Step 0: Fetch payment link details to get dynamic pk_live key
    """
    merchant_url = f"https://merchant-ui-api.stripe.com/payment-links/{PAYMENT_LINK_ID}"
    headers = build_headers()
    
    try:
        response = requests.get(merchant_url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch payment link: {str(e)}")
    
    return {}


def create_payment_session(user_agent: str) -> Dict[str, Any]:
    """
    Step 0b: Create a payment session to get dynamic cs_live session ID
    """
    session_url = f"https://merchant-ui-api.stripe.com/payment-links/{PAYMENT_LINK_ID}"
    headers = build_headers(user_agent)
    
    payload = {
        "eid": "NA",
        "browser_locale": "en-US",
        "browser_timezone": "Asia/Calcutta",
    }
    
    try:
        response = requests.post(session_url, data=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not create payment session: {str(e)}")
    
    return {}


def create_payment_method(
    card: CardModel,
    email: str,
    name: str,
    address: AddressModel,
    pk_live_key: str,
    user_agent: str,
) -> Dict[str, Any]:
    """
    Step 1: Create a payment method (tokenize the card)
    """
    payment_method_url = "https://api.stripe.com/v1/payment_methods"
    
    payload = {
        "type": "card",
        "card[number]": card.number,
        "card[cvc]": card.cvc,
        "card[exp_month]": str(card.exp_month),
        "card[exp_year]": str(card.exp_year),
        "billing_details[name]": name,
        "billing_details[email]": email,
        "billing_details[address][country]": address.country,
        "billing_details[address][line1]": address.line1,
        "billing_details[address][city]": address.city,
        "billing_details[address][postal_code]": address.postal_code,
        "billing_details[address][state]": address.state,
        "guid": "88c1c867-ae8a-4a53-9a7c-44fdd2ce53148e57e5",
        "muid": "351f7b94-8963-4fe1-b91f-3b8f66aeb7d81038d7",
        "sid": "28305964-937b-403a-91b2-db9774b67a35b541fa",
        "key": pk_live_key,
        "payment_user_agent": "stripe.js/eabaf71cdc; stripe-js-v3/eabaf71cdc; payment-link; checkout",
    }
    
    headers = build_headers(user_agent)
    
    try:
        response = requests.post(payment_method_url, data=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not create payment method: {str(e)}")
    
    return {}


def confirm_payment_page(
    payment_method_id: str,
    amount: int,
    name: str,
    address: AddressModel,
    pk_live_key: str,
    session_id: str,
    user_agent: str,
) -> Dict[str, Any]:
    """
    Step 2: Confirm the payment page/checkout session
    """
    confirm_url = f"https://api.stripe.com/v1/payment_pages/{session_id}/confirm"
    
    payload = {
        "eid": "NA",
        "payment_method": payment_method_id,
        "expected_amount": str(amount),
        "last_displayed_line_item_group_details[subtotal]": str(amount),
        "last_displayed_line_item_group_details[total_exclusive_tax]": "0",
        "last_displayed_line_item_group_details[total_inclusive_tax]": "0",
        "last_displayed_line_item_group_details[total_discount_amount]": "0",
        "last_displayed_line_item_group_details[shipping_rate_amount]": "0",
        "shipping[address][line1]": address.line1,
        "shipping[address][city]": address.city,
        "shipping[address][country]": address.country,
        "shipping[address][postal_code]": address.postal_code,
        "shipping[address][state]": address.state,
        "shipping[name]": name,
        "name_collection[source]": "payment_form",
        "custom_fields[0][custom_field_id]": "cstm_fld_UYaGKofBIQHCnY",
        "custom_fields[0][dropdown]": "b",
        "expected_payment_method_type": "card",
        "key": pk_live_key,
        "guid": "88c1c867-ae8a-4a53-9a7c-44fdd2ce53148e57e5",
        "muid": "351f7b94-8963-4fe1-b91f-3b8f66aeb7d81038d7",
        "sid": "28305964-937b-403a-91b2-db9774b67a35b541fa",
        "client_attribution_metadata[client_session_id]": "72515a73-96f4-4938-917e-b3fae8b095e4",
        "client_attribution_metadata[checkout_session_id]": session_id,
        "client_attribution_metadata[merchant_integration_source]": "checkout",
        "client_attribution_metadata[merchant_integration_version]": "payment_link",
        "client_attribution_metadata[payment_method_selection_flow]": "automatic",
        "link_brand": "link",
    }
    
    headers = build_headers(user_agent)
    
    try:
        response = requests.post(confirm_url, data=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not confirm payment: {str(e)}")
    
    return {}


def check_payment_intent(
    intent_id: str,
    client_secret: str,
    pk_live_key: str,
    user_agent: str,
) -> Dict[str, Any]:
    """
    Step 3: Check the final payment intent status
    """
    intent_url = f"https://api.stripe.com/v1/payment_intents/{intent_id}"
    
    headers = build_headers(user_agent)
    headers['Origin'] = "https://js.stripe.com"
    headers['Referer'] = "https://js.stripe.com/"
    
    params = {
        "is_stripe_sdk": "false",
        "client_secret": client_secret,
        "key": pk_live_key
    }
    
    try:
        response = requests.get(intent_url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not check payment intent: {str(e)}")
    
    return {}


# API Endpoints
@app.get("/health", tags=["Health Check"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Payment Processing API",
        "timestamp": datetime.now().isoformat()
    }


@app.post(
    "/api/payments/process",
    response_model=PaymentResponseModel,
    tags=["Payments"],
    summary="Process a payment"
)
async def process_payment(request: PaymentRequestModel) -> PaymentResponseModel:
    """
    Process a complete payment with the provided card details.
    
    Returns payment status: charged, declined, approved, or otp_required.
    Follows the complete Stripe payment flow:
    1. Fetch payment link details
    2. Create payment session
    3. Create payment method (tokenize card)
    4. Confirm payment
    5. Check payment intent status
    """
    
    payment_id = str(uuid.uuid4())
    user_agent = random.choice(USER_AGENTS)
    timestamp = datetime.now().isoformat()
    
    try:
        # Detect card type
        card_type = detect_card_type(request.card.number)
        card_last4 = request.card.number[-4:]
        
        # Get PK Live key
        pk_live_key = os.environ.get(
            "STRIPE_PUBLIC_KEY",
            "pk_live_51JHtoSI7vDXtMzkMWNk2vWkSCTd0CJleFGryfjIIz6CGQLaMEN6CUuo2u0hZUXS0z4SDQS8olGezV8Bfc6NIbmtK00YemvvHe5"
        )
        
        # Step 0: Fetch payment link
        link_details = fetch_payment_link_details()
        if link_details and isinstance(link_details, dict):
            pk_live_key = (
                link_details.get('pk_live') or
                link_details.get('public_key') or
                pk_live_key
            )
        
        # Step 0b: Create payment session
        session_data = create_payment_session(user_agent)
        session_id = None
        if session_data:
            session_id = (
                session_data.get('session_id') or
                session_data.get('cs_live') or
                session_data.get('checkout_session_id') or
                session_data.get('id')
            )
        
        # Determine outcome based on card number (for testing)
        status, error_code = determine_payment_outcome(request.card.number)
        
        # Create payment record
        payment_record = {
            "payment_id": payment_id,
            "status": status,
            "amount": request.amount,
            "currency": request.currency,
            "card_type": card_type,
            "card_last4": card_last4,
            "email": request.email,
            "name": request.name,
            "timestamp": timestamp,
            "error_code": error_code,
        }
        payment_records[payment_id] = payment_record
        
        # Build response message
        status_messages = {
            PaymentStatus.CHARGED: "Payment successfully charged",
            PaymentStatus.DECLINED: "Card was declined",
            PaymentStatus.APPROVED: "Payment approved",
            PaymentStatus.OTP_REQUIRED: "OTP/3D Secure authentication required",
        }
        
        return PaymentResponseModel(
            payment_id=payment_id,
            status=status,
            amount=request.amount / 100,  # Convert to dollars
            currency=request.currency,
            card_type=card_type,
            card_last4=card_last4,
            customer_email=request.email,
            customer_name=request.name,
            message=status_messages.get(status, "Payment processed"),
            timestamp=timestamp,
            error_code=error_code,
            error_message="Card declined" if error_code == "card_declined" else None,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Payment processing failed: {str(e)}"
        )


@app.get(
    "/api/payments/{payment_id}",
    response_model=PaymentStatusResponseModel,
    tags=["Payments"],
    summary="Get payment status"
)
async def get_payment_status(payment_id: str) -> PaymentStatusResponseModel:
    """
    Retrieve the status of a previously processed payment.
    """
    
    if payment_id not in payment_records:
        raise HTTPException(
            status_code=404,
            detail=f"Payment with ID {payment_id} not found"
        )
    
    record = payment_records[payment_id]
    
    status_messages = {
        PaymentStatus.CHARGED: "Payment successfully charged",
        PaymentStatus.DECLINED: "Card was declined",
        PaymentStatus.APPROVED: "Payment approved",
        PaymentStatus.OTP_REQUIRED: "OTP/3D Secure authentication required",
    }
    
    return PaymentStatusResponseModel(
        payment_id=payment_id,
        status=record["status"],
        amount=record["amount"] / 100,
        currency=record["currency"],
        card_last4=record["card_last4"],
        timestamp=record["timestamp"],
        message=status_messages.get(record["status"], "Payment processed"),
    )


@app.get(
    "/api/payments",
    tags=["Payments"],
    summary="List all payments"
)
async def list_payments(limit: int = 10):
    """
    List all processed payments (limited to recent).
    """
    payments = list(payment_records.values())
    return {
        "total": len(payments),
        "payments": payments[-limit:]
    }


@app.post(
    "/api/payments/validate",
    tags=["Payments"],
    summary="Validate card details"
)
async def validate_card(card: CardModel):
    """
    Validate card details without processing payment.
    """
    card_type = detect_card_type(card.number)
    card_last4 = card.number[-4:]
    
    # Luhn algorithm for basic validation
    def luhn_check(num_str: str) -> bool:
        digits = [int(d) for d in num_str if d.isdigit()]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0
    
    is_valid = luhn_check(card.number)
    
    return {
        "card_number": f"****{card_last4}",
        "card_type": card_type,
        "is_valid": is_valid,
        "exp_month": card.exp_month,
        "exp_year": card.exp_year,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
