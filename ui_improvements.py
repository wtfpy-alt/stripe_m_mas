# ====================== ENHANCED UI COMPONENTS ======================

"""
Enhanced UI components for the Razor X Bot
Provides improved formatting, better visual hierarchy, and professional design
"""

# ─── UI Symbols & Borders ───
BORDERS = {
    "thick": "━━━━━━━━━━━━━━━━━━━━━━━━",
    "thin": "─────────────────────────",
    "double": "═════════════════════════",
    "dotted": "•••••••••••••••••••••••••",
}

DIVIDERS = {
    "arrow": "┏━━━━━━━━━━━━━━━━━━━━━━━┓",
    "corner": "╔═══════════════════════╗",
    "simple": "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
}

ICONS = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "loading": "⏳",
    "check": "✔️",
    "cross": "✖️",
    "arrow": "➜",
    "bullet": "▸",
    "star": "⭐",
    "diamond": "💎",
    "crown": "👑",
    "fire": "🔥",
    "lightning": "⚡",
    "gear": "⚙️",
    "shield": "🛡️",
    "lock": "🔒",
    "unlock": "🔓",
    "key": "🔑",
    "user": "👤",
    "users": "👥",
    "clock": "🕐",
    "calendar": "📅",
    "chart": "📊",
    "folder": "📁",
    "file": "📄",
    "link": "🔗",
    "globe": "🌐",
    "database": "🗄️",
    "server": "🖥️",
    "network": "🌐",
    "pulse": "📡",
}


