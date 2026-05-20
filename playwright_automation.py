import random
import time
from typing import Optional
from playwright.sync_api import sync_playwright


def _random_delay(min_ms=200, max_ms=800):
    time.sleep(random.uniform(min_ms / 1000.0, max_ms / 1000.0))


def _emit_event(event_id: Optional[str], message: str, event_type: str = "info"):
    """Emit an event if event_id is provided"""
    if event_id:
        try:
            # Import here to avoid circular dependency
            from app import emit_event
            emit_event(event_id, "log", {"message": message, "type": event_type})
        except Exception:
            pass  # Silently fail if app not available


def _get_random_name() -> str:
    """Generate a random full name to avoid detection"""
    first_names = [
        "John", "Michael", "David", "Robert", "James", "William", "Richard", "Joseph",
        "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark",
        "Donald", "Kevin", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "George",
        "Edward", "Brian", "Ronald", "Mary", "Patricia", "Jennifer", "Linda", "Barbara",
        "Elizabeth", "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Betty", "Margaret",
        "Sandra", "Ashley", "Kimberly", "Emily", "Donna", "Michelle", "Dorothy", "Carol",
        "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia"
    ]
    
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Young",
        "Chavez", "Ruiz", "Torres", "Peterson", "Gray", "Steele", "Holland", "Winters",
        "Bennett", "Cooper", "Mitchell", "Grant", "Pierce", "Kennedy", "Sullivan", "Bishop"
    ]
    
    first = random.choice(first_names)
    last = random.choice(last_names)
    return f"{first} {last}"


def wait_for_and_click(checkout_frame, selector, label, timeout=15000, event_id=None):
    """Wait for element and click it inside the checkout frame"""
    try:
        locator = checkout_frame.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.click(timeout=timeout)
        _emit_event(event_id, f"✅ Clicked {label}", "success")
        return True
    except Exception as exc:
        _emit_event(event_id, f"⚠️ Could not click {label}: {str(exc)[:100]}", "warning")
        return False


def fill_card_field(checkout_frame, selector, value, label, timeout=10000, event_id=None):
    """Fill a card field inside the checkout frame"""
    try:
        locator = checkout_frame.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()
        
        # For card number, use type() to allow field formatting
        # For other fields, use fill()
        if 'card.number' in selector or 'card number' in label.lower():
            # Type character by character to trigger formatting
            locator.type(value, delay=50)
        else:
            locator.fill(value)
        
        display_value = value if 'name' not in label.lower() else '***'
        _emit_event(event_id, f"✓ {label} filled", "success")
        return True
    except Exception as exc:
        _emit_event(event_id, f"⚠️ Could not fill {label}: {str(exc)[:100]}", "warning")
        return False


def get_checkout_frame(page, timeout=20000, event_id=None):
    """Get the Razorpay checkout iframe with proper waiting"""
    try:
        page.wait_for_selector('iframe.razorpay-checkout-frame', timeout=timeout)
        _emit_event(event_id, "✅ Checkout iframe detected in DOM", "success")
    except Exception as exc:
        _emit_event(event_id, f"⚠️ Checkout iframe not found: {str(exc)[:80]}", "warning")
        return None

    return page.frame_locator('iframe.razorpay-checkout-frame')


def _parse_card_details(cc: str) -> tuple:
    """Parse card details from cc parameter.
    
    Accepts formats:
    - Card number only: "4111111111111111"
    - Full format: "4111111111111111:12/25:123" (card:expiry:cvv)
    
    Returns: (card_number, expiry, cvv)
    """
    parts = cc.split(':')
    
    card_number = parts[0].strip() if parts else ""
    
    # Parse expiry or use default
    expiry = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "12/28"
    
    # Parse CVV or use default
    cvv = parts[2].strip() if len(parts) > 2 and parts[2].strip() else "123"
    
    return card_number, expiry, cvv


