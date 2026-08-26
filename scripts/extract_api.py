#!/usr/bin/env python3

"""Extract the carta-frontend actions and parameters used by this wrapper.

The extraction has two stages:

1. A static scan of the ``carta`` package with :obj:`ast`, which finds every
   ``call_action`` and ``get_value`` call site, the path passed to it, and any
   :obj:`carta.util.Macro` arguments. Paths built from f-strings become globs
   (``regionMap[*]``), and paths passed in a local variable are resolved with a
   small constant propagation pass.

2. A runtime replay of each path through real wrapper objects, with
   :obj:`carta.session.Session.call_action` replaced by a recorder. This uses
   the wrapper's own code to prepend base paths, to resolve paths inherited
   from mixins, and to insert colorbar component prefixes, so that none of that
   logic has to be reimplemented here. No frontend or backend is needed.

Call sites which the static stage cannot resolve are reported separately, and
fail ``--check``. A call site with a path which is genuinely dynamic, because it
is provided by the user, must be annotated with ``# carta-api:dynamic``.

The extracted APIs are the two repositories' shared contract. CI generates
``carta-python-api.json`` from this repository and passes it to carta-frontend's
checker to verify that every frontend API used here still exists.
Each entry also records the frontend runtime types which can receive the API, so
polymorphic objects such as annotations can be checked against the correct subtype.

Usage: extract_api.py [--check] [--write-manifest] [--output FILE]
"""

import argparse
import ast
import collections
import dataclasses
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from carta.color_blending import ColorBlending  # noqa: E402
from carta.constants import RegionType  # noqa: E402
from carta.image import Image  # noqa: E402
from carta.region import Region, RegionSet  # noqa: E402
from carta.session import Session  # noqa: E402
from carta.util import Macro  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

PACKAGE = ROOT / "carta"

# The machine-readable contract generated for carta-frontend's CI.
MANIFEST = ROOT / "carta-python-api.json"

WRAPPERS = ("call_action", "get_value")

# Call sites inside the wrapper's own plumbing, which forward a path from a
# caller instead of naming a frontend API.
PLUMBING = {
    ("util.py", "BasePathMixin", "call_action"),
    ("util.py", "BasePathMixin", "get_value"),
    ("session.py", "Session", "get_value"),
    ("wcs_overlay.py", "ColorbarComponent", "call_action"),
    ("wcs_overlay.py", "ColorbarComponent", "get_value"),
}

# Receiver expressions, mapped to the name of the class of the object they
# evaluate to. A call site is replayed on every registered object of that class,
# so a call site in a mixin is replayed on every class which uses the mixin.
# `self` means the class which contains the call site.
RECEIVERS = {
    "self": "self",
    "session": "Session",
    "self.session": "Session",
    "self.image": "Image",
    "self.color_blending": "ColorBlending",
    "self.colorbar": "Colorbar",
    "region_set": "RegionSet",
    "self.region_set": "RegionSet",
    "self.active_frame().regions": "RegionSet",
}

ID_INDEX = re.compile(r"\[\d+\]")
LEGACY_ANNOTATION = re.compile(r"#\s*carta-api:legacy(?:\s+until=(\S+))?\s*$")
DYNAMIC_ANNOTATION = re.compile(r"#\s*carta-api:dynamic(?:\s+path=(\S+))?\s*$")


@dataclasses.dataclass
class Site:
    """A single ``call_action`` or ``get_value`` call site in the wrapper."""

    module: str
    line: int
    clazz: str
    method: str
    wrapper: str
    receiver: str
    path: str
    exact: bool
    return_path: str
    args: tuple = ()
    dynamic: bool = False
    legacy: bool = False
    legacy_until: str = ""

    @property
    def location(self):
        """The source location of this call site."""
        return f"carta/{self.module}:{self.line}{' (dynamic)' if self.dynamic else ''}"

    @property
    def qualname(self):
        """The qualified name of the wrapper method which contains this call site."""
        return f"{self.clazz}.{self.method}" if self.clazz else self.method


