from sqlalchemy.orm import Session
from app.models.user_interaction import UserInteraction
from app.schemas.user_interaction import UserInteractionCreate

def create_user_interaction(db: Session, interaction: UserInteractionCreate) -> UserInteraction:
    db_interaction = UserInteraction(
        session_id=interaction.session_id,
        retail_id=interaction.retail_id,
        url=interaction.url,
        actions=interaction.actions,
        html_content=interaction.html_content,
        client_recommendation=interaction.client_recommendation
    )
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction

def get_user_interaction_by_session_id(db: Session, session_id: str) -> UserInteraction:
    return db.query(UserInteraction).filter(UserInteraction.session_id == session_id).first()

def get_all_user_interactions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(UserInteraction).offset(skip).limit(limit).all()

def get_latest_user_interaction_by_retail_id(db: Session, retail_id: int) -> UserInteraction:
    """Get the latest user interaction by retail_id"""
    return db.query(UserInteraction).filter(
        UserInteraction.retail_id == retail_id
    ).order_by(UserInteraction.created_at.desc()).first()

def update_user_interaction(db: Session, interaction_id: int, update_data: dict) -> UserInteraction:
    """Update user interaction by ID"""
    db_interaction = db.query(UserInteraction).filter(UserInteraction.id == interaction_id).first()
    if not db_interaction:
        raise ValueError(f"UserInteraction with id {interaction_id} not found")
    
    for field, value in update_data.items():
        if hasattr(db_interaction, field):
            setattr(db_interaction, field, value)
    
    db.commit()
    db.refresh(db_interaction)
    return db_interaction