from fastapi import APIRouter
from app.api.v1.endpoints import interactions, gpt_agent

# Public router - no authentication required
public_router = APIRouter()
public_router.include_router(interactions.router, tags=["interactions"])
public_router.include_router(gpt_agent.router, tags=["gpt-agent"])

# Include all routers
def include_routers(app):
    app.include_router(public_router, prefix="/api/v1")
