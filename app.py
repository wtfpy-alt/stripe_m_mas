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
        "rate_limit_window": None,       # No rate limiting
        "max_per_window": None,          # No limit per window
        "max_total": None                # Unlimited total
    },
    "technopile": {
        "rate_limit_window": 5.0,        # 5 seconds per request
        "max_per_window": 1,             # 1 request per window
        "max_total": None                # Unlimited total
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
    
    Returns: (allowed: bool, reason: str, wait_time: float)
    """
    if token not in TOKEN_CONFIG:
        return False, "Invalid auth token", 0
    
    config = TOKEN_CONFIG[token]
    now = time.time()
    key = (token, client_ip)
    
    # No rate limiting for this token
    if config["rate_limit_window"] is None:
        _TOTAL_CHECKS[token] = _TOTAL_CHECKS.get(token, 0) + 1
        return True, "Allowed (no rate limiting)", 0
    
    # Check total limit for this token
    if config["max_total"] is not None:
        total_checks = _TOTAL_CHECKS.get(token, 0)
        if total_checks >= config["max_total"]:
            return False, f"Token {token} has reached maximum of {config['max_total']} total checks", 0
    
    # Check per-IP per-window rate limit
    history = _RATE_LIMIT.get(key, [])
    # Remove old entries outside the window
    valid_history = [t for t in history if now - t < config["rate_limit_window"]]
    
    # Check if limit exceeded
    if len(valid_history) >= config["max_per_window"]:
        # Calculate wait time
        oldest = min(valid_history)
        wait_time = round(config["rate_limit_window"] - (now - oldest), 2)
        _RATE_LIMIT[key] = valid_history
        return False, f"Rate limit exceeded. Wait {wait_time}s. Max {config['max_per_window']} request(s) per {config['rate_limit_window']} seconds", wait_time
    
    # Record this request
    valid_history.append(now)
    _RATE_LIMIT[key] = valid_history
    
    # Increment total check counter
    _TOTAL_CHECKS[token] = _TOTAL_CHECKS.get(token, 0) + 1
    
    return True, "Allowed", 0


@app.get("/razorpay")
async def razorpay(
    request: Request,
    auth: str = Query(...),
    cc: str = Query(...)
):
    """Razorpay checkout endpoint with IP-based rate limiting per auth token.
    
    Supported auth tokens:
    - "WTFH4RSH": No rate limiting
    - "technopile": 1 request per 5 seconds per IP
    
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
    allowed, reason, wait_time = allowed_to_proceed(auth, client_ip)
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


@app.get("/stripe/oauth")
async def stripe_oauth(
    request: Request,
    auth: str = Query(...),
    cc: str = Query(...)
):
    """Stripe card validation endpoint - checks if card is approved WITHOUT charging.
    
    Only validates the card (Steps 0, 0b, 1) - does NOT process payment or charge.
    
    Supported auth tokens:
    - "WTFH4RSH": No rate limiting (unlimited card checks)
    - "technopile": 1 check per 5 seconds per IP
    
    Parameters:
    - auth: Authentication token
    - cc: Card details in format "number|mm|yy|cvv"
         Examples:
         - "4242424242424248|06|28|123"
         - "5555555555554444|12|2028|456"  (supports both 2 and 4-digit years)
    
    Returns:
    - Card validation result with approval status, card type, and details
    """
    # Validate token
    if auth not in TOKEN_CONFIG:
        raise HTTPException(status_code=401, detail="Invalid or unauthorized token")
    
    client_ip = get_client_ip(request)
    logger.info(f"Card validation request from {client_ip} with auth token: {auth}")
    
    # Check rate limit
    allowed, reason, wait_time = allowed_to_proceed(auth, client_ip)
    if not allowed:
        logger.warning(f"Rate limit denied for {auth}:{client_ip} - {reason}")
        raise HTTPException(status_code=429, detail=reason)
    
    # Parse card details from "number|mm|yy|cvv" format
    try:
        parts = cc.split("|")
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="Invalid card format. Use: number|mm|yy|cvv")
        
        card_number = parts[0].strip()
        exp_month = int(parts[1].strip())
        exp_year = int(parts[2].strip())
        cvc = parts[3].strip()
        
        # Convert 4-digit year to 2-digit if needed (e.g., 2028 -> 28)
        if exp_year > 99:
            exp_year = exp_year % 100
        
        # Validate card number
        if not card_number.isdigit() or len(card_number) not in [13, 14, 15, 16]:
            raise HTTPException(status_code=400, detail="Card number must be 13-16 digits")
        
        # Validate expiry
        if not (1 <= exp_month <= 12):
            raise HTTPException(status_code=400, detail="Expiry month must be 01-12")
        
        if not (0 <= exp_year <= 99):
            raise HTTPException(status_code=400, detail="Expiry year must be 2-digit (00-99) or 4-digit (2000-2099)")
        
        # Validate CVC
        if not cvc.isdigit() or len(cvc) not in [3, 4]:
            raise HTTPException(status_code=400, detail="CVC must be 3-4 digits")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid card data format: {str(e)}")
    
    try:
        # Import and use stripe_payment_mimic for card validation only
        from stripe_payment_mimic import validate_card_only
        
        logger.info(f"Validating card for {client_ip} - Card ending in {card_number[-4:]}")
        result = validate_card_only(card_number, exp_month, exp_year, cvc)
        
        logger.info(f"Card validation result for {client_ip} - Status: {result.get('status')}")
        
        return {
            "approved": result.get("approved", False),
            "status": result.get("status"),
            "card_type": result.get("card_type"),
            "card_last4": result.get("card_last4"),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
            "note": "Card validation only - no charge initiated"
        }
    
    except ImportError as e:
        logger.error(f"Cannot import stripe_payment_mimic: {str(e)}")
        raise HTTPException(status_code=503, detail="Stripe validation module not available")
    except Exception as e:
        logger.error(f"Card validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Card validation error: {str(e)}")

