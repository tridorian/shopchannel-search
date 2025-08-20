from typing import Optional, Union
from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint"""
    message: str
    status: str


class ProductResponse(BaseModel):
    """Response model for individual product data"""
    id: str
    record_id: str
    product_number: str
    product_name: str
    image_uri: str
    description: str
    product_uri: str
    category: str
    brands: str
    regular_price: str
    sale_price: str
    is_available: bool


class ErrorResponse(BaseModel):
    """Response model for error cases"""
    detail: str 