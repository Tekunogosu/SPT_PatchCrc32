#!/usr/bin/env python3
"""
CopyReferences Script - Convert from PowerShell to Python
Copies DLL references from SPTarkov installation to References/Client folder.
Works on Linux and Windows.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION - EDIT THESE VARIABLES
# ==========================================
CONFIG = {
    # Excluded patterns for csproj files
    "excluded_patterns": [
        "Reference_Repo.do_not_save",
        "s8_ModSync_Shared",
        "s8_ModSync.Shared.csproj"
    ],
    # Search paths within SPTarkov for DLLs
    "search_paths": [
        "EscapeFromTarkov_Data/Managed",
        "BepInEx/core",
        "BepInEx/plugins/spt"
    ],
    # Output directory for references
    "client_dir": "References/Client",
}

# ==========================================
# LOGGING FUNCTIONS
# ==========================================
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def error_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {message}")

# ==========================================
# CORE FUNCTIONS
# ==========================================

def find_dll_in_sptarkov(spt_path, dll_name):
    """Search for a DLL in the SPTarkov directory."""
    spt_path = Path(spt_path)
    log(f"Searching for: {dll_name} in {spt_path}")
    
    # Check direct path first
    direct_path = spt_path / dll_name
    if direct_path.exists():
        log(f"Found in direct path: {direct_path}")
        return direct_path
    
    # Check predefined search paths
    for search_path in CONFIG["search_paths"]:
        full_path = spt_path / search_path / dll_name
        log(f"Checking: {full_path}")
        if full_path.exists():
            log(f"Found in: {full_path}")
            return full_path
    
    # Recursive search as fallback
    log(f"Doing recursive search for {dll_name}...")
    try:
        matches = list(spt_path.rglob(dll_name))
        if matches:
            log(f"Found {len(matches)} matches:")
            for match in matches:
                log(f"  - {match}")
            return matches[0]
    except Exception as e:
        error_log(f"Recursive search failed: {e}")
    
    error_log(f"DLL not found: {dll_name}")
    return None

def should_process_csproj(file_path):
    """Check if csproj should be processed (not excluded)."""
    file_str = str(file_path)
    for pattern in CONFIG["excluded_patterns"]:
        if pattern in file_str:
            return False
    return True

def copy_references(spt_path):
    """Main function to copy DLL references."""
    log("Starting reference file copy...")
    log(f"SPTarkov path: {spt_path}")
    
    project_root = Path.cwd()
    log(f"Project root: {project_root}")
    
    # Create client directory
    client_dir = project_root / CONFIG["client_dir"]
    if not client_dir.exists():
        client_dir.mkdir(parents=True)
        log(f"Created directory: {client_dir}")
    else:
        log(f"Directory already exists: {client_dir}")
    
    # Find all csproj files
    csproj_files = [
        p for p in project_root.rglob("*.csproj")
        if should_process_csproj(p)
    ]
    
    log(f"Found {len(csproj_files)} csproj files to process")
    
    copied_files = {}
    failed_files = {}
    processed_projects = {}
    
    for csproj in csproj_files:
        log(f"\nProcessing: {csproj}")
        
        try:
            # Parse csproj XML
            tree = ET.parse(csproj)
            root = tree.getroot()
            
            # Handle XML namespace if present
            ns = {'msb': 'http://schemas.microsoft.com/developer/msbuild/2003'}
            
            # Find all Reference elements
            references = root.findall(".//msb:Reference", ns)
            if not references:
                # Try without namespace
                references = root.findall(".//Reference")
            
            log(f"  Found {len(references)} references")
            
            if len(references) == 0:
                log("  No DLL references found")
            
            for reference in references:
                include = reference.get("Include", "")
                
                if not include:
                    continue
                
                # Determine DLL name
                if include.endswith(".dll"):
                    search_dll = include
                else:
                    # Handle versioned references like "Assembly, Version=1.0.0.0"
                    dll_name = include.split(",")[0]
                    search_dll = f"{dll_name}.dll"
                
                log(f"  Processing reference: {include}")
                log(f"  Searching for DLL: {search_dll}")
                
                # Find and copy DLL
                source_file = find_dll_in_sptarkov(spt_path, search_dll)
                
                if source_file:
                    dest_file = client_dir / search_dll
                    shutil.copy2(source_file, dest_file)
                    log(f"  SUCCESS: Copied {search_dll} -> {client_dir}")
                    copied_files[search_dll] = str(client_dir)
                else:
                    error_log(f"  FAILED: Not found - {search_dll}")
                    failed_files[search_dll] = csproj.name
            
            processed_projects[csproj.name] = str(client_dir)
            
        except ET.ParseError as e:
            error_log(f"Failed to parse {csproj.name}: {e}")
        except Exception as e:
            error_log(f"Failed to process {csproj.name}: {e}")
    
    # Summary report
    log("\n=== PROCESSING SUMMARY ===")
    log(f"Processed {len(processed_projects)} projects:")
    for project, status in processed_projects.items():
        log(f"  - {project} -> {status}")
    
    log("\n=== COPY SUMMARY ===")
    log(f"Successfully copied {len(copied_files)} files")
    log(f"Failed to find {len(failed_files)} files")
    
    if failed_files:
        log("\nFailed files:")
        for file, project in failed_files.items():
            log(f"  - {file} (in {project})")
    
    log("\nNote:")
    log("- Client and Updater projects: DLLs copied from SPTarkov")
    log("- Server and Shared projects: Use NuGet packages/sdk references (no DLLs needed)")
    log("- Shared references are build-time dependencies, not runtime references")
    
    log("Reference copy completed.")

# ==========================================
# MAIN ENTRY POINT
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        description="Copy DLL references from SPTarkov installation to References/Client folder"
    )
    parser.add_argument(
        "spt_path",
        help="Path to your SPTarkov installation directory"
    )
    
    args = parser.parse_args()
    
    # Validate SPTarkov path
    spt_path = Path(args.spt_path)
    if not spt_path.exists():
        error_log(f"SPTarkov path does not exist: {spt_path}")
        sys.exit(1)
    
    if not spt_path.is_dir():
        error_log(f"SPTarkov path is not a directory: {spt_path}")
        sys.exit(1)
    
    try:
        copy_references(str(spt_path))
    except KeyboardInterrupt:
        error_log("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        error_log(f"Script execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
