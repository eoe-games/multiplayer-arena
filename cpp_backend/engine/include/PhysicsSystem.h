#pragma once
#include "Vector2.h"
#include "Entity.h"
#include <vector>
#include <memory>

namespace GameEngine {

struct CollisionInfo {
    Entity* entityA;
    Entity* entityB;
    Vector2 normal;
    float penetration;
};

class PhysicsSystem {
private:
    float gravity;
    float friction;
    Vector2 worldBounds;

public:
    PhysicsSystem(float worldWidth = 800, float worldHeight = 600)
        : gravity(0.0f),  // Top-down game, no gravity
          friction(0.95f),
          worldBounds(worldWidth, worldHeight) {}

    // Apply physics to entities
    void update(std::vector<std::shared_ptr<Entity>>& entities, float deltaTime)
    {
        void(deltaTime)();
        for (auto& entity : entities) {
            if (!entity->isActive) continue;

            // Apply friction
            entity->velocity *= friction;

            // Update position (done in entity update)

            // Keep entities in bounds
            keepInBounds(entity.get());
        }
    }

    // Boundary checking
    void keepInBounds(Entity* entity) {
        // Left boundary
        if (entity->position.x - entity->radius < 0) {
            entity->position.x = entity->radius;
            entity->velocity.x = std::abs(entity->velocity.x) * 0.5f;
        }
        // Right boundary
        else if (entity->position.x + entity->radius > worldBounds.x) {
            entity->position.x = worldBounds.x - entity->radius;
            entity->velocity.x = -std::abs(entity->velocity.x) * 0.5f;
        }

        // Top boundary
        if (entity->position.y - entity->radius < 0) {
            entity->position.y = entity->radius;
            entity->velocity.y = std::abs(entity->velocity.y) * 0.5f;
        }
        // Bottom boundary
        else if (entity->position.y + entity->radius > worldBounds.y) {
            entity->position.y = worldBounds.y - entity->radius;
            entity->velocity.y = -std::abs(entity->velocity.y) * 0.5f;
        }
    }

    // Advanced collision resolution
    void resolveCollision(Entity* a, Entity* b) {
        Vector2 diff = b->position - a->position;
        float distance = diff.magnitude();

        if (distance == 0) return; // Same position

        Vector2 normal = diff.normalized();
        float penetration = (a->radius + b->radius) - distance;

        // Separate entities
        Vector2 separation = normal * (penetration * 0.5f);
        a->position -= separation;
        b->position += separation;

        // Calculate relative velocity
        Vector2 relativeVel = b->velocity - a->velocity;
        float velocityAlongNormal = relativeVel.dot(normal);

        // Don't resolve if velocities are separating
        if (velocityAlongNormal > 0) return;

        // Calculate restitution (bounciness)
        float restitution = 0.5f;
        float impulse = -(1 + restitution) * velocityAlongNormal;

        // Apply impulse
        Vector2 impulseVector = normal * impulse;
        a->velocity -= impulseVector * 0.5f;
        b->velocity += impulseVector * 0.5f;
    }

    // Setters
    void setWorldBounds(float width, float height) {
        worldBounds = Vector2(width, height);
    }

    void setFriction(float f) {
        friction = std::max(0.0f, std::min(1.0f, f));
    }
};

} // namespace GameEngine