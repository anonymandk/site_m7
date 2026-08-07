"""Top-level package shim to make imports like
`project_dropshiping.python.*` resolve to the repository's `python/` folder.

This file adds the repository root to the package search path so that the
existing `python` package (at repo root) is visible as a subpackage of
`project_dropshiping` during test collection and runtime.
"""
import os

# Prepend the repository root (parent of this folder) to the package path.
# This allows `import project_dropshiping.python` to find the `python/`
# directory at the repository root.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in __path__:
    __path__.insert(0, repo_root)
