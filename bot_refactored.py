"""
REFACTORED TELEGRAM BOT - Card Checker
- Integrated Autoshopify backend + Stripe gates (stripe_01, stripe2) 
- Inline buttons only, no /command based manual commands
- Single message editing to reduce spam
- OTP bypass logic between stripe gates
- Better progress tracking with progress bar
- Result files generation for checked cards
"""

import telebot
import requests
import json
import random
import os
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import sqlite3
from dataclasses import dataclass

# Import core bot modules
try:
    from bot_core import (
        message_manager, stripe_connector, ProgressBar, file_generator,
        CardCheckResult
    )
except ImportError as e:
    print(f"⚠️ Warning: Could not import bot_core: {e}")

# ============================================================================
# CONFIGURATION
# ============================================================================
TOKEN = "8542683733:AAG8_Z6e0Ivd9xwQGC0ucSbsEwiWtv3vSS0"
ADMIN_ID = 6127646960
LOG_CHANNEL_ID = -1003613602360

# Backend API endpoints
AUTOSHOPIFY_API = "http://localhost:8000"  # Your Autoshopify backend
STRIPE_01_API = "http://localhost:2101"    # Stripe gate 1
STRIPE2_API = "http://localhost:2102"      # Stripe gate 2

# ============================================================================
# PLANS - WITH DEFAULT PLAN FOR NEW USERS
# ============================================================================
PLANS = {
    'default': {'name': '🎯 Free', 'daily_credits': 200, 'description': 'Daily free credits'},
    'bronze': {'name': '🥉 Bronze', 'price': 5, 'credit': 500},
    'silver': {'name': '🥈 Silver', 'price': 15, 'credit': 1500},
    'gold': {'name': '🥇 Gold', 'price': 30, 'credit': 3000},
    'diamond': {'name': '💎 Diamond', 'price': 50, 'credit': 5000},
    'dlx': {'name': '🔥 DLX', 'price': 100, 'credit': 10000}
}

CREDIT_COSTS = {
    'check_card': 1,
    'bulk_check': 5,
}

# ============================================================================
# TELEGRAM BOT SETUP
# ============================================================================
bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=100, parse_mode='HTML')

# In-memory user data
USER_DATA: Dict[int, Dict[str, Any]] = {}
USER_MESSAGES: Dict[int, int] = {}  # Track message IDs for editing

# Database for persistence
DB_FILE = 'users.db'

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================
def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        credits INTEGER DEFAULT 200,
        daily_credits_used INTEGER DEFAULT 0,
        plan TEXT DEFAULT 'default',
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_reset_date DATE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS card_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        card_number TEXT,
        status TEXT,
        gateway TEXT,
        retry_gateway TEXT,
        checked_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

def get_user(user_id: int) -> Dict[str, Any]:
    """Get or create user"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        create_user(user_id)
        return get_user(user_id)
    
    return {
        'user_id': user[0],
        'username': user[1],
        'credits': user[2],
        'daily_credits_used': user[3],
        'plan': user[4],
        'joined_date': user[5],
        'last_reset_date': user[6]
    }

def create_user(user_id: int, username: str = None):
    """Create new user with default plan"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO users (user_id, username, credits, plan) VALUES (?, ?, ?, ?)',
              (user_id, username, 200, 'default'))
    conn.commit()
    conn.close()

def update_credits(user_id: int, amount: int):
    """Update user credits"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_card_check(user_id: int, card: str, status: str, gateway: str, retry_gateway: str = None):
    """Log card check"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO card_checks (user_id, card_number, status, gateway, retry_gateway) VALUES (?, ?, ?, ?, ?)',
              (user_id, card[-4:], status, gateway, retry_gateway))
    conn.commit()
    conn.close()

# ============================================================================
# MESSAGE EDITING HELPER - ONLY ONE MESSAGE PER USER
# ============================================================================
def edit_or_send_message(chat_id: int, text: str, reply_markup=None) -> int:
    """Edit existing message or send new one"""
    msg_id = USER_MESSAGES.get(chat_id)
    
    try:
        if msg_id:
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=text,
                    reply_markup=reply_markup
                )
                return msg_id
            except:
                # If edit fails, delete old and send new
                try:
                    bot.delete_message(chat_id, msg_id)
                except:
                    pass
        
        # Send new message
        msg = bot.send_message(chat_id, text, reply_markup=reply_markup)
        USER_MESSAGES[chat_id] = msg.message_id
        return msg.message_id
    except Exception as e:
        print(f"Error in edit_or_send_message: {e}")
        return None

# ============================================================================
# AUTOSHOPIFY GATEWAY CONNECTOR
# ============================================================================
class AutoshopifyGateway:
    def __init__(self, api_url: str = AUTOSHOPIFY_API):
        self.api_url = api_url
    
    def check_card(self, card: str, exp_month: str, exp_year: str, cvc: str, site: str = None) -> Tuple[str, str]:
        """Check card on Autoshopify gateway"""
        try:
            payload = {
                'card': card,
                'exp_month': exp_month,
                'exp_year': exp_year,
                'cvc': cvc,
                'site': site or 'https://example-shopify.myshopify.com'
            }
            
            response = requests.post(
                f"{self.api_url}/check",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'error')
                return status, json.dumps(data)
            return 'error', f"HTTP {response.status_code}"
        except Exception as e:
            return 'error', str(e)

# ============================================================================
# STRIPE GATEWAY CONNECTORS - WITH OTP BYPASS
# ============================================================================
class StripeGateway:
    def __init__(self, api_url: str, gate_name: str = "stripe"):
        self.api_url = api_url
        self.gate_name = gate_name
        self.otp_cache = {}
    
    def check_card(self, card: str, exp_month: str, exp_year: str, cvc: str) -> Tuple[str, str]:
        """Check card on Stripe gateway"""
        try:
            cc = f"{card}|{exp_month}|{exp_year}|{cvc}"
            response = requests.get(
                f"{self.api_url}/stripe",
                params={"auth": "WTFH4RSH", "cc": cc},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'error')
                return status, json.dumps(data)
            return 'error', f"HTTP {response.status_code}"
        except Exception as e:
            return 'error', str(e)
    
    def check_with_otp_bypass(self, card: str, exp_month: str, exp_year: str, cvc: str,
                               alternate_gate: 'StripeGateway' = None) -> CardCheckResult:
        """Check card with OTP bypass to alternate gate"""
        cache_key = f"{card}|{exp_month}|{exp_year}|{cvc}"
        
        # First attempt
        status, response = self.check_card(card, exp_month, exp_year, cvc)
        result = CardCheckResult(
            card=card,
            status=status,
            gateway=self.gate_name,
            response=response
        )
        
        # If OTP required and alternate gate available
        if status == "otp_required" and cache_key not in self.otp_cache and alternate_gate:
            self.otp_cache[cache_key] = True
            
            # Retry on alternate gate
            alt_status, alt_response = alternate_gate.check_card(card, exp_month, exp_year, cvc)
            
            if alt_status != "otp_required":
                result.status = alt_status
                result.response = alt_response
                result.retried = True
                result.retry_gateway = alternate_gate.gate_name
        
        return result

# Initialize gateways
stripe_gate_01 = StripeGateway(STRIPE_01_API, "stripe_01")
stripe_gate_2 = StripeGateway(STRIPE2_API, "stripe2")
autoshopify_gate = AutoshopifyGateway(AUTOSHOPIFY_API)

# ============================================================================
# INLINE BUTTON CALLBACKS
# ============================================================================
def get_main_menu() -> telebot.types.InlineKeyboardMarkup:
    """Main menu inline buttons"""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔍 Check Card", callback_data="check_card"))
    markup.add(telebot.types.InlineKeyboardButton("📊 Bulk Check", callback_data="bulk_check"))
    markup.add(telebot.types.InlineKeyboardButton("💰 Credits", callback_data="show_credits"))
    markup.add(telebot.types.InlineKeyboardButton("💳 Plans", callback_data="show_plans"))
    markup.add(telebot.types.InlineKeyboardButton("📖 Help", callback_data="show_help"))
    return markup

def get_payment_method_buttons() -> telebot.types.InlineKeyboardMarkup:
    """Choose payment method buttons"""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🛍️ Autoshopify", callback_data="pm_autoshopify"))
    markup.add(telebot.types.InlineKeyboardButton("💳 Stripe (Gate 1)", callback_data="pm_stripe1"))
    markup.add(telebot.types.InlineKeyboardButton("💳 Stripe (Gate 2)", callback_data="pm_stripe2"))
    markup.add(telebot.types.InlineKeyboardButton("⬅️ Back", callback_data="menu_main"))
    return markup

def get_back_button() -> telebot.types.InlineKeyboardMarkup:
    """Back button"""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("⬅️ Back", callback_data="menu_main"))
    return markup

