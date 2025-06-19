from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

app = FastAPI()

# websocket_server.py bulunduğu yer: server/server/
# client klasörü nerede: ../../client/
BASE_DIR = Path(__file__).resolve().parents[2]
app.mount("/", StaticFiles(directory=BASE_DIR / "client", html=True), name="client")

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
