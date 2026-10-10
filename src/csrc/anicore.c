/*
 * anicore - public entry point, format detection and cleanup.
 */
#include "anicore/anicore.h"

#include <stdlib.h>
#include <string.h>

#include "internal.h"

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
    if (!buf || !out || len < 6) {
        return ANICORE_ERR_FORMAT;
    }
    *out = (anicore_cursor){0};

    if (len >= 12 && memcmp(buf, "RIFF", 4) == 0 && memcmp(buf + 8, "ACON", 4) == 0) {
        return anicore_parse_ani(buf, len, out);
    }
    return anicore_parse_ico(buf, len, out);
}

void anicore_free(anicore_cursor *cursor) {
    if (!cursor) {
        return;
    }
    for (uint32_t f = 0; f < cursor->frame_count; ++f) {
        anicore_frame *frame = &cursor->frames[f];
        for (uint32_t i = 0; i < frame->image_count; ++i) {
            free((void *)frame->images[i].blob);
        }
        free(frame->images);
    }
    free(cursor->frames);
    *cursor = (anicore_cursor){0};
}
