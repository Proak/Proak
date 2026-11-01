# Builds the engine-independent gameplay rules that ship inside the UE module and runs their tests.
#   cmake -S tests/core -B build/core && cmake --build build/core && ctest --test-dir build/core -V
cmake_minimum_required(VERSION 3.20)
project(ConfessionRulesTests CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(UE_SRC ${CMAKE_CURRENT_LIST_DIR}/../../ue58/Source/Confession)
add_executable(confession_rules_tests
    test_rules.cpp
    ${UE_SRC}/Private/Core/ConfessionRules.cpp)
target_include_directories(confession_rules_tests PRIVATE ${UE_SRC}/Public)
# Approximate UE's strictness: shadowing and implicit narrowing are errors there too.
target_compile_options(confession_rules_tests PRIVATE
    -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion -Werror -fno-exceptions -fno-rtti)
enable_testing()
add_test(NAME confession_rules COMMAND confession_rules_tests)
