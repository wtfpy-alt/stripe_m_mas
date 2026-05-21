import requests
import random
import re
from faker import Faker

# ==========================================
# CONFIG
# ==========================================

BASE_URL = "https://crisisaid.org"
DONATE_URL = f"{BASE_URL}/donate/"
AJAX_URL = f"{BASE_URL}/wp-admin/admin-ajax.php"

fake = Faker()
session = requests.Session()

# ==========================================
# RANDOM VALID US ADDRESS DATABASE
# ==========================================

VALID_US_ADDRESSES = [
    {"city": "New York", "state": "New York", "zipcode": "10001"},
    {"city": "Los Angeles", "state": "California", "zipcode": "90001"},
    {"city": "Chicago", "state": "Illinois", "zipcode": "60601"},
    {"city": "Houston", "state": "Texas", "zipcode": "77001"},
    {"city": "Phoenix", "state": "Arizona", "zipcode": "85001"},
    {"city": "Philadelphia", "state": "Pennsylvania", "zipcode": "19101"},
    {"city": "San Antonio", "state": "Texas", "zipcode": "78201"},
    {"city": "San Diego", "state": "California", "zipcode": "92101"},
    {"city": "Dallas", "state": "Texas", "zipcode": "75201"},
    {"city": "San Jose", "state": "California", "zipcode": "95101"},
    {"city": "Austin", "state": "Texas", "zipcode": "78701"},
    {"city": "Jacksonville", "state": "Florida", "zipcode": "32099"},
    {"city": "Fort Worth", "state": "Texas", "zipcode": "76102"},
    {"city": "Columbus", "state": "Ohio", "zipcode": "43085"},
    {"city": "Indianapolis", "state": "Indiana", "zipcode": "46204"},
    {"city": "Charlotte", "state": "North Carolina", "zipcode": "28202"},
    {"city": "Seattle", "state": "Washington", "zipcode": "98101"},
    {"city": "Denver", "state": "Colorado", "zipcode": "80202"},
    {"city": "Boston", "state": "Massachusetts", "zipcode": "02101"},
    {"city": "Miami", "state": "Florida", "zipcode": "33101"},
]

# ==========================================
# RANDOM USER GENERATION
# ==========================================

FIRST_NAME = fake.first_name()
LAST_NAME = fake.last_name()

EMAIL = fake.email()
PHONE = fake.numerify(text="##########")

ADDRESS = random.choice(VALID_US_ADDRESSES)

ADDRESS_1 = fake.street_address()
ADDRESS_2 = ""

CITY = ADDRESS["city"]
STATE = ADDRESS["state"]
ZIPCODE = ADDRESS["zipcode"]
COUNTRY = "United States"

# ==========================================
# DONATION CONFIG
# ==========================================

CURRENCY = "USD"
DONATION_TYPE = "one-time"

DONATION_AMOUNT = "$1.00"
FINAL_AMOUNT = "$1.03"

FEE_AMOUNT = "0.03"

DONATION_TARGET = "Where Needed Most"

TRACKING_ID = fake.lexify(text="????????")

# ==========================================
# HEADERS
# ==========================================

headers = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Origin": BASE_URL,
    "Referer": DONATE_URL,
}

# ==========================================
# STEP 1 — LOAD DONATION PAGE
# ==========================================

print("[+] Loading donation page...")

r = session.get(
    DONATE_URL,
    headers=headers,
)

html = r.text

