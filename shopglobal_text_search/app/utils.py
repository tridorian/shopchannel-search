import logging
import re
from fastapi import HTTPException
from google.cloud import discoveryengine
from typing import List, Dict, Any, Optional
import json
import requests
from app.config import (
    SEARCH_SERVING_CONFIG,
    MAX_PAGE_SIZE,
    DEFAULT_PAGE_SIZE,
    ID_SEARCH_URL,
)


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def sanitize_query(query: str) -> str:
    """Sanitize search query to prevent injection attacks"""
    try:
        # Remove any HTML tags and dangerous characters
        query = re.sub(r"<[^>]+>", "", query)
        query = re.sub(r"[^\w\s\u0E00-\u0E7F\-.,]", "", query)
        sanitized = query.strip()
        if not sanitized:
            raise ValueError("Empty query after sanitization")
        return sanitized
    except Exception as e:
        logger.error(f"Query sanitization failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid query format")


def validate_page_size(page_size: int) -> int:
    """Validate and adjust page size to be within allowed limits"""
    try:
        return min(max(1, page_size), MAX_PAGE_SIZE)
    except Exception as e:
        logger.error(f"Page size validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid page size")


def filter_by_category(
    results: List[Dict[str, Any]], category_filter: str
) -> List[Dict[str, Any]]:
    """
    Filter search results by category.

    Args:
        results: List of search results
        category_filter: Category filter string to match against

    Returns:
        List of filtered results that match the category filter

    Examples:
        Category: "แฟชั่น, แฟชั่น > ผู้หญิง > กางเกงชั้นใน, แฟชั่น > ผู้หญิง"
        Filter: "ผู้หญิง" -> Match found
        Filter: "ผู้ชาย" -> No match
    """
    if not category_filter or not category_filter.strip():
        return results

    category_filter = category_filter.strip().lower()
    filtered_results = []

    for result in results:
        category = result.get("category", "")
        if not category:
            continue

        # Split by comma to get individual category paths
        category_paths = [path.strip() for path in category.split(",")]

        # Check each category path
        for path in category_paths:
            if not path:
                continue

            # Split by '>' to get category hierarchy levels
            category_levels = [level.strip().lower() for level in path.split(">")]

            # Check if filter matches any level in this path
            if category_filter in category_levels:
                filtered_results.append(result)
                break  # Found match, no need to check other paths for this result

    logger.info(
        f"Category filter '{category_filter}' matched {len(filtered_results)} out of {len(results)} results"
    )
    return filtered_results


