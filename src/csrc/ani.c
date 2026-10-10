/*
 * ani.c - ANI (RIFF/ACON) animated cursor parsing.
 *
 * An ANI file is a RIFF container. The chunks we care about are:
 *   anih  - animation header (frame/step counts, logical size, jiffy rate)
 *   seq   - per-step index into the icon list (optional)
 *   rate  - per-step duration in jiffies (optional)
 *   LIST fram - the icon list, one complete ICO/CUR per "icon" sub-chunk
 *
 * Every step becomes one frame. When `seq` is absent the steps follow the icon
 * order; when `rate` is absent (or a rate entry is zero) the header jiffy rate
 * is used. Jiffies are 1/60 s and are converted to milliseconds.
 */
#include <stdlib.h>
#include <string.h>

#include "internal.h"

#define ANI_ANIH_SIZE 36
#define ANI_ANIH_C_FRAMES_OFF 4
#define ANI_ANIH_C_STEPS_OFF 8
#define ANI_ANIH_CX_OFF 12
#define ANI_ANIH_CY_OFF 16
#define ANI_ANIH_JIF_RATE_OFF 28

typedef struct {
    const uint8_t *data;
    size_t size;
} ani_icon;

static int ani_push_icon(ani_icon **icons, uint32_t *count, uint32_t *capacity,
                         const uint8_t *data, size_t size) {
    if (*count == *capacity) {
        uint32_t next = *capacity ? *capacity * 2 : 8;
        ani_icon *grown = (ani_icon *)realloc(*icons, (size_t)next * sizeof(ani_icon));
        if (!grown) {
            return 0;
        }
        *icons = grown;
        *capacity = next;
    }
    (*icons)[*count].data = data;
    (*icons)[*count].size = size;
    ++*count;
    return 1;
}

/* Read a LIST chunk, collecting the blobs of its "icon" sub-chunks. */
static anicore_status ani_read_list(anicore_reader *r, size_t chunk_end, ani_icon **icons,
                                    uint32_t *icon_count, uint32_t *icon_capacity) {
    const uint8_t *list_type = reader_ptr(r, 4);
    if (!list_type) {
        return ANICORE_ERR_FORMAT;
    }
    if (memcmp(list_type, "fram", 4) != 0) {
        return ANICORE_OK; /* not the frame list, ignore */
    }

    while (r->pos + 8 <= chunk_end) {
        const uint8_t *sub_id = reader_ptr(r, 4);
        uint32_t sub_size = reader_u32le(r);
        if (!sub_id || !r->ok || r->pos + sub_size > chunk_end) {
            return ANICORE_ERR_FORMAT;
        }
        if (memcmp(sub_id, "icon", 4) == 0) {
            if (!ani_push_icon(icons, icon_count, icon_capacity, r->data + r->pos, sub_size)) {
                return ANICORE_ERR_OOM;
            }
        }
        if (!reader_skip(r, sub_size + (sub_size & 1))) {
            return ANICORE_ERR_FORMAT;
        }
    }
    return ANICORE_OK;
}

