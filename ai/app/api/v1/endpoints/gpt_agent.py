"""
GPT Agent endpoint for analyzing scraped data and creating retail products
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
from pydantic import BaseModel

from app.core.database import get_db
from app.services.gpt_service import GPTService
from app.crud.user_interaction import get_latest_user_interaction_by_retail_id, update_user_interaction
from app.crud.retail_product import create_retail_product
from app.schemas.retail_product import RetailProductCreate
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize GPT service
gpt_service = GPTService()

class CreateProductRequest(BaseModel):
    client_recommendation: Optional[str] = None
    ai_model: Optional[str] = None

@router.post("/create-product/{retail_id}", response_model=Dict[str, Any])
async def create_retail_product_from_analysis(
    retail_id: int,
    request: CreateProductRequest,
    db: Session = Depends(get_db),
    avalai_model: str = Query("4o-mini", description="AvalAI model to use: '4o-mini' or '4o'")
):
    """
    Analyze scraped data and create retail product in one operation.
    Accepts client_recommendation and ai_model in request body to save to database.
    Priority: 1) Request data, 2) Database data, 3) Default values
    """
    try:
        logger.info(f"[create_retail_product_from_analysis] Creating product for retail_id: {retail_id}")
        
        # Get the latest user interaction for this retail_id
        interaction = get_latest_user_interaction_by_retail_id(db, retail_id)
        if not interaction:
            raise HTTPException(
                status_code=404,
                detail=f"No user interaction found for retail_id: {retail_id}"
            )
        
        # Check if HTML content exists
        html_content = getattr(interaction, 'html_content', None)
        if not html_content:
            raise HTTPException(
                status_code=404,
                detail=f"No HTML content found for retail_id: {retail_id}. Run scan endpoint first."
            )
        
        # Priority system for client_recommendation and ai_model
        # 1. First priority: Use values from request if provided
        # 2. Second priority: Use values from database if available
        # 3. Third priority: Use default values
        
        final_client_recommendation = None
        final_ai_model = None
        update_data = {}
        
        # Handle client_recommendation priority
        if request.client_recommendation is not None:
            # Priority 1: Use request value
            final_client_recommendation = request.client_recommendation
            update_data["client_recommendation"] = request.client_recommendation
            logger.info(f"[create_retail_product_from_analysis] Using client_recommendation from request: {len(request.client_recommendation)} characters")
        else:
            # Priority 2: Try to get from database
            db_client_recommendation = getattr(interaction, 'client_recommendation', None)
            if db_client_recommendation:
                final_client_recommendation = db_client_recommendation
                logger.info(f"[create_retail_product_from_analysis] Using client_recommendation from database: {len(db_client_recommendation)} characters")
            else:
                # Priority 3: Use empty string as default
                final_client_recommendation = ""
                logger.info(f"[create_retail_product_from_analysis] No client_recommendation found, using empty string")
        
        # Handle ai_model priority
        if request.ai_model is not None:
            # Priority 1: Use request value
            final_ai_model = request.ai_model
            update_data["ai_model"] = request.ai_model
            logger.info(f"[create_retail_product_from_analysis] Using ai_model from request: {request.ai_model}")
        else:
            # Priority 2: Try to get from database
            db_ai_model = getattr(interaction, 'ai_model', None)
            if db_ai_model:
                final_ai_model = db_ai_model
                logger.info(f"[create_retail_product_from_analysis] Using ai_model from database: {db_ai_model}")
            else:
                # Priority 3: Use default value
                final_ai_model = avalai_model
                logger.info(f"[create_retail_product_from_analysis] No ai_model found, using default: {avalai_model}")
        
        # Update interaction if we have new data to save
        if update_data:
            interaction = update_user_interaction(db, int(interaction.id), update_data)
            logger.info(f"[create_retail_product_from_analysis] Updated interaction {interaction.id} with new data")
        
        # Get actions
        actions = getattr(interaction, 'actions', None) or {}
        
        # Analyze the scraped data using GPT with final values
        recommendation, token_usage, gpt_raw_response, cost = await gpt_service.analyze_scraped_data(
            html_content=str(html_content),
            client_recommendation=str(final_client_recommendation),
            actions=actions if isinstance(actions, dict) else {},
            avalai_model=final_ai_model
        )

        # Update interaction with analysis metadata
        from datetime import datetime
        interaction.analysed_at = datetime.utcnow()
        interaction.ai_model = avalai_model
        interaction.token_used = token_usage.get("total_tokens")
        interaction.ai_costs = cost.get("total_cost")
        db.commit()
        db.refresh(interaction)
        
        # Create retail product from recommendation
        product_data = RetailProductCreate(
            session_id=str(interaction.session_id),
            retail_id=retail_id,
            description=recommendation.description,
            summary=recommendation.summary,
            price=recommendation.price,
            discount=recommendation.discount,
            preparation=recommendation.preparation,
            count_type=recommendation.count_type,
            weight=recommendation.weight,
            weight_with_packaging=recommendation.weight_with_packaging,
            payk_delivery=recommendation.payk_delivery,
            post_delivery=recommendation.post_delivery,
            coverage_area=recommendation.coverage_area,
            image_1=recommendation.image_1,
            image_2=recommendation.image_2,
            image_3=recommendation.image_3
        )
        
        # Create the product in database
        created_product = create_retail_product(db, product_data)
        
        logger.info(f"[create_retail_product_from_analysis] Product created successfully for retail_id: {retail_id}")
        
        return {
            "status": "success",
            "retail_id": retail_id,
            "message": "Product analyzed and created successfully",
            "saved_data": {
                "description": getattr(created_product, 'description', None),
                "summary": getattr(created_product, 'summary', None),
                "price": float(getattr(created_product, 'price', 0)) if getattr(created_product, 'price', None) else None,
                "discount": float(getattr(created_product, 'discount', 0)) if getattr(created_product, 'discount', None) else None,
                "preparation": getattr(created_product, 'preparation', None),
                "count_type": getattr(created_product, 'count_type', None),
                "weight": getattr(created_product, 'weight', None),
                "weight_with_packaging": getattr(created_product, 'weight_with_packaging', None),
                "payk_delivery": getattr(created_product, 'payk_delivery', None),
                "post_delivery": getattr(created_product, 'post_delivery', None),
                "coverage_area": getattr(created_product, 'coverage_area', None),
                "image_1": getattr(created_product, 'image_1', None),
                "image_2": getattr(created_product, 'image_2', None),
                "image_3": getattr(created_product, 'image_3', None)
            },
            "token_usage": token_usage,
            "gpt_raw_response": gpt_raw_response,
            "cost": cost
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[create_retail_product_from_analysis] Error creating product for retail_id {retail_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}") 