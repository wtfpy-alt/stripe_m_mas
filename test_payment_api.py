"""
Test script for Payment Processing API
Demonstrates various payment scenarios with different card types
"""

import requests
import json
import time
from typing import Dict, Any

# API Configuration
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/payments"

# Test Data - Various card types and outcomes
TEST_CARDS = {
    "visa_charged": {
        "number": "4242424242424248",
        "exp_month": 6,
        "exp_year": 28,
        "cvc": "123",
        "card_type": "Visa",
        "expected_status": "charged"
    },
    "visa_declined": {
        "number": "4242424242424241",
        "exp_month": 6,
        "exp_year": 28,
        "cvc": "123",
        "card_type": "Visa",
        "expected_status": "declined"
    },
    "mastercard_charged": {
        "number": "5555555555554448",
        "exp_month": 6,
        "exp_year": 28,
        "cvc": "456",
        "card_type": "Mastercard",
        "expected_status": "charged"
    },
    "mastercard_approved": {
        "number": "5555555555554444",
        "exp_month": 12,
        "exp_year": 28,
        "cvc": "456",
        "card_type": "Mastercard",
        "expected_status": "approved"
    },
    "amex_charged": {
        "number": "378282246310005",
        "exp_month": 6,
        "exp_year": 28,
        "cvc": "1234",
        "card_type": "American Express",
        "expected_status": "charged"
    },
    "discover_charged": {
        "number": "6011111111111118",
        "exp_month": 6,
        "exp_year": 28,
        "cvc": "789",
        "card_type": "Discover",
        "expected_status": "charged"
    },
    "otp_required": {
        "number": "4242424242424240",
        "exp_month": 6,
        "exp_year": 28,
        "cvc": "123",
        "card_type": "Visa",
        "expected_status": "otp_required"
    }
}

TEST_CUSTOMERS = [
    {
        "email": "john.smith@example.com",
        "name": "John Smith",
        "address": {
            "line1": "1620 Northwest 23rd Avenue",
            "city": "Portland",
            "state": "OR",
            "postal_code": "97210",
            "country": "US"
        }
    },
    {
        "email": "sarah.johnson@example.com",
        "name": "Sarah Johnson",
        "address": {
            "line1": "742 Evergreen Terrace",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US"
        }
    },
    {
        "email": "michael.williams@example.com",
        "name": "Michael Williams",
        "address": {
            "line1": "10 Downing Street",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "US"
        }
    }
]

AMOUNTS = [10000, 50000, 100000, 270836]  # $100, $500, $1000, $2708.36


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    """Print a formatted section"""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}")


