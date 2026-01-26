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
    // first string below is your plugin's GUID, it MUST be unique to any other mod. Read more about it in BepInEx docs. Be sure to update it if you copy this project.
    [BepInPlugin("com.s8.sptpatchcrc32", "s8", "1.0.0")]
    [BepInDependency("com.SPT.custom", "4.0.0")]

    public class Plugin : BaseUnityPlugin
    {
        public static ManualLogSource LogSource;
        // BepInEx config to enable debug compare mode (run both original & native dll and log results)
        public static ConfigEntry<bool> DebugCompareConfig;
        // set to true when native CRC DLL is present and successfully loaded
        public static bool NativeDllAvailable = false;

        [DllImport("kernel32", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern IntPtr LoadLibrary(string lpFileName);

        // BaseUnityPlugin inherits MonoBehaviour, so you can use base unity functions like Awake() and Update()
        private void Awake()
        {
            // save the Logger to public static field so we can use it elsewhere in the project
            LogSource = Logger;
            LogSource.LogInfo("[Crc32 Patch] Crc32 Patch Enabled!");

            // bind debug config: when true, run original HashToUInt32 and our native DLL and log both results for comparison
            DebugCompareConfig = Config.Bind("Crc32", "DebugCompare", false, "When true: run original HashToUInt32 and native DLL and log both results for comparison.");
            LogSource.LogInfo($"[Crc32 Debug] Crc32 DebugCompare = {DebugCompareConfig.Value}");


            // Ensure native crc DLL is loaded from plugin folder so DllImport resolves correctly
            try
            {
                var assemblyDir = Path.GetDirectoryName(typeof(Plugin).Assembly.Location);
                var nativePath = Path.Combine(assemblyDir ?? ".", "libcrc32_pclmulqdq.dll");
                if (File.Exists(nativePath))
                {
                    try
                    {
                        var handle = LoadLibrary(nativePath);
                        if (handle != IntPtr.Zero)
                        {
                            NativeDllAvailable = true;
                            LogSource.LogInfo($"[Crc32 Patch] Loaded native DLL: {nativePath}");
                        }
                        else
                        {
                            var err = Marshal.GetLastWin32Error();
                            LogSource.LogError($"[Crc32 Patch] Failed to load native DLL '{nativePath}': Win32 error {err}");
                        }
                    }
                    catch (Exception ex)
                    {
                        LogSource.LogError($"[Crc32 Patch] Failed to load native DLL '{nativePath}': {ex.Message}");
                    }
                }
                else
                {
                    LogSource.LogWarning($"[Crc32 Patch] Native DLL not found at: {nativePath}");
                }
            }
            catch (Exception ex)
            {
                LogSource.LogError($"Error locating assembly directory for native DLL load: {ex.Message}");
            }

            if (NativeDllAvailable)
            {
                Harmony.CreateAndPatchAll(Assembly.GetExecutingAssembly());
                LogSource.LogInfo("Harmony patches applied for Crc32 (native DLL available).");

                LogSource.LogInfo(@"
 Patching CRC function since 2026
 Faster, faster, faster! -- Octane
            EPIC s8
");

            }
            else
            {
                LogSource.LogWarning("Native DLL not available; skipping Harmony patch and leaving original Crc32 implementation active.");
            }
        }
    }
}

[HarmonyPatch(typeof(Crc32), "HashToUInt32")]
[HarmonyPriority(Priority.First)]

class Patch_Crc32
{
    [DllImport("libcrc32_pclmulqdq.dll", CallingConvention = CallingConvention.Cdecl)]
    private static extern unsafe uint crc32_pclmulqdq(uint crc, byte* buf, IntPtr len);

    private static unsafe uint ComputeDllCrc(ReadOnlySpan<byte> source)
    {
        if (source.Length == 0)
        {
            return crc32_pclmulqdq(0u, null, IntPtr.Zero);
        }

        ref byte r0 = ref System.Runtime.InteropServices.MemoryMarshal.GetReference(source);
        fixed (byte* p = &r0)
        {
            return crc32_pclmulqdq(0u, p, (IntPtr)source.Length);
        }
    }

    [HarmonyPrefix]
    private static unsafe bool Prefix(ReadOnlySpan<byte> source, ref uint __result)
    {
        // Safety: guard in case patch was applied erroneously when native DLL isn't available
        if (!SPT_PatchCRC32.Plugin.Plugin.NativeDllAvailable)
            return true; // let original run

        bool debug = SPT_PatchCRC32.Plugin.Plugin.DebugCompareConfig?.Value ?? false;
        if (debug)
        {
            // In debug compare mode, let original run and compare results in Postfix
            return true;
        }

        // Normal mode: call native DLL and skip original implementation
        try
        {
            __result = ComputeDllCrc(source);
            return false; // skip original
        }
        catch (Exception ex)
        {
            SPT_PatchCRC32.Plugin.Plugin.LogSource.LogError($"[Crc32 Patch] crc32 native call failed (prefix): {ex.Message}");
            return true; // fallback to original method on error
        }
    }

    [HarmonyPostfix]
    private static unsafe void Postfix(ReadOnlySpan<byte> source, ref uint __result)
    {
        // Only run comparison logging if debug compare mode is enabled
        
        try
        {
            bool debug = SPT_PatchCRC32.Plugin.Plugin.DebugCompareConfig?.Value ?? false;
            if (!debug) return;

            uint dllResult = ComputeDllCrc(source);
            uint originalResult = __result;
            bool match = (dllResult == originalResult);
            SPT_PatchCRC32.Plugin.Plugin.LogSource.LogInfo($"[Crc32 Debug Compare] Length={source.Length} Original=0x{originalResult:X8} DLL=0x{dllResult:X8} Match={(match ? "YES" : "NO")}");
        }
        catch (Exception ex)
        {
            SPT_PatchCRC32.Plugin.Plugin.LogSource.LogError($"[Crc32 Patch] crc32 native call failed (postfix): {ex.Message}");
        }
    }
}