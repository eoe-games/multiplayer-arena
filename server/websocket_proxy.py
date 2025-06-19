#!/usr/bin/env python3
import asyncio
import websockets
import json
import logging
import os
from datetime import datetime
import random
import sys

# Logging ayarları - sadece önemli hataları göster
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# WebSocket kütüphanesi için ayrı logger - hataları sustur
websockets_logger = logging.getLogger('websockets')
websockets_logger.setLevel(logging.ERROR)

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
                # Daha akıllı bot hareketi
                pdata['x'] += random.randint(-5, 5)
                pdata['y'] += random.randint(-5, 5)
                pdata['x'] = max(50, min(1950, pdata['x']))
                pdata['y'] = max(50, min(1150, pdata['y']))

    async def register_client(self, websocket):
        client_id = self.next_client_id
        self.next_client_id += 1
        self.clients[client_id] = websocket
        
        # Client bilgilerini güvenli şekilde al
        try:
            remote_address = websocket.remote_address
            logger.info(f"✅ Client {client_id} connected from {remote_address}")
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
                        await ws.send(json.dumps(message))
                    except:
                        disconnected.append(client_id)
                        
            # Bağlantısı kopanları temizle
            for client_id in disconnected:
                await self.unregister_client(client_id)

    async def handle_message(self, client_id, websocket, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'PLAYER_JOIN':
                await self.handle_player_join(client_id, data)
            elif msg_type == 'PLAYER_UPDATE':
                await self.handle_player_update(data)
            elif msg_type == 'PLAYER_SHOOT':
                await self.handle_player_shoot(data)
            elif msg_type == 'CHAT_MESSAGE':
                await self.handle_chat_message(data)
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from client {client_id}")
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
            await self.clients[client_id].send(json.dumps(world_state))
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
            
            # Diğer oyunculara bildir
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
                await asyncio.sleep(1/30)  # 30 FPS
                self.game_state['tick'] += 1
                
                # Botları güncelle
                self.update_bots()
                
                # Her saniye dünya durumunu gönder
                if self.game_state['tick'] % 30 == 0:
                    world_state = {
                        'type': 'WORLD_STATE',
                        'players': list(self.players.values()),
                        'tick': self.game_state['tick'],
                        'serverTime': datetime.now().timestamp()
                    }
                    await self.broadcast(world_state)
                    
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
                await asyncio.sleep(1)  # Hata durumunda biraz bekle

# Global server instance
game_server = GameServer()

async def handle_http_request(path, headers):
    """Basit HTTP isteklerini handle et (health check, vs.)"""
    if path == "/":
        return (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "\r\n"
            "WebSocket Game Server is running!\r\n"
            "Connect with a WebSocket client to play."
        )
    elif path == "/health" or path == "/healthz":
        return (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "\r\n"
            "OK"
        )
    else:
        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "\r\n"
            "Not Found"
        )

async def handle_client(websocket, path):
    """WebSocket ve HTTP isteklerini handle et"""
    try:
        # İlk mesajı bekle - HTTP mi WebSocket mi?
        try:
            # Kısa timeout ile ilk veriyi kontrol et
            first_data = await asyncio.wait_for(websocket.recv(), timeout=0.1)
            
            # HTTP isteği mi kontrol et
            if isinstance(first_data, bytes):
                first_data = first_data.decode('utf-8', errors='ignore')
                
            if first_data.startswith(('GET', 'HEAD', 'POST')):
                # HTTP isteği - basit response gönder
                lines = first_data.split('\r\n')
                request_line = lines[0].split(' ')
                
                if len(request_line) >= 2:
                    method = request_line[0]
                    req_path = request_line[1]
                    
                    # Headers'ı parse et
                    headers = {}
                    for line in lines[1:]:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            headers[key.strip().lower()] = value.strip()
                    
                    response = await handle_http_request(req_path, headers)
                    await websocket.send(response.encode())
                    await websocket.close()
                    return
                    
        except asyncio.TimeoutError:
            # Timeout - normal WebSocket bağlantısı olarak devam et
            pass
            
        # WebSocket bağlantısı olarak devam et
        client_id = await game_server.register_client(websocket)
        
        # WebSocket mesajlarını dinle
        async for message in websocket:
            await game_server.handle_message(client_id, websocket, message)
            
    except websockets.exceptions.InvalidMessage:
        # Geçersiz WebSocket mesajı - sessizce kapat
        pass
    except websockets.exceptions.ConnectionClosed:
        # Bağlantı kapandı - normal durum
        pass
    except Exception as e:
        # Beklenmeyen hata
        if "client_id" in locals():
            logger.error(f"Unexpected error with client {client_id}: {e}")
    finally:
        # Client varsa temizle
        if "client_id" in locals():
            await game_server.unregister_client(client_id)

async def main():
    """Ana server başlatıcı"""
    # Game loop'u başlat
    game_loop_task = asyncio.create_task(game_server.game_loop())
    
    # Port ayarı - Render için PORT environment variable kullan
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting WebSocket Game Server on ws://{host}:{port}")
    logger.info(f"🌐 HTTP health check available at http://{host}:{port}/health")
    
    try:
        # WebSocket server'ı başlat
        async with websockets.serve(
            handle_client, 
            host, 
            port,
            compression=None,  # Compression kapalı (performans için)
            ping_interval=20,  # Keep-alive ping (20 saniye)
            ping_timeout=10,   # Ping timeout (10 saniye)
            max_size=10 * 1024 * 1024,  # Max mesaj boyutu (10MB)
            max_queue=32,      # Max kuyruk boyutu
            read_limit=2 ** 16,  # Read buffer limiti
            write_limit=2 ** 16  # Write buffer limiti
        ):
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
