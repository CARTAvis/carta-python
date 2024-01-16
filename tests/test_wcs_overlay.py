import pytest

from carta.util import CartaValidationFailed
from carta.wcs_overlay import WCSOverlay
from carta.constants import NumberFormat as NF, Overlay as O, CoordinateSystem as CS, PaletteColor as PC, FontFamily as FF, FontStyle as FS, LabelType as LT, ColorbarPosition as CP, BeamType as BT


# FIXTURES


@pytest.fixture
def overlay(session):
    return WCSOverlay(session)


@pytest.fixture
def get_value(overlay, mock_get_value):
    return mock_get_value(overlay)


@pytest.fixture
def component_get_value(overlay, mocker):
    def func(comp_enum, mock_value=None):
        return mocker.patch.object(overlay.get(comp_enum), "get_value", return_value=mock_value)
    return func


@pytest.fixture
def session_get_value(session, mock_get_value):
    return mock_get_value(session)


@pytest.fixture
def call_action(overlay, mock_call_action):
    return mock_call_action(overlay)


@pytest.fixture
def component_call_action(overlay, mock_call_action):
    def func(comp_enum):
        return mock_call_action(overlay.get(comp_enum))
    return func


@pytest.fixture
def method(overlay, mock_method):
    return mock_method(overlay)


@pytest.fixture
def component_method(overlay, mock_method):
    def func(comp_enum):
        return mock_method(overlay.get(comp_enum))
    return func

# TESTS


@pytest.mark.parametrize("name,classname", [
    ("global_", "Global"),
    ("title", "Title"),
    ("grid", "Grid"),
    ("border", "Border"),
    ("ticks", "Ticks"),
    ("axes", "Axes"),
    ("numbers", "Numbers"),
    ("labels", "Labels"),
    ("colorbar", "Colorbar"),
    ("beam", "Beam"),
])
def test_subobjects(overlay, name, classname):
    assert getattr(overlay, name).__class__.__name__ == classname


@pytest.mark.parametrize("name,classname", [
    ("border", "ColorbarBorder"),
    ("ticks", "ColorbarTicks"),
    ("numbers", "ColorbarNumbers"),
    ("label", "ColorbarLabel"),
    ("gradient", "ColorbarGradient"),
])
def test_colorbar_subobjects(overlay, name, classname):
    assert getattr(overlay.colorbar, name).__class__.__name__ == classname


@pytest.mark.parametrize("theme_is_dark,expected_rgb", [(True, "#f5498b"), (False, "#c22762")])
def test_palette_to_rgb(overlay, session_get_value, theme_is_dark, expected_rgb):
    session_get_value.side_effect = [theme_is_dark]
    rgb = overlay.palette_to_rgb(PC.ROSE)
    assert rgb == expected_rgb


def test_set_view_area(overlay, call_action):
    overlay.set_view_area(100, 200)
    call_action.assert_called_with("setViewDimension", 100, 200)


def test_toggle_labels(overlay, call_action):
    overlay.toggle_labels()
    call_action.assert_called()


# COMPONENT TESTS

@pytest.mark.parametrize("comp_enum", [O.GLOBAL, O.BEAM])
def test_set_color(overlay, comp_enum, component_call_action):
    comp = overlay.get(comp_enum)
    comp_call_action = component_call_action(comp_enum)
    comp.set_color(PC.ROSE)
    comp_call_action.assert_called_with("setColor", "auto-rose")


@pytest.mark.parametrize("comp_enum", set(O) - {O.GLOBAL, O.BEAM})
def test_set_color_with_custom_flag(mocker, overlay, comp_enum, component_call_action):
    comp = overlay.get(comp_enum)
    comp_call_action = component_call_action(comp_enum)
    comp.set_color(PC.ROSE)
    comp_call_action.assert_has_calls([
        mocker.call("setColor", "auto-rose"),
        mocker.call("setCustomColor", True),
    ])


@pytest.mark.parametrize("comp_enum", set(O) - {O.GLOBAL, O.BEAM})
def test_set_custom_color(overlay, comp_enum, component_call_action):
    comp = overlay.get(comp_enum)
    comp_call_action = component_call_action(comp_enum)
    comp.set_custom_color(True)
    comp_call_action.assert_called_with("setCustomColor", True)


