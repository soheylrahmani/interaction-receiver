from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from app.utils.datetime_utils import format_utc_datetime

from app.core.config import settings
from app.api.v1.endpoints import interactions, gpt_agent

# Custom JSON encoder for consistent datetime formatting
class CustomJSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        # Custom serialization for datetime objects
        if isinstance(content, dict):
            content = self._serialize_datetimes(content)
        elif isinstance(content, list):
            content = [self._serialize_datetimes(item) if isinstance(item, dict) else item for item in content]
        
        return super().render(content)
    
    def _serialize_datetimes(self, obj: any) -> any:
        """Recursively serialize datetime objects in dictionaries and lists"""
        if isinstance(obj, dict):
            return {key: self._serialize_datetimes(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetimes(item) for item in obj]
        elif isinstance(obj, datetime):
            return format_utc_datetime(obj)
        else:
            return obj

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Receive browser interaction recordings, replay them with Playwright, and optionally analyze pages with an LLM",
    version="1.0.0",
    default_response_class=CustomJSONResponse,
    docs_url="/docs",
    redoc_url=None,  # ReDoc disabled; use /docs (Swagger UI) instead
    swagger_ui_parameters={
        "docExpansion": "none",
        "defaultModelsExpandDepth": -1,
    },
)

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include existing routers
app.include_router(interactions.router, prefix=f"{settings.API_V1_STR}/interactions", tags=["interactions"])
app.include_router(gpt_agent.router, prefix=f"{settings.API_V1_STR}/gpt-agent", tags=["gpt-agent"])

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
