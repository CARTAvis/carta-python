"""Static checks for the example scripts in docs/examples.

The examples need a running CARTA backend, so they are not run here. Instead,
these tests check that each example still matches the carta API: that its
imports from ``carta`` exist, that every attribute it uses on a carta object is
defined on some carta class, and that every keyword argument it passes is
accepted by a carta method of that name. This catches renamed or removed
methods and parameters, which would otherwise break the tutorials silently.

Objects are traced by name only: a variable is treated as a carta object if it
is assigned from an expression that starts with a carta import or another
carta object. Attributes of built-in types (for example ``dict.get`` on an
image header) are allowed.
"""

import ast
import importlib
import inspect
import pkgutil
import sys
from pathlib import Path
from unittest import mock

import pytest

import carta

# Selenium is an optional dependency (the "browser" extra) and is not installed
# for the unit tests; stub it so that carta.browser can be imported.
try:
    import selenium  # noqa: F401
except ImportError:
    for name in ("selenium", "selenium.webdriver", "selenium.common", "selenium.common.exceptions", "selenium.webdriver.chrome", "selenium.webdriver.chrome.options", "selenium.webdriver.common", "selenium.webdriver.common.by"):
        sys.modules.setdefault(name, mock.MagicMock())

EXAMPLES_DIR = Path(__file__).parents[1] / "docs" / "examples"
EXAMPLES = sorted(EXAMPLES_DIR.glob("*.py"))

BUILTIN_TYPES = (dict, list, tuple, str, bytes, int, float, set)


def carta_modules():
    for info in pkgutil.iter_modules(carta.__path__, "carta."):
        yield importlib.import_module(info.name)


def carta_api():
    """Map each public attribute name on carta classes to its signatures."""
    api = {}
    for module in carta_modules():
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if not cls.__module__.startswith("carta."):
                continue
            for name, value in inspect.getmembers(cls):
                if name.startswith("_"):
                    continue
                signatures = api.setdefault(name, [])
                if callable(value):
                    try:
                        signatures.append(inspect.signature(value))
                    except (TypeError, ValueError):
                        pass
        # Instance attributes set in __init__ (such as image.raster) are not
        # class members; collect them from the source.
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__ or "__init__" not in vars(cls):
                continue
            tree = ast.parse(inspect.getsource(cls))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self" and isinstance(node.ctx, ast.Store) and not node.attr.startswith("_"):
                    api.setdefault(node.attr, [])
    return api


API = carta_api()


def root_name(node):
    """The variable at the start of an expression like ``a.b(c).d[0]``."""
    while True:
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Subscript):
            node = node.value
        elif isinstance(node, ast.Name):
            return node.id
        else:
            return None


def target_names(target):
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from target_names(element)


def carta_names(tree):
    """Names bound to carta modules, classes or objects in a script."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("carta"):
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.asname or alias.name for alias in node.names if alias.name.startswith("carta"))
    # Propagate through assignments and loops until nothing changes
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                value, targets = node.value, node.targets
            elif isinstance(node, (ast.For, ast.comprehension)):
                value, targets = node.iter, [node.target]
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars is not None and root_name(item.context_expr) in names:
                        new = set(target_names(item.optional_vars)) - names
                        names |= new
                        changed |= bool(new)
                continue
            else:
                continue
            if root_name(value) in names:
                new = {name for target in targets for name in target_names(target)} - names
                names |= new
                changed |= bool(new)
    return names


def is_builtin_attribute(name):
    return any(hasattr(t, name) for t in BUILTIN_TYPES)


def check_example(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    problems = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("carta"):
            module = importlib.import_module(node.module)
            for alias in node.names:
                if not hasattr(module, alias.name):
                    problems.append(f"line {node.lineno}: {node.module} has no {alias.name}")

    names = carta_names(tree)
    imported = {
        alias.asname or alias.name: getattr(importlib.import_module(node.module), alias.name, None)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("carta")
        for alias in node.names
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or root_name(node) not in names:
            continue
        if isinstance(node.value, ast.Name) and node.value.id in imported:
            # An attribute of an imported class or enum, such as Colormap.VIRIDIS
            obj = imported[node.value.id]
            if obj is not None and not hasattr(obj, node.attr):
                problems.append(f"line {node.lineno}: {node.value.id} has no attribute {node.attr!r}")
        elif node.attr not in API and not is_builtin_attribute(node.attr):
            problems.append(f"line {node.lineno}: no carta class has an attribute named {node.attr!r}")

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and root_name(node.func) in names):
            continue
        name = node.func.attr
        signatures = API.get(name, [])
        if not signatures:
            continue
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            if not any(keyword.arg in sig.parameters or any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()) for sig in signatures):
                problems.append(f"line {node.lineno}: no carta method {name}() takes a keyword argument {keyword.arg!r}")

    return problems


@pytest.mark.parametrize("path", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_example_matches_carta_api(path):
    problems = check_example(path)
    assert not problems, f"{path.name} does not match the carta API:\n" + "\n".join(problems)


def test_examples_exist():
    assert EXAMPLES, f"no example scripts found in {EXAMPLES_DIR}"


def test_check_finds_problems(tmp_path):
    example = tmp_path / "broken.py"
    example.write_text(
        "from carta.session import Session\n"
        "from carta.constants import Colormap\n"
        "session = Session.interact('http://localhost', 1)\n"
        "image = session.open_image('a.fits', missing_argument=True)\n"
        "image.raster.set_colourmap(Colormap.VIRIDIS)\n"
        "image.raster.set_colormap(Colormap.NOT_A_COLORMAP)\n"
    )
    problems = check_example(example)
    assert any("missing_argument" in p for p in problems)
    assert any("set_colourmap" in p for p in problems)
    assert any("NOT_A_COLORMAP" in p for p in problems)
