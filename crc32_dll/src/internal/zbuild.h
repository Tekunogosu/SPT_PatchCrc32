/* zbuild.h -- Build system internal helpers for zlib-ng
 * Copyright (C) 2017-2022 Nathan Moinvaziri
 * For conditions of distribution and use, see copyright notice in zlib.h
 */

#ifndef _ZBUILD_H
#define _ZBUILD_H

#include <stddef.h>
#include <string.h>
#include <stdint.h>

#include "./zarch.h"

#if defined(_MSC_VER)
#  define Z_FORCEINLINE __forceinline
#elif defined(__GNUC__)
#  define Z_FORCEINLINE inline __attribute__((always_inline))
#else
    /* It won't actually force inlining but it will suggest it */
#  define Z_FORCEINLINE inline
#endif

/* MS Visual Studio does not allow inline in C, only C++.
   But it provides __inline instead, so use that. */
#if defined(_MSC_VER) && !defined(inline) && !defined(__cplusplus)
#  define inline __inline
#endif

#define Z_INTERNAL

#define MIN(a, b) ((a) > (b) ? (b) : (a))
#define MAX(a, b) ((a) < (b) ? (b) : (a))
#define Z_UNUSED(var) (void)(var)

#if defined(_MSC_VER) && (_MSC_VER >= 1300)
#  include <stdlib.h>
#  pragma intrinsic(_byteswap_ulong)
#  define ZSWAP16(q) _byteswap_ushort(q)
#  define ZSWAP32(q) _byteswap_ulong(q)
#  define ZSWAP64(q) _byteswap_uint64(q)
#elif defined(__clang__) || (defined(__GNUC__) && \
        (__GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 8)))
#  define ZSWAP16(q) __builtin_bswap16(q)
#  define ZSWAP32(q) __builtin_bswap32(q)
#  define ZSWAP64(q) __builtin_bswap64(q)
#else
#  define ZSWAP16(q) ((((q) & 0xff) << 8) | (((q) & 0xff00) >> 8))
#  define ZSWAP32(q) ((((q) >> 24) & 0xff) + (((q) >> 8) & 0xff00) + \
                       (((q) & 0xff00) << 8) + (((q) & 0xff) << 24))
#  define ZSWAP64(q)                           \
           (((q & 0xFF00000000000000u) >> 56u) | \
            ((q & 0x00FF000000000000u) >> 40u) | \
            ((q & 0x0000FF0000000000u) >> 24u) | \
            ((q & 0x000000FF00000000u) >> 8u)  | \
            ((q & 0x00000000FF000000u) << 8u)  | \
            ((q & 0x0000000000FF0000u) << 24u) | \
            ((q & 0x000000000000FF00u) << 40u) | \
            ((q & 0x00000000000000FFu) << 56u))
#endif

#if defined(_MSC_VER)
#  define ALIGNED_(x) __declspec(align(x))
#elif defined(__GNUC__)
#  define ALIGNED_(x) __attribute__ ((aligned(x)))
#else
#  define ALIGNED_(x)
#endif

#define ALIGN_DIFF(ptr, align) \
    (((uintptr_t)(align) - ((uintptr_t)(ptr) & ((align) - 1))) & ((align) - 1))

#define ALIGN_UP(value, align) \
    (((value) + ((align) - 1)) & ~((align) - 1))

#define ALIGN_DOWN(value, align) \
    ((value) & ~((align) - 1))

#endif
