#pragma once

#include <uWebSockets/App.h>
#include <nlohmann/json.hpp>
#include <map>
#include <vector>
#include <string>
#include <random>
#include <chrono>
#include <thread>
#include <mutex>
#include <iostream>
#include <cmath>

using json = nlohmann::json;

struct Player {
    int id;
    int client_id;
    std::string name;
    float x, y;
    float vx, vy;
    float rotation;
    int health;
    int score;
    bool isBot;
    bool isDead;
    double lastUpdate;
    double lastShot;
    float targetX, targetY;
    double moveTimer;
};

struct GameState {
    std::vector<json> entities;
    int tick;
    double serverTime;
};

class GameServer {
private:
    // WebSocket connections
    std::map<int, uWS::WebSocket<false, true>*> clients;
    std::map<int, Player> players;
    
    // Game state
    GameState gameState;
    int nextClientId;
    int nextBotId;
    double startTime;
    bool running;
    
    // Thread safety
    std::mutex playersMutex;
    std::mutex clientsMutex;
    
    // Random number generation
    std::mt19937 rng;
    std::uniform_int_distribution<> xDist;
    std::uniform_int_distribution<> yDist;
    std::uniform_real_distribution<> floatDist;
    
public:
    GameServer();
    ~GameServer();
    
    void start(int port);
    void stop();
    
    // Connection handling
    int registerClient(uWS::WebSocket<false, true>* ws);
    void unregisterClient(int clientId);
    
    // Message handling
    void handleMessage(int clientId, const std::string& message);
    void handlePlayerJoin(int clientId, const json& data);
    void handlePlayerUpdate(int clientId, const json& data);
    void handlePlayerShoot(const json& data);
    void handlePlayerHit(const json& data);
    void handleChatMessage(const json& data);
    void handleHeartbeat(const json& data);
    
    // Game logic
    void gameLoop();
    void updateBots();
    void spawnBots(int count);
    void respawnPlayer(int playerId);
    
    // Broadcasting
    void broadcast(const json& message, int excludeClient = -1);
    void sendToClient(int clientId, const json& message);
    
    // Utilities
    double getCurrentTime();
    float distance(float x1, float y1, float x2, float y2);
};
