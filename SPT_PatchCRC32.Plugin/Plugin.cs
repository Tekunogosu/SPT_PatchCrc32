using BepInEx;
using BepInEx.Logging;
using BepInEx.Configuration;
using HarmonyLib;
using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using UnityEngine;

using SPT.Custom.Utils;

namespace SPT_PatchCRC32.Plugin
{
    [BepInPlugin("com.s8.sptpatchcrc32", "s8", "1.0.0")]
    [BepInDependency("com.SPT.custom", "4.0.0")]
    public unsafe class Plugin : BaseUnityPlugin
    {
        public static ManualLogSource LogSource;
        public static ConfigEntry<bool> DebugCompareConfig;
        public static bool NativeDllAvailable = false;

        // Platform detection
        private static bool IsWindows => RuntimeInformation.IsOSPlatform(OSPlatform.Windows);
        private static bool IsLinux => RuntimeInformation.IsOSPlatform(OSPlatform.Linux);

        // Native function delegate (loaded dynamically)
        public delegate uint Crc32Delegate(uint crc, byte* buf, IntPtr len);
        public static Crc32Delegate _crc32Function;

        // Windows LoadLibrary
        [DllImport("kernel32", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern IntPtr LoadLibrary(string lpFileName);

        [DllImport("kernel32", SetLastError = true)]
        private static extern IntPtr GetProcAddress(IntPtr hModule, string procName);

        [DllImport("kernel32", SetLastError = true)]
        private static extern bool FreeLibrary(IntPtr hModule);

        // Linux dlopen wrapper
        [DllImport("libdl.so.2", EntryPoint = "dlopen", CallingConvention = CallingConvention.Cdecl)]
        private static extern IntPtr NativeLoadLibrary(string path);

        private void Awake()
        {
            LogSource = Logger;
            LogSource.LogInfo("[Crc32 Patch] Crc32 Patch Enabled!");

            DebugCompareConfig = Config.Bind("Crc32", "DebugCompare", false, "When true: run original HashToUInt32 and native DLL and log both results for comparison.");
            LogSource.LogInfo($"[Crc32 Debug] Crc32 DebugCompare = {DebugCompareConfig.Value}");

            if (LoadNativeLibrary())
            {
                NativeDllAvailable = true;
                Harmony.CreateAndPatchAll(Assembly.GetExecutingAssembly());
                LogSource.LogInfo("Harmony patches applied for Crc32 (native library available).");

                LogSource.LogInfo(@"
 Patching CRC function since 2026
 Faster, faster, faster! -- Octane
            EPIC s8
");
            }
            else
            {
                LogSource.LogWarning("Native library not available; skipping Harmony patch and leaving original Crc32 implementation active.");
            }
        }

        private bool LoadNativeLibrary()
        {
            try
            {
                var assemblyDir = Path.GetDirectoryName(typeof(Plugin).Assembly.Location);
                string libName;
                string fullPath;

                if (IsWindows)
                {
                    libName = "libcrc32_pclmulqdq.dll";
                    fullPath = Path.Combine(assemblyDir ?? ".", libName);
                }
                else if (IsLinux)
                {
                    libName = "libcrc32_pclmulqdq.so";
                    fullPath = Path.Combine(assemblyDir ?? ".", libName);
                }
                else
                {
                    LogSource.LogError($"[Crc32 Patch] Unsupported OS platform");
                    return false;
                }

                LogSource.LogInfo($"[Crc32 Patch] Looking for native library: {fullPath}");

                if (!File.Exists(fullPath))
                {
                    LogSource.LogWarning($"[Crc32 Patch] Native library not found at: {fullPath}");
                    return false;
                }

                IntPtr handle;
                if (IsWindows)
                {
                    handle = LoadLibrary(fullPath);
                    if (handle == IntPtr.Zero)
                    {
                        var err = Marshal.GetLastWin32Error();
                        LogSource.LogError($"[Crc32 Patch] Failed to load native library: Win32 error {err}");
                        return false;
                    }
                }
                else
                {
                    handle = NativeLoadLibrary(fullPath);
                    if (handle == IntPtr.Zero)
                    {
                        LogSource.LogError($"[Crc32 Patch] Failed to load native library (dlopen returned null)");
                        return false;
                    }
                }

                IntPtr funcPtr = GetProcAddress(handle, "crc32_pclmulqdq");
                if (funcPtr == IntPtr.Zero)
                {
                    LogSource.LogError($"[Crc32 Patch] Failed to find crc32_pclmulqdq function in library");
                    if (IsWindows) FreeLibrary(handle);
                    return false;
                }

                _crc32Function = Marshal.GetDelegateForFunctionPointer<Crc32Delegate>(funcPtr);
                LogSource.LogInfo($"[Crc32 Patch] Successfully loaded native library: {libName}");
                return true;
            }
            catch (Exception ex)
            {
                LogSource.LogError($"[Crc32 Patch] Error loading native library: {ex.Message}");
                return false;
            }
        }
    }

    [HarmonyPatch(typeof(Crc32), "HashToUInt32")]
    [HarmonyPriority(Priority.First)]
    class Patch_Crc32
    {
        [HarmonyPrefix]
        private static unsafe bool Prefix(ReadOnlySpan<byte> source, ref uint __result)
        {
            if (!SPT_PatchCRC32.Plugin.Plugin.NativeDllAvailable)
                return true;

            bool debug = SPT_PatchCRC32.Plugin.Plugin.DebugCompareConfig?.Value ?? false;
            if (debug)
            {
                return true;
            }

            try
            {
                __result = ComputeNativeCrc(source);
                return false; // Skip original
            }
            catch (Exception ex)
            {
                SPT_PatchCRC32.Plugin.Plugin.LogSource.LogError($"[Crc32 Patch] crc32 native call failed (prefix): {ex.Message}");
                return true; // Fallback to original
            }
        }

        [HarmonyPostfix]
        private static unsafe void Postfix(ReadOnlySpan<byte> source, ref uint __result)
        {
            try
            {
                bool debug = SPT_PatchCRC32.Plugin.Plugin.DebugCompareConfig?.Value ?? false;
                if (!debug) return;

                uint dllResult = ComputeNativeCrc(source);
                uint originalResult = __result;
                bool match = (dllResult == originalResult);
                SPT_PatchCRC32.Plugin.Plugin.LogSource.LogInfo($"[Crc32 Debug Compare] Length={source.Length} Original=0x{originalResult:X8} DLL=0x{dllResult:X8} Match={(match ? "YES" : "NO")}");
            }
            catch (Exception ex)
            {
                SPT_PatchCRC32.Plugin.Plugin.LogSource.LogError($"[Crc32 Patch] crc32 native call failed (postfix): {ex.Message}");
            }
        }

        private static unsafe uint ComputeNativeCrc(ReadOnlySpan<byte> source)
        {
            if (source.Length == 0)
            {
                return SPT_PatchCRC32.Plugin.Plugin._crc32Function(0u, null, IntPtr.Zero);
            }

            ref byte r0 = ref System.Runtime.InteropServices.MemoryMarshal.GetReference(source);
            fixed (byte* p = &r0)
            {
                return SPT_PatchCRC32.Plugin.Plugin._crc32Function(0u, p, (IntPtr)source.Length);
            }
        }
    }
}