@dataclasses.dataclass
class Api:
    """A frontend action, parameter or store object used by the wrapper."""

    kind: str
    path: str
    exact: bool = True
    return_path: str = ""
    sites: list = dataclasses.field(default_factory=list)
    runtime_types: set = dataclasses.field(default_factory=set)
    required: bool = False
    legacy_until: str = ""

    def add(self, site, runtime_types=()):
        """Record a call site which uses this frontend API."""
        if site not in self.sites:
            self.sites.append(site)
        self.exact &= site.exact
        self.runtime_types.update(runtime_types)
        if site.legacy:
            if not self.required and site.legacy_until:
                self.legacy_until = site.legacy_until
        else:
            self.required = True
            self.legacy_until = ""


class Scanner(ast.NodeVisitor):
    """Collects the ``call_action`` and ``get_value`` call sites in one module."""

    def __init__(self, module, source):
        self.module = module
        self.source_lines = source.splitlines()
        self.sites = []
        self.unresolved = []
        self.classes = []
        self.functions = []
        self.assignments = [{}]

    @property
    def clazz(self):
        """The class currently being scanned."""
        return self.classes[-1] if self.classes else ""

    @property
    def method(self):
        """The function currently being scanned."""
        return self.functions[-1] if self.functions else ""

    def legacy_annotation(self, node):
        """Return legacy compatibility metadata attached to a call site."""
        line_numbers = [node.lineno]
        if node.lineno > 1:
            line_numbers.append(node.lineno - 1)
        for line_number in line_numbers:
            match = LEGACY_ANNOTATION.search(self.source_lines[line_number - 1])
            if match:
                return True, match.group(1) or ""
        return False, ""

    def dynamic_annotation(self, node):
        """Return the dynamic path attached to a call site, if any."""
        line_numbers = [node.lineno]
        if node.lineno > 1:
            line_numbers.append(node.lineno - 1)
        for line_number in line_numbers:
            match = DYNAMIC_ANNOTATION.search(self.source_lines[line_number - 1])
            if match:
                return match.group(1) or "*"
        return None

    def visit_ClassDef(self, node):
        """Scan a class definition."""
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node):
        """Scan a function definition."""
        self.functions.append(node.name)
        self.assignments.append(self.local_assignments(node))
        self.generic_visit(node)
        self.assignments.pop()
        self.functions.pop()

    @staticmethod
    def local_assignments(node):
        """Map each local variable in a function to the values bound to it.

        Both assignments and ``for`` loops over literal iterables are followed,
        which is enough to resolve the paths and macro attribute names which the
        wrapper builds up in local variables.
        """
        assignments = collections.defaultdict(list)

        for child in ast.walk(node):
            if isinstance(child, ast.Assign) and len(child.targets) == 1 and isinstance(child.targets[0], ast.Name):
                values = [child.value.body, child.value.orelse] if isinstance(child.value, ast.IfExp) else [child.value]
                assignments[child.targets[0].id].extend(values)
            elif isinstance(child, ast.Call) and getattr(child.func, "attr", "") in ("append", "extend") and isinstance(child.func.value, ast.Name):
                assignments[child.func.value.id].extend(child.args)
            elif isinstance(child, ast.For):
                targets = child.target.elts if isinstance(child.target, ast.Tuple) else [child.target]
                for item in getattr(child.iter, "elts", []):
                    values = item.elts if isinstance(item, ast.Tuple) else [item]
                    for target, value in zip(targets, values) if len(targets) == len(values) else ():
                        if isinstance(target, ast.Name):
                            assignments[target.id].append(value)

        return assignments

    def visit_Call(self, node):
        """Scan a call, and record it if it is a wrapper call."""
        self.generic_visit(node)

        if not isinstance(node.func, ast.Attribute) or node.func.attr not in WRAPPERS:
            return
        if (self.module, self.clazz, self.method) in PLUMBING:
            return

        receiver = ast.unparse(node.func.value)
        return_path = ""
        for keyword in node.keywords:
            if keyword.arg == "return_path" and isinstance(keyword.value, ast.Constant):
                return_path = keyword.value.value

        args = tuple(self.macro_args(node.args[1:]))
        paths, exact = self.paths(node.args[0] if node.args else None)

        dynamic = self.dynamic_annotation(node)
        if dynamic is not None:
            paths, exact = [dynamic], False

        if not paths or receiver not in RECEIVERS:
            self.unresolved.append((f"carta/{self.module}:{node.lineno}", self.clazz, self.method, ast.unparse(node)))
            return

        legacy, legacy_until = self.legacy_annotation(node)
        for path in paths:
            self.sites.append(
                Site(
                    self.module,
                    node.lineno,
                    self.clazz,
                    self.method,
                    node.func.attr,
                    receiver,
                    path,
                    exact,
                    return_path,
                    args,
                    dynamic is not None,
                    legacy,
                    legacy_until,
                )
            )

    def values(self, node):
        """The expressions an argument may evaluate to.

        A local variable, or a variable unpacked with ``*``, is expanded to every
        value bound to it in the enclosing function; any other expression is
        returned unchanged.
        """
        node = node.value if isinstance(node, ast.Starred) else node
        return self.assignments[-1][node.id] if isinstance(node, ast.Name) else [node]

    def strings(self, node):
        """The string constants an argument may evaluate to."""
        strings = []
        for value in self.values(node):
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                strings.append(value.value)
            elif isinstance(value, (ast.List, ast.Tuple)):
                strings.extend(
                    element.value
                    for element in value.elts
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                )
        return strings

    def macro_args(self, nodes):
        """Descriptors for the arguments of a call site which are frontend macros.

        A macro is either an attribute such as ``self._frame``, a call to the
        ``macro`` method of a wrapper object, or a :obj:`carta.util.Macro`
        constructed directly.
        """
        for node in nodes:
            for value in self.values(node):
                if isinstance(value, ast.Attribute) and value.attr in ("_frame", "_region"):
                    yield ("attr", ast.unparse(value))
                    continue
                if not isinstance(value, ast.Call) or len(value.args) != 2:
                    continue
                name = getattr(value.func, "attr", getattr(value.func, "id", ""))
                if name not in ("macro", "Macro"):
                    continue
                owner = "" if name == "Macro" else ast.unparse(value.func.value)
                for target in self.strings(value.args[0]):
                    for variable in self.strings(value.args[1]):
                        yield ("macro", owner, target, variable)

    def paths(self, node):
        """The possible paths for the first argument of a call site.

        Returns the paths and whether they are exact. An inexact path is a glob
        in which each interpolated value has been replaced by ``*``.
        """
        if isinstance(node, ast.JoinedStr):
            return ["".join(v.value if isinstance(v, ast.Constant) else "*" for v in node.values)], False
        return self.strings(node) if node is not None else [], True


