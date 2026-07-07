"""
bot.py

A Telegram bot that asks a few short questions and then publishes a
Game Account offer on Eldorado.gg automatically.

HOW HE USES IT (once it's running):
  1. Open Telegram, find the bot, tap Start (or type /newoffer)
  2. Answer each question the bot asks (game, title, description, price,
     platform, and optionally send a photo)
  3. Bot shows a summary and asks "Post this? yes/no"
  4. If yes -> it calls Eldorado's API and confirms it's live

Setup instructions are in README.md - start there.
"""

import logging
import os

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from eldorado_api import create_account_offer, EldoradoAPIError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
GAME, TITLE, DESCRIPTION, PRICE, PLATFORM, PHOTO, CONFIRM = range(7)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


async def new_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Let's list a new account offer.\n\nWhich game is this account for? "
        "(e.g. Fortnite, Valorant)"
    )
    return GAME


async def got_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["game"] = update.message.text.strip()
    await update.message.reply_text("Got it. Give me a short title for the offer.")
    return TITLE


async def got_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["title"] = update.message.text.strip()
    await update.message.reply_text(
        "Now the description (level, skins, rank, anything a buyer should know)."
    )
    return DESCRIPTION


async def got_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["description"] = update.message.text.strip()
    await update.message.reply_text("What's the price? (just the number, e.g. 25)")
    return PRICE


async def got_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace("$", "")
    try:
        context.user_data["price"] = float(text)
    except ValueError:
        await update.message.reply_text("That doesn't look like a number. Try again, e.g. 25")
        return PRICE
    await update.message.reply_text("Which platform? (PC / PlayStation / Xbox / Mobile)")
    return PLATFORM


async def got_platform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["platform"] = update.message.text.strip()
    await update.message.reply_text(
        "Send a photo of the account now, or type 'skip' if you don't have one."
    )
    return PHOTO


async def got_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_url = None
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        photo_url = file.file_path  # Telegram-hosted URL
    context.user_data["photo_url"] = photo_url

    d = context.user_data
    summary = (
        "Here's what I'll post:\n\n"
        f"Game: {d['game']}\n"
        f"Title: {d['title']}\n"
        f"Description: {d['description']}\n"
        f"Price: ${d['price']}\n"
        f"Platform: {d['platform']}\n"
        f"Photo: {'yes' if photo_url else 'none'}\n\n"
        "Post this now? (yes / no)"
    )
    await update.message.reply_text(summary)
    return CONFIRM


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["photo_url"] = None
    d = context.user_data
    summary = (
        "Here's what I'll post:\n\n"
        f"Game: {d['game']}\n"
        f"Title: {d['title']}\n"
        f"Description: {d['description']}\n"
        f"Price: ${d['price']}\n"
        f"Platform: {d['platform']}\n"
        f"Photo: none\n\n"
        "Post this now? (yes / no)"
    )
    await update.message.reply_text(summary)
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text.strip().lower()
    if answer not in ("yes", "y"):
        await update.message.reply_text(
            "Okay, cancelled. Type /newoffer to start again.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    d = context.user_data
    await update.message.reply_text("Posting to Eldorado now...")
    try:
        result = create_account_offer(
            game=d["game"],
            title=d["title"],
            description=d["description"],
            price=d["price"],
            platform=d.get("platform"),
            photo_url=d.get("photo_url"),
        )
        await update.message.reply_text(f"Done! Offer posted: {result}")
    except EldoradoAPIError as e:
        await update.message.reply_text(
            f"Something went wrong posting to Eldorado:\n{e}\n\n"
            "This usually means the API details in eldorado_api.py still "
            "need to be filled in with the real ones from your seller "
            "dashboard - see README.md."
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit(
            "No TELEGRAM_BOT_TOKEN found. Add it to your .env file first - "
            "see README.md."
        )

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("newoffer", new_offer), CommandHandler("start", new_offer)],
        states={
            GAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_game)],
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_description)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_price)],
            PLATFORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_platform)],
            PHOTO: [
                MessageHandler(filters.PHOTO, got_photo),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.Regex("(?i)^skip$"),
                    skip_photo,
                ),
            ],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
