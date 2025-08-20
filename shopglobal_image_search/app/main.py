from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
from app.config import (
    CORS_ALLOW_ORIGINS,
    GOOGLE_PROJECT_ID,
    APP_HOST,
    APP_PORT,
    APP_AUTO_RELOAD,
    APP_LOG_LEVEL,
)
from app.authentications import validate_api_key, get_gcp_credentials
from app.utils import extract_caption_from_image
from app.data_store import (
    HealthCheckResponse,
    ImageSearchResponse,
    ImageInput,
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
    title="ShopChannel Image-Search API",
    description="API for extracting product context from images using Gemini Pro Vision.",
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
    logger.info("Successfully initialized GCP credentials")
except Exception as e:
    logger.error(f"Failed to initialize GCP credentials: {str(e)}")
    raise


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


@app.post(
    "/api/search-by-image",
    response_model=ImageSearchResponse,
    responses={
        200: {"description": "Successful extract image caption"},
        400: {"model": ErrorResponse, "description": "Invalid image format"},
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Image caption extraction failed"},
    },
)
async def search_by_image(
    payload: ImageInput, api_key: str = Depends(validate_api_key)
):
    """
    Image caption extraction using Gemini Pro Vision.
    Accepts base64-encoded image and returns a short caption.
    Language can be specified using the 'lang' parameter ('th' or 'en').

    Parameters:
    - base64_image: Base64 encoded image string
    - lang: Language of the caption (th/en)

    Returns:
    - text: The caption of the image
    - lang: The language of the caption

    Examples:
    ```json
    {
        "text": "รองเท้าสำหรับการทำงาน",
        "lang": "th"
    }
    ```
    """
    try:
        logger.info(f"Received image search request with language: {payload.lang}")

        if not payload.base64_image:
            logger.error("No image provided in request")
            raise HTTPException(status_code=400, detail="No image provided")

        if not payload.validate_base64():
            logger.error("Invalid base64 image format")
            raise HTTPException(status_code=400, detail="Invalid base64 image format")

        logger.info("Processing image with Gemini Pro Vision")
        caption = extract_caption_from_image(
            payload.base64_image, GOOGLE_PROJECT_ID, payload.lang, credentials
        )
        logger.info(f"Successfully generated caption: {caption}")

        return {"text": caption, "lang": payload.lang}
    except Exception as e:
        logger.error(f"Image analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")


if __name__ == "__main__":
    # Run the FastAPI application using uvicorn
    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=int(APP_PORT),
        reload=bool(APP_AUTO_RELOAD),  # Enable auto-reload during development
        log_level=APP_LOG_LEVEL,
    )
