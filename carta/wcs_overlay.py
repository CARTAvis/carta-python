"""This module contains functionality for interacting with the WCS overlay. The classes in this module should not be instantiated directly. When a session object is created, an overlay object is automatically created as a property, and overlay component objects are created as its subproperties."""

import re

from .util import BasePathMixin
from .constants import CoordinateSystem, LabelType, BeamType, PaletteColor, Overlay, NumberFormat, FontFamily, FontStyle, ColorbarPosition
from .validation import validate, String, Number, Constant, Boolean, all_optional


class WCSOverlay(BasePathMixin):
    """Utility object for collecting session functions related to the WCS overlay. Most functions are additionally grouped in subcomponents, which can be accessed directly by name or looked up in a mapping by `carta.constants.Overlay` enum.

    Parameters
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay object.

    Attributes
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this overlay object.
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay object.
    global\\_ : :obj:`carta.wcs_overlay.Global` object
        The global settings subcomponent.
    title : :obj:`carta.wcs_overlay.Title` object
        The title settings subcomponent.
    grid : :obj:`carta.wcs_overlay.Grid` object
        The grid settings subcomponent.
    border : :obj:`carta.wcs_overlay.Border` object
        The border settings subcomponent.
    ticks : :obj:`carta.wcs_overlay.Ticks` object
        The ticks settings subcomponent.
    axes : :obj:`carta.wcs_overlay.Axes` object
        The axes settings subcomponent.
    numbers : :obj:`carta.wcs_overlay.Numbers` object
        The numbers settings subcomponent.
    labels : :obj:`carta.wcs_overlay.Labels` object
        The labels settings subcomponent.
    colorbar : :obj:`carta.wcs_overlay.Colorbar` object
        The colorbar settings subcomponent.
    beam : :obj:`carta.wcs_overlay.Beam` object
        The beam settings subcomponent.
    """

    def __init__(self, session):
        self.session = session
        self._base_path = "overlayStore"

        self._components = {}
        for component in Overlay:
            comp = OverlayComponent.CLASS[component](self)
            self._components[component] = comp
            name = component.name.lower()
            # This is a reserved word.
            if name == "global":
                name += "_"
            setattr(self, f"{name}", comp)

    @validate(Constant(Overlay))
    def get(self, component):
        """Access an overlay component subobject by name.

        Parameters
        ----------
        component : {0}
            The component to access.

        Returns
        -------
        A member of :obj:`carta.wcs_overlay.OverlayComponent`
            The overlay component object.
        """
        return self._components[component]

    @validate(Constant(PaletteColor))
    def palette_to_rgb(self, color):
        """Convert a palette colour to RGB.

        The RGB value depends on whether the session is using the light theme or the dark theme.

        Parameters
        ----------
        color : {0}
            The colour to convert.

        Returns
        -------
        string
            The RGB value of the palette colour in the session's current theme, as a 6-digit hexadecimal with a leading ``#``.
        """
        color = PaletteColor(color)
        if self.session.get_value("darkTheme"):
            return color.rgb_dark
        return color.rgb_light

    @validate(Number(), Number())
    def set_view_area(self, width, height):
        """Set the dimensions of the view area.

        Parameters
        ----------
        width : {0}
            The new width, in pixels, divided by the device pixel ratio.
        height : {1}
            The new height, in pixels, divided by the device pixel ratio.
        """
        self.call_action("setViewDimension", width, height)

    def toggle_labels(self):
        """Toggle the overlay labels."""
        self.call_action("toggleLabels")


class OverlayComponent(BasePathMixin):
    """A single WCS overlay component.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """

    CLASS = {}
    """Mapping of :obj:`carta.constants.Overlay` enums to component classes. This mapping is used to select the appropriate subclass when an overlay component object is constructed in the wrapper."""

    def __init_subclass__(cls, **kwargs):
        """Automatically register subclasses in mapping from overlay component enums to classes."""
        super().__init_subclass__(**kwargs)

        OverlayComponent.CLASS[cls.COMPONENT] = cls

    def __init__(self, overlay):
        self._base_path = f"overlayStore.{self.COMPONENT}"
        self.session = overlay.session


