cmake_minimum_required(VERSION 3.10)
project(mt4zmq)

# Force 32-bit build for MT4 compatibility
set(CMAKE_GENERATOR_PLATFORM x86)
set(CMAKE_CXX_STANDARD 11)

# Find ZeroMQ
find_package(PkgConfig)
pkg_check_modules(PC_ZeroMQ QUIET libzmq)

find_path(ZeroMQ_INCLUDE_DIR
    NAMES zmq.hpp
    PATHS ${PC_ZeroMQ_INCLUDE_DIRS}
)

find_library(ZeroMQ_LIBRARY
    NAMES zmq libzmq
    PATHS ${PC_ZeroMQ_LIBRARY_DIRS}
)

# MT4ZMQ DLL
add_library(mt4zmq SHARED
    mt4zmq.cpp
    mt4zmq.h
)

# Include directories
target_include_directories(mt4zmq PRIVATE
    ${ZeroMQ_INCLUDE_DIR}
)

# Link libraries
target_link_libraries(mt4zmq
    ${ZeroMQ_LIBRARY}
    ws2_32
)

# Windows specific settings
if(WIN32)
    target_compile_definitions(mt4zmq PRIVATE
        _WIN32_WINNT=0x0601
        WINVER=0x0601
    )
    
    # Export all symbols
    set_target_properties(mt4zmq PROPERTIES
        WINDOWS_EXPORT_ALL_SYMBOLS TRUE
    )
endif()

# Set output directory
set_target_properties(mt4zmq PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/Debug"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/Release"
)

# Install rules
install(TARGETS mt4zmq
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(FILES mt4zmq.h
    DESTINATION include
)