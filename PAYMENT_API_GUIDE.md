# Payment Processing API - Usage Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the API Server
```bash
python payment_api.py
```

The API will start at `http://localhost:8000`

### 3. Access API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Endpoints

### 1. Health Check
**GET** `/health`

Check if the API is running.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Payment Processing API",
  "timestamp": "2026-05-21T10:30:45.123456"
}
```

---

### 2. Process Payment
**POST** `/api/payments/process`

Process a complete payment transaction.

**Request Body:**
```json
{
  "card": {
    "number": "4242424242424242",
    "exp_month": 6,
    "exp_year": 28,
    "cvc": "000"
  },
  "amount": 270836,
  "currency": "USD",
  "email": "customer@example.com",
  "name": "John Doe",
  "address": {
    "line1": "1620 Northwest 23rd Avenue",
    "city": "Portland",
    "state": "OR",
    "postal_code": "97210",
    "country": "US"
  },
  "description": "Purchase of premium subscription",
  "metadata": {
    "order_id": "ORD-12345",
    "user_id": "USR-789"
  }
}
```

**Response (Success):**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "charged",
  "amount": 2708.36,
  "currency": "USD",
  "card_type": "visa",
  "card_last4": "4242",
  "customer_email": "customer@example.com",
  "customer_name": "John Doe",
  "message": "Payment successfully charged",
  "timestamp": "2026-05-21T10:30:45.123456",
  "error_code": null,
  "error_message": null
}
```

---

### 3. Get Payment Status
**GET** `/api/payments/{payment_id}`

Retrieve the status of a processed payment.

```bash
curl http://localhost:8000/api/payments/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "charged",
  "amount": 2708.36,
  "currency": "USD",
  "card_last4": "4242",
  "timestamp": "2026-05-21T10:30:45.123456",
  "message": "Payment successfully charged"
}
```

---

### 4. List All Payments
**GET** `/api/payments?limit=10`

List all processed payments.

```bash
curl http://localhost:8000/api/payments?limit=10
```

**Response:**
```json
{
  "total": 5,
  "payments": [
    {
      "payment_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "charged",
      "amount": 2708.36,
      "currency": "USD",
      "card_type": "visa",
      "card_last4": "4242",
      "email": "customer@example.com",
      "name": "John Doe",
      "timestamp": "2026-05-21T10:30:45.123456"
    }
  ]
}
```

---

### 5. Validate Card
**POST** `/api/payments/validate`

Validate card details without processing payment.

**Request Body:**
```json
{
  "number": "4242424242424242",
  "exp_month": 6,
  "exp_year": 28,
  "cvc": "000"
}
```

**Response:**
```json
{
  "card_number": "****4242",
  "card_type": "visa",
  "is_valid": true,
  "exp_month": 6,
  "exp_year": 28
}
```

---

## Payment Status Types

| Status | Description |
|--------|-------------|
| `charged` | Payment successfully processed and charged |
| `declined` | Card was declined or authentication failed |
| `approved` | Payment authorized but not yet captured |
| `otp_required` | 3D Secure/OTP authentication required |
| `processing` | Payment is being processed |
| `failed` | Payment processing failed |

---

## Test Card Numbers

The API determines payment outcomes based on card number patterns:

| Card Type | Number | Last Digit | Result |
|-----------|--------|-----------|--------|
| Visa | 4242424242424242 | 2 | DECLINED |
| Mastercard | 5555555555554444 | 4 | APPROVED |
| Discover | 6011014839295628 | 8 | CHARGED |
| Amex | 378282246310005 | 5 | APPROVED |

### Outcome Based on Last Digit:
- **Last digit = 0**: OTP_REQUIRED
- **Last digit = 1, 2**: DECLINED
- **Last digit = 3, 4**: APPROVED
- **Last digit = 5-9**: CHARGED

---

## Supported Card Types

The API automatically detects and supports:
- **Visa** (starts with 4)
- **Mastercard** (starts with 51-55, 2221-2720)
- **American Express** (starts with 34, 37)
- **Discover** (starts with 6011, 644, 65)
- **Diners Club** (starts with 36, 38, 30)
- **JCB** (starts with 3528-3589)

---

## Full Payment Flow

The `/api/payments/process` endpoint implements the complete Stripe payment flow:

```
1. Fetch Payment Link Details
   └─ Retrieve dynamic pk_live key from payment link

2. Create Payment Session
   └─ Generate cs_live session ID

3. Create Payment Method (Tokenize Card)
   └─ Secure card details and create payment method

4. Confirm Payment Page
   └─ Confirm the payment with session and method

5. Check Payment Intent Status
   └─ Retrieve final payment status (charged/declined/otp_required/approved)
```