class HasColor:
    """Components which inherit this class have a palette color setting."""

    @property
    def color(self):
        """The color of this component.

        Returns
        -------
        a member of :obj:`carta.constants.color.PaletteColor`
            The color.
        """
        return PaletteColor(self.get_value("color"))

    @validate(Constant(PaletteColor))
    def set_color(self, color):
        """Set the color of this component.

        Parameters
        ----------
        color : {0}
            The color.
        """
        self.call_action("setColor", color)


class HasCustomColor(HasColor):
    """Components which inherit this class have a palette color setting and a custom color flag."""

    @property
    def custom_color(self):
        """Whether a custom color is applied to this component.

        Returns
        -------
        boolean
            Whether a custom color is applied.
        """
        return self.get_value("customColor")

    @validate(Constant(PaletteColor))
    def set_color(self, color):
        """Set the color of this component.

        This automatically enables the use of a custom color.

        Parameters
        ----------
        color : {0}
            The color.
        """
        self.call_action("setColor", color)
        self.set_custom_color(True)

    @validate(Boolean())
    def set_custom_color(self, state):
        """Set whether a custom color should be applied to this component.

        Parameters
        ----------
        state : {0}
            Whether a custom color should be applied to this component. By default the global color is applied.
        """
        self.call_action("setCustomColor", state)


class HasCustomText:
    """Components which inherit this class have a custom text flag. Different components have different text properties, which are set separately."""

    @property
    def custom_text(self):
        """Whether custom text is applied to this component.

        Returns
        -------
        boolean
            Whether custom text is applied.
        """
        return self.get_value("customText")

    @validate(Boolean())
    def set_custom_text(self, state):
        """Set whether custom text should be applied to this component.

        Parameters
        ----------
        state : {0}
            Whether custom text should be applied to this component. By default the text is generated automatically.
        """
        self.call_action("setCustomText", state)


class HasFont:
    """Components which inherit this class have a font setting."""

    @property
    def font(self):
        """The font of this component.

        Returns
        -------
        member of :obj:`carta.constants.FontFamily`
            The font family.
        member of :obj:`carta.constants.FontStyle`
            The font style.
        """
        font_family, font_style = divmod(self.get_value("font"), 4)
        return FontFamily(font_family), FontStyle(font_style)

    @validate(*all_optional(Constant(FontFamily), Constant(FontStyle)))
    def set_font(self, font_family, font_style):
        """Set the font of this component.

        Parameters
        ----------
        font_family : {0}
            The font family.
        font_style : {1}
            The font style.
        """
        if font_family is None or font_style is None:
            current_family, current_style = self.font
        if font_family is None:
            font_family = current_family
        if font_style is None:
            font_style = current_style
        font_id = 4 * font_family + font_style
        self.call_action("setFont", font_id)


class HasVisibility:
    """Components which inherit this class have a visibility setting, including ``show`` and ``hide`` aliases."""

    @property
    def visible(self):
        """The visibility of this component.

        Returns
        -------
        boolean
            Whether this component is visible.
        """
        return self.get_value("visible")

    @validate(Boolean())
    def set_visible(self, state):
        """Set the visibility of this component.

        Parameters
        ----------
        visible : {0}
            Whether this component should be visible.
        """
        self.call_action("setVisible", state)

    def show(self):
        """Show this component."""
        self.set_visible(True)

    def hide(self):
        """Hide this component."""
        self.set_visible(False)


class HasWidth:
    """Components which inherit this class have a width setting."""

    @property
    def width(self):
        """The width of this component.

        Returns
        -------
        boolean
            The width.
        """
        return self.get_value("width")

    @validate(Number.POSITIVE)
    def set_width(self, width):
        """Set the width of this component.

        Parameters
        ----------
        width : {0}
            The width.
        """
        self.call_action("setWidth", width)


class HasRotation:
    """Components which inherit this class have a rotation setting."""

    @property
    def rotation(self):
        """The rotation of this component.

        Returns
        -------
        number
            The rotation in degrees.
        """
        return self.get_value("rotation")

    @validate(Number(min=-90, max=90, step=90))
    def set_rotation(self, rotation):
        """Set the rotation of this component.

        Parameters
        ----------
        rotation: {0}
            The rotation in degrees.
        """
        self.call_action("setRotation", rotation)


