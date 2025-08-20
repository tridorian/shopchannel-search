# ShopChannel Image-Search API

A FastAPI-based service that uses Google's Gemini Pro Vision model to analyze images and generate descriptive captions. The service supports both Thai and English language responses and includes automatic image size optimization.

## Features

- **Image Analysis**: Extract meaningful captions from images using Gemini Pro Vision
- **Multi-language Support**: Generate responses in Thai or English
- **Image Size Optimization**: 
  - Automatic resizing of large images
  - Maintains aspect ratio
  - Configurable size limits and quality settings
- **API Key Authentication**: Secure your endpoints with API key validation
- **CORS Support**: Configurable CORS settings for web applications
- **Health Check Endpoint**: Monitor service status
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Docker Support**: Ready-to-use Docker configuration
- **Cloud Run Ready**: Optimized for Google Cloud Run deployment

## Prerequisites

- Python 3.9+
- Google Cloud Platform account
- Vertex AI API enabled
- Service account with appropriate permissions
- Docker (for containerized deployment)

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd shopglobal_image_search
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
     GOOGLE_APPLICATION_CREDENTIALS_JSON={"type": "service_account", ...}
     GOOGLE_PROJECT_ID=your-project-id
     GEMINI_API_LOCATION=global
     GEMINI_API_MODEL=gemini-2.0-flash-001

     # API Security
     API_KEY=your-api-key
     CORS_ALLOW_ORIGINS=*

     # Image Processing Configuration
     MAX_IMAGE_SIZE_MB=1.0
     TARGET_IMAGE_QUALITY=80

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

### Image Search
```http
POST /api/search-by-image
Headers:
  X-API-Key: your-api-key
Body:
{
    "base64_image": "base64_encoded_string",
    "lang": "th"  // or "en"
}
```
Response:
```json
{
    "text": "Generated caption",
    "lang": "th"
}
```

## Image Processing

The service automatically handles image size optimization:

1. **Size Check**: Images are checked against `MAX_IMAGE_SIZE_MB` (default: 1MB)
2. **Automatic Resizing**: If an image exceeds the size limit:
   - Maintains aspect ratio
   - Resizes to fit within the limit
   - Uses configured quality setting (`TARGET_IMAGE_QUALITY`, default: 80)
3. **Format Support**: Handles various image formats:
   - JPEG
   - PNG
   - WebP
   - GIF
   - BMP

## Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t shopchannel-image-search .
   ```

2. Run the container:
   ```bash
   docker run -p 8080:8080 \
     -e GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}' \
     -e GOOGLE_PROJECT_ID=your-project-id \
     -e API_KEY=your-api-key \
     shopchannel-image-search
   ```

## Cloud Run Deployment

1. Build and push the container:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/shopchannel-image-search
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy shopchannel-image-search \
     --image gcr.io/YOUR_PROJECT_ID/shopchannel-image-search \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars="GOOGLE_PROJECT_ID=your-project-id,API_KEY=your-api-key"
   ```
