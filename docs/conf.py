# This code is part of cqlib.
#
# Copyright (C) 2026 China Telecom Quantum Group.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

project = "cqlib-vqe"
author = "Cqlib VQE contributors"
copyright = "2026, Cqlib VQE contributors"

extensions = [
    "myst_parser",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

root_doc = "index"
language = "zh_CN"

exclude_patterns = [
    "build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "classic"
html_title = "cqlib-vqe 文档"
html_show_sourcelink = False

# Keep the site tree in the sidebar on every page, so navigation does not
# depend on getting back to the index first.
html_sidebars = {
    "**": [
        "globaltoc.html",
        "searchbox.html",
    ],
}
html_theme_options = {
    # One flat list of every page, shown unchanged on every page.
    "globaltoc_collapse": False,
    "globaltoc_maxdepth": "1",
}

myst_heading_anchors = 3
