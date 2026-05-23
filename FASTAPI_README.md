# Razorpay Card Checker FastAPI Backend

High-performance async FastAPI server for Razorpay card checking (~200 RPS).

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_fastapi.txt
```

### 2. Run Server
```bash
# Development (single worker)
python rzapi_fastapi.py

# Production (4 workers, recommended)
uvicorn rzapi_fastapi:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop
```

### 3. Test API
```bash
python test_fastapi.py
```

## API Endpoints

### POST /check - Single Card
```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d '{
    "cc": "4111111111111111",
    "mm": "12",
    "yy": "25",
    "cvv": "123",
    "auth": "technopile",
    "amount": 1
  }'
```

### POST /check-bulk - Bulk Cards
```bash
curl -X POST http://localhost:8000/check-bulk \
  -H "Content-Type: application/json" \
  -d '{
    "cards": [
      "4111111111111111|12|25|123",
      "5555555555554444|01|26|456"
    ],
    "auth": "technopile",
    "amount": 1
  }'
```

### GET /stats - Get Statistics
```bash
curl http://localhost:8000/stats
```

### GET /health - Health Check
```bash
curl http://localhost:8000/health
```

### GET /docs - Interactive Docs
Open: http://localhost:8000/docs

## Response Example
```json
{
  "status": "charged|live|ccn|dead|error",
  "card": "4111...1111",
  "message": "Success",
  "payment_id": "pay_xxx",
  "time_taken": 5.23,
  "timestamp": "2024-05-23T12:34:56.789"
}
```

## Performance
- **200+ RPS** with 4 workers
- **Connection pooling** with 500 connections
- **Fully async** I/O operations
- **Concurrent bulk** processing

## Docker
```bash
docker build -f Dockerfile.fastapi -t rzapi .
docker run -p 8000:8000 rzapi
```
