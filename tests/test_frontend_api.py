import importlib.util
import json
import pathlib

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "extract_frontend_api.py"


def load_script():
    spec = importlib.util.spec_from_file_location("extract_frontend_api", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extract = load_script()


@pytest.fixture(scope="module")
def manifest():
    sites, _ = extract.scan()
    apis = extract.replay(extract.Registry(), sites)
    return extract.manifest(sorted(apis.values(), key=lambda a: (a.kind, a.path)))


def deprecations(*paths):
    return [{"path": path, "kind": "action", "owner": "Store", "member": path.rpartition(".")[2], "message": "gone"} for path in paths]


def api(path, exact=True):
    return {"kind": "action", "path": path, "exact": exact, "return_path": "", "runtime_types": [], "wrappers": ["Wrapper.method"]}


def test_manifest_is_current(manifest):
    assert extract.manifest_diff(manifest) == "", "frontend_api.json is out of date: run scripts/extract_frontend_api.py --write-manifest"


def test_manifest_matches_committed_file(manifest):
    assert json.loads(extract.MANIFEST.read_text()) == manifest


def test_manifest_has_only_api_entries(manifest):
    assert set(manifest) == {"apis"}


def test_manifest_entries_are_sorted_and_stable(manifest):
    entries = manifest["apis"]
    assert entries
    assert [(e["kind"], e["path"]) for e in entries] == sorted((e["kind"], e["path"]) for e in entries)
    for entry in entries:
        # Source locations are excluded, so that unrelated edits do not change the contract.
        assert set(entry) == {"kind", "path", "exact", "return_path", "runtime_types", "wrappers"}
        assert entry["kind"] in ("action", "parameter", "reference")
        assert entry["runtime_types"] == sorted(entry["runtime_types"])
        assert entry["wrappers"] == sorted(entry["wrappers"])


def test_manifest_serialisation_is_canonical(manifest):
    dumped = extract.dump_manifest(manifest)
    assert dumped.endswith("\n")
    assert json.loads(dumped) == manifest


def test_manifest_diff_reports_a_change(manifest):
    changed = {"apis": [dict(manifest["apis"][0], path="changed")]}
    diff = extract.manifest_diff(changed)
    assert "changed" in diff


def test_exact_path_is_deprecated():
    assert extract.deprecated_apis(api("frameMap[*].renderConfig.setColorMap"), deprecations("frameMap[*].renderConfig.setColorMap"))


def test_unrelated_path_is_not_deprecated():
    assert not extract.deprecated_apis(api("frameMap[*].renderConfig.setColorMap"), deprecations("frameMap[*].renderConfig.setGamma"))


def test_wrapper_glob_matches_deprecated_path():
    assert extract.deprecated_apis(api("frameMap[*].zoomToSize*", exact=False), deprecations("frameMap[*].zoomToSizeXWcs"))


def test_frontend_glob_matches_wrapper_path():
    assert extract.deprecated_apis(api("overlaySettings.colorbar.setLabelFont"), deprecations("overlaySettings.colorbar.setLabel*"))


def test_wildcard_matches_a_single_component_only():
    assert extract.deprecated_apis(api("preferenceStore.*", exact=False), deprecations("preferenceStore.astGridVisible"))
    assert not extract.deprecated_apis(api("preferenceStore.*", exact=False), deprecations("preferenceStore.nested.value"))


def test_index_placeholder_is_not_a_wildcard():
    assert not extract.deprecated_apis(api("frameMap[*].setZoom"), deprecations("frameMapEntry.setZoom"))
    assert not extract.deprecated_apis(api("frameMap[*].setZoom"), deprecations("frames[*].setZoom"))
    assert extract.deprecated_apis(api("frameMap[*].regionSet.regionMap[*].setColor"), deprecations("frameMap[*].regionSet.regionMap[*].setColor"))


def test_report_deprecations_counts_matches(capsys):
    data = {"schema": 1, "frontend_version": "6.1.0-dev", "deprecations": deprecations("a.b", "c.d")}
    assert extract.report_deprecations([api("a.b"), api("e.f")], data) == 1
    output = capsys.readouterr().out
    assert "a.b" in output
    assert "Wrapper.method" in output
    assert "6.1.0-dev" in output


def test_load_deprecations(tmp_path):
    path = tmp_path / "deprecations.json"
    path.write_text(json.dumps({"schema": extract.SCHEMA, "frontend_version": "6.1.0-dev", "deprecations": []}))
    assert extract.load_deprecations(path)["deprecations"] == []


def test_load_deprecations_rejects_an_unknown_schema(tmp_path):
    path = tmp_path / "deprecations.json"
    path.write_text(json.dumps({"schema": extract.SCHEMA + 1, "deprecations": []}))
    with pytest.raises(SystemExit):
        extract.load_deprecations(path)
