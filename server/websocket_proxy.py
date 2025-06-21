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
        for i in range(count):
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
                'isBot': True,
                'lastUpdate': datetime.now().timestamp(),
                'lastShot': 0,  # Ateş etme için
                'targetX': random.randint(200, 1800),  # Hedef pozisyon
                'targetY': random.randint(200, 1000),
                'moveTimer': 0  # Hareket zamanlayıcı
            }

    def update_bots(self):
        current_time = datetime.now().timestamp()
        
        for pdata in self.players.values():
            if pdata.get("isBot") and not pdata.get('isDead', False):
                # Her 2-5 saniyede bir yeni hedef belirle
                if current_time - pdata.get('moveTimer', 0) > random.uniform(2, 5):
                    pdata['targetX'] = random.randint(200, 1800)
                    pdata['targetY'] = random.randint(200, 1000)
                    pdata['moveTimer'] = current_time
                
                # Hedefe doğru yumuşak hareket
                dx = pdata['targetX'] - pdata['x']
                dy = pdata['targetY'] - pdata['y']
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 10:  # Hedefe yakın değilse hareket et
                    # Normalize et ve hız uygula
                    speed = 150  # Sabit hız
                    normalized_dx = dx / distance
                    normalized_dy = dy / distance
                    
                    # Frame-independent hareket (deltaTime = 0.05)
                    pdata['x'] += normalized_dx * speed * 0.05
                    pdata['y'] += normalized_dy * speed * 0.05
                    
                    # Velocity değerlerini güncelle (görsel için)
                    pdata['vx'] = normalized_dx * speed
                    pdata['vy'] = normalized_dy * speed
                    
                    # Rotasyonu güncelle
                    pdata['rotation'] = math.atan2(dy, dx)
                else:
                    # Hedefe ulaştı, dur
                    pdata['vx'] = 0
                    pdata['vy'] = 0
                
                # Dünya sınırları
                pdata['x'] = max(50, min(1950, pdata['x']))
                pdata['y'] = max(50, min(1150, pdata['y']))
                
                # lastUpdate güncelle
                pdata['lastUpdate'] = current_time
                
                # En yakın oyuncuyu bul ve ona doğru ateş et
                if current_time - pdata.get('lastShot', 0) > random.uniform(1, 3):
                    # Canlı oyuncuları bul
                    alive_players = [p for p in self.players.values() 
                                   if p['id'] != pdata['id'] 
                                   and not p.get('isDead', False)
                                   and p['health'] > 0]
                    
                    if alive_players:
                        # En yakın oyuncuyu bul
                        closest_player = None
                        min_distance = float('inf')
                        
                        for target in alive_players:
                            dist = math.sqrt((target['x'] - pdata['x'])**2 + 
                                           (target['y'] - pdata['y'])**2)
                            if dist < min_distance and dist < 500:  # 500 birim menzil
                                min_distance = dist
                                closest_player = target
                        
                        if closest_player:
                            # Hedefe doğru ateş et
                            dx = closest_player['x'] - pdata['x']
                            dy = closest_player['y'] - pdata['y']
                            shoot_rotation = math.atan2(dy, dx)
                            
                            # Biraz rastgelelik ekle (perfect aim olmasın)
                            shoot_rotation += random.uniform(-0.2, 0.2)
                            
                            # Namlu pozisyonunu hesapla
                            muzzle_offset = 30
                            shoot_x = pdata['x'] + math.cos(shoot_rotation) * muzzle_offset
                            shoot_y = pdata['y'] + math.sin(shoot_rotation) * muzzle_offset
                            
                            pdata['lastShot'] = current_time
                            
                            asyncio.create_task(self.broadcast({
                                'type': 'PLAYER_SHOOT',
                                'shooterId': pdata['id'],
                                'x': shoot_x,
                                'y': shoot_y,
                                'rotation': shoot_rotation,
                                'timestamp': current_time
                            }))
                
                # Her tick pozisyon gönder (smooth hareket için)
                asyncio.create_task(self.broadcast({
                    'type': 'PLAYER_UPDATE',
                    'playerId': pdata['id'],
                    'x': pdata['x'],
                    'y': pdata['y'],
                    'vx': pdata['vx'],
                    'vy': pdata['vy'],
                    'rotation': pdata['rotation']
                }))

    async def register_client(self, websocket):
        client_id = self.next_client_id
        self.next_client_id += 1
        self.clients[client_id] = websocket
        
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
                await self.handle_player_update(client_id, data)
            elif msg_type == 'PLAYER_SHOOT':
                await self.handle_player_shoot(data)
            elif msg_type == 'CHAT_MESSAGE':
                await self.handle_chat_message(data)
            elif msg_type == 'PLAYER_HIT':
                await self.handle_player_hit(data)
            elif msg_type == 'HEARTBEAT':
                # Heartbeat mesajı - sadece lastUpdate'i güncelle
                player_id = data.get('playerId')
                if player_id in self.players:
                    self.players[player_id]['lastUpdate'] = datetime.now().timestamp()
                
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
            'joinTime': datetime.now().isoformat(),
            'lastUpdate': datetime.now().timestamp()
        }
        
        self.players[player_id] = player_data
        
        # Diğer oyunculara bildir
        await self.broadcast({
            'type': 'PLAYER_JOIN',
            'playerId': player_id,
            'name': player_name,
            'x': player_data['x'],
            'y': player_data['y'],
            'health': player_data['health'],
            'score': player_data['score']
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

    async def handle_player_update(self, client_id, data):
        player_id = data.get('playerId')
        if player_id in self.players:
            player = self.players[player_id]
            
            # Client ID kontrolü - sadece kendi verisini güncelleyebilir
            if player.get('client_id') != client_id:
                logger.warning(f"Client {client_id} tried to update player {player_id}")
                return
            
            # Pozisyon güncellemesini kaydet
            old_x = player.get('x', 0)
            old_y = player.get('y', 0)
            
            player.update({
                'x': data.get('x', player['x']),
                'y': data.get('y', player['y']),
                'vx': data.get('vx', 0),
                'vy': data.get('vy', 0),
                'rotation': data.get('rotation', 0),
                'lastUpdate': datetime.now().timestamp()  # 🔥 ÖNEMLİ: lastUpdate'i güncelle!
            })
            
            # Pozisyon değişikliğini diğer oyunculara bildir
            # Sadece önemli pozisyon değişikliklerinde gönder (optimizasyon)
            if abs(old_x - player['x']) > 2 or abs(old_y - player['y']) > 2:
                update_message = {
                    'type': 'PLAYER_UPDATE',
                    'playerId': player_id,
                    'x': player['x'],
                    'y': player['y'],
                    'vx': player['vx'],
                    'vy': player['vy'],
                    'rotation': player['rotation']
                }
                # Güncelleyen client hariç herkese gönder
                await self.broadcast(update_message, exclude_client=client_id)

    async def handle_player_shoot(self, data):
        shooter_id = data.get('playerId')
        if shooter_id in self.players:
            # Ateş bilgisini tüm oyunculara yayınla
            shoot_data = {
                'type': 'PLAYER_SHOOT',
                'shooterId': shooter_id,
                'x': data.get('x'),
                'y': data.get('y'),
                'rotation': data.get('rotation'),
                'timestamp': datetime.now().timestamp()
            }
            await self.broadcast(shoot_data)

    async def handle_player_hit(self, data):
        victim_id = data.get('victimId')
        shooter_id = data.get('shooterId')
        damage = data.get('damage', 20)
        
        if victim_id in self.players and shooter_id in self.players:
            victim = self.players[victim_id]
            shooter = self.players[shooter_id]
            
            # 🔥 Eğer oyuncu zaten ölüyse hasar alma
            if victim.get('isDead', False):
                return
            
            # Hasar uygula
            victim['health'] = max(0, victim['health'] - damage)
            
            # Ölüm kontrolü
            if victim['health'] <= 0:
                victim['isDead'] = True  # Ölü olarak işaretle
                shooter['score'] += 1
                
                # Ölüm mesajı gönder
                await self.broadcast({
                    'type': 'PLAYER_DEATH',
                    'victimId': victim_id,
                    'shooterId': shooter_id,
                    'killerName': shooter['name'],
                    'victimName': victim['name']
                })
                
                # Yeniden doğma
                asyncio.create_task(self.respawn_player(victim_id))
            else:
                # Hasar mesajı gönder
                await self.broadcast({
                    'type': 'PLAYER_HIT',
                    'victimId': victim_id,
                    'health': victim['health'],
                    'damage': damage
                })

    async def respawn_player(self, player_id):
        await asyncio.sleep(3)  # 3 saniye bekle
        
        if player_id in self.players:
            player = self.players[player_id]
            player['health'] = 100
            player['isDead'] = False  # Artık ölü değil
            player['x'] = random.randint(200, 1800)
            player['y'] = random.randint(200, 1000)
            
            # Yeniden doğma mesajı
            await self.broadcast({
                'type': 'PLAYER_RESPAWN',
                'playerId': player_id,
                'x': player['x'],
                'y': player['y'],
                'health': player['health']
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
        """Ana oyun döngüsü"""
        while True:
            try:
                await asyncio.sleep(0.05)  # 20 FPS for server
                self.game_state['tick'] += 1
                
                # Botları güncelle
                self.update_bots()
                
                # Bağlantısı kopan oyuncuları temizle
                current_time = datetime.now().timestamp()
                disconnected_players = []
                
                for player_id, player in self.players.items():
                    if not player.get('isBot') and player.get('lastUpdate'):
                        # 30 saniyedir güncelleme gelmemişse bağlantı kopmuştur (10'dan 30'a çıkardık)
                        if current_time - player['lastUpdate'] > 30:
                            disconnected_players.append(player_id)
                            logger.warning(f"Player {player_id} timed out (no update for 30s)")
                
                for player_id in disconnected_players:
                    await self.handle_player_leave(player_id)
                
                # Her 2 saniyede bir senkronizasyon mesajı gönder
                if self.game_state['tick'] % 40 == 0:
                    sync_data = {
                        'type': 'SYNC',
                        'tick': self.game_state['tick'],
                        'serverTime': current_time,
                        'playerCount': len([p for p in self.players.values() if not p.get('isBot')])
                    }
                    await self.broadcast(sync_data)
                    
                # Her 10 saniyede bir full world state gönder (güvenlik için)
                if self.game_state['tick'] % 200 == 0:
                    world_state = {
                        'type': 'WORLD_STATE',
                        'players': list(self.players.values()),
                        'tick': self.game_state['tick'],
                        'serverTime': current_time
                    }
                    await self.broadcast(world_state)
                    logger.info(f"Sent world state - {len(self.players)} players online")
                    
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
                await asyncio.sleep(1)

# Global server instance
game_server = GameServer()

async def websocket_handler(request):
    """WebSocket bağlantılarını handle et"""
    ws = web.WebSocketResponse(
        heartbeat=30,  # 30 saniye heartbeat
        timeout=60,    # 60 saniye timeout
        autoping=True  # Otomatik ping/pong
    )
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
            elif msg.type == WSMsgType.CLOSE:
                logger.info(f'WebSocket closed for client {client_id}')
                break
    except Exception as e:
        logger.error(f"Error in websocket handler: {e}")
    finally:
        await game_server.unregister_client(client_id)
    
    return ws

async def health_check(request):
    """Health check endpoint"""
    player_count = len([p for p in game_server.players.values() if not p.get('isBot')])
    bot_count = len([p for p in game_server.players.values() if p.get('isBot')])
    
    health_data = {
        "status": "OK",
        "players": player_count,
        "bots": bot_count,
        "total_entities": len(game_server.players),
        "tick": game_server.game_state['tick'],
        "uptime": int(datetime.now().timestamp() - game_server.game_state.get('start_time', 0))
    }
    
    return web.json_response(health_data)

async def serve_static(request):
    """Static dosyaları serve et"""
    filename = request.match_info['filename']
    
    # Güvenlik kontrolü - path traversal engelle
    if '..' in filename or filename.startswith('/'):
        return web.Response(text="Invalid path", status=400)
    
    filepath = os.path.join('../client', filename)
    
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
    elif filename.endswith('.png'):
        content_type = 'image/png'
    elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
        content_type = 'image/jpeg'
    
    try:
        # Binary dosyalar için
        if content_type.startswith('image/'):
            with open(filepath, 'rb') as f:
                content = f.read()
            return web.Response(body=content, content_type=content_type)
        else:
            # Text dosyalar için
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return web.Response(text=content, content_type=content_type)
    except Exception as e:
        logger.error(f"Error serving {filename}: {e}")
        return web.Response(text="Error loading file", status=500)

async def index_handler(request):
    """Ana sayfa - Oyun client'ını serve et"""
    try:
        # ../client/index.html dosyasını oku
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
                <title>Multiplayer Arena</title>
                <style>
                    body { 
                        font-family: Arial; 
                        background: #0a0a0a; 
                        color: white; 
                        text-align: center; 
                        padding: 50px;
                        margin: 0;
                    }
                    .container {
                        max-width: 800px;
                        margin: 0 auto;
                    }
                    h1 { 
                        color: #00ff88; 
                        font-size: 3em;
                        margin-bottom: 0.5em;
                    }
                    .status { 
                        background: #1a1a1a;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                    }
                    .online { color: #00ff88; }
                    .error { color: #ff6666; }
                    code { 
                        background: #2a2a2a; 
                        padding: 5px 10px; 
                        border-radius: 5px;
                        font-size: 1.1em;
                    }
                    a { 
                        color: #00aaff; 
                        text-decoration: none;
                    }
                    a:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎮 Multiplayer Arena</h1>
                    <div class="status">
                        <p class="online">✅ Server is running!</p>
                        <p>WebSocket endpoint: <code>ws://this-domain/ws</code></p>
                    </div>
                    <div class="status error">
                        <p>⚠️ Client files not found!</p>
                        <p>Please upload the game client files to the <code>client/</code> directory.</p>
                    </div>
                    <p>
                        <a href="/health">Health Check</a> | 
                        <a href="https://github.com/yourusername/multiplayer-arena">GitHub</a>
                    </p>
                </div>
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
    app.router.add_get('/{filename}', serve_static)
    
    # CORS'u tüm route'lara ekle
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

async def main():
    """Ana server başlatıcı"""
    # Başlangıç zamanını kaydet
    game_server.game_state['start_time'] = datetime.now().timestamp()
    
    # Game loop'u başlat
    game_loop_task = asyncio.create_task(game_server.game_loop())
    
    # Port ayarı - Render için PORT environment variable kullan
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting Multiplayer Arena Server")
    logger.info(f"🌐 Host: {host}:{port}")
    logger.info(f"🔌 WebSocket: ws://{host}:{port}/ws")
    logger.info(f"💚 Health: http://{host}:{port}/health")
    
    try:
        # Aiohttp app oluştur
        app = await create_app()
        
        # Server'ı başlat
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info("✅ Server is ready and accepting connections!")
        logger.info(f"🤖 Spawned {len(game_server.players)} bots")
        
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
