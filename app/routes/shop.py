"""Shop availability endpoints - queries Printful API for real stock data."""

import logging
import httpx
import re
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shop", tags=["Shop"])

PRINTFUL_API_BASE = "https://api.printful.com"

# Category configuration - products are auto-categorized based on title prefix
PRODUCT_CATEGORIES = [
    {
        "id": "getrooted",
        "name": "#getrooted Collection",
        "description": "Root yourself in faith with these essentials",
        "prefixes": ["#getrooted", "getrooted"]
    },
    {
        "id": "onlyblv",
        "name": "ONLY BLV Collection", 
        "description": "Rep the brand that's building tools for real growth",
        "prefixes": ["ONLY BLV", "Only BLV", "only blv"]
    },
    {
        "id": "trooth",
        "name": "T[root]H Collection",
        "description": "Gear from the T[root]H Discipleship app",
        "prefixes": ["T[root]H", "Trooth", "t[root]h"]
    }
]


class VariantAvailability(BaseModel):
    """Availability info for a single variant."""
    external_id: str  # Shopify variant ID
    color: Optional[str] = None
    size: Optional[str] = None
    in_stock: bool
    discontinued: bool = False
    is_ignored: bool = False  # True if fulfillment is disabled in Printful


class ProductAvailability(BaseModel):
    """Availability info for a product."""
    external_id: str  # Shopify product ID
    name: str
    variants: List[VariantAvailability]


class AvailabilityResponse(BaseModel):
    """Response with all product availability."""
    products: List[ProductAvailability]


def _get_printful_headers() -> Dict[str, str]:
    """Get headers for Printful API requests."""
    token = settings.printful_api_token
    if not token:
        raise HTTPException(
            status_code=500,
            detail="Printful API token not configured"
        )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    # Add store ID header if configured (required for multi-store accounts)
    if settings.printful_store_id:
        headers["X-PF-Store-Id"] = settings.printful_store_id
    return headers


