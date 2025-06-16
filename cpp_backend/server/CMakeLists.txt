# Game Server Executable
project(GameServer)

# Include directories
include_directories(include)
include_directories(../shared)
include_directories(../engine/include)
include_directories(../external)

# Source files
set(SERVER_SOURCES
        src/main.cpp
        src/GameServer.cpp
        src/Player.cpp
        src/BattleArena.cpp
)

# Create executable
add_executable(GameServer ${SERVER_SOURCES})

# Link libraries
target_link_libraries(GameServer
        GameEngine
        ${Boost_LIBRARIES}
        pthread
)

# macOS specific
if(APPLE)
    target_compile_definitions(GameServer PRIVATE _WEBSOCKETPP_CPP11_STL_)
endif()

message(STATUS "🖥️ Game Server configured")