#!/usr/bin/env python3
import asyncio
import websockets
import json
import logging
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameServer:
    def __init__(self):
        self.clients = {}  # client_id -> websocket
        self.players = {}  # player_id -> player_data
        self.next_client_id = 1
        self.next_bot_id = 10000
        self.game_state = {
            "entities": [],
            "tick": 0,
            "serverTime": 0
        }
        self.spawn_bots(3)  # başlangıçta 3 bot spawn

    def spawn_bots(self, count):
        for _ in range(count):
            bot_id = self.next_bot_id
            self.next_bot_id += 1
            self.players[bot_id] = {
                'id': bot_id,
                'client_id': None,
                'name': f'Bot{bot_id}',
                'x': random.randint(200, 1800),
                'y': random.randint(200, 1000),
                'vx': 0,
                'vy': 0,
                'rotation': 0,
                'health': 100,
                'score': 0,
                'isBot': True
            }

    def update_bots(self):
        for pdata in self.players.values():
            if pdata.get("isBot"):
                pdata['x'] += random.randint(-10, 10)
                pdata['y'] += random.randint(-10, 10)
                pdata['x'] = max(50, min(1950, pdata['x']))
                pdata['y'] = max(50, min(1150, pdata['y']))

    async def register_client(self, websocket):
        client_id = self.next_client_id
        self.next_client_id += 1
        self.clients[client_id] = websocket
        logger.info(f"✅ Client {client_id} connected from {websocket.remote_address}")
        return client_id

    async def unregister_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]
        player_id = None
        for pid, pdata in self.players.items():
            if pdata.get('client_id') == client_id:
                player_id = pid
                break
        if player_id:
            await self.handle_player_leave(player_id)
        logger.info(f"❌ Client {client_id} disconnected")

    async def broadcast(self, message, exclude_client=None):
        if self.clients:
            disconnected = []
            for client_id, ws in self.clients.items():
                if client_id != exclude_client:
                    try:
                        await ws.send(json.dumps(message))
                    except:
                        disconnected.append(client_id)
            for client_id in disconnected:
                await self.unregister_client(client_id)

    async def handle_message(self, client_id, websocket, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            logger.info(f"📥 Client {client_id}: {msg_type}")
            if msg_type == 'PLAYER_JOIN':
                await self.handle_player_join(client_id, data)
            elif msg_type == 'PLAYER_UPDATE':
                await self.handle_player_update(data)
            elif msg_type == 'PLAYER_SHOOT':
                await self.handle_player_shoot(data)
            elif msg_type == 'CHAT_MESSAGE':
                await self.handle_chat_message(data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client_id}: {message}")

    async def handle_player_join(self, client_id, data):
        player_id = data.get('playerId')
        player_name = data.get('name', 'Player')
        player_data = {
            'id': player_id,
            'client_id': client_id,
            'name': player_name,
            'x': random.randint(200, 1800),
            'y': random.randint(200, 1000),
            'vx': 0,
            'vy': 0,
            'rotation': 0,
            'health': 100,
            'score': 0,
            'joinTime': datetime.now().isoformat()
        }
        self.players[player_id] = player_data
        await self.broadcast({
            'type': 'PLAYER_JOIN',
            'playerId': player_id,
            'name': player_name,
            'x': player_data['x'],
            'y': player_data['y']
        }, exclude_client=client_id)
        world_state = {
            'type': 'WORLD_STATE',
            'players': list(self.players.values()),
            'tick': self.game_state['tick']
        }
        await self.clients[client_id].send(json.dumps(world_state))
        logger.info(f"🎮 {player_name} (ID: {player_id}) joined the game")

    async def handle_player_update(self, data):
        player_id = data.get('playerId')
        if player_id in self.players:
            self.players[player_id].update({
                'x': data.get('x', self.players[player_id]['x']),
                'y': data.get('y', self.players[player_id]['y']),
                'vx': data.get('vx', 0),
                'vy': data.get('vy', 0),
                'rotation': data.get('rotation', 0)
            })
            await self.broadcast({
                'type': 'PLAYER_UPDATE',
                'playerId': player_id,
                'x': self.players[player_id]['x'],
                'y': self.players[player_id]['y'],
                'vx': self.players[player_id]['vx'],
                'vy': self.players[player_id]['vy'],
                'rotation': self.players[player_id]['rotation']
            })

    async def handle_player_shoot(self, data):
        shooter_id = data.get('playerId')
        if shooter_id in self.players:
            await self.broadcast({
                'type': 'PLAYER_SHOOT',
                'shooterId': shooter_id,
                'origin': data.get('origin'),
                'direction': data.get('direction')
            })

    async def handle_player_leave(self, player_id):
        if player_id in self.players:
            player_name = self.players[player_id]['name']
            del self.players[player_id]
            await self.broadcast({'type': 'PLAYER_LEAVE','playerId': player_id})
            logger.info(f"👋 {player_name} (ID: {player_id}) left the game")

    async def handle_chat_message(self, data):
        await self.broadcast({
            'type': 'CHAT_MESSAGE',
            'playerId': data.get('playerId'),
            'message': data.get('message'),
            'timestamp': datetime.now().isoformat()
        })

    async def game_loop(self):
        while True:
            await asyncio.sleep(1/30)
            self.game_state['tick'] += 1

            self.update_bots()

            if self.game_state['tick'] % 30 == 0:
                world_state = {
                    'type': 'WORLD_STATE',
                    'players': list(self.players.values()),
                    'tick': self.game_state['tick'],
                    'serverTime': datetime.now().timestamp()
                }
                await self.broadcast(world_state)

game_server = GameServer()

async def handle_client(websocket, path):
    client_id = await game_server.register_client(websocket)
    try:
        async for message in websocket:
            await game_server.handle_message(client_id, websocket, message)
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {client_id} connection closed")
    finally:
        await game_server.unregister_client(client_id)

async def main():
    asyncio.create_task(game_server.game_loop())
    logger.info("🚀 Starting WebSocket Game Server on ws://0.0.0.0:8080")
    async with websockets.serve(handle_client, "0.0.0.0", 8080):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
