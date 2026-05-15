#!/usr/bin/env python3
"""
LOKI TELEGRAM BOT — с поддержкой прокси для Telegram API.
Если api.telegram.org заблокирован, используется прокси-воркер.
"""

import asyncio
import json
import os
import sys
import logging
from datetime import datetime

# Добавляем корень nexus-core в PATH
NEXUS_CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, NEXUS_CORE)

from agents.loki.loki_agent import (
    LokiAgent, full_report, service_status, docker_ps,
    nexus_metrics, vpn_status, get_ram, get_disk, get_uptime,
    get_load, fail2ban_status, ssh_keys, who_is_online,
)

try:
    from telegram import Update, Bot
    from telegram.ext import (
        Application, CommandHandler, ContextTypes,
        MessageHandler, filters,
    )
    from telegram.request import HTTPXRequest
except ImportError:
    print("ERROR: python-telegram-bot not installed.")
    print("Install: pip install python-telegram-bot")
    sys.exit(1)

# =========================================================
# CONFIG
# =========================================================

TOKEN_FILE = "/root/nexus-core/agents/loki/.bot_token"
CHAT_ID_FILE = "/root/nexus-core/agents/loki/.chat_id"

# Прокси для Telegram API (если api.telegram.org заблокирован)
# Можно использовать: свой прокси, Cloudflare Worker, или другой домен
TELEGRAM_PROXY = os.environ.get("TELEGRAM_PROXY", "")  # например: socks5://host:port
TELEGRAM_API_FALLBACK = os.environ.get("TELEGRAM_API_FALLBACK", "")  # альтернативный API endpoint

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("loki-bot")

agent = LokiAgent()


def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    return os.environ.get("LOKI_BOT_TOKEN", "")


def save_chat_id(chat_id: int):
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(chat_id))


def get_chat_id():
    if os.path.exists(CHAT_ID_FILE):
        with open(CHAT_ID_FILE) as f:
            return int(f.read().strip())
    return None


def check_telegram_access() -> dict:
    """Проверить доступность Telegram API."""
    import urllib.request
    results = {}

    # Прямой доступ
    try:
        req = urllib.request.urlopen("https://api.telegram.org", timeout=5)
        results["direct"] = f"ok ({req.status})"
    except Exception as e:
        results["direct"] = f"blocked ({type(e).__name__})"

    # Через прокси (если задан)
    if TELEGRAM_PROXY:
        try:
            proxy_handler = urllib.request.ProxyHandler({
                'https': TELEGRAM_PROXY,
                'http': TELEGRAM_PROXY,
            })
            opener = urllib.request.build_opener(proxy_handler)
            req = opener.open("https://api.telegram.org", timeout=10)
            results["proxy"] = f"ok ({req.status})"
        except Exception as e:
            results["proxy"] = f"failed ({type(e).__name__})"

    return results


