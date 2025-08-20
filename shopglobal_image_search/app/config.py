import os
from dotenv import load_dotenv

load_dotenv()

# Environment variables
APP_HOST = os.getenv("HOST", "0.0.0.0")
APP_PORT = os.getenv("PORT", "8080")
APP_AUTO_RELOAD = os.getenv("AUTO_RELOAD", "False")
APP_LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
GOOGLE_CREDENTIAL = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID_PROD", "prd-search-shg-api")
GEMINI_API_LOCATION = os.getenv("GEMINI_API_LOCATION", "global")
GEMINI_API_MODEL = os.getenv("GEMINI_API_MODEL", "gemini-2.0-flash-001")
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")
API_KEY = os.getenv("API_KEY", "tridorian-dummy-key")
MAX_IMAGE_SIZE_MB = float(os.getenv("MAX_IMAGE_SIZE_MB", "1.0"))
TARGET_IMAGE_QUALITY = int(os.getenv("TARGET_IMAGE_QUALITY", "80"))
GCP_CREDENTIALS_FILE = os.getenv(
    "GCP_CREDENTIALS_FILE_PROD",
    "./app/prd-search-shg-api-d3bc1167b44a.json",
)
