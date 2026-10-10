cmake_minimum_required(VERSION 3.15)
project(ani2xcur LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

# --- C core: Windows cursor container parsing -------------------------------
add_library(anicore STATIC
    src/csrc/anicore.c
)
target_include_directories(anicore PUBLIC src/csrc/include)
target_compile_options(anicore PRIVATE -Wall -Wextra)

# --- pybind11 bindings ------------------------------------------------------
pybind11_add_module(_anicore src/csrc/bindings.cpp)
target_link_libraries(_anicore PRIVATE anicore)

install(TARGETS _anicore LIBRARY DESTINATION ani2xcur)
