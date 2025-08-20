# ShopChannel Text Search API

A FastAPI-based search service that integrates with Google Vertex AI Search to provide product search functionality. The service supports both Thai and English queries and can return results in either a general format or a WordPress WooCommerce Flatsome theme-specific format.

## Features

- **Natural Language Search**: Advanced product search using Google Vertex AI Search
- **Multi-language Support**: 
  - Thai and English query support
  - Automatic language detection
  - Spell correction and query expansion
- **Category Filtering**:
  - Post-search category filtering
  - Hierarchical category matching
  - Flexible category level matching
- **Price Range Filtering**:
  - Filter products by minimum and maximum price
  - Smart price selection (sale_price takes priority over regular_price)
  - Flexible range filtering (can specify only min or max)
- **WordPress Integration**: 
  - WooCommerce Flatsome theme compatibility
  - Customizable result format
- **Performance Features**:
  - Configurable page size
  - Response caching
  - Query optimization
- **Security**:
  - API key authentication
  - CORS support
  - Input sanitization
- **Monitoring**:
  - Health check endpoint
  - Request logging
  - Error tracking
- **Deployment**:
  - Docker support
  - Cloud Run ready
  - Environment-based configuration

## Prerequisites

- Python 3.11+
- Google Cloud Platform account
- Vertex AI Search enabled
- Service account with appropriate permissions
- Docker (for containerized deployment)

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd shopglobal_text_search
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your configuration values:
     ```ini
     # Google Cloud Configuration
     GOOGLE_PROJECT_ID=your-project-id
     GOOGLE_LOCATION=global
     GOOGLE_ENGINE_ID=your-engine-id
     GOOGLE_APPLICATION_CREDENTIALS_JSON={"type": "service_account", ...}

     # API Security
     API_KEY=your-api-key
     CORS_ALLOW_ORIGINS=*

     # Search Configuration
     DEFAULT_PAGE_SIZE=10
     MAX_PAGE_SIZE=50

     # Server Configuration
     PORT=8080
     ```

5. Configure GCP credentials:
   - Option 1: Set `GOOGLE_APPLICATION_CREDENTIALS_JSON` in `.env`
   - Option 2: Place your service account JSON file as `credentials_gcp_local.json`

## Local Development

Run the application locally:
```bash
uvicorn app.main:app --reload --port 8080
```

The API will be available at `http://localhost:8080`

## API Documentation

### Health Check
```http
GET /
```
Response:
```json
{
    "message": "ok",
    "status": "healthy"
}
```

### General Search
```http
GET /api/search-by-text?query={search_text}&page={page_number}&page_size={page_size}&cat={category_filter}&lo_price={min_price}&hi_price={max_price}
Headers:
  X-API-Key: your-api-key
```

Parameters:
- `query` (required): Search query text (Thai or English)
- `page` (optional): Page number to retrieve (1-based, default: 1)
- `page_size` (optional): Number of results per page (default: 10, max: 50)
- `cat` (optional): Category filter to narrow down results
- `lo_price` (optional): Minimum price filter (inclusive)
- `hi_price` (optional): Maximum price filter (inclusive)

Price Filter Logic:
- Uses `sale_price` if it exists and is valid (not empty, not "0")
- Falls back to `regular_price` if `sale_price` is not available
- Filters products where `lo_price` ≤ effective_price ≤ `hi_price`

Category Filter Examples:
```
Category: "แฟชั่น, แฟชั่น > ผู้หญิง > กางเกงชั้นใน, แฟชั่น > ผู้หญิง"

- Filter "ผู้หญิง" → ✅ Match (found in hierarchy)
- Filter "แฟชั่น" → ✅ Match (found at top level)
- Filter "กางเกงชั้นใน" → ✅ Match (found in sub-category)
- Filter "ผู้ชาย" → ❌ No match
```

Response:
```json
{
    "query": "รองเท้า",
    "results": [
        {
            "id": "product_id",
            "record_id": "32987",
            "product_number": "121552*006",
            "product_name": "รองเท้าหนังวัวแบบสลิปออน",
            "image_uri": "https://example.com/image.jpg",
            "description": "รองเท้าหนังวัวแบบสลิปออน...",
            "product_uri": "https://example.com/product/121552",
            "category": "แฟชั่น > ผู้หญิง > รองเท้า",
            "brands": "AETREX",
            "regular_price": "3990",
            "sale_price": "",
            "is_available": true
        }
    ],
    "total_results": 150,
    "page": 1,
    "page_size": 10,
    "total_pages": 15
}
```

### WordPress Search
```http
GET /api/wp/search-by-text?query={search_text}&page={page_number}&page_size={page_size}&cat={category_filter}&lo_price={min_price}&hi_price={max_price}
Headers:
  X-API-Key: your-api-key
```

Parameters:
- `query` (required): Search query text (Thai or English)
- `page` (optional): Page number to retrieve (1-based, default: 1)
- `page_size` (optional): Number of results per page (default: 10, max: 50)
- `cat` (optional): Category filter to narrow down results
- `lo_price` (optional): Minimum price filter (inclusive)
- `hi_price` (optional): Maximum price filter (inclusive)