@pytest.mark.parametrize("comp_enum", O)
def test_color(overlay, component_get_value, comp_enum):
    comp_get_value = component_get_value(comp_enum, "auto-rose")
    comp = overlay.get(comp_enum)
    color = comp.color
    comp_get_value.assert_called_with("color")
    assert color == PC.ROSE


@pytest.mark.parametrize("comp_enum", set(O) - {O.GLOBAL, O.BEAM})
def test_custom_color(overlay, component_get_value, comp_enum):
    comp_get_value = component_get_value(comp_enum, True)
    comp = overlay.get(comp_enum)
    custom_color = comp.custom_color
    comp_get_value.assert_called_with("customColor")
    assert custom_color is True


@pytest.mark.parametrize("comp_enum", [O.TITLE, O.LABELS])
def test_set_custom_text(overlay, comp_enum, component_call_action):
    comp = overlay.get(comp_enum)
    comp_call_action = component_call_action(comp_enum)
    comp.set_custom_text(True)
    comp_call_action.assert_called_with("setCustomText", True)


@pytest.mark.parametrize("comp_enum", [O.TITLE, O.LABELS])
def test_custom_text(overlay, component_get_value, comp_enum):
    comp_get_value = component_get_value(comp_enum, True)
    comp = overlay.get(comp_enum)
    custom_text = comp.custom_text
    comp_get_value.assert_called_with("customText")
    assert custom_text is True


@pytest.mark.parametrize("comp_enum", [O.TITLE, O.NUMBERS, O.LABELS])
def test_set_font(overlay, component_call_action, comp_enum):
    comp = overlay.get(comp_enum)
    comp_call_action = component_call_action(comp_enum)
    comp.set_font(FF.ARIAL, FS.BOLD)
    comp_call_action.assert_called_with("setFont", 9)


@pytest.mark.parametrize("comp_enum", [O.TITLE, O.NUMBERS, O.LABELS])
def test_font(overlay, component_get_value, comp_enum):
    comp = overlay.get(comp_enum)
    comp_get_value = component_get_value(comp_enum, 9)
    family, style = comp.font
    comp_get_value.assert_called_with("font")
    assert family == FF.ARIAL
    assert style == FS.BOLD


@pytest.mark.parametrize("comp_enum", set(O) - {O.GLOBAL})
def test_set_visible(overlay, component_call_action, comp_enum):
    comp = overlay.get(comp_enum)
    comp_call_action = component_call_action(comp_enum)
    comp.set_visible(True)
    comp_call_action.assert_called_with("setVisible", True)


@pytest.mark.parametrize("comp_enum", set(O) - {O.GLOBAL})
def test_show_hide(mocker, overlay, component_method, comp_enum):
    comp = overlay.get(comp_enum)
    comp_method = component_method(comp_enum)("set_visible", None)

    comp.show()
    comp.hide()

    comp_method.assert_has_calls([
        mocker.call(True),
        mocker.call(False),
    ])


@pytest.mark.parametrize("comp_enum", set(O) - {O.GLOBAL})
def test_visible(overlay, component_get_value, comp_enum):
    comp = overlay.get(comp_enum)
    comp_get_value = component_get_value(comp_enum, True)
    visible = comp.visible
    comp_get_value.assert_called_with("visible")
    assert visible is True


@pytest.mark.parametrize("comp_enum", [O.GRID, O.BORDER, O.AXES, O.TICKS, O.COLORBAR, O.BEAM])
def test_set_width(overlay, component_call_action, comp_enum):
    comp = overlay.get(comp_enum)
    comp_call_action = component_call_action(comp_enum)
    comp.set_width(5)
    comp_call_action.assert_called_with("setWidth", 5)


@pytest.mark.parametrize("comp_enum", [O.GRID, O.BORDER, O.AXES, O.TICKS, O.COLORBAR, O.BEAM])
def test_width(overlay, component_get_value, comp_enum):
    comp = overlay.get(comp_enum)
    comp_get_value = component_get_value(comp_enum, 5)
    width = comp.width
    comp_get_value.assert_called_with("width")
    assert width == 5


