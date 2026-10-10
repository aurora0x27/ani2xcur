/*
 * anicore - entry point and version helpers.
 *
 * The actual container parsers live in ani.c / ico.c and are wired up in later
 * phases; this file currently exposes the public API surface only.
 */
#include "anicore/anicore.h"

#include <stdlib.h>

#define ANICORE_STRINGIFY_(x) #x
#define ANICORE_STRINGIFY(x) ANICORE_STRINGIFY_(x)

const char *anicore_version(void) {
    return ANICORE_STRINGIFY(ANICORE_VERSION_MAJOR) "." ANICORE_STRINGIFY(
               ANICORE_VERSION_MINOR) "." ANICORE_STRINGIFY(ANICORE_VERSION_PATCH);
}

const char *anicore_strerror(anicore_status status) {
    switch (status) {
        case ANICORE_OK:
            return "ok";
        case ANICORE_ERR_FORMAT:
            return "unrecognized or malformed cursor file";
        case ANICORE_ERR_OOM:
            return "out of memory";
        case ANICORE_ERR_UNSUPPORTED:
            return "unsupported cursor format";
        default:
            return "unknown error";
    }
}

anicore_status anicore_parse(const uint8_t *buf, size_t len, anicore_cursor *out) {
    (void)buf;
    (void)len;
    if (out) {
        *out = (anicore_cursor){0};
    }
    return ANICORE_ERR_UNSUPPORTED;
}

void anicore_free(anicore_cursor *cursor) {
    if (!cursor) {
        return;
    }
    free(cursor->delays_ms);
    free(cursor->frames);
    *cursor = (anicore_cursor){0};
}
