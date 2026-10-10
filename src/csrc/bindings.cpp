/*
 * pybind11 bindings for the anicore C library.
 */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "anicore/anicore.h"

namespace py = pybind11;

PYBIND11_MODULE(_anicore, m) {
    m.doc() = "C core for ani2xcur: Windows cursor container parsing (ANI / ICO / CUR)";
    m.attr("__version__") = anicore_version();

    py::enum_<anicore_status>(m, "Status")
        .value("OK", ANICORE_OK)
        .value("ERR_FORMAT", ANICORE_ERR_FORMAT)
        .value("ERR_OOM", ANICORE_ERR_OOM)
        .value("ERR_UNSUPPORTED", ANICORE_ERR_UNSUPPORTED);

    m.def("version", &anicore_version, "Return the anicore core version string.");
    m.def("strerror", &anicore_strerror, py::arg("status"), "Describe a status code.");
}