def test_global_set_tolerance(overlay, component_call_action):
    global_call_action = component_call_action(O.GLOBAL)
    overlay.global_.set_tolerance(85)
    global_call_action.assert_called_with("setTolerance", 85)


def test_global_tolerance(overlay, component_get_value):
    global_get_value = component_get_value(O.GLOBAL, 85)
    tolerance = overlay.global_.tolerance
    global_get_value.assert_called_with("tolerance")
    assert tolerance == 85


def test_global_set_labelling(overlay, component_call_action):
    global_call_action = component_call_action(O.GLOBAL)
    overlay.global_.set_labelling(LT.EXTERIOR)
    global_call_action.assert_called_with("setLabelType", LT.EXTERIOR)


def test_global_labelling(overlay, component_get_value):
    global_get_value = component_get_value(O.GLOBAL, "Exterior")
    labelling = overlay.global_.labelling
    global_get_value.assert_called_with("labelType")
    assert labelling == LT.EXTERIOR


@pytest.mark.parametrize("system", CS)
def test_global_set_coordinate_system(overlay, component_call_action, system):
    global_call_action = component_call_action(O.GLOBAL)
    overlay.global_.set_coordinate_system(system)
    global_call_action.assert_called_with("setSystem", system)


def test_global_set_coordinate_system_invalid(overlay):
    with pytest.raises(CartaValidationFailed) as e:
        overlay.global_.set_coordinate_system("invalid")
    assert "Invalid function parameter" in str(e.value)


def test_global_coordinate_system(overlay, component_get_value):
    global_get_value = component_get_value(O.GLOBAL, "AUTO")
    system = overlay.global_.coordinate_system
    global_get_value.assert_called_with("system")
    assert isinstance(system, CS)


def test_grid_set_gap(mocker, overlay, component_call_action):
    grid_call_action = component_call_action(O.GRID)
    overlay.grid.set_gap(2, 3)
    grid_call_action.assert_has_calls([
        mocker.call("setGapX", 2),
        mocker.call("setGapY", 3),
        mocker.call("setCustomGap", True),
    ])


def test_grid_set_custom_gap(overlay, component_call_action):
    grid_call_action = component_call_action(O.GRID)
    overlay.grid.set_custom_gap(False)
    grid_call_action.assert_called_with("setCustomGap", False)


def test_grid_gap(mocker, overlay, component_get_value):
    grid_get_value = component_get_value(O.GRID)
    grid_get_value.side_effect = [2, 3]
    gap_x, gap_y = overlay.grid.gap
    grid_get_value.assert_has_calls([mocker.call("gapX"), mocker.call("gapY")])
    assert gap_x == 2
    assert gap_y == 3


def test_grid_custom_gap(overlay, component_get_value):
    grid_get_value = component_get_value(O.GRID, True)
    custom_gap = overlay.grid.custom_gap
    grid_get_value.assert_called_with("customGap")
    assert custom_gap is True


@pytest.mark.parametrize("x", NF)
@pytest.mark.parametrize("y", NF)
def test_numbers_set_format(mocker, overlay, component_call_action, x, y):
    numbers_call_action = component_call_action(O.NUMBERS)
    overlay.numbers.set_format(x, y)
    numbers_call_action.assert_has_calls([
        mocker.call("setFormatX", x),
        mocker.call("setFormatY", y),
        mocker.call("setCustomFormat", True),
    ])


@pytest.mark.parametrize("x,y", [
    ("invalid", "invalid"),
    (NF.DEGREES, "invalid"),
    ("invalid", NF.DEGREES),
])
def test_numbers_set_format_invalid(overlay, x, y):
    with pytest.raises(CartaValidationFailed) as e:
        overlay.numbers.set_format(x, y)
    assert "Invalid function parameter" in str(e.value)


@pytest.mark.parametrize("val", [True, False])
def test_numbers_set_custom_format(overlay, component_call_action, val):
    numbers_call_action = component_call_action(O.NUMBERS)
    overlay.numbers.set_custom_format(val)
    numbers_call_action.assert_called_with("setCustomFormat", val)


