
#include "GameServer.hpp"

GameServer::GameServer() 
    : nextClientId(1), 
      nextBotId(-1000),
      running(false),
      rng(std::chrono::steady_clock::now().time_since_epoch().count()),
      xDist(200, 1800),
      yDist(200, 1000),
      floatDist(0.0, 1.0) {
    
    gameState.tick = 0;
    gameState.serverTime = 0;
    startTime = getCurrentTime();
}

GameServer::~GameServer() {
    stop();
}

double GameServer::getCurrentTime() {
    return std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()
    ).count();
}

float GameServer::distance(float x1, float y1, float x2, float y2) {
    float dx = x2 - x1;
    float dy = y2 - y1;
    return std::sqrt(dx * dx + dy * dy);
}

void GameServer::start(int port) {
    std::cout << "🚀 Starting Multiplayer Arena Server on port " << port << std::endl;
    running = true;
    
    // Spawn initial bots
    spawnBots(10);
    
    // Start game loop in separate thread
    std::thread gameThread(&GameServer::gameLoop, this);
    gameThread.detach();
}

void GameServer::stop() {
    running = false;
}

int GameServer::registerClient(uWS::WebSocket<false, true>* ws) {
    std::lock_guard<std::mutex> lock(clientsMutex);
    int clientId = nextClientId++;
    clients[clientId] = ws;
    
    std::cout << "✅ Client " << clientId << " connected" << std::endl;
    return clientId;
}

void GameServer::unregisterClient(int clientId) {
    std::lock_guard<std::mutex> lock(clientsMutex);
    
    // Find and remove player
    int playerId = -1;
    {
        std::lock_guard<std::mutex> playerLock(playersMutex);
        for (auto& [id, player] : players) {
            if (player.client_id == clientId) {
                playerId = id;
                break;
            }
        }
        
        if (playerId != -1) {
            std::string playerName = players[playerId].name;
            players.erase(playerId);
            
            // Notify others
            json msg;
            msg["type"] = "PLAYER_LEAVE";
            msg["playerId"] = playerId;
            broadcast(msg);
            
            std::cout << "👋 " << playerName << " (ID: " << playerId << ") left the game" << std::endl;
        }
    }
    
    clients.erase(clientId);
    std::cout << "❌ Client " << clientId << " disconnected" << std::endl;
}

void GameServer::handleMessage(int clientId, const std::string& message) {
    try {
        json data = json::parse(message);
        std::string type = data["type"];
        
        if (type == "PLAYER_JOIN") {
            handlePlayerJoin(clientId, data);
        } else if (type == "PLAYER_UPDATE") {
            handlePlayerUpdate(clientId, data);
        } else if (type == "PLAYER_SHOOT") {
            handlePlayerShoot(data);
        } else if (type == "PLAYER_HIT") {
            handlePlayerHit(data);
        } else if (type == "CHAT_MESSAGE") {
            handleChatMessage(data);
        } else if (type == "HEARTBEAT") {
            handleHeartbeat(data);
        }
    } catch (const std::exception& e) {
        std::cerr << "Error handling message from client " << clientId << ": " << e.what() << std::endl;
    }
}

void GameServer::handlePlayerJoin(int clientId, const json& data) {
    int playerId = data["playerId"];
    std::string playerName = data.value("name", "Player");
    
    Player player;
    player.id = playerId;
    player.client_id = clientId;
    player.name = playerName;
    player.x = xDist(rng);
    player.y = yDist(rng);
    player.vx = 0;
    player.vy = 0;
    player.rotation = 0;
    player.health = 100;
    player.score = 0;
    player.isBot = false;
    player.isDead = false;
    player.lastUpdate = getCurrentTime();
    
    {
        std::lock_guard<std::mutex> lock(playersMutex);
        players[playerId] = player;
    }
    
    // Notify other players
    json joinMsg;
    joinMsg["type"] = "PLAYER_JOIN";
    joinMsg["playerId"] = playerId;
    joinMsg["name"] = playerName;
    joinMsg["x"] = player.x;
    joinMsg["y"] = player.y;
    joinMsg["health"] = player.health;
    joinMsg["score"] = player.score;
    broadcast(joinMsg, clientId);
    
    // Send world state to new player
    json worldState;
    worldState["type"] = "WORLD_STATE";
    worldState["players"] = json::array();
    worldState["tick"] = gameState.tick;
    
    {
        std::lock_guard<std::mutex> lock(playersMutex);
        for (const auto& [id, p] : players) {
            json playerData;
            playerData["id"] = p.id;
            playerData["name"] = p.name;
            playerData["x"] = p.x;
            playerData["y"] = p.y;
            playerData["vx"] = p.vx;
            playerData["vy"] = p.vy;
            playerData["rotation"] = p.rotation;
            playerData["health"] = p.health;
            playerData["score"] = p.score;
            playerData["isBot"] = p.isBot;
            playerData["isDead"] = p.isDead;
            worldState["players"].push_back(playerData);
        }
    }
    
    sendToClient(clientId, worldState);
    std::cout << "🎮 " << playerName << " (ID: " << playerId << ") joined the game" << std::endl;
}

