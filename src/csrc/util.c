#include <stdlib.h>
#include <string.h>

#include "internal.h"

uint8_t *anicore_memdup(const uint8_t *src, size_t n) {
    uint8_t *p = (uint8_t *)malloc(n ? n : 1);
    if (!p) {
        return NULL;
    }
    if (n) {
        memcpy(p, src, n);
    }
    return p;
}
