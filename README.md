# Eldorado Auto-Listing Bot — Setup Guide

This is a Telegram bot. Your brother chats with it (from his phone or his
desktop — Telegram works on both, same bot, same conversation), answers a
few short questions, and it publishes a Game Account listing on Eldorado.gg
automatically.

Follow these steps in order. None of them require coding — just clicking
through some pages and copying/pasting a few codes.

---

## Step 1 — Get the Eldorado API key

1. Log into eldorado.gg with the seller account.
2. Go to the seller dashboard, find the "Seller API" / "Developer" section.
3. Generate an API key. Copy it somewhere safe (you'll paste it into a
   file later — see Step 4).
4. While you're there, also copy:
   - The **base API URL** shown
   - The exact **endpoint / path** for creating an Account offer (may be
     called "Create Offer", "Create Listing", or similar)
   - Any **example request** they show, so we can match the exact field
     names (e.g. do they call it `"title"` or `"offerTitle"`?)

Send me a screenshot or copy-paste of what that page shows and I'll wire
the code to match it exactly — right now the code has sensible guesses in
their place.

---

## Step 2 — Create the Telegram bot (5 minutes)

1. Open Telegram, search for **"BotFather"** (it's Telegram's official bot
   for creating other bots — look for the blue checkmark).
2. Send it the message `/newbot`.
3. Give it a name (anything, e.g. "Hassan Eldorado Bot").
4. Give it a username ending in "bot" (e.g. `hassan_eldorado_bot`).
5. BotFather replies with a **token** — a long string of letters and
   numbers. Copy it. This is what goes into `TELEGRAM_BOT_TOKEN`.

---

## Step 3 — Get the code

You already have three files from earlier in this conversation:
- `bot.py`
- `eldorado_api.py`
- `requirements.txt`

Plus `.env.example` — rename your copy of this to `.env` and fill in:
```
TELEGRAM_BOT_TOKEN=   <- from Step 2
ELDORADO_API_KEY=     <- from Step 1
ELDORADO_API_BASE_URL=        <- from Step 1
ELDORADO_CREATE_OFFER_PATH=   <- from Step 1
```

---

## Step 4 — Deploy it on Railway (free, always-on)

Railway keeps the bot running 24/7 so it works anytime, from any device,
without your PC needing to be on.

1. Go to **railway.app** and sign up (you can use a GitHub account or email).
2. Click **New Project → Deploy from GitHub repo**.
   - If you don't already have a GitHub account, make a free one at
     github.com, create a new repository, and upload the 4 files
     (`bot.py`, `eldorado_api.py`, `requirements.txt`, and your filled-in
     `.env` — or better, add the `.env` values in Railway directly instead
     of uploading the file, see next step).
3. In Railway, open your project → **Variables** tab, and add each value
   from your `.env` file there (this keeps secrets out of GitHub, which is
   safer). Add: `TELEGRAM_BOT_TOKEN`, `ELDORADO_API_KEY`,
   `ELDORADO_API_BASE_URL`, `ELDORADO_CREATE_OFFER_PATH`.
4. Railway will detect it's a Python project and install
   `requirements.txt` automatically.
5. Set the **Start Command** to:
   ```
   python bot.py
   ```
6. Deploy. Once it says "running", the bot is live.

---

## Step 5 — Use it

On any device (phone or desktop), open Telegram, find the bot by the
username you gave it in Step 2, and tap **Start** or send `/newoffer`.
Answer the questions it asks. At the end it shows a summary and asks
"Post this now?" — reply "yes" and it publishes the listing.

---

## If something breaks

- Bot doesn't respond at all → check Railway shows the project as
  "running", and double check `TELEGRAM_BOT_TOKEN` was pasted correctly.
- Bot responds but posting fails → almost always means the Eldorado
  fields in `eldorado_api.py` need adjusting to match their real API
  (see Step 1) — send me the error message it shows and I'll fix it.

---

## What to send me next

Whichever of these you have — send it over and I'll finish wiring the
real Eldorado connection:
- A screenshot of the Seller API page in his Eldorado dashboard, or
- The endpoint URL + a sample request they show, or
- Just his API key + confirmation he's generated it (I won't need the key
  itself, just to know it exists — keep it private, only paste it into
  the `.env` file, never into chat)