class HasCustomPrecision:
    """Components which inherit this class have a precision setting and a custom precision flag."""

    @property
    def precision(self):
        """The precision of this component.

        Returns
        -------
        number
            The precision.
        """
        return self.get_value("precision")

    @property
    def custom_precision(self):
        """Whether a custom precision is applied to this component.

        Returns
        -------
        boolean
            Whether a custom precision is applied.
        """
        return self.get_value("customPrecision")

    @validate(Number(min=0))
    def set_precision(self, precision):
        """Set the precision of this component.

        This also automatically enables the custom precision.

        Parameters
        ----------
        precision : {0}
            The precision.
        """
        self.call_action("setPrecision", precision)
        self.set_custom_precision(True)

    @validate(Boolean())
    def set_custom_precision(self, state):
        """Set whether a custom precision should be applied to this component.

        Parameters
        ----------
        state
            Whether a custom precision should be applied.
        """
        self.call_action("setCustomPrecision", state)


class Global(HasColor, OverlayComponent):
    """The global WCS overlay configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.GLOBAL

    @property
    def tolerance(self):
        """The tolerance.

        Returns
        -------
        number
            The tolerance, as a percentage.
        """
        return self.get_value("tolerance")

    @property
    def coordinate_system(self):
        """The coordinate system.

        Returns
        -------
        a member of :obj:`carta.constants.CoordinateSystem`
            The coordinate system.
        """
        return CoordinateSystem(self.get_value("system"))

    @property
    def labelling(self):
        """The labelling (internal or external).

        Returns
        -------
        a member of :obj:`carta.constants.LabelType`
            The type of labelling.
        """
        return LabelType(self.get_value("labelType"))

    @validate(Number.PERCENTAGE)
    def set_tolerance(self, tolerance):
        """Set the tolerance.

        Parameters
        ----------
        tolerance : {0}
            The tolerance, as a percentage.
        """
        self.call_action("setTolerance", tolerance)

    @validate(Constant(CoordinateSystem))
    def set_coordinate_system(self, coordinate_system):
        """Set the coordinate system.

        Parameters
        ----------
        coordinate_system : {0}
            The coordinate system.
        """
        self.call_action("setSystem", coordinate_system)

    @validate(Constant(LabelType))
    def set_labelling(self, labelling):
        """Set the type of labelling (internal or external).

        Parameters
        ----------
        labelling : {0}
            The type of labelling.
        """
        self.call_action("setLabelType", labelling)


class Title(HasCustomColor, HasCustomText, HasFont, HasVisibility, OverlayComponent):
    """The WCS overlay title configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.TITLE


class Grid(HasCustomColor, HasVisibility, HasWidth, OverlayComponent):
    """The WCS overlay grid configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.GRID

    @property
    def gap(self):
        """The gap.

        Returns
        -------
        number
            The X gap.
        number
            The Y gap.
        """
        return self.get_value("gapX"), self.get_value("gapY")

    @property
    def custom_gap(self):
        """Whether a custom gap is applied to this component.

        Returns
        -------
        boolean
            Whether a custom gap is applied.
        """
        return self.get_value("customGap")

    @validate(*all_optional(Number.POSITIVE, Number.POSITIVE))
    def set_gap(self, gap_x, gap_y):
        """Set the gap.

        This also automatically enables the custom gap.

        Parameters
        ----------
        gap_x : {0}
            The X gap.
        gap_y : {1}
            The Y gap.
        """
        if gap_x is not None:
            self.call_action("setGapX", gap_x)
        if gap_y is not None:
            self.call_action("setGapY", gap_y)
        if gap_x is not None or gap_y is not None:
            self.set_custom_gap(True)

    @validate(Boolean())
    def set_custom_gap(self, state):
        """Set whether a custom gap should be applied to this component.

        Parameters
        ----------
        state : {0}
            Whether a custom gap should be applied.
        """
        self.call_action("setCustomGap", state)


class Border(HasCustomColor, HasVisibility, HasWidth, OverlayComponent):
    """The WCS overlay border configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.BORDER