class Registry:
    """Real wrapper objects, used to resolve the base path of each call site."""

    def __init__(self):
        self.session = Session(0, None)
        self.objects = []
        self.by_class = collections.defaultdict(list)
        self.seen = set()

        image = Image(self.session, 0)
        for obj in (self.session, image, ColorBlending(self.session, 0)):
            self.collect(obj)
        for region_type in RegionType:
            self.collect(Region.region_class(region_type)(image.regions, 0))

    def collect(self, obj):
        """Recursively register wrapper objects reachable from an object."""
        if id(obj) in self.seen or type(obj).__module__.split(".")[0] != "carta":
            return
        self.seen.add(id(obj))

        if any(hasattr(obj, wrapper) for wrapper in WRAPPERS):
            self.objects.append(obj)
            for clazz in type(obj).__mro__:
                self.by_class[clazz.__name__].append(obj)

        for value in list(vars(obj).values()):
            for item in value.values() if isinstance(value, dict) else [value]:
                self.collect(item)

    def instances(self, site):
        """The registered objects on which a call site should be replayed."""
        clazz = site.clazz if RECEIVERS[site.receiver] == "self" else RECEIVERS[site.receiver]
        return [o for o in self.by_class[clazz] if hasattr(o, site.wrapper)]


def resolve_object(path, instance):
    """Resolve a dotted attribute path rooted at ``self`` to a wrapper object."""
    obj = instance
    for attr in path.split(".")[1:]:
        obj = getattr(obj, attr, None)
    return obj


