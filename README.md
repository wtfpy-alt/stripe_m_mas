# Razorpay FastAPI Automator

This repository provides a small FastAPI app exposing a single endpoint to exercise the Razorpay checkout flow using Playwright.

Endpoint format:

```
GET /razorpay?auth=MY_SECRET_TOKEN&cc=4111111111111111
```

Environment variables:

- `RAZORPAY_AUTH_TOKEN` — secret token used to authorize requests (defaults to `MY_SECRET_TOKEN`).
- `RAZORPAY_TARGET_URL` — optional override of the Razorpay payment page URL.

Quick start (virtualenv):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# install browsers for playwright
python -m playwright install chromium

# run the API
uvicorn app:app --host 0.0.0.0 --port 8000
```

Notes about hosting:

- Render: recommended. Create a web service that runs `uvicorn app:app --host 0.0.0.0 --port $PORT`. Ensure the service's startup script runs `python -m playwright install chromium` during build or startup and set `RAZORPAY_AUTH_TOKEN` in environment settings.
- Vercel: not recommended for Playwright because Vercel serverless environments have restrictions and Playwright requires bundled browsers and specific runtime support.

Security:

- Keep `RAZORPAY_AUTH_TOKEN` secret. This server will execute browser automation and can perform real payments — treat the environment carefully.
# Rzp
