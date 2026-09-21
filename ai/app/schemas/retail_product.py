from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.core.pydantic_config import BaseModelConfig

class RetailProductCreate(BaseModel, BaseModelConfig):
    # Pre-filled fields (not scraped)
    session_id: str
    retail_id: int
    
    # Fields to be scraped and recommended by GPT agent
    description: Optional[str] = None
    summary: Optional[str] = None
    price: Optional[Decimal] = None
    discount: Optional[Decimal] = Decimal('0')
    preparation: Optional[int] = None  # Preparation time in minutes
    count_type: Optional[int] = 0  # NUMERICAL=0, KILOGRAMS=1, GRAMS=2, METER=3, CENTIMETER=4, SHEKEL=5
    weight: Optional[int] = None  # Weight in grams
    weight_with_packaging: Optional[int] = None  # Weight with packaging in grams
    payk_delivery: Optional[int] = 0  # ACTIVE=0, INACTIVE=1
    post_delivery: Optional[int] = 0  # ACTIVE=0, INACTIVE=1
    coverage_area: Optional[int] = 0  # ACTIVE=0 (سراسر کشور), INACTIVE=1 (فقط شهر مبدا)
    
    # Additional fields for images
    image_1: Optional[str] = None
    image_2: Optional[str] = None
    image_3: Optional[str] = None

class RetailProductResponse(BaseModel, BaseModelConfig):
    # All fields including pre-filled ones
    id: int
    session_id: str
    retail_id: int
    status: int
    payment_method: int
    
    # Scraped and recommended fields
    description: Optional[str]
    summary: Optional[str]
    price: Optional[Decimal]
    discount: Decimal
    preparation: Optional[int]
    count_type: int
    weight: Optional[int]
    weight_with_packaging: Optional[int]
    payk_delivery: int
    post_delivery: int
    coverage_area: int
    
    # Image fields
    image_1: Optional[str]
    image_2: Optional[str]
    image_3: Optional[str]
    
    created_at: datetime
    updated_at: Optional[datetime]

class RetailProductUpdate(BaseModel, BaseModelConfig):
    # Only fields that can be updated by scraping/recommendation
    description: Optional[str] = None
    summary: Optional[str] = None
    price: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    preparation: Optional[int] = None
    count_type: Optional[int] = None
    weight: Optional[int] = None
    weight_with_packaging: Optional[int] = None
    payk_delivery: Optional[int] = None
    post_delivery: Optional[int] = None
    coverage_area: Optional[int] = None
    image_1: Optional[str] = None
    image_2: Optional[str] = None
    image_3: Optional[str] = None

class RetailProductRecommendation(BaseModel, BaseModelConfig):
    """Schema for GPT agent recommendations"""
    description: Optional[str] = None
    summary: Optional[str] = None
    price: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    preparation: Optional[int] = None
    count_type: Optional[int] = None
    weight: Optional[int] = None
    weight_with_packaging: Optional[int] = None
    payk_delivery: Optional[int] = None
    post_delivery: Optional[int] = None
    coverage_area: Optional[int] = None
    image_1: Optional[str] = None
    image_2: Optional[str] = None
    image_3: Optional[str] = None