def test_numbers_format(overlay, component_get_value, mocker):
    numbers_get_value = component_get_value(O.NUMBERS)
    numbers_get_value.side_effect = [NF.DEGREES, NF.DEGREES]
    x, y = overlay.numbers.format
    numbers_get_value.assert_has_calls([
        mocker.call("formatTypeX"),
        mocker.call("formatTypeY"),
    ])
    assert isinstance(x, NF)
    assert isinstance(y, NF)


def test_numbers_set_precision(mocker, overlay, component_call_action):
    numbers_call_action = component_call_action(O.NUMBERS)
    overlay.numbers.set_precision(3)
    numbers_call_action.assert_has_calls([
        mocker.call("setPrecision", 3),
        mocker.call("setCustomPrecision", True),
    ])


def test_numbers_set_custom_precision(overlay, component_call_action):
    numbers_call_action = component_call_action(O.NUMBERS)
    overlay.numbers.set_custom_precision(False)
    numbers_call_action.assert_called_with("setCustomPrecision", False)


def test_numbers_precision(overlay, component_get_value):
    numbers_get_value = component_get_value(O.NUMBERS, 3)
    precision = overlay.numbers.precision
    numbers_get_value.assert_called_with("precision")
    assert precision == 3


def test_numbers_custom_precision(overlay, component_get_value):
    numbers_get_value = component_get_value(O.NUMBERS)
    numbers_get_value.side_effect = [True]
    custom_precision = overlay.numbers.custom_precision
    numbers_get_value.assert_called_with("customPrecision")
    assert custom_precision is True


def test_labels_set_label_text(mocker, overlay, component_call_action):
    labels_call_action = component_call_action(O.LABELS)
    overlay.labels.set_label_text("AAA", "BBB")
    labels_call_action.assert_has_calls([
        mocker.call("setCustomLabelX", "AAA"),
        mocker.call("setCustomLabelY", "BBB"),
        mocker.call("setCustomText", True),
    ])


def test_labels_label_text(mocker, overlay, component_get_value):
    labels_get_value = component_get_value(O.LABELS)
    labels_get_value.side_effect = ["AAA", "BBB"]
    label_x, label_y = overlay.labels.label_text
    labels_get_value.assert_has_calls([mocker.call("customLabelX"), mocker.call("customLabelY")])
    assert label_x == "AAA"
    assert label_y == "BBB"


def test_ticks_set_density(mocker, overlay, component_call_action):
    ticks_call_action = component_call_action(O.TICKS)
    overlay.ticks.set_density(2, 3)
    ticks_call_action.assert_has_calls([
        mocker.call("setDensityX", 2),
        mocker.call("setDensityY", 3),
        mocker.call("setCustomDensity", True),
    ])


def test_ticks_set_custom_density(overlay, component_call_action):
    ticks_call_action = component_call_action(O.TICKS)
    overlay.ticks.set_custom_density(False)
    ticks_call_action.assert_called_with("setCustomDensity", False)


def test_ticks_density(mocker, overlay, component_get_value):
    ticks_get_value = component_get_value(O.TICKS)
    ticks_get_value.side_effect = [2, 3]
    density_x, density_y = overlay.ticks.density
    ticks_get_value.assert_has_calls([mocker.call("densityX"), mocker.call("densityY")])
    assert density_x == 2
    assert density_y == 3


def test_ticks_custom_density(overlay, component_get_value):
    ticks_get_value = component_get_value(O.TICKS, True)
    custom_density = overlay.ticks.custom_density
    ticks_get_value.assert_called_with("customDensity")
    assert custom_density is True


def test_ticks_set_draw_on_all_edges(overlay, component_call_action):
    ticks_call_action = component_call_action(O.TICKS)
    overlay.ticks.set_draw_on_all_edges(False)
    ticks_call_action.assert_called_with("setDrawAll", False)


def test_ticks_draw_on_all_edges(overlay, component_get_value):
    ticks_get_value = component_get_value(O.TICKS, True)
    draw_on_all_edges = overlay.ticks.draw_on_all_edges
    ticks_get_value.assert_called_with("drawAll")
    assert draw_on_all_edges is True


