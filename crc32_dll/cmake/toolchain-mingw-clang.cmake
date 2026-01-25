# Toolchain file that prefers mingw-winlibs-llvm-msvcrt clang if available
# Usage: cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=cmake/toolchain-mingw-clang.cmake

# Target system
set(CMAKE_SYSTEM_NAME Windows CACHE STRING "")

# If scoop is present, prefer its mingw-winlibs-llvm-msvcrt install
if(DEFINED ENV{SCOOP})
  set(_scoop_mingw_path "$ENV{SCOOP}/apps/mingw-winlibs-llvm-msvcrt/current/bin")
else()
  set(_scoop_mingw_path "")
endif()

if(_scoop_mingw_path AND EXISTS "${_scoop_mingw_path}/clang.exe")
  set(CMAKE_C_COMPILER "${_scoop_mingw_path}/clang.exe" CACHE FILEPATH "C compiler (mingw-llvm clang)" FORCE)
  set(CMAKE_CXX_COMPILER "${_scoop_mingw_path}/clang++.exe" CACHE FILEPATH "C++ compiler (mingw-llvm clang++)" FORCE)
  # prefer ninja shipped with the same distribution if present
  if(EXISTS "${_scoop_mingw_path}/ninja.exe")
    set(CMAKE_MAKE_PROGRAM "${_scoop_mingw_path}/ninja.exe" CACHE FILEPATH "Ninja from mingw distribution" FORCE)
  endif()
else()
  # Fallback: find clang/clang++ from PATH
  find_program(_clang_exe NAMES clang clang.exe)
  if(_clang_exe)
    set(CMAKE_C_COMPILER "${_clang_exe}" CACHE FILEPATH "C compiler (found clang)" FORCE)
    get_filename_component(_clang_dir "${_clang_exe}" DIRECTORY)
    if(EXISTS "${_clang_dir}/clang++.exe")
      set(CMAKE_CXX_COMPILER "${_clang_dir}/clang++.exe" CACHE FILEPATH "C++ compiler (found clang++)" FORCE)
    endif()
  endif()
endif()

# Expose a helpful variable to indicate we've set compilers
if(CMAKE_C_COMPILER MATCHES "clang")
  set(USING_MINGW_CLANG TRUE CACHE BOOL "Using mingw-llvm clang for builds" FORCE)
endif()
