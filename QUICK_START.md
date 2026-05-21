# 🚀 REFACTORED BOT - Quick Start Guide

## ⏱️ 5-Minute Setup

### Prerequisites
- Python 3.8+
- Telegram bot token (from @BotFather)
- Running backend services (Autoshopify + Stripe gates)

### Step 1: Install Dependencies (1 min)
```bash
cd /home/wtfpy/razorpay
pip install telebot requests
```

### Step 2: Update Configuration (1 min)
Edit `bot_refactored.py` and update:
```python
TOKEN = "YOUR_BOT_TOKEN"                      # Get from @BotFather
ADMIN_ID = YOUR_ADMIN_ID                      # Your Telegram user ID
AUTOSHOPIFY_API = "http://localhost:8000"    # Your Autoshopify backend
STRIPE_01_API = "http://localhost:2101"      # Stripe gate 1
STRIPE2_API = "http://localhost:2102"        # Stripe gate 2
```

### Step 3: Start Bot (1 min)
```bash
python bot_refactored.py
```

Expected output:
```
✅ Bot initialized with Autoshopify + Stripe gates
🔌 Autoshopify API: http://localhost:8000
🔌 Stripe Gate 1: http://localhost:2101
🔌 Stripe Gate 2: http://localhost:2102
🚀 Starting bot...
```

### Step 4: Test in Telegram (2 min)
1. Open Telegram and find your bot
2. Send `/start` to bot
3. Click "🔍 Check Card"
4. Click a payment method
5. Send test card: `4111111111111111|12|25|123`
6. Bot responds with result

**✅ You're done!**

---

## 🎮 User Interface

### Main Menu Buttons
```
🔍 Check Card     → Single card checking
📊 Bulk Check     → Multiple cards at once  
💰 Credits        → View current balance
💳 Plans          → Upgrade options
📖 Help           → Information
```

### Payment Methods
```
🛍️ Autoshopify    → Shopify checkout flow
💳 Stripe (Gate 1) → First Stripe processor
💳 Stripe (Gate 2) → Second Stripe processor
```

---

## 💡 Key Features

✅ **Single message editing** - No spam, only edits one message
✅ **200 daily free credits** - Every new user gets free credits
✅ **OTP bypass logic** - Auto-retries on alternate Stripe gate
✅ **Real-time progress** - Live progress bar during bulk checking
✅ **Result files** - Text file exports by status (charged, approved, declined, otp, errors)
✅ **HTML formatting** - Better visual presentation
✅ **Inline buttons only** - No manual commands needed

---

## 📋 Card Input Format

Send card details as: `card|month|year|cvc`

### Example
```
4111111111111111|12|25|123
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `REFACTORED_BOT_GUIDE.md` | Complete feature documentation |
| `MIGRATION_GUIDE.md` | Changes from old bot |
| `AUTOSHOPIFY_INTEGRATION.md` | Backend integration details |
| `bot_refactored.py` | Main bot code |
| `bot_core.py` | Core utilities and helpers |

---

## 🆘 Troubleshooting

### Bot doesn't start
```bash
# Check Python version
python --version

# Check imports
python -c "import telebot; import requests"

# Check token is set
grep TOKEN bot_refactored.py
```

### Bot doesn't respond
```bash
# Restart bot
Ctrl+C
python bot_refactored.py

# Check logs
tail -f bot.log
```

### API connection fails
```bash
# Test Autoshopify
curl -X POST http://localhost:8000/check -H "Content-Type: application/json" -d '{"card": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvc": "123"}'

# Test Stripe gates
curl http://localhost:2101/stripe
curl http://localhost:2102/stripe2
```

---

## 🔧 Useful Commands

### Check user credits
```bash
sqlite3 users.db "SELECT user_id, credits FROM users;"
```

### View card checks
```bash
sqlite3 users.db "SELECT * FROM card_checks LIMIT 5;"
```

### Add credits to user
```bash
sqlite3 users.db "UPDATE users SET credits = 1000 WHERE user_id = 123456;"
```

### Reset daily usage
```bash
sqlite3 users.db "UPDATE users SET daily_credits_used = 0;"
```

---

## ✅ Deployment Checklist

Before going live:
- [ ] Bot token updated
- [ ] Admin ID set
- [ ] API URLs configured correctly
- [ ] All backends running and responding
- [ ] Test single card check
- [ ] Test bulk card check
- [ ] Test OTP bypass
- [ ] Database created (users.db)
- [ ] Result files directory exists (/tmp)
- [ ] Logs are being written

---

## 📞 Next Steps

1. Review [REFACTORED_BOT_GUIDE.md](REFACTORED_BOT_GUIDE.md) for complete documentation
2. Check [AUTOSHOPIFY_INTEGRATION.md](AUTOSHOPIFY_INTEGRATION.md) for backend setup
3. Read [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) to understand changes
4. Start testing with real cards when ready
5. Monitor performance and adjust configuration as needed

**Status**: ✅ Ready to deploy!
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
