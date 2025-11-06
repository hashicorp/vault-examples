cmake_minimum_required(VERSION 3.10)
project(vault-cpp-app)

# C++17 표준 설정
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 컴파일 옵션 설정
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2")

# libcurl 찾기
find_package(CURL REQUIRED)

# pthread 찾기
find_package(Threads REQUIRED)

# 실행 파일 생성
add_executable(vault-app
    src/main.cpp
    src/Config.cpp
    src/HttpClient.cpp
    src/VaultClient.cpp
)

# include 디렉토리 추가
target_include_directories(vault-app PRIVATE include)
target_include_directories(vault-app PRIVATE third_party)

# 라이브러리 링크
target_link_libraries(vault-app PRIVATE 
    CURL::libcurl 
    Threads::Threads
)

# 컴파일러별 특정 옵션
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(vault-app PRIVATE -Wpedantic)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(vault-app PRIVATE -Weverything)
endif()

# 디버그 빌드 시 디버그 정보 포함
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_compile_options(vault-app PRIVATE -g)
endif()

# 릴리즈 빌드 시 최적화
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    target_compile_options(vault-app PRIVATE -O3 -DNDEBUG)
endif()
