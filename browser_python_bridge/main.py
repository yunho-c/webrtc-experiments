import asyncio
import websockets
import numpy as np
import json
import logging
import time

# --- Configuration ---
HOST = "localhost"
PORT = 8765
FRAME_RATE = 30  # Target frames per second

# --- Set up basic logging ---
# We'll use a more detailed format to include timings
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# --- Resolution presets ---
RESOLUTIONS = {
    "HD (1280x720)": (1280, 720),
    "FHD (1920x1080)": (1920, 1080),
    "4K (3840x2160)": (3840, 2160),
}


# --- Video Source Simulation ---
class VideoSource:
    """
    A class to simulate a video source by generating frames.
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.frame_index = 0
        logging.info(f"Initialized video source with resolution {width}x{height}")

    def get_frame(self):
        """
        Generates a single frame.
        """
        r_shift = int(127 * (1 + np.sin(self.frame_index * 0.05)))
        g_shift = int(127 * (1 + np.sin(self.frame_index * 0.03)))
        b_shift = int(127 * (1 + np.cos(self.frame_index * 0.07)))

        frame = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        y_gradient = np.linspace(0, 255, self.height, dtype=np.uint8)
        x_gradient = np.linspace(0, 255, self.width, dtype=np.uint8)

        frame[:, :, 0] = (y_gradient[:, np.newaxis] + r_shift) % 255
        frame[:, :, 1] = (x_gradient[np.newaxis, :] + g_shift) % 255
        frame[:, :, 2] = b_shift
        frame[:, :, 3] = 255

        self.frame_index += 1
        return frame.tobytes()


# --- WebSocket Handler ---
async def stream_video(websocket):
    """
    Handles WebSocket connections and streams video frames with performance logging.
    """
    logging.info(f"Client connected from {websocket.remote_address}")
    video_source = None

    try:
        message = await websocket.recv()
        data = json.loads(message)

        if data.get("action") == "start":
            resolution_key = data.get("resolution", "HD (1280x720)")
            width, height = RESOLUTIONS.get(resolution_key, (1280, 720))

            logging.info(
                f"Request received to start stream with resolution: {width}x{height}"
            )
            video_source = VideoSource(width, height)

            target_frame_time = 1.0 / FRAME_RATE

            while True:
                # --- Start Profiling Timers ---
                loop_start_time = time.perf_counter()

                # 1. Profile frame generation
                get_frame_start = time.perf_counter()
                frame_bytes = video_source.get_frame()
                get_frame_end = time.perf_counter()

                # 2. Profile WebSocket send operation
                send_start = time.perf_counter()
                await websocket.send(frame_bytes)
                send_end = time.perf_counter()

                # --- Calculate Durations ---
                get_frame_duration_ms = (get_frame_end - get_frame_start) * 1000
                send_duration_ms = (send_end - send_start) * 1000

                # Regulate the frame rate
                elapsed_time = time.perf_counter() - loop_start_time
                sleep_duration = max(0, target_frame_time - elapsed_time)
                await asyncio.sleep(sleep_duration)

                total_loop_duration_ms = (time.perf_counter() - loop_start_time) * 1000

                # --- Log Timings to Console ---
                logging.info(
                    f"Frame Gen: {get_frame_duration_ms:6.2f}ms | "
                    f"WS Send: {send_duration_ms:6.2f}ms | "
                    f"Sleep: {sleep_duration * 1000:6.2f}ms | "
                    f"Total: {total_loop_duration_ms:6.2f}ms"
                )

    except websockets.exceptions.ConnectionClosed as e:
        logging.warning(f"Connection closed by client: {e.code} {e.reason}")
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        logging.info("Client disconnected.")


# --- Main Server Execution ---
async def main():
    logging.info(f"Starting WebSocket server on ws://{HOST}:{PORT}")
    async with websockets.serve(stream_video, HOST, PORT, max_size=None):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server is shutting down.")
