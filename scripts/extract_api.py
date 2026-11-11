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
fail ``--check``. Resolution is all-or-nothing: if any value a path, projection
or macro argument may take is not a constant, the whole call site is
unresolved. A call site with a path which is genuinely dynamic, because it
is provided by the user, must be annotated with ``# carta-api:dynamic``.
Wrappers used indirectly, through an alias such as ``f = self.get_value`` or
by name as a string such as ``getattr(obj, "get_value")``, are reported in the
same way, because their call sites cannot be found.

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

from carta.color_blending import ColorBlending, Layer  # noqa: E402
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
FRONTEND_ROOT_TYPES = {
    "backendService": "BackendService",
    "fileBrowserStore": "FileBrowserStore",
    "preferenceStore": "PreferenceStore",
    "widgetsStore": "WidgetsStore",
}

# Marks a value which the static scan cannot reduce to a constant, such as a
# function parameter or a loop over a computed iterable.
UNKNOWN = object()


@dataclasses.dataclass(frozen=True)
class Appended:
    """A value added to a local list with ``append`` or ``extend``."""

    node: ast.AST


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
    return_path: str | list | dict
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
    return_path: str | list | dict = ""
    sites: list = dataclasses.field(default_factory=list)
    runtime_types: set = dataclasses.field(default_factory=set)
    required: bool = False
    legacy_until: str = ""
    return_paths: list = dataclasses.field(default_factory=list)

    def __post_init__(self):
        """Keep the initial return path in the complete projection list."""
        self.return_paths.append(self.return_path)

    def add(self, site, runtime_types=()):
        """Record a call site which uses this frontend API."""
        if site not in self.sites:
            self.sites.append(site)
        if self.kind != "reference" and site.return_path not in self.return_paths:
            self.return_paths.append(site.return_path)
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
        self.called = set()
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

    def annotation(self, node, pattern):
        """Return the ``carta-api`` annotation attached to a call site, if any.

        The annotation may be a trailing comment on the first line of the call,
        or a comment on its own on the line immediately before it. A trailing
        comment on the previous line belongs to that line's code, so it does not
        apply to this call.
        """
        match = pattern.search(self.source_lines[node.lineno - 1])
        if match is None and node.lineno > 1:
            previous = self.source_lines[node.lineno - 2]
            if previous.lstrip().startswith("#"):
                match = pattern.search(previous)
        return match

    def legacy_annotation(self, node):
        """Return legacy compatibility metadata attached to a call site."""
        match = self.annotation(node, LEGACY_ANNOTATION)
        return (True, match.group(1) or "") if match else (False, "")

    def dynamic_annotation(self, node):
        """Return the dynamic path attached to a call site, if any."""
        match = self.annotation(node, DYNAMIC_ANNOTATION)
        return (match.group(1) or "*") if match else None

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

        # A parameter can be bound to anything by the caller, even if the
        # function also assigns a default to it.
        arguments = node.args
        for arg in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg):
            if arg is not None:
                assignments[arg.arg].append(UNKNOWN)

        def bind_unknown(target):
            for name in ast.walk(target):
                if isinstance(name, ast.Name):
                    assignments[name.id].append(UNKNOWN)

        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        assignments[target.id].append(child.value)
                    else:
                        bind_unknown(target)
            elif isinstance(child, (ast.AugAssign, ast.AnnAssign)):
                bind_unknown(child.target)
            elif isinstance(child, ast.NamedExpr):
                assignments[child.target.id].append(child.value)
            elif isinstance(child, ast.Call) and getattr(child.func, "attr", "") in ("append", "extend") and isinstance(child.func.value, ast.Name):
                assignments[child.func.value.id].extend(Appended(arg) for arg in child.args)
            elif isinstance(child, (ast.For, ast.comprehension)):
                targets = child.target.elts if isinstance(child.target, ast.Tuple) else [child.target]
                items = child.iter.elts if isinstance(child.iter, (ast.List, ast.Tuple, ast.Set)) else None
                if items is None:
                    for target in targets:
                        bind_unknown(target)
                    continue
                for item in items:
                    values = item.elts if isinstance(item, ast.Tuple) else [item]
                    if len(targets) != len(values):
                        for target in targets:
                            bind_unknown(target)
                        continue
                    for target, value in zip(targets, values):
                        if isinstance(target, ast.Name):
                            assignments[target.id].append(value)
                        else:
                            bind_unknown(target)
            elif isinstance(child, (ast.With, ast.AsyncWith)):
                for item in child.items:
                    if item.optional_vars is not None:
                        bind_unknown(item.optional_vars)

        return assignments

    def report_indirect(self, node, description):
        """Report a wrapper used indirectly, whose call sites cannot be found."""
        self.unresolved.append((f"carta/{self.module}:{node.lineno}", self.clazz, self.method, f"{ast.unparse(node)}  # {description}"))

    def visit_Attribute(self, node):
        """Report a wrapper method referenced without being called directly.

        A call through an alias, such as ``f = self.get_value`` followed by
        ``f(path)``, is not a wrapper call site, so its path would be missing
        from the manifest without any error.
        """
        self.generic_visit(node)
        # PLUMBING is deliberately not honoured here: plumbing may call another
        # wrapper directly, but an alias would hide that call as well.
        if node.attr in WRAPPERS and isinstance(node.ctx, ast.Load) and id(node) not in self.called:
            self.report_indirect(node, "referenced without being called; call it directly")

    def visit_Constant(self, node):
        """Report a wrapper named by a string, which hides its call sites.

        This covers ``getattr(obj, "get_value")``, ``operator.methodcaller``,
        ``operator.attrgetter`` and names stored in variables, whatever
        function eventually uses the string.
        """
        if isinstance(node.value, str) and node.value in WRAPPERS:
            self.report_indirect(node, "wrapper named by a string; call it directly")

    def visit_Call(self, node):
        """Scan a call, and record it if it is a wrapper call."""
        self.called.add(id(node.func))
        self.generic_visit(node)

        if not isinstance(node.func, ast.Attribute) or node.func.attr not in WRAPPERS:
            return
        if (self.module, self.clazz, self.method) in PLUMBING:
            return

        receiver = ast.unparse(node.func.value)

        # get_value(path, return_path) takes the projection as its second
        # positional argument; call_action passes its remaining positional
        # arguments to the frontend action.
        return_path_nodes = [keyword.value for keyword in node.keywords if keyword.arg == "return_path"]
        action_args = node.args[1:]
        if node.func.attr == "get_value":
            return_path_nodes.extend(node.args[1:2])
            action_args = []
        return_path, return_path_resolved = self.return_path(return_path_nodes)

        args, macros_resolved = self.macro_args(action_args)
        paths, exact = self.paths(node.args[0] if node.args else None)

        dynamic = self.dynamic_annotation(node)
        if dynamic is not None:
            paths, exact = [dynamic], False

        if not paths or receiver not in RECEIVERS or not return_path_resolved or not macros_resolved:
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

    @staticmethod
    def return_path(nodes):
        """The literal response projection of a call site, and whether it is literal."""
        if not nodes:
            return "", True
        if len(nodes) > 1:
            return "", False
        try:
            value = ast.literal_eval(nodes[0])
        except (ValueError, TypeError, SyntaxError):
            return "", False
        if value is None:
            return "", True
        if isinstance(value, (str, list, dict)):
            return value, True
        return "", False

    def values(self, node):
        """The expressions an argument may evaluate to.

        A local variable, or a variable unpacked with ``*``, is expanded to every
        value bound to it in the enclosing function; any other expression is
        returned unchanged.
        """
        node = node.value if isinstance(node, ast.Starred) else node
        if isinstance(node, ast.Name):
            values = self.assignments[-1].get(node.id, [UNKNOWN])
            return [value.node if isinstance(value, Appended) else value for value in values]
        if isinstance(node, ast.IfExp):
            return [node.body, node.orelse]
        return [node]

    def strings(self, node, *, allow_globs=False, depth=0):
        """The string constants an argument may evaluate to.

        Returns the strings, whether they are all exact, and whether every
        candidate value was resolved. Resolution is all-or-nothing: if any
        candidate is not a string constant (or, with ``allow_globs``, an
        f-string), the call site is reported as unresolved instead of being
        recorded with only the candidates which happen to be constants.
        """
        strings, exact = [], True
        if depth > 10:
            return [], True, False
        for value in self.values(node):
            if value is UNKNOWN:
                return [], True, False
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                strings.append(value.value)
            elif allow_globs and isinstance(value, ast.JoinedStr):
                strings.append("".join(v.value if isinstance(v, ast.Constant) else "*" for v in value.values))
                exact = False
            elif isinstance(value, (ast.List, ast.Tuple, ast.Name, ast.IfExp)):
                elements = value.elts if isinstance(value, (ast.List, ast.Tuple)) else [value]
                for element in elements:
                    nested, nested_exact, resolved = self.strings(element, allow_globs=allow_globs, depth=depth + 1)
                    if not resolved:
                        return [], True, False
                    strings.extend(nested)
                    exact &= nested_exact
            else:
                return [], True, False
        return strings, exact, True

    def macro_args(self, nodes):
        """Descriptors for the arguments of a call site which are frontend macros.

        A macro is either an attribute such as ``self._frame``, a call to the
        ``macro`` method of a wrapper object, or a :obj:`carta.util.Macro`
        constructed directly.

        Returns the descriptors and whether every macro was resolved. A macro
        whose target or variable is not a string constant, or which is built
        with keyword arguments, is unresolved.
        """
        descriptors = []
        for node in nodes:
            for value in self.values(node):
                if isinstance(value, ast.Attribute) and value.attr in ("_frame", "_region"):
                    descriptors.append(("attr", ast.unparse(value)))
                    continue
                if not isinstance(value, ast.Call):
                    continue
                name = getattr(value.func, "attr", getattr(value.func, "id", ""))
                if name not in ("macro", "Macro"):
                    continue
                if len(value.args) != 2 or value.keywords:
                    return descriptors, False
                owner = "" if name == "Macro" else ast.unparse(value.func.value)
                targets, _, targets_resolved = self.strings(value.args[0])
                variables, _, variables_resolved = self.strings(value.args[1])
                if not (targets_resolved and variables_resolved and targets and variables):
                    return descriptors, False
                for target in targets:
                    for variable in variables:
                        descriptors.append(("macro", owner, target, variable))
        return tuple(descriptors), True

    def paths(self, node):
        """The possible paths for the first argument of a call site.

        Returns the paths and whether they are exact. An inexact path is a glob
        in which each interpolated value has been replaced by ``*``.
        """
        if node is None:
            return [], True
        if isinstance(node, ast.Starred):
            # call_action(*args): the path is the first element of the list,
            # and values appended to it later are action arguments.
            if not isinstance(node.value, ast.Name):
                return [], True
            heads = []
            for value in self.assignments[-1].get(node.value.id, [UNKNOWN]):
                if isinstance(value, Appended):
                    continue
                if not isinstance(value, (ast.List, ast.Tuple)) or not value.elts or isinstance(value.elts[0], ast.Starred):
                    return [], True
                heads.append(value.elts[0])
            if not heads:
                return [], True
            node = ast.Tuple(elts=heads, ctx=ast.Load())
        strings, exact, resolved = self.strings(node, allow_globs=True)
        return (strings, exact) if resolved else ([], True)


