from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import logging
import os

from app.core.database import get_db
from app.services.scan_service import ScanService
from app.services.gpt_service import GPTService
from app.crud.user_interaction import (
    create_user_interaction,
    get_user_interaction_by_session_id,
    get_all_user_interactions,
    get_latest_user_interaction_by_retail_id,
    update_user_interaction,
)
from app.crud.retail_product import create_retail_product, get_latest_retail_product_by_retail_id
from app.schemas.retail_product import RetailProductCreate
from app.schemas.user_interaction import (
    UserInteractionCreate,
    UserInteractionResponse,
    ScanRequest,
    ScanResponse,
    UserInteractionBasicResponse,
    ScanAndAnalyzeRequest,
    ScanAndAnalyzeResponse,
    UpdateClientRecommendationRequest,
    UpdateClientRecommendationResponse,
    UserInteractionWithProductResponse,
)
from app.models.user_interaction import UserInteraction

router = APIRouter()
scan_service = ScanService()
gpt_service = GPTService()

@router.post("/scan", response_model=ScanResponse)
async def scan_and_filter_station(
    request: ScanRequest,
    db: Session = Depends(get_db)
):
    """
    Scan website by replaying user actions and prepare filtered HTML for GPT agent
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[scan endpoint] Starting scan for retail_id: {request.retail_id}")
        
        # Step 1: Find the latest user interaction for this retail_id
        original_interaction = get_latest_user_interaction_by_retail_id(db, request.retail_id)
        if not original_interaction:
            raise HTTPException(
                status_code=404, 
                detail=f"No user interaction found for retail_id: {request.retail_id}"
            )
        
        logger.info(f"[scan endpoint] Found interaction: {original_interaction.id}")
        logger.info(f"[scan endpoint] Original URL: {original_interaction.url}")
        logger.info(f"[scan endpoint] Actions to replay: {len(original_interaction.actions or [])}")
        
        # Step 1.5: Update the interaction with client_recommendation and ai_model if provided
        update_data = {}
        if request.client_recommendation is not None:
            update_data["client_recommendation"] = request.client_recommendation
            logger.info(f"[scan endpoint] Client recommendation provided: {len(request.client_recommendation)} characters")
        
        if request.ai_model is not None:
            update_data["ai_model"] = request.ai_model
            logger.info(f"[scan endpoint] AI model provided: {request.ai_model}")
        
        # Update the interaction if we have data to update
        if update_data:
            updated_interaction = update_user_interaction(db, int(original_interaction.id), update_data)
            logger.info(f"[scan endpoint] Updated interaction {original_interaction.id} with client data")
            # Use the updated interaction for the rest of the process
            original_interaction = updated_interaction
        
        # Step 2: Replay user actions
        actions = original_interaction.actions or []
        if not actions:
            logger.warning(f"[scan endpoint] No actions found for interaction {original_interaction.id}")
        
        replay_result = await scan_service.replay_user_actions(
            url=str(original_interaction.url),
            actions=actions
        )

        # If all actions failed or replay returned error, stop and return error
        if replay_result["status"] == "error" or replay_result.get("successful_actions", 0) == 0:
            logger.error(f"[scan endpoint] All actions failed or replay returned error: {replay_result.get('error', replay_result.get('message', 'Unknown error'))}")
            # Prepare detailed error info for client
            action_results = replay_result.get("action_results", [])
            failed_details = [
                f"#{r['action_index']} {r['action_type']} {r['selector']}: {r['error']}" for r in action_results if not r.get("success")
            ]
            detail_msg = f"Failed to replay actions. Errors: {failed_details if failed_details else replay_result.get('error', replay_result.get('message', 'All actions failed'))}"
            # Add more context for debugging
            debug_info = {
                "failed_actions": [
                    {
                        "index": r["action_index"],
                        "type": r["action_type"],
                        "selector": r["selector"],
                        "error": r["error"]
                    } for r in action_results if not r.get("success")
                ],
                "all_action_results": action_results
            }
            raise HTTPException(
                status_code=400,
                detail={
                    "message": detail_msg,
                    "debug": debug_info
                }
            )

        # Handle partial success (some actions failed)
        if replay_result["status"] == "partial_success":
            logger.warning(f"[scan endpoint] Partial success: {replay_result.get('message', 'Some actions failed')}")
            logger.warning(f"[scan endpoint] Successful actions: {replay_result.get('successful_actions', 0)}")
            logger.warning(f"[scan endpoint] Failed actions: {replay_result.get('failed_actions', 0)}")
            # Log detailed action results for debugging
            action_results = replay_result.get("action_results", [])
            for result in action_results:
                if not result.get("success"):
                    logger.warning(f"[scan endpoint] Failed action {result.get('action_index')}: {result.get('error')}")

        logger.info(f"[scan endpoint] Successfully replayed actions")
        logger.info(f"[scan endpoint] HTML content length: {len(replay_result.get('html_content', ''))}")
        
        # Step 3: Filter HTML content (lighter filtering)
        filtered_result = await scan_service.filter_html_content(
            html_content=replay_result.get("html_content", "")
        )
        
        if filtered_result["status"] == "error":
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to filter HTML content: {filtered_result['error']}"
            )
        
        logger.info(f"[scan endpoint] Successfully filtered HTML content")
        logger.info(f"[scan endpoint] Original HTML length: {filtered_result.get('original_length', 0)}")
        logger.info(f"[scan endpoint] Filtered HTML length: {filtered_result.get('filtered_length', 0)}")
        
        # Step 4: Update the interaction with filtered HTML content
        from datetime import datetime
        count_failed_action = replay_result.get('failed_actions', 0)
        update_data = {
            "html_content": filtered_result.get("filtered_html"),
            "count_failed_action": count_failed_action,
            "scanned_at": datetime.utcnow(),
        }
        
        updated_interaction = update_user_interaction(db, int(original_interaction.id), update_data)
        logger.info(f"[scan endpoint] Updated interaction {original_interaction.id}")
        
        logger.info(f"[scan endpoint] Scan completed successfully for retail_id: {request.retail_id}")
        
        return ScanResponse(
            retail_id=request.retail_id,
            status="success",
            message="Scan completed successfully",
            interaction_id=updated_interaction.id,
            html_content=updated_interaction.html_content,
            # Additional debug information
            original_url=original_interaction.url,
            actions_count=len(actions),
            html_content_length=len(updated_interaction.html_content or ""),
            original_html_length=filtered_result.get("original_length", 0),
            filtered_html_length=filtered_result.get("filtered_length", 0),
            # Action tracking information
            successful_actions=replay_result.get("successful_actions"),
            failed_actions=replay_result.get("failed_actions"),
            total_actions=replay_result.get("total_actions"),
            action_results=replay_result.get("action_results")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[scan endpoint] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/scan-and-analyze", response_model=ScanAndAnalyzeResponse)
async def scan_and_analyze_station(
    request: ScanAndAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Scan website by replaying user actions, then analyze with GPT agent in one operation.
    This combines the scan and GPT agent functionality into a single endpoint.
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[scan-and-analyze endpoint] Starting combined scan and analyze for retail_id: {request.retail_id}")
        
        # Step 1: Find the latest user interaction for this retail_id
        original_interaction = get_latest_user_interaction_by_retail_id(db, request.retail_id)
        if not original_interaction:
            raise HTTPException(
                status_code=404, 
                detail=f"No user interaction found for retail_id: {request.retail_id}"
            )
        
        logger.info(f"[scan-and-analyze endpoint] Found interaction: {original_interaction.id}")
        logger.info(f"[scan-and-analyze endpoint] Original URL: {original_interaction.url}")
        logger.info(f"[scan-and-analyze endpoint] Actions to replay: {len(original_interaction.actions or [])}")
        
        # Step 1.5: Update the interaction with client_recommendation and ai_model if provided
        update_data = {}
        if request.client_recommendation is not None:
            update_data["client_recommendation"] = request.client_recommendation
            logger.info(f"[scan-and-analyze endpoint] Client recommendation provided: {len(request.client_recommendation)} characters")
        
        if request.ai_model is not None:
            update_data["ai_model"] = request.ai_model
            logger.info(f"[scan-and-analyze endpoint] AI model provided: {request.ai_model}")
        
        # Update the interaction if we have data to update
        if update_data:
            updated_interaction = update_user_interaction(db, int(original_interaction.id), update_data)
            logger.info(f"[scan-and-analyze endpoint] Updated interaction {original_interaction.id} with client data")
            # Use the updated interaction for the rest of the process
            original_interaction = updated_interaction
        
        # Step 2: Replay user actions (SCAN PHASE)
        actions = original_interaction.actions or []
        if not actions:
            logger.warning(f"[scan-and-analyze endpoint] No actions found for interaction {original_interaction.id}")
        
        replay_result = await scan_service.replay_user_actions(
            url=str(original_interaction.url),
            actions=actions
        )

        # If all actions failed or replay returned error, stop and return error
        if replay_result["status"] == "error" or replay_result.get("successful_actions", 0) == 0:
            logger.error(f"[scan-and-analyze endpoint] All actions failed or replay returned error: {replay_result.get('error', replay_result.get('message', 'Unknown error'))}")
            # Prepare detailed error info for client
            action_results = replay_result.get("action_results", [])
            failed_details = [
                f"#{r['action_index']} {r['action_type']} {r['selector']}: {r['error']}" for r in action_results if not r.get("success")
            ]
            detail_msg = f"Failed to replay actions. Errors: {failed_details if failed_details else replay_result.get('error', replay_result.get('message', 'All actions failed'))}"
            # Add more context for debugging
            debug_info = {
                "failed_actions": [
                    {
                        "index": r["action_index"],
                        "type": r["action_type"],
                        "selector": r["selector"],
                        "error": r["error"]
                    } for r in action_results if not r.get("success")
                ],
                "all_action_results": action_results
            }
            raise HTTPException(
                status_code=400,
                detail={
                    "message": detail_msg,
                    "debug": debug_info
                }
            )

        # Handle partial success (some actions failed)
        if replay_result["status"] == "partial_success":
            logger.warning(f"[scan-and-analyze endpoint] Partial success: {replay_result.get('message', 'Some actions failed')}")
            logger.warning(f"[scan-and-analyze endpoint] Successful actions: {replay_result.get('successful_actions', 0)}")
            logger.warning(f"[scan-and-analyze endpoint] Failed actions: {replay_result.get('failed_actions', 0)}")
            # Log detailed action results for debugging
            action_results = replay_result.get("action_results", [])
            for result in action_results:
                if not result.get("success"):
                    logger.warning(f"[scan-and-analyze endpoint] Failed action {result.get('action_index')}: {result.get('error')}")

        logger.info(f"[scan-and-analyze endpoint] Successfully replayed actions")
        logger.info(f"[scan-and-analyze endpoint] HTML content length: {len(replay_result.get('html_content', ''))}")
        
        # Step 3: Filter HTML content (lighter filtering)
        filtered_result = await scan_service.filter_html_content(
            html_content=replay_result.get("html_content", "")
        )
        
        if filtered_result["status"] == "error":
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to filter HTML content: {filtered_result['error']}"
            )
        
        logger.info(f"[scan-and-analyze endpoint] Successfully filtered HTML content")
        logger.info(f"[scan-and-analyze endpoint] Original HTML length: {filtered_result.get('original_length', 0)}")
        logger.info(f"[scan-and-analyze endpoint] Filtered HTML length: {filtered_result.get('filtered_length', 0)}")
        
        # Step 4: Update the interaction with filtered HTML content
        from datetime import datetime
        count_failed_action = replay_result.get('failed_actions', 0)
        update_data = {
            "html_content": filtered_result.get("filtered_html"),
            "count_failed_action": count_failed_action,
            "scanned_at": datetime.utcnow(),
        }
        
        updated_interaction = update_user_interaction(db, int(original_interaction.id), update_data)
        logger.info(f"[scan-and-analyze endpoint] Updated interaction {original_interaction.id}")
        
        # Step 5: Analyze with GPT agent (ANALYZE PHASE)
        logger.info(f"[scan-and-analyze endpoint] Starting GPT analysis for retail_id: {request.retail_id}")
        
        # Priority system for client_recommendation and ai_model
        # 1. First priority: Use values from request if provided
        # 2. Second priority: Use values from database if available
        # 3. Third priority: Use default values
        
        final_client_recommendation = None
        final_ai_model = None
        gpt_update_data = {}
        
        # Handle client_recommendation priority
        if request.client_recommendation is not None:
            # Priority 1: Use request value
            final_client_recommendation = request.client_recommendation
            gpt_update_data["client_recommendation"] = request.client_recommendation
            logger.info(f"[scan-and-analyze endpoint] Using client_recommendation from request: {len(request.client_recommendation)} characters")
        else:
            # Priority 2: Try to get from database
            db_client_recommendation = getattr(updated_interaction, 'client_recommendation', None)
            if db_client_recommendation:
                final_client_recommendation = db_client_recommendation
                logger.info(f"[scan-and-analyze endpoint] Using client_recommendation from database: {len(db_client_recommendation)} characters")
            else:
                # Priority 3: Use empty string as default
                final_client_recommendation = ""
                logger.info(f"[scan-and-analyze endpoint] No client_recommendation found, using empty string")
        
        # Handle ai_model priority
        if request.ai_model is not None:
            # Priority 1: Use request value
            final_ai_model = request.ai_model
            gpt_update_data["ai_model"] = request.ai_model
            logger.info(f"[scan-and-analyze endpoint] Using ai_model from request: {request.ai_model}")
        else:
            # Priority 2: Try to get from database
            db_ai_model = getattr(updated_interaction, 'ai_model', None)
            if db_ai_model:
                final_ai_model = db_ai_model
                logger.info(f"[scan-and-analyze endpoint] Using ai_model from database: {db_ai_model}")
            else:
                # Priority 3: Use default value
                final_ai_model = request.avalai_model or "4o-mini"
                logger.info(f"[scan-and-analyze endpoint] No ai_model found, using default: {final_ai_model}")
        
        # Update interaction if we have new data to save
        if gpt_update_data:
            updated_interaction = update_user_interaction(db, int(updated_interaction.id), gpt_update_data)
            logger.info(f"[scan-and-analyze endpoint] Updated interaction {updated_interaction.id} with GPT data")
        
        # Get actions
        actions = getattr(updated_interaction, 'actions', None) or {}
        
        # Analyze the scraped data using GPT with final values
        recommendation, token_usage, gpt_raw_response, cost = await gpt_service.analyze_scraped_data(
            html_content=str(filtered_result.get("filtered_html")),
            client_recommendation=str(final_client_recommendation),
            actions=actions if isinstance(actions, dict) else {},
            avalai_model=final_ai_model
        )

        # Update interaction with analysis metadata
        updated_interaction.analysed_at = datetime.utcnow()
        updated_interaction.ai_model = final_ai_model
        updated_interaction.token_used = token_usage.get("total_tokens")
        updated_interaction.ai_costs = cost.get("total_cost")
        db.commit()
        db.refresh(updated_interaction)
        
        # Create retail product from recommendation
        product_data = RetailProductCreate(
            session_id=str(updated_interaction.session_id),
            retail_id=request.retail_id,
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
        
        logger.info(f"[scan-and-analyze endpoint] Product created successfully for retail_id: {request.retail_id}")
        
        # Prepare the response data
        response_data = ScanAndAnalyzeResponse(
            retail_id=request.retail_id,
            status="success",
            message="Scan and analysis completed successfully",
            interaction_id=updated_interaction.id,
            # Scan results
            html_content=updated_interaction.html_content,
            original_url=original_interaction.url,
            actions_count=len(actions),
            html_content_length=len(updated_interaction.html_content or ""),
            original_html_length=filtered_result.get("original_length", 0),
            filtered_html_length=filtered_result.get("filtered_length", 0),
            successful_actions=replay_result.get("successful_actions"),
            failed_actions=replay_result.get("failed_actions"),
            total_actions=replay_result.get("total_actions"),
            action_results=replay_result.get("action_results"),
            # GPT analysis results
            saved_data={
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
            token_usage=token_usage,
            gpt_raw_response=gpt_raw_response,
            cost=cost
        )
        
        # Step 6: Send callback if URL is provided
        callback_status = None
        callback_response = None
        
        if request.callback_url:
            logger.info(f"[scan-and-analyze endpoint] Sending callback to: {request.callback_url}")
            
            try:
                import httpx
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Convert response data to dict for JSON serialization
                    callback_payload = response_data.dict()
                    
                    # Send POST request to callback URL
                    response = await client.post(
                        request.callback_url,
                        json=callback_payload,
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "Interaction-Receiver/1.0"
                        }
                    )
                    
                    callback_status = "success" if response.status_code < 400 else "failed"
                    callback_response = {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": response.text[:1000] if response.text else None
                    }
                    
                    logger.info(f"[scan-and-analyze endpoint] Callback response status: {response.status_code}")
                    
                    if response.status_code >= 400:
                        logger.error(f"[scan-and-analyze endpoint] Callback failed: {response.text}")
                    else:
                        logger.info(f"[scan-and-analyze endpoint] Callback sent successfully")
                        
            except httpx.TimeoutException:
                callback_status = "timeout"
                logger.error(f"[scan-and-analyze endpoint] Callback timeout after 30 seconds")
            except httpx.RequestError as e:
                callback_status = "network_error"
                logger.error(f"[scan-and-analyze endpoint] Callback network error: {str(e)}")
            except Exception as e:
                callback_status = "error"
                logger.error(f"[scan-and-analyze endpoint] Callback unexpected error: {str(e)}")
        
        # Update response with callback information
        response_data.callback_url = request.callback_url
        response_data.callback_status = callback_status
        response_data.callback_response = callback_response
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[scan-and-analyze endpoint] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=list[UserInteractionResponse])
def get_interactions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all user interactions
    """
    interactions = get_all_user_interactions(db, skip=skip, limit=limit)
    return interactions


