"""WebSocket endpoint — /ws/analysis-stream.

ConnectionService (Controller, GRASP) manages the registry; this module just wires it to FastAPI.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.connection import connection_service

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/analysis-stream")
async def analysis_stream(ws: WebSocket):
    await connection_service.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        connection_service.disconnect(ws)
