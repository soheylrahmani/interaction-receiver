#!/usr/bin/env python3
"""
Development runner for FastAPI.
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

if __name__ == "__main__":
    print("Starting FastAPI development server...")
    print("API:  http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    os.environ["DEBUG"] = "True"
    os.environ["ENVIRONMENT"] = "development"

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        log_level="info",
    )