# ============================================================================
# COMMAND HANDLERS
# ============================================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Start command - creates user and shows main menu"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Create user if doesn't exist
    user = get_user(user_id)
    
    welcome_text = f"""
<b>🎉 Welcome to Card Checker Bot!</b>

<blockquote>
You have been granted <b>200 daily free credits</b> to start checking cards.

<b>Available Gateways:</b>
✓ Autoshopify
✓ Stripe Gate 1
✓ Stripe Gate 2

Each card check costs <b>1 credit</b>.
Use inline buttons to navigate the bot.
</blockquote>

Your Credits: <code>{user['credits']}</code>
Plan: {PLANS[user['plan']]['name']}
"""
    
    msg = bot.send_message(user_id, welcome_text, reply_markup=get_main_menu())
    USER_MESSAGES[user_id] = msg.message_id

# ============================================================================
# CALLBACK HANDLERS
# ============================================================================
@bot.callback_query_handler(func=lambda call: call.data == "menu_main")
def handle_menu_main(call):
    """Main menu"""
    user_id = call.from_user.id
    user = get_user(user_id)
    
    menu_text = f"""
<b>🏠 Main Menu</b>

<blockquote>
<b>Credits:</b> {user['credits']} ({user['plan']})
<b>Daily Used:</b> {user['daily_credits_used']}/200
</blockquote>

Choose an option:
"""
    
    edit_or_send_message(user_id, menu_text, get_main_menu())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "show_credits")
def handle_show_credits(call):
    """Show credits"""
    user_id = call.from_user.id
    user = get_user(user_id)
    
    credits_text = f"""
<b>💰 Your Credits</b>

<blockquote>
<b>Total Credits:</b> {user['credits']}
<b>Plan:</b> {PLANS[user['plan']]['name']}
<b>Daily Limit:</b> 200
<b>Used Today:</b> {user['daily_credits_used']}
<b>Remaining:</b> {200 - user['daily_credits_used']}

<b>Cost per check:</b> 1 credit
</blockquote>
"""
    
    edit_or_send_message(user_id, credits_text, get_back_button())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "show_plans")
def handle_show_plans(call):
    """Show plans"""
    user_id = call.from_user.id
    
    plans_text = "<b>💳 Available Plans</b>\n\n<blockquote>"
    for plan_id, plan in PLANS.items():
        if plan_id != 'default':
            plans_text += f"\n{plan['name']}\nPrice: ${plan['price']} → {plan['credit']} credits"
    plans_text += "\n</blockquote>"
    
    edit_or_send_message(user_id, plans_text, get_back_button())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "show_help")
def handle_show_help(call):
    """Show help"""
    user_id = call.from_user.id
    
    help_text = """
<b>📖 Help & Information</b>

<blockquote>
<b>How to use:</b>
1. Click "Check Card" to check a single card
2. Provide card details (number, month, year, CVV)
3. Select payment gateway
4. Bot will check and show result

<b>OTP Bypass:</b>
If card returns OTP from one gate, bot automatically retries on alternate gate.

<b>Gateways:</b>
• <b>Autoshopify:</b> Shopify checkout integration
• <b>Stripe Gates:</b> Direct Stripe API checking

<b>Results:</b>
After checking, you'll receive result files with categorized cards.

<b>Commands:</b>
/start - Start bot
/balance - Check credits
</b>
</blockquote>
"""
    
    edit_or_send_message(user_id, help_text, get_back_button())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "check_card")
def handle_check_card(call):
    """Check single card"""
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if user['credits'] < 1:
        error_text = "<b>❌ Insufficient Credits</b>\n\n<blockquote>You don't have enough credits to check cards.</blockquote>"
        edit_or_send_message(user_id, error_text, get_back_button())
        bot.answer_callback_query(call.id, "Not enough credits!", show_alert=True)
        return
    
    instruction_text = """
<b>💳 Check Single Card</b>

<blockquote>
Send card details in this format:
<code>4111111111111111|12|25|123</code>

Format: <code>card_number|month|year|cvc</code>
</blockquote>
"""
    
    edit_or_send_message(user_id, instruction_text, get_back_button())
    
    # Set user state
    USER_DATA[user_id] = {'state': 'waiting_card_single', 'gateway': None}
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "bulk_check")
def handle_bulk_check(call):
    """Bulk check cards"""
    user_id = call.from_user.id
    
    instruction_text = """
<b>📊 Bulk Check Cards</b>

<blockquote>
Send multiple cards, one per line:
<code>4111111111111111|12|25|123
5555555555554444|06|27|456
4242424242424242|03|26|789</code>

Format: <code>card_number|month|year|cvc</code>
</blockquote>
"""
    
    edit_or_send_message(user_id, instruction_text, get_back_button())
    
    # Set user state
    USER_DATA[user_id] = {'state': 'waiting_cards_bulk', 'gateway': None, 'cards': []}
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pm_"))
def handle_payment_method(call):
    """Payment method selection"""
    user_id = call.from_user.id
    method = call.data.split("_")[1]  # autoshopify, stripe1, stripe2
    
    if user_id in USER_DATA:
        USER_DATA[user_id]['gateway'] = method
        
        ready_text = f"""
<b>✅ Gateway Selected: <code>{method}</code></b>

<blockquote>
Ready to check cards with <b>{method}</b> gateway.
</blockquote>

Send your cards and I'll start checking!
"""
        
        edit_or_send_message(user_id, ready_text, get_back_button())
    
    bot.answer_callback_query(call.id)

# ============================================================================
# TEXT MESSAGE HANDLERS FOR CARD INPUT
# ============================================================================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_DATA and USER_DATA[msg.from_user.id].get('state') == 'waiting_card_single')
def handle_card_input_single(message):
    """Handle single card input"""
    user_id = message.from_user.id
    user = get_user(user_id)
    user_state = USER_DATA.get(user_id, {})
    gateway = user_state.get('gateway') or 'autoshopify'
    
    try:
        # Parse card
        parts = message.text.strip().split('|')
        if len(parts) != 4:
            error_text = "<b>❌ Invalid Format</b>\n\nUse: <code>card|month|year|cvc</code>"
            edit_or_send_message(user_id, error_text, get_back_button())
            return
        
        card, month, year, cvc = parts
        
        # Update credits
        update_credits(user_id, -1)
        
        # Show progress
        progress_text = f"""
<b>🔍 Checking Card...</b>

<blockquote>
Card: <code>****{card[-4:]}</code>
Gateway: <b>{gateway}</b>
Status: Checking...
</blockquote>
"""
        edit_or_send_message(user_id, progress_text)
        
        # Check card with appropriate gateway
        if gateway == 'autoshopify':
            status, response = autoshopify_gate.check_card(card, month, year, cvc)
        elif gateway == 'stripe1':
            result = stripe_gate_01.check_with_otp_bypass(card, month, year, cvc, stripe_gate_2)
            status = result.status
            response = result.response
        elif gateway == 'stripe2':
            result = stripe_gate_2.check_with_otp_bypass(card, month, year, cvc, stripe_gate_01)
            status = result.status
            response = result.response
        else:
            status = 'error'
            response = 'Unknown gateway'
        
        # Log result
        add_card_check(user_id, card, status, gateway)
        
        # Show result
        result_text = f"""
<b>✅ Check Complete</b>

<blockquote>
Card: <code>****{card[-4:]}</code>
Gateway: <b>{gateway}</b>
Status: <b>{status.upper()}</b>

Response: <code>{str(response)[:200]}</code>
</blockquote>

Credits Used: 1
"""
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ Check Another", callback_data="check_card"))
        markup.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main"))
        
        edit_or_send_message(user_id, result_text, markup)
        
        # Clear state
        if user_id in USER_DATA:
            del USER_DATA[user_id]
        
    except Exception as e:
        error_text = f"<b>❌ Error</b>\n\n<blockquote>{str(e)[:100]}</blockquote>"
        edit_or_send_message(user_id, error_text, get_back_button())

@bot.message_handler(func=lambda msg: msg.from_user.id in USER_DATA and USER_DATA[msg.from_user.id].get('state') == 'waiting_cards_bulk')
def handle_card_input_bulk(message):
    """Handle bulk card input"""
    user_id = message.from_user.id
    user = get_user(user_id)
    user_state = USER_DATA.get(user_id, {})
    gateway = user_state.get('gateway') or 'autoshopify'
    
    try:
        # Parse cards
        lines = message.text.strip().split('\n')
        cards = []
        
        for line in lines:
            parts = line.strip().split('|')
            if len(parts) == 4:
                cards.append(tuple(parts))
        
        if not cards:
            error_text = "<b>❌ No Valid Cards Found</b>"
            edit_or_send_message(user_id, error_text, get_back_button())
            return
        
        # Check if enough credits
        cost = len(cards) * 1
        if user['credits'] < cost:
            error_text = f"<b>❌ Insufficient Credits</b>\n\n<blockquote>Need {cost}, have {user['credits']}</blockquote>"
            edit_or_send_message(user_id, error_text, get_back_button())
            return
        
        # Update credits
        update_credits(user_id, -cost)
        
        # Show progress
        progress_text = f"""
<b>🔄 Checking {len(cards)} Cards...</b>

<blockquote>
Gateway: <b>{gateway}</b>
Total: {len(cards)}
Progress: Starting...
</blockquote>

[████░░░░░░░░░░░░░░] 0%
"""
        msg_id = edit_or_send_message(user_id, progress_text)
        
        # Check all cards
        results = []
        charged = 0
        approved = 0
        declined = 0
        otp = 0
        errors = 0
        
        for idx, (card, month, year, cvc) in enumerate(cards):
            try:
                # Check with appropriate gateway
                if gateway == 'autoshopify':
                    status, response = autoshopify_gate.check_card(card, month, year, cvc)
                    result = CardCheckResult(card=card, status=status, gateway=gateway, response=response)
                elif gateway == 'stripe1':
                    result = stripe_gate_01.check_with_otp_bypass(card, month, year, cvc, stripe_gate_2)
                elif gateway == 'stripe2':
                    result = stripe_gate_2.check_with_otp_bypass(card, month, year, cvc, stripe_gate_01)
                else:
                    result = CardCheckResult(card=card, status='error', gateway=gateway, response='Unknown gateway')
                
                results.append(result)
                
                # Count statuses
                if result.status == 'charged':
                    charged += 1
                elif result.status == 'approved':
                    approved += 1
                elif result.status == 'declined':
                    declined += 1
                elif result.status == 'otp_required':
                    otp += 1
                else:
                    errors += 1
                
                # Update progress every 5 cards or at the end
                if (idx + 1) % 5 == 0 or idx == len(cards) - 1:
                    progress = int((idx + 1) / len(cards) * 20)
                    bar = "█" * progress + "░" * (20 - progress)
                    percent = int((idx + 1) / len(cards) * 100)
                    
                    progress_text = f"""
<b>🔄 Checking {len(cards)} Cards...</b>

<blockquote>
Gateway: <b>{gateway}</b>
Progress: {idx + 1}/{len(cards)}

✓ Charged: {charged}
✅ Approved: {approved}
❌ Declined: {declined}
⏳ OTP: {otp}
⚠️ Errors: {errors}
</blockquote>

[{bar}] {percent}%
"""
                    
                    try:
                        bot.edit_message_text(progress_text, user_id, msg_id)
                    except:
                        pass
            
            except Exception as e:
                errors += 1
                continue
        
        # Generate result files
        file_paths = file_generator.generate_result_files(results, user_id)
        
        # Show final summary
        final_text = f"""
<b>✨ Bulk Check Complete!</b>

<blockquote>
<b>Final Results:</b>
✓ Charged: {charged}
✅ Approved: {approved}
❌ Declined: {declined}
⏳ OTP: {otp}
⚠️ Errors: {errors}

Total: {len(cards)} cards checked
</blockquote>

📁 Result files have been generated!
"""
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔄 Check More", callback_data="bulk_check"))
        markup.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main"))
        
        edit_or_send_message(user_id, final_text, markup)
        
        # Send result files
        for file_type, file_path in file_paths.items():
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    bot.send_document(user_id, f, caption=f"📄 {file_type.upper()} Cards")
        
        # Clear state
        if user_id in USER_DATA:
            del USER_DATA[user_id]
        
    except Exception as e:
        error_text = f"<b>❌ Error</b>\n\n<blockquote>{str(e)[:100]}</blockquote>"
        edit_or_send_message(user_id, error_text, get_back_button())

@bot.message_handler(commands=['balance'])
def handle_balance(message):
    """Check balance"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    balance_text = f"""
<b>💰 Your Balance</b>

<blockquote>
Credits: <b>{user['credits']}</b>
Plan: {PLANS[user['plan']]['name']}
Daily Used: {user['daily_credits_used']}/200
</blockquote>
"""
    
    msg = bot.send_message(user_id, balance_text, reply_markup=get_main_menu())
    USER_MESSAGES[user_id] = msg.message_id

# ============================================================================
# INITIALIZE & RUN
# ============================================================================
if __name__ == '__main__':
    init_database()
    print("✅ Bot initialized with Autoshopify + Stripe gates")
    print("🔌 Autoshopify API:", AUTOSHOPIFY_API)
    print("🔌 Stripe Gate 1:", STRIPE_01_API)
    print("🔌 Stripe Gate 2:", STRIPE2_API)
    print("🚀 Starting bot...")
    bot.infinity_polling()
