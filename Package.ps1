<#
.SYNOPSIS
    Build and package SPT_PatchCRC32 plugin for distribution

.DESCRIPTION
    This script builds all projects (C# plugin and native DLL), packages them
    into BepInEx-compatible structure, and creates a 7z archive.

.PREREQUISITES
    Before running this script, you MUST copy required reference DLLs:

    1. Run CopyReferences.ps1 with your SPTarkov path:
       .\CopyReferences.ps1 -SptPath "C:\Path\To\SPTarkov"

    2. This will copy all necessary DLLs to References\Client folder

    3. Ensure both 7z (7-Zip) and CMake are installed and available in PATH
#>

param(
    [switch]$SkipBuild,
    [switch]$SkipClean,
    [Alias("t")][switch]$RunTests,
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = $PSScriptRoot

# Logging functions
function Write-Log {
    param([string]$Message, [string]$ForegroundColor = "White")
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $ForegroundColor
}

function Write-Success { param([string]$Message) Write-Log $Message "Green" }
function Write-Error { param([string]$Message) Write-Log $Message "Red" }
function Write-Warning { param([string]$Message) Write-Log $Message "Yellow" }
function Write-Info { param([string]$Message) Write-Log $Message "Cyan" }

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check if References\Client exists and has DLLs
    $referencesDir = Join-Path $ScriptRoot "References\Client"
    if (-not (Test-Path $referencesDir)) {
        Write-Error "References\Client folder not found!"
        Write-Error "Please run: .\CopyReferences.ps1 -SptPath `"C:\Path\To\SPTarkov`""
        return $false
    }

    $dllFiles = Get-ChildItem -Path $referencesDir -Filter "*.dll"
    if ($dllFiles.Count -eq 0) {
        Write-Error "No DLLs found in References\Client folder!"
        Write-Error "Please run: .\CopyReferences.ps1 -SptPath `"C:\Path\To\SPTarkov`""
        return $false
    }
    Write-Success "Found $($dllFiles.Count) DLLs in References\Client"

    # Check if dotnet is available
    try {
        $dotnetVersion = dotnet --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "dotnet found: $dotnetVersion"
        } else {
            Write-Error "dotnet not found or not working properly"
            return $false
        }
    } catch {
        Write-Error "dotnet not found. Please install .NET SDK"
        return $false
    }

    # Check if cmake is available
    try {
        $cmakeVersion = cmake --version 2>&1 | Select-Object -First 1
        Write-Success "cmake found: $cmakeVersion"
    } catch {
        Write-Error "cmake not found. Please install CMake and add to PATH"
        return $false
    }

    # Check if 7z is available
    try {
        $sevenZipVersion = 7z 2>&1 | Select-Object -First 1
        Write-Success "7z found"
    } catch {
        Write-Error "7z (7-Zip) not found. Please install 7-Zip and add to PATH"
        return $false
    }

    return $true
}

# Build C# plugin
function Build-CSharpPlugin {
    Write-Info "Building C# plugin..."

    $csprojPath = Join-Path $ScriptRoot "SPT_PatchCRC32.Plugin\SPT_PatchCRC32.Plugin.csproj"

    if (-not (Test-Path $csprojPath)) {
        Write-Error "C# project not found: $csprojPath"
        return $false
    }

    $buildArgs = @(
        "build",
        $csprojPath,
        "--configuration", "Release",
        "--no-restore"
    )

    Write-Info "Running: dotnet $($buildArgs -join ' ')"
    $result = & dotnet @buildArgs 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Error "C# build failed!"
        Write-Error $result
        return $false
    }

    Write-Success "C# plugin built successfully"
    return $true
}

