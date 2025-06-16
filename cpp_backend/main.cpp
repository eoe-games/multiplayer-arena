#include <iostream>
#include "Vector2.h"
using namespace std;
using namespace GameEngine;

int main() {
    cout << "🎮 Multiplayer Game Engine Starting..." << endl;

    // Vector2 test
    Vector2 pos(10, 20);
    Vector2 velocity(5, -3);

    cout << "Position: " << pos << endl;
    cout << "Velocity: " << velocity << endl;

    // Movement simulation
    pos += velocity;
    cout << "New Position: " << pos << endl;

    // Distance calculation
    Vector2 target(50, 50);
    float distance = pos.distance(target);
    cout << "Distance to target: " << distance << endl;

    // Normalize test
    Vector2 direction = (target - pos).normalized();
    cout << "Direction to target: " << direction << endl;

    return 0;
}