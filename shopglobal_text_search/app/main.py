from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
from app.config import (
    CORS_ALLOW_ORIGINS,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_QUERY_LENGTH,
    MAX_QUERY_LENGTH,
    APP_HOST,
    APP_PORT,
    APP_AUTO_RELOAD,
    APP_LOG_LEVEL,
)
from app.authentications import validate_api_key, get_gcp_credentials
from app.utils import (
    perform_search,
    transform_to_flatsome_json,
    get_product_name_from_id,
)
from app.data_store import (
    HealthCheckResponse,
    SearchResponse,
    FlatsomeResponse,
    ErrorResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


########################################################
# FastAPI Setup
########################################################
app = FastAPI(
    title="ShopChannel Text-Search API",
    description="API for searching products by natural language text. Using Google Vertex AI Search. Supports both Thai and English queries.",
    version="0.0.1",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ALLOW_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize credentials
try:
    credentials = get_gcp_credentials()
except Exception as e:
    logger.error(f"Failed to initialize GCP credentials: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to initialize GCP credentials")


########################################################
# API Endpoints
########################################################
@app.get(
    "/",
    response_model=HealthCheckResponse,
    responses={
        200: {"description": "Service is healthy"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def health_check():
    """
    Health check endpoint to verify the service is running properly.

    Returns:
        HealthCheckResponse: Status of the service

    Examples:
        ```json
        {
            "message": "ok",
            "status": "healthy"
        }
        ```
    """
    # from fastapi.responses import RedirectResponse

    # return RedirectResponse(url="/docs")
    return {"message": "ok", "status": "healthy"}


@app.get(
    "/api/search-by-text",
    response_model=SearchResponse,
    responses={
        200: {"description": "Successful search results"},
        400: {"model": ErrorResponse, "description": "Invalid query or parameters"},
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Search operation failed"},
    },
)
async def search_products(
    query: str = Query(
        ...,
        description="Search query text (supports both Thai and English)",
        examples="เสื้อผ้าผู้ชาย",
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
    ),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        description="Number of results per page",
        ge=1,
        le=MAX_PAGE_SIZE,
    ),
    page: int = Query(
        1,
        description="Page number (1-based)",
        ge=1,
    ),
    cat: str = Query(
        None,
        description="Category filter to narrow down search results. Matches any level in category hierarchy.",
        examples="ผู้หญิง",
    ),
    lo_price: float = Query(
        None,
        description="Minimum price filter (inclusive). Uses sale_price if available, otherwise regular_price.",
        examples=1000,
        ge=0,
    ),
    hi_price: float = Query(
        None,
        description="Maximum price filter (inclusive). Uses sale_price if available, otherwise regular_price.",
        examples=5000,
        ge=0,
    ),
    api_key: str = Depends(validate_api_key),
):
    """
    General purpose product search endpoint

    This endpoint supports both Thai and English queries. The search is optimized for Thai language
    with automatic language detection and appropriate text processing.

    Features:
    - Multi-language support (Thai and English)
    - Automatic language detection
    - Spell correction
    - Query expansion
    - Pagination support
    - Category filtering
    - Price range filtering

    Parameters:
    - query: The search text to find products (Thai or English)
    - page_size: Number of results per page (1-{MAX_PAGE_SIZE})
    - page: Page number to retrieve (1-based)
    - cat: Optional category filter (matches any level in category hierarchy)
    - lo_price: Optional minimum price filter (inclusive)
    - hi_price: Optional maximum price filter (inclusive)
    - X-API-Key: API key for authentication (header)

    Returns:
    - List of matching products with their details including:
        - Product ID and record ID
        - Product name and description
        - Image URL
        - Category and brand information
        - Pricing information
        - Availability status
    - Pagination metadata:
        - Current page number
        - Page size
        - Total results count
        - Total pages count

    Examples:
    - Thai query: /api/search-by-text?query=เสื้อผ้าผู้ชาย
    - English query: /api/search-by-text?query=men's clothing
    - With pagination: /api/search-by-text?query=เสื้อผ้าผู้ชาย&page=2&page_size=20
    - With category filter: /api/search-by-text?query=รองเท้า&cat=ผู้หญิง&page=1
    - With price range: /api/search-by-text?query=รองเท้า&lo_price=3000&hi_price=9000&page=1
    - Combined filters: /api/search-by-text?query=รองเท้า&cat=ผู้หญิง&lo_price=3000&hi_price=9000&page=2&page_size=15

    Category Filter Examples:
    - Category: "แฟชั่น, แฟชั่น > ผู้หญิง > กางเกงชั้นใน, แฟชั่น > ผู้หญิง"
    - Filter "ผู้หญิง" will match this product
    - Filter "แฟชั่น" will match this product
    - Filter "กางเกงชั้นใน" will match this product
    - Filter "ผู้ชาย" will NOT match this product

    Price Filter Examples:
    - Product with regular_price: "5000", sale_price: "" → Effective price: 5000
    - Product with regular_price: "5000", sale_price: "3500" → Effective price: 3500 (sale takes priority)
    - Filter lo_price=3000, hi_price=9000 → Includes products with effective price 3000-9000

    Response Example:
    ```json
    {
        "query": "เสื้อผ้าผู้ชาย",
        "results": [
            {
                "id": "123",
                "record_id": "REC001",
                "product_number": "SKU001",
                "product_name": "เสื้อเชิ้ตผู้ชาย",
                "image_uri": "https://example.com/image.jpg",
                "description": "เสื้อเชิ้ตผู้ชายสไตล์แคชชวล",
                "product_uri": "https://example.com/product/123",
                "category": "เสื้อผ้าผู้ชาย",
                "brands": "Brand A",
                "regular_price": "599",
                "sale_price": "499",
                "is_available": true
            }
        ],
        "total_results": 150,
        "page": 1,
        "page_size": 10,
        "total_pages": 15
    }
    ```
    """
    try:
        if query.isdigit():
            query = get_product_name_from_id(query, api_key)
            if query == "":
                raise Exception("No product found from the query ID")
        results, total_results, total_pages = await perform_search(
            query,
            page_size,
            page,
            credentials,
            category=cat,
            lo_price=lo_price,
            hi_price=hi_price,
        )
        return {
            "query": query,
            "results": results,
            "total_results": total_results,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Search operation failed: {str(e)}"
        )


@app.get(
    "/api/wp/search-by-text",
    response_model=FlatsomeResponse,
    responses={
        200: {"description": "Successful search results in Flatsome format"},
        400: {"model": ErrorResponse, "description": "Invalid query or parameters"},
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Search operation failed"},
    },
)
async def search_products_wp(
    query: str = Query(
        ...,
        description="Search query text (supports both Thai and English)",
        examples="เสื้อผ้าผู้ชาย",
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
    ),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        description="Number of results per page",
        ge=1,
        le=MAX_PAGE_SIZE,
    ),
    page: int = Query(
        1,
        description="Page number (1-based)",
        ge=1,
    ),
    cat: str = Query(
        None,
        description="Category filter to narrow down search results. Matches any level in category hierarchy.",
        examples="ผู้หญิง",
    ),
    lo_price: float = Query(
        None,
        description="Minimum price filter (inclusive). Uses sale_price if available, otherwise regular_price.",
        examples=1000,
        ge=0,
    ),
    hi_price: float = Query(
        None,
        description="Maximum price filter (inclusive). Uses sale_price if available, otherwise regular_price.",
        examples=5000,
        ge=0,
    ),
    api_key: str = Depends(validate_api_key),
):
    """
    WordPress WooCommerce Flatsome theme specific search endpoint

    This endpoint returns search results in the format expected by the Flatsome theme's
    WooCommerce product search functionality. It's specifically designed for integration
    with WordPress sites using the Flatsome theme.

    Features:
    - Compatible with Flatsome theme's AJAX search
    - Formatted price display with HTML
    - Support for sale prices
    - Out of stock handling
    - Category filtering
    - Price range filtering
    - Pagination support

    Parameters:
    - query: The search text to find products (Thai or English)
    - page_size: Number of results per page (1-{MAX_PAGE_SIZE})
    - page: Page number to retrieve (1-based)
    - cat: Optional category filter (matches any level in category hierarchy)
    - lo_price: Optional minimum price filter (inclusive)
    - hi_price: Optional maximum price filter (inclusive)
    - X-API-Key: API key for authentication (header)

    Returns:
    - List of suggestions in Flatsome theme format including:
        - Product type
        - Product ID
        - Product name
        - Product URL
        - Image URL
        - Formatted price HTML
    - Pagination metadata:
        - Current page number
        - Page size
        - Total results count
        - Total pages count

    Examples:
    - Thai query: /api/wp/search-by-text?query=เสื้อผ้าผู้ชาย
    - English query: /api/wp/search-by-text?query=men's clothing
    - With pagination: /api/wp/search-by-text?query=เสื้อผ้าผู้ชาย&page=2&page_size=20
    - With category filter: /api/wp/search-by-text?query=รองเท้า&cat=ผู้หญิง&page=1
    - With price range: /api/wp/search-by-text?query=รองเท้า&lo_price=3000&hi_price=9000&page=1
    - Combined filters: /api/wp/search-by-text?query=รองเท้า&cat=ผู้หญิง&lo_price=3000&hi_price=9000&page=2&page_size=15

    Category Filter Examples:
    - Category: "แฟชั่น, แฟชั่น > ผู้หญิง > กางเกงชั้นใน, แฟชั่น > ผู้หญิง"
    - Filter "ผู้หญิง" will match this product
    - Filter "แฟชั่น" will match this product
    - Filter "กางเกงชั้นใน" will match this product
    - Filter "ผู้ชาย" will NOT match this product

    Price Filter Examples:
    - Product with regular_price: "5000", sale_price: "" → Effective price: 5000
    - Product with regular_price: "5000", sale_price: "3500" → Effective price: 3500 (sale takes priority)
    - Filter lo_price=3000, hi_price=9000 → Includes products with effective price 3000-9000

    Response Example:
    ```json
    {
        "suggestions": [
            {
                "type": "Product",
                "id": 123,
                "value": "เสื้อเชิ้ตผู้ชาย",
                "url": "https://example.com/product/123",
                "img": "https://example.com/image.jpg",
                "price": "<span class=\"woocommerce-Price-amount amount\"><bdi>499&nbsp;<span class=\"woocommerce-Price-currencySymbol\">&#3647;</span></bdi></span>"
            }
        ],
        "total_results": 150,
        "page": 1,
        "page_size": 10,
        "total_pages": 15
    }
    ```
    """
    try:
        if query.isdigit():
            query = get_product_name_from_id(query, api_key)
            if query == "":
                raise Exception("No product found from the query ID")
        results, total_results, total_pages = await perform_search(
            query,
            page_size,
            page,
            credentials,
            category=cat,
            lo_price=lo_price,
            hi_price=hi_price,
        )
        return transform_to_flatsome_json(
            results, total_results, page, page_size, total_pages
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Search operation failed: {str(e)}"
        )


if __name__ == "__main__":
    # Run the FastAPI application using uvicorn
    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=int(APP_PORT),
        reload=bool(APP_AUTO_RELOAD),  # Enable auto-reload during development
        log_level=APP_LOG_LEVEL,
    )
