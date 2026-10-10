/*
 * anicore - internal helpers shared by the container parsers.
 */
#ifndef ANICORE_INTERNAL_H
#define ANICORE_INTERNAL_H

#include <stddef.h>
#include <stdint.h>

#include "anicore/anicore.h"

/* Bounds-checked little-endian reader over a memory buffer. */
typedef struct {
    const uint8_t *data;
    size_t size;
    size_t pos;
    int ok;
} anicore_reader;

static inline void reader_init(anicore_reader *r, const uint8_t *data, size_t size) {
    r->data = data;
    r->size = size;
    r->pos = 0;
    r->ok = 1;
}

static inline int reader_need(const anicore_reader *r, size_t n) {
    return r->ok && n <= r->size - r->pos;
}

static inline uint8_t reader_u8(anicore_reader *r) {
    if (!reader_need(r, 1)) {
        r->ok = 0;
        return 0;
    }
    return r->data[r->pos++];
}

static inline uint16_t reader_u16le(anicore_reader *r) {
    if (!reader_need(r, 2)) {
        r->ok = 0;
        return 0;
    }
    uint16_t v = (uint16_t)(r->data[r->pos] | (r->data[r->pos + 1] << 8));
    r->pos += 2;
    return v;
}

static inline uint32_t reader_u32le(anicore_reader *r) {
    if (!reader_need(r, 4)) {
        r->ok = 0;
        return 0;
    }
    uint32_t v = (uint32_t)r->data[r->pos] | ((uint32_t)r->data[r->pos + 1] << 8) |
                 ((uint32_t)r->data[r->pos + 2] << 16) | ((uint32_t)r->data[r->pos + 3] << 24);
    r->pos += 4;
    return v;
}

/* Borrow `n` bytes and advance; returns NULL and clears `ok` on failure. */
static inline const uint8_t *reader_ptr(anicore_reader *r, size_t n) {
    if (!reader_need(r, n)) {
        r->ok = 0;
        return NULL;
    }
    const uint8_t *p = r->data + r->pos;
    r->pos += n;
    return p;
}

static inline int reader_skip(anicore_reader *r, size_t n) {
    if (!reader_need(r, n)) {
        r->ok = 0;
        return 0;
    }
    r->pos += n;
    return 1;
}

static inline int reader_seek(anicore_reader *r, size_t off) {
    if (!r->ok || off > r->size) {
        r->ok = 0;
        return 0;
    }
    r->pos = off;
    return 1;
}

static inline size_t reader_remaining(const anicore_reader *r) {
    return r->ok ? r->size - r->pos : 0;
}

static inline uint16_t load_u16le(const uint8_t *p) {
    return (uint16_t)(p[0] | (p[1] << 8));
}

static inline uint32_t load_u32le(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static inline void store_u16le(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)(v & 0xff);
    p[1] = (uint8_t)(v >> 8);
}

static inline void store_u32le(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v & 0xff);
    p[1] = (uint8_t)((v >> 8) & 0xff);
    p[2] = (uint8_t)((v >> 16) & 0xff);
    p[3] = (uint8_t)((v >> 24) & 0xff);
}

/* Copy `n` bytes into a fresh allocation (never returns NULL for n == 0). */
uint8_t *anicore_memdup(const uint8_t *src, size_t n);

/*
 * Parse an ICO/CUR buffer into a flat list of single-image rasters, one per
 * directory entry. On success the caller owns `*out_images` (release each
 * image's blob and the array with free()).
 */
anicore_status anicore_ico_read_images(const uint8_t *buf, size_t len, anicore_image **out_images,
                                      uint32_t *out_count);

/* Parse an ICO/CUR buffer as a static cursor (a single frame of all rasters). */
anicore_status anicore_parse_ico(const uint8_t *buf, size_t len, anicore_cursor *out);

/* Parse an ANI (RIFF/ACON) buffer. */
anicore_status anicore_parse_ani(const uint8_t *buf, size_t len, anicore_cursor *out);

#endif /* ANICORE_INTERNAL_H */
