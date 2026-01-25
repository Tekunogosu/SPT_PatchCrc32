# SPT_PatchCRC32

A high-performance CRC32 patch for SPTarkov that utilizes hardware-accelerated PCLMULQDQ instructions for faster checksum calculations.

## Project Overview

- **Plugin GUID**: com.s8.spt_patchcrc32
- **Plugin Version**: 1.0.0
- **Assembly Version**: 1.7.0
- **Target Framework**: .NET Standard 2.1
- **SPT Dependency**: com.SPT.custom 4.0.0

## Platform Requirements

**This project is exclusively designed for Windows x86_64 platforms.**

It will not work on:
- 32-bit Windows
- Linux/macOS
- ARM architectures (ARM64/x86)

**Hardware Requirements:**
- CPU: Must support SSE4.1 and PCLMULQDQ instructions. 
- In human terms: Unless your CPU was stolen from a museum, you are fine.
- The Litmus Test: If your PC can even launch Escape From Tarkov (let alone play it), your CPU is already way too powerful for this project. If you are capable of getting "Head, Eyes," you are capable of running this plugin.
- (Basically, any Intel CPU after 2010 or AMD CPU after 2011 works perfectly.)


**Software Requirements for Building:**
- .NET SDK (for C# compilation)
- CMake 3.15+ (3.19+ recommended for presets)
- 7-Zip (7z.exe) for packaging
- MinGW-w64 LLVM Clang (recommended) or MSVC

## Features

- Hardware-accelerated CRC32 using PCLMULQDQ instructions (SSE4.1)
- Approximately 1000+ times faster than software-based CRC32 implementation (based on test suite results)
- Seamless integration with BepInEx for SPTarkov
- Optional debug mode for comparing results
- Graceful fallback to original implementation if native DLL is unavailable

## Architecture

This project consists of two main components:

### C# Plugin Layer (BepInEx + Harmony)
- **Location**: `SPT_PatchCRC32.Plugin/`
- **Framework**: BepInEx plugin with Harmony patching
- **Function**: Patches `SPT.Custom.Utils.Crc32.HashToUInt32` method
- **Safety**: Graceful fallback if native DLL fails to load

### Native DLL Layer (Hardware Acceleration)
- **Location**: `crc32_dll/`
- **Implementation**: PCLMULQDQ algorithm from zlib-ng (Intel's original implementation)
- **Build System**: CMake with Ninja generator
- **Algorithm Features**:
  - Parallelized folding for optimal throughput
  - Support for various buffer sizes (small, medium, large)
  - Memory alignment handling for unaligned reads

### Build System
- **C# Plugin**: `dotnet build --configuration Release`
- **Native DLL**: `cmake --preset default` + `cmake --build build`
- **Packaging**: `Package.ps1` orchestrates both builds and creates distribution archive
- **Reference Management**: `CopyReferences.ps1` copies SPTarkov DLLs for building

## Installation

1. Build the project using `Package.ps1`
2. Extract the generated `.7z` archive to your SPTarkov root directory
3. The plugin will be automatically loaded by BepInEx

## Building

### Prerequisites

Before building, you must copy SPTarkov reference DLLs:

```powershell
.\CopyReferences.ps1 -SptPath "C:\Path\To\SPTarkov"
```

This script copies required DLLs from your SPTarkov installation to the `References\Client` folder.

### Build Command

Run the packaging script:

```powershell
.\Package.ps1
```

This will:
1. Build the C# plugin project
2. Build the native CRC32 DLL using CMake
3. Package everything into a BepInEx-compatible structure
4. Create a 7z archive ready for distribution

### Optional: Run Tests

To verify correctness and measure performance:

```powershell
.\Package.ps1 -RunTests
```

**Note:** The test suite can take 1+ minute to complete as it processes data sizes up to 512MB.

## Usage

The plugin automatically patches the CRC32 function in SPTarkov when the native DLL is loaded. No configuration is required.

### Debug Mode

Enable debug comparison mode in BepInEx config (`BepInEx/config/com.s8.spt_patchcrc32.cfg`):

```ini
[Crc32]
DebugCompare = true
```

When enabled, both the original and native CRC32 implementations will run, and results will be logged for comparison.

## Testing

The project includes a comprehensive test suite (`crc32_dll/tests/csharp/Crc32TestSuite.cs`) that:

- Compares three implementations:
  - System.IO.Hashing.Crc32 (Microsoft official - used as basis/truth)
  - SPT C# reference implementation (software-based)
  - Native PCLMULQDQ implementation (hardware-accelerated)
- Tests various data sizes: 1 byte to 512MB
- Tests alignment scenarios: Unaligned (1, 3, 7, 13-byte offsets) and aligned (4, 8, 16, 32-byte boundaries)

### Test Results

Based on the test suite (data sizes 64MB-512MB):
- All three implementations produce **identical** CRC32 results
- Native PCLMULQDQ implementation is approximately **1000+ times faster** than SPT C# implementation
- All alignment scenarios handled correctly

## Credits

### SPT (Single Player Tarkov)

This plugin is designed for [SPT](https://sp-tarkov.com) (Single Player Tarkov) - a modding framework that transforms Escape From Tarkov into a fully offline, single-player experience.

- **Website**: https://sp-tarkov.com
- **Wiki**: https://wiki.sp-tarkov.com
- **GitHub**: https://github.com/sp-tarkov

### zlib-ng

This project incorporates CRC32 implementation code derived from [zlib-ng](https://github.com/zlib-ng/zlib-ng).

```
zlib-ng - Next Generation zlib

Copyright (C) 2021 Nathan Moinvaziri and others
For conditions of distribution and use, see copyright notice in zlib.h
```

The following files in `crc32_dll/src/` and `crc32_dll/include/` contain code from zlib-ng:
- `crc32_pclmulqdq.c` - CRC32 implementation using PCLMULQDQ
- `internal/crc32_pclmulqdq_tpl.h` - Template for PCLMULQDQ/VPCLMULQDQ
- `internal/crc32_braid_p.h` - CRC32 braid algorithm helpers
- `internal/crc32_braid_tbl.h` - CRC32 lookup tables
- `internal/zbuild.h` - Build system helpers
- `internal/zendian.h` - Endianness detection
- `internal/zarch.h` - Architecture detection
- `internal/x86_intrins.h` - X86 intrinsic wrappers
- `include/crc32.h` - CRC32 interface header

### Original PCLMULQDQ Implementation

The PCLMULQDQ CRC32 algorithm was originally developed by Intel Corporation:

```
Copyright (C) 2013 Intel Corporation. All rights reserved.
Copyright (C) 2016 Marian Beermann (support for initial value)
Authors:
    Wajdi Feghali   <wajdi.k.feghali@intel.com>
    Jim Guilford    <james.guilford@intel.com>
    Vinodh Gopal    <vinodh.gopal@intel.com>
    Erdinc Ozturk   <erdinc.ozturk@intel.com>
    Jim Kukunas     <james.t.kukunas@linux.intel.com>
```

## License

This project is provided as-is. The zlib-ng code is distributed under the zlib license. See individual source files for copyright notices.

```
Copyright 2026 s8ga

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## (DLL) Release Built By

>>> clang --version
(built by Brecht Sanders, r3) clang version 19.1.7
Target: x86_64-w64-windows-gnu
Thread model: posix
InstalledDir: C:/Users/[REDACTED]/scoop/apps/mingw-winlibs-llvm-msvcrt/14.2.0-19.1.7-12.0.0-r3/bin


### Technical Implementation Details

**The Bottleneck**
Profiling analysis of the SPT Plugin execution path identified the `CRC32` calculation (For bundle loading) as a significant performance bottleneck. While CRC32 is mathematically simple, it is computed frequently on large datasets, making CPU efficiency critical.

**The Constraint: Legacy Mono Runtime**
Escape From Tarkov runs on a version of the Unity engine that utilizes an older Mono runtime. This environment imposes strict limitations on performance optimization:
- **Poor JIT Optimization:** The Just-In-Time (JIT) compiler in this version of Mono lacks modern features found in .NET Core/5+, specifically **Automatic Vectorization (Auto-SIMD)**.
- **Library Limitations:** Modern high-performance libraries (like `System.IO.Hashing`) rely on runtime intrinsics that are simply unavailable or unoptimized in this environment.

Because the JIT cannot automatically compile C# logic into vector instructions (SSE/AVX), a pure C# implementation—no matter how well-written—remains bound by scalar execution speeds.

**The Solution: Native Bypass**
To overcome the runtime's limitations, this project implements a **Native DLL Interop** solution. By offloading the calculation to an external C library, we bypass the Mono JIT entirely. This allows us to directly call (adopted from zlib-ng) the machine code, explicitly invoking **PCLMULQDQ** hardware instructions to process data in parallel, achieving speeds impossible within the managed environment.

**A Note on SPT Architecture**
I would like to extend my sincere gratitude to the **SPT Development Team**. Working within the constraints of the Tarkov client and the Mono runtime is an immense technical challenge. The original C# usage provided by SPT is robust and well-architected; this plugin simply provides a hardware-specific optimization path that was technically impossible to achieve using the standard managed code available to the SPT core team.