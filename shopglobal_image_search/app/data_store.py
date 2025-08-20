from pydantic import BaseModel, Field
from typing import Literal
import base64


########################################################
# Models
########################################################
class ImageInput(BaseModel):
    """Input model for image search request."""

    base64_image: str = Field(..., description="Base64 encoded image string")
    lang: Literal["th", "en"] = Field(
        default="th", description="Language for the response (th/en)"
    )

    def validate_base64(self) -> bool:
        """Validate if the base64 string is properly formatted."""
        try:
            base64.b64decode(self.base64_image)
            return True
        except Exception:
            return False

    class Config:
        json_schema_extra = {
            "example": {"base64_image": "base64_encoded_string_here", "lang": "th"}
        }


class ImageSearchResponse(BaseModel):
    text: str = Field(..., description="The caption of the image")
    lang: str = Field(..., description="The language of the caption")


class HealthCheckResponse(BaseModel):
    message: str = Field(..., description="Status message")
    status: str = Field(..., description="Health status")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
