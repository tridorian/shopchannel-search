import logging
import re
from typing import Optional, Dict, Any
from fastapi import HTTPException
from google.cloud import bigquery

from app.config import (
    GOOGLE_PROJECT_ID,
    GOOGLE_DATASET_ID,
    GOOGLE_TABLE_ID,
    MIN_ID_LENGTH,
    MAX_ID_LENGTH
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def sanitize_id(product_number: str) -> str:
    """Sanitize product number to prevent injection attacks"""
    try:
        # Remove any dangerous characters, keep only alphanumeric and safe characters including *
        product_number = re.sub(r"[^\w\-_*]", "", product_number)
        sanitized = product_number.strip()
        
        if not sanitized:
            raise ValueError("Empty ID after sanitization")
        
        if len(sanitized) < MIN_ID_LENGTH or len(sanitized) > MAX_ID_LENGTH:
            raise ValueError(f"ID length must be between {MIN_ID_LENGTH} and {MAX_ID_LENGTH} characters")
            
        return sanitized
    except Exception as e:
        logger.error(f"ID sanitization failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid ID format")


async def search_product_by_id(product_number: str, credentials) -> Optional[Dict[str, Any]]:
    """
    Search for a product by product_number in BigQuery
    
    Args:
        product_number: The product number to search for (e.g., "121552*006")
        credentials: GCP credentials for BigQuery access
        
    Returns:
        Dict containing product data if found, None if not found
        
    Raises:
        HTTPException: If search operation fails
    """
    try:
        # Sanitize the ID
        sanitized_id = sanitize_id(product_number)
        
        logger.info(f"Searching for product with product_number: {sanitized_id}")
        
        # Initialize BigQuery client
        client = bigquery.Client(credentials=credentials, project=GOOGLE_PROJECT_ID)
        
        # Construct the query
        table_ref = f"{GOOGLE_PROJECT_ID}.{GOOGLE_DATASET_ID}.{GOOGLE_TABLE_ID}"
        query = f"""
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
            FROM `{table_ref}`
            WHERE product_number = @product_number
            LIMIT 1
        """
        
        # Configure query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product_number", "STRING", sanitized_id)
            ]
        )
        
        # Execute the query
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()
        
        # Process the result
        for row in results:
            product_data = {
                "id": row.record_id or "",
                "record_id": row.record_id or "",
                "product_number": row.product_number or "",
                "product_name": row.product_name or "",
                "image_uri": row.image_uri or "",
                "description": row.description or "",
                "product_uri": row.custom_uri or "",
                "category": row.category or "",
                "brands": row.brands or "",
                "regular_price": row.regular_price or "",
                "sale_price": row.sale_price or "",
                "is_available": bool(row.is_available) if row.is_available is not None else False,
            }
            
            logger.info(f"Found product: {product_data['product_name']}")
            return product_data
        
        # No results found
        logger.info(f"No product found with product_number: {sanitized_id}")
        return None
        
    except Exception as e:
        logger.error(f"Search by ID failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search operation failed") 