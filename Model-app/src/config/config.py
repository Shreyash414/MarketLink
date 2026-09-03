"""
Centralized Configuration for SIH26132 Mandi Recommendation System.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Workspace Root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env if present
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR.parent / ".env")
load_dotenv()

# API Settings
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY")
API_RESOURCE_ID_CURRENT = "9ef84268-d588-465a-a308-a864a43d0070"
API_RESOURCE_ID_HISTORICAL = "35985678-0d79-46b4-9ed6-6f13308a1d24"
API_BASE_URL = "https://api.data.gov.in/resource/"

# Commodity Configuration
DEFAULT_COMMODITY = "Onion"

# Directories
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
CURRENT_DATA_DIR = PROCESSED_DATA_DIR / "current"
MODELS_BASE_DIR = PROCESSED_DATA_DIR / "models"

# File Paths (Backward Compatible defaults)
MARKET_METADATA_FILE = PROCESSED_DATA_DIR / "market_metadata.csv"
CURRENT_ONION_FILE = CURRENT_DATA_DIR / "onion_current.csv"
MODEL_DIR = MODELS_BASE_DIR / "change_xgboost_v3" / "final"


def get_current_data_file(commodity: str = DEFAULT_COMMODITY) -> Path:
    """Return path for processed current data for a specific commodity."""
    return CURRENT_DATA_DIR / f"{commodity.strip().lower()}_current.csv"


def get_model_dir(commodity: str = DEFAULT_COMMODITY, model_type: str = "change_xgboost_v3") -> Path:
    """
    Return directory where final model files are stored for a commodity.
    Preserves backward compatibility for Onion at models/change_xgboost_v3/final.
    """
    c_clean = commodity.strip().lower()
    if c_clean == "onion":
        return MODEL_DIR
    return MODELS_BASE_DIR / c_clean / model_type / "final"


# Economic Defaults
DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM = 3.0  # ₹ / quintal / km
DEFAULT_MARKET_FEE_PER_QUINTAL = 20.0        # ₹ / quintal

# API Request Defaults (current daily snapshot)
API_PAGE_LIMIT = 50
API_MAX_RETRIES = 2
API_CONNECT_TIMEOUT = 3
API_READ_TIMEOUT = 5

# Historical AGMARKNET resource is ~81M rows. Unfiltered or loosely
# filtered queries time out; targeted PascalCase filters succeed.
HIST_API_PAGE_LIMIT = 500
HIST_API_MAX_RETRIES = 5
HIST_API_CONNECT_TIMEOUT = 15
HIST_API_READ_TIMEOUT = 90
HIST_API_RETRY_STATUSES = (429, 502, 503, 504)
HIST_REQUEST_SLEEP_SEC = 1.0

# Training eligibility gates
MIN_VARIETY_GRADE_OBSERVATIONS = 60
MIN_MARKET_TRAINING_SESSIONS = 200
MIN_FEATURE_ROWS = 50
MAX_INVALID_PRICE_RATE = 0.30
MAX_DUPLICATE_RATE = 0.50
MAX_GAP_DAYS_RATIO = 0.85

# Data Reliability & Freshness Defaults (Task 8)
MAX_DATA_AGE_DAYS = 7                   # Days before CACHE is classified as CACHE_STALE
MIN_REQUIRED_HISTORY_SESSIONS = 31      # Minimum observed sessions required for 30-day V3 features
STALE_CACHE_ALLOWED_FOR_FARMER = True   # Whether STALE_CACHE is allowed in farmer-facing mode (with CACHE_STALE warning)



# Ensure essential directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_BASE_DIR.mkdir(parents=True, exist_ok=True)


