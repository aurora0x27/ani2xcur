/*
 * ico.c - ICO / CUR container parsing.
 *
 * ICO (type 1) and CUR (type 2) share the same layout: a 6 byte header, then a
 * directory of 16 byte entries, each pointing at an image payload that is
 * either a PNG stream or a DIB (BITMAPINFOHEADER). For every directory entry we
 * synthesize a self-contained single-image ICO/CUR so the Python layer can hand
 * the blob straight to Pillow.
 */
#include <stdlib.h>
#include <string.h>

#include "internal.h"

#define ICO_HEADER_SIZE 6
#define ICO_DIR_ENTRY_SIZE 16
#define ICO_TYPE_ICON 1
#define ICO_TYPE_CURSOR 2

typedef struct {
    uint32_t width;
    uint32_t height;
    uint8_t color_count;
    uint16_t field_a; /* planes (ICO) / hotspot_x (CUR) */
    uint16_t field_b; /* bit count (ICO) / hotspot_y (CUR) */
    uint32_t payload_size;
    uint32_t payload_offset;
} ico_entry;

static anicore_status ico_open(const uint8_t *buf, size_t len, uint16_t *out_type,
                               ico_entry **out_entries, uint32_t *out_count) {
    anicore_reader r;
    reader_init(&r, buf, len);

    uint16_t reserved = reader_u16le(&r);
    uint16_t type = reader_u16le(&r);
    uint16_t count = reader_u16le(&r);
    if (!r.ok || reserved != 0 || (type != ICO_TYPE_ICON && type != ICO_TYPE_CURSOR) || count == 0) {
        return ANICORE_ERR_FORMAT;
    }
    if (!reader_need(&r, (size_t)count * ICO_DIR_ENTRY_SIZE)) {
        return ANICORE_ERR_FORMAT;
    }

    ico_entry *entries = (ico_entry *)calloc(count, sizeof(ico_entry));
    if (!entries) {
        return ANICORE_ERR_OOM;
    }

    for (uint32_t i = 0; i < count; ++i) {
        uint8_t width = reader_u8(&r);
        uint8_t height = reader_u8(&r);
        uint8_t colors = reader_u8(&r);
        (void)reader_u8(&r); /* reserved */
        uint16_t field_a = reader_u16le(&r);
        uint16_t field_b = reader_u16le(&r);
        uint32_t payload_size = reader_u32le(&r);
        uint32_t payload_offset = reader_u32le(&r);
        if (!r.ok || (size_t)payload_offset + payload_size > len) {
            free(entries);
            return ANICORE_ERR_FORMAT;
        }
        entries[i].width = width ? width : 256; /* 0 encodes 256 in the directory */
        entries[i].height = height ? height : 256;
        entries[i].color_count = colors;
        entries[i].field_a = field_a;
        entries[i].field_b = field_b;
        entries[i].payload_size = payload_size;
        entries[i].payload_offset = payload_offset;
    }

    *out_type = type;
    *out_entries = entries;
    *out_count = count;
    return ANICORE_OK;
}

/* Build a single-entry ICO/CUR around one payload. The result is malloc'd. */
static anicore_status ico_build_image(const uint8_t *buf, uint16_t type, const ico_entry *e,
                                      anicore_image *out) {
    size_t total = ICO_HEADER_SIZE + ICO_DIR_ENTRY_SIZE + (size_t)e->payload_size;
    uint8_t *blob = (uint8_t *)malloc(total);
    if (!blob) {
        return ANICORE_ERR_OOM;
    }

    store_u16le(blob, 0);      /* reserved */
    store_u16le(blob + 2, type);
    store_u16le(blob + 4, 1);  /* single entry */

    uint8_t *dir = blob + ICO_HEADER_SIZE;
    dir[0] = (uint8_t)(e->width >= 256 ? 0 : e->width);
    dir[1] = (uint8_t)(e->height >= 256 ? 0 : e->height);
    dir[2] = e->color_count;
    dir[3] = 0;
    store_u16le(dir + 4, e->field_a);
    store_u16le(dir + 6, e->field_b);
    store_u32le(dir + 8, e->payload_size);
    store_u32le(dir + 12, ICO_HEADER_SIZE + ICO_DIR_ENTRY_SIZE);

    memcpy(blob + ICO_HEADER_SIZE + ICO_DIR_ENTRY_SIZE, buf + e->payload_offset, e->payload_size);

    out->nominal = e->width > e->height ? e->width : e->height;
    out->width = e->width;
    out->height = e->height;
    out->hotspot_x = type == ICO_TYPE_CURSOR ? e->field_a : 0;
    out->hotspot_y = type == ICO_TYPE_CURSOR ? e->field_b : 0;
    out->blob = blob;
    out->blob_size = total;
    return ANICORE_OK;
}

static void ico_free_images(anicore_image *images, uint32_t count) {
    if (!images) {
        return;
    }
    for (uint32_t i = 0; i < count; ++i) {
        free((void *)images[i].blob);
    }
    free(images);
}

anicore_status anicore_ico_read_images(const uint8_t *buf, size_t len, anicore_image **out_images,
                                       uint32_t *out_count) {
    uint16_t type = 0;
    ico_entry *entries = NULL;
    uint32_t count = 0;

    anicore_status status = ico_open(buf, len, &type, &entries, &count);
    if (status != ANICORE_OK) {
        return status;
    }

    anicore_image *images = (anicore_image *)calloc(count, sizeof(anicore_image));
    if (!images) {
        free(entries);
        return ANICORE_ERR_OOM;
    }

    for (uint32_t i = 0; i < count; ++i) {
        status = ico_build_image(buf, type, &entries[i], &images[i]);
        if (status != ANICORE_OK) {
            ico_free_images(images, i);
            free(entries);
            return status;
        }
    }

    free(entries);
    *out_images = images;
    *out_count = count;
    return ANICORE_OK;
}

anicore_status anicore_parse_ico(const uint8_t *buf, size_t len, anicore_cursor *out) {
    anicore_image *images = NULL;
    uint32_t count = 0;

    anicore_status status = anicore_ico_read_images(buf, len, &images, &count);
    if (status != ANICORE_OK) {
        return status;
    }

    anicore_frame *frames = (anicore_frame *)calloc(1, sizeof(anicore_frame));
    if (!frames) {
        ico_free_images(images, count);
        return ANICORE_ERR_OOM;
    }
    frames[0].delay_ms = 0;
    frames[0].image_count = count;
    frames[0].images = images;

    out->width = images[0].width;
    out->height = images[0].height;
    out->hotspot_x = images[0].hotspot_x;
    out->hotspot_y = images[0].hotspot_y;
    out->frame_count = 1;
    out->frames = frames;
    return ANICORE_OK;
}