def resolve_macro(descriptor, instance):
    """Resolve a macro argument descriptor to a :obj:`carta.util.Macro`."""
    if descriptor[0] == "attr":
        owner, _, attr = descriptor[1].rpartition(".")
        value = getattr(resolve_object(owner, instance), attr, None)
        return value if isinstance(value, Macro) else None

    _, owner, target, variable = descriptor
    if not owner:
        return Macro(target, variable)
    obj = resolve_object(owner, instance)
    return obj.macro(target, variable) if obj is not None else None


def macro_path(macro):
    """The generic path of a macro."""
    path = f"{macro.target}.{macro.variable}" if macro.target else macro.variable
    return ID_INDEX.sub("[*]", path)


def request_path(path, args):
    """The kind and generic path of a recorded frontend request."""
    if path == "fetchParameter" and args and isinstance(args[0], Macro):
        return "parameter", macro_path(args[0])
    return "action", ID_INDEX.sub("[*]", path)


def frontend_runtime_type(instance):
    """Return the frontend runtime type declared by a wrapper object."""
    runtime_type = getattr(instance, "FRONTEND_RUNTIME_TYPE", None)
    if runtime_type is None:
        raise ValueError(
            f"{type(instance).__name__} does not declare FRONTEND_RUNTIME_TYPE"
        )
    return runtime_type


def region_runtime_types(instance):
    """Return the runtime types which may receive a region request.

    A concrete region object declares one type. ``RegionSet`` can address an
    arbitrary region ID, so derive the possible types from the registered
    region classes instead of maintaining a second mapping here.
    """
    instance_type = type(instance)
    runtime_type = instance_type.__dict__.get("FRONTEND_RUNTIME_TYPE")
    if runtime_type is not None and instance_type is not Region:
        return [runtime_type]
    if isinstance(instance, (Region, RegionSet)):
        region_classes = set(Region.CUSTOM_CLASS.values())
        missing = [
            clazz.__name__
            for clazz in region_classes
            if all(region_type.name.startswith("ANN") for region_type in getattr(clazz, "REGION_TYPES", ()))
            and "FRONTEND_RUNTIME_TYPE" not in clazz.__dict__
        ]
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Annotation classes do not declare FRONTEND_RUNTIME_TYPE: {names}")
        return sorted({frontend_runtime_type(Region), *(frontend_runtime_type(clazz) for clazz in region_classes if "FRONTEND_RUNTIME_TYPE" in clazz.__dict__)})
    raise ValueError(
        f"{type(instance).__name__} does not declare FRONTEND_RUNTIME_TYPE"
    )


def frontend_runtime_types(path, instance):
    """Return the frontend class types which can receive a recorded path."""
    region_prefix = "frameMap[*].regionSet.regionMap[*]"
    if path == region_prefix or path.startswith(f"{region_prefix}."):
        return region_runtime_types(instance)

    if path == "frameMap[*]" or path.startswith("frameMap[*].") or path == "activeFrame" or path.startswith("activeFrame."):
        return ["FrameStore"]

    if path == "overlaySettings":
        return ["OverlaySettings"]
    if path.startswith("overlaySettings."):
        return [frontend_runtime_type(instance)]

    root_types = {
        "backendService": "BackendService",
        "fileBrowserStore": "FileBrowserStore",
        "preferenceStore": "PreferenceStore",
        "widgetsStore": "WidgetsStore",
    }
    root = path.split(".", 1)[0]
    return [root_types[root]] if root in root_types else ["AppStore"]


