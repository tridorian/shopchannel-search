import logging
from fastapi import HTTPException
import base64
import logging
from typing import Tuple
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
from PIL import Image
import io
from app.config import (
    TARGET_IMAGE_QUALITY,
    MAX_IMAGE_SIZE_MB,
    GEMINI_API_LOCATION,
    GEMINI_API_MODEL
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


########################################################
# Functions
########################################################
def get_image_size_mb(base64_image: str) -> float:
    """Calculate approximate image size in MB from base64 string."""
    size_mb = (len(base64_image) * 0.75) / (1024 * 1024)
    logger.info(f"Base64 string length: {len(base64_image)} bytes")
    logger.info(f"Approximate image size: {size_mb:.2f}MB")
    return size_mb


def get_mime_type(image_format: str) -> str:
    """Get MIME type for image format."""
    mime_types = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "GIF": "image/gif",
        "BMP": "image/bmp",
    }
    return mime_types.get(image_format.upper(), "image/jpeg")


def resize_image_if_needed(
    image_data: bytes, max_size_mb: float = MAX_IMAGE_SIZE_MB
) -> Tuple[bytes, str]:
    """
    Resize image if it's larger than max_size_mb.
    Returns tuple of (resized image data in bytes, mime type).
    """
    try:
        # Convert bytes to image
        image = Image.open(io.BytesIO(image_data))
        original_format = image.format or "JPEG"
        original_size = len(image_data)
        logger.info(f"Original image format: {original_format}")
        logger.info(f"Original image dimensions: {image.size}")
        logger.info(f"Original image size: {original_size / (1024 * 1024):.2f}MB")

        # Calculate new dimensions while maintaining aspect ratio
        max_size_bytes = max_size_mb * 1024 * 1024
        ratio = (max_size_bytes / original_size) ** 0.5
        new_size = tuple(int(dim * ratio) for dim in image.size)
        logger.info(f"Resizing image to {new_size}")

        # Resize image
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format=original_format, quality=TARGET_IMAGE_QUALITY)

        resized_data = output.getvalue()
        final_size = len(resized_data)
        logger.info(f"Final image size: {final_size / (1024 * 1024):.2f}MB")

        mime_type = get_mime_type(original_format)
        logger.info(f"Final image format: {original_format} (MIME: {mime_type})")
        return resized_data, mime_type

    except Exception as e:
        logger.error(f"Error resizing image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")


def extract_caption_from_image(
    base64_image: str, project_id: str, lang: str = "th", credentials: str = None
) -> str:
    """Extract caption from image using Gemini Pro Vision model."""
    try:
        # Check image size from base64 string
        image_size_mb = get_image_size_mb(base64_image)

        # Decode base64 to bytes
        image_data = base64.b64decode(base64_image)
        mime_type = "image/jpeg"  # Default mime type

        # Resize if needed
        if image_size_mb > MAX_IMAGE_SIZE_MB:
            logger.info(
                f"Image size {image_size_mb:.2f}MB exceeds limit {MAX_IMAGE_SIZE_MB}MB, resizing..."
            )
            image_data, mime_type = resize_image_if_needed(image_data)

        logger.info(
            f"Initializing Vertex AI with project: {project_id}, location: {GEMINI_API_LOCATION}"
        )
        vertexai.init(
            project=project_id, location=GEMINI_API_LOCATION, credentials=credentials
        )

        logger.info(f"Loading model: {GEMINI_API_MODEL}")
        model = GenerativeModel(GEMINI_API_MODEL)

        image_part = Part.from_data(mime_type=mime_type, data=image_data)

        prompt = (
            "From the image, detect and describe only the primary object or product that a human might want to find, use, or purchase. "
            "The item can be wearable, usable, consumable, or any object typically found in daily life. "
            "It doesn't need to be a brand-name product or something sold in major shopping malls — it can be a common item such as a plastic cup, pen, towel, or anything else practical. "
            "Avoid describing background, scenery, or people. "
            "Describe only the main product in a short, human-friendly phrase that someone might use when searching online."
        )
        prompt += (
            " Please respond in Thai language only."
            if lang == "th"
            else " Please respond in English language only."
        )

        logger.info(f"Generating content with model in {lang} language")
        response = model.generate_content([prompt, image_part])
        caption = response.text.strip() if response.text else ""

        # Normalize to lowercase for fallback check
        caption_lower = caption.lower()
        fallback_phrases = [
            "ฉันขอโทษ", "ไม่เห็นผลิตภัณฑ์", "ไม่พบสินค้า", 
            "sorry", "can't identify", "nothing in this image",
        ]
        # Check if it cannot detect any product in the image
        if any(fallback in caption_lower for fallback in fallback_phrases):
            caption = ""  # Return empty

        logger.info("Successfully generated response")
        return caption
    except Exception as e:
        logger.error(f"Failed to extract caption: {str(e)}", exc_info=True)
        raise