@app.get("/stripe_01")
async def stripe(
    request: Request,
    auth: str = Query(...),
    cc: str = Query(...)
):
    """Stripe payment processing endpoint with rate limiting per auth token.
    
    Uses stripe_payment_mimic.py to process actual Stripe payment flows.
    
    Supported auth tokens:
    - "WTFH4RSH": No rate limiting (unlimited requests)
    - "technopile": 1 request per 5 seconds per IP
    
    Parameters:
    - auth: Authentication token
    - cc: Card details in format "number|mm|yy|cvv"
         Examples:
         - "4242424242424248|06|28|123"
         - "5555555555554444|12|2028|456"  (supports both 2 and 4-digit years)
         - "378282246310005|06|28|1234"
    
    Returns:
    - Stripe payment processing result with status, payment_id, and full details
    """
    # Validate token
    if auth not in TOKEN_CONFIG:
        raise HTTPException(status_code=401, detail="Invalid or unauthorized token")
    
    client_ip = get_client_ip(request)
    logger.info(f"Stripe payment request from {client_ip} with auth token: {auth}")
    
    # Check rate limit
    allowed, reason, wait_time = allowed_to_proceed(auth, client_ip)
    if not allowed:
        logger.warning(f"Rate limit denied for {auth}:{client_ip} - {reason}")
        raise HTTPException(status_code=429, detail=reason)
    
    # Parse card details from "number|mm|yy|cvv" format
    try:
        parts = cc.split("|")
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="Invalid card format. Use: number|mm|yy|cvv")
        
        card_number = parts[0].strip()
        exp_month = int(parts[1].strip())
        exp_year = int(parts[2].strip())
        cvc = parts[3].strip()
        
        # Convert 4-digit year to 2-digit if needed (e.g., 2028 -> 28)
        if exp_year > 99:
            exp_year = exp_year % 100
        
        # Validate card number
        if not card_number.isdigit() or len(card_number) not in [13, 14, 15, 16]:
            raise HTTPException(status_code=400, detail="Card number must be 13-16 digits")
        
        # Validate expiry
        if not (1 <= exp_month <= 12):
            raise HTTPException(status_code=400, detail="Expiry month must be 01-12")
        
        if not (0 <= exp_year <= 99):
            raise HTTPException(status_code=400, detail="Expiry year must be 2-digit (00-99) or 4-digit (2000-2099)")
        
        # Validate CVC
        if not cvc.isdigit() or len(cvc) not in [3, 4]:
            raise HTTPException(status_code=400, detail="CVC must be 3-4 digits")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid card data format: {str(e)}")
    
    # Prepare payment request
    import requests as req
    
    try:
        # Import and use stripe_payment_mimic for actual Stripe flow
        from stripe_payment_mimic import process_payment_with_card
        
        logger.info(f"Processing payment for {client_ip} - Card ending in {card_number[-4:]}")
        result = process_payment_with_card(card_number, exp_month, exp_year, cvc)
        
        logger.info(f"Payment result for {client_ip} - Status: {result.get('status')}")
        
        return {
            "success": result.get("success", False),
            "status": result.get("status"),
            "payment_id": result.get("payment_id"),
            "payment_method_id": result.get("payment_method_id"),
            "card_type": result.get("card_type"),
            "card_last4": result.get("card_last4"),
            "amount": result.get("amount"),
            "currency": result.get("currency"),
            "stripe_status": result.get("stripe_status"),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
            "error": result.get("error")
        }
    
    except ImportError as e:
        logger.error(f"Cannot import stripe_payment_mimic: {str(e)}")
        raise HTTPException(status_code=503, detail="Stripe payment module not available")
    except Exception as e:
        logger.error(f"Stripe payment error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Payment processing error: {str(e)}")