@router.get("/availability", response_model=AvailabilityResponse)
async def get_shop_availability():
    """
    Get availability for all synced products from Printful.
    
    Returns real stock data from Printful, not Shopify's fake 9999 inventory.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, get all sync products
            headers = _get_printful_headers()
            
            products_response = await client.get(
                f"{PRINTFUL_API_BASE}/sync/products",
                headers=headers
            )
            
            if products_response.status_code != 200:
                logger.error(f"Printful API error: {products_response.status_code} - {products_response.text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Printful API returned {products_response.status_code}"
                )
            
            products_data = products_response.json()
            logger.info(f"Fetched {len(products_data.get('result', []))} sync products from Printful")
            
            result_products: List[ProductAvailability] = []
            
            # For each product, get detailed variant info
            for product in products_data.get("result", []):
                sync_product_id = product.get("id")
                external_id = str(product.get("external_id", ""))
                product_name = product.get("name", "Unknown")
                
                # Get full product details including variants
                detail_response = await client.get(
                    f"{PRINTFUL_API_BASE}/sync/products/{sync_product_id}",
                    headers=headers
                )
                
                if detail_response.status_code != 200:
                    logger.warning(f"Could not fetch details for product {sync_product_id}")
                    continue
                
                detail_data = detail_response.json()
                sync_variants = detail_data.get("result", {}).get("sync_variants", [])
                
                variants: List[VariantAvailability] = []
                
                for variant in sync_variants:
                    variant_external_id = str(variant.get("external_id", ""))
                    
                    # Use direct color and size fields from Printful
                    color = variant.get("color")
                    size = variant.get("size")
                    # Normalize "One size" to None for consistency
                    if size and size.lower() == "one size":
                        size = None
                    
                    # Check availability from Printful
                    # Printful marks items as "discontinued" or other statuses
                    availability_status = variant.get("availability_status", "active")
                    is_discontinued = availability_status in ("discontinued", "out_of_stock")
                    
                    # Also check if the variant is marked as ignored/hidden
                    is_ignored = variant.get("is_ignored", False)
                    
                    # For Printful print-on-demand, items are available unless explicitly marked otherwise
                    in_stock = not is_discontinued and not is_ignored
                    
                    # Log for debugging
                    logger.debug(
                        f"Variant {variant_external_id}: {color}/{size} - "
                        f"status={availability_status}, in_stock={in_stock}"
                    )
                    
                    variants.append(VariantAvailability(
                        external_id=variant_external_id,
                        color=color,
                        size=size,
                        in_stock=in_stock,
                        discontinued=is_discontinued,
                        is_ignored=is_ignored
                    ))
                
                result_products.append(ProductAvailability(
                    external_id=external_id,
                    name=product_name,
                    variants=variants
                ))
            
            return AvailabilityResponse(products=result_products)
            
    except httpx.RequestError as e:
        logger.error(f"Network error calling Printful API: {e}")
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Printful API"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_shop_availability: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error fetching availability"
        )


@router.get("/availability/{shopify_product_id}")
async def get_product_availability(shopify_product_id: str):
    """
    Get availability for a specific Shopify product ID.
    
    This is a convenience endpoint if you only need one product.
    """
    all_availability = await get_shop_availability()
    
    for product in all_availability.products:
        if product.external_id == shopify_product_id:
            return product
    
    raise HTTPException(
        status_code=404,
        detail=f"Product {shopify_product_id} not found in Printful sync"
    )


# ============ Shopify Product Fetching ============

class ShopifyVariant(BaseModel):
    """A product variant from Shopify."""
    id: str
    title: str
    price: str
    available_for_sale: bool
    color: Optional[str] = None
    size: Optional[str] = None
    image_url: Optional[str] = None


class ShopifyProduct(BaseModel):
    """A product from Shopify Storefront API."""
    id: str  # Numeric product ID (without GID prefix)
    title: str
    description: Optional[str] = None
    price_range: str  # e.g., "From $29.99" or "$19.99"
    featured_image: Optional[str] = None
    options: List[Dict[str, Any]]  # [{name: "Color", values: ["Black", "Navy"]}]
    variants: List[ShopifyVariant]
    category_id: Optional[str] = None  # Assigned category


class ProductCategory(BaseModel):
    """A category with its products."""
    id: str
    name: str
    description: str
    products: List[ShopifyProduct]


class ProductsResponse(BaseModel):
    """Response with all products organized by category."""
    categories: List[ProductCategory]
    uncategorized: List[ShopifyProduct]  # Products that didn't match any category


def _categorize_product(title: str) -> Optional[str]:
    """Determine which category a product belongs to based on title."""
    title_lower = title.lower()
    for category in PRODUCT_CATEGORIES:
        for prefix in category["prefixes"]:
            if title_lower.startswith(prefix.lower()):
                return category["id"]
    return None


def _extract_numeric_id(gid: str) -> str:
    """Extract numeric ID from Shopify GID."""
    # gid://shopify/Product/12345 -> 12345
    match = re.search(r'/(\d+)$', gid)
    return match.group(1) if match else gid


def _format_price_range(variants: List[dict]) -> str:
    """Format price range from variants."""
    prices = [float(v.get("price", {}).get("amount", 0)) for v in variants]
    if not prices:
        return "$0.00"
    
    min_price = min(prices)
    max_price = max(prices)
    
    if min_price == max_price:
        return f"${min_price:.2f}"
    else:
        return f"From ${min_price:.2f}"


@router.get("/products", response_model=ProductsResponse)
async def get_shop_products():
    """
    Fetch all products from Shopify Storefront API and organize by category.
    
    Products are auto-categorized based on title prefixes:
    - "#getrooted" -> getrooted collection
    - "ONLY BLV" -> onlyblv collection  
    - "T[root]H" -> trooth collection
    
    Returns products grouped by category for easy frontend rendering.
    """
    store_domain = settings.shopify_store_domain
    token = settings.shopify_storefront_token
    
    if not store_domain or not token:
        raise HTTPException(
            status_code=500,
            detail="Shopify credentials not configured"
        )
    
    # GraphQL query to fetch all products
    query = """
    {
      products(first: 100, sortKey: TITLE) {
        edges {
          node {
            id
            title
            description
            featuredImage {
              url
            }
            options {
              name
              values
            }
            variants(first: 100) {
              edges {
                node {
                  id
                  title
                  availableForSale
                  price {
                    amount
                    currencyCode
                  }
                  selectedOptions {
                    name
                    value
                  }
                  image {
                    url
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://{store_domain}/api/2024-01/graphql.json",
                headers={
                    "Content-Type": "application/json",
                    "X-Shopify-Storefront-Access-Token": token
                },
                json={"query": query}
            )
            
            if response.status_code != 200:
                logger.error(f"Shopify API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Shopify API returned {response.status_code}"
                )
            
            data = response.json()
            
            if "errors" in data:
                logger.error(f"Shopify GraphQL errors: {data['errors']}")
                raise HTTPException(
                    status_code=502,
                    detail="Shopify GraphQL query failed"
                )
            
            products_data = data.get("data", {}).get("products", {}).get("edges", [])
            logger.info(f"Fetched {len(products_data)} products from Shopify")
            
            # Organize by category
            categorized: Dict[str, List[ShopifyProduct]] = {cat["id"]: [] for cat in PRODUCT_CATEGORIES}
            uncategorized: List[ShopifyProduct] = []
            
            for edge in products_data:
                node = edge["node"]
                product_id = _extract_numeric_id(node["id"])
                title = node["title"]
                
                # Parse variants
                variants = []
                for v_edge in node.get("variants", {}).get("edges", []):
                    v = v_edge["node"]
                    
                    # Extract color and size from selectedOptions
                    color = None
                    size = None
                    for opt in v.get("selectedOptions", []):
                        if opt["name"].lower() == "color":
                            color = opt["value"]
                        elif opt["name"].lower() == "size":
                            size = opt["value"]
                    
                    variants.append(ShopifyVariant(
                        id=_extract_numeric_id(v["id"]),
                        title=v["title"],
                        price=v.get("price", {}).get("amount", "0"),
                        available_for_sale=v.get("availableForSale", True),
                        color=color,
                        size=size,
                        image_url=v.get("image", {}).get("url") if v.get("image") else None
                    ))
                
                # Determine category
                category_id = _categorize_product(title)
                
                product = ShopifyProduct(
                    id=product_id,
                    title=title,
                    description=node.get("description"),
                    price_range=_format_price_range([v_edge["node"] for v_edge in node.get("variants", {}).get("edges", [])]),
                    featured_image=node.get("featuredImage", {}).get("url") if node.get("featuredImage") else None,
                    options=node.get("options", []),
                    variants=variants,
                    category_id=category_id
                )
                
                if category_id:
                    categorized[category_id].append(product)
                else:
                    uncategorized.append(product)
            
            # Build response with non-empty categories
            categories = []
            for cat_config in PRODUCT_CATEGORIES:
                cat_id = cat_config["id"]
                if categorized[cat_id]:  # Only include categories with products
                    categories.append(ProductCategory(
                        id=cat_id,
                        name=cat_config["name"],
                        description=cat_config["description"],
                        products=categorized[cat_id]
                    ))
            
            return ProductsResponse(
                categories=categories,
                uncategorized=uncategorized
            )
            
    except httpx.RequestError as e:
        logger.error(f"Network error calling Shopify API: {e}")
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Shopify API"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_shop_products: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error fetching products"
        )