# Build native DLL
function Build-NativeDll {
    Write-Info "Building native CRC32 DLL..."

    $crc32Dir = Join-Path $ScriptRoot "crc32_dll"
    $buildDir = Join-Path $crc32Dir "build"

    if (-not (Test-Path $crc32Dir)) {
        Write-Error "crc32_dll folder not found: $crc32Dir"
        return $false
    }

    # Create build directory
    if (-not (Test-Path $buildDir)) {
        New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
        Write-Info "Created build directory: $buildDir"
    }

    # Configure CMake: prefer presets/toolchain if available
    Push-Location $crc32Dir
    try {
        # Fail-fast: require preset to exist, do not try fallbacks
        if (-not (Test-Path (Join-Path $crc32Dir "CMakePresets.json"))) {
            Write-Error "CMakePresets.json not found — cannot determine toolchain. Aborting."
            Pop-Location
            return $false
        }

        Write-Info "Found CMakePresets.json — using preset 'default' to configure"
        Write-Info "Running: cmake --preset default"
        $result = & cmake --preset default 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "CMake preset configuration failed!"
            Write-Error $result
            Pop-Location
            return $false
        }
    } finally {
        Pop-Location
    }

    # Build using CMake (works for Ninja or Visual Studio multi-config)
    Write-Info "Building with CMake..."
    $buildCmakeArgs = @(
        "--build", $buildDir,
        "--config", "Release"
    )

    Write-Info "Running: cmake --build $($buildCmakeArgs -join ' ')"
    $result = & cmake @buildCmakeArgs 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Native DLL build failed!"
        Write-Error $result
        return $false
    }

    Write-Success "Native DLL built successfully"
    return $true
}

function Run-Tests {
    Write-Info "Running C# crc32 tests (this may take at least 1 minute)..."
    Write-Warning "WARNING: Running the test suite can take >= 1 minute. Proceeding..."

    $crc32Dir = Join-Path $ScriptRoot "crc32_dll"
    $buildDir = Join-Path $crc32Dir "build"

    if (-not (Test-Path $buildDir)) {
        Write-Error "Build directory not found: $buildDir. Aborting."
        return $false
    }

    # Prepare log file
    $logFile = Join-Path $buildDir "test-output.log"
    if (Test-Path $logFile) { Remove-Item $logFile -Force }

    # Build and run the C# test target defined in CMakeLists (test_csharp)
    Write-Info "Invoking CMake target: test_csharp"
    $cmakeArgs = @("--build", $buildDir, "--target", "test_csharp", "--config", "Release")
    Write-Info "Running: cmake $($cmakeArgs -join ' ')"

    # Stream output live to console and also save to log file
    & cmake @cmakeArgs 2>&1 | Tee-Object -FilePath $logFile
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Error "Test run failed (exit code $exitCode). See log: $logFile"
        Write-Info "Last 200 lines of test output:"
        Get-Content $logFile -Tail 200 | ForEach-Object { Write-Host $_ }
        return $false
    }

    Write-Success "Test run completed successfully. Full output saved to: $logFile"
    Write-Info "Last 50 lines of test output:"
    Get-Content $logFile -Tail 50 | ForEach-Object { Write-Host $_ }

    return $true
}

