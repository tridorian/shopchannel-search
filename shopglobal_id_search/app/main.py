from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
from app.config import (
    CORS_ALLOW_ORIGINS,
    MIN_ID_LENGTH,
    MAX_ID_LENGTH,
    APP_HOST,
    APP_PORT,
    APP_AUTO_RELOAD,
    APP_LOG_LEVEL,
)
from app.authentications import validate_api_key, get_gcp_credentials
from app.utils import search_product_by_id
from app.data_store import HealthCheckResponse, ProductResponse, ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


########################################################
# FastAPI Setup
########################################################
app = FastAPI(
    title="ShopChannel Search-by-ID API",
    description="API for searching individual products by product_number from BigQuery. Returns exact matches for product lookup.",
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
    "/api/search-by-id",
    response_model=ProductResponse,
    responses={
        200: {"description": "Product found and returned"},
        400: {"model": ErrorResponse, "description": "Invalid ID parameter"},
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        404: {"model": ErrorResponse, "description": "Product not found"},
        500: {"model": ErrorResponse, "description": "Search operation failed"},
    },
)
async def search_by_id(
    id: str = Query(
        ...,
        description="Product number to search for",
        examples="121552*006",
        min_length=MIN_ID_LENGTH,
        max_length=MAX_ID_LENGTH,
    ),
    api_key: str = Depends(validate_api_key),
):
    """
    Search for a product by exact product number match

    This endpoint searches the BigQuery product database for an exact match
    on the product_number field. Returns the complete product information if found.

    Features:
    - Direct BigQuery lookup by product_number
    - Exact match search (no fuzzy matching)
    - Input sanitization for security
    - Fast single-row retrieval

    Parameters:
    - id: The product number to search for (must be {MIN_ID_LENGTH}-{MAX_ID_LENGTH} characters)
    - X-API-Key: API key for authentication (header)

    Returns:
    - Product object if found (200)
    - 404 error if not found

    Examples:
    - Found: /api/search-by-id?id=121552*006 → 200 + product object
    - Not found: /api/search-by-id?id=INVALID123 → 404

    Response Example (Found - 200):
    ```json
    {
        "id": "32987",
        "record_id": "32987",
        "product_number": "121552*006",
        "product_name": "รองเท้าหนังวัวแบบสลิปออน ตกแต่งสายคาดแบบถัก รุ่น Libby สำหรับผู้หญิง",
        "image_uri": "https://www.shopch.in.th/wp-content/uploads/2022/02/121552_01-1-1.webp",
        "description": "",
        "product_uri": "https://www.shopch.in.th/เซตเสอยดคอกลม-สพ-3",
        "category": "แฟชั่น > ผู้หญิง > รองเท้า",
        "brands": "AETREX",
        "regular_price": "3990",
        "sale_price": "",
        "is_available": true
    }
    ```

    Response Example (Not Found - 404):
    ```json
    {
        "detail": "Product not found"
    }
    ```
    """
    try:
        product_data = await search_product_by_id(id, credentials)

        if product_data:
            return ProductResponse(**product_data)
        else:
            raise HTTPException(status_code=404, detail="Product not found")

    except HTTPException:
        # Re-raise HTTP exceptions (like 404, 400)
        raise
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
