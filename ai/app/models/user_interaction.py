from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.sql import func
from app.core.database import Base


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)
    retail_id = Column(Integer, nullable=False, index=True)
    url = Column(String(1500), nullable=False)
    actions = Column(JSON, nullable=True)
    html_content = Column(Text)
    client_recommendation = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # New columns (all nullable)
    captured_at = Column(DateTime(timezone=True), nullable=True)
    scanned_at = Column(DateTime(timezone=True), nullable=True)
    count_action = Column(Integer, nullable=True)
    count_failed_action = Column(Integer, nullable=True)
    analysed_at = Column(DateTime(timezone=True), nullable=True)
    ai_model = Column(String(255), nullable=True)
    token_used = Column(Integer, nullable=True)
    ai_costs = Column(Float, nullable=True)
