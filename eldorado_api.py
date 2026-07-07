"""
eldorado_api.py

Thin wrapper around Eldorado.gg's Seller API for creating a new
"Game Account" offer/listing.

IMPORTANT - READ THIS FIRST:
Eldorado does not publish its Seller API docs publicly. They only become
visible once you log in to your Eldorado seller dashboard and open the
"Seller API" / "Developer" section there. That's normal and not a mistake
on our end.

So this file is 90% done. The only thing missing is the exact endpoint
URL and the exact field names Eldorado expects, which you get by:
  1. Logging into eldorado.gg with the seller account
  2. Going to the Seller API / Developer settings page
  3. Generating an API key
  4. Copying the "Create Offer" (or "Create Listing") endpoint + sample
     request body shown there

Once you have that, fill in the 3 TODOs below and everything else
(the Telegram bot, the conversation flow) will work without any changes.
"""

import os
import requests

# TODO 1: Paste the base API URL shown in your Eldorado seller dashboard.
# Example placeholder - REPLACE with the real one from your dashboard.
ELDORADO_API_BASE_URL = os.environ.get("ELDORADO_API_BASE_URL", "https://api.eldorado.gg")

# TODO 2: Paste the exact path for "create account offer" from the docs.
# Example placeholder - REPLACE with the real one from your dashboard.
CREATE_ACCOUNT_OFFER_PATH = os.environ.get("ELDORADO_CREATE_OFFER_PATH", "/seller/v1/offers/account")

# Your API key - keep this in the .env file, never hard-code it here.
ELDORADO_API_KEY = os.environ.get("ELDORADO_API_KEY")


class EldoradoAPIError(Exception):
    pass


def create_account_offer(game: str, title: str, description: str, price: float,
                          platform: str = None, photo_url: str = None) -> dict:
    """
    Creates a new Game Account offer on Eldorado.

    Args:
        game: e.g. "Fortnite", "Valorant"
        title: short offer title
        description: full offer description
        price: price in USD (or whatever currency his account uses)
        platform: e.g. "PC", "PS5", "Xbox" (device filter - optional, depends on game)
        photo_url: a public URL to an image of the account (optional)

    Returns:
        dict with the created offer info (id, url, etc.) - shape depends
        on what Eldorado's API actually returns; adjust once you see a
        real response.
    """
    if not ELDORADO_API_KEY:
        raise EldoradoAPIError(
            "No API key found. Add ELDORADO_API_KEY to your .env file first."
        )

    # TODO 3: Adjust these field names to match exactly what Eldorado's
    # docs say. This is a reasonable guess based on how the rest of their
    # platform is structured (game, title, description, price, platform,
    # images) but every marketplace names things slightly differently.
    payload = {
        "game": game,
        "category": "Account",
        "title": title,
        "description": description,
        "price": price,
        "platform": platform,
        "images": [photo_url] if photo_url else [],
    }

    headers = {
        "X-API-Key": ELDORADO_API_KEY,
        "Content-Type": "application/json",
    }

    url = f"{ELDORADO_API_BASE_URL}{CREATE_ACCOUNT_OFFER_PATH}"
    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code not in (200, 201):
        raise EldoradoAPIError(
            f"Eldorado API returned {response.status_code}: {response.text}"
        )

    return response.json()
