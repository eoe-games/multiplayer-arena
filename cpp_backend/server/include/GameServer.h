#pragma once

#include <thread>
#include <mutex>
#include <map>
#include <iostream>
#include "World.h"
#include "PhysicsSystem.h"
#include "NetworkManager.h"
#include "Player.h"
#include "Vector2.h"
#include "../../shared/Messages.h"

namespace GameEngine {

    class GameServer : public NetworkManager {
    private:
        bool running;
        std::thread gameThread;

        World world;
        PhysicsSystem physics;
        std::map<uint32_t, std::shared_ptr<Player>> players;
        uint32_t nextPlayerId;
        uint32_t frameCount = 0;

    public:
        GameServer();
        ~GameServer();

        void start(int port) override;
        void stop() override;
        void sendMessage(const NetworkMessage& msg, uint32_t clientId) override;
        void broadcast(const NetworkMessage& msg) override;
        void update() override;

        void gameLoop();
        void spawnPlayer();
        void simulatePlayerInput();

        void updateGameLogic(float deltaTime);
        void updateAI(float deltaTime);
        void shootProjectile(std::shared_ptr<Player> shooter, const Vector2& direction);
        void spawnPowerUp();
        void checkGameRules();
        void resetGame();
        void processInputs();
        void updateGameMode(float deltaTime);
        void broadcastWorldState();
    };

} // namespace GameEngine
