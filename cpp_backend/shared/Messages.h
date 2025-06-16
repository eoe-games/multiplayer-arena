#pragma once
#include <string>
#include <vector>
#include "Vector2.h"

namespace GameEngine {

    // Message types for network communication
    enum class MessageType : uint8_t {
        // Connection
        CONNECT = 0,
        DISCONNECT = 1,
        PING = 2,
        PONG = 3,

        // Player actions
        PLAYER_JOIN = 10,
        PLAYER_LEAVE = 11,
        PLAYER_INPUT = 12,
        PLAYER_SHOOT = 13,

        // Game state
        WORLD_STATE = 20,
        ENTITY_SPAWN = 21,
        ENTITY_DESTROY = 22,
        ENTITY_UPDATE = 23,

        // Game events
        PLAYER_HIT = 30,
        PLAYER_KILL = 31,
        GAME_OVER = 32,
        CHAT_MESSAGE = 33
    };

    // Input state
    struct InputState {
        bool up = false;
        bool down = false;
        bool left = false;
        bool right = false;
        bool shoot = false;
        float mouseX = 0;
        float mouseY = 0;
        uint32_t timestamp = 0;
    };

    // Entity snapshot for networking
    struct EntitySnapshot {
        uint32_t id;
        uint32_t type;
        Vector2 position;
        Vector2 velocity;
        float rotation = 0;
        float health = 100;
        bool isActive = true;
    };

    // Player info
    struct PlayerInfo {
        uint32_t id;
        std::string name;
        int score = 0;
        int kills = 0;
        int deaths = 0;
        uint32_t ping = 0;
    };

    // World state update
    struct WorldStateMessage {
        uint32_t tick;
        float serverTime;
        std::vector<EntitySnapshot> entities;
        std::vector<PlayerInfo> players;
    };

    // Projectile data
    struct ProjectileData {
        uint32_t shooterId;
        Vector2 origin;
        Vector2 direction;
        float speed = 500.0f;
        float damage = 20.0f;
    };

} // namespace GameEngine