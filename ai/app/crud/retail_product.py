from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.retail_product import RetailProduct
from app.schemas.retail_product import RetailProductCreate, RetailProductUpdate

def create_retail_product(db: Session, retail_product: RetailProductCreate) -> RetailProduct:
    """Create a new retail product"""
    db_retail_product = RetailProduct(**retail_product.dict())
    db.add(db_retail_product)
    db.commit()
    db.refresh(db_retail_product)
    return db_retail_product

def get_retail_product(db: Session, product_id: int) -> Optional[RetailProduct]:
    """Get retail product by ID"""
    return db.query(RetailProduct).filter(RetailProduct.id == product_id).first()

def get_retail_products(db: Session, skip: int = 0, limit: int = 100) -> List[RetailProduct]:
    """Get all retail products with pagination"""
    return db.query(RetailProduct).offset(skip).limit(limit).all()

def get_retail_products_by_session(db: Session, session_id: str, skip: int = 0, limit: int = 100) -> List[RetailProduct]:
    """Get retail products by session ID"""
    return db.query(RetailProduct).filter(RetailProduct.session_id == session_id).offset(skip).limit(limit).all()

def get_retail_products_by_retail(db: Session, retail_id: int, skip: int = 0, limit: int = 100) -> List[RetailProduct]:
    """Get retail products by retail ID"""
    return db.query(RetailProduct).filter(RetailProduct.retail_id == retail_id).offset(skip).limit(limit).all()

def get_latest_retail_product_by_retail_id(db: Session, retail_id: int) -> Optional[RetailProduct]:
    """Get the latest retail product by retail ID (ordered by created_at desc)"""
    return db.query(RetailProduct).filter(
        RetailProduct.retail_id == retail_id
    ).order_by(RetailProduct.created_at.desc()).first()

def update_retail_product(db: Session, product_id: int, retail_product_update: RetailProductUpdate) -> Optional[RetailProduct]:
    """Update retail product"""
    db_retail_product = get_retail_product(db, product_id)
    if not db_retail_product:
        return None
    
    update_data = retail_product_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_retail_product, field, value)
    
    db.commit()
    db.refresh(db_retail_product)
    return db_retail_product

def delete_retail_product(db: Session, product_id: int) -> bool:
    """Delete retail product"""
    db_retail_product = get_retail_product(db, product_id)
    if not db_retail_product:
        return False
    
    db.delete(db_retail_product)
    db.commit()
    return True

def search_retail_products(db: Session, search_term: str, skip: int = 0, limit: int = 100) -> List[RetailProduct]:
    """Search retail products by description"""
    return db.query(RetailProduct).filter(
        RetailProduct.description.contains(search_term)
    ).offset(skip).limit(limit).all()