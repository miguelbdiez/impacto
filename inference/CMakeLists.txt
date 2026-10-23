cmake_minimum_required(VERSION 3.24)
project(impacto_inference LANGUAGES CXX)

# OpenNN is built from source, CPU only. It must be the same OpenNN version Neural Designer used to
# train the model: the parameter file stores a fingerprint of the network layout. Pass a local
# checkout with -DOPENNN_SOURCE_DIR=<path>; otherwise the pinned commit is downloaded from GitHub.
set(OPENNN_GIT_TAG 5aa391cb0b9abf6b8f98a6674cbe3f671846bbac)
set(OPENNN_SOURCE_DIR "" CACHE PATH "Local OpenNN checkout (optional)")

set(OpenNN_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(OpenNN_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(OpenNN_BUILD_BENCHMARKS OFF CACHE BOOL "" FORCE)
set(OpenNN_DISABLE_CUDA ON CACHE BOOL "" FORCE)
set(OpenNN_ENABLE_LTO OFF CACHE BOOL "" FORCE)
set(OpenNN_CPU_TARGET PORTABLE CACHE STRING "" FORCE)

if(OPENNN_SOURCE_DIR)
    add_subdirectory("${OPENNN_SOURCE_DIR}" opennn EXCLUDE_FROM_ALL)
else()
    include(FetchContent)
    FetchContent_Declare(opennn
        GIT_REPOSITORY https://github.com/Artelnics/opennn.git
        GIT_TAG ${OPENNN_GIT_TAG}
        EXCLUDE_FROM_ALL)
    FetchContent_MakeAvailable(opennn)
endif()

add_executable(impacto_predict predict.cpp)
target_link_libraries(impacto_predict PRIVATE opennn)