void GameServer::handlePlayerUpdate(int clientId, const json& data) {
    int playerId = data["playerId"];
    
    std::lock_guard<std::mutex> lock(playersMutex);
    auto it = players.find(playerId);
    if (it != players.end() && it->second.client_id == clientId) {
        Player& player = it->second;
        
        float oldX = player.x;
        float oldY = player.y;
        
        player.x = data.value("x", player.x);
        player.y = data.value("y", player.y);
        player.vx = data.value("vx", 0.0f);
        player.vy = data.value("vy", 0.0f);
        player.rotation = data.value("rotation", 0.0f);
        player.lastUpdate = getCurrentTime();
        
        // Broadcast significant position changes
        if (std::abs(oldX - player.x) > 2 || std::abs(oldY - player.y) > 2) {
            json updateMsg;
            updateMsg["type"] = "PLAYER_UPDATE";
            updateMsg["playerId"] = playerId;
            updateMsg["x"] = player.x;
            updateMsg["y"] = player.y;
            updateMsg["vx"] = player.vx;
            updateMsg["vy"] = player.vy;
            updateMsg["rotation"] = player.rotation;
            broadcast(updateMsg, clientId);
        }
    }
}

void GameServer::handlePlayerShoot(const json& data) {
    int shooterId = data["playerId"];
    
    json shootMsg;
    shootMsg["type"] = "PLAYER_SHOOT";
    shootMsg["shooterId"] = shooterId;
    shootMsg["x"] = data["x"];
    shootMsg["y"] = data["y"];
    shootMsg["rotation"] = data["rotation"];
    shootMsg["timestamp"] = getCurrentTime();
    
    broadcast(shootMsg);
}

void GameServer::handlePlayerHit(const json& data) {
    int victimId = data["victimId"];
    int shooterId = data["shooterId"];
    int damage = data.value("damage", 20);
    
    std::lock_guard<std::mutex> lock(playersMutex);
    
    auto victimIt = players.find(victimId);
    auto shooterIt = players.find(shooterId);
    
    if (victimIt != players.end() && shooterIt != players.end()) {
        Player& victim = victimIt->second;
        Player& shooter = shooterIt->second;
        
        if (victim.isDead || victimId == shooterId) return;
        
        victim.health = std::max(0, victim.health - damage);
        
        if (victim.health <= 0) {
            victim.isDead = true;
            shooter.score++;
            
            json deathMsg;
            deathMsg["type"] = "PLAYER_DEATH";
            deathMsg["victimId"] = victimId;
            deathMsg["shooterId"] = shooterId;
            deathMsg["killerName"] = shooter.name;
            deathMsg["victimName"] = victim.name;
            broadcast(deathMsg);
            
            // Schedule respawn
            std::thread([this, victimId]() {
                std::this_thread::sleep_for(std::chrono::seconds(3));
                respawnPlayer(victimId);
            }).detach();
        } else {
            json hitMsg;
            hitMsg["type"] = "PLAYER_HIT";
            hitMsg["victimId"] = victimId;
            hitMsg["health"] = victim.health;
            hitMsg["damage"] = damage;
            broadcast(hitMsg);
        }
    }
}

void GameServer::handleChatMessage(const json& data) {
    json chatMsg;
    chatMsg["type"] = "CHAT_MESSAGE";
    chatMsg["playerId"] = data["playerId"];
    chatMsg["message"] = data["message"];
    chatMsg["timestamp"] = getCurrentTime();
    
    broadcast(chatMsg);
}