class Axes(HasCustomColor, HasVisibility, HasWidth, OverlayComponent):
    """The WCS overlay axes configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.AXES


class Numbers(HasCustomColor, HasFont, HasVisibility, HasCustomPrecision, OverlayComponent):
    """The WCS overlay numbers configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.NUMBERS

    @property
    def format(self):
        """The X and Y number format.

        If the image has no WCS information, both the X and Y formats will be ``None``.

        If a custom number format is not set, this returns the default format set by the coordinate system.

        Returns
        -------
        a member of :obj:`carta.constants.NumberFormat` or ``None``
            The X format.
        a member of :obj:`carta.constants.NumberFormat` or ``None``
            The Y format.
        """
        format_x = self.get_value("formatTypeX")
        format_y = self.get_value("formatTypeY")
        return NumberFormat(format_x), NumberFormat(format_y)

    @property
    def custom_format(self):
        """Whether a custom format is applied to the numbers.

        Returns
        -------
        boolean
            Whether a custom format is applied.
        """
        return self.get_value("customFormat")

    @validate(*all_optional(Constant(NumberFormat), Constant(NumberFormat)))
    def set_format(self, format_x=None, format_y=None):
        """Set the X and/or Y number format.

        This also automatically enables the custom number format, if either of the format parameters is set. If only one format is provided, the other will be set to the last previously used custom format, or to the system default.

        Parameters
        ----------
        format_x : {0}
            The X format.
        format_y : {1}
            The Y format.
        """
        if format_x is not None:
            self.call_action("setFormatX", format_x)
        if format_y is not None:
            self.call_action("setFormatY", format_y)
        if format_x is not None or format_y is not None:
            self.set_custom_format(True)

    @validate(Boolean())
    def set_custom_format(self, state):
        """Set whether a custom format should be applied to the numbers.

        Parameters
        ----------
        state : {0}
            Whether a custom format should be applied.
        """
        self.call_action("setCustomFormat", state)


class Labels(HasCustomColor, HasCustomText, HasFont, HasVisibility, OverlayComponent):
    """The WCS overlay labels configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.LABELS

    @property
    def label_text(self):
        """The label text.

        If a custom label text has not been set, these values will be blank.

        Returns
        -------
        string
            The X label text.
        string
            The Y label text.
        """
        return self.get_value("customLabelX"), self.get_value("customLabelY")

    @validate(*all_optional(String(), String()))
    def set_label_text(self, label_x=None, label_y=None):
        """Set the label text.

        This also automatically enables the custom label text.

        Parameters
        ----------
        label_x : {0}
            The X-axis label text.
        label_y : {1}
            The Y-axis label text.
        """
        if label_x is not None:
            self.call_action("setCustomLabelX", label_x)
        if label_y is not None:
            self.call_action("setCustomLabelY", label_y)
        if label_x is not None or label_y is not None:
            self.call_action("setCustomText", True)


class Ticks(HasCustomColor, HasVisibility, HasWidth, OverlayComponent):
    """The WCS overlay ticks configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.TICKS

    @property
    def density(self):
        """The density.

        Returns
        -------
        number
            The X density.
        number
            The Y density.
        """
        return self.get_value("densityX"), self.get_value("densityY")

    @property
    def custom_density(self):
        """Whether a custom density is applied to the ticks.

        Returns
        -------
        boolean
            Whether a custom density is applied.
        """
        return self.get_value("customDensity")

    @property
    def draw_on_all_edges(self):
        """Whether the ticks are drawn on all edges.

        Returns
        -------
        boolean
            Whether the ticks are drawn on all edges.
        """
        return self.get_value("drawAll")

    @property
    def minor_length(self):
        """The minor tick length.

        Returns
        -------
        number
            The minor length, as a percentage.
        """
        return self.get_value("length")

    @property
    def major_length(self):
        """The major tick length.

        Returns
        -------
        number
            The major length, as a percentage.
        """
        return self.get_value("majorLength")

    @validate(*all_optional(Number.POSITIVE, Number.POSITIVE))
    def set_density(self, density_x=None, density_y=None):
        """Set the density.

        This also automatically enables the custom density.
        """
        if density_x is not None:
            self.call_action("setDensityX", density_x)
        if density_y is not None:
            self.call_action("setDensityY", density_y)
        if density_x is not None or density_y is not None:
            self.set_custom_density(True)

    @validate(Boolean())
    def set_custom_density(self, state):
        """Set whether a custom density should be applied to the ticks.

        Parameters
        ----------
        state : {0}
            Whether a custom density should be applied.
        """
        self.call_action("setCustomDensity", state)

    @validate(Boolean())
    def set_draw_on_all_edges(self, state):
        """Set whether the ticks should be drawn on all edges.

        Parameters
        ----------
        state : {0}
            Whether the ticks should be drawn on all edges.
        """
        self.call_action("setDrawAll", state)

    @validate(Number.PERCENTAGE)
    def set_minor_length(self, length):
        """Set the minor tick length.

        Parameters
        ----------
        length : {0}
            The minor tick length, as a percentage.
        """
        self.call_action("setLength", length)

    @validate(Number.PERCENTAGE)
    def set_major_length(self, length):
        """Set the major tick length.

        Parameters
        ----------
        length : {0}
            The major tick length, as a percentage.
        """
        self.call_action("setMajorLength", length)