# SAVE FULL HTML FOR DEBUGGING
with open("debug.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"[+] GET Status: {r.status_code}")

# ==========================================
# TOKEN EXTRACTION FUNCTION
# ==========================================

def extract(pattern, text, name, flags=re.S):
    match = re.search(pattern, text, flags)

    if not match:
        print(f"[-] Failed extracting: {name}")
        return None

    value = match.group(1)

    print(f"[+] {name}: {value}")

    return value

# ==========================================
# EXTRACT DYNAMIC TOKENS
# ==========================================

# FORM ID
FORM_ID = extract(
    r'new GFStripe\(\s*\{.*?"formId":(\d+)',
    html,
    "FORM_ID"
)

# FEED ID
FEED_ID = extract(
    r'"feedId":"(\d+)"',
    html,
    "FEED_ID"
)

# IMPORTANT STRIPE VALIDATION NONCE
NONCE = extract(
    r'"validate_form_nonce":"([^"]+)"',
    html,
    "NONCE"
)

# VERSION HASH
VERSION_HASH = extract(
    r'"version_hash":"([^"]+)"',
    html,
    "VERSION_HASH"
)

# OPTIONAL EXTRA NONCES
AJAX_SUBMISSION_NONCE = extract(
    r'"ajax_submission_nonce":"([^"]+)"',
    html,
    "AJAX_SUBMISSION_NONCE"
)

CONFIG_NONCE = extract(
    r'"config_nonce":"([^"]+)"',
    html,
    "CONFIG_NONCE"
)

# STATE TOKEN
STATE_1 = extract(
    r'name="state_1"\s+value=\'([^\']+)\'',
    html,
    "STATE_1"
)

if not STATE_1:
    STATE_1 = extract(
        r'name="state_1"\s+value="([^"]+)"',
        html,
        "STATE_1"
    )

# UNIQUE ID
GFORM_UNIQUE_ID = extract(
    r'name="gform_unique_id"\s+value=\'([^\']+)\'',
    html,
    "GFORM_UNIQUE_ID"
)

if not GFORM_UNIQUE_ID:
    GFORM_UNIQUE_ID = extract(
        r'name="gform_unique_id"\s+value="([^"]+)"',
        html,
        "GFORM_UNIQUE_ID"
    )

# AJAX HASH
AJAX_HASH = extract(
    r'hash=([a-f0-9]{32})',
    html,
    "AJAX_HASH"
)

# STRIPE PUBLIC KEY
STRIPE_PK = extract(
    r'"apiKey":"(pk_live_[^"]+)"',
    html,
    "STRIPE_PK"
)

# PAGE INSTANCE
PAGE_INSTANCE = extract(
    r'"pageInstance":(\d+)',
    html,
    "PAGE_INSTANCE"
)

print("\n[+] TOKEN EXTRACTION COMPLETE")

# ==========================================
# VALIDATION
# ==========================================

required_tokens = {
    "FORM_ID": FORM_ID,
    "FEED_ID": FEED_ID,
    "NONCE": NONCE,
    "VERSION_HASH": VERSION_HASH,
    "AJAX_HASH": AJAX_HASH,
}

missing = [k for k, v in required_tokens.items() if not v]

if missing:
    print(f"\n[-] Missing required tokens: {missing}")
    exit()

# ==========================================
# BUILD FORM DATA
# ==========================================

data = {
    "input_41": "USD",
    "input_11": "one-time",
    "input_3": "Other|0",
    "input_4": "$1.00",
    "input_10": "Where Needed Most",
    "input_26": "",

    "input_1.3": FIRST_NAME,
    "input_1.6": LAST_NAME,
    "input_2": EMAIL,
    "input_16": PHONE,

    "input_23.1": ADDRESS_1,
    "input_23.2": ADDRESS_2,
    "input_23.3": CITY,
    "input_23.4": STATE,
    "input_23.5": ZIPCODE,
    "input_23.6": COUNTRY,

    "input_39": "",
    "input_20": "$1.00",

    "input_42": DONATE_URL,
    "input_45": "0",

    "gform_submission_method": "iframe",
    "gform_theme": "gravity-theme",
    "gform_style_settings": "[]",

    "is_submit_1": "1",

    "gform_unique_id": GFORM_UNIQUE_ID,

    "state_1": STATE_1,

    "gform_target_page_number_1": "0",
    "gform_source_page_number_1": "4",

    "gform_field_values": "",

    "version_hash": VERSION_HASH,

    "gform_submission_speeds": (
        '{"pages":{"4":[85752]}}'
    ),

    "action": "gfstripe_validate_form",

    "feed_id": FEED_ID,
    "form_id": FORM_ID,

    "tracking_id": TRACKING_ID,

    "payment_method": "card",

    "nonce": NONCE,

    "gform_ajax--stripe-temp": (
        f"form_id={FORM_ID}"
        "&title="
        "&description="
        "&tabindex=0"
        "&theme=gravity-theme"
        "&styles=[]"
        f"&hash={AJAX_HASH}"
    ),
}

# ==========================================
# SEND VALIDATION REQUEST
# ==========================================

print("\n[+] Sending validation request...")

response = session.post(
    AJAX_URL,
    headers=headers,
    data=data,
)

# ==========================================
# OUTPUT
# ==========================================

print("\n==============================")
print("STATUS:", response.status_code)
print("==============================\n")

print(response.text)