from dotenv import load_dotenv
import os
from google.oauth2 import service_account
from google.cloud import discoveryengine_v1

load_dotenv()

# Environment variables
APP_HOST = os.getenv("HOST", "0.0.0.0")
APP_PORT = os.getenv("PORT", "8080")
APP_AUTO_RELOAD = os.getenv("AUTO_RELOAD", "False")
APP_LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
GOOGLE_CREDENTIAL = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID_PROD", "prd-search-shg-api")
GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION", "global")
GOOGLE_ENGINE_ID = os.getenv(
    "GOOGLE_ENGINE_ID_PROD", "shopchannel-search_1750768887325"
)
SEARCH_SERVING_CONFIG = f"projects/{GOOGLE_PROJECT_ID}/locations/{GOOGLE_LOCATION}/collections/default_collection/engines/{GOOGLE_ENGINE_ID}/servingConfigs/default_search"
CORS_ALLOW_ORIGINS = os.getenv(
    "CORS_ALLOW_ORIGINS", "*"
)  # In production, replace with specific origins
API_KEY = os.getenv("API_KEY", "tridorian-dummy-key")
GCP_CREDENTIALS_FILE = os.getenv(
    "GCP_CREDENTIALS_FILE_PROD",
    "./app/prd-search-shg-api-d3bc1167b44a.json",
)
ID_SEARCH_URL = "https://shopchannel-id-search-891706886553.asia-southeast1.run.app/api/search-by-id"

# Constants
MAX_QUERY_LENGTH = 1000
MIN_QUERY_LENGTH = 1
MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 10
