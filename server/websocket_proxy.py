#!/usr/bin/env python3
import asyncio
import websockets
import json
import logging
import os
from datetime import datetime
import random
import math
import sys
from aiohttp import web, WSMsgType
import aiohttp_cors

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GameServer:
    def __init__(self):
        self.clients = {}  # client_id -> websocket
        self.players = {}  # player_id -> player_data
        self.next_client_id = 1
        self.next_bot_id = -1000  # Negative IDs for bots
        self.game_state = {
            "entities": [],
            "tick": 0,
            "serverTime": 0
        }
        self.spawn_bots(3)  # başlangıçta 3 bot spawn

    def spawn_bots(self, count):
        for _ in range(count):
            bot_id = self.next_bot_id
            self.next_bot_id -= 1
            self.players[bot_id] = {
                'id': bot_id,
                'client_id': None,
                'name': f'Bot{abs(bot_id)}',
                'x': random.randint(200, 1800),
                'y': random.randint(200, 1000),
                'vx': 0,
                'vy': 0,
                'rotation': 0,
                'health': 100,
                'score': random.randint(0, 5),
                'isBot': True
            }

    def update_bots(self):
        for pdata in self.players.values():
            if pdata.get("isBot"):
                # Daha akıllı bot hareketi
                time_factor = datetime.now().timestamp() * 0.5
                pdata['x'] += random.randint(-3, 3) + 2 * math.sin(time_factor + pdata['id'])
                pdata['y'] += random.randint(-3, 3) + 2 * math.cos(time_factor + pdata['id'] * 0.7)
                pdata['x'] = max(50, min(1950, pdata['x']))
                pdata['y'] = max(50, min(1150, pdata['y']))

    async def register_client(self, websocket):
        client_id = self.next_client_id
        self.next_client_id += 1
        self.clients[client_id] = websocket
        
        try:
            logger.info(f"✅ Client {client_id} connected")
        except:
            logger.info(f"✅ Client {client_id} connected")
            
        return client_id

    async def unregister_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]
            
        # Oyuncuyu bul ve kaldır
        player_id = None
        for pid, pdata in list(self.players.items()):
            if pdata.get('client_id') == client_id:
                player_id = pid
                break
                
        if player_id:
            await self.handle_player_leave(player_id)
            
        logger.info(f"❌ Client {client_id} disconnected")

    async def broadcast(self, message, exclude_client=None):
        if self.clients:
            disconnected = []
            for client_id, ws in list(self.clients.items()):
                if client_id != exclude_client:
                    try:
                        await ws.send_str(json.dumps(message))
                    except:
                        disconnected.append(client_id)
                        
            # Bağlantısı kopanları temizle
            for client_id in disconnected:
                await self.unregister_client(client_id)

    async def handle_message(self, client_id, data):
        try:
            msg_type = data.get('type')
            
            if msg_type == 'PLAYER_JOIN':
                await self.handle_player_join(client_id, data)
            elif msg_type == 'PLAYER_UPDATE':
                await self.handle_player_update(data)
            elif msg_type == 'PLAYER_SHOOT':
                await self.handle_player_shoot(data)
            elif msg_type == 'CHAT_MESSAGE':
                await self.handle_chat_message(data)
                
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")

    async def handle_player_join(self, client_id, data):
        player_id = data.get('playerId')
        player_name = data.get('name', 'Player')
        
        # Oyuncu verisi oluştur
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
        
        # Diğer oyunculara bildir
        await self.broadcast({
            'type': 'PLAYER_JOIN',
            'playerId': player_id,
            'name': player_name,
            'x': player_data['x'],
            'y': player_data['y']
        }, exclude_client=client_id)
        
        # Yeni oyuncuya mevcut dünya durumunu gönder
        world_state = {
            'type': 'WORLD_STATE',
            'players': list(self.players.values()),
            'tick': self.game_state['tick']
        }
        
        try:
            await self.clients[client_id].send_str(json.dumps(world_state))
            logger.info(f"🎮 {player_name} (ID: {player_id}) joined the game")
        except Exception as e:
            logger.error(f"Failed to send world state to client {client_id}: {e}")

    async def handle_player_update(self, data):
        player_id = data.get('playerId')
        if player_id in self.players:
            # Pozisyon güncellemesini kaydet
            self.players[player_id].update({
                'x': data.get('x', self.players[player_id]['x']),
                'y': data.get('y', self.players[player_id]['y']),
                'vx': data.get('vx', 0),
                'vy': data.get('vy', 0),
                'rotation': data.get('rotation', 0)
            })
            
            # Diğer oyunculara bildir (rate limiting ile)
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
            # Ateş bilgisini tüm oyunculara yayınla
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
            
            # Diğer oyunculara bildir
            await self.broadcast({
                'type': 'PLAYER_LEAVE',
                'playerId': player_id
            })
            
            logger.info(f"👋 {player_name} (ID: {player_id}) left the game")

    async def handle_chat_message(self, data):
        # Chat mesajını tüm oyunculara ilet
        await self.broadcast({
            'type': 'CHAT_MESSAGE',
            'playerId': data.get('playerId'),
            'message': data.get('message'),
            'timestamp': datetime.now().isoformat()
        })

    async def game_loop(self):
        """Ana oyun döngüsü - dünya durumunu periyodik olarak güncelle"""
        while True:
            try:
                await asyncio.sleep(1/20)  # 20 FPS for server
                self.game_state['tick'] += 1
                
                # Botları güncelle
                self.update_bots()
                
                # Her 2 saniyede dünya durumunu gönder
                if self.game_state['tick'] % 40 == 0:
                    world_state = {
                        'type': 'WORLD_STATE',
                        'players': list(self.players.values()),
                        'tick': self.game_state['tick'],
                        'serverTime': datetime.now().timestamp()
                    }
                    await self.broadcast(world_state)
                    
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
                await asyncio.sleep(1)

