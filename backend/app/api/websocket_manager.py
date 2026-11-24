import json
import logging
from typing import Dict, List, Any
from fastapi import WebSocket

logger = logging.getLogger("vaaniweb.ws")


class WebSocketManager:
    """Manages active WebSocket connections for live browser preview and action event streaming."""

    def __init__(self):
        # Maps session_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str = "default"):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket client connected for session '{session_id}'. Total: {len(self.active_connections[session_id])}")

    def disconnect(self, websocket: WebSocket, session_id: str = "default"):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected from session '{session_id}'.")

    async def broadcast_to_session(self, session_id: str, event_type: str, data: Any):
        """Send a structured event message to all clients listening to a session."""
        message = {
            "type": event_type,
            "data": data
        }
        json_str = json.dumps(message)
        dead_sockets = []

        connections = self.active_connections.get(session_id, [])
        for socket in connections:
            try:
                await socket.send_text(json_str)
            except Exception as e:
                logger.warning(f"Error sending to websocket client: {e}")
                dead_sockets.append(socket)

        for dead in dead_sockets:
            self.disconnect(dead, session_id)


ws_manager = WebSocketManager()
