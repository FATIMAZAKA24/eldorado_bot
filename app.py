"""
app.py

Telegram bot for auto-listing Eldorado account offers, built as a Flask
web app using Telegram's WEBHOOK mode (instead of constantly polling for
messages). This is what lets it run on PythonAnywhere's free tier, which
doesn't support long-running background scripts.

HOW IT WORKS:
Telegram sends a POST request to this app's /webhook URL every time
someone messages the bot. This app reads the message, figures out what
step of the conversation the person is on (stored in a simple in-memory
dict), and replies accordingly - same questions as before (game, title,
description, price, account details, confirm).

ONE-TIME SETUP NEEDED (after deploying, see README.md):
Tell Telegram to send messages to this app by visiting, once, in any
browser:
    https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<your-pythonanywhere-username>.pythonanywhere.com/webhook

NOTE ON MEMORY: conversation progress is stored in memory (the
`user_state` dict below). If the web app restarts mid-conversation,
that one conversation resets - the person just sends /newoffer again.
Fine for personal/low-volume use like this.
"""

import os
import random
import string
import requests
from flask import Flask, request, jsonify

from eldorado_api import create_account_offer, EldoradoAPIError, GAME_LOOKUP
from supplier_api import (
    pick_random_offers,
    pick_random_mixed_offers,
    offer_to_listing_data,
    SupplierAPIError,
)

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# In-memory conversation state: {chat_id: {"step": "...", "data": {...}}}
user_state = {}

STEP_GAME = "game"
STEP_TITLE = "title"
STEP_DESCRIPTION = "description"
STEP_PRICE = "price"
STEP_ACCOUNT_DETAILS = "account_details"
STEP_CONFIRM = "confirm"


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API_URL}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=15,
    )


def generate_fake_credentials():
    """Generates a random-looking, clearly fake email:password placeholder."""
    username = "".join(random.choices(string.ascii_lowercase, k=8)) + str(random.randint(10, 99))
    domain = random.choice(["gmail.com", "yahoo.com", "outlook.com"])
    password = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{username}@{domain} | {password}"


def handle_autolist(chat_id, text):
    """
    Handles "/autolist <count> [game name]" - picks random supplier offers
    and posts them to Eldorado automatically with a 20% markup.
    """
    parts = text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        send_message(
            chat_id,
            "Usage: /autolist <count> [game name]\n"
            "Example: /autolist 5\n"
            "Or: /autolist 5 pokemon go",
        )
        return

    count = min(int(parts[1]), 20)  # safety cap per batch
    game_name = parts[2].strip() if len(parts) > 2 else None

    send_message(
        chat_id,
        f"Picking {count} random offer(s)"
        f"{' for ' + game_name if game_name else ' across all supplier games'}...",
    )

    try:
        if game_name:
            offers = pick_random_offers(game_name, count)
        else:
            offers = pick_random_mixed_offers(count)
    except SupplierAPIError as e:
        send_message(chat_id, f"Couldn't fetch offers from supplier:\n{e}")
        return

    if not offers:
        send_message(chat_id, "No offers found to list.")
        return

    results = []
    for offer in offers:
        listing = offer_to_listing_data(offer, markup_percent=20.0)
        fake_creds = generate_fake_credentials()
        try:
            create_account_offer(
                game_name=listing["game_name"],
                title=listing["title"],
                description=listing["description"],
                price=listing["price"],
                account_secret_details=[fake_creds],
            )
            results.append(
                f"[OK] {listing['game_name']} - {listing['external_id']} - ${listing['price']}"
            )
        except EldoradoAPIError as e:
            results.append(
                f"[FAILED] {listing['game_name']} - {listing['external_id']}: {e}"
            )

    send_message(chat_id, "Done!\n\n" + "\n".join(results))


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    message = update.get("message")
    if not message or "text" not in message:
        return jsonify({"ok": True})

    chat_id = message["chat"]["id"]
    text = message["text"].strip()

    # Commands work regardless of conversation state.
    if text.startswith("/autolist"):
        handle_autolist(chat_id, text)
        return jsonify({"ok": True})

    if text in ("/start", "/newoffer"):
        known_games = ", ".join(sorted(g.title() for g in GAME_LOOKUP.keys()))
        user_state[chat_id] = {"step": STEP_GAME, "data": {}}
        send_message(
            chat_id,
            "Let's list a new account offer.\n\n"
            f"Which game is this for? (set up so far: {known_games})",
        )
        return jsonify({"ok": True})

    if text == "/cancel":
        user_state.pop(chat_id, None)
        send_message(chat_id, "Cancelled.")
        return jsonify({"ok": True})

    state = user_state.get(chat_id)
    if not state:
        send_message(chat_id, "Send /newoffer to start listing an account.")
        return jsonify({"ok": True})

    step = state["step"]
    data = state["data"]

    if step == STEP_GAME:
        data["game"] = text
        state["step"] = STEP_TITLE
        send_message(chat_id, "Got it. Give me a short title for the offer.")

    elif step == STEP_TITLE:
        data["title"] = text
        state["step"] = STEP_DESCRIPTION
        send_message(
            chat_id,
            "Now the description (level, skins, rank, anything a buyer should know).",
        )

    elif step == STEP_DESCRIPTION:
        data["description"] = text
        state["step"] = STEP_PRICE
        send_message(chat_id, "What's the price in USD? (just the number, e.g. 25)")

    elif step == STEP_PRICE:
        try:
            data["price"] = float(text.replace("$", ""))
        except ValueError:
            send_message(chat_id, "That doesn't look like a number. Try again, e.g. 25")
            return jsonify({"ok": True})
        state["step"] = STEP_ACCOUNT_DETAILS
        send_message(
            chat_id,
            "Now send the account details the buyer will need after purchase "
            "(login code, recovery code, etc. - whatever this game requires).",
        )

    elif step == STEP_ACCOUNT_DETAILS:
        data["account_secret_details"] = [text]
        state["step"] = STEP_CONFIRM
        summary = (
            "Here's what I'll post:\n\n"
            f"Game: {data['game']}\n"
            f"Title: {data['title']}\n"
            f"Description: {data['description']}\n"
            f"Price: ${data['price']}\n"
            f"Account details: (hidden, {len(data['account_secret_details'][0])} chars)\n\n"
            "Post this now? (yes / no)"
        )
        send_message(chat_id, summary)

    elif step == STEP_CONFIRM:
        if text.lower() in ("yes", "y"):
            send_message(chat_id, "Posting to Eldorado now...")
            try:
                result = create_account_offer(
                    game_name=data["game"],
                    title=data["title"],
                    description=data["description"],
                    price=data["price"],
                    account_secret_details=data["account_secret_details"],
                )
                send_message(chat_id, f"Done! Offer posted: {result}")
            except EldoradoAPIError as e:
                send_message(chat_id, f"Something went wrong posting to Eldorado:\n{e}")
        else:
            send_message(chat_id, "Okay, cancelled. Type /newoffer to start again.")
        user_state.pop(chat_id, None)

    return jsonify({"ok": True})


@app.route("/", methods=["GET"])
def index():
    return "Eldorado bot is running."


if __name__ == "__main__":
    app.run()