# Global server instance
game_server = GameServer()

async def websocket_handler(request):
    """WebSocket bağlantılarını handle et"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    client_id = await game_server.register_client(ws)
    
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await game_server.handle_message(client_id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client {client_id}")
            elif msg.type == WSMsgType.ERROR:
                logger.error(f'WebSocket error: {ws.exception()}')
    except Exception as e:
        logger.error(f"Error in websocket handler: {e}")
    finally:
        await game_server.unregister_client(client_id)
    
    return ws

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="OK", status=200)

async def serve_static(request):
    """Static dosyaları serve et"""
    filename = request.match_info['filename']
    filepath = os.path.join('../client', filename)  # ../client/ yolunu kullan
    
    if not os.path.exists(filepath):
        return web.Response(text="File not found", status=404)
    
    # MIME type belirleme
    content_type = 'text/plain'
    if filename.endswith('.html'):
        content_type = 'text/html'
    elif filename.endswith('.css'):
        content_type = 'text/css'
    elif filename.endswith('.js'):
        content_type = 'application/javascript'
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type=content_type)
    except Exception as e:
        logger.error(f"Error serving {filename}: {e}")
        return web.Response(text="Error loading file", status=500)

async def index_handler(request):
    """Ana sayfa - Oyun client'ını serve et"""
    try:
        # ../client/index.html dosyasını oku (server klasöründen çıkıp client'a git)
        if os.path.exists('../client/index.html'):
            with open('../client/index.html', 'r', encoding='utf-8') as f:
                html = f.read()
            return web.Response(text=html, content_type='text/html')
        else:
            # Fallback HTML
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Game Server</title>
                <style>
                    body { font-family: Arial; background: #222; color: white; text-align: center; padding: 50px; }
                    .error { color: #ff6666; }
                </style>
            </head>
            <body>
                <h1>🎮 WebSocket Game Server</h1>
                <p class="error">Client files not found!</p>
                <p>Server is running at: <code>ws://this-domain/ws</code></p>
                <p>Please upload client files to serve the game.</p>
                <p>Health check: <a href="/health">/health</a></p>
            </body>
            </html>
            """
            return web.Response(text=html, content_type='text/html')
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return web.Response(text="Error loading game", status=500)

async def create_app():
    """Aiohttp uygulamasını oluştur"""
    app = web.Application()
    
    # CORS ayarları
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Routes
    app.router.add_get('/', index_handler)
    app.router.add_get('/health', health_check)
    app.router.add_get('/healthz', health_check)  # Kubernetes style
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/{filename}', serve_static)  # Static dosyalar için
    
    # CORS'u tüm route'lara ekle
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

async def main():
    """Ana server başlatıcı"""
    # Game loop'u başlat
    game_loop_task = asyncio.create_task(game_server.game_loop())
    
    # Port ayarı - Render için PORT environment variable kullan
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting Game Server on http://{host}:{port}")
    logger.info(f"🌐 WebSocket endpoint: ws://{host}:{port}/ws")
    logger.info(f"💚 Health check: http://{host}:{port}/health")
    
    try:
        # Aiohttp app oluştur
        app = await create_app()
        
        # Server'ı başlat
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info("✅ Server is ready and accepting connections!")
        
        # Sonsuza kadar çalış
        await asyncio.Future()
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        game_loop_task.cancel()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
