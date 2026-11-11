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
    assert any(api["path"] == "getImageDataUrl" for api in data["apis"])
    assert next(api for api in data["apis"] if api["path"] == "activeImage")["return_path"] == {
        "type": "type",
        "id": "store.id",
    }
    region_list_api = next(api for api in data["apis"] if api["path"] == "frameMap[*].regionSet.regionList")
    assert region_list_api["return_paths"] == ["", "id"]
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

    entry = extract.manifest([api])["apis"][0]

    assert "return_path" not in entry
    assert entry["return_paths"] == ["", projection]


def test_manifest_keeps_single_return_path_compatible():
    site = extract.Site("example.py", 1, "Example", "get_ids", "get_value", "self", "items", True, "id")
    api = extract.Api("parameter", "items", return_path="id")
    api.add(site)
    # Repeated use of the same projection must retain the single-field format.
    api.add(site)

    entry = extract.manifest([api])["apis"][0]

    assert entry["return_path"] == "id"
    assert "return_paths" not in entry


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
    assert json.loads(manifests[0])["apis"][0]["return_paths"] == [
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