@router.get("/extension-download")
async def extension_download():
    """
    Download Chrome extension zip file.
    """
    file_path = "static/retail-action-recorder-chrome.zip"
    filename = "retail-action-recorder-chrome.zip"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Extension file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/zip",
    )


@router.post("/extension-action", response_model=UserInteractionBasicResponse)
async def extension_action(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receive and store/update user actions from the browser extension.
    Expects JSON: {retail_id or user_id, session_id, actions, url, client_recommendation (optional)}.
    interaction-tracker sends user_id; it is stored as retail_id.
    """
    data = await request.json()
    try:
        interaction_data = UserInteractionCreate(**data)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    retail_id = interaction_data.retail_id
    session_id = interaction_data.session_id
    client_recommendation = interaction_data.client_recommendation
    # Convert actions to dicts for JSON serializability, and ensure all datetimes are ISO strings
    def action_to_serializable_dict(a):
        d = a.dict() if hasattr(a, "dict") else dict(a)
        if isinstance(d.get("timestamp"), (str, type(None))):
            return d
        d["timestamp"] = d["timestamp"].isoformat()
        return d
    actions = [action_to_serializable_dict(a) for a in interaction_data.actions]
    url = interaction_data.url
    # Try to find existing interaction
    interaction = db.query(UserInteraction).filter_by(retail_id=retail_id, session_id=session_id).first()
    if interaction:
        prev_actions = interaction.actions or []
        prev_timestamps = {a.get("timestamp") for a in prev_actions if "timestamp" in a}
        new_actions = [a for a in actions if a.get("timestamp") not in prev_timestamps]
        interaction.actions = sorted(prev_actions + new_actions, key=lambda a: a.get("timestamp"))
        if url:
            interaction.url = url
        # Update client_recommendation if provided
        if client_recommendation is not None:
            interaction.client_recommendation = client_recommendation
        # Update captured_at and count_action if new actions are added
        if new_actions:
            # Get the latest timestamp from all actions
            latest_action_time = max(a.get("timestamp") for a in interaction.actions if a.get("timestamp"))
            from datetime import datetime
            # Parse ISO string if needed
            if isinstance(latest_action_time, str):
                try:
                    latest_action_time_dt = datetime.fromisoformat(latest_action_time)
                except Exception:
                    latest_action_time_dt = None
            else:
                latest_action_time_dt = latest_action_time
            interaction.captured_at = latest_action_time_dt
            # Count all actions
            interaction.count_action = len(interaction.actions)
    else:
        interaction_data.actions = actions
        # Set captured_at and count_action for new interaction
        from datetime import datetime
        latest_action_time = max((a.get("timestamp") for a in actions if a.get("timestamp")), default=None)
        if isinstance(latest_action_time, str):
            try:
                latest_action_time_dt = datetime.fromisoformat(latest_action_time)
            except Exception:
                latest_action_time_dt = None
        else:
            latest_action_time_dt = latest_action_time
        interaction = create_user_interaction(db, interaction_data)
        interaction.captured_at = latest_action_time_dt
        interaction.count_action = len(actions)
        # Set client_recommendation for new interaction if provided
        if client_recommendation is not None:
            interaction.client_recommendation = client_recommendation
    db.commit()
    db.refresh(interaction)
    return UserInteractionBasicResponse.from_orm(interaction)


@router.get("/by-session-id/{session_id}", response_model=UserInteractionWithProductResponse)
def get_interaction_by_session_id(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user interaction by session ID along with latest retail product data
    """
    interaction = get_user_interaction_by_session_id(db, session_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    # Get the latest retail product for this retail_id
    retail_product = get_latest_retail_product_by_retail_id(db, interaction.retail_id)
    
    # Prepare retail product data if exists
    retail_product_data = None
    if retail_product:
        retail_product_data = {
            "id": retail_product.id,
            "session_id": retail_product.session_id,
            "retail_id": retail_product.retail_id,
            "status": retail_product.status,
            "payment_method": retail_product.payment_method,
            "description": retail_product.description,
            "summary": retail_product.summary,
            "price": float(retail_product.price) if retail_product.price else None,
            "discount": float(retail_product.discount) if retail_product.discount else None,
            "preparation": retail_product.preparation,
            "count_type": retail_product.count_type,
            "weight": retail_product.weight,
            "weight_with_packaging": retail_product.weight_with_packaging,
            "payk_delivery": retail_product.payk_delivery,
            "post_delivery": retail_product.post_delivery,
            "coverage_area": retail_product.coverage_area,
            "image_1": retail_product.image_1,
            "image_2": retail_product.image_2,
            "image_3": retail_product.image_3,
            "created_at": retail_product.created_at,
            "updated_at": retail_product.updated_at
        }
    
    return UserInteractionWithProductResponse(
        user_interaction=interaction,
        retail_product=retail_product_data
    )

@router.get("/by-retail-id/{retail_id}", response_model=UserInteractionWithProductResponse)
def get_gpt_ready_data_by_retail_id(
    retail_id: int,
    db: Session = Depends(get_db)
):
    """
    Get complete user interaction data for GPT processing along with latest retail product data
    """
    interaction = get_latest_user_interaction_by_retail_id(db, retail_id)
    if not interaction:
        raise HTTPException(
            status_code=404, 
            detail=f"No user interaction found for retail_id: {retail_id}"
        )
    
    # Get the latest retail product for this retail_id
    retail_product = get_latest_retail_product_by_retail_id(db, retail_id)
    
    # Prepare retail product data if exists
    retail_product_data = None
    if retail_product:
        retail_product_data = {
            "id": retail_product.id,
            "session_id": retail_product.session_id,
            "retail_id": retail_product.retail_id,
            "status": retail_product.status,
            "payment_method": retail_product.payment_method,
            "description": retail_product.description,
            "summary": retail_product.summary,
            "price": float(retail_product.price) if retail_product.price else None,
            "discount": float(retail_product.discount) if retail_product.discount else None,
            "preparation": retail_product.preparation,
            "count_type": retail_product.count_type,
            "weight": retail_product.weight,
            "weight_with_packaging": retail_product.weight_with_packaging,
            "payk_delivery": retail_product.payk_delivery,
            "post_delivery": retail_product.post_delivery,
            "coverage_area": retail_product.coverage_area,
            "image_1": retail_product.image_1,
            "image_2": retail_product.image_2,
            "image_3": retail_product.image_3,
            "created_at": retail_product.created_at,
            "updated_at": retail_product.updated_at
        }
    
    return UserInteractionWithProductResponse(
        user_interaction=interaction,
        retail_product=retail_product_data
    )

@router.put("/update-client-recommendation", response_model=UpdateClientRecommendationResponse)
async def update_client_recommendation_and_link(
    request: UpdateClientRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    Update client recommendation and/or link for a specific retail_id
    Finds the latest user interaction for the given retail_id and updates it
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[update-client-recommendation endpoint] Starting update for retail_id: {request.retail_id}")
        
        # Step 1: Find the latest user interaction for this retail_id
        original_interaction = get_latest_user_interaction_by_retail_id(db, request.retail_id)
        if not original_interaction:
            raise HTTPException(
                status_code=404, 
                detail=f"No user interaction found for retail_id: {request.retail_id}"
            )
        
        logger.info(f"[update-client-recommendation endpoint] Found interaction: {original_interaction.id}")
        logger.info(f"[update-client-recommendation endpoint] Original URL: {original_interaction.url}")
        
        # Step 2: Prepare update data
        update_data = {}
        updated_fields = {}
        
        if request.client_recommendation is not None:
            update_data["client_recommendation"] = request.client_recommendation
            updated_fields["client_recommendation"] = f"{len(request.client_recommendation)} characters"
            logger.info(f"[update-client-recommendation endpoint] Will update client_recommendation: {len(request.client_recommendation)} characters")
        
        if request.url is not None:
            update_data["url"] = request.url
            updated_fields["url"] = request.url
            logger.info(f"[update-client-recommendation endpoint] Will update url: {request.url}")
        
        # Step 3: Update the interaction in database
        if update_data:
            updated_interaction = update_user_interaction(db, int(original_interaction.id), update_data)
            logger.info(f"[update-client-recommendation endpoint] Successfully updated interaction {original_interaction.id}")
            
            return UpdateClientRecommendationResponse(
                retail_id=request.retail_id,
                status="success",
                message="Client recommendation and/or link updated successfully",
                interaction_id=updated_interaction.id,
                updated_fields=updated_fields
            )
        else:
            logger.warning(f"[update-client-recommendation endpoint] No fields to update for retail_id: {request.retail_id}")
            return UpdateClientRecommendationResponse(
                retail_id=request.retail_id,
                status="success",
                message="No fields to update - both client_recommendation and url were None",
                interaction_id=original_interaction.id,
                updated_fields={}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update-client-recommendation endpoint] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

