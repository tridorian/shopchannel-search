from fastapi.security.api_key import APIKeyHeader
from fastapi import Depends, HTTPException
import os
import json
import logging
from app.config import API_KEY, GCP_CREDENTIALS_FILE, GOOGLE_CREDENTIAL
from google.oauth2 import service_account

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# API Key Configuration
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


########################################################
# Authentication
########################################################
def validate_api_key(api_key: str = Depends(api_key_header)) -> str:
    """Validate the API key from the request header."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key is missing")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


########################################################
# GCP Setup
########################################################
def get_gcp_credentials():
    """Initialize and return GCP credentials."""
    try:
        # First: try to get credentials from environment
        if GOOGLE_CREDENTIAL:
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    info=json.loads(GOOGLE_CREDENTIAL),
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                if credentials.valid:
                    logger.info("Using GCP credentials from environment")
                    return credentials
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(
                    f"Failed to parse GCP credentials from environment: {str(e)}"
                )
        # If environment credentials not available, try local file
        if os.path.exists(GCP_CREDENTIALS_FILE):
            return service_account.Credentials.from_service_account_file(
                GCP_CREDENTIALS_FILE,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        raise ValueError("No valid GCP credentials found in environment or local file")
    except Exception as e:
        logger.error(f"Failed to initialize GCP credentials: {str(e)}")
        raise
