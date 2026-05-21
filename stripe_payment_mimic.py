"""
Script to mimic Stripe complete payment flow with final status.
Fetches dynamic pk_live key from payment link, with randomized user agents,
addresses, and customer names.
Shows: ACCEPTED, DECLINED, OTP REQUIRED, or CHARGED.
"""

import requests
import os
import json
import random
from typing import Dict, Any

# Payment link ID to fetch
PAYMENT_LINK_ID = "28E5kDbEv0E59T4beId3i1r"
PAYMENT_LINK_URL = "https://buy.stripe.com"

# List of random user agents
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
]

# List of random names
RANDOM_NAMES = [
    ("John", "Smith"),
    ("Sarah", "Johnson"),
    ("Michael", "Williams"),
    ("Emma", "Brown"),
    ("David", "Jones"),
    ("Lisa", "Garcia"),
    ("James", "Miller"),
    ("Anna", "Davis"),
    ("Robert", "Anderson"),
    ("Mary", "Taylor"),
]

# List of random addresses
RANDOM_ADDRESSES = [
    {
        "line1": "1620 Northwest 23rd Avenue",
        "city": "Portland",
        "state": "OR",
        "postal_code": "97210",
    },
    {
        "line1": "742 Evergreen Terrace",
        "city": "Springfield",
        "state": "IL",
        "postal_code": "62701",
    },
    {
        "line1": "124 Conch Street",
        "city": "Bikini Bottom",
        "state": "CA",
        "postal_code": "93510",
    },
    {
        "line1": "8 Beverly Hills",
        "city": "Los Angeles",
        "state": "CA",
        "postal_code": "90210",
    },
    {
        "line1": "10 Downing Street",
        "city": "London",
        "state": "NY",
        "postal_code": "10001",
    },
]

# Card numbers for testing (different outcomes)
CARD_NUMBERS = {
    "discover": "6011014839295628",
    "visa": "4242424242424242",
    "mastercard": "5555555555554444",
}


def get_random_values(card_number: str = None, exp_month: int = None, exp_year: int = None, cvc: str = None) -> Dict[str, Any]:
    """Generate random values for this transaction, with optional card overrides"""
    first_name, last_name = random.choice(RANDOM_NAMES)
    address = random.choice(RANDOM_ADDRESSES)
    
    # Use provided card data or randomize
    if card_number:
        # Detect card type from BIN
        if card_number.startswith('4'):
            card_type = 'visa'
        elif card_number.startswith(('51', '52', '53', '54', '55')) or (len(card_number) > 4 and card_number[:4] in ['2221', '2222', '2223', '2224', '2225', '2226', '2227', '2228', '2229', '2230', '2231', '2232', '2233', '2234', '2235', '2236', '2237', '2238', '2239', '2240', '2241', '2242', '2243', '2244', '2245', '2246', '2247', '2248', '2249', '2250', '2251', '2252', '2253', '2254', '2255', '2256', '2257', '2258', '2259', '2260', '2261', '2262', '2263', '2264', '2265', '2266', '2267', '2268', '2269', '2270', '2271', '2272', '2273', '2274', '2275', '2276', '2277', '2278', '2279', '2280', '2281', '2282', '2283', '2284', '2285', '2286', '2287', '2288', '2289', '2290', '2291', '2292', '2293', '2294', '2295', '2296', '2297', '2298', '2299', '2300', '2301', '2302', '2303', '2304', '2305', '2306', '2307', '2308', '2309', '2310', '2311', '2312', '2313', '2314', '2315', '2316', '2317', '2318', '2319', '2320', '2321', '2322', '2323', '2324', '2325', '2326', '2327', '2328', '2329', '2330', '2331', '2332', '2333', '2334', '2335', '2336', '2337', '2338', '2339', '2340', '2341', '2342', '2343', '2344', '2345', '2346', '2347', '2348', '2349', '2350', '2351', '2352', '2353', '2354', '2355', '2356', '2357', '2358', '2359', '2360', '2361', '2362', '2363', '2364', '2365', '2366', '2367', '2368', '2369', '2370', '2371', '2372', '2373', '2374', '2375', '2376', '2377', '2378', '2379', '2380', '2381', '2382', '2383', '2384', '2385', '2386', '2387', '2388', '2389', '2390', '2391', '2392', '2393', '2394', '2395', '2396', '2397', '2398', '2399', '2400', '2401', '2402', '2403', '2404', '2405', '2406', '2407', '2408', '2409', '2410', '2411', '2412', '2413', '2414', '2415', '2416', '2417', '2418', '2419', '2420', '2421', '2422', '2423', '2424', '2425', '2426', '2427', '2428', '2429', '2430', '2431', '2432', '2433', '2434', '2435', '2436', '2437', '2438', '2439', '2440', '2441', '2442', '2443', '2444', '2445', '2446', '2447', '2448', '2449', '2450', '2451', '2452', '2453', '2454', '2455', '2456', '2457', '2458', '2459', '2460', '2461', '2462', '2463', '2464', '2465', '2466', '2467', '2468', '2469', '2470', '2471', '2472', '2473', '2474', '2475', '2476', '2477', '2478', '2479', '2480', '2481', '2482', '2483', '2484', '2485', '2486', '2487', '2488', '2489', '2490', '2491', '2492', '2493', '2494', '2495', '2496', '2497', '2498', '2499', '2500', '2501', '2502', '2503', '2504', '2505', '2506', '2507', '2508', '2509', '2510', '2511', '2512', '2513', '2514', '2515', '2516', '2517', '2518', '2519', '2520', '2521', '2522', '2523', '2524', '2525', '2526', '2527', '2528', '2529', '2530', '2531', '2532', '2533', '2534', '2535', '2536', '2537', '2538', '2539', '2540', '2541', '2542', '2543', '2544', '2545', '2546', '2547', '2548', '2549', '2550', '2551', '2552', '2553', '2554', '2555', '2556', '2557', '2558', '2559', '2560', '2561', '2562', '2563', '2564', '2565', '2566', '2567', '2568', '2569', '2570', '2571', '2572', '2573', '2574', '2575', '2576', '2577', '2578', '2579', '2580', '2581', '2582', '2583', '2584', '2585', '2586', '2587', '2588', '2589', '2590', '2591', '2592', '2593', '2594', '2595', '2596', '2597', '2598', '2599', '2600', '2601', '2602', '2603', '2604', '2605', '2606', '2607', '2608', '2609', '2610', '2611', '2612', '2613', '2614', '2615', '2616', '2617', '2618', '2619', '2620', '2621', '2622', '2623', '2624', '2625', '2626', '2627', '2628', '2629', '2630', '2631', '2632', '2633', '2634', '2635', '2636', '2637', '2638', '2639', '2640', '2641', '2642', '2643', '2644', '2645', '2646', '2647', '2648', '2649', '2650', '2651', '2652', '2653', '2654', '2655', '2656', '2657', '2658', '2659', '2660', '2661', '2662', '2663', '2664', '2665', '2666', '2667', '2668', '2669', '2670', '2671', '2672', '2673', '2674', '2675', '2676', '2677', '2678', '2679', '2680', '2681', '2682', '2683', '2684', '2685', '2686', '2687', '2688', '2689', '2690', '2691', '2692', '2693', '2694', '2695', '2696', '2697', '2698', '2699', '2700', '2701', '2702', '2703', '2704', '2705', '2706', '2707', '2708', '2709', '2710', '2711', '2712', '2713', '2714', '2715', '2716', '2717', '2718', '2719', '2720']):
            card_type = 'mastercard'
        elif card_number.startswith(('34', '37')):
            card_type = 'amex'
        elif card_number.startswith('6011') or card_number.startswith(('644', '645', '646', '647', '648', '649', '65')):
            card_type = 'discover'
        elif card_number.startswith(('36', '38', '300', '301', '302', '303', '304', '305')):
            card_type = 'diners'
        elif card_number.startswith('35'):
            card_type = 'jcb'
        else:
            card_type = 'unknown'
    else:
        card_type, card_number = random.choice(list(CARD_NUMBERS.items()))
    
    user_agent = random.choice(USER_AGENTS)
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
        "address": address,
        "card_type": card_type,
        "card_number": card_number,
        "exp_month": exp_month or 6,
        "exp_year": exp_year or 28,
        "cvc": cvc or "000",
        "user_agent": user_agent,
    }