# =========================================================
# COMMAND HANDLERS
# =========================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_chat_id(update.effective_chat.id)
    await update.message.reply_text(
        "🛡️ *Loki Bot активирован*\n\n"
        "Я агент-оператор сервера. Команды:\n"
        "📊 /status — статус сервера\n"
        "🔍 /diagnose — диагностика\n"
        "🐳 /docker — Docker контейнеры\n"
        "🧠 /nexus — Nexus API метрики\n"
        "🔒 /vpn — VPN статус\n"
        "💾 /disk — диск\n"
        "🧮 /ram — память\n"
        "🔐 /security — безопасность\n"
        "👥 /users — кто онлайн\n"
        "📋 /services — сервисы\n"
        "🔧 /heal — починить проблемы\n"
        "📊 /report — полный отчёт\n"
        "❓ /help — помощь",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Команды Loki Bot:*\n\n"
        "📊 /status — краткий статус\n"
        "🔍 /diagnose — диагностика проблем\n"
        "🐳 /docker — список контейнеров\n"
        "🧠 /nexus — метрики Nexus API\n"
        "🔒 /vpn — статус AmneziaWG\n"
        "💾 /disk — использование диска\n"
        "🧮 /ram — использование RAM\n"
        "🔐 /security — fail2ban + SSH ключи\n"
        "👥 /users — кто на сервере\n"
        "📋 /services — статус сервисов\n"
        "🔧 /heal — auto-heal проблем\n"
        "📊 /report — полный отчёт\n\n"
        "Можно писать текстом: «статус», «диагностика», «почини»",
        parse_mode="Markdown",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = full_report()
    ram = report["ram"]
    disk_info = report["disk"][0] if report["disk"] else {}
    nexus = report["nexus"]
    vpn = report["vpn"]

    text = (
        f"📊 *Server Status*\n"
        f"⏱ Uptime: {report['uptime']}\n"
        f"🔄 Load: {report['load']}\n"
        f"💾 Disk: {disk_info.get('used','?')}/{disk_info.get('size','?')} ({disk_info.get('use_percent','?')})\n"
        f"🧮 RAM: {ram.get('mem_used','?')}/{ram.get('mem_total','?')} (avail: {ram.get('mem_available','?')})\n"
        f"🧠 Nexus: completed={nexus.get('completed_requests','?')}, queue={nexus.get('queue','?')}\n"
        f"🔒 VPN: {vpn.get('status','?')}\n"
        f"🐳 Docker: {len(report['docker'])} containers"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = agent.diagnose()
    result = result.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
    await update.message.reply_text(f"```\n{result}\n```", parse_mode="Markdown")


async def cmd_docker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    containers = docker_ps()
    lines = ["🐳 *Docker Containers:*"]
    for c in containers:
        status = c["status"]
        if "up" in status.lower() and "unhealthy" not in status.lower():
            emoji = "🟢"
        elif "unhealthy" in status.lower():
            emoji = "🔴"
        elif "exited" in status.lower():
            emoji = "⚪"
        else:
            emoji = "🟡"
        lines.append(f"{emoji} *{c['name']}* — {status}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_nexus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metrics = nexus_metrics()
    if "error" in metrics:
        await update.message.reply_text(f"❌ Nexus API error: {metrics['error']}")
        return
    text = (
        f"🧠 *Nexus API Metrics*\n"
        f"📨 Total: {metrics.get('total_requests', '?')}\n"
        f"✅ Completed: {metrics.get('completed_requests', '?')}\n"
        f"❌ Failed: {metrics.get('failed_requests', '?')}\n"
        f"📋 Queue: {metrics.get('queue', '?')}\n"
        f"⚡ Active: {metrics.get('active', '?')}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_vpn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vpn = vpn_status()
    status = vpn.get("status", "unknown")
    emoji = "🟢" if status == "up" else "🟡" if status == "stale" else "🔴"
    text = f"🔒 *VPN:* {emoji} {status}\n"
    if "endpoint" in vpn:
        text += f"📍 {vpn['endpoint']}\n"
    if "latest handshake" in vpn:
        text += f"🤝 {vpn['latest handshake']}\n"
    if "transfer" in vpn:
        text += f"📊 {vpn['transfer']}"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    disks = get_disk()
    lines = ["💾 *Disk:*"]
    for d in disks:
        pct = int(d["use_percent"].replace("%", ""))
        emoji = "🔴" if pct > 85 else "🟡" if pct > 70 else "🟢"
        lines.append(f"{emoji} {d['mount']}: {d['used']}/{d['size']} ({d['use_percent']})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_ram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ram = get_ram()
    if not ram:
        await update.message.reply_text("❌ Cannot get RAM info")
        return
    try:
        used = float(ram.get("mem_used", "0").replace("Gi", ""))
        total = float(ram.get("mem_total", "1").replace("Gi", ""))
        pct = int((used / total) * 100) if total > 0 else 0
    except:
        pct = 0
    emoji = "🔴" if pct > 85 else "🟡" if pct > 70 else "🟢"
    text = (
        f"🧮 *Memory:* {emoji} {pct}%\n"
        f"📊 {ram.get('mem_used','?')} / {ram.get('mem_total','?')}\n"
        f"✅ Available: {ram.get('mem_available','?')}\n"
        f"🔄 Swap: {ram.get('swap_used','?')} / {ram.get('swap_total','?')}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f2b = fail2ban_status()
    keys = ssh_keys()
    users = who_is_online()
    lines = ["🔐 *Security:*"]
    lines.append(f"\n🛡️ Fail2ban:")
    for line in f2b.splitlines()[:10]:
        lines.append(f"  {line}")
    lines.append(f"\n🔑 SSH Keys: {len(keys)}")
    lines.append(f"\n👥 Online:")
    for line in users.splitlines():
        if line.strip():
            lines.append(f"  • {line.strip()}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = who_is_online()
    await update.message.reply_text(f"👥 *Online:*\n```\n{users}\n```", parse_mode="Markdown")


async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    services = ["nexus-api", "nginx", "mysql", "docker", "fail2ban", "ssh", "named", "exim4"]
    lines = ["📋 *Services:*"]
    for svc in services:
        s = service_status(svc)
        emoji = "🟢" if s["active"] else "🔴"
        lines.append(f"{emoji} {svc}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_heal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔧 Running auto-heal...")
    result = agent.auto_heal(dry_run=False)
    lines = ["🔧 *Auto-Heal:*"]
    for a in result["actions"]:
        lines.append(f"  ✅ {a}")
    for e in result["errors"]:
        lines.append(f"  ❌ {e}")
    if not result["actions"]:
        lines.append("  👍 No issues!")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = full_report()
    text = (
        f"📊 *Full Report*\n"
        f"🕐 {report['timestamp']}\n"
        f"⏱ {report['uptime']}\n"
        f"🔄 Load: {report['load']}\n"
        f"💾 Disk: {report['disk'][0]['use_percent'] if report['disk'] else '?'}\n"
        f"🧮 RAM: {report['ram'].get('mem_used','?')}/{report['ram'].get('mem_total','?')}\n"
        f"🧠 Nexus: {report['nexus'].get('completed_requests','?')} done\n"
        f"🔒 VPN: {report['vpn'].get('status','?')}\n"
        f"🐳 Docker: {len(report['docker'])} containers"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверить доступность Telegram API."""
    await update.message.reply_text("🔍 Checking Telegram API access...")
    results = check_telegram_access()
    lines = ["🔍 *Telegram API Access:*"]
    for method, status in results.items():
        emoji = "🟢" if "ok" in status else "🔴"
        lines.append(f"{emoji} {method}: {status}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    result = agent.run(text)
    if isinstance(result, str):
        await update.message.reply_text(result)
    else:
        await update.message.reply_text(json.dumps(result, ensure_ascii=False, indent=2))


# =========================================================
# MAIN
# =========================================================

def main():
    token = get_token()
    if not token:
        print("ERROR: No bot token found.")
        print(f"Create file {TOKEN_FILE} with your bot token")
        sys.exit(1)

    # Проверяем доступность Telegram API
    logger.info("Checking Telegram API access...")
    access = check_telegram_access()
    for method, status in access.items():
        logger.info(f"  {method}: {status}")

    # Если прямой доступ заблокирован, но есть прокси — используем его
    if "blocked" in access.get("direct", "") and not TELEGRAM_PROXY:
        logger.warning("Telegram API is blocked directly!")
        logger.warning("Set TELEGRAM_PROXY environment variable to use a proxy")
        logger.warning("Example: TELEGRAM_PROXY=socks5://host:1080 python loki_bot.py")
        logger.warning("Or use Cloudflare Worker as proxy")
        # Всё равно запускаем — может быть доступ через VPN или другую маршрутизацию

    logger.info("Starting Loki Telegram Bot...")

    # Настройка запросов с увеличенным таймаутом
    request_kwargs = {
        "connection_pool_size": 8,
        "read_timeout": 30,
        "write_timeout": 30,
        "connect_timeout": 15,
        "pool_timeout": 10,
    }

    # Если задан прокси — используем его
    if TELEGRAM_API_FALLBACK:
        logger.info(f"Using Telegram API fallback: {TELEGRAM_API_FALLBACK}")
        request_kwargs["base_url"] = TELEGRAM_API_FALLBACK

    request = HTTPXRequest(**request_kwargs)

    app = Application.builder().token(token).request(request).build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("diagnose", cmd_diagnose))
    app.add_handler(CommandHandler("docker", cmd_docker))
    app.add_handler(CommandHandler("nexus", cmd_nexus))
    app.add_handler(CommandHandler("vpn", cmd_vpn))
    app.add_handler(CommandHandler("disk", cmd_disk))
    app.add_handler(CommandHandler("ram", cmd_ram))
    app.add_handler(CommandHandler("security", cmd_security))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CommandHandler("heal", cmd_heal))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("access", cmd_access))

    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