def check_api_health() -> bool:
    """Check if API is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def test_payment(
    card: Dict[str, Any],
    customer: Dict[str, Any],
    amount: int,
    description: str
) -> Dict[str, Any]:
    """Process a test payment"""
    
    payload = {
        "card": {
            "number": card["number"],
            "exp_month": card["exp_month"],
            "exp_year": card["exp_year"],
            "cvc": card["cvc"]
        },
        "amount": amount,
        "currency": "USD",
        "email": customer["email"],
        "name": customer["name"],
        "address": customer["address"],
        "description": description
    }
    
    try:
        response = requests.post(f"{API_ENDPOINT}/process", json=payload, timeout=30)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Request failed: {str(e)}",
            "status_code": response.status_code if 'response' in locals() else None
        }


def test_card_validation(card: Dict[str, Any]) -> Dict[str, Any]:
    """Test card validation endpoint"""
    payload = {
        "number": card["number"],
        "exp_month": card["exp_month"],
        "exp_year": card["exp_year"],
        "cvc": card["cvc"]
    }
    
    try:
        response = requests.post(f"{API_ENDPOINT}/validate", json=payload, timeout=10)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


def test_payment_status(payment_id: str) -> Dict[str, Any]:
    """Retrieve payment status"""
    try:
        response = requests.get(f"{API_ENDPOINT}/{payment_id}", timeout=10)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


def test_list_payments(limit: int = 10) -> Dict[str, Any]:
    """List all payments"""
    try:
        response = requests.get(f"{API_ENDPOINT}?limit={limit}", timeout=10)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


def run_single_payment_test():
    """Test a single payment"""
    print_header("SINGLE PAYMENT TEST")
    
    card = TEST_CARDS["visa_charged"]
    customer = TEST_CUSTOMERS[0]
    amount = 50000  # $500.00
    
    print(f"Card Type: {card['card_type']}")
    print(f"Card Number: {card['number'][-4:]} (last 4 digits)")
    print(f"Customer: {customer['name']} ({customer['email']})")
    print(f"Amount: ${amount / 100:.2f}")
    
    print("\nProcessing payment...")
    result = test_payment(card, customer, amount, "Single test payment")
    
    print("\nResponse:")
    print(json.dumps(result, indent=2, default=str))
    
    if "payment_id" in result:
        print(f"\n✓ Payment ID: {result['payment_id']}")
        print(f"✓ Status: {result['status']}")
        print(f"✓ Message: {result['message']}")
        return result.get("payment_id")
    
    return None


def run_multiple_card_types_test():
    """Test multiple card types"""
    print_header("MULTIPLE CARD TYPES TEST")
    
    results = []
    
    for card_name, card_data in TEST_CARDS.items():
        print_section(f"Testing {card_data['card_type']}")
        
        customer = TEST_CUSTOMERS[0]
        amount = 10000  # $100.00
        
        print(f"Card: {card_data['card_type']}")
        print(f"Expected Status: {card_data['expected_status'].upper()}")
        
        result = test_payment(
            card_data,
            customer,
            amount,
            f"Test {card_data['card_type']}"
        )
        
        if "payment_id" in result:
            status = result["status"]
            matches = status == card_data["expected_status"]
            match_indicator = "✓" if matches else "✗"
            
            print(f"Actual Status: {status.upper()}")
            print(f"{match_indicator} Status Match: {'YES' if matches else 'NO'}")
            print(f"Message: {result.get('message', 'N/A')}")
            
            results.append({
                "card_type": card_data['card_type'],
                "expected": card_data['expected_status'],
                "actual": status,
                "matches": matches,
                "payment_id": result['payment_id']
            })
        else:
            print(f"✗ Error: {result.get('error', 'Unknown error')}")
            results.append({
                "card_type": card_data['card_type'],
                "error": True
            })
    
    # Print summary
    print_section("SUMMARY - Multiple Card Types")
    print(f"{'Card Type':<20} {'Expected':<15} {'Actual':<15} {'Match':<10}")
    print("─" * 60)
    for result in results:
        if "error" not in result:
            print(f"{result['card_type']:<20} {result['expected']:<15} {result['actual']:<15} {'✓' if result['matches'] else '✗':<10}")
        else:
            print(f"{result['card_type']:<20} {'ERROR':<15} {'':<15} {'✗':<10}")
    
    return results


def run_different_amounts_test():
    """Test payments with different amounts"""
    print_header("DIFFERENT AMOUNTS TEST")
    
    card = TEST_CARDS["mastercard_charged"]
    customer = TEST_CUSTOMERS[1]
    
    results = []
    
    for amount in AMOUNTS:
        print_section(f"Amount: ${amount / 100:.2f}")
        
        result = test_payment(
            card,
            customer,
            amount,
            f"Test payment for ${amount / 100:.2f}"
        )
        
        if "payment_id" in result:
            print(f"✓ Status: {result['status']}")
            print(f"✓ Amount: ${result['amount']:.2f} {result['currency']}")
            print(f"✓ Payment ID: {result['payment_id']}")
            results.append(result)
        else:
            print(f"✗ Error: {result.get('error', 'Unknown error')}")
    
    return results


def run_different_customers_test():
    """Test payments from different customers"""
    print_header("DIFFERENT CUSTOMERS TEST")
    
    card = TEST_CARDS["amex_charged"]
    amount = 50000
    
    results = []
    
    for customer in TEST_CUSTOMERS:
        print_section(f"Customer: {customer['name']}")
        
        print(f"Email: {customer['email']}")
        print(f"City: {customer['address']['city']}, {customer['address']['state']}")
        
        result = test_payment(
            card,
            customer,
            amount,
            f"Payment for {customer['name']}"
        )
        
        if "payment_id" in result:
            print(f"✓ Status: {result['status']}")
            print(f"✓ Payment ID: {result['payment_id']}")
            results.append(result)
        else:
            print(f"✗ Error: {result.get('error', 'Unknown error')}")
    
    return results


def run_card_validation_test():
    """Test card validation"""
    print_header("CARD VALIDATION TEST")
    
    for card_name, card_data in TEST_CARDS.items():
        print_section(f"Validating {card_data['card_type']}")
        
        result = test_card_validation(card_data)
        
        if "card_number" in result:
            print(f"Card Number: {result['card_number']}")
            print(f"Card Type: {result['card_type']}")
            print(f"Valid: {'✓' if result['is_valid'] else '✗'}")
            print(f"Exp: {result['exp_month']}/{result['exp_year']}")
        else:
            print(f"✗ Error: {result.get('error', 'Unknown error')}")


def run_payment_status_check():
    """Test payment status retrieval"""
    print_header("PAYMENT STATUS CHECK TEST")
    
    # First, process a payment
    print_section("Step 1: Process Payment")
    card = TEST_CARDS["visa_charged"]
    customer = TEST_CUSTOMERS[0]
    
    payment_result = test_payment(card, customer, 50000, "Status check test")
    
    if "payment_id" not in payment_result:
        print(f"✗ Failed to create payment: {payment_result.get('error')}")
        return
    
    payment_id = payment_result["payment_id"]
    print(f"✓ Payment created: {payment_id}")
    
    # Then check its status
    print_section("Step 2: Check Payment Status")
    status_result = test_payment_status(payment_id)
    
    if "payment_id" in status_result:
        print(f"Payment ID: {status_result['payment_id']}")
        print(f"Status: {status_result['status']}")
        print(f"Amount: ${status_result['amount']:.2f}")
        print(f"Card Last 4: {status_result['card_last4']}")
        print(f"Timestamp: {status_result['timestamp']}")
        print(f"✓ Status retrieved successfully")
    else:
        print(f"✗ Error: {status_result.get('error', 'Unknown error')}")


def run_list_payments_test():
    """Test listing payments"""
    print_header("LIST PAYMENTS TEST")
    
    result = test_list_payments(limit=5)
    
    if "payments" in result:
        print(f"Total Payments: {result['total']}")
        print(f"Recent Payments (limit 5):\n")
        
        for i, payment in enumerate(result['payments'], 1):
            print(f"{i}. Payment ID: {payment['payment_id']}")
            print(f"   Status: {payment['status']}")
            print(f"   Amount: ${payment['amount'] / 100:.2f} {payment['currency']}")
            print(f"   Card: {payment['card_type']} ****{payment['card_last4']}")
            print(f"   Customer: {payment['name']} ({payment['email']})")
            print()
    else:
        print(f"✗ Error: {result.get('error', 'Unknown error')}")


def main():
    """Run all tests"""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  PAYMENT PROCESSING API - COMPREHENSIVE TEST SUITE".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Check API health
    print("\n🔍 Checking API health...")
    if not check_api_health():
        print("✗ API is not running!")
        print("\nStart the API with:")
        print("  python payment_api.py")
        print("\nOr with uvicorn directly:")
        print("  uvicorn payment_api:app --reload")
        return
    
    print("✓ API is running and healthy")
    
    # Run tests
    print("\n📋 Available Tests:")
    print("  1. Single Payment Test")
    print("  2. Multiple Card Types Test")
    print("  3. Different Amounts Test")
    print("  4. Different Customers Test")
    print("  5. Card Validation Test")
    print("  6. Payment Status Check Test")
    print("  7. List Payments Test")
    print("  8. Run All Tests")
    
    choice = input("\nSelect test to run (1-8, or press Enter for all): ").strip()
    
    if choice == "1" or choice == "":
        run_single_payment_test()
    
    if choice == "2" or choice == "":
        run_multiple_card_types_test()
    
    if choice == "3" or choice == "":
        run_different_amounts_test()
    
    if choice == "4" or choice == "":
        run_different_customers_test()
    
    if choice == "5" or choice == "":
        run_card_validation_test()
    
    if choice == "6" or choice == "":
        run_payment_status_check()
    
    if choice == "7" or choice == "":
        run_list_payments_test()
    
    print("\n" + "=" * 80)
    print("✓ All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
