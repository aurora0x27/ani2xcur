/*
 * pybind11 bindings for the anicore C library.
 *
 * The C structs borrow raw pointers, so every parse copies the frame blobs into
 * Python `bytes` before the C side is released.
 */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "anicore/anicore.h"

namespace py = pybind11;

namespace {

struct Image {
    std::uint32_t nominal;
    std::uint32_t width;
    std::uint32_t height;
    std::uint32_t hotspot_x;
    std::uint32_t hotspot_y;
    py::bytes blob;
};

struct Frame {
    std::uint32_t delay_ms;
    std::vector<Image> images;
};

struct Cursor {
    std::uint32_t width;
    std::uint32_t height;
    std::uint32_t hotspot_x;
    std::uint32_t hotspot_y;
    std::vector<Frame> frames;
};

Cursor parse(const py::bytes &data) {
    char *buffer = nullptr;
    Py_ssize_t length = 0;
    if (PyBytes_AsStringAndSize(data.ptr(), &buffer, &length) != 0) {
        throw py::error_already_set();
    }

    anicore_cursor raw;
    anicore_status status =
        anicore_parse(reinterpret_cast<const std::uint8_t *>(buffer),
                      static_cast<std::size_t>(length), &raw);
    if (status != ANICORE_OK) {
        throw py::value_error(anicore_strerror(status));
    }

    Cursor cursor;
    cursor.width = raw.width;
    cursor.height = raw.height;
    cursor.hotspot_x = raw.hotspot_x;
    cursor.hotspot_y = raw.hotspot_y;
    cursor.frames.reserve(raw.frame_count);
    for (std::uint32_t f = 0; f < raw.frame_count; ++f) {
        const anicore_frame &raw_frame = raw.frames[f];
        Frame frame;
        frame.delay_ms = raw_frame.delay_ms;
        frame.images.reserve(raw_frame.image_count);
        for (std::uint32_t i = 0; i < raw_frame.image_count; ++i) {
            const anicore_image &raw_image = raw_frame.images[i];
            Image image;
            image.nominal = raw_image.nominal;
            image.width = raw_image.width;
            image.height = raw_image.height;
            image.hotspot_x = raw_image.hotspot_x;
            image.hotspot_y = raw_image.hotspot_y;
            image.blob = py::bytes(reinterpret_cast<const char *>(raw_image.blob),
                                   raw_image.blob_size);
            frame.images.push_back(std::move(image));
        }
        cursor.frames.push_back(std::move(frame));
    }
    anicore_free(&raw);
    return cursor;
}

}  // namespace

PYBIND11_MODULE(_anicore, m) {
    m.doc() = "C core for ani2xcur: Windows cursor container parsing (ANI / ICO / CUR)";
    m.attr("__version__") = anicore_version();

    py::enum_<anicore_status>(m, "Status")
        .value("OK", ANICORE_OK)
        .value("ERR_FORMAT", ANICORE_ERR_FORMAT)
        .value("ERR_OOM", ANICORE_ERR_OOM)
        .value("ERR_UNSUPPORTED", ANICORE_ERR_UNSUPPORTED);

    py::class_<Image>(m, "Image", "A single raster of a cursor (single-image ICO/CUR).")
        .def_property_readonly("nominal", [](const Image &self) { return self.nominal; })
        .def_property_readonly("width", [](const Image &self) { return self.width; })
        .def_property_readonly("height", [](const Image &self) { return self.height; })
        .def_property_readonly("hotspot_x", [](const Image &self) { return self.hotspot_x; })
        .def_property_readonly("hotspot_y", [](const Image &self) { return self.hotspot_y; })
        .def_property_readonly("blob", [](const Image &self) { return self.blob; })
        .def("__repr__", [](const Image &self) {
            return "<anicore.Image " + std::to_string(self.width) + "x" +
                   std::to_string(self.height) + " hotspot=(" + std::to_string(self.hotspot_x) +
                   "," + std::to_string(self.hotspot_y) + ")>";
        });

    py::class_<Frame>(m, "Frame", "One animation step: its delay and its rasters.")
        .def_property_readonly("delay_ms", [](const Frame &self) { return self.delay_ms; })
        .def_property_readonly("images", [](const Frame &self) { return self.images; })
        .def("__repr__", [](const Frame &self) {
            return "<anicore.Frame delay_ms=" + std::to_string(self.delay_ms) + " images=" +
                   std::to_string(self.images.size()) + ">";
        });

    py::class_<Cursor>(m, "Cursor", "A parsed cursor: a list of frames.")
        .def_property_readonly("width", [](const Cursor &self) { return self.width; })
        .def_property_readonly("height", [](const Cursor &self) { return self.height; })
        .def_property_readonly("hotspot_x", [](const Cursor &self) { return self.hotspot_x; })
        .def_property_readonly("hotspot_y", [](const Cursor &self) { return self.hotspot_y; })
        .def_property_readonly("frames", [](const Cursor &self) { return self.frames; })
        .def("__repr__", [](const Cursor &self) {
            return "<anicore.Cursor " + std::to_string(self.width) + "x" +
                   std::to_string(self.height) + " frames=" + std::to_string(self.frames.size()) +
                   ">";
        });

    m.def("parse", &parse, py::arg("data"),
          "Parse an ANI / ICO / CUR buffer into a Cursor. Raises ValueError on bad input.");
    m.def("version", &anicore_version, "Return the anicore core version string.");
    m.def("strerror", &anicore_strerror, py::arg("status"), "Describe a status code.");
}
