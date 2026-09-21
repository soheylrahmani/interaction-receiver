from pydantic import BaseModel, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.core.pydantic_config import BaseModelConfig

class Action(BaseModel, BaseModelConfig):
    type: str
    value: str
    selector: str
    timestamp: datetime

class UserInteractionResponse(BaseModel, BaseModelConfig):
    id: int
    session_id: str
    retail_id: int
    url: str
    actions: List[Action]
    html_content: Optional[str]
    client_recommendation: Optional[str] = None  # Can be very large (LONGTEXT in DB)
    created_at: datetime
    updated_at: Optional[datetime]
    captured_at: Optional[datetime] = None
    count_action: Optional[int] = None
    count_failed_action: Optional[int] = None
    scanned_at: Optional[datetime] = None
    analysed_at: Optional[datetime] = None
    ai_model: Optional[str] = None
    token_used: Optional[int] = None
    ai_costs: Optional[float] = None

class UserInteractionWithProductResponse(BaseModel, BaseModelConfig):
    """Response schema that includes both user interaction and retail product data"""
    user_interaction: UserInteractionResponse
    retail_product: Optional[Dict[str, Any]] = None  # Will contain retail product data if exists

class ScanRequest(BaseModel, BaseModelConfig):
    retail_id: int
    client_recommendation: Optional[str] = None
    ai_model: Optional[str] = None

class ScanResponse(BaseModel, BaseModelConfig):
    retail_id: int
    status: str
    message: str
    interaction_id: int
    html_content: Optional[str] = None
    # Additional debug information
    original_url: Optional[str] = None
    actions_count: Optional[int] = None
    html_content_length: Optional[int] = None
    original_html_length: Optional[int] = None
    filtered_html_length: Optional[int] = None
    # Error and action tracking
    error: Optional[str] = None
    error_type: Optional[str] = None
    successful_actions: Optional[int] = None
    failed_actions: Optional[int] = None
    total_actions: Optional[int] = None
    action_results: Optional[List[Dict[str, Any]]] = None

class UserInteractionCreate(BaseModel, BaseModelConfig):
    session_id: str
    retail_id: Optional[int] = None
    user_id: Optional[int] = None  # alias sent by interaction-tracker
    url: str
    actions: List[Action]
    html_content: Optional[str] = None
    client_recommendation: Optional[str] = None

    @model_validator(mode="after")
    def accept_tracker_user_id(self):
        if self.retail_id is None and self.user_id is None:
            raise ValueError("Either retail_id or user_id is required")
        if self.retail_id is None:
            self.retail_id = self.user_id
        return self

class UserInteractionBasicResponse(BaseModel, BaseModelConfig):
    id: int
    session_id: str
    retail_id: int
    url: str
    actions: List[Action]
    html_content: Optional[str]
    client_recommendation: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]
    captured_at: Optional[datetime] = None
    count_action: Optional[int] = None
    count_failed_action: Optional[int] = None
    scanned_at: Optional[datetime] = None
    analysed_at: Optional[datetime] = None
    ai_model: Optional[str] = None
    token_used: Optional[int] = None
    ai_costs: Optional[float] = None

    class Config:
        from_attributes = True

class ScanAndAnalyzeRequest(BaseModel, BaseModelConfig):
    retail_id: int
    client_recommendation: Optional[str] = None
    ai_model: Optional[str] = None
    avalai_model: Optional[str] = "4o-mini"  # Default GPT model
    callback_url: Optional[str] = None  # URL to send results to after completion

class ScanAndAnalyzeResponse(BaseModel, BaseModelConfig):
    retail_id: int
    status: str
    message: str
    interaction_id: int
    # Scan results
    html_content: Optional[str] = None
    original_url: Optional[str] = None
    actions_count: Optional[int] = None
    html_content_length: Optional[int] = None
    original_html_length: Optional[int] = None
    filtered_html_length: Optional[int] = None
    successful_actions: Optional[int] = None
    failed_actions: Optional[int] = None
    total_actions: Optional[int] = None
    action_results: Optional[List[Dict[str, Any]]] = None
    # GPT analysis results
    saved_data: Optional[Dict[str, Any]] = None
    token_usage: Optional[Dict[str, Any]] = None
    gpt_raw_response: Optional[str] = None
    cost: Optional[Dict[str, Any]] = None
    # Callback information
    callback_url: Optional[str] = None
    callback_status: Optional[str] = None
    callback_response: Optional[Dict[str, Any]] = None
    # Error handling
    error: Optional[str] = None
    error_type: Optional[str] = None

class UpdateClientRecommendationRequest(BaseModel, BaseModelConfig):
    retail_id: int
    client_recommendation: Optional[str] = None
    url: Optional[str] = None

class UpdateClientRecommendationResponse(BaseModel, BaseModelConfig):
    retail_id: int
    status: str
    message: str
    interaction_id: Optional[int] = None
    updated_fields: Optional[Dict[str, Any]] = None
    error: Optional[str] = None