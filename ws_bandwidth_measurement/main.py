# Save as server.py
# Install with: pip install websockets
import asyncio
import websockets

async def echo(websocket):
    """Receives data and discards it to measure ingress speed."""
    try:
        async for message in websocket:
            # For a pure throughput test, you might even comment out the send.
            # await websocket.send(message)
            pass # Just consume the data as fast as possible.
    except websockets.ConnectionClosed:
        print("Client disconnected.")

async def main():
    async with websockets.serve(echo, "localhost", 8765):
        print("Server started on ws://localhost:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