---

## Python Usage Examples

### Example 1: Process a Visa Payment
```python
import requests

url = "http://localhost:8000/api/payments/process"

payload = {
    "card": {
        "number": "4242424242424242",
        "exp_month": 6,
        "exp_year": 28,
        "cvc": "123"
    },
    "amount": 50000,  # $500.00 in cents
    "currency": "USD",
    "email": "john@example.com",
    "name": "John Smith",
    "address": {
        "line1": "123 Main Street",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94103",
        "country": "US"
    }
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Payment ID: {result['payment_id']}")
print(f"Status: {result['status']}")
print(f"Message: {result['message']}")
```

### Example 2: Check Payment Status
```python
import requests

payment_id = "550e8400-e29b-41d4-a716-446655440000"
url = f"http://localhost:8000/api/payments/{payment_id}"

response = requests.get(url)
result = response.json()

print(f"Status: {result['status']}")
print(f"Amount: ${result['amount']:.2f}")
```

### Example 3: Validate Card Before Processing
```python
import requests

url = "http://localhost:8000/api/payments/validate"

payload = {
    "number": "5555555555554444",
    "exp_month": 12,
    "exp_year": 28,
    "cvc": "456"
}

response = requests.post(url, json=payload)
result = response.json()

if result['is_valid']:
    print(f"Card {result['card_number']} is valid ({result['card_type']})")
else:
    print("Invalid card")
```

---

## cURL Examples

### Process Payment
```bash
curl -X POST http://localhost:8000/api/payments/process \
  -H "Content-Type: application/json" \
  -d '{
    "card": {
      "number": "4242424242424242",
      "exp_month": 6,
      "exp_year": 28,
      "cvc": "123"
    },
    "amount": 50000,
    "currency": "USD",
    "email": "john@example.com",
    "name": "John Smith",
    "address": {
      "line1": "123 Main Street",
      "city": "San Francisco",
      "state": "CA",
      "postal_code": "94103"
    }
  }'
```

### Get Payment Status
```bash
curl http://localhost:8000/api/payments/550e8400-e29b-41d4-a716-446655440000
```

### Validate Card
```bash
curl -X POST http://localhost:8000/api/payments/validate \
  -H "Content-Type: application/json" \
  -d '{
    "number": "4242424242424242",
    "exp_month": 6,
    "exp_year": 28,
    "cvc": "123"
  }'
```

---

## Error Handling

### Invalid Card Number
```json
{
  "detail": "Payment processing failed: Card number must be 13-16 digits"
}
```

### Payment Not Found
```json
{
  "detail": "Payment with ID abc123 not found"
}
```

### Invalid Amount
```json
{
  "detail": "ensure this value is greater than 0 (type=value_error.number.not_gt; limit_value=0)"
}
```

---

## Environment Variables

Set the Stripe public key via environment variable:

```bash
export STRIPE_PUBLIC_KEY="pk_live_YOUR_KEY_HERE"
python payment_api.py
```

If not set, the API uses a default test key.

---

## Integration Notes

### For Production:
1. **Database**: Replace `payment_records` dict with a persistent database (PostgreSQL, MongoDB, etc.)
2. **Authentication**: Add API key authentication and rate limiting
3. **Validation**: Add additional fraud detection and validation
4. **Logging**: Implement comprehensive logging and monitoring
5. **Security**: Use HTTPS, implement CORS properly, validate all inputs
6. **Error Handling**: Implement comprehensive error handling and retries

### For Testing:
- Use the provided test card numbers
- Monitor the Swagger UI at http://localhost:8000/docs
- Check payment records via the `/api/payments` endpoint

---

## Troubleshooting

### API Won't Start
```bash
# Make sure port 8000 is available
lsof -i :8000

# Use a different port
python -c "import uvicorn; uvicorn.run('payment_api:app', host='0.0.0.0', port=8001)"
```

### Can't Connect to Stripe
- Check internet connection
- Verify API endpoints are accessible
- Check firewall/proxy settings

### Card Always Declines
- Use correct test card format (16 digits)
- Check card type is supported
- Verify card number checksum (Luhn algorithm)

---

## API Rate Limits

Currently no rate limiting. Implement in production based on your requirements.

---

## Support

For issues or questions, check:
1. Swagger UI documentation: http://localhost:8000/docs
2. ReDoc documentation: http://localhost:8000/redoc
3. Error messages in payment responses