void GameServer::handleHeartbeat(const json& data) {
    int playerId = data["playerId"];
    
    std::lock_guard<std::mutex> lock(playersMutex);
    auto it = players.find(playerId);
    if (it != players.end()) {
        it->second.lastUpdate = getCurrentTime();
    }
}

void GameServer::spawnBots(int count) {
    std::lock_guard<std::mutex> lock(playersMutex);
    
    for (int i = 0; i < count; i++) {
        Player bot;
        bot.id = nextBotId--;
        bot.client_id = -1;
        bot.name = "Bot" + std::to_string(std::abs(bot.id));
        bot.x = xDist(rng);
        bot.y = yDist(rng);
        bot.vx = 0;
        bot.vy = 0;
        bot.rotation = 0;
        bot.health = 100;
        bot.score = std::uniform_int_distribution<>(0, 5)(rng);
        bot.isBot = true;
        bot.isDead = false;
        bot.lastUpdate = getCurrentTime();
        bot.lastShot = 0;
        bot.targetX = xDist(rng);
        bot.targetY = yDist(rng);
        bot.moveTimer = 0;
        
        players[bot.id] = bot;
    }
}

void GameServer::updateBots() {
    double currentTime = getCurrentTime();
    
    std::lock_guard<std::mutex> lock(playersMutex);
    
    for (auto& [id, bot] : players) {
        if (!bot.isBot || bot.isDead) continue;
        
        // Update movement target
        if (currentTime - bot.moveTimer > floatDist(rng) * 3 + 2) {
            bot.targetX = xDist(rng);
            bot.targetY = yDist(rng);
            bot.moveTimer = currentTime;
        }
        
        // Move towards target
        float dx = bot.targetX - bot.x;
        float dy = bot.targetY - bot.y;
        float dist = distance(bot.x, bot.y, bot.targetX, bot.targetY);
        
        if (dist > 10) {
            float speed = 150.0f;
            float normalizedDx = dx / dist;
            float normalizedDy = dy / dist;
            
            bot.x += normalizedDx * speed * 0.05f;
            bot.y += normalizedDy * speed * 0.05f;
            bot.vx = normalizedDx * speed;
            bot.vy = normalizedDy * speed;
            bot.rotation = std::atan2(dy, dx);
        } else {
            bot.vx = 0;
            bot.vy = 0;
        }
        
        // Keep in bounds
        bot.x = std::max(50.0f, std::min(1950.0f, bot.x));
        bot.y = std::max(50.0f, std::min(1150.0f, bot.y));
        
        bot.lastUpdate = currentTime;
        
        // Shoot at nearest real player
        if (currentTime - bot.lastShot > floatDist(rng) * 2 + 1) {
            Player* nearestPlayer = nullptr;
            float minDist = 500.0f;
            
            for (auto& [pid, player] : players) {
                if (player.id != bot.id && !player.isBot && !player.isDead && player.health > 0) {
                    float d = distance(bot.x, bot.y, player.x, player.y);
                    if (d < minDist) {
                        minDist = d;
                        nearestPlayer = &player;
                    }
                }
            }
            
            if (nearestPlayer) {
                float dx = nearestPlayer->x - bot.x;
                float dy = nearestPlayer->y - bot.y;
                float shootRotation = std::atan2(dy, dx) + (floatDist(rng) - 0.5f) * 0.4f;
                
                float muzzleOffset = 30.0f;
                float shootX = bot.x + std::cos(shootRotation) * muzzleOffset;
                float shootY = bot.y + std::sin(shootRotation) * muzzleOffset;
                
                bot.lastShot = currentTime;
                
                json shootMsg;
                shootMsg["type"] = "PLAYER_SHOOT";
                shootMsg["shooterId"] = bot.id;
                shootMsg["x"] = shootX;
                shootMsg["y"] = shootY;
                shootMsg["rotation"] = shootRotation;
                shootMsg["timestamp"] = currentTime;
                broadcast(shootMsg);
            }
        }
        
        // Broadcast bot position
        json updateMsg;
        updateMsg["type"] = "PLAYER_UPDATE";
        updateMsg["playerId"] = bot.id;
        updateMsg["x"] = bot.x;
        updateMsg["y"] = bot.y;
        updateMsg["vx"] = bot.vx;
        updateMsg["vy"] = bot.vy;
        updateMsg["rotation"] = bot.rotation;
        broadcast(updateMsg);
    }
}

