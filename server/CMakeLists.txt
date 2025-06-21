cmake_minimum_required(VERSION 3.16)
project(multiplayer-arena)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(Threads REQUIRED)
find_package(ZLIB REQUIRED)

# Download and include dependencies
include(FetchContent)

# uWebSockets
FetchContent_Declare(
    uwebsockets
    GIT_REPOSITORY https://github.com/uNetworking/uWebSockets.git
    GIT_TAG v20.60.0
)

# uSockets (dependency of uWebSockets)
FetchContent_Declare(
    usockets
    GIT_REPOSITORY https://github.com/uNetworking/uSockets.git
    GIT_TAG v0.8.6
)

# nlohmann/json
FetchContent_Declare(
    json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)

FetchContent_MakeAvailable(json)

# Build uSockets
FetchContent_GetProperties(usockets)
if(NOT usockets_POPULATED)
    FetchContent_Populate(usockets)
    
    # Build uSockets library
    add_library(uSockets STATIC
        ${usockets_SOURCE_DIR}/src/bsd.c
        ${usockets_SOURCE_DIR}/src/context.c
        ${usockets_SOURCE_DIR}/src/loop.c
        ${usockets_SOURCE_DIR}/src/socket.c
        ${usockets_SOURCE_DIR}/src/eventing/epoll_kqueue.c
        ${usockets_SOURCE_DIR}/src/eventing/libuv.c
        ${usockets_SOURCE_DIR}/src/crypto/openssl.c
        ${usockets_SOURCE_DIR}/src/crypto/wolfssl.c
    )
    
    target_include_directories(uSockets PUBLIC ${usockets_SOURCE_DIR}/src)
    target_compile_definitions(uSockets PRIVATE LIBUS_USE_EPOLL)
    
    # Link with SSL (optional, disable if not needed)
    find_package(OpenSSL)
    if(OPENSSL_FOUND)
        target_link_libraries(uSockets ${OPENSSL_LIBRARIES})
        target_compile_definitions(uSockets PRIVATE LIBUS_USE_OPENSSL)
    endif()
endif()

# Get uWebSockets
FetchContent_GetProperties(uwebsockets)
if(NOT uwebsockets_POPULATED)
    FetchContent_Populate(uwebsockets)
endif()

# Create executable
add_executable(game_server
    main.cpp
    GameServer.cpp
)

# Include directories
target_include_directories(game_server PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${uwebsockets_SOURCE_DIR}/src
    ${usockets_SOURCE_DIR}/src
)

# Link libraries
target_link_libraries(game_server
    uSockets
    nlohmann_json::nlohmann_json
    Threads::Threads
    ZLIB::ZLIB
)

# Platform-specific settings
if(UNIX AND NOT APPLE)
    target_link_libraries(game_server ${CMAKE_DL_LIBS})
endif()

# Optimization flags for release
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    target_compile_options(game_server PRIVATE -O3 -march=native)
endif()

# Copy client files to build directory
file(COPY ../client DESTINATION ${CMAKE_BINARY_DIR}/../)
