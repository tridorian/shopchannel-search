import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables
APP_HOST = os.getenv("HOST", "0.0.0.0")
APP_PORT = os.getenv("PORT", "8080")
APP_AUTO_RELOAD = os.getenv("AUTO_RELOAD", "False")
APP_LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
GOOGLE_CREDENTIAL = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
# Google Cloud Configuration
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID_PROD", "prd-search-shg-api")
GOOGLE_DATASET_ID = os.getenv("GOOGLE_DATASET_ID_PROD", "shopchannel")
GOOGLE_TABLE_ID = os.getenv("GOOGLE_TABLE_ID", "products")
API_KEY = os.getenv("API_KEY", "tridorian-dummy-key")
GCP_CREDENTIALS_FILE = os.getenv(
    "GCP_CREDENTIALS_FILE_PROD",
    "./app/prd-search-shg-api-d3bc1167b44a.json",
)

# CORS Configuration
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")

# Query Configuration
MIN_ID_LENGTH = int(os.getenv("MIN_ID_LENGTH", "1"))
MAX_ID_LENGTH = int(os.getenv("MAX_ID_LENGTH", "10"))
