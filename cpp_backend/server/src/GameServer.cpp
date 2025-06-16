#include "GameServer.h"
#include <chrono>
#include <random>
#include <cmath>

namespace GameEngine {

GameServer::GameServer()
    : NetworkManager(true),
      running(false),
      physics(800, 600),
      nextPlayerId(1),
      frameCount(0) {}

GameServer::~GameServer() {
    stop();
}

void GameServer::start(int port) {
    std::cout << "🚀 Starting Game Server (Mock Mode) on port " << port << std::endl;
    running = true;
    spawnPlayer();
    spawnPlayer();
    gameThread = std::thread(&GameServer::gameLoop, this);
}

void GameServer::stop() {
    if (running) {
        running = false;
        if (gameThread.joinable()) gameThread.join();
    }
}

void GameServer::sendMessage(const NetworkMessage& msg, uint32_t clientId) {
    std::cout << "📤 Sending message type " << static_cast<int>(msg.type)
              << " to client " << clientId << std::endl;
}

void GameServer::broadcast(const NetworkMessage& msg) {
    std::cout << "📡 Broadcasting message type " << static_cast<int>(msg.type) << std::endl;
}

void GameServer::update() {}

void GameServer::spawnPlayer() {
    auto player = std::make_shared<Player>();
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> disX(100, 700);
    std::uniform_real_distribution<> disY(100, 500);

    player->position = Vector2(disX(gen), disY(gen));
    player->name = "Player " + std::to_string(nextPlayerId);

    players[nextPlayerId] = player;
    world.addEntity(player);

    std::cout << "🎮 Spawned " << player->name << " at " << player->position << std::endl;
    nextPlayerId++;
}

void GameServer::simulatePlayerInput() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> dis(-50, 50);
    for (auto& [id, player] : players) {
        player->velocity = Vector2(dis(gen), dis(gen));
    }
}

void GameServer::gameLoop() {
    auto lastTime = std::chrono::steady_clock::now();
    auto lastSpawnTime = lastTime;
    std::vector<float> frameTimes;
    float avgFrameTime = 0;
    const int PERF_SAMPLE_COUNT = 60;

    while (running) {
        auto currentTime = std::chrono::steady_clock::now();
        float deltaTime = std::chrono::duration<float>(currentTime - lastTime).count();
        lastTime = currentTime;

        frameTimes.push_back(deltaTime);
        if (frameTimes.size() > PERF_SAMPLE_COUNT) frameTimes.erase(frameTimes.begin());

        if (frameCount % 60 == 0 && !frameTimes.empty()) {
            avgFrameTime = 0;
            for (float ft : frameTimes) avgFrameTime += ft;
            avgFrameTime /= frameTimes.size();
        }

        if (std::chrono::duration<float>(currentTime - lastSpawnTime).count() > 10.0f) {
            spawnPowerUp();
            lastSpawnTime = currentTime;
        }

        updateGameLogic(deltaTime);
        auto entities = world.getEntities();
        physics.update(entities, deltaTime);
        world.update(deltaTime);
        checkGameRules();

        if (frameCount % 2 == 0) broadcastWorldState();

        if (frameCount % 300 == 0) {
            float fps = 1.0f / avgFrameTime;
            std::cout << "📊 Performance: " << fps << " FPS | Entities: "
                      << world.getEntityCount() << " | Players: " << players.size() << std::endl;
        }

        frameCount++;

        auto frameTime = std::chrono::duration<float>(
            std::chrono::steady_clock::now() - currentTime
        ).count();
        if (frameTime < 0.016667f) {
            std::this_thread::sleep_for(
                std::chrono::microseconds(static_cast<int>((0.016667f - frameTime) * 1e6))
            );
        }
    }
    std::cout << "🛑 Game loop stopped!" << std::endl;
}

void GameServer::updateGameLogic(float deltaTime) {
    updateAI(deltaTime);
    processInputs();
    updateGameMode(deltaTime);
}

void GameServer::updateAI(float deltaTime) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> dis(-1.0, 1.0);

    for (auto& [id, player] : players) {
        if (id > 1000) {
            std::shared_ptr<Player> nearestEnemy = nullptr;
            float nearestDist = std::numeric_limits<float>::max();
            for (auto& [otherId, other] : players) {
                if (otherId != id && other->isActive) {
                    float dist = player->position.distance(other->position);
                    if (dist < nearestDist) {
                        nearestDist = dist;
                        nearestEnemy = other;
                    }
                }
            }

            if (nearestEnemy) {
                Vector2 dir = (nearestEnemy->position - player->position).normalized();
                player->velocity = dir * 200.0f;
                if (nearestDist < 300.0f) shootProjectile(player, dir);
            } else {
                player->velocity = Vector2(dis(gen) * 100, dis(gen) * 100);
            }
        }
    }
}

void GameServer::shootProjectile(std::shared_ptr<Player> shooter, const Vector2& direction) {
    static uint32_t projectileId = 10000;

    auto projectile = std::make_shared<Projectile>(shooter->getId());
    projectile->position = shooter->position + direction * 30.0f;
    projectile->velocity = direction * 800.0f;
    world.addEntity(projectile);

    NetworkMessage msg(MessageType::PLAYER_SHOOT, shooter->getId());
    msg.data = std::to_string(projectile->position.x) + "," +
               std::to_string(projectile->position.y) + "," +
               std::to_string(direction.x) + "," +
               std::to_string(direction.y);
    broadcast(msg);
}

void GameServer::spawnPowerUp() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> disX(100, 1900);
    std::uniform_real_distribution<> disY(100, 1100);

    auto powerUp = std::make_shared<Entity>(EntityType::POWERUP);
    powerUp->position = Vector2(disX(gen), disY(gen));
    powerUp->radius = 15.0f;
    powerUp->name = "PowerUp";

    world.addEntity(powerUp);
    std::cout << "✨ Spawned power-up at " << powerUp->position << std::endl;
}

void GameServer::checkGameRules() {
    const int SCORE_LIMIT = 20;
    for (auto& [id, player] : players) {
        if (player->score >= SCORE_LIMIT) {
            std::cout << "🏆 " << player->name << " wins with "
                      << player->score << " points!" << std::endl;
            resetGame();
            break;
        }
    }
}

void GameServer::resetGame() {
    for (auto& [id, player] : players) {
        player->score = 0;
        player->health = player->maxHealth;

        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<> disX(100, 1900);
        std::uniform_real_distribution<> disY(100, 1100);

        player->position = Vector2(disX(gen), disY(gen));
    }

    auto entities = world.getEntities();
    for (auto& entity : entities) {
        if (entity->type == EntityType::PROJECTILE) {
            entity->isActive = false;
        }
    }
    std::cout << "🔄 Game reset!" << std::endl;
}

void GameServer::processInputs() {
    // Placeholder for real network input handling
}

void GameServer::updateGameMode(float deltaTime) {
    // Placeholder for game mode logic
}

void GameServer::broadcastWorldState() {
    WorldStateMessage worldState;
    worldState.tick = frameCount;
    worldState.serverTime = std::chrono::duration<float>(
        std::chrono::steady_clock::now().time_since_epoch()
    ).count();

    auto entities = world.getEntities();
    for (const auto& entity : entities) {
        EntitySnapshot snapshot;
        snapshot.id = entity->getId();
        snapshot.type = static_cast<uint32_t>(entity->type);
        snapshot.position = entity->position;
        snapshot.velocity = entity->velocity;
        snapshot.health = 100;
        snapshot.isActive = entity->isActive;

        if (entity->type == EntityType::PLAYER) {
            auto player = std::dynamic_pointer_cast<Player>(entity);
            if (player) snapshot.health = player->health;
        }

        worldState.entities.push_back(snapshot);
    }

    for (const auto& [id, player] : players) {
        PlayerInfo info;
        info.id = id;
        info.name = player->name;
        info.score = player->score;
        info.kills = player->score;
        info.deaths = 0;
        info.ping = 20 + (id % 30);
        worldState.players.push_back(info);
    }

    if (frameCount % 300 == 0) {
        std::cout << "📡 Broadcasting world state: "
                  << worldState.entities.size() << " entities, "
                  << worldState.players.size() << " players" << std::endl;
    }
}

} // namespace GameEngine
