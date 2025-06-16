#include "Vector2.h"
#include <algorithm>
#include <cstdlib>  // for rand()
#include <cmath>

namespace GameEngine {

    Vector2 Vector2::random(float minX, float maxX, float minY, float maxY) {
        float x = minX + (maxX - minX) * (rand() / float(RAND_MAX));
        float y = minY + (maxY - minY) * (rand() / float(RAND_MAX));
        return Vector2(x, y);
    }

    Vector2 Vector2::fromAngle(float angle) {
        return Vector2(std::cos(angle), std::sin(angle));
    }

    float Vector2::toAngle() const {
        return std::atan2(y, x);
    }

    Vector2 Vector2::rotated(float angle) const {
        float c = std::cos(angle);
        float s = std::sin(angle);
        return Vector2(x * c - y * s, x * s + y * c);
    }

    Vector2 Vector2::clamped(float maxLength) const {
        float len = magnitude();
        if (len > maxLength && len > 0) {
            return (*this) * (maxLength / len);
        }
        return *this;
    }

} // namespace GameEngine
