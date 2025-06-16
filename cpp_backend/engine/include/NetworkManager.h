#pragma once
#include <string>
#include <functional>
#include <map>
#include <vector>
#include <cstdint>
#include "../../shared/Messages.h"

namespace GameEngine {

    struct NetworkMessage {
        MessageType type;
        uint32_t clientId;
        std::string data;

        NetworkMessage(MessageType t = MessageType::CONNECT, uint32_t id = 0)
            : type(t), clientId(id) {}
    };

    class NetworkManager {
    protected:
        bool isServer;
        uint32_t localId;
        std::map<MessageType, std::function<void(const NetworkMessage&)>> handlers;

    public:
        NetworkManager(bool server = false)
            : isServer(server), localId(0) {}

        virtual ~NetworkManager() = default;

        virtual void start(int port) = 0;
        virtual void stop() = 0;
        virtual void sendMessage(const NetworkMessage& msg, uint32_t clientId = 0) = 0;
        virtual void broadcast(const NetworkMessage& msg) = 0;
        virtual void update() = 0;

        void registerHandler(MessageType type, std::function<void(const NetworkMessage&)> handler) {
            handlers[type] = handler;
        }

        void processMessage(const NetworkMessage& msg) {
            auto it = handlers.find(msg.type);
            if (it != handlers.end()) {
                it->second(msg);
            }
        }

        bool getIsServer() const { return isServer; }
        uint32_t getLocalId() const { return localId; }
    };

} // namespace GameEngine