void GameServer::respawnPlayer(int playerId) {
    std::lock_guard<std::mutex> lock(playersMutex);
    
    auto it = players.find(playerId);
    if (it != players.end()) {
        Player& player = it->second;
        player.health = 100;
        player.isDead = false;
        player.x = xDist(rng);
        player.y = yDist(rng);
        
        json respawnMsg;
        respawnMsg["type"] = "PLAYER_RESPAWN";
        respawnMsg["playerId"] = playerId;
        respawnMsg["x"] = player.x;
        respawnMsg["y"] = player.y;
        respawnMsg["health"] = player.health;
        broadcast(respawnMsg);
    }
}

void GameServer::gameLoop() {
    while (running) {
        auto loopStart = std::chrono::steady_clock::now();
        
        gameState.tick++;
        updateBots();
        
        // Clean up disconnected players
        double currentTime = getCurrentTime();
        std::vector<int> disconnectedPlayers;
        
        {
            std::lock_guard<std::mutex> lock(playersMutex);
            for (const auto& [id, player] : players) {
                if (!player.isBot && currentTime - player.lastUpdate > 30) {
                    disconnectedPlayers.push_back(id);
                }
            }
        }
        
        for (int playerId : disconnectedPlayers) {
            std::cout << "Player " << playerId << " timed out" << std::endl;
            unregisterClient(players[playerId].client_id);
        }
        
        // Send sync message every 2 seconds
        if (gameState.tick % 40 == 0) {
            json syncMsg;
            syncMsg["type"] = "SYNC";
            syncMsg["tick"] = gameState.tick;
            syncMsg["serverTime"] = currentTime;
            
            int playerCount = 0;
            {
                std::lock_guard<std::mutex> lock(playersMutex);
                for (const auto& [id, player] : players) {
                    if (!player.isBot) playerCount++;
                }
            }
            syncMsg["playerCount"] = playerCount;
            
            broadcast(syncMsg);
        }
        
        // Send full world state every 10 seconds
        if (gameState.tick % 200 == 0) {
            json worldState;
            worldState["type"] = "WORLD_STATE";
            worldState["players"] = json::array();
            worldState["tick"] = gameState.tick;
            worldState["serverTime"] = currentTime;
            
            {
                std::lock_guard<std::mutex> lock(playersMutex);
                for (const auto& [id, player] : players) {
                    json playerData;
                    playerData["id"] = player.id;
                    playerData["name"] = player.name;
                    playerData["x"] = player.x;
                    playerData["y"] = player.y;
                    playerData["vx"] = player.vx;
                    playerData["vy"] = player.vy;
                    playerData["rotation"] = player.rotation;
                    playerData["health"] = player.health;
                    playerData["score"] = player.score;
                    playerData["isBot"] = player.isBot;
                    playerData["isDead"] = player.isDead;
                    worldState["players"].push_back(playerData);
                }
            }
            
            broadcast(worldState);
            std::cout << "Sent world state - " << players.size() << " players online" << std::endl;
        }
        
        // Sleep to maintain 20 FPS
        auto loopEnd = std::chrono::steady_clock::now();
        auto loopDuration = std::chrono::duration_cast<std::chrono::milliseconds>(loopEnd - loopStart);
        if (loopDuration.count() < 50) {
            std::this_thread::sleep_for(std::chrono::milliseconds(50 - loopDuration.count()));
        }
    }
}

void GameServer::broadcast(const json& message, int excludeClient) {
    std::string msgStr = message.dump();
    
    std::lock_guard<std::mutex> lock(clientsMutex);
    std::vector<int> disconnected;
    
    for (const auto& [clientId, ws] : clients) {
        if (clientId != excludeClient) {
            try {
                ws->send(msgStr, uWS::OpCode::TEXT);
            } catch (...) {
                disconnected.push_back(clientId);
            }
        }
    }
    
    // Clean up disconnected clients
    for (int clientId : disconnected) {
        unregisterClient(clientId);
    }
}

void GameServer::sendToClient(int clientId, const json& message) {
    std::lock_guard<std::mutex> lock(clientsMutex);
    auto it = clients.find(clientId);
    if (it != clients.end()) {
        try {
            it->second->send(message.dump(), uWS::OpCode::TEXT);
        } catch (...) {
            unregisterClient(clientId);
        }
    }
}
