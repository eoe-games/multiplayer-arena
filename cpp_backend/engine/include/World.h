#pragma once
#include "Entity.h"
#include <vector>
#include <memory>
#include <algorithm>

namespace GameEngine {

class World {
private:
    std::vector<std::shared_ptr<Entity>> entities;
    std::vector<std::shared_ptr<Entity>> pendingEntities;

public:
    World() = default;

    // Entity management
    void addEntity(std::shared_ptr<Entity> entity) {
        pendingEntities.push_back(entity);
    }

    void removeEntity(uint32_t id) {
        entities.erase(
            std::remove_if(entities.begin(), entities.end(),
                [id](const std::shared_ptr<Entity>& e) {
                    return e->getId() == id;
                }),
            entities.end()
        );
    }

    std::shared_ptr<Entity> getEntity(uint32_t id) {
        auto it = std::find_if(entities.begin(), entities.end(),
            [id](const std::shared_ptr<Entity>& e) {
                return e->getId() == id;
            });
        return (it != entities.end()) ? *it : nullptr;
    }

    // Update world
    void update(float deltaTime) {
        // Add pending entities
        entities.insert(entities.end(), pendingEntities.begin(), pendingEntities.end());
        pendingEntities.clear();

        // Update all entities
        for (auto& entity : entities) {
            if (entity->isActive) {
                entity->update(deltaTime);
            }
        }

        // Check collisions
        checkCollisions();

        // Remove inactive entities
        entities.erase(
            std::remove_if(entities.begin(), entities.end(),
                [](const std::shared_ptr<Entity>& e) {
                    return !e->isActive;
                }),
            entities.end()
        );
    }

    void checkCollisions() {
        for (size_t i = 0; i < entities.size(); i++) {
            for (size_t j = i + 1; j < entities.size(); j++) {
                if (entities[i]->checkCollision(entities[j].get())) {
                    entities[i]->onCollision(entities[j].get());
                    entities[j]->onCollision(entities[i].get());
                }
            }
        }
    }

    // Getters
    const std::vector<std::shared_ptr<Entity>>& getEntities() const {
        return entities;
    }

    size_t getEntityCount() const {
        return entities.size();
    }
};

} // namespace GameEngine