def filter_by_price_range(
    results: List[Dict[str, Any]],
    lo_price: Optional[float] = None,
    hi_price: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Filter search results by price range.

    Args:
        results: List of search results
        lo_price: Minimum price (inclusive)
        hi_price: Maximum price (inclusive)

    Returns:
        List of filtered results that match the price range

    Logic:
        - Uses sale_price if it exists and is valid (not empty, not "0")
        - Otherwise uses regular_price
        - Filters products where lo_price <= effective_price <= hi_price
    """
    if lo_price is None and hi_price is None:
        return results

    filtered_results = []

    for result in results:
        # Get price fields
        regular_price_str = result.get("regular_price", "")
        sale_price_str = result.get("sale_price", "")

        # Determine effective price (sale_price takes priority if valid)
        effective_price = None

        try:
            # Try to use sale_price first
            if (
                sale_price_str
                and sale_price_str.strip()
                and sale_price_str.strip() != "0"
            ):
                effective_price = float(sale_price_str.strip())
            # Fallback to regular_price
            elif regular_price_str and regular_price_str.strip():
                effective_price = float(regular_price_str.strip())
        except (ValueError, TypeError):
            # Skip products with invalid price data
            continue

        # Skip if we couldn't determine a valid price
        if effective_price is None or effective_price <= 0:
            continue

        # Apply price range filters
        if lo_price is not None and effective_price < lo_price:
            continue
        if hi_price is not None and effective_price > hi_price:
            continue

        # Product passes price filter
        filtered_results.append(result)

    logger.info(
        f"Price filter (lo:{lo_price}, hi:{hi_price}) matched {len(filtered_results)} out of {len(results)} results"
    )
    return filtered_results


def get_product_name_from_id(id: str, api_key: str) -> str:
    url = ID_SEARCH_URL
    headers = {"X-API-Key": api_key}
    params = {"id": id}
    logger.info(f"Searching for product name from id: {str(id)}")
    try:
        response = requests.request("GET", url, headers=headers, params=params, data="")
    except Exception as e:
        logger.error(f"ID search failed: {str(e)}")
    resp_dict = json.loads(response.text)

    if "product_name" in resp_dict:
        return resp_dict["product_name"]
    else:
        return ""


async def perform_search(
    query: str,
    page_size: int = DEFAULT_PAGE_SIZE,
    page: int = 1,
    credentials: str = None,
    category: Optional[str] = None,
    lo_price: Optional[float] = None,
    hi_price: Optional[float] = None,
) -> tuple:
    """Perform product search using Google Vertex AI Search with pagination"""
    try:
        # Sanitize and validate inputs
        query = sanitize_query(query)
        page_size = validate_page_size(page_size)
        page = max(1, page)  # Ensure page is at least 1

        logger.info(f"Searching for: {query} (page {page}, size {page_size})")
        if category:
            logger.info(f"With category filter: {category}")

        # Calculate total results first by getting a larger batch
        # We need to get more results to apply our custom filters (category, price)
        # since Vertex AI doesn't support these filters natively
        max_fetch_size = min(
            1000, MAX_PAGE_SIZE * 10
        )  # Get up to 1000 or 10 pages worth

        # Initialize client and execute search
        client = discoveryengine.SearchServiceClient(credentials=credentials)
        request_dict = {
            "serving_config": SEARCH_SERVING_CONFIG,
            "query": query,
            "page_size": max_fetch_size,
            "query_expansion_spec": {"condition": "AUTO"},
            "spell_correction_spec": {"mode": "AUTO"},
            "language_code": "th",
        }
        response = client.search(request=request_dict)

        # Process all results
        all_results = [
            {
                "id": res.document.id,
                "record_id": res.document.struct_data.get("record_id", ""),
                "product_number": res.document.struct_data.get("product_number", ""),
                "product_name": res.document.struct_data.get("product_name", ""),
                "image_uri": res.document.struct_data.get("image_uri", ""),
                "description": res.document.struct_data.get("description", ""),
                "product_uri": res.document.struct_data.get("custom_uri", ""),
                "category": res.document.struct_data.get("category", ""),
                "brands": res.document.struct_data.get("brands", ""),
                "regular_price": res.document.struct_data.get("regular_price", ""),
                "sale_price": res.document.struct_data.get("sale_price", ""),
                "is_available": res.document.struct_data.get("is_available", 0) == 1,
            }
            for res in response.results
        ]

        logger.info(f"Found {len(all_results)} raw results from search")

        # Apply category filter if provided
        if category:
            all_results = filter_by_category(all_results, category)

        # Apply price range filter if provided
        if lo_price is not None or hi_price is not None:
            all_results = filter_by_price_range(all_results, lo_price, hi_price)

        # Get total count after filtering
        total_results = len(all_results)
        total_pages = (total_results + page_size - 1) // page_size  # Ceiling division

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = all_results[start_idx:end_idx]

        logger.info(
            f"Returning page {page}/{total_pages}: {len(paginated_results)} results (total: {total_results})"
        )

        return paginated_results, total_results, total_pages

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search operation failed")


def safe_parse_product_id(product_number: str) -> int:
    """
    Safely parse product number string to integer ID.
    Logic:
        1. Trim the string
        2. Split by space and use first element if multiple elements exist
        3. Try to convert to int
        4. Return 0 if conversion fails
    """
    try:
        if not product_number:
            return 0

        # Step 1: Trim the string
        trimmed = product_number.strip()
        if not trimmed:
            return 0

        # Step 2: Split by space and use first element if multiple elements exist
        parts = trimmed.split()
        if not parts:
            return 0

        # Use the first part
        first_part = parts[0].strip()
        if not first_part:
            return 0

        # Step 3: Try to convert to int
        return int(first_part)

    except (ValueError, TypeError, AttributeError):
        # Step 4: Return 0 if conversion fails
        logger.warning(
            f"Failed to parse product ID from '{product_number}', using 0 instead"
        )
        return 0


def transform_to_flatsome_json(
    results, total_results: int, page: int, page_size: int, total_pages: int
):
    """Transform search results to WooCommerce Flatsome theme format"""
    try:
        suggestions = []
        for res in results:
            regular_price = res.get("regular_price", "0")
            sale_price = res.get("sale_price", "0")
            is_available = res.get("is_available", False)

            suggestions.append(
                {
                    "type": "Product",
                    "id": safe_parse_product_id(res.get("product_number", "")),
                    "value": res.get("product_name", ""),
                    "url": res.get("product_uri", ""),
                    "img": res.get("image_uri", ""),
                    "price": format_price_html(regular_price, sale_price, is_available),
                }
            )
        return {
            "suggestions": suggestions,
            "total_results": total_results,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Failed to transform results: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to format results")


def format_price_html(
    regular_price: str, sale_price: str = "0", is_available: bool = False
) -> str:
    """Format price in WooCommerce HTML format"""
    try:
        regular_price = float(regular_price or "0")
        sale_price = float(sale_price or "0")

        def format_number(num: float) -> str:
            return f"{num:,.2f}"

        def price_amount_html(price: str) -> str:
            return f'<span class="woocommerce-Price-amount amount"><bdi>{price}&nbsp;<span class="woocommerce-Price-currencySymbol">&#3647;</span></bdi></span>'

        if not is_available or regular_price == 0:
            return '<span class="woocommerce-Price-amount amount"><bdi>Out of stock</bdi></span>'

        if sale_price > 0 and sale_price < regular_price:
            regular_price_str = format_number(regular_price)
            sale_price_str = format_number(sale_price)
            return f'<del aria-hidden="true">{price_amount_html(regular_price_str)}</del> <span class="screen-reader-text">Original price was: {regular_price_str}&nbsp;&#3647;.</span><ins aria-hidden="true">{price_amount_html(sale_price_str)}</ins><span class="screen-reader-text">Current price is: {sale_price_str}&nbsp;&#3647;.</span>'

        price_str = format_number(regular_price)
        return price_amount_html(price_str)
    except Exception as e:
        logger.error(f"Failed to format price: {str(e)}")
        return '<span class="woocommerce-Price-amount amount"><bdi>Price unavailable</bdi></span>'