Response:
```json
{
    "suggestions": [
        {
            "type": "Product",
            "id": 121552,
            "value": "รองเท้าหนังวัวแบบสลิปออน",
            "url": "https://example.com/product/121552",
            "img": "https://example.com/image.jpg",
            "price": "<span class=\"woocommerce-Price-amount amount\"><bdi>3,990.00&nbsp;<span class=\"woocommerce-Price-currencySymbol\">&#3647;</span></bdi></span>"
        }
    ],
    "total_results": 150,
    "page": 1,
    "page_size": 10,
    "total_pages": 15
}
```

## Search Features

The service provides advanced search capabilities:

1. **Language Detection**:
   - Automatic detection of Thai and English queries
   - Language-specific search optimization
   - Cross-language result support

2. **Query Enhancement**:
   - Spell correction
   - Synonym expansion
   - Common typo handling

3. **Category Filtering**:
   - Post-search filtering by category
   - Hierarchical category structure support
   - Case-insensitive matching
   - Multiple category path support

4. **Price Range Filtering**:
   - Smart price detection (sale_price > regular_price priority)
   - Range filtering with inclusive bounds
   - Support for partial ranges (only min or only max)
   - Automatic handling of invalid price data

5. **Result Formatting**:
   - General JSON format for API integration
   - WordPress WooCommerce Flatsome theme format
   - Customizable result fields

6. **Pagination Support**:
   - Page-based navigation with 1-based indexing
   - Configurable page size (1-50 items per page)
   - Total results and total pages metadata
   - Efficient offset-based pagination

### Pagination Usage Examples

```bash
# Get first page (default)
GET /api/search-by-text?query=รองเท้า

# Get specific page with custom page size
GET /api/search-by-text?query=รองเท้า&page=2&page_size=20

# Navigate through pages
GET /api/search-by-text?query=เสื้อผ้า&page=1&page_size=15
GET /api/search-by-text?query=เสื้อผ้า&page=2&page_size=15
GET /api/search-by-text?query=เสื้อผ้า&page=3&page_size=15

# WordPress endpoint with pagination
GET /api/wp/search-by-text?query=รองเท้า&page=1&page_size=10
```

### Category Filter Usage Examples

```bash
# Search for shoes in women's category
GET /api/search-by-text?query=รองเท้า&cat=ผู้หญิง&page=1

# Search for jewelry with brand filter and pagination
GET /api/search-by-text?query=เครื่องประดับ&cat=ต่างหู&page=1&page_size=20

# WordPress endpoint with category filter
GET /api/wp/search-by-text?query=เสื้อผ้า&cat=แฟชั่น&page=1
```

### Price Filter Usage Examples

```bash
# Search for products in price range 3000-9000
GET /api/search-by-text?query=รองเท้า&lo_price=3000&hi_price=9000&page=1

# Search for products under 5000 with pagination
GET /api/search-by-text?query=เสื้อผ้า&hi_price=5000&page=2&page_size=25

# Search for products over 10000
GET /api/search-by-text?query=เครื่องประดับ&lo_price=10000&page=1

# Combined category, price, and pagination filters
GET /api/search-by-text?query=รองเท้า&cat=ผู้หญิง&lo_price=3000&hi_price=9000&page=1&page_size=12

# WordPress endpoint with price filter and pagination
GET /api/wp/search-by-text?query=เสื้อผ้า&lo_price=1000&hi_price=5000&page=1&page_size=8
```

### Combined Usage Examples

```bash
# Complex search with all filters
GET /api/search-by-text?query=รองเท้าผู้หญิง&cat=ผู้หญิง&lo_price=2000&hi_price=8000&page=1&page_size=20

# Multi-page browsing with filters
GET /api/search-by-text?query=เสื้อผ้า&cat=แฟชั่น&hi_price=3000&page=1&page_size=15
GET /api/search-by-text?query=เสื้อผ้า&cat=แฟชั่น&hi_price=3000&page=2&page_size=15

# WordPress complex search
GET /api/wp/search-by-text?query=กระเป๋า&cat=ผู้หญิง&lo_price=1500&page=1&page_size=12
```

## Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t shopchannel-text-search .
   ```

2. Run the container:
   ```bash
   docker run -p 8080:8080 \
     -e GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}' \
     -e GOOGLE_PROJECT_ID=your-project-id \
     -e GOOGLE_ENGINE_ID=your-engine-id \
     -e API_KEY=your-api-key \
     shopchannel-text-search
   ```

## Cloud Run Deployment

1. Build and push the container:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/shopchannel-text-search
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy shopchannel-text-search \
     --image gcr.io/YOUR_PROJECT_ID/shopchannel-text-search \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars="GOOGLE_PROJECT_ID=your-project-id,GOOGLE_ENGINE_ID=your-engine-id,API_KEY=your-api-key"
   ```

## Security Considerations

- API key authentication is required for all endpoints
- Input sanitization is performed on search queries
- Page size is limited to prevent large result sets
- CORS is configurable through environment variables