def replay(registry, sites):
    """Resolve the full frontend path of each call site by replaying it.

    Each path is passed to the real wrapper method of a real wrapper object,
    with :obj:`carta.session.Session.call_action` replaced by a recorder, so
    that base paths, mixins and prefix rewriting are resolved by the wrapper
    itself.
    """
    recorded = []
    original = Session.call_action
    Session.call_action = lambda self, path, *args, **kwargs: recorded.append((path, args, kwargs))

    apis = {}

    def add(kind, path, site, return_path="", runtime_types=()):
        apis.setdefault((kind, path), Api(kind, path, return_path=return_path)).add(site, runtime_types)

    try:
        for site in sites:
            for instance in registry.instances(site):
                recorded.clear()
                getattr(instance, site.wrapper)(site.path, return_path=site.return_path or None)
                for path, args, kwargs in recorded:
                    kind, full_path = request_path(path, args)
                    add(kind, full_path, site, site.return_path, frontend_runtime_types(full_path, instance))

            # Macro arguments are resolved on the object which contains the call
            # site, which is not necessarily the object being called.
            for owner in registry.by_class[site.clazz]:
                for node in site.args:
                    macro = resolve_macro(node, owner)
                    if macro is not None:
                        full_path = macro_path(macro)
                        add("reference", full_path, site, runtime_types=frontend_runtime_types(full_path, owner))
    finally:
        Session.call_action = original

    return apis


def scan():
    """Scan the package and return its call sites and unresolved call sites."""
    sites, unresolved = [], []

    for path in sorted(PACKAGE.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        scanner = Scanner(path.relative_to(PACKAGE).as_posix(), source)
        scanner.visit(ast.parse(source, filename=str(path)))
        sites.extend(scanner.sites)
        unresolved.extend(scanner.unresolved)

    return sites, unresolved


def manifest(apis):
    """The contract manifest of the frontend APIs which the wrapper uses.

    The manifest deliberately omits the source locations of the call sites, so
    that it changes only when the frontend API surface which the wrapper uses
    changes, and not whenever an unrelated edit shifts a line.
    """
    entries = []
    for api in apis:
        entry = {
                "kind": api.kind,
                "path": api.path,
                "exact": api.exact,
                "return_path": api.return_path,
                "runtime_types": sorted(api.runtime_types),
                "wrappers": sorted({s.qualname for s in api.sites}),
        }
        if not api.required:
            entry["compatibility"] = "legacy"
            if api.legacy_until:
                entry["until"] = api.legacy_until
        entries.append(entry)
    return {"apis": entries}


def dump_manifest(data):
    """The canonical serialisation of the manifest."""
    return json.dumps(data, indent=2) + "\n"


def print_report(apis, unresolved, sites, objects):
    """Print every frontend API, and any unresolved call sites, as text."""
    for kind in ("action", "parameter", "reference"):
        selected = [a for a in apis if a.kind == kind]
        print(f"\n{kind.upper()}S ({len(selected)})\n")
        for api in selected:
            suffix = f" -> {api.return_path}" if api.return_path else ""
            compatibility = "  [legacy" + (f" until={api.legacy_until}" if api.legacy_until else "") + "]" if not api.required else ""
            print(f"  {api.path}{suffix}{'' if api.exact else '  [glob]'}{compatibility}")
    print(f"\nUNRESOLVED CALL SITES ({len(unresolved)})\n")
    for location, clazz, method, source in unresolved:
        print(f"  {location} {clazz}.{method}\n      {source}")

    print(f"\n{len(sites)} resolved call sites, {len(apis)} distinct frontend APIs, {objects} wrapper objects")


def main():
    """Extract the frontend APIs and print a report."""
    parser = argparse.ArgumentParser(description="Extract the carta-frontend APIs used by this wrapper.")
    parser.add_argument("--check", action="store_true", help="exit with an error if any call site is unresolved")
    parser.add_argument("--write-manifest", action="store_true", help=f"write the contract manifest to {MANIFEST.name}")
    parser.add_argument("--output", metavar="FILE", help="write the manifest to FILE instead of the default path")
    args = parser.parse_args()

    if args.output and not args.write_manifest:
        parser.error("--output requires --write-manifest")

    sites, unresolved = scan()
    registry = Registry()
    apis = replay(registry, sites)
    ordered = sorted(apis.values(), key=lambda a: (a.kind, a.path))
    data = manifest(ordered)

    failed = bool(unresolved) and args.check

    if args.write_manifest:
        output = pathlib.Path(args.output) if args.output else MANIFEST
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(dump_manifest(data))
        print(f"Wrote {len(data['apis'])} frontend APIs to {output}.")

    if not args.write_manifest:
        print_report(ordered, unresolved, sites, len(registry.objects))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
