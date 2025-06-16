#pragma once
#include "Vector2.h"
#include <memory>
#include <string>

namespace GameEngine {

class World; // Forward declaration

enum class EntityType {
    NONE,
    PLAYER,
    PROJECTILE,
    WALL,
    POWERUP
};

class Entity {
protected:
    static uint32_t nextId;
    uint32_t id;

public:
    Vector2 position;
    Vector2 velocity;
    float radius;           // Collision radius
    EntityType type;
    bool isActive;
    std::string name;

    // Constructor
    Entity(EntityType type = EntityType::NONE)
        : id(nextId++),
          position(0, 0),
          velocity(0, 0),
          radius(16.0f),
          type(type),
          isActive(true),
          name("Entity_" + std::to_string(id)) {}

    virtual ~Entity() = default;

    // Core functions
    virtual void update(float deltaTime) {
        position += velocity * deltaTime;
    }

    virtual void onCollision(Entity* other) {
        // Override in derived classes
        void(other)();
    }

    // Getters
    uint32_t getId() const { return id; }

    // Collision check
    bool checkCollision(const Entity* other) const
    {
        if (!isActive || !other->isActive) return false;
        float distance = position.distance(other->position);
        return distance < (radius + other->radius);
    }
};

// Concrete entity types
class Player : public Entity {
public:
    float health;
    float maxHealth;
    int score;

    Player() : Entity(EntityType::PLAYER), health(100), maxHealth(100), score(0) {
        radius = 20.0f;
        name = "Player";
    }

    void takeDamage(float damage) {
        health -= damage;
        if (health <= 0) {
            health = 0;
            isActive = false;
        }
    }

    void heal(float amount) {
        health = std::min(health + amount, maxHealth);
    }
};

class Projectile : public Entity
{
public:
    float damage;
    uint32_t ownerId;
    float lifetime;

    Projectile(uint32_t owner)
        : Entity(EntityType::PROJECTILE),
          damage(20.0f),
          ownerId(owner),
          lifetime(5.0f) {
        radius = 5.0f;
        name = "Projectile";
    }

    void update(float deltaTime) override {
        Entity::update(deltaTime);
        lifetime -= deltaTime;
        if (lifetime <= 0) {
            isActive = false;
        }
    }

    void onCollision(Entity* other) override {
        if (other->type == EntityType::PLAYER && other->getId() != ownerId) {
            isActive = false;
        }
    }
};

    // Entity.h'nin sonuna ekle (Projectile class'ından sonra)

    class Explosion : public Entity {
    public:
        float maxRadius;
        float currentRadius;
        float expansionRate;
        float lifetime;

        Explosion(Vector2 pos) : Entity(EntityType::POWERUP) {
            position = pos;
            maxRadius = 50.0f;
            currentRadius = 0.0f;
            expansionRate = 200.0f;
            lifetime = 0.5f;
            name = "Explosion";
        }

        void update(float deltaTime) override {
            lifetime -= deltaTime;
            currentRadius = std::min(currentRadius + expansionRate * deltaTime, maxRadius);

            if (lifetime <= 0) {
                isActive = false;
            }
        }
    };

    // Particle effect
    class Particle : public Entity {
    public:
        float lifetime;
        float maxLifetime;
        Vector2 acceleration;
        float size;

        Particle(Vector2 pos, Vector2 vel) : Entity(EntityType::NONE) {
            position = pos;
            velocity = vel;
            acceleration = Vector2(0, 100); // gravity
            maxLifetime = lifetime = 1.0f;
            size = 3.0f;
            radius = size;
        }

        void update(float deltaTime) override {
            Entity::update(deltaTime);
            velocity += acceleration * deltaTime;
            lifetime -= deltaTime;

            // Fade out
            size = 3.0f * (lifetime / maxLifetime);

            if (lifetime <= 0) {
                isActive = false;
            }
        }
    };


} // namespace GameEngine