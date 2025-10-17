import asyncio
import websockets
import json
import os

# Store connected clients
customers = {}  # session_id -> websocket
agents = set()  # set of agent websockets

async def handler(websocket):
    role = None
    session_id = None
    picked_customer = None

    try:
        async for message in websocket:
            data = json.loads(message)

            # --- When a new client connects ---
            if "role" in data:
                role = data["role"]
                if role == "customer":
                    session_id = f"customer_{id(websocket)}"
                    customers[session_id] = websocket
                    await websocket.send(json.dumps({"type": "session", "session_id": session_id}))
                    print(f"✅ Customer connected: {session_id}")
                    # Update all agents
                    await notify_agents()
                elif role == "agent":
                    agents.add(websocket)
                    print("🎧 Agent connected")
                    await notify_agents()

            # --- When an agent selects a customer ---
            elif data.get("type") == "pick_customer" and role == "agent":
                picked_customer = data["session_id"]
                await websocket.send(json.dumps({"type": "info", "text": f"Connected with {picked_customer}"}))
                print(f"Agent picked {picked_customer}")

            # --- When a message is sent ---
            elif data.get("type") == "message":
                text = data["text"]
                sender = data.get("sender")

                # Customer sending message
                if sender == "customer" and session_id:
                    for agent in agents:
                        try:
                            await agent.send(json.dumps({"type": "message", "text": text, "from": session_id}))
                        except:
                            pass

                # Agent replying
                elif sender == "agent" and picked_customer:
                    target_ws = customers.get(picked_customer)
                    if target_ws:
                        await target_ws.send(json.dumps({"type": "message", "text": text, "from": "agent"}))

    except websockets.exceptions.ConnectionClosed:
        print(f"🔌 Disconnected: {role or 'unknown'}")

    finally:
        # Cleanup when disconnected
        if role == "customer" and session_id in customers:
            del customers[session_id]
            await notify_agents()
        elif role == "agent" and websocket in agents:
            agents.remove(websocket)

async def notify_agents():
    """Send list of active customers to all agents."""
    data = json.dumps({"type": "customers", "list": list(customers.keys())})
    for agent in agents:
        try:
            await agent.send(data)
        except:
            pass

# --- Deployment setup ---
PORT = int(os.environ.get("PORT", 10000))
print(f"🚀 Server starting on port {PORT} ...")

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"✅ Server running at ws://0.0.0.0:{PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

