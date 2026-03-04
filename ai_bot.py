"""
AI Scanner Bot — Groq-powered maintenance issue detector

Detects issues without trigger words, then hands off to main bot
by sending to a dedicated AI Alerts channel.
"""

import logging
import asyncio
import uuid
from datetime import datetime, timezone

from crash_report import install_global_handler
install_global_handler("kurtex-ai-scanner")  

from telegram import Update
from telegram.ext import (
    Application, MessageHandler, CallbackQueryHandler,
    filters, ApplicationHandlerStop
)
from telegram.error import TelegramError

from config_ai import config
from ai_scanner import is_maintenance_issue, summarize_issue
from shifts_ai import ADMINS, MAIN_ADMIN_ID

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

MAIN_BOT_TRIGGERS = ['#maintenance', '#issue', '#breakdown', '#problem', '#help', '#emergency']


async def post_init(application: Application) -> None:
    me = await application.bot.get_me()
    logger.info(f"AI Scanner Bot @{me.username} running.")
    logger.info(f"Watching driver group: {config.DRIVER_GROUP_ID}")
    logger.info(f"Sending AI alerts to channel: {config.AI_ALERTS_CHANNEL_ID}")


async def _delete_after(bot, chat_id, message_id, seconds):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError:
        pass


async def post_init(application: Application) -> None:
    me = await application.bot.get_me()
    logger.info(f"AI Scanner Bot @{me.username} running.")
    logger.info(f"Watching driver group: {config.DRIVER_GROUP_ID}")


async def scan_message(update: Update, ctx):
    msg  = update.effective_message
    user = update.effective_user

    if not msg or not user or user.is_bot:
        return
    if update.effective_chat.id != config.DRIVER_GROUP_ID:
        return

    text = msg.text or msg.caption or ""
    if not text.strip() or len(text.strip()) < 10:
        return

    low = text.lower()
    if any(w in low for w in MAIN_BOT_TRIGGERS):
        logger.info("Trigger word found, skipping (main bot handles this)")
        return

    logger.info(f"Scanning message from {user.first_name}: {text[:60]}")

    is_issue, confidence = await is_maintenance_issue(text)
    if not is_issue:
        logger.info(f"Not an issue (confidence: {confidence})")
        return

    logger.info(f"Issue detected! Confidence: {confidence}. Handing off to main bot...")

    summary     = await summarize_issue(text)
    driver_name = f"{user.first_name} {user.last_name or ''}".strip()
    chat_title  = update.effective_chat.title or "Driver Group"
    alert_id    = str(uuid.uuid4())
    now         = datetime.now(timezone.utc).isoformat()

    # Send alert to the AI Alerts channel instead of writing to JSON
    alert_text = (
        f"🤖 *AI DETECTED ISSUE*\n\n"
        f"*Driver:* {driver_name}\n"
        f"*Group:* {chat_title}\n"
        f"*Issue:* {summary}\n"
        f"*Message:* _{text[:200]}_\n"
        f"*Confidence:* {confidence}\n\n"
        f"`{alert_id}`"
    )

    try:
        await ctx.bot.send_message(
            chat_id=config.AI_ALERTS_CHANNEL_ID,
            text=alert_text,
            parse_mode="Markdown"
        )
        logger.info(f"Alert {alert_id} sent to AI Alerts channel")
    except TelegramError as e:
        logger.error(f"Failed to send alert to channel: {e}")


def main():
    app = (
        Application.builder()
        .token(config.TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & (filters.TEXT | filters.PHOTO),
        scan_message
    ))

    logger.info("Starting AI Scanner Bot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