def test_ticks_set_minor_length(overlay, component_call_action):
    ticks_call_action = component_call_action(O.TICKS)
    overlay.ticks.set_minor_length(3)
    ticks_call_action.assert_called_with("setLength", 3)


def test_ticks_minor_length(overlay, component_get_value):
    ticks_get_value = component_get_value(O.TICKS, 3)
    minor_length = overlay.ticks.minor_length
    ticks_get_value.assert_called_with("length")
    assert minor_length == 3


def test_ticks_set_major_length(overlay, component_call_action):
    ticks_call_action = component_call_action(O.TICKS)
    overlay.ticks.set_major_length(3)
    ticks_call_action.assert_called_with("setMajorLength", 3)


def test_ticks_major_length(overlay, component_get_value):
    ticks_get_value = component_get_value(O.TICKS, 3)
    major_length = overlay.ticks.major_length
    ticks_get_value.assert_called_with("majorLength")
    assert major_length == 3


def test_colorbar_set_interactive(overlay, component_call_action):
    colorbar_call_action = component_call_action(O.COLORBAR)
    overlay.colorbar.set_interactive(False)
    colorbar_call_action.assert_called_with("setInteractive", False)


def test_colorbar_interactive(overlay, component_get_value):
    colorbar_get_value = component_get_value(O.COLORBAR, True)
    interactive = overlay.colorbar.interactive
    colorbar_get_value.assert_called_with("interactive")
    assert interactive is True


def test_colorbar_set_offset(overlay, component_call_action):
    colorbar_call_action = component_call_action(O.COLORBAR)
    overlay.colorbar.set_offset(3)
    colorbar_call_action.assert_called_with("setOffset", 3)


def test_colorbar_offset(overlay, component_get_value):
    colorbar_get_value = component_get_value(O.COLORBAR, 3)
    offset = overlay.colorbar.offset
    colorbar_get_value.assert_called_with("offset")
    assert offset == 3


def test_colorbar_set_position(overlay, component_call_action):
    colorbar_call_action = component_call_action(O.COLORBAR)
    overlay.colorbar.set_position(CP.BOTTOM)
    colorbar_call_action.assert_called_with("setPosition", CP.BOTTOM)


def test_colorbar_position(overlay, component_get_value):
    colorbar_get_value = component_get_value(O.COLORBAR, "bottom")
    position = overlay.colorbar.position
    colorbar_get_value.assert_called_with("position")
    assert position == CP.BOTTOM


def test_colorbar_set_border_properties(mocker, overlay, component_call_action):
    colorbar_call_action = component_call_action(O.COLORBAR)

    overlay.colorbar.border.set_visible(False)
    overlay.colorbar.border.set_width(3)
    overlay.colorbar.border.set_color(PC.ROSE)
    overlay.colorbar.border.set_custom_color(False)

    colorbar_call_action.assert_has_calls([
        mocker.call("setBorderVisible", False),
        mocker.call("setBorderWidth", 3),
        mocker.call("setBorderColor", PC.ROSE),
        mocker.call("setBorderCustomColor", True),
        mocker.call("setBorderCustomColor", False),
    ])


def test_colorbar_get_border_properties(mocker, overlay, component_get_value):
    colorbar_get_value = component_get_value(O.COLORBAR)
    colorbar_get_value.side_effect = [True, 3, "auto-rose", True]

    visible = overlay.colorbar.border.visible
    width = overlay.colorbar.border.width
    color = overlay.colorbar.border.color
    custom_color = overlay.colorbar.border.custom_color

    colorbar_get_value.assert_has_calls([
        mocker.call("borderVisible", return_path=None),
        mocker.call("borderWidth", return_path=None),
        mocker.call("borderColor", return_path=None),
        mocker.call("borderCustomColor", return_path=None),
    ])

    assert visible is True
    assert width == 3
    assert color == PC.ROSE
    assert custom_color is True


