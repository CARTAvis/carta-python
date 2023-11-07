"""This module contains functionality for interacting with the WCS overlay. The class in this module should not be instantiated directly. When a session object is created, an overlay object is automatically created as a property."""

from .util import logger, BasePathMixin
from .constants import CoordinateSystem, LabelType, BeamType, PaletteColor, Overlay, NumberFormat
from .validation import validate, String, Number, Constant, Boolean, NoneOr, OneOf


class WCSOverlay(BasePathMixin):
    """Utility object for collecting session functions related to the WCS overlay.

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
    """

    class Component(BasePathMixin):
        """Internal helper class for simplifying component paths."""

        def __init__(self, component):
            self._base_path = f"overlayStore.{component}"

    def __init__(self, session):
        self.session = session
        self._base_path = "overlayStore"

        self._components = {}
        for component in Overlay:
            component_obj = WCSOverlay.Component(component)
            self._components[component] = component_obj
            setattr(self, f"_{component.name.lower()}", component_obj)

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
        if self.get_value("darkTheme"):
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

    @validate(Constant(CoordinateSystem))
    def set_coordinate_system(self, system=CoordinateSystem.AUTO):
        """Set the coordinate system.

        Parameters
        ----------
        system : {0}
            The coordinate system.
        """
        self._global.call_action("setSystem", system)

    @property
    def coordinate_system(self):
        """Get the coordinate system.

        Returns
        ----------
        :obj:`carta.constants.CoordinateSystem`
            The coordinate system.
        """
        return CoordinateSystem(self._global.get_value("system"))

    @validate(Constant(LabelType))
    def set_label_type(self, label_type):
        """Set the label type.

        Parameters
        ----------
        label_type : {0}
            The label type.
        """
        self._global.call_action("setLabelType", label_type)

    @validate(NoneOr(String()), NoneOr(String()), NoneOr(String()))
    def set_text(self, title=None, label_x=None, label_y=None):
        """Set custom title and/or the axis label text.

        Parameters
        ----------
        title : {0}
            The title text.
        label_x : {1}
            The X-axis text.
        label_y : {2}
            The Y-axis text.
        """
        if title is not None:
            self._title.call_action("setCustomTitleString", title)
            self._title.call_action("setCustomText", True)
        if label_x is not None:
            self._labels.call_action("setCustomLabelX", label_x)
        if label_y is not None:
            self._labels.call_action("setCustomLabelX", label_y)
        if label_x is not None or label_y is not None:
            self._labels.call_action("setCustomText", True)

    def clear_text(self):
        """Clear all custom title and axis text."""
        self._title.call_action("setCustomText", False)
        self._labels.call_action("setCustomText", False)

    @validate(OneOf(Overlay.TITLE, Overlay.NUMBERS, Overlay.LABELS), NoneOr(String()), NoneOr(Number()))
    def set_font(self, component, font=None, font_size=None):
        """Set the font and/or font size of an overlay component.

        TODO: can we get the allowed font names from somewhere?

        Parameters
        ----------
        component : {0}
            The overlay component.
        font : {1}
            The font name.
        font_size : {2}
            The font size.
        """
        if font is not None:
            self._components[component].call_action("setFont", font)
        if font_size is not None:
            self._components[component].call_action("setFontSize", font_size)

    @validate(NoneOr(Constant(NumberFormat)), NoneOr(Constant(NumberFormat)))
    def set_custom_number_format(self, x_format=None, y_format=None):
        """Set a custom X and Y number format.

        Parameters
        ----------
        x_format : {0}
            The X format. If this is unset, the last custom X format to be set will be restored.
        x_format : {1}
            The Y format. If this is unset, the last custom Y format to be set will be restored.
        """
        if x_format is not None:
            self._numbers.call_action("setFormatX", x_format)
        if y_format is not None:
            self._numbers.call_action("setFormatY", y_format)
        self._numbers.call_action("setCustomFormat", True)

    def clear_custom_number_format(self):
        """Disable the custom X and Y number format."""
        self._numbers.call_action("setCustomFormat", False)

    @property
    def number_format(self):
        """Return the current X and Y number formats, and whether they are a custom setting.

        If the image has no WCS information, both the X and Y formats will be ``None``.

        If a custom number format is not set, the format is derived from the coordinate system.

        Returns
        -------
        tuple (a member of :obj:`carta.constants.NumberFormat` or ``None``, a member of :obj:`carta.constants.NumberFormat` or ``None``, boolean)
            A tuple containing the X format, the Y format, and whether a custom format is set.
        """
        number_format_x = self._numbers.get_value("formatTypeX")
        number_format_y = self._numbers.get_value("formatTypeY")
        custom_format = self._numbers.get_value("customFormat")
        return NumberFormat(number_format_x), NumberFormat(number_format_y), custom_format

    @validate(NoneOr(Constant(BeamType)), NoneOr(Number()), NoneOr(Number()), NoneOr(Number()))
    def set_beam(self, beam_type=None, width=None, shift_x=None, shift_y=None):
        """Set the beam properties.

        Parameters
        ----------
        beam_type : {0}
            The beam type.
        width : {1}
            The beam width.
        shift_x : {2}
            The X position.
        shift_y : {3}
            The Y position.
        """
        if beam_type is not None:
            self._beam.call_action("setBeamType", beam_type)
        if width is not None:
            self._beam.call_action("setWidth", width)
        if shift_x is not None:
            self._beam.call_action("setShiftX", shift_x)
        if shift_y is not None:
            self._beam.call_action("setShiftY", shift_y)

    @validate(Constant(PaletteColor), Constant(Overlay))
    def set_color(self, color, component=Overlay.GLOBAL):
        """Set the custom color on an overlay component, or the global color.

        Parameters
        ----------
        color : {0}
            The color.
        component : {1}
            The overlay component.
        """
        self._components[component].call_action("setColor", color)
        if component not in (Overlay.GLOBAL, Overlay.BEAM):
            self._components[component].call_action("setCustomColor", True)

    @validate(Constant(Overlay, exclude=(Overlay.GLOBAL,)))
    def clear_color(self, component):
        """Clear the custom color from an overlay component.

        Parameters
        ----------
        component : {0}
            The overlay component.
        """
        if component == Overlay.BEAM:
            logger.warning("Cannot clear the color from the beam component. A color must be set on this component explicitly.")
            return

        self._components[component].call_action("setCustomColor", False)

    @validate(Constant(Overlay))
    def color(self, component):
        """The color of an overlay component.

        If called on the global overlay options, this function returns the global (default) overlay color. For any single overlay component other than the beam, it returns its custom color if a custom color is enabled, otherwise None. For the beam it returns the beam color.

        Parameters
        ----------
        component : {0}
            The overlay component.

        Returns
        -------
        A member of :obj:`carta.constants.PaletteColor` or None
            The color of the component or None if no custom color is set on the component.
        """
        if component in (Overlay.GLOBAL, Overlay.BEAM) or self._components[component].get_value("customColor"):
            return PaletteColor(self._components[component].get_value("color"))

    @validate(Number(min=0, interval=Number.EXCLUDE), OneOf(Overlay.GRID, Overlay.BORDER, Overlay.TICKS, Overlay.AXES, Overlay.COLORBAR))
    def set_width(self, width, component):
        """Set the line width of an overlay component.

        Parameters
        ----------
        component : {0}
            The overlay component.
        """
        self._components[component].call_action("setWidth", width)

    @validate(OneOf(Overlay.GRID, Overlay.BORDER, Overlay.TICKS, Overlay.AXES, Overlay.COLORBAR))
    def width(self, component):
        """The line width of an overlay component.

        Parameters
        ----------
        component : {0}
            The overlay component.

        Returns
        ----------
        number
            The line width of the component.
        """
        return self._components[component].get_value("width")

    @validate(Constant(Overlay, exclude=(Overlay.GLOBAL,)), Boolean())
    def set_visible(self, component, visible):
        """Set the visibility of an overlay component.

        Ticks cannot be shown or hidden in AST, but it is possible to set the width to a very small non-zero number to make them effectively invisible.

        Parameters
        ----------
        component : {0}
            The overlay component.
        visible : {1}
            The visibility state.
        """
        if component == Overlay.TICKS:
            logger.warning("Ticks cannot be shown or hidden.")
            return

        self._components[component].call_action("setVisible", visible)

    @validate(Constant(Overlay, exclude=(Overlay.GLOBAL,)))
    def visible(self, component):
        """Whether an overlay component is visible.

        Ticks cannot be shown or hidden in AST.

        Parameters
        ----------
        component : {0}
            The overlay component.

        Returns
        -------
        boolean or None
            Whether the component is visible, or None for an invalid component.
        """
        if component == Overlay.TICKS:
            logger.warning("Ticks cannot be shown or hidden.")
            return

        return self._components[component].get_value("visible")

    @validate(Constant(Overlay, exclude=(Overlay.GLOBAL,)))
    def show(self, component):
        """Show an overlay component.

        Parameters
        ----------
        component : {0}
            The overlay component.
        """
        self.set_visible(component, True)

    @validate(Constant(Overlay, exclude=(Overlay.GLOBAL,)))
    def hide(self, component):
        """Hide an overlay component.

        Parameters
        ----------
        component : {0}
            The overlay component.
        """
        self.set_visible(component, False)

    def toggle_labels(self):
        """Toggle the overlay labels."""
        self.call_action("toggleLabels")
