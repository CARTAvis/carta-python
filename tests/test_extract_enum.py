import importlib.util
import json
import pathlib
from enum import IntEnum

import pytest

from carta import constants


SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "extract_enum.py"


def load_script():
    spec = importlib.util.spec_from_file_location("extract_enum", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extract = load_script()


def test_manifest_groups_enum_sources_and_keeps_protobuf_names_unqualified():
    data = extract.manifest()

    assert set(data) == {"enums"}
    assert set(data["enums"]) == {"carta-python", "frontend", "protobuf"}
    assert "FontStyle" in data["enums"]["carta-python"]
    assert "FontStyle" in data["enums"]["frontend"]
    assert "RegionType" in data["enums"]["protobuf"]
    assert "protobuf:RegionType" not in data["enums"]["protobuf"]
    assert {member["name"] for member in data["enums"]["protobuf"]["RegionType"]} == {
        "POINT",
        "LINE",
        "POLYLINE",
        "RECTANGLE",
        "ELLIPSE",
        "ANNULUS",
        "POLYGON",
        "ANNPOINT",
        "ANNLINE",
        "ANNPOLYLINE",
        "ANNRECTANGLE",
        "ANNELLIPSE",
        "ANNPOLYGON",
        "ANNVECTOR",
        "ANNRULER",
        "ANNTEXT",
        "ANNCOMPASS",
    }


def test_protobuf_registry_owns_source_identification():
    assert constants.SmoothingMode.EXTERNAL_NAME == "SmoothingMode"
    assert constants.ProtobufEnum.ENUMS["SmoothingMode"] is constants.SmoothingMode
    assert "protobuf:SmoothingMode" not in constants.ProtobufEnum.ENUMS
    assert "EXTERNAL_NAME" not in constants.SmoothingMode.__members__


def test_manifest_is_canonical():
    data = extract.manifest()
    dumped = extract.dump_manifest(data)

    assert dumped.endswith("\n")
    assert json.loads(dumped) == data


def test_enum_members_include_aliases():
    class AliasEnum(IntEnum):
        FIRST = 1
        ALSO_FIRST = 1

    assert extract.enum_members(AliasEnum) == [
        {"name": "ALSO_FIRST", "value": 1},
        {"name": "FIRST", "value": 1},
    ]


def test_enum_registry_rejects_duplicate_external_names():
    with pytest.raises(ValueError, match="Duplicate enum external name"):
        class DuplicateFrontendEnum(constants.FrontendEnum, IntEnum, external_name="ColorMap"):
            VALUE = 0

    with pytest.raises(ValueError, match="Duplicate enum external name"):
        constants._registered_enum(
            constants.FrontendEnum,
            IntEnum,
            "DuplicateFunctionalEnum",
            ("VALUE",),
            external_name="ColorMap",
        )
