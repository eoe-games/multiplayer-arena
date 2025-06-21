#include "GameServer.hpp"
#include <cstdlib>
#include <fstream>
#include <sstream>

// Per-socket data
struct PerSocketData {
    int clientId;
};

// Simple static file serving
std::string getMimeType(const std::string& path) {
    if (path.ends_with(".html")) return "text/html";
    if (path.ends_with(".css")) return "text/css";
    if (path.ends_with(".js")) return "application/javascript";
    if (path.ends_with(".png")) return "image/png";
    if (path.ends_with(".jpg") || path.ends_with(".jpeg")) return "image/jpeg";
    return "text/plain";
}

std::string readFile(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return "";
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

int main() {
    // Get port from environment or use default
    int port = 8080;
    if (const char* portEnv = std::getenv("PORT")) {
        port = std::atoi(portEnv);
    }
    
    GameServer gameServer;
    
    uWS::App().ws<PerSocketData>("/ws", {
        // WebSocket settings
        .compression = uWS::SHARED_COMPRESSOR,
        .maxPayloadLength = 16 * 1024 * 1024,
        .idleTimeout = 60,
        .maxBackpressure = 1 * 1024 * 1024,
        
        // Connection opened
        .open = [&gameServer](auto* ws) {
            PerSocketData* data = (PerSocketData*)ws->getUserData();
            data->clientId = gameServer.registerClient(ws);
        },
        
        // Message received
        .message = [&gameServer](auto* ws, std::string_view message, uWS::OpCode) {
            PerSocketData* data = (PerSocketData*)ws->getUserData();
            gameServer.handleMessage(data->clientId, std::string(message));
        },
        
        // Connection closed
        .close = [&gameServer](auto* ws, int code, std::string_view message) {
            PerSocketData* data = (PerSocketData*)ws->getUserData();
            gameServer.unregisterClient(data->clientId);
        }
    })
    
    // Health check endpoint
    .get("/health", [](auto* res, auto* req) {
        json health;
        health["status"] = "OK";
        health["timestamp"] = std::chrono::duration<double>(
            std::chrono::steady_clock::now().time_since_epoch()
        ).count();
        
        res->writeHeader("Content-Type", "application/json");
        res->end(health.dump());
    })
    
    .get("/healthz", [](auto* res, auto* req) {
        res->end("OK");
    })
    
    // Serve index.html for root
    .get("/", [](auto* res, auto* req) {
        std::string content = readFile("../client/index.html");
        if (content.empty()) {
            // Fallback HTML if file not found
            content = R"(
<!DOCTYPE html>
<html>
<head>
    <title>Multiplayer Arena</title>
    <style>
        body { 
            font-family: Arial; 
            background: #0a0a0a; 
            color: white; 
            text-align: center; 
            padding: 50px;
            margin: 0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 { 
            color: #00ff88; 
            font-size: 3em;
            margin-bottom: 0.5em;
        }
        .status { 
            background: #1a1a1a;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .online { color: #00ff88; }
        .error { color: #ff6666; }
        code { 
            background: #2a2a2a; 
            padding: 5px 10px; 
            border-radius: 5px;
            font-size: 1.1em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 Multiplayer Arena</h1>
        <div class="status">
            <p class="online">✅ C++ Server is running!</p>
            <p>WebSocket endpoint: <code>ws://localhost:8080/ws</code></p>
        </div>
        <div class="status error">
            <p>⚠️ Client files not found!</p>
            <p>Please make sure client files are in the <code>../client/</code> directory.</p>
        </div>
    </div>
</body>
</html>
            )";
        }
        
        res->writeHeader("Content-Type", "text/html");
        res->end(content);
    })
    
    // Serve static files
    .get("/:file", [](auto* res, auto* req) {
        std::string filename = std::string(req->getParameter(0));
        
        // Security check
        if (filename.find("..") != std::string::npos || filename[0] == '/') {
            res->writeStatus("400 Bad Request");
            res->end("Invalid path");
            return;
        }
        
        std::string filepath = "../client/" + filename;
        std::string content = readFile(filepath);
        
        if (content.empty()) {
            res->writeStatus("404 Not Found");
            res->end("File not found");
            return;
        }
        
        res->writeHeader("Content-Type", getMimeType(filename));
        res->end(content);
    })
    
    .listen(port, [&gameServer, port](auto* token) {
        if (token) {
            std::cout << "🚀 Starting Multiplayer Arena Server (C++)" << std::endl;
            std::cout << "🌐 Host: 0.0.0.0:" << port << std::endl;
            std::cout << "🔌 WebSocket: ws://0.0.0.0:" << port << "/ws" << std::endl;
            std::cout << "💚 Health: http://0.0.0.0:" << port << "/health" << std::endl;
            
            gameServer.start(port);
            
            std::cout << "✅ Server is ready and accepting connections!" << std::endl;
            std::cout << "🤖 Spawned 10 bots" << std::endl;
        } else {
            std::cerr << "❌ Failed to listen on port " << port << std::endl;
            std::exit(1);
        }
    }).run();
    
    std::cout << "🛑 Server stopped" << std::endl;
    return 0;
}