def test_colorbar_set_ticks_properties(mocker, overlay, component_call_action):
    colorbar_call_action = component_call_action(O.COLORBAR)

    overlay.colorbar.ticks.set_visible(False)
    overlay.colorbar.ticks.set_width(3)
    overlay.colorbar.ticks.set_color(PC.ROSE)
    overlay.colorbar.ticks.set_custom_color(False)
    overlay.colorbar.ticks.set_density(3)
    overlay.colorbar.ticks.set_length(3)

    colorbar_call_action.assert_has_calls([
        mocker.call("setTickVisible", False),
        mocker.call("setTickWidth", 3),
        mocker.call("setTickColor", PC.ROSE),
        mocker.call("setTickCustomColor", True),
        mocker.call("setTickCustomColor", False),
        mocker.call("setTickDensity", 3),
        mocker.call("setTickLen", 3),
    ])


def test_colorbar_get_ticks_properties(mocker, overlay, component_get_value):
    colorbar_get_value = component_get_value(O.COLORBAR)
    colorbar_get_value.side_effect = [True, 3, "auto-rose", True, 3, 3]

    visible = overlay.colorbar.ticks.visible
    width = overlay.colorbar.ticks.width
    color = overlay.colorbar.ticks.color
    custom_color = overlay.colorbar.ticks.custom_color
    density = overlay.colorbar.ticks.density
    length = overlay.colorbar.ticks.length

    colorbar_get_value.assert_has_calls([
        mocker.call("tickVisible", return_path=None),
        mocker.call("tickWidth", return_path=None),
        mocker.call("tickColor", return_path=None),
        mocker.call("tickCustomColor", return_path=None),
        mocker.call("tickDensity", return_path=None),
        mocker.call("tickLen", return_path=None),
    ])

    assert visible is True
    assert width == 3
    assert color == PC.ROSE
    assert custom_color is True
    assert density == 3
    assert length == 3


def test_colorbar_set_numbers_properties(mocker, overlay, component_call_action):
    colorbar_call_action = component_call_action(O.COLORBAR)

    overlay.colorbar.numbers.set_visible(False)
    overlay.colorbar.numbers.set_precision(3)
    overlay.colorbar.numbers.set_custom_precision(False)
    overlay.colorbar.numbers.set_color(PC.ROSE)
    overlay.colorbar.numbers.set_custom_color(False)
    overlay.colorbar.numbers.set_custom_text(False)
    overlay.colorbar.numbers.set_font(FF.ARIAL, FS.BOLD)
    overlay.colorbar.numbers.set_rotation(90)

    colorbar_call_action.assert_has_calls([
        mocker.call("setNumberVisible", False),
        mocker.call("setNumberPrecision", 3),
        mocker.call("setNumberCustomPrecision", True),
        mocker.call("setNumberCustomPrecision", False),
        mocker.call("setNumberColor", PC.ROSE),
        mocker.call("setNumberCustomColor", True),
        mocker.call("setNumberCustomColor", False),
        mocker.call("setNumberCustomText", False),
        mocker.call("setNumberFont", 9),
        mocker.call("setNumberRotation", 90),
    ])


def test_colorbar_get_numbers_properties(mocker, overlay, component_get_value):
    colorbar_get_value = component_get_value(O.COLORBAR)
    colorbar_get_value.side_effect = [True, 3, True, "auto-rose", True, True, 9, 90]

    visible = overlay.colorbar.numbers.visible
    precision = overlay.colorbar.numbers.precision
    custom_precision = overlay.colorbar.numbers.custom_precision
    color = overlay.colorbar.numbers.color
    custom_color = overlay.colorbar.numbers.custom_color
    custom_text = overlay.colorbar.numbers.custom_text
    family, style = overlay.colorbar.numbers.font
    rotation = overlay.colorbar.numbers.rotation

    colorbar_get_value.assert_has_calls([
        mocker.call("numberVisible", return_path=None),
        mocker.call("numberPrecision", return_path=None),
        mocker.call("numberCustomPrecision", return_path=None),
        mocker.call("numberColor", return_path=None),
        mocker.call("numberCustomColor", return_path=None),
        mocker.call("numberCustomText", return_path=None),
        mocker.call("numberFont", return_path=None),
        mocker.call("numberRotation", return_path=None),
    ])

    assert visible is True
    assert precision == 3
    assert custom_precision is True
    assert color == PC.ROSE
    assert custom_color is True
    assert custom_text is True
    assert family == FF.ARIAL
    assert style == FS.BOLD
    assert rotation == 90


