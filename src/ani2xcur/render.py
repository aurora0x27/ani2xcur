"""Scale parsed cursors into the nominal sizes needed for an XCursor theme.

Rasters are resized with Lanczos in **premultiplied** alpha space (transparent
pixels would otherwise bleed their colour into the edges) and the output is kept
premultiplied, which is exactly what the XCursor format expects.
"""

from __future__ import annotations

from collections.abc import Iterable

from PIL import Image, ImageChops

from .model import Cursor, CursorFrame, CursorImage

#: Nominal sizes produced by default.
DEFAULT_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 96, 128)


def premultiply(image: Image.Image) -> Image.Image:
    """Return ``image`` converted to RGBA with premultiplied alpha."""
    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    return Image.merge(
        "RGBA",
        (
            ImageChops.multiply(red, alpha),
            ImageChops.multiply(green, alpha),
            ImageChops.multiply(blue, alpha),
            alpha,
        ),
    )


def _pick_source(
    images: dict[int, CursorImage], target: int, allow_upscale: bool
) -> CursorImage | None:
    """Choose the source raster that scales best to ``target``.

    Preference is the smallest source that is at least ``target`` (a downscale);
    otherwise the largest source is upscaled, unless upscaling is disallowed.
    """
    if not images:
        return None
    ordered = [images[key] for key in sorted(images)]
    for source in ordered:
        if source.nominal >= target:
            return source
    return ordered[-1] if allow_upscale else None


def _scale_hotspot(
    hotspot: tuple[int, int], source_width: int, source_height: int, target: int
) -> tuple[int, int]:
    """Scale a hotspot to the resized raster, clamped to its bounds."""
    x, y = hotspot
    scaled_x = int(x * target / source_width + 0.5) if source_width else 0
    scaled_y = int(y * target / source_height + 0.5) if source_height else 0
    return max(0, min(scaled_x, target)), max(0, min(scaled_y, target))


def resize_cursor(
    cursor: Cursor,
    sizes: Iterable[int] = DEFAULT_SIZES,
    *,
    allow_upscale: bool = True,
) -> Cursor:
    """Resize every frame of ``cursor`` to each of ``sizes``.

    Returns a new :class:`Cursor` whose frames carry premultiplied RGBA rasters
    keyed by the requested nominal sizes. Sizes with no usable source (larger
    than every source when ``allow_upscale`` is false) are skipped.
    """
    targets = sorted({int(size) for size in sizes})
    if not targets:
        raise ValueError("no target sizes given")

    frames: list[CursorFrame] = []
    for frame in cursor.frames:
        images: dict[int, CursorImage] = {}
        for target in targets:
            source = _pick_source(frame.images, target, allow_upscale)
            if source is None:
                continue
            scaled = premultiply(source.image).resize((target, target), Image.LANCZOS)
            images[target] = CursorImage(
                nominal=target,
                width=target,
                height=target,
                hotspot=_scale_hotspot(source.hotspot, source.width, source.height, target),
                image=scaled,
            )
        frames.append(CursorFrame(delay_ms=frame.delay_ms, images=images))

    return Cursor(name=cursor.name, frames=frames, source=cursor.source)