@app.get("/stripe2")
async def stripe2(
    request: Request,
    auth: str = Query(...),
    cc: str = Query(...)
):
    """Stripe payment processing endpoint v2 with alternative payment link and rate limiting per auth token.
    
    Uses stripe_payment_mimic.py to process actual Stripe payment flows with the new payment link.
    
    Supported auth tokens:
    - "WTFH4RSH": No rate limiting (unlimited requests)
    - "technopile": 1 request per 5 seconds per IP
    
    Parameters:
    - auth: Authentication token
    - cc: Card details in format "number|mm|yy|cvv"
         Examples:
         - "4242424242424248|06|28|123"
         - "5555555555554444|12|2028|456"  (supports both 2 and 4-digit years)
         - "378282246310005|06|28|1234"
    
    Returns:
    - Stripe payment processing result with status, payment_id, and full details
    """
    # Validate token
    if auth not in TOKEN_CONFIG:
        raise HTTPException(status_code=401, detail="Invalid or unauthorized token")
    
    client_ip = get_client_ip(request)
    logger.info(f"Stripe v2 payment request from {client_ip} with auth token: {auth}")
    
    # Check rate limit
    allowed, reason, wait_time = allowed_to_proceed(auth, client_ip)
    if not allowed:
        logger.warning(f"Rate limit denied for {auth}:{client_ip} - {reason}")
        raise HTTPException(status_code=429, detail=reason)
    
    # Parse card details from "number|mm|yy|cvv" format
    try:
        parts = cc.split("|")
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="Invalid card format. Use: number|mm|yy|cvv")
        
        card_number = parts[0].strip()
        exp_month = int(parts[1].strip())
        exp_year = int(parts[2].strip())
        cvc = parts[3].strip()
        
        # Convert 4-digit year to 2-digit if needed (e.g., 2028 -> 28)
        if exp_year > 99:
            exp_year = exp_year % 100
        
        # Validate card number
        if not card_number.isdigit() or len(card_number) not in [13, 14, 15, 16]:
            raise HTTPException(status_code=400, detail="Card number must be 13-16 digits")
        
        # Validate expiry
        if not (1 <= exp_month <= 12):
            raise HTTPException(status_code=400, detail="Expiry month must be 01-12")
        
        if not (0 <= exp_year <= 99):
            raise HTTPException(status_code=400, detail="Expiry year must be 2-digit (00-99) or 4-digit (2000-2099)")
        
        # Validate CVC
        if not cvc.isdigit() or len(cvc) not in [3, 4]:
            raise HTTPException(status_code=400, detail="CVC must be 3-4 digits")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid card data format: {str(e)}")
    
    # Prepare payment request with alternative payment link
    try:
        # Import and use stripe_payment_mimic for actual Stripe flow
        from stripe_payment_mimic import process_payment_with_card_v2
        
        logger.info(f"Processing v2 payment for {client_ip} - Card ending in {card_number[-4:]}")
        result = process_payment_with_card_v2(
            card_number,
            exp_month,
            exp_year,
            cvc,
            payment_link_id="28EaEX0ZR72t5CO2Icd3i1z",
            payment_link_url="https://buy.stripe.com"
        )
        
        logger.info(f"V2 payment result for {client_ip} - Status: {result.get('status')}")
        
        return {
            "success": result.get("success", False),
            "status": result.get("status"),
            "payment_id": result.get("payment_id"),
            "payment_method_id": result.get("payment_method_id"),
            "card_type": result.get("card_type"),
            "card_last4": result.get("card_last4"),
            "amount": result.get("amount"),
            "currency": result.get("currency"),
            "stripe_status": result.get("stripe_status"),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
            "error": result.get("error")
        }
    
    except ImportError as e:
        logger.error(f"Cannot import stripe_payment_mimic: {str(e)}")
        raise HTTPException(status_code=503, detail="Stripe payment module not available")
    except Exception as e:
        logger.error(f"Stripe v2 payment error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Payment processing error: {str(e)}")


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
            "rate_limiting_enabled": config["rate_limit_window"] is not None,
            "active_ips": {}
        }
        
        # Only show active IPs if rate limiting is enabled
        if config["rate_limit_window"] is not None:
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
        else:
            token_stats["active_ips"]["status"] = "No rate limiting"
        
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
            "WTFH4RSH": "No rate limiting - unlimited requests",
            "technopile": "1 request per 5 seconds per IP"
        },
        "endpoints": {
            "/stripe": {
                "method": "GET",
                "query_params": {
                    "auth": "Authentication token (WTFH4RSH or technopile)",
                    "cc": "Card details in format: number|mm|yy|cvv"
                },
                "payment_link": "28E5kDbEv0E59T4beId3i1r",
                "examples": [
                    "/stripe?auth=WTFH4RSH&cc=4242424242424248|06|28|123",
                    "/stripe?auth=technopile&cc=5555555555554444|12|28|456"
                ]
            },
            "/stripe2": {
                "method": "GET",
                "description": "Alternative Stripe endpoint with different payment link",
                "query_params": {
                    "auth": "Authentication token (WTFH4RSH or technopile)",
                    "cc": "Card details in format: number|mm|yy|cvv"
                },
                "payment_link": "28EaEX0ZR72t5CO2Icd3i1z",
                "rate_limits": {
                    "WTFH4RSH": "No rate limiting",
                    "technopile": "1 request per 5 seconds per IP"
                },
                "examples": [
                    "/stripe2?auth=WTFH4RSH&cc=4242424242424248|06|28|123",
                    "/stripe2?auth=technopile&cc=5555555555554444|12|28|456"
                ]
            },
            "/razorpay": {
                "method": "GET",
                "query_params": {
                    "auth": "Authentication token",
                    "cc": "Card details"
                }
            }
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
        port=int(os.environ.get("PORT", 2101))
    )


