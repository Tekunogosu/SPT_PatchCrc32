cmake_minimum_required(VERSION 3.15)

# Option: prefer mingw-llvm clang on Windows when available (ON by default)
option(PREFER_MINGW_LLVM_CLANG "Prefer mingw-winlibs-llvm-msvcrt clang/clang++ on Windows if available" ON)

# If enabled and the user hasn't specified a compiler, try to select mingw clang
if(PREFER_MINGW_LLVM_CLANG AND (NOT DEFINED CMAKE_C_COMPILER OR CMAKE_C_COMPILER STREQUAL ""))
  if(WIN32)
    # look for clang in common scoop location or in PATH
    find_program(MINGW_CLANG_EXECUTABLE NAMES clang clang.exe HINTS "$ENV{SCOOP}/apps/mingw-winlibs-llvm-msvcrt/current/bin" "C:/Users/$ENV{USERNAME}/scoop/apps/mingw-winlibs-llvm-msvcrt/current/bin")
    if(MINGW_CLANG_EXECUTABLE)
      message(STATUS "Prefering mingw-llvm clang: ${MINGW_CLANG_EXECUTABLE}")
      set(CMAKE_C_COMPILER "${MINGW_CLANG_EXECUTABLE}" CACHE FILEPATH "C compiler (preferred mingw-llvm clang)" FORCE)
      get_filename_component(_clang_dir "${MINGW_CLANG_EXECUTABLE}" DIRECTORY)
      set(CMAKE_CXX_COMPILER "${_clang_dir}/clang++.exe" CACHE FILEPATH "C++ compiler (preferred mingw-llvm clang++)" FORCE)
    endif()
  endif()
endif()

project(crc32_pclmulqdq C)

set(CMAKE_C_STANDARD 11)

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -O2")

if(MSVC)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
else()
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fPIC -mpclmul -msse4.1 -mssse3")
endif()

add_definitions(-DX86_PCLMULQDQ_CRC -DBUILDING_DLL)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/src/internal
)

# Main library target
add_library(crc32_pclmulqdq SHARED
    src/crc32_pclmulqdq.c
)

# Copy the built library to the C# test folder so tests can find the DLL
add_custom_command(TARGET crc32_pclmulqdq POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:crc32_pclmulqdq>
        ${CMAKE_SOURCE_DIR}/tests/csharp/$<TARGET_FILE_NAME:crc32_pclmulqdq>
    COMMENT "Copying crc32 library to tests/csharp for C# tests"
)

if(WIN32)
    set_target_properties(crc32_pclmulqdq PROPERTIES
        WINDOWS_EXPORT_ALL_SYMBOLS TRUE
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    )
endif()

if(UNIX AND NOT APPLE)
    set_target_properties(crc32_pclmulqdq PROPERTIES
        VERSION 1.0
        SOVERSION 1
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    )
endif()

# Enable testing
enable_testing()


# Custom target to run C# tests
find_program(DOTNET_EXE dotnet)
if(DOTNET_EXE)
    add_custom_target(test_csharp
        COMMAND ${DOTNET_EXE} run --project ${CMAKE_SOURCE_DIR}/tests/csharp/Crc32TestSuite.csproj
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/tests/csharp
        DEPENDS crc32_pclmulqdq
        COMMENT "Running C# test suite..."
    )

    # Add C# tests to main run_ctest target (create run_ctest target if not present)
    add_custom_target(run_ctest DEPENDS test_csharp)
else()
    message(WARNING "dotnet not found. C# tests will not be available.")
endif()


# Print build summary
message(STATUS "")
message(STATUS "==================================================")
message(STATUS "  CRC32 PCLMULQDQ Build Configuration")
message(STATUS "==================================================")
message(STATUS "  Library:   crc32_pclmulqdq")
message(STATUS "  Tests:")
if(DOTNET_EXE)
    message(STATUS "    - C# Test:    Crc32TestSuite")
endif()
message(STATUS "  Build Targets:")
message(STATUS "    - make             : Build library")
if(DOTNET_EXE)
    message(STATUS "    - make test_csharp  : Run C# test suite")
endif()
message(STATUS "==================================================")
message(STATUS "")
