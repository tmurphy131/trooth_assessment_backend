"""Shopify Admin API client for creating one-time prize discount codes.

Auth uses the client credentials grant for the "TROOTH Trivia Rewards" Dev
Dashboard app: client ID + secret are exchanged for a 24-hour access token
right before each use (codes are created rarely, so no caching).

When SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET are unset, the client runs in
dry-run mode outside production (returns DRYRUN-… codes, no network) and
refuses to run in production, so winners never get a fake code.
"""
import logging
import secrets
import string
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)

_CODE_ALPHABET = string.ascii_uppercase + string.digits
_PLACE_SUFFIX = {1: "1ST", 2: "2ND", 3: "3RD"}

_BASIC_CREATE = """
mutation CreatePrizeCode($input: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $input) {
    codeDiscountNode { id }
    userErrors { field message code }
  }
}
"""


class ShopifyAdminError(Exception):
    pass


@dataclass
class PrizeCode:
    code: str
    discount_id: str
    dry_run: bool = False


def is_configured() -> bool:
    return bool(settings.shopify_client_id and settings.shopify_client_secret)


def generate_code(place: int) -> str:
    suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
    return f"TROOTH-{_PLACE_SUFFIX.get(place, f'P{place}')}-{suffix}"


def _admin_base() -> str:
    return f"https://{settings.shopify_store_domain}/admin"


def _get_access_token(client: httpx.Client) -> str:
    r = client.post(
        f"{_admin_base()}/oauth/access_token",
        data={
            "client_id": settings.shopify_client_id,
            "client_secret": settings.shopify_client_secret,
            "grant_type": "client_credentials",
        },
    )
    if r.status_code != 200:
        raise ShopifyAdminError(f"Token request failed ({r.status_code}): {r.text[:300]}")
    token = r.json().get("access_token")
    if not token:
        raise ShopifyAdminError("Token response had no access_token")
    return token


def _graphql(client: httpx.Client, token: str, query: str, variables: dict) -> dict:
    r = client.post(
        f"{_admin_base()}/api/{settings.shopify_admin_api_version}/graphql.json",
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
    )
    if r.status_code != 200:
        raise ShopifyAdminError(f"GraphQL request failed ({r.status_code}): {r.text[:300]}")
    body = r.json()
    if body.get("errors"):
        raise ShopifyAdminError(f"GraphQL errors: {body['errors']}")
    return body["data"]


def build_prize_input(code: str, title: str, amount: int, starts_at: datetime, ends_at: datetime) -> dict:
    """Fixed dollar amount off items in the prize collection, single use.

    Shopify can't natively cap a percentage code at one item (buy-X-get-Y needs
    a separate purchased item; discountOnQuantity is BXGY-only), so prizes are
    fixed amounts sized to the catalog — 1st place covers the priciest item.
    """
    return {
        "title": title,
        "code": code,
        "startsAt": starts_at.isoformat(),
        "endsAt": ends_at.isoformat(),
        "context": {"all": "ALL"},
        "customerGets": {
            "value": {"discountAmount": {"amount": f"{amount:.2f}", "appliesOnEachItem": False}},
            "items": {"collections": {"add": [settings.shopify_prize_collection_id]}},
        },
        "usageLimit": 1,
        "appliesOncePerCustomer": True,
    }


def create_prize_code(place: int, amount: int, title: str, starts_at: datetime, ends_at: datetime) -> PrizeCode:
    code = generate_code(place)

    if not is_configured():
        if settings.is_production:
            raise ShopifyAdminError("Shopify Admin credentials are not configured in production")
        logger.warning(f"[shopify] DRY RUN — would create ${amount} prize code for place {place}")
        return PrizeCode(code=f"DRYRUN-{code}", discount_id="dry-run", dry_run=True)

    variables = {"input": build_prize_input(code, title, amount, starts_at, ends_at)}
    with httpx.Client(timeout=30) as client:
        token = _get_access_token(client)
        data = _graphql(client, token, _BASIC_CREATE, variables)

    result = data["discountCodeBasicCreate"]
    if result.get("userErrors"):
        raise ShopifyAdminError(f"discountCodeBasicCreate userErrors: {result['userErrors']}")
    discount_id = result["codeDiscountNode"]["id"]
    logger.info(f"[shopify] Created prize code {code} (${amount} off, place {place}) id={discount_id}")
    return PrizeCode(code=code, discount_id=discount_id)
