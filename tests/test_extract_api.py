import importlib.util
import json
import pathlib

from carta import constants
from carta.region import TextAnnotation
from carta.wcs_overlay import ColorbarComponent, Global


SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "extract_api.py"


def load_script():
    spec = importlib.util.spec_from_file_location("extract_api", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extract = load_script()


def test_manifest_is_generated_without_version_or_deprecation_data():
    sites, unresolved = extract.scan()
    assert unresolved == []

    apis = extract.replay(extract.Registry(), sites)
    data = extract.manifest(sorted(apis.values(), key=lambda api: (api.kind, api.path)))

    assert set(data) == {"apis"}
    assert data["apis"]
    assert [(api["kind"], api["path"]) for api in data["apis"]] == sorted(
        (api["kind"], api["path"]) for api in data["apis"]
    )
    assert any(api["path"] == "getImageDataUrl" for api in data["apis"])
    assert all("MINIMUM_CARTA_VERSION" not in api for api in data["apis"])


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


def test_registry_contains_expected_python_wrapper_types():
    registry = extract.Registry()

    assert registry.by_class["Session"]
    assert registry.by_class["Image"]
    assert constants.RegionType.POINT in constants.RegionType


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
