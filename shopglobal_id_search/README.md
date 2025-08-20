# ShopChannel ID Search API

A FastAPI-based microservice that provides direct product lookup by product number from BigQuery. This service is designed for fast, exact-match retrieval of individual products using their unique product number identifier.

## Features

- **Direct BigQuery Access**: Fast single-row retrieval from BigQuery
- **Exact Match Search**: Precise product_number matching (no fuzzy search)
- **Input Sanitization**: Security measures to prevent injection attacks
- **API Key Authentication**: Secure endpoint access
- **Simple REST Design**: Returns product directly (200) or 404 if not found
- **Comprehensive Logging**: Request tracking and error monitoring
- **Docker Support**: Ready-to-use containerization
- **Cloud Run Ready**: Optimized for Google Cloud deployment

## Prerequisites

- Python 3.11+
- Google Cloud Platform account
- BigQuery access permissions
- Service account with BigQuery read permissions
- Docker (for containerized deployment)

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd shopglobal_id_search
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
   - Create a `.env` file in the project root
   - Fill in your configuration values:
     ```ini
     # Google Cloud Configuration
     GOOGLE_PROJECT_ID=your-project-id
     GOOGLE_DATASET_ID=your-dataset-id
     GOOGLE_TABLE_ID=your-table-id
     GOOGLE_APPLICATION_CREDENTIALS_JSON={"type": "service_account", ...}

     # API Security
     API_KEY=your-api-key
     CORS_ALLOW_ORIGINS=*

     # Query Configuration
     MIN_ID_LENGTH=1
     MAX_ID_LENGTH=20

     # Server Configuration
     APP_HOST=0.0.0.0
     APP_PORT=8080
     APP_AUTO_RELOAD=False
     APP_LOG_LEVEL=info
     ```

5. Configure GCP credentials:
   - Option 1: Set `GOOGLE_APPLICATION_CREDENTIALS_JSON` in `.env`
   - Option 2: Use default credential chain (for local development)

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

### Search by Product Number
```http
GET /api/search-by-id?id={product_number}
Headers:
  X-API-Key: your-api-key
```

Parameters:
- `id` (required): Product number to search for (1-20 characters, supports alphanumeric + * - _)

**Response (Found - 200):**
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

**Response (Not Found - 404):**
```json
{
    "detail": "Product not found"
}
```

## Usage Examples

```bash
# Search for existing product (returns 200 + product object)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8080/api/search-by-id?id=121552*006"

# Search for non-existing product (returns 404)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8080/api/search-by-id?id=INVALID123"

# Health check
curl "http://localhost:8080/"
```

## BigQuery Integration

The service queries BigQuery using the following structure:

```sql
SELECT 
    record_id,
    product_number,
    product_name,
    is_published,
    description,
    sale_start_date,
    sale_end_date,
    stock,
    sale_price,
    regular_price,
    category,
    brands,
    image_uri,
    custom_uri,
    is_product_variation,
    is_available
FROM `{project}.{dataset}.{table}`
WHERE product_number = @product_number
LIMIT 1
```

## Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t shopchannel-id-search .
   ```

2. Run the container:
   ```bash
   docker run -p 8080:8080 \
     -e GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}' \
     -e GOOGLE_PROJECT_ID=your-project-id \
     -e GOOGLE_DATASET_ID=your-dataset-id \
     -e GOOGLE_TABLE_ID=your-table-id \
     -e API_KEY=your-api-key \
     shopchannel-id-search
   ```

## Cloud Run Deployment

1. Build and push the container:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/shopchannel-id-search
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy shopchannel-id-search \
     --image gcr.io/YOUR_PROJECT_ID/shopchannel-id-search \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars="GOOGLE_PROJECT_ID=your-project-id,GOOGLE_DATASET_ID=your-dataset-id,GOOGLE_TABLE_ID=your-table-id,API_KEY=your-api-key"
   ```

## Security Considerations

- API key authentication is required for search endpoints
- Input sanitization prevents SQL injection attacks
- Product number length validation (1-20 characters)
- Parameterized queries for BigQuery safety
- CORS configuration for web application integration
- Supports special characters in product numbers (*-_)

## Error Handling

The API provides comprehensive error handling:

- **200 OK**: Product found and returned
- **400 Bad Request**: Invalid product number format or length
- **401 Unauthorized**: Missing API key
- **403 Forbidden**: Invalid API key
- **404 Not Found**: Product with specified number does not exist
- **500 Internal Server Error**: BigQuery or system errors

## Performance

- **Fast Lookup**: Direct BigQuery indexed lookup by product_number
- **Single Row**: LIMIT 1 for optimal performance
- **Parameterized Queries**: Prepared statements for efficiency
- **Lightweight**: Minimal processing overhead

## Monitoring

The service includes:
- Health check endpoint for load balancer monitoring
- Structured logging for request tracking
- Error logging for debugging
- Response time monitoring capabilities

## Product Number Format

The API supports product numbers with the following characters:
- Alphanumeric characters (a-z, A-Z, 0-9)
- Asterisk (*) - commonly used in product codes
- Hyphen (-) and underscore (_)
- Examples: `121552*006`, `PROD-001`, `item_123`

## Related Services

This microservice is part of the ShopChannel ecosystem:
- `shopglobal_text_search` - Full-text product search with filters
- `shopglobal_image_search` - AI-powered image analysis
- `shopglobal_line_chat` - Conversation logging

## API Testing

Use the FastAPI automatic documentation:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc` 