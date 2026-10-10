/*
 * anicore - Windows cursor container parsing (ANI / ICO / CUR).
 *
 * The core only understands the binary container formats. It does not decode
 * pixels: image payloads are handed back to the caller as raw blobs, and the
 * Python layer decodes them with Pillow.
 */
#ifndef ANICORE_ANICORE_H
#define ANICORE_ANICORE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ANICORE_VERSION_MAJOR 0
#define ANICORE_VERSION_MINOR 1
#define ANICORE_VERSION_PATCH 0

typedef enum {
    ANICORE_OK = 0,
    ANICORE_ERR_FORMAT = 1,
    ANICORE_ERR_OOM = 2,
    ANICORE_ERR_UNSUPPORTED = 3,
} anicore_status;

/* A single raster frame of a cursor. */
typedef struct {
    uint32_t nominal;    /* nominal (directory) size of this image */
    uint32_t width;
    uint32_t height;
    uint32_t hotspot_x;
    uint32_t hotspot_y;
    const uint8_t *blob; /* raw image payload, borrowed from the input buffer */
    size_t blob_size;
} anicore_frame;

/* A parsed cursor: a static cursor has exactly one frame, an animated one has many. */
typedef struct {
    uint32_t width;       /* logical size, from the container header (0 if unknown) */
    uint32_t height;
    uint32_t hotspot_x;
    uint32_t hotspot_y;
    uint32_t frame_count;
    uint32_t *delays_ms;  /* per-frame delay in milliseconds, length == frame_count */
    anicore_frame *frames;
} anicore_cursor;

/* Human readable core version, e.g. "0.1.0". */
const char *anicore_version(void);

/* Human readable description of a status code. */
const char *anicore_strerror(anicore_status status);

/*
 * Parse an ANI / ICO / CUR buffer. The format is detected automatically.
 * On success `out` points at freshly allocated storage owned by the caller and
 * must be released with anicore_free().
 */
anicore_status anicore_parse(const uint8_t *buf, size_t len, anicore_cursor *out);

/* Release storage allocated by anicore_parse(). Safe to call on a zeroed struct. */
void anicore_free(anicore_cursor *cursor);

#ifdef __cplusplus
}
#endif

#endif /* ANICORE_ANICORE_H */