def create_header(title, bold_sans=None):
    """Create a professional header with decorative borders"""
    if bold_sans:
        title = bold_sans(title)
    return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ {ICONS['star']} {title:^25} {ICONS['star']} ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"""


def create_section(title, content, bs=None, emoji=None):
    """Create a formatted section with title and content"""
    if bs:
        title = bs(title)
    prefix = emoji or ICONS['arrow']
    return f"{prefix} <b>{title}</b>\n{content}"


def create_menu_item(command, description, emoji=None, bs=None):
    """Create a formatted menu item"""
    if bs:
        description = bs(description)
    icon = emoji or ICONS['bullet']
    return f"{icon} <code>/{command}</code> ━ <b>{description}</b>"


def create_status_bar(label, value, status="normal", bs=None):
    """Create a status line with value and indicator"""
    if bs:
        label = bs(label)
        value = bs(str(value))
    
    status_icons = {
        "success": ICONS['check'],
        "error": ICONS['cross'],
        "warning": ICONS['warning'],
        "normal": ICONS['info'],
        "premium": ICONS['crown'],
        "free": ICONS['unlock'],
    }
    
    icon = status_icons.get(status, ICONS['info'])
    return f"{icon} <b>{label}:</b> <code>{value}</code>"


def create_stats_box(stats_dict, bs=None):
    """Create a formatted statistics box"""
    lines = []
    for key, value in stats_dict.items():
        if bs:
            key = bs(key)
            value = bs(str(value))
        lines.append(f"  ▸ <b>{key}</b>: <code>{value}</code>")
    return "\n".join(lines)


def create_card_box(card_details, bs=None):
    """Create a formatted credit card display"""
    lines = [DIVIDERS['corner']]
    
    for key, value in card_details.items():
        if bs:
            key = bs(key)
        lines.append(f"  <b>{key}</b>: <code>{value}</code>")
    
    lines.append("╚═══════════════════════╝")
    return "\n".join(lines)


def create_progress_bar(current, total, bs=None):
    """Create a visual progress bar"""
    if bs:
        current = bs(str(current))
        total = bs(str(total))
    
    percentage = int((current / total * 100) if total > 0 else 0)
    filled = int(percentage / 10)
    empty = 10 - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {percentage}% ({current}/{total})"


def create_info_box(title, info_dict, bs=None):
    """Create a detailed information box"""
    if bs:
        title = bs(title)
    
    lines = [f"{ICONS['info']} <b>{title}</b>"]
    lines.append(BORDERS['double'])
    
    for key, value in info_dict.items():
        if bs:
            key = bs(key)
        lines.append(f"  ▸ <b>{key}</b>: <code>{value}</code>")
    
    lines.append(BORDERS['double'])
    return "\n".join(lines)


def create_alert(message, level="info", bs=None):
    """Create an alert message"""
    if bs:
        message = bs(message)
    
    alert_icons = {
        "success": f"{ICONS['check']} ✨",
        "error": f"{ICONS['error']} 🚨",
        "warning": f"{ICONS['warning']} ⚠️",
        "info": f"{ICONS['info']} ℹ️",
    }
    
    icon = alert_icons.get(level, ICONS['info'])
    return f"{icon} <b>{message}</b>"


def format_table(headers, rows, bs=None):
    """Create a formatted table"""
    if bs:
        headers = [bs(h) for h in headers]
    
    lines = []
    lines.append("┌" + "┬".join(["─" * 20] * len(headers)) + "┐")
    lines.append("│ " + " │ ".join(f"{h:^18}" for h in headers) + " │")
    lines.append("├" + "┼".join(["─" * 20] * len(headers)) + "┤")
    
    for row in rows:
        lines.append("│ " + " │ ".join(f"{str(v):^18}" for v in row) + " │")
    
    lines.append("└" + "┴".join(["─" * 20] * len(headers)) + "┘")
    return "\n".join(lines)


def create_command_list(commands, bs=None):
    """Create a formatted command list"""
    lines = [f"{ICONS['lightning']} <b>COMMANDS</b> {ICONS['lightning']}"]
    lines.append(BORDERS['thick'])
    
    for cmd_group, items in commands.items():
        if bs:
            cmd_group = bs(cmd_group)
        lines.append(f"\n{ICONS['star']} <b>{cmd_group.upper()}</b>")
        for cmd, desc in items:
            if bs:
                desc = bs(desc)
            lines.append(f"  {ICONS['bullet']} <code>/{cmd}</code> → {desc}")
    
    return "\n".join(lines)


def create_plan_display(plan_info, bs=None):
    """Create a formatted plan display"""
    lines = []
    for plan_name, details in plan_info.items():
        if bs:
            plan_name = bs(plan_name)
        
        lines.append(f"\n{details.get('emoji', ICONS['star'])} <b>{plan_name}</b>")
        lines.append(f"  Duration: <code>{details.get('duration_days', 'N/A')} days</code>")
        lines.append(f"  Price: <code>{details.get('price', 'N/A')}</code>")
        lines.append(f"  Tier: <code>{details.get('tier', 'N/A')}</code>")
    
    return "\n".join(lines)


def create_error_message(error_code, error_msg, bs=None):
    """Create a formatted error message"""
    if bs:
        error_msg = bs(error_msg)
    return f"""{ICONS['error']}  <b>ERROR</b>  {ICONS['error']}
{BORDERS['thick']}
<b>Code:</b> <code>{error_code}</code>
<b>Message:</b> <code>{error_msg}</code>
{BORDERS['thick']}"""


def create_success_message(title, message, bs=None):
    """Create a formatted success message"""
    if bs:
        title = bs(title)
        message = bs(message)
    return f"""{ICONS['success']}  <b>{title}</b>  {ICONS['success']}
{BORDERS['thick']}
{message}
{BORDERS['thick']}"""


def create_loading_message(task, bs=None):
    """Create a loading/processing message"""
    if bs:
        task = bs(task)
    return f"{ICONS['loading']} <b>Processing:</b> {task}..."


# ─── Color-coded status badges ───
def create_status_badge(status, bs=None):
    """Create a status badge with appropriate icon and styling"""
    badges = {
        "active": f"{ICONS['check']} <b>ACTIVE</b>",
        "inactive": f"{ICONS['cross']} <b>INACTIVE</b>",
        "pending": f"{ICONS['loading']} <b>PENDING</b>",
        "premium": f"{ICONS['crown']} <b>PREMIUM</b>",
        "free": f"{ICONS['unlock']} <b>FREE</b>",
        "banned": f"{ICONS['shield']} <b>BANNED</b>",
        "verified": f"{ICONS['check']} <b>VERIFIED</b>",
    }
    return badges.get(status, status)


def create_divider(style="thick"):
    """Create a visual divider"""
    dividers = {
        "thick": "━" * 30,
        "thin": "─" * 30,
        "double": "═" * 30,
        "dotted": "•" * 30,
        "waves": "∼" * 30,
    }
    return dividers.get(style, "━" * 30)


def wrap_in_code_block(text, language=""):
    """Wrap text in code block"""
    return f"```{language}\n{text}\n```"