def run_checkout(cc: str, target_url: str, headless: bool = True, attempts: int = 3, event_id: Optional[str] = None) -> dict:
    """Run the Razorpay checkout flow with retries and jitter to avoid rate limits.

    Returns: dict with keys: ok (bool), message (str) or error (str)
    """
    # Parse card details from cc parameter
    card_number, expiry, cvv = _parse_card_details(cc)
    
    _emit_event(event_id, "🚀 Starting payment checkout automation", "step")
    _emit_event(event_id, f"📍 Target URL: {target_url}", "info")
    _emit_event(event_id, f"💳 Card: {card_number[-4:].rjust(len(card_number), '*')}", "info")
    _emit_event(event_id, f"📅 Expiry: {expiry}", "info")
    
    for attempt in range(1, attempts + 1):
        try:
            _emit_event(event_id, f"Attempt {attempt}/{attempts}...", "info")
            
            with sync_playwright() as p:
                _emit_event(event_id, "🌐 Launching browser...", "step")

                browser = p.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--single-process",
                        "--no-zygote"
                    ]
                )

                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                )

                page = context.new_page()
                page.set_default_timeout(15000)

                # random short delay before navigation
                _random_delay(200, 700)
                _emit_event(event_id, "📄 Navigating to payment page...", "step")
                page.goto(target_url, wait_until="domcontentloaded")
                _emit_event(event_id, "✅ Page loaded", "success")
                _random_delay(300, 900)

                # best-effort: pre-fill merchant fields before clicking Pay
                invoice_number = str(random.randint(100000, 999999))
                _emit_event(event_id, "📝 Pre-filling form fields...", "step")
                try:
                    page.fill('input[type="number"], input[placeholder*="amount" i], input[name*="amount" i]', "80")
                    _emit_event(event_id, "✓ Amount field filled", "success")
                except Exception:
                    pass
                try:
                    page.fill('input[placeholder*="email" i], input[name*="email" i]', "testuser@gmail.com")
                    _emit_event(event_id, "✓ Email field filled", "success")
                except Exception:
                    pass
                try:
                    page.fill('input[aria-label*="Phone" i], input[type="tel"]', "916463344567")
                    _emit_event(event_id, "✓ Phone field filled", "success")
                except Exception:
                    pass
                try:
                    page.fill('input[placeholder*="invoice" i], input[name*="invoice" i]', invoice_number)
                    _emit_event(event_id, f"✓ Invoice field filled: {invoice_number}", "success")
                except Exception:
                    pass
                try:
                    page.fill('input[name="service_availed"], input[aria-label*="Service" i], input[placeholder*="service" i]', "Gardening")
                    _emit_event(event_id, "✓ Service field filled", "success")
                except Exception:
                    pass
                _random_delay(200, 700)

                # Click main Pay / Proceed
                time.sleep(2)
                _emit_event(event_id, "🔘 Clicking Pay button...", "step")
                pay_clicked = False
                
                # Try multiple selectors for the Pay button
                selectors = [
                    'button:has-text("Pay")',
                    'button[type="submit"]:has-text("Pay")',
                    'button.btn--gradient:has-text("Pay")',
                    'button.btn--gradient',
                    'button:has-text("Proceed")',
                    'button[type="submit"]',
                ]
                time.sleep(2)
                for selector in selectors:
                    try:
                        button = page.locator(selector).first
                        button.wait_for(state="visible", timeout=3000)
                        button.click(timeout=3000)
                        _emit_event(event_id, f"✅ Pay button clicked (selector: {selector})", "success")
                        pay_clicked = True
                        break
                    except Exception as e:
                        _emit_event(event_id, f"Selector '{selector}' failed: {str(e)[:60]}", "info")
                        continue
                
                if not pay_clicked:
                    browser.close()
                    _emit_event(event_id, f"❌ Failed to click pay button with any selector", "error")
                    return {"ok": False, "error": "Could not click pay button"}

                # capture responses for diagnostics
                responses = []
                def _on_response(r):
                    try:
                        txt = r.text()
                    except Exception:
                        txt = None
                    try:
                        res_type = r.request.resource_type
                    except Exception:
                        res_type = None
                    headers = r.headers
                    content_type = headers.get('content-type', '') if headers else ''
                    responses.append({
                        'url': r.url,
                        'status': r.status,
                        'resource_type': res_type,
                        'content_type': content_type,
                        'text': (txt or '')[:2000],
                    })
                page.on('response', _on_response)

                # Wait for and get checkout iframe
                _emit_event(event_id, "⏳ Waiting for checkout iframe...", "step")
                checkout_frame = get_checkout_frame(page, timeout=20000, event_id=event_id)
                if checkout_frame is None:
                    _emit_event(event_id, "⚠️ Checkout iframe not found. Card automation may not work.", "warning")
                    checkout_frame = page
                
                _random_delay(2000, 3000)

                # === SELECT CARDS & FILL CARD DETAILS (inside the checkout frame) ===
                _emit_event(event_id, "🎴 Selecting Cards payment method...", "step")
                cards_selected = (
                    wait_for_and_click(checkout_frame, 'span[data-testid="Cards"]', "Cards option", timeout=20000, event_id=event_id)
                    or wait_for_and_click(checkout_frame, 'span:has-text("Cards")', "Cards option", timeout=20000, event_id=event_id)
                    or wait_for_and_click(checkout_frame, 'text=Cards', "Cards option", timeout=20000, event_id=event_id)
                )
                if not cards_selected:
                    _emit_event(event_id, "⚠️ Could not auto-select Cards → attempting to proceed anyway", "warning")

                # Re-acquire the iframe in case the checkout widget reloaded
                if checkout_frame is not page:
                    checkout_frame = get_checkout_frame(page, timeout=20000, event_id=event_id)
                    if checkout_frame is None:
                        checkout_frame = page

                _random_delay(1000, 2000)

                # Fill Card Details
                _emit_event(event_id, "💳 Filling card details...", "step")
                card_ok = fill_card_field(checkout_frame, 'input[name="card.number"]', card_number, "Card number", timeout=10000, event_id=event_id)
                expiry_ok = fill_card_field(checkout_frame, 'input[name="card.expiry"]', expiry, "Card expiry", timeout=10000, event_id=event_id)
                cvv_ok = fill_card_field(checkout_frame, 'input[name="card.cvv"]', cvv, "Card CVV", timeout=10000, event_id=event_id)
                name_ok = fill_card_field(checkout_frame, 'input[name="card.name"]', _get_random_name(), "Cardholder name", timeout=10000, event_id=event_id)

                if card_ok and expiry_ok and cvv_ok and name_ok:
                    _emit_event(event_id, "✅ All card fields filled successfully", "success")
                else:
                    _emit_event(event_id, "⚠️ Some card fields could not be filled automatically", "warning")

                _random_delay(1000, 2000)

                # Click Continue
                _emit_event(event_id, "🚀 Clicking Continue...", "step")
                if not wait_for_and_click(checkout_frame, 'button:has-text("Continue")', "Continue button", timeout=20000, event_id=event_id):
                    _emit_event(event_id, "⚠️ Continue button not clicked", "warning")
                else:
                    _emit_event(event_id, "Continue clicked, checking for follow-up prompts...", "info")
                    _random_delay(1000, 2000)
                    
                    # Click Maybe later / pay without saving card
                    _emit_event(event_id, "📋 Checking for card save prompt...", "step")
                    maybe_later_clicked = (
                        wait_for_and_click(checkout_frame, 'button[name="pay_without_saving_card"]', "Pay without saving card", timeout=20000, event_id=event_id)
                        or wait_for_and_click(checkout_frame, 'button:has-text("Maybe later")', "Maybe later button", timeout=20000, event_id=event_id)
                    )

                    if maybe_later_clicked:
                        _emit_event(event_id, "✅ Card save prompt handled", "success")
                    else:
                        _emit_event(event_id, "ℹ️ No card save prompt detected", "info")

                # Wait for retry description and other visible messages
                _emit_event(event_id, "🔍 Scanning for payment result...", "step")
                retry_text = ""
                detected = None

                # re-acquire the checkout iframe after actions, in case it refreshed
                try:
                    page.wait_for_selector('iframe.razorpay-checkout-frame', timeout=15000)
                    checkout_frame = page.frame_locator('iframe.razorpay-checkout-frame')
                except Exception:
                    pass

                # 1) check for explicit retry-description inside the checkout iframe
                try:
                    retry_node = checkout_frame.locator('[data-testid="retry-description"]').first
                    retry_node.wait_for(state="visible", timeout=20000)
                    retry_text = retry_node.inner_text().strip()
                    detected = retry_text
                    _emit_event(event_id, f"📣 Detected response: {retry_text}", "info")
                except Exception:
                    pass

                # 2) fallback: check for direct visible keywords in the checkout iframe
                if not detected:
                    _emit_event(event_id, "Checking for payment keywords...", "info")
                    try:
                        keywords = [
                            'International cards are not supported',
                            'card declined',
                            'transaction declined',
                            'otp required',
                            'one time password',
                            '3d secure',
                            'authentication required',
                            'invalid card',
                            'insufficient funds',
                        ]
                        for kw in keywords:
                            try:
                                node = checkout_frame.locator(f'text=/{kw}/i')
                                if node.count() > 0:
                                    detected = node.first.inner_text().strip()
                                    _emit_event(event_id, f"🔑 Keyword match: {detected}", "success")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # 3) fallback: check page-level retry-description if not inside iframe
                if not detected:
                    try:
                        retry_node = page.locator('[data-testid="retry-description"]').first
                        if retry_node.count() > 0 and retry_node.is_visible():
                            detected = retry_node.inner_text().strip()
                            _emit_event(event_id, f"📄 Page-level response: {detected}", "info")
                    except Exception:
                        pass

                # allow the widget a bit more time to render final status text
                page.wait_for_timeout(2000)

                if detected:
                    _emit_event(event_id, f"✅ Payment response detected: {detected}", "success")
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    browser.close()
                    return {"ok": True, "status": status, "message": detected}

                # 4) get visible text from the checkout frame and scan for known keywords
                _emit_event(event_id, "📊 Analyzing page content...", "info")
                body_text = ""
                try:
                    frame = None
                    for f in page.frames:
                        if 'api.razorpay.com/v1/checkout/public' in (f.url or ''):
                            frame = f
                            break
                    if frame:
                        body_text = frame.evaluate('''() => {
                            const nodes = Array.from(document.querySelectorAll('body *'));
                            const visibleTexts = [];
                            for (const el of nodes) {
                                const style = window.getComputedStyle(el);
                                if (!el.innerText) continue;
                                if (style && (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0')) continue;
                                const tag = el.tagName.toLowerCase();
                                if (tag === 'script' || tag === 'style' || tag === 'noscript') continue;
                                const text = el.innerText.trim();
                                if (text) visibleTexts.push(text);
                            }
                            return visibleTexts.join('\n');
                        }
                        ''')
                    else:
                        body_text = ''

                    if not detected:
                        keywords = [
                            'International cards are not supported',
                            'card declined',
                            'transaction declined',
                            'otp required',
                            'one time password',
                            '3d secure',
                            'authentication required',
                            'invalid card',
                            'insufficient funds',
                        ]
                        for kw in keywords:
                            try:
                                if frame is not None:
                                    loc = frame.locator(f'text=/{kw}/i')
                                    if loc.count() > 0:
                                        detected = loc.first.inner_text().strip()
                                        _emit_event(event_id, f"🎯 Found: {detected}", "success")
                                        break
                            except Exception:
                                continue

                        if not detected:
                            lower = (body_text or "").lower()
                            for kw in keywords:
                                if kw.lower() in lower:
                                    detected = kw.upper()
                                    _emit_event(event_id, f"🎯 Found: {detected}", "success")
                                    break
                except Exception as e:
                    _emit_event(event_id, f"⚠️ Content analysis error: {str(e)[:80]}", "warning")
                    body_text = ""

                # 5) fallback: look for any visible alert/notice elements
                try:
                    alerts = checkout_frame.locator("[role=alert], .error, .alert, [data-testid*='error'], [data-testid*='retry']").all()
                    for a in alerts:
                        text = a.inner_text().strip()
                        if text:
                            detected = detected or text
                            _emit_event(event_id, f"⚠️ Alert detected: {text}", "warning")
                            break
                except Exception:
                    pass

                browser.close()
                if detected:
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    return {"ok": True, "status": status, "message": detected}

                # inspect captured responses for keywords in XHR/fetch or JSON/text responses only
                try:
                    keywords = [
                        'international cards are not supported',
                        'card declined',
                        'transaction declined',
                        'otp required',
                        'one time password',
                        '3d secure',
                        'authentication required',
                        'invalid card',
                        'insufficient funds',
                        'otp',
                    ]
                    for resp in reversed(responses[-50:]):
                        content_type = (resp.get('content_type') or '').lower()
                        res_type = (resp.get('resource_type') or '').lower()
                        if 'javascript' in content_type or resp.get('url', '').lower().endswith('.js'):
                            continue
                        if res_type not in ('xhr', 'fetch') and 'json' not in content_type and 'text/plain' not in content_type:
                            continue
                        txt = (resp.get('text') or '').lower()
                        if not txt:
                            continue
                        for kw in keywords:
                            if kw in txt:
                                detected = txt.strip()[:500]
                                _emit_event(event_id, f"📡 Response keyword match: {kw}", "info")
                                break
                        if detected:
                            break
                except Exception:
                    pass

                if detected:
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower or 'card declined' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    return {"ok": True, "status": status, "excerpt": detected[:800]}

                snippet = (body_text or "").strip()[:1000]
                diagnostics = {"frame_text_snippet": snippet}
                try:
                    if frame:
                        data_testid = frame.evaluate('''() => Array.from(document.querySelectorAll('[data-testid]')).slice(0,20).map(el=>({td: el.getAttribute('data-testid'), text: el.innerText.trim()}))''')
                        diagnostics['data_testid'] = data_testid
                except Exception:
                    pass

                # include recent captured responses for debugging
                try:
                    diagnostics['responses'] = responses[-10:]
                except Exception:
                    diagnostics['responses'] = []

                _emit_event(event_id, "✅ Automation step completed", "success")
                return {"ok": True, "detected": None, "message": "", "diagnostics": diagnostics}

        except Exception as exc:
            # exponential backoff with jitter to avoid repeating rapidly
            backoff = (2 ** (attempt - 1)) + random.random()
            _emit_event(event_id, f"❌ Attempt {attempt} failed: {str(exc)[:100]}", "error")
            if attempt < attempts:
                _emit_event(event_id, f"⏳ Retrying in {backoff:.1f}s...", "warning")
            time.sleep(backoff)
            last_err = str(exc)
            continue

    _emit_event(event_id, "❌ All automation attempts failed", "error")
    return {"ok": False, "error": f"all attempts failed: {last_err}"}
    """Run the Razorpay checkout flow with retries and jitter to avoid rate limits.

    Returns: dict with keys: ok (bool), message (str) or error (str)
    """
    _emit_event(event_id, "🚀 Starting payment checkout automation", "step")
    _emit_event(event_id, f"📍 Target URL: {target_url}", "info")
    _emit_event(event_id, f"💳 Card: {cc[-4:].rjust(len(cc), '*')}", "info")
    
    for attempt in range(1, attempts + 1):
        try:
            _emit_event(event_id, f"Attempt {attempt}/{attempts}...", "info")
            
            with sync_playwright() as p:
                _emit_event(event_id, "🌐 Launching browser...", "step")
                browser = p.chromium.launch(headless=headless, args=["--no-sandbox"])
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/116.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                )
                page = context.new_page()
                page.set_default_timeout(15000)

                # random short delay before navigation
                _random_delay(200, 700)
                _emit_event(event_id, "📄 Navigating to payment page...", "step")
                page.goto(target_url, wait_until="domcontentloaded")
                _emit_event(event_id, "✅ Page loaded", "success")
                _random_delay(300, 900)

                # best-effort: pre-fill merchant fields before clicking Pay
                invoice_number = str(random.randint(100000, 999999))
                _emit_event(event_id, "📝 Pre-filling form fields...", "step")
                try:
                    page.fill('input[type="number"], input[placeholder*="amount" i], input[name*="amount" i]', "700")
                    _emit_event(event_id, "✓ Amount field filled", "success")
                except Exception:
                    pass
                try:
                    page.fill('input[placeholder*="email" i], input[name*="email" i]', "testuser@gmail.com")
                    _emit_event(event_id, "✓ Email field filled", "success")
                except Exception:
                    pass
                try:
                    page.fill('input[aria-label*="Phone" i], input[type="tel"]', "916463344567")
                    _emit_event(event_id, "✓ Phone field filled", "success")
                except Exception:
                    pass
                try:
                    page.fill('input[placeholder*="invoice" i], input[name*="invoice" i]', invoice_number)
                    _emit_event(event_id, f"✓ Invoice field filled: {invoice_number}", "success")
                except Exception:
                    pass
                try:
                    page.fill('input[name="service_availed"], input[aria-label*="Service" i], input[placeholder*="service" i]', "Gardening")
                    _emit_event(event_id, "✓ Service field filled", "success")
                except Exception:
                    pass
                _random_delay(200, 700)

                # Click main Pay / Proceed
                _emit_event(event_id, "🔘 Clicking Pay button...", "step")
                try:
                    page.locator('button:has-text("Pay"), button:has-text("Proceed")').first.click()
                    _emit_event(event_id, "✅ Pay button clicked", "success")
                except Exception as exc:
                    browser.close()
                    _emit_event(event_id, f"❌ Failed to click pay button: {exc}", "error")
                    return {"ok": False, "error": f"click pay failed: {exc}"}

                # capture responses for diagnostics
                responses = []
                def _on_response(r):
                    try:
                        txt = r.text()
                    except Exception:
                        txt = None
                    try:
                        res_type = r.request.resource_type
                    except Exception:
                        res_type = None
                    headers = r.headers
                    content_type = headers.get('content-type', '') if headers else ''
                    responses.append({
                        'url': r.url,
                        'status': r.status,
                        'resource_type': res_type,
                        'content_type': content_type,
                        'text': (txt or '')[:2000],
                    })
                page.on('response', _on_response)

                # Wait for checkout iframe to appear with multiple strategies
                _emit_event(event_id, "⏳ Waiting for checkout iframe...", "step")
                checkout = None
                iframe_found = False
                
                try:
                    # Strategy 1: Wait for the iframe to be in DOM
                    page.wait_for_selector('iframe.razorpay-checkout-frame', timeout=15000)
                    _emit_event(event_id, "✅ Iframe detected in DOM", "success")
                    iframe_found = True
                except Exception as e:
                    _emit_event(event_id, f"⚠️ Primary iframe selector failed: {str(e)[:100]}", "warning")
                    
                    # Strategy 2: Try alternative iframe selectors
                    try:
                        page.wait_for_selector('iframe[src*="razorpay"]', timeout=10000)
                        _emit_event(event_id, "✅ Alternative iframe found", "success")
                        iframe_found = True
                    except Exception:
                        pass
                    
                    # Strategy 3: Just wait and list all iframes
                    _random_delay(500, 1500)
                    try:
                        iframes = page.locator('iframe').all()
                        _emit_event(event_id, f"📊 Found {len(iframes)} iframes on page", "info")
                        for i, iframe in enumerate(iframes):
                            try:
                                src = iframe.get_attribute('src')
                                cls = iframe.get_attribute('class')
                                _emit_event(event_id, f"  Iframe {i}: class={cls}, src={src}", "info")
                            except:
                                pass
                    except Exception:
                        pass

                # Try to get the checkout frame
                if iframe_found:
                    checkout = page.frame_locator('iframe.razorpay-checkout-frame')
                else:
                    # Try alternative frame locators
                    try:
                        checkout = page.frame_locator('iframe[src*="razorpay"]')
                        _emit_event(event_id, "📍 Using alternative frame locator", "info")
                    except:
                        try:
                            all_frames = page.frames
                            _emit_event(event_id, f"🔍 Scanning {len(all_frames)} frames...", "info")
                            for frame in all_frames:
                                try:
                                    # Try to find card inputs in each frame
                                    if frame.locator('input[name="card.number"]').count() > 0:
                                        _emit_event(event_id, f"✅ Found card form in frame", "success")
                                        checkout = frame
                                        break
                                except:
                                    pass
                        except:
                            pass

                if checkout:
                    _emit_event(event_id, "✅ Checkout frame ready", "success")
                else:
                    _emit_event(event_id, "⚠️ Could not locate checkout frame, attempting page-level fill", "warning")
                    checkout = page

                # small jitter then try selecting Cards
                _random_delay(200, 800)
                _emit_event(event_id, "🎴 Selecting Cards payment method...", "step")
                try:
                    checkout.locator('span:has-text("Cards")').click(timeout=3000)
                    _emit_event(event_id, "✅ Cards method selected", "success")
                except Exception as e:
                    _emit_event(event_id, f"⚠️ Could not select Cards method: {str(e)[:80]}", "warning")
                    # Try clicking button instead
                    try:
                        checkout.locator('button:has-text("Cards")').click(timeout=2000)
                        _emit_event(event_id, "✓ Cards selected via button", "success")
                    except:
                        pass

                # Wait a bit for any animation/transition
                _random_delay(500, 1000)

                # Fill inputs with better error handling and retry logic
                _emit_event(event_id, "💳 Filling card details...", "step")
                
                # Card Number
                try:
                    card_input = checkout.locator('input[name="card.number"]').first
                    card_input.wait_for(state="visible", timeout=5000)
                    card_input.fill(cc, timeout=5000)
                    _emit_event(event_id, f"✓ Card number filled: {cc[-4:].rjust(len(cc), '*')}", "success")
                except Exception as e:
                    _emit_event(event_id, f"⚠️ Card number fill failed: {str(e)[:100]}", "warning")
                    # Try alternative approach
                    try:
                        checkout.locator('input[name*="card"]').first.fill(cc, timeout=3000)
                        _emit_event(event_id, f"✓ Card filled via alternative selector", "success")
                    except:
                        pass

                # Expiry
                try:
                    expiry_input = checkout.locator('input[name="card.expiry"]').first
                    expiry_input.wait_for(state="visible", timeout=4000)
                    expiry_input.fill('12/28', timeout=4000)
                    _emit_event(event_id, "✓ Expiry filled: 12/28", "success")
                except Exception as e:
                    _emit_event(event_id, f"⚠️ Expiry fill failed: {str(e)[:100]}", "warning")

                # CVV
                try:
                    cvv_input = checkout.locator('input[name="card.cvv"]').first
                    cvv_input.wait_for(state="visible", timeout=3000)
                    cvv_input.fill('123', timeout=3000)
                    _emit_event(event_id, "✓ CVV filled", "success")
                except Exception as e:
                    _emit_event(event_id, f"⚠️ CVV fill failed: {str(e)[:100]}", "warning")

                # Name
                try:
                    name_input = checkout.locator('input[name="card.name"]').first
                    name_input.wait_for(state="visible", timeout=4000)
                    name_input.fill(_get_random_name(), timeout=4000)
                    _emit_event(event_id, "✓ Cardholder name filled", "success")
                except Exception as e:
                    _emit_event(event_id, f"⚠️ Name fill failed: {str(e)[:100]}", "warning")

                _random_delay(200, 700)
                _emit_event(event_id, "🚀 Clicking Continue...", "step")
                try:
                    checkout.locator('button:has-text("Continue")').click(timeout=5000)
                    _emit_event(event_id, "✅ Continue clicked", "success")
                except Exception:
                    _emit_event(event_id, "⚠️ Continue button not clicked", "warning")

                _random_delay(200, 700)
                # Click Maybe later / pay without saving card
                _emit_event(event_id, "📋 Checking for card save prompt...", "step")
                try:
                    checkout.locator('button[name="pay_without_saving_card"]').click(timeout=5000)
                    _emit_event(event_id, "✅ Card save skipped (pay_without_saving_card)", "success")
                except Exception:
                    try:
                        checkout.locator('button:has-text("Maybe later")').click(timeout=5000)
                        _emit_event(event_id, "✅ Card save skipped (Maybe later)", "success")
                    except Exception:
                        _emit_event(event_id, "ℹ️ No card save prompt detected", "info")

                # Wait for retry description and other visible messages
                _emit_event(event_id, "🔍 Scanning for payment result...", "step")
                retry_text = ""
                detected = None

                # re-acquire the checkout iframe after actions, in case it refreshed
                try:
                    page.wait_for_selector('iframe.razorpay-checkout-frame', timeout=15000)
                    checkout = page.frame_locator('iframe.razorpay-checkout-frame')
                except Exception:
                    pass

                # 1) check for explicit retry-description inside the checkout iframe
                try:
                    retry_node = checkout.locator('[data-testid="retry-description"]').first
                    retry_node.wait_for(state="visible", timeout=20000)
                    retry_text = retry_node.inner_text().strip()
                    detected = retry_text
                    _emit_event(event_id, f"📣 Detected response: {retry_text}", "info")
                except Exception:
                    pass

                # 2) fallback: check for direct visible keywords in the checkout iframe
                if not detected:
                    _emit_event(event_id, "Checking for payment keywords...", "info")
                    try:
                        keywords = [
                            'International cards are not supported',
                            'card declined',
                            'transaction declined',
                            'otp required',
                            'one time password',
                            '3d secure',
                            'authentication required',
                            'invalid card',
                            'insufficient funds',
                        ]
                        for kw in keywords:
                            try:
                                node = checkout.locator(f'text=/{kw}/i')
                                if node.count() > 0:
                                    detected = node.first.inner_text().strip()
                                    _emit_event(event_id, f"🔑 Keyword match: {detected}", "success")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # 3) fallback: check page-level retry-description if not inside iframe
                if not detected:
                    try:
                        retry_node = page.locator('[data-testid="retry-description"]').first
                        if retry_node.count() > 0 and retry_node.is_visible():
                            detected = retry_node.inner_text().strip()
                            _emit_event(event_id, f"📄 Page-level response: {detected}", "info")
                    except Exception:
                        pass

                # allow the widget a bit more time to render final status text
                page.wait_for_timeout(2000)

                if detected:
                    _emit_event(event_id, f"✅ Payment response detected: {detected}", "success")
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    browser.close()
                    return {"ok": True, "status": status, "message": detected}

                # 4) get visible text from the checkout frame and scan for known keywords
                _emit_event(event_id, "📊 Analyzing page content...", "info")
                body_text = ""
                try:
                    frame = None
                    for f in page.frames:
                        if 'api.razorpay.com/v1/checkout/public' in (f.url or ''):
                            frame = f
                            break
                    if frame:
                        body_text = frame.evaluate('''() => {
                            const nodes = Array.from(document.querySelectorAll('body *'));
                            const visibleTexts = [];
                            for (const el of nodes) {
                                const style = window.getComputedStyle(el);
                                if (!el.innerText) continue;
                                if (style && (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0')) continue;
                                const tag = el.tagName.toLowerCase();
                                if (tag === 'script' || tag === 'style' || tag === 'noscript') continue;
                                const text = el.innerText.trim();
                                if (text) visibleTexts.push(text);
                            }
                            return visibleTexts.join('\n');
                        }
                        ''')
                    else:
                        body_text = ''

                    if not detected:
                        keywords = [
                            'International cards are not supported',
                            'card declined',
                            'transaction declined',
                            'otp required',
                            'one time password',
                            '3d secure',
                            'authentication required',
                            'invalid card',
                            'insufficient funds',
                        ]
                        for kw in keywords:
                            try:
                                if frame is not None:
                                    loc = frame.locator(f'text=/{kw}/i')
                                    if loc.count() > 0:
                                        detected = loc.first.inner_text().strip()
                                        _emit_event(event_id, f"🎯 Found: {detected}", "success")
                                        break
                            except Exception:
                                continue

                        if not detected:
                            lower = (body_text or "").lower()
                            for kw in keywords:
                                if kw.lower() in lower:
                                    detected = kw.upper()
                                    _emit_event(event_id, f"🎯 Found: {detected}", "success")
                                    break
                except Exception as e:
                    _emit_event(event_id, f"⚠️ Content analysis error: {e}", "warning")
                    body_text = ""

                # 5) fallback: look for any visible alert/notice elements
                try:
                    alerts = checkout.locator("[role=alert], .error, .alert, [data-testid*='error'], [data-testid*='retry']").all()
                    for a in alerts:
                        text = a.inner_text().strip()
                        if text:
                            detected = detected or text
                            _emit_event(event_id, f"⚠️ Alert detected: {text}", "warning")
                            break
                except Exception:
                    pass

                browser.close()
                if detected:
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    return {"ok": True, "status": status, "message": detected}

                # inspect captured responses for keywords in XHR/fetch or JSON/text responses only
                try:
                    keywords = [
                        'international cards are not supported',
                        'card declined',
                        'transaction declined',
                        'otp required',
                        'one time password',
                        '3d secure',
                        'authentication required',
                        'invalid card',
                        'insufficient funds',
                        'otp',
                    ]
                    for resp in reversed(responses[-50:]):
                        content_type = (resp.get('content_type') or '').lower()
                        res_type = (resp.get('resource_type') or '').lower()
                        if 'javascript' in content_type or resp.get('url', '').lower().endswith('.js'):
                            continue
                        if res_type not in ('xhr', 'fetch') and 'json' not in content_type and 'text/plain' not in content_type:
                            continue
                        txt = (resp.get('text') or '').lower()
                        if not txt:
                            continue
                        for kw in keywords:
                            if kw in txt:
                                detected = txt.strip()[:500]
                                _emit_event(event_id, f"📡 Response keyword match: {kw}", "info")
                                break
                        if detected:
                            break
                except Exception:
                    pass

                if detected:
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower or 'card declined' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    return {"ok": True, "status": status, "excerpt": detected[:800]}

                snippet = (body_text or "").strip()[:1000]
                diagnostics = {"frame_text_snippet": snippet}
                try:
                    if frame:
                        data_testid = frame.evaluate('''() => Array.from(document.querySelectorAll('[data-testid]')).slice(0,20).map(el=>({td: el.getAttribute('data-testid'), text: el.innerText.trim()}))''')
                        diagnostics['data_testid'] = data_testid
                except Exception:
                    pass

                # include recent captured responses for debugging
                try:
                    diagnostics['responses'] = responses[-10:]
                except Exception:
                    diagnostics['responses'] = []

                _emit_event(event_id, "✅ Automation step completed", "success")
                return {"ok": True, "detected": None, "message": "", "diagnostics": diagnostics}

        except Exception as exc:
            # exponential backoff with jitter to avoid repeating rapidly
            backoff = (2 ** (attempt - 1)) + random.random()
            _emit_event(event_id, f"❌ Attempt {attempt} failed: {exc}", "error")
            if attempt < attempts:
                _emit_event(event_id, f"⏳ Retrying in {backoff:.1f}s...", "warning")
            time.sleep(backoff)
            last_err = str(exc)
            continue

    _emit_event(event_id, "❌ All automation attempts failed", "error")
    return {"ok": False, "error": f"all attempts failed: {last_err}"}
    """Run the Razorpay checkout flow with retries and jitter to avoid rate limits.

    Returns: dict with keys: ok (bool), message (str) or error (str)
    """
    for attempt in range(1, attempts + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless, args=["--no-sandbox"])
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/116.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                )
                page = context.new_page()
                page.set_default_timeout(15000)

                # random short delay before navigation
                _random_delay(200, 700)
                page.goto(target_url, wait_until="domcontentloaded")
                _random_delay(300, 900)

                # best-effort: pre-fill merchant fields before clicking Pay
                invoice_number = str(random.randint(100000, 999999))
                try:
                    page.fill('input[type="number"], input[placeholder*="amount" i], input[name*="amount" i]', "700")
                except Exception:
                    pass
                try:
                    page.fill('input[placeholder*="email" i], input[name*="email" i]', "testuser@gmail.com")
                except Exception:
                    pass
                try:
                    page.fill('input[aria-label*="Phone" i], input[type="tel"]', "916463344567")
                except Exception:
                    pass
                try:
                    page.fill('input[placeholder*="invoice" i], input[name*="invoice" i]', invoice_number)
                except Exception:
                    pass
                try:
                    page.fill('input[name="service_availed"], input[aria-label*="Service" i], input[placeholder*="service" i]', "Gardening")
                except Exception:
                    pass
                _random_delay(200, 700)

                # Click main Pay / Proceed
                try:
                    page.locator('button:has-text("Pay"), button:has-text("Proceed")').first.click()
                except Exception as exc:
                    browser.close()
                    return {"ok": False, "error": f"click pay failed: {exc}"}

                # capture responses for diagnostics
                responses = []
                def _on_response(r):
                    try:
                        txt = r.text()
                    except Exception:
                        txt = None
                    try:
                        res_type = r.request.resource_type
                    except Exception:
                        res_type = None
                    headers = r.headers
                    content_type = headers.get('content-type', '') if headers else ''
                    responses.append({
                        'url': r.url,
                        'status': r.status,
                        'resource_type': res_type,
                        'content_type': content_type,
                        'text': (txt or '')[:2000],
                    })
                page.on('response', _on_response)

                # Wait for checkout iframe to appear
                try:
                    page.wait_for_selector('iframe.razorpay-checkout-frame', timeout=10000)
                except Exception:
                    # iframe didn't appear yet — wait a bit more
                    _random_delay(500, 1500)

                # Use frame locator to interact inside checkout
                checkout = page.frame_locator('iframe.razorpay-checkout-frame')

                # small jitter then try selecting Cards
                _random_delay(200, 800)
                try:
                    checkout.locator('span:has-text("Cards")').click(timeout=3000)
                except Exception:
                    pass

                # Fill inputs (best-effort) — prefer direct fill to avoid keyboard emulation
                try:
                    checkout.locator('input[name="card.number"]').first.fill(card_number, timeout=5000)
                    checkout.locator('input[name="card.expiry"]').first.fill(expiry, timeout=4000)
                    checkout.locator('input[name="card.cvv"]').first.fill(cvv, timeout=3000)
                    checkout.locator('input[name="card.name"]').first.fill(_get_random_name(), timeout=4000)
                except Exception:
                    # continue even if fills fail — widget may behave differently
                    pass

                _random_delay(200, 700)
                try:
                    checkout.locator('button:has-text("Continue")').click(timeout=5000)
                except Exception:
                    pass

                _random_delay(200, 700)
                # Click Maybe later / pay without saving card
                try:
                    checkout.locator('button[name="pay_without_saving_card"]').click(timeout=5000)
                except Exception:
                    try:
                        checkout.locator('button:has-text("Maybe later")').click(timeout=5000)
                    except Exception:
                        pass

                # Wait for retry description and other visible messages
                retry_text = ""
                detected = None

                # re-acquire the checkout iframe after actions, in case it refreshed
                try:
                    page.wait_for_selector('iframe.razorpay-checkout-frame', timeout=15000)
                    checkout = page.frame_locator('iframe.razorpay-checkout-frame')
                except Exception:
                    pass

                # 1) check for explicit retry-description inside the checkout iframe
                try:
                    retry_node = checkout.locator('[data-testid="retry-description"]').first
                    retry_node.wait_for(state="visible", timeout=20000)
                    retry_text = retry_node.inner_text().strip()
                    detected = retry_text
                except Exception:
                    pass

                # 2) fallback: check for direct visible keywords in the checkout iframe
                if not detected:
                    try:
                        keywords = [
                            'International cards are not supported',
                            'card declined',
                            'transaction declined',
                            'otp required',
                            'one time password',
                            '3d secure',
                            'authentication required',
                            'invalid card',
                            'insufficient funds',
                        ]
                        for kw in keywords:
                            try:
                                node = checkout.locator(f'text=/{kw}/i')
                                if node.count() > 0:
                                    detected = node.first.inner_text().strip()
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # 3) fallback: check page-level retry-description if not inside iframe
                if not detected:
                    try:
                        retry_node = page.locator('[data-testid="retry-description"]').first
                        if retry_node.count() > 0 and retry_node.is_visible():
                            detected = retry_node.inner_text().strip()
                    except Exception:
                        pass

                # allow the widget a bit more time to render final status text
                page.wait_for_timeout(2000)

                if detected:
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    browser.close()
                    return {"ok": True, "status": status, "message": detected}

                # 4) get visible text from the checkout frame and scan for known keywords
                body_text = ""
                try:
                    frame = None
                    for f in page.frames:
                        if 'api.razorpay.com/v1/checkout/public' in (f.url or ''):
                            frame = f
                            break
                    if frame:
                        body_text = frame.evaluate('''() => {
                            const nodes = Array.from(document.querySelectorAll('body *'));
                            const visibleTexts = [];
                            for (const el of nodes) {
                                const style = window.getComputedStyle(el);
                                if (!el.innerText) continue;
                                if (style && (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0')) continue;
                                const tag = el.tagName.toLowerCase();
                                if (tag === 'script' || tag === 'style' || tag === 'noscript') continue;
                                const text = el.innerText.trim();
                                if (text) visibleTexts.push(text);
                            }
                            return visibleTexts.join('\n');
                        }
                        ''')
                    else:
                        body_text = ''

                    if not detected:
                        keywords = [
                            'International cards are not supported',
                            'card declined',
                            'transaction declined',
                            'otp required',
                            'one time password',
                            '3d secure',
                            'authentication required',
                            'invalid card',
                            'insufficient funds',
                        ]
                        for kw in keywords:
                            try:
                                if frame is not None:
                                    loc = frame.locator(f'text=/{kw}/i')
                                    if loc.count() > 0:
                                        detected = loc.first.inner_text().strip()
                                        break
                            except Exception:
                                continue

                        if not detected:
                            lower = (body_text or "").lower()
                            for kw in keywords:
                                if kw.lower() in lower:
                                    detected = kw.upper()
                                    break
                except Exception:
                    body_text = ""

                # 5) fallback: look for any visible alert/notice elements
                try:
                    alerts = checkout.locator("[role=alert], .error, .alert, [data-testid*='error'], [data-testid*='retry']").all()
                    for a in alerts:
                        text = a.inner_text().strip()
                        if text:
                            detected = detected or text
                            break
                except Exception:
                    pass

                browser.close()
                if detected:
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    return {"ok": True, "status": status, "message": detected}

                # inspect captured responses for keywords in XHR/fetch or JSON/text responses only
                try:
                    keywords = [
                        'international cards are not supported',
                        'card declined',
                        'transaction declined',
                        'otp required',
                        'one time password',
                        '3d secure',
                        'authentication required',
                        'invalid card',
                        'insufficient funds',
                        'otp',
                    ]
                    for resp in reversed(responses[-50:]):
                        content_type = (resp.get('content_type') or '').lower()
                        res_type = (resp.get('resource_type') or '').lower()
                        if 'javascript' in content_type or resp.get('url', '').lower().endswith('.js'):
                            continue
                        if res_type not in ('xhr', 'fetch') and 'json' not in content_type and 'text/plain' not in content_type:
                            continue
                        txt = (resp.get('text') or '').lower()
                        if not txt:
                            continue
                        for kw in keywords:
                            if kw in txt:
                                detected = txt.strip()[:500]
                                break
                        if detected:
                            break
                except Exception:
                    pass

                if detected:
                    det_lower = detected.lower()
                    if 'otp' in det_lower or 'one time' in det_lower:
                        status = 'OTP_REQUIRED'
                    elif 'international' in det_lower:
                        status = 'INTERNATIONAL_CARDS_NOT_ACCEPTED'
                    elif 'declin' in det_lower or 'card declined' in det_lower:
                        status = 'CARD_DECLINED'
                    elif 'insufficient fund' in det_lower:
                        status = 'INSUFFICIENT_FUNDS'
                    else:
                        status = 'MESSAGE'
                    return {"ok": True, "status": status, "excerpt": detected[:800]}

                snippet = (body_text or "").strip()[:1000]
                diagnostics = {"frame_text_snippet": snippet}
                try:
                    if frame:
                        data_testid = frame.evaluate('''() => Array.from(document.querySelectorAll('[data-testid]')).slice(0,20).map(el=>({td: el.getAttribute('data-testid'), text: el.innerText.trim()}))''')
                        diagnostics['data_testid'] = data_testid
                except Exception:
                    pass

                # include recent captured responses for debugging
                try:
                    diagnostics['responses'] = responses[-10:]
                except Exception:
                    diagnostics['responses'] = []

                return {"ok": True, "detected": None, "message": "", "diagnostics": diagnostics}

        except Exception as exc:
            # exponential backoff with jitter to avoid repeating rapidly
            backoff = (2 ** (attempt - 1)) + random.random()
            time.sleep(backoff)
            last_err = str(exc)
            continue

    return {"ok": False, "error": f"all attempts failed: {last_err}"}