def test_colorbar_set_label_properties(mocker, overlay, component_call_action):
    colorbar_call_action = component_call_action(O.COLORBAR)

    overlay.colorbar.label.set_visible(False)
    overlay.colorbar.label.set_color(PC.ROSE)
    overlay.colorbar.label.set_custom_color(False)
    overlay.colorbar.label.set_custom_text(False)
    overlay.colorbar.label.set_font(FF.ARIAL, FS.BOLD)
    overlay.colorbar.label.set_rotation(90)

    colorbar_call_action.assert_has_calls([
        mocker.call("setLabelVisible", False),
        mocker.call("setLabelColor", PC.ROSE),
        mocker.call("setLabelCustomColor", True),
        mocker.call("setLabelCustomColor", False),
        mocker.call("setLabelCustomText", False),
        mocker.call("setLabelFont", 9),
        mocker.call("setLabelRotation", 90),
    ])


def test_colorbar_get_label_properties(mocker, overlay, component_get_value):
    colorbar_get_value = component_get_value(O.COLORBAR)
    colorbar_get_value.side_effect = [True, "auto-rose", True, True, 9, 90]

    visible = overlay.colorbar.label.visible
    color = overlay.colorbar.label.color
    custom_color = overlay.colorbar.label.custom_color
    custom_text = overlay.colorbar.label.custom_text
    family, style = overlay.colorbar.label.font
    rotation = overlay.colorbar.label.rotation

    colorbar_get_value.assert_has_calls([
        mocker.call("labelVisible", return_path=None),
        mocker.call("labelColor", return_path=None),
        mocker.call("labelCustomColor", return_path=None),
        mocker.call("labelCustomText", return_path=None),
        mocker.call("labelFont", return_path=None),
        mocker.call("labelRotation", return_path=None),
    ])

    assert visible is True
    assert color == PC.ROSE
    assert custom_color is True
    assert custom_text is True
    assert family == FF.ARIAL
    assert style == FS.BOLD
    assert rotation == 90


def test_colorbar_set_gradient_properties(mocker, overlay, component_call_action):
    colorbar_call_action = component_call_action(O.COLORBAR)
    overlay.colorbar.gradient.set_visible(False)
    colorbar_call_action.assert_has_calls([
        mocker.call("setGradientVisible", False),
    ])


def test_colorbar_get_gradient_properties(mocker, overlay, component_get_value):
    colorbar_get_value = component_get_value(O.COLORBAR)
    colorbar_get_value.side_effect = [True]
    visible = overlay.colorbar.gradient.visible
    colorbar_get_value.assert_has_calls([
        mocker.call("gradientVisible", return_path=None),
    ])
    assert visible is True


def test_beam_set_position(mocker, overlay, component_call_action):
    beam_call_action = component_call_action(O.BEAM)
    overlay.beam.set_position(2, 3)
    beam_call_action.assert_has_calls([
        mocker.call("setShiftX", 2),
        mocker.call("setShiftY", 3),
    ])


def test_beam_position(mocker, overlay, component_get_value):
    beam_get_value = component_get_value(O.BEAM)
    beam_get_value.side_effect = [2, 3]
    pos_x, pos_y = overlay.beam.position
    beam_get_value.assert_has_calls([mocker.call("shiftX"), mocker.call("shiftY")])
    assert pos_x == 2
    assert pos_y == 3


def test_beam_set_type(overlay, component_call_action):
    beam_call_action = component_call_action(O.BEAM)
    overlay.beam.set_type(BT.SOLID)
    beam_call_action.assert_called_with("setType", BT.SOLID)


def test_beam_type(overlay, component_get_value):
    beam_get_value = component_get_value(O.BEAM, "solid")
    beam_type = overlay.beam.type
    beam_get_value.assert_called_with("type")
    assert beam_type == BT.SOLID
