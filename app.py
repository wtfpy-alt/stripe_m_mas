from fastapi import FastAPI, HTTPException, Query, Request
import os
import asyncio
import time
from typing import Dict, Tuple
from concurrent.futures import ProcessPoolExecutor
import logging

from playwright_automation import run_checkout

app = FastAPI()

SECRET = "WTFH4RSH"
TARGET_URL = os.environ.get("RAZORPAY_TARGET_URL", "https://pages.razorpay.com/pl_Qhw5srUaiC30d5/view")

# Rate limiting per (auth_token, client_ip) combination
# Key: (token, ip), Value: list of timestamps
_RATE_LIMIT: Dict[Tuple[str, str], list] = {}
RATE_LIMIT_WINDOW = 10.0  # 10 seconds per IP address
MAX_REQUESTS_PER_WINDOW = 1  # 1 request per 10 seconds per IP per token

# Process pool for handling automation tasks
_PROCESS_POOL = ProcessPoolExecutor(
    max_workers=int(os.environ.get("MAX_WORKERS", "4"))
)

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request, handling proxies"""
    # Check X-Forwarded-For header (for proxies/load balancers)
    if request.headers.get("x-forwarded-for"):
        return request.headers.get("x-forwarded-for").split(",")[0].strip()
    
    # Check X-Real-IP header
    if request.headers.get("x-real-ip"):
        return request.headers.get("x-real-ip")
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


def allowed_to_proceed(token: str, client_ip: str) -> bool:
    """Check rate limit for (token, client_ip) combination"""
    now = time.time()
    key = (token, client_ip)
    
    history = _RATE_LIMIT.get(key, [])
    # Remove old entries outside the window
    history = [t for t in history if now - t < RATE_LIMIT_WINDOW]
    
    # Check if limit exceeded
    if len(history) >= MAX_REQUESTS_PER_WINDOW:
        _RATE_LIMIT[key] = history
        return False
    
    # Record this request
    history.append(now)
    _RATE_LIMIT[key] = history
    return True


@app.get("/razorpay")
async def razorpay(
    request: Request,
    auth: str = Query(...),
    cc: str = Query(...)
):
    """Razorpay checkout endpoint with IP-based rate limiting per auth token.
    
    Parameters:
    - auth: Authentication token (must match SECRET)
    - cc: Card details in format "card_number:expiry:cvv" or just "card_number"
         Examples:
         - "4111111111111111:12/25:123"
         - "4111111111111111" (uses default 12/28 and CVV 123)
    """
    if auth != SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    client_ip = get_client_ip(request)
    logger.info(f"Request from {client_ip} with auth token: {auth}")
    
    if not allowed_to_proceed(auth, client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max 1 request per {RATE_LIMIT_WINDOW} seconds per IP address"
        )
    
    # Run the Playwright automation using process pool executor
    # This provides better isolation and traffic management
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            _PROCESS_POOL,
            run_checkout,
            cc,
            TARGET_URL,
            False,  # headless
            3,     # attempts
            None   # event_id
        )
        return result
    except Exception as e:
        logger.error(f"Checkout failed for {client_ip}: {str(e)}")
        raise HTTPException(status_code=500, detail="Checkout automation failed")

@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/stats")
async def get_stats():
    """Get rate limiting statistics"""
    stats = {
        "total_tracked_ips": len(_RATE_LIMIT),
        "rate_limit_window_seconds": RATE_LIMIT_WINDOW,
        "max_requests_per_window": MAX_REQUESTS_PER_WINDOW,
        "active_limits": {}
    }
    
    now = time.time()
    for (token, ip), timestamps in _RATE_LIMIT.items():
        # Only show active limits (within the window)
        recent = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        if recent:
            stats["active_limits"][f"{token}:{ip}"] = {
                "requests_in_window": len(recent),
                "oldest_request_age_sec": round(now - min(recent), 2)
            }
    
    return stats


@app.get("/config")
async def get_config():
    """Get current rate limiting configuration"""
    return {
        "rate_limit_window_seconds": RATE_LIMIT_WINDOW,
        "max_requests_per_window": MAX_REQUESTS_PER_WINDOW,
        "process_pool_max_workers": int(os.environ.get("MAX_WORKERS", "4")),
        "description": f"Max {MAX_REQUESTS_PER_WINDOW} request(s) per {RATE_LIMIT_WINDOW} seconds per IP address per auth token"
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup process pool on shutdown"""
    _PROCESS_POOL.shutdown(wait=True)
    logger.info("Process pool shut down")


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )


