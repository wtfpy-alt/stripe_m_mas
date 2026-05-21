"""
Core bot modules for refactored bot structure
- Message manager for edit_text handling
- OTP bypass logic for stripe gateways  
- Progress bar display
- Result file generation
"""

import os
import requests
import json
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

# ============================================================================
# MESSAGE MANAGER - Handle single message edits per user
# ============================================================================
class MessageManager:
    """Manages single message per user, edits instead of spamming"""
    
    def __init__(self):
        self.user_messages: Dict[int, int] = {}  # user_id -> message_id
    
    def store_message(self, user_id: int, message_id: int):
        """Store message ID for user"""
        self.user_messages[user_id] = message_id
    
    def get_message(self, user_id: int) -> int:
        """Get stored message ID for user"""
        return self.user_messages.get(user_id)
    
    def clear_message(self, user_id: int):
        """Clear message ID for user"""
        if user_id in self.user_messages:
            del self.user_messages[user_id]

message_manager = MessageManager()


# ============================================================================
# OTP BYPASS LOGIC - Automatically retry OTP cards on alternate gateway
# ============================================================================
@dataclass
class CardCheckResult:
    """Result of a single card check"""
    card: str
    status: str  # 'charged', 'approved', 'declined', 'otp_required', 'error'
    gateway: str  # which gateway was used
    response: str = ""
    retried: bool = False  # was this retried from OTP?
    retry_gateway: str = ""  # which gateway was used for retry


class StripeGatewayConnector:
    """Connects to both stripe endpoints with OTP bypass logic"""
    
    def __init__(self, api_url: str = "http://localhost:2101"):
        self.api_url = api_url
        self.otp_bypass_cache = {}  # Track cards sent to prevent infinite loops
    
    def check_card_stripe1(self, card: str, exp_month: str, exp_year: str, cvc: str) -> Tuple[str, str]:
        """Check card on /stripe endpoint (original)"""
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
    
    def check_card_stripe2(self, card: str, exp_month: str, exp_year: str, cvc: str) -> Tuple[str, str]:
        """Check card on /stripe2 endpoint (alternative)"""
        try:
            cc = f"{card}|{exp_month}|{exp_year}|{cvc}"
            response = requests.get(
                f"{self.api_url}/stripe2",
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
    
    def check_card_with_otp_bypass(self, card: str, exp_month: str, exp_year: str, cvc: str, 
                                   primary_gateway: str = "stripe1") -> CardCheckResult:
        """
        Check card with automatic OTP bypass logic
        
        If primary gateway returns 'otp_required', automatically retry on alternate gateway
        """
        cache_key = f"{card}|{exp_month}|{exp_year}|{cvc}"
        
        # Determine which gateway to use first
        if primary_gateway == "stripe1":
            first_gateway = self.check_card_stripe1
            second_gateway = self.check_card_stripe2
            first_name = "stripe1"
            second_name = "stripe2"
        else:
            first_gateway = self.check_card_stripe2
            second_gateway = self.check_card_stripe1
            first_name = "stripe2"
            second_name = "stripe1"
        
        # First attempt
        status, response = first_gateway(card, exp_month, exp_year, cvc)
        result = CardCheckResult(
            card=card,
            status=status,
            gateway=first_name,
            response=response
        )
        
        # If OTP required and not already retried, try alternate gateway
        if status == "otp_required" and cache_key not in self.otp_bypass_cache:
            self.otp_bypass_cache[cache_key] = True
            retry_status, retry_response = second_gateway(card, exp_month, exp_year, cvc)
            
            # If alternate gateway returns something better, use that
            if retry_status != "otp_required":
                result.status = retry_status
                result.response = retry_response
                result.retried = True
                result.retry_gateway = second_name
        
        return result


stripe_connector = StripeGatewayConnector()


# ============================================================================
# PROGRESS BAR - Display checking progress with nice formatting
# ============================================================================
class ProgressBar:
    """Displays progress of card checking"""
    
    @staticmethod
    def get_progress_text(total: int, checked: int, charged: int, approved: int, 
                         declined: int, otp: int, errors: int) -> str:
        """Get formatted progress text"""
        if total == 0:
            total = 1  # Avoid division by zero
        
        percent = int((checked / total) * 100)
        filled = int((checked / total) * 20)
        bar = "█" * filled + "░" * (20 - filled)
        
        progress = f"""<b>🔄 Card Checking Progress</b>

<code>[{bar}] {percent}%</code>

<b>Results:</b>
✓ <b>Charged:</b> {charged}
✅ <b>Approved:</b> {approved}  
❌ <b>Declined:</b> {declined}
⏳ <b>OTP Required:</b> {otp}
⚠️ <b>Errors:</b> {errors}

<b>Total:</b> {checked}/{total}"""
        
        return progress
    
    @staticmethod
    def get_final_summary(charged: int, approved: int, declined: int, 
                         otp: int, errors: int) -> str:
        """Get final summary after checking"""
        total = charged + approved + declined + otp + errors
        
        summary = f"""<b>✨ Checking Complete!</b>

<b>Final Results:</b>
✓ <b>Charged:</b> {charged}
✅ <b>Approved:</b> {approved}
❌ <b>Declined:</b> {declined}  
⏳ <b>OTP Required:</b> {otp}
⚠️ <b>Errors:</b> {errors}

<blockquote>Total cards checked: <b>{total}</b></blockquote>

📁 <b>Result files have been generated and saved.</b>"""
        
        return summary


# ============================================================================
# RESULT FILE GENERATOR - Create text files with results
# ============================================================================
class ResultFileGenerator:
    """Generates text files with card results"""
    
    def __init__(self, output_dir: str = "/tmp"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_result_files(self, results: List[CardCheckResult], user_id: int) -> Dict[str, str]:
        """
        Generate result files from card check results
        
        Returns: dict with keys: 'charged', 'approved', 'declined', 'otp_required', 'errors'
        Values are file paths
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Categorize results
        charged_cards = []
        approved_cards = []
        declined_cards = []
        otp_cards = []
        error_cards = []
        
        for result in results:
            card_line = f"{result.card} | {result.gateway}"
            if result.retried:
                card_line += f" (retried on {result.retry_gateway})"
            
            if result.status == 'charged':
                charged_cards.append(card_line)
            elif result.status == 'approved':
                approved_cards.append(card_line)
            elif result.status == 'declined':
                declined_cards.append(card_line)
            elif result.status == 'otp_required':
                otp_cards.append(card_line)
            else:
                error_cards.append(f"{card_line} | Error: {result.response[:100]}")
        
        files = {}
        
        # Write files
        if charged_cards:
            filepath = f"{self.output_dir}/charged_{user_id}_{timestamp}.txt"
            with open(filepath, 'w') as f:
                f.write("✓ CHARGED CARDS\n")
                f.write("=" * 50 + "\n")
                for card in charged_cards:
                    f.write(f"{card}\n")
            files['charged'] = filepath
        
        if approved_cards:
            filepath = f"{self.output_dir}/approved_{user_id}_{timestamp}.txt"
            with open(filepath, 'w') as f:
                f.write("✅ APPROVED CARDS\n")
                f.write("=" * 50 + "\n")
                for card in approved_cards:
                    f.write(f"{card}\n")
            files['approved'] = filepath
        
        if declined_cards:
            filepath = f"{self.output_dir}/declined_{user_id}_{timestamp}.txt"
            with open(filepath, 'w') as f:
                f.write("❌ DECLINED CARDS\n")
                f.write("=" * 50 + "\n")
                for card in declined_cards:
                    f.write(f"{card}\n")
            files['declined'] = filepath
        
        if otp_cards:
            filepath = f"{self.output_dir}/otp_required_{user_id}_{timestamp}.txt"
            with open(filepath, 'w') as f:
                f.write("⏳ OTP REQUIRED CARDS\n")
                f.write("=" * 50 + "\n")
                for card in otp_cards:
                    f.write(f"{card}\n")
            files['otp_required'] = filepath
        
        if error_cards:
            filepath = f"{self.output_dir}/errors_{user_id}_{timestamp}.txt"
            with open(filepath, 'w') as f:
                f.write("⚠️ ERROR CARDS\n")
                f.write("=" * 50 + "\n")
                for card in error_cards:
                    f.write(f"{card}\n")
            files['errors'] = filepath
        
        return files


file_generator = ResultFileGenerator()
