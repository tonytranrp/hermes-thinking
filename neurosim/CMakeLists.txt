cmake_minimum_required(VERSION 3.23)
project(NeuroSim VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# --- Architecture detection for SIMD ---
include(CheckCXXCompilerFlag)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|amd64|AMD64")
    check_cxx_compiler_flag("-mavx2" HAS_AVX2)
    check_cxx_compiler_flag("-mavx512f" HAS_AVX512)
    if(HAS_AVX512)
        add_compile_definitions(NEUROSIM_AVX512)
        add_compile_options(-mavx512f -mavx512vl)
        message(STATUS "NeuroSim: AVX-512 enabled")
    elseif(HAS_AVX2)
        add_compile_definitions(NEUROSIM_AVX2)
        add_compile_options(-mavx2 -mfma)
        message(STATUS "NeuroSim: AVX2 enabled")
    else()
        add_compile_definitions(NEUROSIM_SCALAR)
        message(STATUS "NeuroSim: Scalar fallback (no AVX)")
    endif()
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|arm64")
    add_compile_definitions(NEUROSIM_NEON)
    message(STATUS "NeuroSim: NEON enabled")
else()
    add_compile_definitions(NEUROSIM_SCALAR)
    message(STATUS "NeuroSim: Scalar fallback")
endif()

# --- Optimization flags ---
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_options(-O3 -flto -march=native)
endif()

# --- Threading ---
find_package(Threads REQUIRED)

# --- Source files ---
set(NEUROSIM_SOURCES
    src/main.cpp
    src/neuron.cpp
    src/network.cpp
    src/scheduler.cpp
    src/synapse.cpp
    src/allocator.cpp
    src/spike_logger.cpp
    src/visualization.cpp
    src/spike_queue.cpp
    src/topology.cpp
    src/perf.cpp
    src/hodgkin_huxley.cpp
    src/plasticity.cpp
)

add_executable(neurosim ${NEUROSIM_SOURCES})
target_include_directories(neurosim PRIVATE ${CMAKE_SOURCE_DIR}/include)

target_link_libraries(neurosim PRIVATE Threads::Threads)

# --- Warnings ---
target_compile_options(neurosim PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion
    -Wno-unused-parameter
)
