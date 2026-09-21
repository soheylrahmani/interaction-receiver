from sqlalchemy import Column, Integer, String, Text, DateTime, DECIMAL, BigInteger, SmallInteger
from sqlalchemy.sql import func
from app.core.database import Base

class RetailProduct(Base):
    __tablename__ = "retail_products"
    
    # Pre-filled fields (not scraped)
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    retail_id = Column(BigInteger, nullable=False, index=True)
    status = Column(SmallInteger, default=0)  # WAITING=0, CONFIRMED=1, BLOCK=2
    payment_method = Column(SmallInteger, default=0)  # OFFLINE=0, ONLINE=1
    
    # Fields to be scraped and recommended by GPT agent
    description = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    price = Column(DECIMAL(14, 2), nullable=True)
    discount = Column(DECIMAL(14, 2), default=0)
    preparation = Column(BigInteger, nullable=True)  # Preparation time in minutes
    count_type = Column(SmallInteger, default=0)  # NUMERICAL=0, KILOGRAMS=1, GRAMS=2, METER=3, CENTIMETER=4, SHEKEL=5
    weight = Column(Integer, nullable=True)  # Weight in grams
    weight_with_packaging = Column(Integer, nullable=True)  # Weight with packaging in grams
    payk_delivery = Column(SmallInteger, default=0)  # ACTIVE=0, INACTIVE=1
    post_delivery = Column(SmallInteger, default=0)  # ACTIVE=0, INACTIVE=1
    coverage_area = Column(SmallInteger, default=0)  # ACTIVE=0 (سراسر کشور), INACTIVE=1 (فقط شهر مبدا)
    
    # Additional fields for images and inventory
    image_1 = Column(String(500), nullable=True)
    image_2 = Column(String(500), nullable=True)
    image_3 = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Constants matching Laravel model
    WAITING = 0
    CONFIRMED = 1
    BLOCK = 2
    
    NUMERICAL = 0
    KILOGRAMS = 1
    GRAMS = 2
    METER = 3
    CENTIMETER = 4
    SHEKEL = 5
    
    ACTIVE = 0
    INACTIVE = 1
    
    ONLINE = 1
    OFFLINE = 0 