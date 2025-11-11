"""
Web UI Module

FastAPI-based WebSocket server for real-time agent chat interface.

Provides:
- WebSocket endpoint for chat (/chat)
- Health check endpoint (/health)
- API info endpoint (/api/info)
- Static file serving for frontend

Usage:
    uvicorn web_ui.app:app --reload --port 8080
"""

__version__ = "1.0.0"