class ColorbarComponent:
    """Base class for components of the WCS overlay colorbar.

    Attributes
    ----------
    colorbar : :obj:`carta.wcs_overlay.Colorbar` object
        The colorbar object associated with this colorbar component.
    """

    def __init__(self, colorbar):
        self.colorbar = colorbar

    def call_action(self, path, *args, **kwargs):
        """Convenience wrapper for the colorbar object's generic action method.

        This method calls :obj:`carta.wcs_overlay.Colorbar.call_action` after inserting this subcomponent's name prefix into the path parameter. It assumes that the action name starts with a lowercase word, and that the prefix should be inserted after this word with a leading capital letter.

        Parameters
        ----------
        path : string
            The path to an action relative to the colorbar object's store, with this subcomponent's name prefix omitted.
        *args
            A variable-length list of parameters. These are passed unmodified to the colorbar method.
        **kwargs
            Arbitrary keyword parameters. These are passed unmodified to the colorbar method.

        Returns
        -------
        object or None
            The unmodified return value of the colorbar method.
        """
        path = re.sub(r"(?:.*\.)*(.*?)([A-Z].*)", rf"\1{self.PREFIX.title()}\2", path)
        self.colorbar.call_action(path, *args, **kwargs)

    def get_value(self, path, return_path=None):
        """Convenience wrapper for the colorbar object's generic method for retrieving attribute values.

        This method calls :obj:`carta.wcs_overlay.Colorbar.get_value` after inserting this subcomponent's name prefix into the path parameter. It assumes that the attribute name starts with a lowercase letter, that the prefix should be inserted before it, and that the first letter of the original name should be capitalised.

        Parameters
        ----------
        path : string
            The path to an attribute relative to the colorbar object's store, with this subcomponent's name prefix omitted.
        return_path : string, optional
            Specifies a subobject of the attribute value which should be returned instead of the whole object.

        Returns
        -------
        object
            The unmodified return value of the colorbar method.
        """
        def rewrite(m):
            before, first, rest = m.groups()
            return f"{before}{self.PREFIX}{first.upper()}{rest}"

        path = re.sub(r"((?:.*\.)?.*?)(.)(.*)", rewrite, path)
        return self.colorbar.get_value(path, return_path=return_path)


class ColorbarBorder(HasVisibility, HasWidth, HasCustomColor, ColorbarComponent):
    """The WCS overlay colorbar border configuration.

    Attributes
    ----------
    colorbar : :obj:`carta.wcs_overlay.Colorbar` object
        The colorbar object associated with this colorbar component.
    """
    PREFIX = "border"


class ColorbarTicks(HasVisibility, HasWidth, HasCustomColor, ColorbarComponent):
    """The WCS overlay colorbar ticks configuration.

    Attributes
    ----------
    colorbar : :obj:`carta.wcs_overlay.Colorbar` object
        The colorbar object associated with this colorbar component.
    """
    PREFIX = "tick"

    @property
    def density(self):
        """The colorbar ticks density.

        Returns
        -------
        number
            The density.
        """
        return self.get_value("density")

    @property
    def length(self):
        """The colorbar ticks length.

        Returns
        -------
        number
            The length.
        """
        return self.get_value("len")

    @validate(Number.POSITIVE)
    def set_density(self, density):
        """Set the colorbar ticks density.

        Parameters
        ----------
        density : {0}
            The density.
        """
        self.call_action("setDensity", density)

    @validate(Number.POSITIVE)
    def set_length(self, length):
        """Set the colorbar ticks length.

        Parameters
        ----------
        length : {0}
            The length.
        """
        self.call_action("setLen", length)


class ColorbarNumbers(HasVisibility, HasCustomPrecision, HasCustomColor, HasFont, HasRotation, ColorbarComponent):
    """The WCS overlay colorbar numbers configuration.

    Attributes
    ----------
    colorbar : :obj:`carta.wcs_overlay.Colorbar` object
        The colorbar object associated with this colorbar component.
    """
    PREFIX = "number"


