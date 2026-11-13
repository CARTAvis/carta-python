# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
#sys.path.insert(0, os.path.abspath('.'))
# We need this to build the docs from the local repository files rather than an installed copy
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------

project = 'carta-python'
copyright = '2020, Adrianna Pińska'
author = 'Adrianna Pińska'

# The full version, including alpha/beta/rc tags

with open("../../VERSION.txt") as f:
    version = f.read().strip()

release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx_tabs.tabs',
    'sphinx_design',
    'myst_parser',
]

# Pages can be written in reStructuredText or in MyST Markdown
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Generate one API reference page per module (see _templates/autosummary)
autosummary_generate = True

napoleon_google_docstring = False
napoleon_use_param = False
napoleon_use_ivar = True

# This mocks out the external dependencies
autodoc_mock_imports = ["selenium", "requests"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'pydata_sphinx_theme'

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/CARTAvis/carta-python",
            "icon": "fa-brands fa-github",
        },
    ],
    "navbar_align": "left",
    "show_toc_level": 2,
    # The home page has no sections, so it needs no page table of contents
    "secondary_sidebar_items": {
        "**": ["page-toc"],
        "index": [],
    },
    "pygments_dark_style": "nord",
}

# The version is shown on the home page and in the Read the Docs version menu
html_title = project

# Do not link to the reStructuredText source of each page
html_show_sourcelink = False

# Read the Docs sets this so that search engines point to one version of each page
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")

# Pages with no left sidebar content
html_sidebars = {
    "index": [],
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []
