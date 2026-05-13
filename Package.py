#!/usr/bin/env python3
"""
SPT_PatchCRC32 Build and Package Script
Converted from PowerShell to Python.
Designed to work on Linux and Windows (requires .NET SDK, CMake, and 7z/zip).
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# ==========================================
# CONFIGURATION - EDIT THESE VARIABLES
# ==========================================
CONFIG = {
    # Paths relative to the script location
    "script_root": None,  # Auto-detected
    "references_client_dir": "References/Client",
    "csharp_project_path": "SPT_PatchCRC32.Plugin/SPT_PatchCRC32.Plugin.csproj",
    "csharp_artifact_dir": "SPT_PatchCRC32.Plugin/artifact",
    "csharp_fallback_artifact_dir": "SPT_PatchCRC32.Plugin/bin/Release/netstandard2.1",
    "native_src_dir": "crc32_dll",
    "native_build_dir": "crc32_dll/build",
    "native_expected_dll": "crc32_dll/build/bin/libcrc32_pclmulqdq.dll",
    "package_base_dir": "Package",
    "plugin_target_subdir": "BepInEx/plugins/s8_SPT_PatchCRC32",
    
    # Executables to check for
    "dotnet_cmd": "dotnet",
    "cmake_cmd": "cmake",
    "archiver_cmd": "7z",  # Falls back to 'zip' if not found
    
    # Archive settings
    "version": "1.0.0",
    "base_archive_name": "s8_SPT_PatchCRC32",
    
    # Flags
    "skip_build": False,
    "skip_clean": False,
    "run_tests": False,
}

# ==========================================
# LOGGING UTILITIES
# ==========================================
def log(message, color="white"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {
        "white": "\033[97m",
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "gray": "\033[90m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}[{timestamp}] {message}{colors['reset']}")

def success(msg): log(msg, "green")
def error(msg): log(msg, "red")
def warning(msg): log(msg, "yellow")
def info(msg): log(msg, "cyan")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def check_executable(cmd):
    """Check if a command exists in PATH using shutil.which()."""
    result = shutil.which(cmd)
    if result:
        log(f"  Found at: {result}", "gray")
        return True
    return False

def run_command(cmd_list, cwd=None, capture=False):
    """Run a shell command with better error handling."""
    try:
        # Debug: show what we're trying to run
        info(f"Running: {' '.join(cmd_list)}")
        if cwd:
            info(f"  Working directory: {cwd}")
        
        if capture:
            result = subprocess.run(cmd_list, cwd=cwd, check=True, capture_output=True, text=True)
            return result.stdout
        else:
            subprocess.run(cmd_list, cwd=cwd, check=True)
            return True
    except FileNotFoundError as e:
        error(f"Command not found: {cmd_list[0]}")
        error(f"Error details: {e}")
        error("Check that the executable is in your PATH")
        return False
    except subprocess.CalledProcessError as e:
        error(f"Command failed with exit code {e.returncode}")
        if hasattr(e, 'stderr') and e.stderr:
            error(f"Stderr: {e.stderr[:500]}")
        return False
    except Exception as e:
        error(f"Unexpected error running command: {e}")
        return False

def find_files(directory, pattern):
    """Find files recursively matching a pattern."""
    path = Path(directory)
    if not path.exists():
        return []
    return list(path.rglob(pattern))

# ==========================================
# CORE FUNCTIONS
# ==========================================

def check_prerequisites():
    info("Checking prerequisites...")
    
    # Check References\Client
    ref_dir = Path(CONFIG["script_root"]) / CONFIG["references_client_dir"]
    if not ref_dir.exists():
        error(f"References client folder not found: {ref_dir}")
        error("Please run the reference copying script first.")
        return False
    
    dlls = find_files(ref_dir, "*.dll")
    if not dlls:
        error(f"No DLLs found in {ref_dir}")
        return False
    success(f"Found {len(dlls)} DLLs in References/Client")

    # Check dotnet
    if not check_executable(CONFIG["dotnet_cmd"]):
        error(f"{CONFIG['dotnet_cmd']} not found. Please install .NET SDK and add to PATH.")
        return False
    success(f"{CONFIG['dotnet_cmd']} found")

    # Check cmake
    if not check_executable(CONFIG["cmake_cmd"]):
        error(f"{CONFIG['cmake_cmd']} not found. Please install CMake and add to PATH.")
        return False
    success(f"{CONFIG['cmake_cmd']} found")

    # Check archiver
    archiver = CONFIG["archiver_cmd"]
    if not check_executable(archiver):
        warning(f"{archiver} not found. Falling back to 'zip'.")
        CONFIG["archiver_cmd"] = "zip"
        if not check_executable("zip"):
            error("'zip' command not found. Cannot create archive.")
            return False
    success(f"Archiver found: {CONFIG['archiver_cmd']}")

    return True

def build_csharp_plugin():
    info("Building C# plugin...")
    csproj = Path(CONFIG["script_root"]) / CONFIG["csharp_project_path"]
    
    if not csproj.exists():
        error(f"C# project not found: {csproj}")
        return False

    # args = ["dotnet", "build", str(csproj), "--configuration", "Release"]
    args = ["dotnet", "build", str(csproj), "--configuration", "Release", "/p:AllowUnsafeBlocks=true"]
    
    if not run_command(args):
        error("C# build failed!")
        return False
    
    success("C# plugin built successfully")
    return True

def build_native_dll():
    info("Building native CRC32 DLL...")
    src_dir = Path(CONFIG["script_root"]) / CONFIG["native_src_dir"]
    build_dir = Path(CONFIG["script_root"]) / CONFIG["native_build_dir"]

    if not src_dir.exists():
        error(f"Native source folder not found: {src_dir}")
        return False

    # Create build dir
    build_dir.mkdir(parents=True, exist_ok=True)

    # Detect OS to handle toolchain differences
    import platform
    is_linux = platform.system() == "Linux"

    if is_linux:
        info("Detected Linux. Bypassing Windows MinGW preset. Using native toolchain...")
        
        # Clean build dir to ensure fresh config
        if build_dir.exists():
            shutil.rmtree(build_dir)
            build_dir.mkdir()

        # Configure CMake directly (Unix Makefiles)
        # We explicitly set CMAKE_BUILD_TYPE to Release
        info("Configuring CMake with Unix Makefiles...")
        configure_args = [
            CONFIG["cmake_cmd"],
            "-G", "Unix Makefiles",
            "-DCMAKE_BUILD_TYPE=Release",
            str(src_dir)
        ]
        
        if not run_command(configure_args, cwd=build_dir):
            error("CMake configuration failed!")
            return False

        # Build
        info("Building with CMake...")
        build_args = [CONFIG["cmake_cmd"], "--build", str(build_dir), "--config", "Release"]
        if not run_command(build_args):
            error("Native DLL build failed!")
            return False
            
    else:
        # Original Windows logic using Presets
        preset_file = src_dir / "CMakePresets.json"
        if not preset_file.exists():
            error("CMakePresets.json not found. Aborting.")
            return False

        info("Found CMakePresets.json — using preset 'default' to configure")
        if not run_command([CONFIG["cmake_cmd"], "--preset", "default"], cwd=src_dir):
            error("CMake preset configuration failed!")
            return False

        info("Building with CMake...")
        build_args = [CONFIG["cmake_cmd"], "--build", str(build_dir), "--config", "Release"]
        if not run_command(build_args):
            error("Native DLL build failed!")
            return False

    success("Native DLL built successfully")
    return True

def run_tests():
    info("Running C# crc32 tests...")
    build_dir = Path(CONFIG["script_root"]) / CONFIG["native_build_dir"]
    
    if not build_dir.exists():
        error("Build directory not found.")
        return False

    log_file = build_dir / "test-output.log"
    if log_file.exists():
        log_file.unlink()

    info("Invoking CMake target: test_csharp")
    args = [CONFIG["cmake_cmd"], "--build", str(build_dir), "--target", "test_csharp", "--config", "Release", "--no-restore"]
    

    try:
        with open(log_file, "w") as f:
            subprocess.run(args, check=True, stdout=f, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        error("Test run failed. See log.")
        if log_file.exists():
            with open(log_file, "r") as f:
                lines = f.readlines()
                print("".join(lines[-50:]))
        return False

    success("Tests completed successfully.")
    return True

def create_package():
    info("Creating package...")
    base_pkg = Path(CONFIG["script_root"]) / CONFIG["package_base_dir"]
    target_dir = base_pkg / CONFIG["plugin_target_subdir"]

    # Clean previous
    if not CONFIG["skip_clean"]:
        if base_pkg.exists():
            info("Cleaning previous package...")
            shutil.rmtree(base_pkg)

    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy C# DLLs
    artifact_dirs = [
        Path(CONFIG["script_root"]) / CONFIG["csharp_artifact_dir"],
        Path(CONFIG["script_root"]) / CONFIG["csharp_fallback_artifact_dir"]
    ]
    
    found_dlls = False
    for art_dir in artifact_dirs:
        if art_dir.exists():
            dlls = find_files(art_dir, "*.dll")
            if dlls:
                info(f"Copying C# DLLs from {art_dir}")
                for d in dlls:
                    shutil.copy(d, target_dir / d.name)
                found_dlls = True
                break
    
    if not found_dlls:
        error("No C# DLLs found in artifact directories.")
        return False
    success("C# DLLs copied")

    # Copy Native DLL
    # On Windows: crc32_dll/build/bin/libcrc32_pclmulqdq.dll
    # On Linux:   crc32_dll/build/lib/libcrc32_pclmulqdq.so
    native_src = Path(CONFIG["script_root"]) / CONFIG["native_expected_dll"]
    
    if not native_src.exists():
        # Fallback for Linux: look in 'lib' subfolder for .so files
        bin_dir = Path(CONFIG["script_root"]) / "crc32_dll/build/lib"
        if bin_dir.exists():
            so_files = list(bin_dir.glob("*.so*"))
            if so_files:
                native_src = so_files[0]
                info(f"Linux detected: Found {native_src.name} in lib/ folder")
            else:
                # Fallback to bin/ if lib/ is empty (just in case)
                bin_dir = Path(CONFIG["script_root"]) / "crc32_dll/build/bin"
                if bin_dir.exists():
                    so_files = list(bin_dir.glob("*.so*"))
                    if so_files:
                        native_src = so_files[0]
                        info(f"Linux detected: Found {native_src.name} in bin/ folder")
        
        if not native_src.exists():
            error(f"Native DLL/So not found in expected locations.")
            return False

    info(f"Copying native library from: {native_src}")
    # Keep the original filename in the package (e.g., libcrc32_pclmulqdq.so)
    shutil.copy(native_src, target_dir / native_src.name)
    success("Native library copied")

    # List contents
    info("Package contents:")
    for item in target_dir.rglob("*"):
        rel = item.relative_to(target_dir)
        print(f"  - {rel}")

    # Create Archive
    ext = ".7z" if CONFIG["archiver_cmd"] == "7z" else ".zip"
    archive_name = f"{CONFIG['base_archive_name']}-v{CONFIG['version']}-win-x86_64{ext}"
    archive_path = Path(CONFIG["script_root"]) / archive_name

    if archive_path.exists():
        archive_path.unlink()

    info(f"Creating {ext} archive...")
    pkg_root = Path(CONFIG["script_root"]) / CONFIG["package_base_dir"]
    
    if CONFIG["archiver_cmd"] == "7z":
        args = ["7z", "a", "-t7z", "-mx9", "-m0=LZMA2", str(archive_path), "BepInEx/*"]
        run_command(args, cwd=pkg_root)
    else:
        args = ["zip", "-r", str(archive_path), "BepInEx"]
        run_command(args, cwd=pkg_root)

    if not archive_path.exists():
        error("Archive creation failed.")
        return False

    success(f"Package created: {archive_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Build and package SPT_PatchCRC32")
    parser.add_argument("--skip-build", action="store_true", help="Skip building projects")
    parser.add_argument("--skip-clean", action="store_true", help="Skip cleaning previous package")
    parser.add_argument("-t", "--tests", action="store_true", help="Run tests")
    parser.add_argument("--version", default="1.0.0", help="Version string")
    
    args = parser.parse_args()

    # Update Config
    CONFIG["script_root"] = Path(__file__).resolve().parent
    CONFIG["skip_build"] = args.skip_build
    CONFIG["skip_clean"] = args.skip_clean
    CONFIG["run_tests"] = args.tests
    CONFIG["version"] = args.version

    log("=== SPT_PatchCRC32 Package Script ===", "cyan")
    log(f"Version: {CONFIG['version']}")
    log("")

    if not check_prerequisites():
        error("Prerequisites check failed.")
        sys.exit(1)

    log("")

    if not CONFIG["skip_build"]:
        if not build_csharp_plugin():
            error("C# build failed.")
            sys.exit(1)
        if not build_native_dll():
            error("Native build failed.")
            sys.exit(1)
    else:
        warning("Skipping build (using existing artifacts)")

    if CONFIG["run_tests"]:
        warning("Test run requested. Tests may take >= 1 minute.")
        if not run_tests():
            error("Tests failed.")
            sys.exit(1)

    log("")

    if not create_package():
        error("Package creation failed.")
        sys.exit(1)

    log("")
    success("=== Build and package completed successfully! ===")
    
    ext = "7z" if CONFIG["archiver_cmd"] == "7z" else "zip"
    final_archive_name = f"{CONFIG['base_archive_name']}-v{CONFIG['version']}-win-x86_64.{ext}"
    log(f"Package location: {Path(CONFIG['script_root']) / final_archive_name}")
    
    log("To install, extract the archive to your SPTarkov root directory.")

if __name__ == "__main__":
    main()