# Package everything
function New-Package {
    Write-Info "Creating package..."

    $packageDir = Join-Path $ScriptRoot "Package\s8_SPT_PatchCRC32"
    $targetDir = Join-Path $ScriptRoot "Package\BepInEx\plugins\s8_SPT_PatchCRC32"

    # Clean previous package
    if (-not $SkipClean) {
        Write-Info "Cleaning previous package..."
        if (Test-Path (Join-Path $ScriptRoot "Package")) {
            try {
                Remove-Item -Path (Join-Path $ScriptRoot "Package") -Recurse -Force -ErrorAction Stop
            } catch {
                Write-Error "Failed to remove previous package directory: $($_.Exception.Message)"
                return $false
            }
        }
    }

    # Create directories
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

    # Copy C# plugin files from artifact — only DLLs to avoid nested plugin dir
    $artifactDir = Join-Path $ScriptRoot "SPT_PatchCRC32.Plugin\artifact"
    if (-not (Test-Path $artifactDir)) {
        Write-Warning "Artifact folder not found, trying bin/Release..."
        $artifactDir = Join-Path $ScriptRoot "SPT_PatchCRC32.Plugin\bin\Release\netstandard2.1"
    }

    if (Test-Path $artifactDir) {
        Write-Info "Copying C# plugin DLL(s) into $targetDir (flatten)"
        # Fail-fast: require at least one DLL to be present
        $dlls = Get-ChildItem -Path $artifactDir -Filter "*.dll" -File -Recurse -ErrorAction SilentlyContinue
        if (-not $dlls -or $dlls.Count -eq 0) {
            Write-Error "No DLLs found in artifact directory ($artifactDir). Aborting."
            return $false
        }

        foreach ($d in $dlls) {
            Write-Info "  - Copying $($d.Name)"
            Copy-Item -Path $d.FullName -Destination (Join-Path $targetDir $d.Name) -Force
        }

        Write-Success "C# plugin DLL(s) copied"
    } else {
        Write-Error "C# plugin output not found at expected path: $artifactDir. Aborting."
        return $false
    }

    # Copy native DLL — fail-fast: expect the Ninja output at build/bin/libcrc32_pclmulqdq.dll
    $expectedDll = [System.IO.Path]::Combine($ScriptRoot,'crc32_dll','build','bin','libcrc32_pclmulqdq.dll')

    if (-not (Test-Path $expectedDll)) {
        Write-Error "Expected native DLL not found at: $expectedDll. Aborting."
        return $false
    }

    Write-Info "Copying native DLL from: $expectedDll"
    Copy-Item -Path $expectedDll -Destination (Join-Path $targetDir "libcrc32_pclmulqdq.dll") -Force
    Write-Success "Native DLL copied"

    # Verify package contents
    Write-Info "Package contents:"
    Get-ChildItem -Path $targetDir -Recurse | ForEach-Object {
        Write-Host "  - $($_.FullName.Replace($targetDir, ''))" -ForegroundColor Gray
    }

    # Create 7z archive
    Write-Info "Creating 7z archive..."
    $archiveName = "s8_SPT_PatchCRC32-v$Version-win-x86_64.7z"
    $archivePath = Join-Path $ScriptRoot $archiveName

    if (Test-Path $archivePath) {
        Remove-Item -Path $archivePath -Force
    }

    $packageRoot = Join-Path $ScriptRoot "Package"
    $7zArgs = @(
        "a",
        "-t7z",
        "-mx9",
        "-m0=LZMA2",
        $archiveName,
        "BepInEx\*"
    )

    Push-Location $packageRoot
    $result = & 7z @7zArgs 2>&1
    Pop-Location

    if ($LASTEXITCODE -ne 0) {
        Write-Error "7z archive creation failed!"
        Write-Error $result
        return $false
    }

    Write-Success "Package created: $archivePath"
    return $true
}

# Main execution
function Main {
    Write-Log "=== SPT_PatchCRC32 Package Script ===" "Cyan"
    Write-Log "Version: $Version"
    Write-Log ""

    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        Write-Error "Prerequisites check failed. Please fix the issues above and try again."
        exit 1
    }

    Write-Log ""

    # Build projects
    if (-not $SkipBuild) {
        if (-not (Build-CSharpPlugin)) {
            Write-Error "C# build failed. Aborting."
            exit 1
        }

        if (-not (Build-NativeDll)) {
            Write-Error "Native DLL build failed. Aborting."
            exit 1
        }
    } else {
        Write-Warning "Skipping build (using existing artifacts)"
    }

    if ($RunTests) {
        Write-Warning "Test run requested (-t). Tests may take >= 1 minute."
        if (-not (Run-Tests)) {
            Write-Error "Tests failed. Aborting."
            exit 1
        }
    }

    Write-Log ""

    # Create package
    if (-not (New-Package)) {
        Write-Error "Package creation failed. Aborting."
        exit 1
    }

    Write-Log ""
    Write-Success "=== Build and package completed successfully! ==="
    Write-Log "Package location: $(Join-Path $ScriptRoot 's8_SPT_PatchCRC32-v$Version-win-x86_64.7z')"
    Write-Log ""
    Write-Log "To install, extract the archive to your SPTarkov root directory."
}

# Run main function
Main