def step_0_fetch_payment_link() -> Dict[str, Any]:
    """
    Step 0: Fetch payment link details to get dynamic pk_live key and custom fields
    
    Returns:
        dict: Payment link details including the pk_live key and custom fields
    """
    merchant_url = f"https://merchant-ui-api.stripe.com/payment-links/{PAYMENT_LINK_ID}"
    
    headers = {
        "Accept": "application/json",
        "Sec-Ch-Ua-Platform": "Linux",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Not-A.Brand";v="24", "Chromium";v="146"',
        "Content-Type": "application/x-www-form-urlencoded",
        "Sec-Ch-Ua-Mobile": "?0",
        "User-Agent": random.choice(USER_AGENTS),
        "Origin": PAYMENT_LINK_URL,
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": f"{PAYMENT_LINK_URL}/",
        "Accept-Encoding": "gzip, deflate, br",
        "Priority": "u=1, i",
        "Connection": "keep-alive",
    }
    
    print("\n" + "=" * 80)
    print("STEP 0: FETCH PAYMENT LINK (Get Dynamic pk_live Key and Custom Fields)")
    print("=" * 80)
    print(f"Endpoint: GET /payment-links/{PAYMENT_LINK_ID}")
    print(f"Host: merchant-ui-api.stripe.com")
    
    try:
        response = requests.get(
            merchant_url,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            link_details = response.json()
            pk_live_key = link_details.get('pk_live') or link_details.get('public_key')
            print(f"\n✓ Payment Link Fetched")
            print(f"  Link ID: {PAYMENT_LINK_ID}")
            if pk_live_key:
                print(f"  Public Key: {pk_live_key[:20]}...{pk_live_key[-10:]}")
            
            # Debug: Print response structure
            print(f"\n  Response keys: {list(link_details.keys())}")
            
            # Try different paths to find custom fields
            custom_fields = None
            
            # Try direct path
            if 'custom_fields' in link_details:
                custom_fields = link_details.get('custom_fields', [])
                print(f"  Found custom_fields at top level")
            
            # Try nested under 'attributes'
            elif 'attributes' in link_details:
                custom_fields = link_details['attributes'].get('custom_fields', [])
                print(f"  Found custom_fields under attributes")
            
            # Try nested under 'payment_settings'
            elif 'payment_settings' in link_details:
                custom_fields = link_details['payment_settings'].get('custom_fields', [])
                print(f"  Found custom_fields under payment_settings")
            
            # Try nested under 'checkout'
            elif 'checkout' in link_details:
                custom_fields = link_details['checkout'].get('custom_fields', [])
                print(f"  Found custom_fields under checkout")
            
            # Try nested under 'form'
            elif 'form' in link_details:
                custom_fields = link_details['form'].get('custom_fields', [])
                print(f"  Found custom_fields under form")
            
            # If still not found, try to find any dict with custom_fields
            if not custom_fields:
                print(f"  Searching for custom_fields in nested objects...")
                for key, value in link_details.items():
                    if isinstance(value, dict) and 'custom_fields' in value:
                        custom_fields = value.get('custom_fields', [])
                        print(f"  Found custom_fields under '{key}'")
                        break
            
            if custom_fields:
                print(f"  Custom Fields: {len(custom_fields)} found")
                for field in custom_fields:
                    field_id = field.get('id', 'unknown')
                    field_type = field.get('type', 'unknown')
                    is_required = field.get('required', False)
                    print(f"    - {field_id}: type={field_type}, required={is_required}")
                    # Print dropdown options if available
                    if field_type == 'dropdown':
                        dropdown_config = field.get('dropdown', {})
                        if isinstance(dropdown_config, dict):
                            options = dropdown_config.get('options', [])
                        elif isinstance(dropdown_config, list):
                            options = dropdown_config
                        else:
                            options = []
                        if options:
                            print(f"      Options: {options}")
            else:
                print(f"  Custom Fields: None found (searched all nested paths)")
            
            return link_details
        else:
            print(f"\n✗ Failed: {response.status_code}")
            print(response.text[:500])
            return {}
    
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Error: {str(e)}")
        print("Note: Using fallback approach...")
        return {}


def fetch_payment_page_amount(user_agent: str, session_id: str = None) -> Dict[str, Any]:

    import re
    import requests

    # Use the session ID if provided to fetch the actual checkout page
    if session_id:
        page_url = f"https://buy.stripe.com/c/pay/{session_id}"
        print(f"Using session-specific checkout page")
    else:
        page_url = f"https://buy.stripe.com/{PAYMENT_LINK_ID}"
        print(f"Using static payment link")

    headers = {
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": user_agent,
    }

    print("\n" + "=" * 80)
    print("FETCH PAYMENT PAGE AMOUNT")
    print("=" * 80)

    try:

        response = requests.get(
            page_url,
            headers=headers,
            timeout=30
        )

        print(f"Status: {response.status_code}")

        if response.status_code != 200:
            return {}

        html = response.text

        # =========================================================
        # MAIN STRIPE AMOUNT REGEX
        # =========================================================

        pattern = r'CurrencyAmount[^>]*>\s*\$([\d,]+(?:\.\d+)?)\s*<'

        match = re.search(pattern, html, re.IGNORECASE)

        if match:

            amount_text = match.group(1)

            amount_float = float(
                amount_text.replace(",", "")
            )

            amount_cents = int(amount_float * 100)

            print(f"\n✓ Amount Found")
            print(f"Displayed: ${amount_float:.2f}")
            print(f"Cents: {amount_cents}")

            return {
                "amount": str(amount_cents),
                "currency": "usd",
                "formatted": f"${amount_float:.2f}"
            }

        print("\n⚠️ Amount span not found")

        # DEBUG
        currency_index = html.find("CurrencyAmount")

        if currency_index != -1:

            print("\nNearby HTML:")

            print(
                html[
                    max(0, currency_index - 200):
                    currency_index + 300
                ]
            )

        return {}

    except Exception as e:

        print(f"\n✗ Error: {e}")

        return {}


def step_0b_create_payment_session(user_agent: str) -> Dict[str, Any]:
    """
    Step 0b: Create a payment session to get dynamic cs_live session ID
    
    Args:
        user_agent: The user agent to use
    
    Returns:
        dict: Payment session details including cs_live session_id and custom fields
    """
    session_url = f"https://merchant-ui-api.stripe.com/payment-links/{PAYMENT_LINK_ID}"
    
    headers = {
        "Accept": "application/json",
        "Sec-Ch-Ua-Platform": "Linux",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Not-A.Brand";v="24", "Chromium";v="146"',
        "Content-Type": "application/x-www-form-urlencoded",
        "Sec-Ch-Ua-Mobile": "?0",
        "User-Agent": user_agent,
        "Origin": "https://buy.stripe.com",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": f"{PAYMENT_LINK_URL}/",
        "Accept-Encoding": "gzip, deflate, br",
        "Priority": "u=1, i",
        "Connection": "keep-alive",
    }
    
    # Browser locale and timezone data
    payload = {
        "eid": "NA",
        "browser_locale": "en-US",
        "browser_timezone": "Asia/Calcutta",
    }
    
    print("\n" + "=" * 80)
    print("STEP 0b: CREATE PAYMENT SESSION (Get Dynamic cs_live)")
    print("=" * 80)
    print(f"Endpoint: POST /payment-links/{PAYMENT_LINK_ID}")
    print(f"Host: merchant-ui-api.stripe.com")
    
    try:
        response = requests.post(
            session_url,
            data=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data.get('session_id')
            print(f"\n✓ Payment Session Created")
            if session_id:
                print(f"  Session ID: {session_id[:20]}...{session_id[-10:]}")
            
            # Try to extract amount from session response
            print(f"\n  Checking for amount in session response...")
            amount = None
            
            # Priority 1: line_item_group.due or .total (main amount to charge)
            if 'line_item_group' in session_data:
                line_item_group = session_data['line_item_group']
                amount = line_item_group.get('due') or line_item_group.get('total')
                if amount:
                    print(f"  ✓ Found amount in line_item_group: {amount} ({session_data.get('currency', 'unknown')})")
                    session_data['_extracted_amount'] = str(amount)
            
            # Priority 2: adaptive_pricing_info.local_currency_options[0].amount
            if not amount and 'adaptive_pricing_info' in session_data:
                adaptive_pricing = session_data['adaptive_pricing_info']
                if 'local_currency_options' in adaptive_pricing:
                    options = adaptive_pricing['local_currency_options']
                    if options and len(options) > 0:
                        amount = options[0].get('amount')
                        if amount:
                            print(f"  ✓ Found amount in adaptive_pricing_info: {amount}")
                            session_data['_extracted_amount'] = str(amount)
            
            # Priority 3: adaptive_pricing_info.integration_amount
            if not amount and 'adaptive_pricing_info' in session_data:
                amount = session_data['adaptive_pricing_info'].get('integration_amount')
                if amount:
                    print(f"  ✓ Found integration_amount: {amount}")
                    session_data['_extracted_amount'] = str(amount)
            
            if not amount:
                print(f"  ⚠️  No amount found in session response")
            
            # Try to extract custom fields from session response
            print(f"\n  Checking for custom fields in session response...")
            custom_fields = None
            
            # Try direct path
            if 'custom_fields' in session_data:
                custom_fields = session_data.get('custom_fields', [])
                print(f"  Found custom_fields at top level of session")
            
            # Try nested paths
            if not custom_fields:
                for key in ['attributes', 'payment_settings', 'checkout', 'form', 'settings']:
                    if key in session_data:
                        custom_fields = session_data[key].get('custom_fields', [])
                        if custom_fields:
                            print(f"  Found custom_fields under session.{key}")
                            break
            
            # Print what we found
            if custom_fields:
                print(f"  Custom Fields: {len(custom_fields)} found in session")
                for field in custom_fields:
                    field_id = field.get('id', 'unknown')
                    field_type = field.get('type', 'unknown')
                    print(f"    - {field_id}: type={field_type}")
                # Store in session_data for later retrieval
                session_data['_extracted_custom_fields'] = custom_fields
            else:
                print(f"  No custom fields found in session response")
            
            return session_data
        else:
            print(f"\n✗ Failed: {response.status_code}")
            error = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            print(json.dumps(error, indent=2) if isinstance(error, dict) else str(error)[:300])
            return {}
    
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Error: {str(e)}")
        return {}


# Card and billing details (will be randomized per transaction)
CARD_DETAILS = {
    "type": "card",
    "card[number]": "PLACEHOLDER_CARD_NUMBER",
    "card[cvc]": "000",
    "card[exp_month]": "06",
    "card[exp_year]": "28",
}

BILLING_DETAILS = {
    "billing_details[name]": "PLACEHOLDER_NAME",
    "billing_details[email]": "PLACEHOLDER_EMAIL",
    "billing_details[address][country]": "US",
    "billing_details[address][line1]": "PLACEHOLDER_LINE1",
    "billing_details[address][city]": "PLACEHOLDER_CITY",
    "billing_details[address][postal_code]": "PLACEHOLDER_ZIP",
    "billing_details[address][state]": "PLACEHOLDER_STATE",
}

# Client metadata (will be updated with random values)
CLIENT_METADATA = {
    "guid": "88c1c867-ae8a-4a53-9a7c-44fdd2ce53148e57e5",
    "muid": "351f7b94-8963-4fe1-b91f-3b8f66aeb7d81038d7",
    "sid": "28305964-937b-403a-91b2-db9774b67a35b541fa",
    "key": "PLACEHOLDER_PK_LIVE",
    "payment_user_agent": "stripe.js/eabaf71cdc; stripe-js-v3/eabaf71cdc; payment-link; checkout",
}

CHECKOUT_ATTRIBUTION = {
    "client_attribution_metadata[client_session_id]": "72515a73-96f4-4938-917e-b3fae8b095e4",
    "client_attribution_metadata[checkout_session_id]": "cs_live_a1wWPIqsFTDoNwKqbxHQ8gA0ieI6wlFSUC5v9RyWDHSIFceywPZnlFAcBg",
    "client_attribution_metadata[merchant_integration_source]": "checkout",
    "client_attribution_metadata[merchant_integration_version]": "payment_link",
    "client_attribution_metadata[payment_method_selection_flow]": "automatic",
    "client_attribution_metadata[checkout_config_id]": "9bf50b1b-4c6c-4905-ae01-0fad3cda214d",
}


def build_request_payload(random_values: Dict[str, Any], pk_live_key: str) -> Dict[str, str]:
    """Build the complete payload for the Stripe API request with random values"""
    address = random_values['address']
    
    payload = {
        "type": "card",
        "card[number]": random_values['card_number'],
        "card[cvc]": str(random_values.get('cvc', '000')),
        "card[exp_month]": str(random_values.get('exp_month', 6)).zfill(2),
        "card[exp_year]": str(random_values.get('exp_year', 28)).zfill(2),
        "billing_details[name]": random_values['full_name'],
        "billing_details[email]": random_values['email'],
        "billing_details[address][country]": "US",
        "billing_details[address][line1]": address['line1'],
        "billing_details[address][city]": address['city'],
        "billing_details[address][postal_code]": address['postal_code'],
        "billing_details[address][state]": address['state'],
        "guid": "88c1c867-ae8a-4a53-9a7c-44fdd2ce53148e57e5",
        "muid": "351f7b94-8963-4fe1-b91f-3b8f66aeb7d81038d7",
        "sid": "28305964-937b-403a-91b2-db9774b67a35b541fa",
        "key": pk_live_key,
        "payment_user_agent": "stripe.js/eabaf71cdc; stripe-js-v3/eabaf71cdc; payment-link; checkout",
        "client_attribution_metadata[client_session_id]": "72515a73-96f4-4938-917e-b3fae8b095e4",
        "client_attribution_metadata[checkout_session_id]": "cs_live_a1wWPIqsFTDoNwKqbxHQ8gA0ieI6wlFSUC5v9RyWDHSIFceywPZnlFAcBg",
        "client_attribution_metadata[merchant_integration_source]": "checkout",
        "client_attribution_metadata[merchant_integration_version]": "payment_link",
        "client_attribution_metadata[payment_method_selection_flow]": "automatic",
        "client_attribution_metadata[checkout_config_id]": "9bf50b1b-4c6c-4905-ae01-0fad3cda214d",
    }
    
    return payload


def build_headers(user_agent: str) -> Dict[str, str]:
    """Build headers matching the original request with random user agent"""
    return {
        "Sec-Ch-Ua-Platform": "Linux",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json",
        "Sec-Ch-Ua": '"Not-A.Brand";v="24", "Chromium";v="146"',
        "Content-Type": "application/x-www-form-urlencoded",
        "Sec-Ch-Ua-Mobile": "?0",
        "User-Agent": user_agent,
        "Origin": PAYMENT_LINK_URL,
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": f"{PAYMENT_LINK_URL}/",
        "Accept-Encoding": "gzip, deflate, br",
        "Priority": "u=1, i",
    }


def step_1_create_payment_method(random_values: Dict[str, Any], pk_live_key: str) -> Dict[str, Any]:
    """
    Step 1: Create a payment method (tokenize the card)
    
    Args:
        random_values: Dictionary with randomized customer data
        pk_live_key: The dynamic public key from payment link
    
    Returns:
        dict: The payment method object with ID
    """
    payment_method_url = "https://api.stripe.com/v1/payment_methods"
    payload = build_request_payload(random_values, pk_live_key)
    headers = build_headers(random_values['user_agent'])
    
    print("\n" + "=" * 80)
    print("STEP 1: CREATE PAYMENT METHOD (Card Tokenization)")
    print("=" * 80)
    print(f"Endpoint: POST /v1/payment_methods")
    print(f"Card: {random_values['card_type'].title()} ****{random_values['card_number'][-4:]}")
    print(f"Name: {random_values['full_name']}")
    print(f"Email: {random_values['email']}")
    print(f"Address: {random_values['address']['line1']}, {random_values['address']['city']}, {random_values['address']['state']}")
    
    try:
        response = requests.post(
            payment_method_url,
            data=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            payment_method = response.json()
            pm_id = payment_method.get('id')
            print(f"\n✓ Payment Method Created: {pm_id}")
            return payment_method
        else:
            print(f"\n✗ Failed: {response.status_code}")
            print(response.text[:300])
            return {}
    
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Error: {str(e)}")
        return {}


def step_2_confirm_payment_page(
    payment_method_id: str,
    random_values: Dict[str, Any],
    pk_live_key: str,
    session_id: str,
    custom_fields_list: list = None,
    amount: str = "130313"
) -> Dict[str, Any]:

    confirm_url = f"https://api.stripe.com/v1/payment_pages/{session_id}/confirm"

    address = random_values['address']

    payload = {
        "eid": "NA",

        "payment_method": payment_method_id,

        "expected_amount": amount,

        "last_displayed_line_item_group_details[subtotal]": amount,
        "last_displayed_line_item_group_details[total_exclusive_tax]": "0",
        "last_displayed_line_item_group_details[total_inclusive_tax]": "0",
        "last_displayed_line_item_group_details[total_discount_amount]": "0",
        "last_displayed_line_item_group_details[shipping_rate_amount]": "0",

        "shipping[address][line1]": address['line1'],
        "shipping[address][city]": address['city'],
        "shipping[address][country]": "US",
        "shipping[address][postal_code]": address['postal_code'],
        "shipping[address][state]": address['state'],

        "shipping[name]": random_values['full_name'],

        "name_collection[individual_name]": random_values['first_name'],
        "name_collection[source]": "payment_form",

        "expected_payment_method_type": "card",

        "guid": "88c1c867-ae8a-4a53-9a7c-44fdd2ce53148e57e5",
        "muid": "351f7b94-8963-4fe1-b91f-3b8f66aeb7d81038d7",

        "sid": "".join(random.choices("0123456789abcdef", k=32)),

        "key": pk_live_key or "PLACEHOLDER_PK",

        "version": "eabaf71cdc",

        "client_attribution_metadata[client_session_id]":
            "".join(random.choices("abcdef0123456789", k=32)),

        "client_attribution_metadata[checkout_session_id]": session_id,

        "client_attribution_metadata[merchant_integration_source]": "checkout",

        "client_attribution_metadata[merchant_integration_version]": "payment_link",

        "client_attribution_metadata[payment_method_selection_flow]": "automatic",

        "client_attribution_metadata[checkout_config_id]":
            "a5352a94-8cf1-45ed-844a-8c645d7b5ac0",

        "link_brand": "link",
    }

    # ============================================================
    # DYNAMIC CUSTOM FIELDS
    # ============================================================

    if custom_fields_list:

        print("\nCUSTOM FIELDS FOUND:")
        print(f"Total fields: {len(custom_fields_list)}")

        for idx, field in enumerate(custom_fields_list):

            field_id = field.get("id")
            field_type = field.get("type")
            is_required = field.get("required", False)

            if not field_id:
                print(f"  [{idx}] Skipping field without ID")
                continue

            print(f"  [{idx}] Field ID: {field_id}")
            print(f"       Type: {field_type}")
            print(f"       Required: {is_required}")

            payload[f"custom_fields[{idx}][custom_field_id]"] = field_id

            # ====================================================
            # DROPDOWN
            # ====================================================

            if field_type == "dropdown":

                # Get options - might be under 'dropdown' key or directly
                dropdown_config = field.get("dropdown", {})
                
                if isinstance(dropdown_config, dict):
                    options = dropdown_config.get("options", [])
                elif isinstance(dropdown_config, list):
                    options = dropdown_config
                else:
                    options = []

                print(f"       Options count: {len(options)}")

                selected_value = None

                # Try to find default option
                for option in options:
                    if isinstance(option, dict):
                        if option.get("default"):
                            selected_value = option.get("value")
                            print(f"       Selected (default): {selected_value}")
                            break
                    else:
                        # Option might be a string directly
                        print(f"       Option format: {option}")

                # Fallback to first option
                if not selected_value and options:
                    if isinstance(options[0], dict):
                        selected_value = options[0].get("value")
                    else:
                        selected_value = str(options[0])
                    if selected_value:
                        print(f"       Selected (first): {selected_value}")

                # Final fallback
                if not selected_value:
                    selected_value = "a"
                    print(f"       Selected (fallback): {selected_value}")

                payload[f"custom_fields[{idx}][dropdown]"] = selected_value

            # ====================================================
            # TEXT
            # ====================================================

            elif field_type == "text":

                text_value = random_values['full_name']
                payload[f"custom_fields[{idx}][text]"] = text_value
                print(f"       Value: {text_value}")

            # ====================================================
            # NUMERIC
            # ====================================================

            elif field_type == "numeric":

                payload[f"custom_fields[{idx}][numeric]"] = "1"
                print(f"       Value: 1")

            # ====================================================
            # UNKNOWN TYPE
            # ====================================================

            else:

                payload[f"custom_fields[{idx}][text]"] = "default"
                print(f"       Type unknown, using text default")

    headers = build_headers(random_values['user_agent'])

    print("\n" + "=" * 80)
    print("STEP 2: CONFIRM PAYMENT PAGE")
    print("=" * 80)

    print(f"Endpoint: POST /v1/payment_pages/{session_id}/confirm")
    print(f"Payment Method: {payment_method_id}")

    try:

        response = requests.post(
            confirm_url,
            data=payload,
            headers=headers,
            timeout=30
        )

        print(f"\nResponse Status: {response.status_code}")

        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2)[:5000])
        except:
            print(response.text[:5000])

        # ========================================================
        # SUCCESS
        # ========================================================

        if response.status_code == 200:

            return response.json()

        # ========================================================
        # CARD DECLINED / OTP
        # ========================================================

        elif response.status_code == 402:

            error_data = response.json()
            error = error_data.get("error", {})

            return {
                "payment_intent": {
                    "id": error.get("charge", ""),
                    "status": (
                        "requires_payment_method"
                        if error.get("code") == "card_declined"
                        else "requires_action"
                    ),
                    "client_secret": "",
                    "last_payment_error": error
                }
            }

        # ========================================================
        # OTHER ERRORS
        # ========================================================

        else:

            return {
                "error": True,
                "status_code": response.status_code,
                "response": (
                    response.json()
                    if "application/json"
                    in response.headers.get("content-type", "")
                    else response.text
                )
            }

    except requests.exceptions.RequestException as e:

        return {
            "error": True,
            "message": str(e)
        }


def step_3_check_payment_intent(intent_id: str, client_secret: str, user_agent: str, pk_live_key: str, payment_error: Dict[str, Any] = None, amount: str = "130313") -> Dict[str, Any]:
    """
    Step 3: Check the final payment intent status
    
    Args:
        intent_id: The payment intent ID
        client_secret: The client secret for the intent
        user_agent: The user agent to use
        pk_live_key: The dynamic public key
        payment_error: Optional error dict if payment was declined
        amount: The payment amount in cents
    
    Returns:
        dict: The final payment intent with status
    """
    # If we have a payment error (402 response), return it as the final status
    if payment_error:
        print("\n" + "=" * 80)
        print("STEP 3: PAYMENT STATUS (From Confirmation)")
        print("=" * 80)
        print(f"Status: {payment_error.get('code', 'unknown')}")
        return {
            "id": intent_id,
            "status": "requires_payment_method" if payment_error.get('code') == 'card_declined' else "requires_action",
            "last_payment_error": payment_error,
            "amount": int(amount),
            "currency": "usd"
        }
    
    intent_url = f"https://api.stripe.com/v1/payment_intents/{intent_id}"
    
    headers = build_headers(user_agent)
    headers['Origin'] = "https://js.stripe.com"
    headers['Referer'] = "https://js.stripe.com/"
    
    params = {
        "is_stripe_sdk": "false",
        "client_secret": client_secret,
        "key": pk_live_key
    }
    
    print("\n" + "=" * 80)
    print("STEP 3: CHECK FINAL PAYMENT STATUS")
    print("=" * 80)
    print(f"Endpoint: GET /v1/payment_intents/{intent_id}")
    
    try:
        response = requests.get(
            intent_url,
            params=params,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            intent = response.json()
            return intent
        else:
            print(f"\n✗ Failed: {response.status_code}")
            return {}
    
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Error: {str(e)}")
        return {}


def print_final_status(intent: Dict[str, Any]):
    """
    Print the final payment status with user-friendly messages
    
    Args:
        intent: The payment intent object
    """
    status = intent.get('status', 'unknown')
    error = intent.get('last_payment_error', {})
    
    print("\n" + "=" * 80)
    print("FINAL PAYMENT STATUS")
    print("=" * 80)
    
    status_map = {
        'succeeded': {
            'emoji': '✓',
            'message': 'PAYMENT CHARGED',
            'description': 'Payment was successfully charged'
        },
        'processing': {
            'emoji': '⏳',
            'message': 'PAYMENT PROCESSING',
            'description': 'Payment is being processed'
        },
        'requires_payment_method': {
            'emoji': '✗',
            'message': 'PAYMENT DECLINED',
            'description': 'Card was declined or authentication failed'
        },
        'requires_action': {
            'emoji': '⚠️',
            'message': 'OTP/3D SECURE REQUIRED',
            'description': 'Customer action needed for 3D Secure authentication'
        },
        'requires_capture': {
            'emoji': '⏳',
            'message': 'PAYMENT AUTHORIZED',
            'description': 'Payment authorized, requires capture'
        },
        'canceled': {
            'emoji': '✗',
            'message': 'PAYMENT CANCELED',
            'description': 'Payment was canceled'
        },
    }
    
    status_info = status_map.get(status, {
        'emoji': '?',
        'message': 'UNKNOWN STATUS',
        'description': f'Status: {status}'
    })
    
    print(f"\n{status_info['emoji']} {status_info['message']}")
    print(f"   {status_info['description']}")
    
    # Print additional details based on status
    if error and 'code' in error:
        print(f"\nError Details:")
        print(f"  Code: {error.get('code')}")
        print(f"  Message: {error.get('message')}")
    
    if status == 'succeeded':
        amount = intent.get('amount', 0) / 100
        currency = intent.get('currency', 'usd').upper()
        print(f"\nTransaction Details:")
        print(f"  Amount: ${amount:.2f} {currency}")
        print(f"  Intent ID: {intent.get('id')}")
    
    print("\n" + "=" * 80)


def process_payment_with_card(card_number: str, exp_month: int, exp_year: int, cvc: str) -> Dict[str, Any]:
    """
    Process a payment using custom card data.
    
    Args:
        card_number: 13-16 digit card number
        exp_month: Expiry month (1-12)
        exp_year: Expiry year (2-digit or 4-digit)
        cvc: 3-4 digit security code
    
    Returns:
        dict: Payment result with status and details
    """
    # Convert 4-digit year to 2-digit if needed
    if exp_year > 99:
        exp_year = exp_year % 100
    
    # Get random values but override with provided card data
    random_values = get_random_values(card_number, exp_month, exp_year, cvc)
    
    print("Generated Transaction Data:")
    print(f"  Name: {random_values['full_name']}")
    print(f"  Email: {random_values['email']}")
    print(f"  Card: {random_values['card_type'].title()} ****{random_values['card_number'][-4:]}")
    print(f"  Address: {random_values['address']['city']}, {random_values['address']['state']}")
    
    # Step 0: Fetch payment link to get dynamic pk_live key
    payment_link_details = step_0_fetch_payment_link()
    
    # Try to extract pk_live key from response
    pk_live_key = None
    if payment_link_details and isinstance(payment_link_details, dict):
        pk_live_key = (
            payment_link_details.get('pk_live') or 
            payment_link_details.get('public_key') or
            payment_link_details.get('key') or
            payment_link_details.get('stripe_key')
        )
    
    # Fallback to environment variable if not found
    if not pk_live_key:
        pk_live_key = os.environ.get("STRIPE_PUBLIC_KEY")
    
    # Final fallback
    if not pk_live_key:
        pk_live_key = "pk_live_51JHtoSI7vDXtMzkMWNk2vWkSCTd0CJleFGryfjIIz6CGQLaMEN6CUuo2u0hZUXS0z4SDQS8olGezV8Bfc6NIbmtK00YemvvHe5"
    
    # Extract custom fields from payment link - search in multiple paths
    custom_fields_list = []
    if payment_link_details and isinstance(payment_link_details, dict):
        # Try direct path
        custom_fields_list = payment_link_details.get('custom_fields', [])
        
        # Try nested paths if not found
        if not custom_fields_list:
            for key in ['attributes', 'payment_settings', 'checkout', 'form']:
                if key in payment_link_details:
                    custom_fields_list = payment_link_details[key].get('custom_fields', [])
                    if custom_fields_list:
                        break
    
    # Step 0b: Create payment session
    session_data = step_0b_create_payment_session(random_values['user_agent'])
    
    if not session_data:
        return {
            "success": False,
            "status": "failed",
            "error": "Failed to create payment session",
            "card_last4": card_number[-4:],
            "card_type": random_values['card_type']
        }
    
    session_id = session_data.get('session_id') or session_data.get('cs_live') or session_data.get('checkout_session_id') or session_data.get('id')
    
    if not session_id:
        return {
            "success": False,
            "status": "failed",
            "error": "Could not extract session ID",
            "card_last4": card_number[-4:],
            "card_type": random_values['card_type']
        }
    
    # Also check if custom fields were extracted in session data
    if session_data.get('_extracted_custom_fields'):
        print(f"\n✓ Using custom fields extracted from session response")
        custom_fields_list = session_data['_extracted_custom_fields']
    
    # Extract amount from session data or fetch from page
    amount = session_data.get('_extracted_amount')
    
    if not amount:
        print(f"\n✓ Amount not in session, fetching from payment page...")
        page_data = fetch_payment_page_amount(random_values['user_agent'], session_id=session_id)
        amount = page_data.get('amount')
    
    if amount:
        print(f"✓ Using amount: {amount} (${int(amount)/100:.2f})")
    else:
        print(f"⚠️  Could not extract amount, using fallback: 130313")
        amount = "130313"
    
    # Step 1: Create payment method
    payment_method = step_1_create_payment_method(random_values, pk_live_key)
    
    if not payment_method or 'id' not in payment_method:
        return {
            "success": False,
            "status": "failed",
            "error": "Failed to create payment method",
            "card_last4": card_number[-4:],
            "card_type": random_values['card_type']
        }
    
    payment_method_id = payment_method['id']
    
    # Step 2: Confirm payment page with dynamic custom fields and amount
    payment_page = step_2_confirm_payment_page(payment_method_id, random_values, pk_live_key, session_id, custom_fields_list=custom_fields_list, amount=amount)
    
    if not payment_page or 'payment_intent' not in payment_page:
        return {
            "success": False,
            "status": "failed",
            "error": "Failed to confirm payment page",
            "card_last4": card_number[-4:],
            "card_type": random_values['card_type']
        }
    
    payment_intent_data = payment_page.get('payment_intent', {})
    intent_id = payment_intent_data.get('id')
    client_secret = payment_intent_data.get('client_secret', '')
    payment_error = payment_intent_data.get('last_payment_error')
    
    # Step 3: Check final payment status (pass error if it exists)
    final_intent = step_3_check_payment_intent(intent_id, client_secret, random_values['user_agent'], pk_live_key, payment_error, amount)
    
    if not final_intent:
        return {
            "success": False,
            "status": "failed",
            "error": "Failed to retrieve payment intent status",
            "card_last4": card_number[-4:],
            "card_type": random_values['card_type']
        }
    
    # Extract status and convert to our format
    stripe_status = final_intent.get('status', 'unknown')
    error_obj = final_intent.get('last_payment_error', {})
    
    status_map = {
        'succeeded': 'charged',
        'processing': 'processing',
        'requires_payment_method': 'declined',
        'requires_action': 'otp_required',
        'requires_capture': 'approved',
        'canceled': 'declined',
    }
    
    our_status = status_map.get(stripe_status, 'failed')
    
    return {
        "success": True,
        "status": our_status,
        "stripe_status": stripe_status,
        "payment_id": intent_id,
        "payment_method_id": payment_method_id,
        "card_type": random_values['card_type'],
        "card_last4": card_number[-4:],
        "amount": final_intent.get('amount', 0) / 100,
        "currency": final_intent.get('currency', 'usd').upper(),
        "error_code": error_obj.get('code') if error_obj else None,
        "error_message": error_obj.get('message') if error_obj else None,
        "full_response": final_intent
    }


def expected_response_example() -> Dict[str, Any]:
    """
    Return the expected response structure based on the Stripe API docs
    This is the example response from the user's request
    """
    return {
        "id": "pm_1TZE7mGco2mvL6zTtOn7jDHx",
        "object": "payment_method",
        "allow_redisplay": "unspecified",
        "billing_details": {
            "address": {
                "city": None,
                "country": "US",
                "line1": None,
                "line2": None,
                "postal_code": "10001",
                "state": None
            },
            "email": "sherenhaters@gmail.com",
            "name": "John Verstappen",
            "phone": None,
            "tax_id": None
        },
        "card": {
            "brand": "mastercard",
            "checks": {
                "address_line1_check": None,
                "address_postal_code_check": None,
                "cvc_check": None
            },
            "country": "US",
            "display_brand": "mastercard",
            "exp_month": 12,
            "exp_year": 2028,
            "funding": "prepaid",
            "generated_from": None,
            "last4": "5089",
            "networks": {
                "available": ["mastercard"],
                "preferred": None
            },
            "regulated_status": "unregulated",
            "three_d_secure_usage": {
                "supported": True
            },
            "wallet": None
        },
        "created": 1779298902,
        "customer": None,
        "customer_account": None,
        "livemode": True,
        "shared_payment_granted_token": None,
        "type": "card"
    }


if __name__ == "__main__":
    print("\n⚠️  WARNING: This script uses randomized customer data for demonstration.")
    print("Do NOT use real card numbers in production code.\n")
    
    # Get random values for this transaction
    random_values = get_random_values()
    print("Generated Transaction Data:")
    print(f"  Name: {random_values['full_name']}")
    print(f"  Email: {random_values['email']}")
    print(f"  Card: {random_values['card_type'].title()} ****{random_values['card_number'][-4:]}")
    print(f"  Address: {random_values['address']['city']}, {random_values['address']['state']}")
    
    # Step 0: Fetch payment link to get dynamic pk_live key
    print("\nStarting complete payment flow...")
    payment_link_details = step_0_fetch_payment_link()
    
    # Try to extract pk_live key from response, fallback to environment variable
    pk_live_key = None
    if payment_link_details and isinstance(payment_link_details, dict):
        # Try multiple possible field names where the key might be
        pk_live_key = (
            payment_link_details.get('pk_live') or 
            payment_link_details.get('public_key') or
            payment_link_details.get('key') or
            payment_link_details.get('stripe_key')
        )
    
    # Fallback to environment variable if not found in response
    if not pk_live_key:
        pk_live_key = os.environ.get("STRIPE_PUBLIC_KEY")
    
    # Final fallback to the original working key (in real scenario, this should be set via env)
    if not pk_live_key:
        pk_live_key = "pk_live_51JHtoSI7vDXtMzkMWNk2vWkSCTd0CJleFGryfjIIz6CGQLaMEN6CUuo2u0hZUXS0z4SDQS8olGezV8Bfc6NIbmtK00YemvvHe5"
    
    # Step 0b: Create payment session to get dynamic cs_live session ID
    session_data = step_0b_create_payment_session(random_values['user_agent'])
    
    if not session_data:
        print("❌ Failed to create payment session. Exiting.")
        exit(1)
    
    # Extract session ID from response
    session_id = session_data.get('session_id')
    
    # Try alternative keys if session_id not found
    if not session_id:
        session_id = (
            session_data.get('cs_live') or 
            session_data.get('checkout_session_id') or
            session_data.get('id')
        )
    
    if not session_id:
        print("❌ Could not extract session ID from response. Exiting.")
        exit(1)
    
    print(f"\n✓ Dynamic Session ID Extracted: {session_id[:20]}...{session_id[-10:]}")
    
    # Step 1: Create payment method
    payment_method = step_1_create_payment_method(random_values, pk_live_key)
    
    if not payment_method or 'id' not in payment_method:
        print("❌ Failed to create payment method. Exiting.")
        exit(1)
    
    payment_method_id = payment_method['id']
    
    # Step 2: Confirm payment page with dynamic session ID
    payment_page = step_2_confirm_payment_page(payment_method_id, random_values, pk_live_key, session_id)
    
    if not payment_page or 'payment_intent' not in payment_page:
        print("❌ Failed to confirm payment page. Exiting.")
        exit(1)
    
    payment_intent_data = payment_page['payment_intent']
    intent_id = payment_intent_data.get('id')
    client_secret = payment_intent_data.get('client_secret')
    
    # Step 3: Check final payment status
    final_intent = step_3_check_payment_intent(intent_id, client_secret, random_values['user_agent'], pk_live_key)
    
    if final_intent:
        print_final_status(final_intent)
    else:
        print("❌ Failed to retrieve payment intent status.")
