"""
supplier_api.py

Fetches available account offers from the supplier (luqustore.fun, backed
by fastbuy.market) to auto-list on Eldorado with a markup.

CONFIRMED WORKING ENDPOINT (captured directly from the real website's own
network traffic - no API key needed, this is how the site itself works):

    GET https://luqustore.fun/api/proxy/public/offer/list
        ?gameTypeId=<uuid>
        &isStock=false
        &orderBy=createdAt
        &orderDirection=desc
        &page=<n>
        &perPage=20

Each offer in the response includes (confirmed from a real capture):
    - title: ready-made listing title (already has the fire-emoji style)
    - description: ready-made full description (matches his real
      Eldorado listings)
    - amountCentsWithMargin: price in CENTS (e.g. 1215 = $12.15)
    - currency: "USD"
    - accountData.externalId: the account ID (e.g. "PG-SMSTE")
    - images: list of real image URLs

MARKUP: he wants to add 20% on top of the supplier's price - applied in
bot.py / app.py when building the Eldorado listing, not here.
"""

import random
import requests

SUPPLIER_BASE_URL = "https://luqustore.fun/api/proxy/public/offer/list"

# Confirmed gameTypeId values (from the supplier's own game-type list).
GAME_TYPE_IDS = {
    "pokemon go": "36ee7ec3-939e-4902-9e2c-50997aca7d32",
    "pokemon tcg pocket": "bfc8c38e-2703-4575-85ca-f0530cfa1ed5",
    "raid shadow legends": "9c946a2f-dc30-421b-a5cc-bde3805189b0",
    "dragon ball legends": "88bb2233-8bf5-4936-b9a2-8d243338faa9",
    "watcher of realms": "c8596cbd-c31d-4734-8fbe-b2f5b0f53887",
}


class SupplierAPIError(Exception):
    pass


def fetch_offers(game_name: str, max_pages: int = 3) -> list:
    """
    Fetches available offers for one game from the supplier.

    Args:
        game_name: must be one of the keys in GAME_TYPE_IDS (case-insensitive)
        max_pages: how many pages of 20 to pull (raise if you need more
            variety to pick randomly from)

    Returns:
        list of offer dicts as returned by the supplier's API
    """
    key = game_name.strip().lower()
    if key not in GAME_TYPE_IDS:
        raise SupplierAPIError(
            f"'{game_name}' isn't a known supplier game. "
            f"Available: {', '.join(GAME_TYPE_IDS.keys())}"
        )
    game_type_id = GAME_TYPE_IDS[key]

    all_offers = []
    for page in range(1, max_pages + 1):
        params = {
            "gameTypeId": game_type_id,
            "isStock": "false",
            "orderBy": "createdAt",
            "orderDirection": "desc",
            "page": page,
            "perPage": 20,
        }
        response = requests.get(SUPPLIER_BASE_URL, params=params, timeout=20)
        if response.status_code != 200:
            raise SupplierAPIError(
                f"Supplier API returned {response.status_code}: {response.text}"
            )
        data = response.json()
        offers = data.get("data", [])
        all_offers.extend(offers)

        total_pages = data.get("_metadata", {}).get("pagination", {}).get("totalPage", 1)
        if page >= total_pages:
            break

    return all_offers


def pick_random_offers(game_name: str, count: int) -> list:
    """Fetches offers for one game and randomly picks `count` of them."""
    offers = fetch_offers(game_name)
    if not offers:
        raise SupplierAPIError(f"No offers currently available for '{game_name}'.")
    return random.sample(offers, min(count, len(offers)))


def pick_random_mixed_offers(count: int) -> list:
    """
    Picks `count` offers total, each independently randomly chosen from
    across ALL available games (mixed batch).
    """
    picks = []
    games = list(GAME_TYPE_IDS.keys())
    for _ in range(count):
        game = random.choice(games)
        offers = fetch_offers(game)
        if offers:
            picks.append(random.choice(offers))
    return picks


def offer_to_listing_data(offer: dict, markup_percent: float = 20.0) -> dict:
    """
    Converts a raw supplier offer into the fields needed to create an
    Eldorado listing, applying the markup.
    """
    base_cents = offer.get("amountCentsWithMargin", 0)
    base_price = base_cents / 100
    final_price = round(base_price * (1 + markup_percent / 100), 2)

    return {
        "title": offer.get("title", "").strip(),
        "description": offer.get("description", "").strip(),
        "price": final_price,
        "external_id": offer.get("accountData", {}).get("externalId", ""),
        "game_name": offer.get("gameType", {}).get("name", ""),
    }
