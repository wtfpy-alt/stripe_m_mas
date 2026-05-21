# Payment Processing API - Quick Start Guide

## 🚀 Quick Start

### Option 1: Run Locally (Python)

#### Prerequisites
- Python 3.7+
- pip

#### Steps

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the API server:**
   ```bash
   python payment_api.py
   ```
   
   Or use uvicorn directly:
   ```bash
   uvicorn payment_api:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access the API:**
   - API Docs (Swagger UI): http://localhost:8000/docs
   - API Docs (ReDoc): http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

---

### Option 2: Run with Docker

#### Prerequisites
- Docker

#### Steps

1. **Build Docker image:**
   ```bash
   docker build -t payment-api:latest .
   ```

2. **Run container:**
   ```bash
   docker run -p 8000:8000 payment-api:latest
   ```

3. **Access the API:**
   - http://localhost:8000/docs

---

## 📊 API Features

### Supported Card Types
- ✓ Visa
- ✓ Mastercard
- ✓ American Express
- ✓ Discover
- ✓ Diners Club
- ✓ JCB

### Payment Statuses
- `charged` - Successfully processed
- `declined` - Card declined
- `approved` - Authorized (not captured)
- `otp_required` - 3D Secure required

### Main Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/payments/process` | Process a payment |
| GET | `/api/payments/{id}` | Get payment status |
| GET | `/api/payments` | List all payments |
| POST | `/api/payments/validate` | Validate card details |
| GET | `/health` | Health check |

---

## 🧪 Testing

### Option 1: Use Swagger UI
1. Open http://localhost:8000/docs
2. Click on `/api/payments/process`
3. Click "Try it out"
4. Enter test card details
5. Click "Execute"

### Option 2: Use Test Script
```bash
python test_payment_api.py
```

This will run an interactive test suite with:
- Single payment test
- Multiple card types
- Different amounts
- Different customers
- Card validation
- Payment status checks

### Option 3: Use cURL
```bash
curl -X POST http://localhost:8000/api/payments/process \
  -H "Content-Type: application/json" \
  -d '{
    "card": {
      "number": "4242424242424248",
      "exp_month": 6,
      "exp_year": 28,
      "cvc": "123"
    },
    "amount": 50000,
    "currency": "USD",
    "email": "test@example.com",
    "name": "Test User",
    "address": {
      "line1": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "postal_code": "94103"
    }
  }'
```

---

## 💳 Test Card Numbers

Based on card number patterns (especially last digit):

| Card Type | Number | Expected Result |
|-----------|--------|-----------------|
| Visa (Charged) | 4242424242424248 | charged |
| Visa (Declined) | 4242424242424241 | declined |
| Visa (OTP) | 4242424242424240 | otp_required |
| Mastercard (Approved) | 5555555555554444 | approved |
| Mastercard (Charged) | 5555555555554448 | charged |
| Amex (Charged) | 378282246310005 | charged |
| Discover (Charged) | 6011111111111118 | charged |

**Last digit logic:**
- 0 = otp_required
- 1, 2 = declined
- 3, 4 = approved
- 5-9 = charged

---

## 📝 Example Request/Response

### Request
```json
{
  "card": {
    "number": "4242424242424248",
    "exp_month": 6,
    "exp_year": 28,
    "cvc": "123"
  },
  "amount": 50000,
  "currency": "USD",
  "email": "john@example.com",
  "name": "John Doe",
  "address": {
    "line1": "123 Main Street",
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94103",
    "country": "US"
  },
  "description": "Purchase order",
  "metadata": {
    "order_id": "ORD-12345"
  }
}
```

### Response
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "charged",
  "amount": 500.00,
  "currency": "USD",
  "card_type": "visa",
  "card_last4": "4248",
  "customer_email": "john@example.com",
  "customer_name": "John Doe",
  "message": "Payment successfully charged",
  "timestamp": "2026-05-21T10:30:45.123456",
  "error_code": null,
  "error_message": null
}
```

---

## 📚 Documentation

- **Full API Guide**: See [PAYMENT_API_GUIDE.md](PAYMENT_API_GUIDE.md)
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔧 Configuration

### Environment Variables
```bash
export STRIPE_PUBLIC_KEY="pk_live_YOUR_KEY_HERE"
python payment_api.py
```

### Custom Port
```bash
uvicorn payment_api:app --host 0.0.0.0 --port 8080
```

### Production Deployment
For production, consider:
1. Using a database (PostgreSQL, MongoDB)
2. Adding authentication/API keys
3. Implementing rate limiting
4. Adding request logging
5. Using HTTPS
6. Setting up monitoring and alerts

---

## 📞 Troubleshooting

### API won't start
```bash
# Check if port is in use
lsof -i :8000

# Use different port
uvicorn payment_api:app --port 8001
```

### Can't connect to Stripe
- Check internet connection
- Verify firewall settings
- Check proxy configuration

### Card always declines
- Verify card number format (16 digits for Visa/Mastercard)
- Check card number passes Luhn validation
- Try different test cards

### Tests fail
- Ensure API is running (`python payment_api.py`)
- Check API is accessible at http://localhost:8000/health
- Verify no firewalls blocking connections

---

## 🎯 Complete Payment Flow

```
1. Health Check
   └─ GET /health

2. Validate Card (optional)
   └─ POST /api/payments/validate

3. Process Payment
   ├─ Fetch payment link details (internal)
   ├─ Create payment session (internal)
   ├─ Tokenize card (internal)
   ├─ Confirm payment (internal)
   ├─ Check intent status (internal)
   └─ Return payment_id and status

4. Check Payment Status
   └─ GET /api/payments/{payment_id}

5. List Payments
   └─ GET /api/payments
```

---

## 📊 Performance

- **Average response time**: < 5 seconds
- **Concurrent requests**: Unlimited (limited by system resources)
- **Request timeout**: 30 seconds per step

---

## 🔒 Security Considerations

### Current Implementation
- ⚠️ No authentication
- ⚠️ No rate limiting
- ⚠️ In-memory storage (lost on restart)

### Production Recommendations
- ✓ Add API key authentication
- ✓ Implement rate limiting (100 requests/min)
- ✓ Use database for persistence
- ✓ Enable HTTPS/TLS
- ✓ Validate all inputs
- ✓ Log all transactions
- ✓ Implement fraud detection
- ✓ Use VPN/IP whitelisting

---

## 📄 License

This project is provided as-is for educational and testing purposes.

---

## 🤝 Support

For issues or questions:
1. Check the comprehensive [PAYMENT_API_GUIDE.md](PAYMENT_API_GUIDE.md)
2. Review error messages in responses
3. Test with Swagger UI: http://localhost:8000/docs
4. Run test script: `python test_payment_api.py`
