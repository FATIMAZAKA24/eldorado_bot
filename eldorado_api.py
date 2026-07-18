"""
eldorado_api.py

Wrapper around Eldorado.gg's real Seller API, using the official
Client Credentials flow confirmed by Eldorado's API team.

HOW AUTH WORKS (confirmed, not a guess):
1. A Client ID + Client Secret were generated once from the browser
   (this is done, already in your .env file).
2. This code exchanges that Client ID + Secret for a short-lived
   access token (valid ~15 minutes) by calling:
       POST /api/authentication/seller/token
3. That access token is sent as:  Authorization: Bearer <token>
   on every actual API call (like creating an offer).
4. When the token expires, we just request a new one - handled
   automatically below.

Endpoint used to create a Game Account offer:
   POST /api/flexibleOffers/account

NOTE: The exact fields inside the offer payload below are still
placeholders in a few spots (marked TODO) - once you paste in an
example request body from Swagger's "Try it out" for this specific
endpoint, I'll match them exactly.
"""

import os
import time
import requests

ELDORADO_HOSTNAME = "www.eldorado.gg"
TOKEN_PATH = "/api/authentication/seller/token"
CREATE_ACCOUNT_OFFER_PATH = "/api/flexibleOffers/account"

CLIENT_ID = os.environ.get("ELDORADO_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ELDORADO_CLIENT_SECRET")

# Simple in-memory cache so we don't fetch a new token on every single call.
_cached_token = None
_token_expires_at = 0


class EldoradoAPIError(Exception):
    pass


def _get_access_token() -> str:
    global _cached_token, _token_expires_at

    if not CLIENT_ID or not CLIENT_SECRET:
        raise EldoradoAPIError(
            "Missing ELDORADO_CLIENT_ID / ELDORADO_CLIENT_SECRET in your .env file."
        )

    # Reuse the cached token if it's still valid (with a 30s safety buffer).
    if _cached_token and time.time() < _token_expires_at - 30:
        return _cached_token

    url = f"https://{ELDORADO_HOSTNAME}{TOKEN_PATH}"
    response = requests.post(
        url,
        json={"clientId": CLIENT_ID, "clientSecret": CLIENT_SECRET},
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if response.status_code != 200:
        raise EldoradoAPIError(
            f"Eldorado token request failed ({response.status_code}): {response.text}"
        )

    data = response.json()
    _cached_token = data["AccessToken"]
    _token_expires_at = time.time() + data.get("ExpiresIn", 900)
    return _cached_token


# Known games and their internal Eldorado codes.
# Add a new entry here every time you capture a new game's real request
# (see README for how to capture one - Network tab, filter "flexibleOffers",
# create one real listing, look at the "account" request's Payload tab).
GAME_LOOKUP = {
    "8 ball pool": {"game_id": "77", "trade_environment_id": None},
    "pokemon go": {"game_id": "57", "trade_environment_id": None},
    "steal a brainrot": {"game_id": "259", "trade_environment_id": "0"},
    "raid shadow legends": {"game_id": "73", "trade_environment_id": None},
    # Add a new entry here every time you capture a new game's real request
    # (Network tab, filter "flexibleOffers", create one real listing, look
    # at the "account" request's Payload tab) - or read it from his existing
    # listings via the console script we used to get these four.
}


def create_account_offer(game_name: str, title: str, description: str, price: float,
                          account_secret_details: list,
                          guaranteed_delivery_time: str = "Instant",
                          has_original_email: bool = True) -> dict:
    """
    Creates a new Game Account offer on Eldorado.

    Args:
        game_name: e.g. "8 Ball Pool" - must exist in GAME_LOOKUP above,
            or this raises an error telling you to capture it first.
        title: short offer title
        description: full offer description
        price: price per unit in USD
        account_secret_details: list of strings with the account info the
            buyer needs (e.g. login code, recovery code, etc. - depends
            on the game)
        guaranteed_delivery_time: e.g. "Instant", "Minute20" - depends on
            what Eldorado allows for that game
        has_original_email: whether the original account email is included

    Returns:
        dict with the created offer info as returned by Eldorado.
    """
    game_key = game_name.strip().lower()
    if game_key not in GAME_LOOKUP:
        raise EldoradoAPIError(
            f"'{game_name}' isn't set up yet. Capture one real listing for "
            f"this game (Network tab -> filter flexibleOffers -> create a "
            f"listing -> check the 'account' request's Payload) and add its "
            f"gameId to GAME_LOOKUP in eldorado_api.py."
        )
    game_info = GAME_LOOKUP[game_key]

    token = _get_access_token()

    payload = {
        "accountSecretDetails": account_secret_details,
        "augmentedGame": {
            "gameId": game_info["game_id"],
            "category": "Account",
            "attributeIdsCsv": None,
            "tradeEnvironmentId": game_info["trade_environment_id"],
            "offerAttributes": [],
        },
        "details": {
            "pricing": {
                "quantity": 1,
                "pricePerUnit": {"amount": price, "currency": "USD"},
            },
            "description": description,
            "guaranteedDeliveryTime": guaranteed_delivery_time,
            "hasOriginalEmail": has_original_email,
            "offerImages": [],
            "offerTitle": title,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    url = f"https://{ELDORADO_HOSTNAME}{CREATE_ACCOUNT_OFFER_PATH}"
    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code not in (200, 201):
        raise EldoradoAPIError(
            f"Eldorado API returned {response.status_code}: {response.text}"
        )

    return response.json()