class ColorbarLabel(HasVisibility, HasCustomColor, HasCustomText, HasFont, HasRotation, ColorbarComponent):
    """The WCS overlay colorbar label configuration.

    Attributes
    ----------
    colorbar : :obj:`carta.wcs_overlay.Colorbar` object
        The colorbar object associated with this colorbar component.
    """
    PREFIX = "label"


class ColorbarGradient(HasVisibility, ColorbarComponent):
    """The WCS overlay colorbar gradient configuration.

    Attributes
    ----------
    colorbar : :obj:`carta.wcs_overlay.Colorbar` object
        The colorbar object associated with this colorbar component.
    """
    PREFIX = "gradient"


class Colorbar(HasCustomColor, HasVisibility, HasWidth, OverlayComponent):
    """The WCS overlay colorbar configuration.

    This component has subcomponents which are configured separately through properties on this object.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    border : :obj:`carta.wcs_overlay.ColorbarBorder` object
        The border subcomponent.
    ticks : :obj:`carta.wcs_overlay.ColorbarTicks` object
        The ticks subcomponent.
    numbers : :obj:`carta.wcs_overlay.ColorbarNumbers` object
        The numbers subcomponent.
    label : :obj:`carta.wcs_overlay.ColorbarLabel` object
        The label subcomponent.
    gradient : :obj:`carta.wcs_overlay.ColorbarGradient` object
        The gradient subcomponent.
    """
    COMPONENT = Overlay.COLORBAR

    def __init__(self, overlay):
        super().__init__(overlay)
        self.border = ColorbarBorder(self)
        self.ticks = ColorbarTicks(self)
        self.numbers = ColorbarNumbers(self)
        self.label = ColorbarLabel(self)
        self.gradient = ColorbarGradient(self)

    @property
    def interactive(self):
        """Whether the colorbar is interactive.

        Returns
        -------
        boolean
            Whether the colorbar is interactive.
        """
        return self.get_value("interactive")

    @property
    def offset(self):
        """The colorbar offset.

        Returns
        -------
        number
            The offset, in pixels.
        """
        return self.get_value("offset")

    @property
    def position(self):
        """The colorbar position.

        Returns
        -------
        a member of :obj:`carta.constants.ColorbarPosition`
            The position.
        """
        return ColorbarPosition(self.get_value("position"))

    @validate(Boolean())
    def set_interactive(self, state):
        """Set whether the colorbar should be interactive.

        Parameters
        ----------
        state : {0}
            Whether the colorbar should be interactive.
        """
        self.call_action("setInteractive", state)

    @validate(Number(min=0))
    def set_offset(self, offset):
        """Set the colorbar offset.

        Parameters
        ----------
        offset : {0}
            The offset, in pixels.
        """
        self.call_action("setOffset", offset)

    @validate(Constant(ColorbarPosition))
    def set_position(self, position):
        """Set the colorbar position.

        Parameters
        ----------
        offset : {0}
            The position.
        """
        self.call_action("setPosition", position)


class Beam(HasColor, HasVisibility, HasWidth, OverlayComponent):
    """The WCS overlay beam configuration.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this overlay component.
    """
    COMPONENT = Overlay.BEAM

    @property
    def position(self):
        """The beam position.

        Returns
        -------
        number
            The X beam position, in pixels.
        number
            The Y beam position, in pixels.
        """
        return self.get_value("shiftX"), self.get_value("shiftY")

    @property
    def type(self):
        """The beam type.

        Returns
        -------
        a member of :obj:`carta.constants.BeamType`
            The beam type.
        """
        return BeamType(self.get_value("type"))

    @validate(*all_optional(Number(), Number()))
    def set_position(self, position_x=None, position_y=None):
        """Set the beam position.

        Parameters
        ----------
        position_x : {0}
            The X position, in pixels.
        position_y : {1}
            The Y position, in pixels.
        """
        if position_x is not None:
            self.call_action("setShiftX", position_x)
        if position_y is not None:
            self.call_action("setShiftY", position_y)

    @validate(Constant(BeamType))
    def set_type(self, beam_type):
        """Set the beam type.

        Parameters
        ----------
        beam_type : {0}
            The beam type.
        """
        self.call_action("setType", beam_type)
