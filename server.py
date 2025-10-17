import asyncio
import websockets
import json
import os
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import threading

# ----------------- WebSocket Chat -----------------
customers = {}  # session_id -> websocket
agents = set()  # set of agent websockets

async def handler(websocket):
    role = None
    session_id = None
    picked_customer = None

    try:
        async for message in websocket:
            data = json.loads(message)

            if "role" in data:
                role = data["role"]
                if role == "customer":
                    session_id = f"customer_{id(websocket)}"
                    customers[session_id] = websocket
                    await websocket.send(json.dumps({"type": "session", "session_id": session_id}))
                    await notify_agents()
                elif role == "agent":
                    agents.add(websocket)
                    await notify_agents()

            elif data.get("type") == "pick_customer" and role == "agent":
                picked_customer = data["session_id"]
                await websocket.send(json.dumps({"type": "info", "text": f"Connected with {picked_customer}"}))

            elif data.get("type") == "message":
                text = data["text"]
                sender = data.get("sender")

                if sender == "customer" and session_id:
                    for agent in agents:
                        try:
                            await agent.send(json.dumps({"type": "message", "text": text, "from": session_id}))
                        except:
                            pass
                elif sender == "agent" and picked_customer:
                    target_ws = customers.get(picked_customer)
                    if target_ws:
                        await target_ws.send(json.dumps({"type": "message", "text": text, "from": "agent"}))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if role == "customer" and session_id in customers:
            del customers[session_id]
            await notify_agents()
        elif role == "agent" and websocket in agents:
            agents.remove(websocket)

async def notify_agents():
    data = json.dumps({"type": "customers", "list": list(customers.keys())})
    for agent in agents:
        try:
            await agent.send(data)
        except:
            pass

# ----------------- HTTP Server -----------------
def run_http_server():
    port = 8080  # HTTP port for serving index.html
    handler = SimpleHTTPRequestHandler
    with TCPServer(("", port), handler) as httpd:
        print(f"🌐 HTTP server running at http://0.0.0.0:{port}")
        httpd.serve_forever()

# ----------------- Deployment -----------------
PORT = int(os.environ.get("PORT", 10000))

async def main():
    threading.Thread(target=run_http_server, daemon=True).start()
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"🚀 WebSocket server running at ws://0.0.0.0:{PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())


