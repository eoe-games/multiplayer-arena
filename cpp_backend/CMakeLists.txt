cmake_minimum_required(VERSION 3.20)
project(game_game_engine)

# C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compiler flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2")

# Find packages
find_package(PkgConfig REQUIRED)
find_package(Boost REQUIRED COMPONENTS system thread)


# Include directories
include_directories(${Boost_INCLUDE_DIRS})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/external/websocketpp)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/external)  # JSON için


# Add subdirectories
add_subdirectory(engine)
add_subdirectory(server)

# Print info
message(STATUS "🎮 Multiplayer Game Engine")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Boost found: ${Boost_FOUND}")