#pragma once
#include <cmath>
#include <iostream>

namespace GameEngine {

class Vector2 {
public:
    float x, y;

    // Constructors
    Vector2() : x(0), y(0) {}
    Vector2(float x, float y) : x(x), y(y) {}

    // Operator overloads
    Vector2 operator+(const Vector2& other) const {
        return Vector2(x + other.x, y + other.y);
    }

    Vector2 operator-(const Vector2& other) const {
        return Vector2(x - other.x, y - other.y);
    }

    Vector2 operator*(float scalar) const {
        return Vector2(x * scalar, y * scalar);
    }

    Vector2 operator/(float scalar) const {
        return Vector2(x / scalar, y / scalar);
    }

    Vector2& operator+=(const Vector2& other) {
        x += other.x;
        y += other.y;
        return *this;
    }

    Vector2& operator-=(const Vector2& other) {
        x -= other.x;
        y -= other.y;
        return *this;
    }

    Vector2& operator*=(float scalar) {
        x *= scalar;
        y *= scalar;
        return *this;
    }

    Vector2& operator/=(float scalar) {
        x /= scalar;
        y /= scalar;
        return *this;
    }

    // Utility functions
    float magnitude() const {
        return std::sqrt(x * x + y * y);
    }

    float magnitudeSquared() const {
        return x * x + y * y;
    }

    Vector2 normalized() const {
        float mag = magnitude();
        if (mag == 0) return Vector2(0, 0);
        return *this / mag;
    }

    float dot(const Vector2& other) const {
        return x * other.x + y * other.y;
    }

    float distance(const Vector2& other) const {
        return (*this - other).magnitude();
    }

    float distanceSquared(const Vector2& other) const {
        return (*this - other).magnitudeSquared();
    }

    // Static utility functions
    static Vector2 lerp(const Vector2& a, const Vector2& b, float t) {
        return a + (b - a) * t;
    }

    static Vector2 random(float minX, float maxX, float minY, float maxY);
    static Vector2 fromAngle(float angle);
    float toAngle() const;
    Vector2 rotated(float angle) const;
    Vector2 clamped(float maxLength) const;

    // Debug output
    friend std::ostream& operator<<(std::ostream& os, const Vector2& v) {
        os << "(" << v.x << ", " << v.y << ")";
        return os;
    }
};

} // namespace GameEngine
