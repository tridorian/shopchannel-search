from pydantic import BaseModel, Field
from typing import List


class ProductBase(BaseModel):
    id: str = Field(..., description="Unique identifier of the product")
    record_id: str = Field(..., description="Record ID from the data source")
    product_number: str = Field(..., description="Product SKU or number")
    product_name: str = Field(..., description="Name of the product")
    image_uri: str = Field(..., description="URL of the product image")
    description: str = Field(..., description="Product description")
    product_uri: str = Field(..., description="URL to the product page")
    category: str = Field(..., description="Product category")
    brands: str = Field(..., description="Product brand(s)")
    regular_price: str = Field(..., description="Regular price of the product")
    sale_price: str = Field(..., description="Sale price of the product (if on sale)")
    is_available: bool = Field(..., description="Product availability status")


class SearchResponse(BaseModel):
    query: str = Field(..., description="The original search query")
    results: List[ProductBase] = Field(..., description="List of matching products")
    total_results: int = Field(..., description="Total number of results found")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of results per page")
    total_pages: int = Field(..., description="Total number of pages")


class FlatsomeSuggestion(BaseModel):
    type: str = Field(..., description="Type of suggestion (always 'Product')")
    id: int = Field(..., description="Product ID")
    value: str = Field(..., description="Product name")
    url: str = Field(..., description="Product URL")
    img: str = Field(..., description="Product image URL")
    price: str = Field(..., description="Formatted price HTML")


class FlatsomeResponse(BaseModel):
    suggestions: List[FlatsomeSuggestion] = Field(
        ..., description="List of product suggestions"
    )
    total_results: int = Field(..., description="Total number of results found")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of results per page")
    total_pages: int = Field(..., description="Total number of pages")


class HealthCheckResponse(BaseModel):
    message: str = Field(..., description="Status message")
    status: str = Field(..., description="Health status")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
