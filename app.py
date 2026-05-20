from fastapi import FastAPI, HTTPException, Query, Request
import os
import asyncio
import time
from typing import Dict, Tuple
from concurrent.futures import ProcessPoolExecutor
import logging

from playwright_automation import run_checkout

app = FastAPI()

# Token-based rate limiting configuration
# Each token can have different rate limit settings
TOKEN_CONFIG = {
    "WTFH4RSH": {
        "rate_limit_window": 10.0,      # 10 seconds per IP
        "max_per_window": 1,             # 1 request per window
        "max_total": None                # Unlimited total
    },
    "technopile": {
        "rate_limit_window": 10.0,      # 10 seconds per IP
        "max_per_window": 1,             # 1 request per window
        "max_total": 50                  # Max 50 checks total
    }
}

TARGET_URL = os.environ.get("RAZORPAY_TARGET_URL", "https://pages.razorpay.com/pl_Qhw5srUaiC30d5/view")

# Rate limiting per (auth_token, client_ip) combination
# Key: (token, ip), Value: list of timestamps
_RATE_LIMIT: Dict[Tuple[str, str], list] = {}

# Global check counters per token (for max_total limit)
_TOTAL_CHECKS: Dict[str, int] = {}

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


def allowed_to_proceed(token: str, client_ip: str) -> tuple:
    """Check rate limit for (token, client_ip) combination.
    
    Returns: (allowed: bool, reason: str)
    """
    if token not in TOKEN_CONFIG:
        return False, "Invalid auth token"
    
    config = TOKEN_CONFIG[token]
    now = time.time()
    key = (token, client_ip)
    
    # Check total limit for this token
    if config["max_total"] is not None:
        total_checks = _TOTAL_CHECKS.get(token, 0)
        if total_checks >= config["max_total"]:
            return False, f"Token {token} has reached maximum of {config['max_total']} total checks"
    
    # Check per-IP per-window rate limit
    history = _RATE_LIMIT.get(key, [])
    # Remove old entries outside the window
    history = [t for t in history if now - t < config["rate_limit_window"]]
    
    # Check if limit exceeded
    if len(history) >= config["max_per_window"]:
        _RATE_LIMIT[key] = history
        return False, f"Rate limit exceeded. Max {config['max_per_window']} request(s) per {config['rate_limit_window']} seconds per IP address"
    
    # Record this request
    history.append(now)
    _RATE_LIMIT[key] = history
    
    # Increment total check counter
    _TOTAL_CHECKS[token] = _TOTAL_CHECKS.get(token, 0) + 1
    
    return True, "Allowed"


@app.get("/razorpay")
async def razorpay(
    request: Request,
    auth: str = Query(...),
    cc: str = Query(...)
):
    """Razorpay checkout endpoint with IP-based rate limiting per auth token.
    
    Supported auth tokens:
    - "WTFH4RSH": 1 request per 10 seconds per IP (unlimited total)
    - "technopile": 1 request per 10 seconds per IP (max 50 total checks)
    
    Parameters:
    - auth: Authentication token
    - cc: Card details in format "card_number:expiry:cvv" or just "card_number"
         Examples:
         - "4111111111111111:12/25:123"
         - "4111111111111111" (uses default 12/28 and CVV 123)
    """
    # Validate token
    if auth not in TOKEN_CONFIG:
        raise HTTPException(status_code=401, detail="Invalid or unauthorized token")
    
    client_ip = get_client_ip(request)
    logger.info(f"Request from {client_ip} with auth token: {auth}")
    
    # Check rate limit
    allowed, reason = allowed_to_proceed(auth, client_ip)
    if not allowed:
        logger.warning(f"Rate limit denied for {auth}:{client_ip} - {reason}")
        raise HTTPException(status_code=429, detail=reason)
    
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
    """Get rate limiting statistics per token"""
    stats = {
        "tokens": {}
    }
    
    now = time.time()
    
    # Per-token statistics
    for token in TOKEN_CONFIG.keys():
        config = TOKEN_CONFIG[token]
        total_checks = _TOTAL_CHECKS.get(token, 0)
        
        token_stats = {
            "config": config,
            "total_checks_used": total_checks,
            "active_ips": {}
        }
        
        # Count active IPs for this token
        for (t, ip), timestamps in _RATE_LIMIT.items():
            if t != token:
                continue
            recent = [ts for ts in timestamps if now - ts < config["rate_limit_window"]]
            if recent:
                token_stats["active_ips"][ip] = {
                    "requests_in_window": len(recent),
                    "oldest_request_age_sec": round(now - min(recent), 2)
                }
        
        # Show if max_total limit is approaching
        if config["max_total"] is not None:
            remaining = config["max_total"] - total_checks
            token_stats["max_total_remaining"] = remaining
            token_stats["max_total_percentage_used"] = round((total_checks / config["max_total"]) * 100, 2)
        
        stats["tokens"][token] = token_stats
    
    return stats


@app.get("/config")
async def get_config():
    """Get all token configurations and rate limiting settings"""
    return {
        "tokens": TOKEN_CONFIG,
        "description": {
            "WTFH4RSH": "Default token - 1 request per 10 seconds per IP, unlimited total checks",
            "technopile": "Limited token - 1 request per 10 seconds per IP, maximum 50 total checks"
        }
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


