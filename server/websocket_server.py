from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

app = FastAPI()

# websocket_server.py dosyası: server/websocket_server.py
# client klasörü: proje kökünde => multiplayer-arena/client

BASE_DIR = Path(__file__).resolve().parent.parent  # == multiplayer-arena/
CLIENT_DIR = BASE_DIR / "client"

# Mount client only if it exists
if CLIENT_DIR.exists():
    app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="client")
else:
    print(f"WARNING: 'client' directory not found at {CLIENT_DIR}")

clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for client in clients:
                await client.send_text(data)
    except WebSocketDisconnect:
        clients.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.websocket_server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
