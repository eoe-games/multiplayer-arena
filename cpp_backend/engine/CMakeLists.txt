# Game Engine Library
project(GameEngine)

# Include directories
include_directories(include)

# Source files
set(ENGINE_SOURCES
        src/Vector2.cpp
        src/Entity.cpp
        src/World.cpp
        src/PhysicsSystem.cpp
        src/NetworkManager.cpp
)

# Header files
set(ENGINE_HEADERS
        include/Vector2.h
        include/Entity.h
        include/World.h
        include/PhysicsSystem.h
        include/NetworkManager.h
        ../main.cpp
)

# Create static library
add_library(GameEngine STATIC ${ENGINE_SOURCES} ${ENGINE_HEADERS})

# Make headers available to other projects
target_include_directories(GameEngine PUBLIC include)

message(STATUS "📚 Game Engine Library configured")