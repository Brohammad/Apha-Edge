# C++ engine RSI indicator scaffolding
# Build with: cmake -B build && cmake --build build

cmake_minimum_required(VERSION 3.16)
project(alphaedge_cpp LANGUAGES CXX)

add_library(alphaedge_indicators STATIC
    src/rsi.cpp
)
target_include_directories(alphaedge_indicators PUBLIC include)
