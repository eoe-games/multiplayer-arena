#include <iostream>
#include "GameServer.h"

using namespace GameEngine;

int main() {
    std::cout << "🎮 Multiplayer Game Engine Starting..." << std::endl;

    // Create and start server
    GameServer server;
    server.start(8080);

    // Run for 10 seconds
    std::cout << "⏱️ Running for 10 seconds..." << std::endl;
    std::this_thread::sleep_for(std::chrono::seconds(10));

    // Stop server
    server.stop();

    std::cout << "✅ Server stopped successfully!" << std::endl;

    return 0;
}