class Registry:
    """Real wrapper objects, used to resolve the base path of each call site."""

    def __init__(self):
        self.session = Session(0, None)
        self.objects = []
        self.by_class = collections.defaultdict(list)
        self.seen = set()

        image = Image(self.session, 0)
        color_blending = ColorBlending(self.session, 0)
        for obj in (self.session, image, color_blending, Layer(color_blending, 0)):
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
        instances = [o for o in self.by_class[clazz] if hasattr(o, site.wrapper)]
        if not instances:
            raise ValueError(f"No registered {clazz} receiver for {site.location} ({site.qualname})")
        return instances


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

    root = path.split(".", 1)[0]
    return [FRONTEND_ROOT_TYPES[root]] if root in FRONTEND_ROOT_TYPES else ["AppStore"]


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
        # A frontend API can be used with several response projections. Each
        # projection gets its own entry, so that a checker which validates the
        # single ``return_path`` of each entry validates all of them.
        for projection in sorted(api.return_paths, key=lambda projection: json.dumps(projection, sort_keys=True)):
            entry = {
                "kind": api.kind,
                "path": api.path,
                "exact": api.exact,
                "runtime_types": sorted(api.runtime_types),
                "wrappers": sorted({s.qualname for s in api.sites if api.kind == "reference" or s.return_path == projection}),
                "return_path": projection,
            }
            if not api.required:
                entry["compatibility"] = "legacy"
                if api.legacy_until:
                    entry["until"] = api.legacy_until
            entries.append(entry)
    return {"apis": entries}


def dump_manifest(data):
    """The canonical serialisation of the manifest."""
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def print_unresolved(unresolved, *, file=None):
    """Print unresolved call sites to the requested output stream."""
    print(f"\nUNRESOLVED CALL SITES ({len(unresolved)})\n", file=file)
    for location, clazz, method, source in unresolved:
        print(f"  {location} {clazz}.{method}\n      {source}", file=file)


def print_report(apis, unresolved, sites, objects):
    """Print every frontend API, and any unresolved call sites, as text."""
    for kind in ("action", "parameter", "reference"):
        selected = [a for a in apis if a.kind == kind]
        print(f"\n{kind.upper()}S ({len(selected)})\n")
        for api in selected:
            return_paths = api.return_paths
            if len(return_paths) > 1:
                suffix = f" -> {return_paths}"
            else:
                suffix = f" -> {return_paths[0]}" if return_paths[0] else ""
            compatibility = "  [legacy" + (f" until={api.legacy_until}" if api.legacy_until else "") + "]" if not api.required else ""
            print(f"  {api.path}{suffix}{'' if api.exact else '  [glob]'}{compatibility}")
    print_unresolved(unresolved)

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
    elif failed:
        print_unresolved(unresolved, file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
