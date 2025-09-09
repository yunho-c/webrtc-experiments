import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List

# Create a FastAPI application instance
app = FastAPI()


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        # Store active connections mapping client_id to WebSocket object
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"New connection: {client_id}")
        await self.broadcast_user_list()

    def disconnect(self, client_id: str):
        """Disconnect a client."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Connection closed: {client_id}")

    async def broadcast_user_list(self):
        """Broadcast the list of connected users to everyone."""
        user_list = list(self.active_connections.keys())
        message = {"type": "users", "data": user_list}
        for connection in self.active_connections.values():
            await connection.send_json(message)

    async def send_personal_message(self, message: dict, recipient_id: str):
        """Send a message to a specific client."""
        if recipient_id in self.active_connections:
            websocket = self.active_connections[recipient_id]
            await websocket.send_json(message)
        else:
            print(f"Error: Recipient {recipient_id} not found.")


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    The main WebSocket endpoint for signaling.
    Handles connection, disconnection, and message routing.
    """
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Wait for a message from the client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Extract target and message data
            target_id = message.get("target")

            if target_id:
                # Add the sender's ID to the message for context
                message["from"] = client_id
                # Forward the message to the target client
                await manager.send_personal_message(message, target_id)
            else:
                print(f"Warning: Message from {client_id} has no target.")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        # Broadcast the updated user list after a disconnect
        await manager.broadcast_user_list()
    except Exception as e:
        print(f"An error occurred with client {client_id}: {e}")
        manager.disconnect(client_id)
        await manager.broadcast_user_list()


# Add a root endpoint for basic health check
@app.get("/")
async def read_root():
    return {"message": "WebRTC Signaling Server is running"}


if __name__ == "__main__":
    import uvicorn

    # This block allows running the server directly with `python main.py`
    uvicorn.run(app, host="0.0.0.0", port=8000)