anicore_status anicore_parse_ani(const uint8_t *buf, size_t len, anicore_cursor *out) {
    anicore_reader r;
    reader_init(&r, buf, len);

    const uint8_t *riff = reader_ptr(&r, 4);
    (void)reader_u32le(&r); /* RIFF size */
    const uint8_t *form = reader_ptr(&r, 4);
    if (!riff || !form || memcmp(riff, "RIFF", 4) != 0 || memcmp(form, "ACON", 4) != 0) {
        return ANICORE_ERR_FORMAT;
    }

    uint32_t c_steps = 0;
    uint32_t cx = 0;
    uint32_t cy = 0;
    uint32_t jif_rate = 0;
    int have_anih = 0;
    uint32_t *seq = NULL;
    uint32_t seq_count = 0;
    uint32_t *rate = NULL;
    uint32_t rate_count = 0;
    ani_icon *icons = NULL;
    uint32_t icon_count = 0;
    uint32_t icon_capacity = 0;
    anicore_status status = ANICORE_OK;

    while (reader_remaining(&r) >= 8) {
        const uint8_t *cid = reader_ptr(&r, 4);
        uint32_t csize = reader_u32le(&r);
        if (!cid || !r.ok) {
            status = ANICORE_ERR_FORMAT;
            break;
        }
        size_t chunk_end = r.pos + (size_t)csize;
        if (chunk_end > r.size) {
            status = ANICORE_ERR_FORMAT;
            break;
        }

        if (memcmp(cid, "anih", 4) == 0) {
            if (csize < ANI_ANIH_SIZE) {
                status = ANICORE_ERR_FORMAT;
                break;
            }
            const uint8_t *p = r.data + r.pos;
            c_steps = load_u32le(p + ANI_ANIH_C_STEPS_OFF);
            cx = load_u32le(p + ANI_ANIH_CX_OFF);
            cy = load_u32le(p + ANI_ANIH_CY_OFF);
            jif_rate = load_u32le(p + ANI_ANIH_JIF_RATE_OFF);
            have_anih = 1;
        } else if (memcmp(cid, "seq ", 4) == 0) {
            free(seq);
            seq = NULL;
            seq_count = 0;
            if (csize % 4 != 0) {
                status = ANICORE_ERR_FORMAT;
                break;
            }
            seq_count = csize / 4;
            seq = (uint32_t *)malloc((size_t)seq_count * sizeof(uint32_t));
            if (!seq && seq_count) {
                status = ANICORE_ERR_OOM;
                break;
            }
            for (uint32_t i = 0; i < seq_count; ++i) {
                seq[i] = load_u32le(r.data + r.pos + (size_t)i * 4);
            }
        } else if (memcmp(cid, "rate", 4) == 0) {
            free(rate);
            rate = NULL;
            rate_count = 0;
            if (csize % 4 != 0) {
                status = ANICORE_ERR_FORMAT;
                break;
            }
            rate_count = csize / 4;
            rate = (uint32_t *)malloc((size_t)rate_count * sizeof(uint32_t));
            if (!rate && rate_count) {
                status = ANICORE_ERR_OOM;
                break;
            }
            for (uint32_t i = 0; i < rate_count; ++i) {
                rate[i] = load_u32le(r.data + r.pos + (size_t)i * 4);
            }
        } else if (memcmp(cid, "LIST", 4) == 0) {
            status = ani_read_list(&r, chunk_end, &icons, &icon_count, &icon_capacity);
            if (status != ANICORE_OK) {
                break;
            }
        }

        if (!reader_seek(&r, chunk_end + (csize & 1))) {
            status = ANICORE_ERR_FORMAT;
            break;
        }
    }

    if (status == ANICORE_OK && !have_anih) {
        status = ANICORE_ERR_FORMAT;
    }

    if (status == ANICORE_OK) {
        uint32_t steps = seq_count ? seq_count : (c_steps ? c_steps : icon_count);
        if (steps == 0 || icon_count == 0) {
            status = ANICORE_ERR_FORMAT;
        } else {
            out->frames = (anicore_frame *)calloc(steps, sizeof(anicore_frame));
            if (!out->frames) {
                status = ANICORE_ERR_OOM;
            } else {
                out->frame_count = steps;
                for (uint32_t i = 0; i < steps && status == ANICORE_OK; ++i) {
                    uint32_t index = seq ? seq[i] : i;
                    if (index >= icon_count) {
                        status = ANICORE_ERR_FORMAT;
                        break;
                    }
                    anicore_image *images = NULL;
                    uint32_t image_count = 0;
                    status = anicore_ico_read_images(icons[index].data, icons[index].size, &images,
                                                     &image_count);
                    if (status != ANICORE_OK) {
                        break;
                    }
                    uint32_t raw = rate ? rate[i] : 0;
                    if (raw == 0) {
                        raw = jif_rate;
                    }
                    out->frames[i].delay_ms = (uint32_t)(((uint64_t)raw * 1000 + 30) / 60);
                    out->frames[i].image_count = image_count;
                    out->frames[i].images = images;
                }
            }

            if (status == ANICORE_OK) {
                const anicore_image *first = &out->frames[0].images[0];
                out->width = cx ? cx : first->width;
                out->height = cy ? cy : first->height;
                out->hotspot_x = first->hotspot_x;
                out->hotspot_y = first->hotspot_y;
            }
        }
    }

    free(seq);
    free(rate);
    free(icons);
    if (status != ANICORE_OK) {
        anicore_free(out);
    }
    return status;
}
