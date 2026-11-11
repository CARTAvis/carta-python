import importlib.util
import json
import pathlib
import sys

import pytest

from carta import constants
from carta.color_blending import Layer
from carta.region import TextAnnotation
from carta.wcs_overlay import ColorbarComponent, Global


SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "extract_api.py"


def load_script():
    spec = importlib.util.spec_from_file_location("extract_api", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extract = load_script()


def test_manifest_contains_expected_api_entries():
    sites, unresolved = extract.scan()
    assert unresolved == []

    apis = extract.replay(extract.Registry(), sites)
    data = extract.manifest(sorted(apis.values(), key=lambda api: (api.kind, api.path)))
    represented_sites = {id(site) for api in apis.values() for site in api.sites}

    assert [site.qualname for site in sites if id(site) not in represented_sites] == []
    assert set(data) == {"apis"}
    assert data["apis"]
    assert [(api["kind"], api["path"]) for api in data["apis"]] == sorted(
        (api["kind"], api["path"]) for api in data["apis"]
    )
    assert all("return_paths" not in api for api in data["apis"])
    assert any(api["path"] == "getImageDataUrl" for api in data["apis"])
    assert next(api for api in data["apis"] if api["path"] == "activeImage")["return_path"] == {
        "type": "type",
        "id": "store.id",
    }
    region_list_apis = [api for api in data["apis"] if api["path"] == "frameMap[*].regionSet.regionList"]
    assert [(api["return_path"], api["wrappers"]) for api in region_list_apis] == [
        ("", ["RegionSet.list"]),
        ("id", ["RegionSet.export_to"]),
    ]
    assert all("MINIMUM_CARTA_VERSION" not in api for api in data["apis"])


def test_scanner_preserves_composite_return_paths():
    source = """\
class Example:
    def get(self):
        self.get_value("items", return_path=["id", "name"])
        self.get_value("active", return_path={"type": "type", "id": "store.id"})
"""
    scanner = extract.Scanner("example.py", source)
    scanner.visit(extract.ast.parse(source))

    assert scanner.unresolved == []
    assert [site.return_path for site in scanner.sites] == [
        ["id", "name"],
        {"type": "type", "id": "store.id"},
    ]


@pytest.mark.parametrize("assignment", ["", 'path = "items"\n'])
def test_scanner_reports_unresolved_module_level_path(assignment):
    source = assignment + "session.get_value(path)\n"
    scanner = extract.Scanner("example.py", source)

    scanner.visit(extract.ast.parse(source))

    line = 2 if assignment else 1
    assert scanner.sites == []
    assert scanner.unresolved == [(f"carta/example.py:{line}", "", "", "session.get_value(path)")]


def test_scanner_handles_module_level_action_arguments():
    source = 'session.call_action("appendFile", directory, file_name)\n'
    scanner = extract.Scanner("example.py", source)

    scanner.visit(extract.ast.parse(source))

    assert scanner.unresolved == []
    assert len(scanner.sites) == 1
    assert scanner.sites[0].path == "appendFile"
    assert scanner.sites[0].receiver == "session"


def test_check_reports_unresolved_sites_when_writing_manifest(monkeypatch, tmp_path, capsys):
    output = tmp_path / "api.json"
    unresolved = [("carta/example.py:4", "Example", "get", "self.get_value(path)")]
    monkeypatch.setattr(extract, "scan", lambda: ([], unresolved))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--check", "--write-manifest", "--output", str(output)])

    assert extract.main() == 1

    captured = capsys.readouterr()
    assert "UNRESOLVED CALL SITES (1)" in captured.err
    assert "carta/example.py:4 Example.get" in captured.err
    assert "self.get_value(path)" in captured.err
    assert json.loads(output.read_text()) == {"apis": []}


def test_legacy_annotation_marks_an_api_as_compatibility_only():
    source = """\
class Example:
    def update(self):
        # carta-api:legacy until=6.1
        self.call_action("oldStore.setFoo")
"""
    scanner = extract.Scanner("example.py", source)
    scanner.visit(extract.ast.parse(source))

    assert scanner.unresolved == []
    assert len(scanner.sites) == 1
    assert scanner.sites[0].legacy is True
    assert scanner.sites[0].legacy_until == "6.1"

    api = extract.Api("action", "oldStore.setFoo")
    api.add(scanner.sites[0])
    entry = extract.manifest([api])["apis"][0]
    assert entry["compatibility"] == "legacy"
    assert entry["until"] == "6.1"


def test_dynamic_annotation_declares_a_wildcard_api():
    source = """\
class Example:
    def get(self, name):
        # carta-api:dynamic path=*
        return self.get_value(name)
"""
    scanner = extract.Scanner("example.py", source)
    scanner.visit(extract.ast.parse(source))

    assert scanner.unresolved == []
    assert len(scanner.sites) == 1
    assert scanner.sites[0].path == "*"
    assert scanner.sites[0].exact is False
    assert scanner.sites[0].dynamic is True


def scan_source(source):
    scanner = extract.Scanner("example.py", source)
    scanner.visit(extract.ast.parse(source))
    return scanner


@pytest.mark.parametrize("source", [
    # Only one of the candidates is a constant.
    """\
class Example:
    def get(self, flag):
        path = "isValidWcs" if flag else self._compute()
        return self.get_value(path)
""",
    # A loop over a tuple with a computed element.
    """\
class Example:
    def get(self):
        for path in ("isValidWcs", self.name()):
            self.get_value(path)
""",
    # A loop over a computed iterable.
    """\
class Example:
    def get(self):
        for path in self.paths():
            self.get_value(path)
""",
    # A parameter with a default assigned in the body can still be passed by the caller.
    """\
class Example:
    def get(self, path=None):
        if path is None:
            path = "isValidWcs"
        return self.get_value(path)
""",
    # A projection which is not a literal.
    """\
class Example:
    def get(self, field):
        return self.get_value("frameInfo", field)
""",
    # A macro with a computed variable name.
    """\
class Example:
    def get(self, name):
        self.call_action("setFoo", Macro("", name))
""",
    # A macro built with keyword arguments.
    """\
class Example:
    def get(self):
        self.call_action("setFoo", Macro(target="", variable="bar"))
""",
    # A starred argument list which does not start with a constant path.
    """\
class Example:
    def get(self, action):
        args = [action]
        return self.call_action(*args)
""",
])
def test_scanner_reports_partially_resolved_call_sites(source):
    scanner = scan_source(source)

    assert scanner.sites == []
    assert len(scanner.unresolved) == 1


REFERENCED = "referenced without being called"
NAMED = "wrapper named by a string"


@pytest.mark.parametrize("source,description", [
    # An alias called later
    ("""\
class Example:
    def get(self):
        f = self.get_value
        return f("isVisible")
""", REFERENCED),
    # A partial application
    ("""\
class Example:
    def set(self):
        return functools.partial(self.call_action, "setFoo")
""", REFERENCED),
    # An alias defined in the class body
    ("""\
class Example:
    fetch = BasePathMixin.get_value
""", REFERENCED),
    # An alias inside a plumbing method, whose direct calls are exempt
    ("""\
class BasePathMixin:
    def call_action(self, path):
        send = self.session.call_action
        return send(path)
""", REFERENCED),
    # getattr with a constant name, with or without a default
    ("""\
class Example:
    def get(self):
        return getattr(self, "get_value")("isVisible")
""", NAMED),
    ("""\
class Example:
    def get(self):
        return getattr(self, "get_value", None)("isVisible")
""", NAMED),
    # A nested getattr is reported once
    ("""\
class Example:
    def set(self):
        return getattr(self.session, "call_action")("setFoo")
""", NAMED),
    # A name stored in a variable
    ("""\
class Example:
    def get(self):
        name = "get_value"
        return getattr(self, name)("isVisible")
""", NAMED),
    # operator helpers
    ("""\
class Example:
    def get(self):
        return operator.methodcaller("get_value", "isVisible")(self)
""", NAMED),
    ("""\
class Example:
    def set(self):
        return attrgetter("call_action")(self)("setFoo")
""", NAMED),
    # Annotations do not apply to indirect use
    ("""\
class Example:
    def get(self):
        f = self.get_value  # carta-api:dynamic
        return f("isVisible")
""", REFERENCED),
])
def test_scanner_reports_wrappers_used_indirectly(source, description):
    # Scan as util.py so that BasePathMixin.call_action is a plumbing method.
    scanner = extract.Scanner("util.py", source)
    scanner.visit(extract.ast.parse(source))

    assert scanner.sites == []
    assert len(scanner.unresolved) == 1
    location, _, _, text = scanner.unresolved[0]
    assert location.startswith("carta/util.py:")
    assert description in text


def test_scanner_accepts_direct_calls_and_other_lookups():
    scanner = scan_source("""\
class Example:
    def get(self):
        self.call_action("setFoo", 1)
        value = self.get_value("isVisible")
        return getattr(self, "width"), value
""")

    assert scanner.unresolved == []
    assert [site.path for site in scanner.sites] == ["setFoo", "isVisible"]


def test_scanner_ignores_assigning_or_deleting_wrapper_attributes():
    scanner = scan_source("""\
class Example:
    def patch(self, recorder):
        self.get_value = recorder
        del self.call_action
""")

    assert scanner.unresolved == []
    assert scanner.sites == []


def test_scanner_exempts_direct_calls_in_plumbing_methods():
    source = """\
class BasePathMixin:
    def call_action(self, path, *args):
        return self.session.call_action(f"{self._base_path}.{path}", *args)
"""
    scanner = extract.Scanner("util.py", source)
    scanner.visit(extract.ast.parse(source))

    assert scanner.unresolved == []
    assert scanner.sites == []


def test_scanner_reads_positional_get_value_projection():
    scanner = scan_source("""\
class Example:
    def get(self):
        return self.get_value("frameInfo", "fileInfo")
""")

    assert scanner.unresolved == []
    assert [(site.path, site.return_path, site.args) for site in scanner.sites] == [("frameInfo", "fileInfo", ())]


def test_scanner_resolves_starred_path_with_appended_arguments():
    scanner = scan_source("""\
class Example:
    def get(self, color=None):
        args = ["getImageDataUrl"]
        if color:
            args.append(color)
        return self.call_action(*args)
""")

    assert scanner.unresolved == []
    assert [site.path for site in scanner.sites] == ["getImageDataUrl"]


@pytest.mark.parametrize("annotation", ["legacy", "dynamic"])
def test_trailing_annotation_does_not_apply_to_the_next_call(annotation):
    scanner = scan_source(f"""\
class Example:
    def update(self):
        self.call_action("oldStore.setFoo")  # carta-api:{annotation}
        self.call_action("newStore.setBar")
""")

    assert scanner.unresolved == []
    first, second = scanner.sites
    assert (first.legacy or first.dynamic) is True
    assert (second.path, second.legacy, second.dynamic) == ("newStore.setBar", False, False)


def test_manifest_serialisation_is_canonical():
    data = {"apis": [{"kind": "action", "path": "setFoo"}]}
    dumped = extract.dump_manifest(data)

    assert dumped.endswith("\n")
    assert json.loads(dumped) == data


@pytest.mark.parametrize("projection", ["id", ["id", "name"], {"region_id": "id"}])
def test_manifest_preserves_multiple_return_paths_for_one_api(projection):
    sites = [
        extract.Site("example.py", 1, "Example", "get", "get_value", "self", "items", True, ""),
        extract.Site("example.py", 2, "Example", "get_ids", "get_value", "self", "items", True, projection),
    ]
    api = extract.Api("parameter", "items")
    for site in sites:
        api.add(site)

    entries = extract.manifest([api])["apis"]

    assert [(entry["return_path"], entry["wrappers"]) for entry in entries] == [
        ("", ["Example.get"]),
        (projection, ["Example.get_ids"]),
    ]
    assert all("return_paths" not in entry for entry in entries)


def test_manifest_keeps_single_return_path_compatible():
    site = extract.Site("example.py", 1, "Example", "get_ids", "get_value", "self", "items", True, "id")
    api = extract.Api("parameter", "items", return_path="id")
    api.add(site)
    # Repeated use of the same projection must retain the single-field format.
    api.add(site)

    entries = extract.manifest([api])["apis"]

    assert len(entries) == 1
    assert entries[0]["return_path"] == "id"


def test_manifest_projection_serialisation_is_independent_of_scan_order():
    projection_orders = [
        ["", "id", ["id", "name"], {"name": "name", "region_id": "id"}],
        [{"region_id": "id", "name": "name"}, ["id", "name"], "id", ""],
    ]
    manifests = []
    for projections in projection_orders:
        api = extract.Api("parameter", "items", return_path=projections[0])
        for line, projection in enumerate(projections, start=1):
            api.add(extract.Site("example.py", line, "Example", "get", "get_value", "self", "items", True, projection))
        manifests.append(extract.dump_manifest(extract.manifest([api])))

    assert manifests[0] == manifests[1]
    assert [entry["return_path"] for entry in json.loads(manifests[0])["apis"]] == [
        "", "id", ["id", "name"], {"name": "name", "region_id": "id"},
    ]


def test_registry_contains_expected_python_wrapper_types():
    registry = extract.Registry()

    assert registry.by_class["Session"]
    assert registry.by_class["Image"]
    assert registry.by_class[Layer.__name__]
    assert constants.RegionType.POINT in constants.RegionType


def test_every_call_site_has_a_registered_receiver():
    sites, _ = extract.scan()
    registry = extract.Registry()

    missing = [site.qualname for site in sites if not registry.instances(site)]

    assert missing == []


def test_registry_rejects_call_site_without_a_receiver():
    site = extract.Site("example.py", 1, "Example", "get", "get_value", "self", "value", True, "")

    with pytest.raises(ValueError, match="No registered Example receiver"):
        extract.Registry().instances(site)


def test_frontend_runtime_types_are_declared_on_wrapper_classes():
    assert TextAnnotation.FRONTEND_RUNTIME_TYPE == "TextAnnotationStore"
    assert Global.FRONTEND_RUNTIME_TYPE == "OverlayGlobalSettings"
    assert ColorbarComponent.FRONTEND_RUNTIME_TYPE == "OverlayColorbarSettings"

    assert extract.frontend_runtime_types(
        "frameMap[*].regionSet.regionMap[*].setText", object.__new__(TextAnnotation)
    ) == ["TextAnnotationStore"]
    assert extract.frontend_runtime_types(
        "overlaySettings.global.setColor", object.__new__(Global)
    ) == ["OverlayGlobalSettings"]
