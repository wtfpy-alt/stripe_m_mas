from fastapi import FastAPI, HTTPException, Query
import os
import asyncio
import time
from typing import Dict

from playwright_automation import run_checkout

app = FastAPI()

SECRET = "WTFH4RSH"
TARGET_URL = os.environ.get("RAZORPAY_TARGET_URL", "https://pages.razorpay.com/pl_Qhw5srUaiC30d5/view")

# Simple in-memory rate limiter per auth token
_RATE_LIMIT: Dict[str, list] = {}
MAX_PER_MINUTE = int(os.environ.get("MAX_PER_MINUTE", "50"))


def allowed_to_proceed(token: str) -> bool:
    now = time.time()
    window = 60.0
    history = _RATE_LIMIT.get(token, [])
    # remove old entries
    history = [t for t in history if now - t < window]
    if len(history) >= MAX_PER_MINUTE:
        _RATE_LIMIT[token] = history
        return False
    history.append(now)
    _RATE_LIMIT[token] = history
    return True


@app.get("/razorpay")
async def razorpay(auth: str = Query(...), cc: str = Query(...)):
    if auth != SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not allowed_to_proceed(auth):
        raise HTTPException(status_code=429, detail="Too many requests")

    # Run the Playwright automation in a thread to avoid blocking
    # headless=False so you can watch the browser
    result = await asyncio.to_thread(run_checkout, cc, TARGET_URL, True, 3, None)
    return result


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )


