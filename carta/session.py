"""
This is the main module of the CARTA Python wrapper. It contains a session class which represents a CARTA frontend session.

The user can interact with an existing CARTA session open in their browser by creating a session object using the :obj:`carta.session.Session.interact` classmethod.

Alternatively, the user can create a new session which runs in a headless browser controlled by the wrapper. The user can connect to an existing CARTA backend instance (using the :obj:`carta.session.Session.connect` classmethod), or first start a new CARTA backend instance which is also controlled by the wrapper (using the :obj:`carta.session.Session.new` classmethod). The backend can be started either on the local host or on a remote host which the user can access with passwordless SSH.
"""

import base64

from .image import Image
from .constants import CoordinateSystem, LabelType, BeamType, PaletteColor, Overlay, PanelMode, GridMode, ArithmeticExpression
from .backend import Backend
from .protocol import Protocol
from .util import logger, Macro, split_action_path, CartaBadID, CartaBadSession, CartaBadUrl
from .validation import validate, String, Number, Color, Constant, Boolean, NoneOr, OneOf


class Session:
    """This object corresponds to a CARTA frontend session.

    This class provides the core generic method for calling actions on the frontend (through the backend), as well as convenience methods which wrap this generic method and provide a more intuitive and user-friendly interface to frontend functionality associated with the session as a whole.

    This class should not be instantiated directly. Four class methods are provided for creating different types of sessions with all the appropriate parameters set:

    * :obj:`carta.session.Session.interact` for interacting with an existing CARTA session open in the user's browser.
    * :obj:`carta.session.Session.start_and_interact` for starting a new backend instance and then interacting with the default session which is automatically opened by the backend in the user's browser.
    * :obj:`carta.session.Session.create` for creating a new CARTA session in a headless browser by connecting to an existing CARTA backend or controller instance.
    * :obj:`carta.session.Session.start_and_create` for starting a new backend instance and then connecting to it to create a new session in a headless browser.

    The session object can be used to create image objects, which provide analogous convenience methods for functionality associated with individual images.

    Parameters
    ----------
    session_id : integer
        The ID of the CARTA frontend session associated with this object. This is set automatically when a new session is created with :obj:`carta.session.Session.create` or :obj:`carta.session.Session.start_and_create`.
    protocol : :obj:`carta.protocol.Protocol`
        The protocol object which handles HTTP communication with the CARTA scripting API. This is created automatically when a new session is created with one of the three class methods for creating sessions.
    browser : :obj:`carta.browser.Browser`
        The browser object associated with this session. This is created automatically when a new session is created with :obj:`carta.session.Session.create` or :obj:`carta.session.Session.start_and_create`.
    backend : :obj:`carta.backend.Backend`
        The backend object associated with this session. This is created automatically when a new session is created with :obj:`carta.session.Session.start_and_create`.

    Attributes
    ----------
    session_id : integer
        The ID of the CARTA frontend session associated with this object.
    """

    def __init__(self, session_id, protocol, browser=None, backend=None):
        self.session_id = session_id
        self._protocol = protocol
        self._browser = browser
        self._backend = backend

        # This is a local point of reference for paths, and may not be in sync with the frontend's starting directory
        self._pwd = None

    def __del__(self):
        self.close()

    @classmethod
    def interact(cls, frontend_url, session_id, token=None, debug_no_auth=False, backend=None):
        """Interact with an existing CARTA frontend session.

        Parameters
        ----------
        frontend_url : string
            The frontend URL of the CARTA instance.
        session_id : integer
            The ID of an existing CARTA frontend session. You may supply this as a string of digits; it will be converted to an integer automatically.
        token : :obj:`carta.token.Token`, optional
            The security token used by the CARTA instance. You may omit this if the URL contains a token.
        debug_no_auth : boolean, optional
            Disable authentication. Set this if the backend has been started with the ``--debug_no_auth`` option. This is provided for debugging purposes only and should not be used under normal circumstances.
        backend : :obj:`carta.backend.Backend`
            The backend object associated with this session, if any. This is set if this method is called from :obj:`carta.session.Session.start_and_interact`.

        Returns
        -------
        :obj:`carta.session.Session`
            A session object associated with the frontend session provided.

        Raises
        ------
        CartaBadID
            If the ID provided cannot be converted to an integer
        CartaBadToken
            If an invalid token was provided.
        CartaBadUrl
            If an invalid URL was provided.
        CartaBadSession
            If the session object could not be created.
        """
        try:
            session_id = int(session_id)
        except ValueError:
            raise CartaBadID(f"Session ID '{session_id}' is not a number.")

        return cls(session_id, Protocol(frontend_url, token, debug_no_auth=debug_no_auth), backend=backend)

    @classmethod
    def start_and_interact(cls, executable_path="carta", remote_host=None, params=tuple(), token=None, frontend_url_timeout=10, session_creation_timeout=10):
        """Start a new CARTA backend instance and interact with the default CARTA frontend session which is created automatically in the user's browser. This method cannot be used with a CARTA controller instance.

        Parameters
        ----------
        executable_path : string, optional
            A custom path to the CARTA backend executable. The default is ``"carta"``.
        remote_host : string, optional
            A remote host where the backend process should be launched, which must be accessible through passwordless ssh. By default the backend process is launched on the local host.
        params : iterable, optional
            Additional parameters to be passed to the backend process. By default scripting is enabled. The parameters are appended to the end of the command, so a positional parameter for a data directory can be included. Example: ``["--verbosity", 5, "--port", 3010]``
        token : :obj:`carta.token.Token`, optional
            The security token to use. Parsed from the backend output by default.
        frontend_url_timeout : integer
            How long to keep checking the backend output for the frontend URL. Default: 10 seconds.
        session_creation_timeout : integer
            How long to keep checking the output for a default session ID. Default: 10 seconds.

        Returns
        -------
        :obj:`carta.session.Session`
            A session object associated with the frontend session provided.

        Raises
        ------
        CartaBadID
            If a valid ID cannot be obtained from the backend process output.
        CartaBadToken
            If a valid token cannot be obtained from the backend process output, or the provided token is invalid.
        CartaBadUrl
            If a valid URL cannot be obtained from the backend process output.
        CartaBadSession
            If the session object could not be created.
        """
        backend = Backend(("--enable_scripting", *params), executable_path, remote_host, token, frontend_url_timeout, session_creation_timeout)
        if not backend.start():
            raise CartaBadSession(f"CARTA backend exited unexpectedly:\n{''.join(backend.errors)}")

        if backend.frontend_url is None:
            backend.stop()
            raise CartaBadUrl("Could not parse CARTA frontend URL from backend output.")

        if backend.last_session_id is None:
            backend.stop()
            raise CartaBadID("Could not parse default CARTA session ID from backend output.")

        return cls.interact(backend.frontend_url, backend.last_session_id, token, backend.debug_no_auth, backend)

    @classmethod
    def create(cls, browser, frontend_url, token=None, timeout=10, debug_no_auth=False):
        """Connect to an existing CARTA backend or CARTA controller instance and create a new session.

        Parameters
        ----------
        browser : :obj:`carta.browser.Browser`
            The browser to use to open the frontend.
        frontend_url : string
            The frontend URL of the CARTA instance.
        token : :obj:`carta.token.Token`, optional
            The security token used by the CARTA instance. You may omit this if the URL contains a token.
        timeout : integer, optional
            The number of seconds to spend retrying parsing connection information from the frontend (default: 10).
        debug_no_auth : boolean, optional
            Disable authentication. Set this if the backend has been started with the ``--debug_no_auth`` option. This is provided for debugging purposes only and should not be used under normal circumstances.

        Returns
        -------
        :obj:`carta.session.Session`
            A session object connected to a new frontend session running in the browser provided.

        Raises
        ------
        CartaBadToken
            If an invalid token was provided.
        CartaBadUrl
            If an invalid URL was provided.
        CartaBadSession
            If the session object could not be created.
        """
        return browser.new_session_from_url(frontend_url, token, backend=None, timeout=timeout, debug_no_auth=debug_no_auth)

    @classmethod
    def start_and_create(cls, browser, executable_path="carta", remote_host=None, params=tuple(), timeout=10, token=None, frontend_url_timeout=10):
        """Start a new CARTA backend instance and create a new session. This method cannot be used with a CARTA controller instance (which already starts and stops backend instances for the user on demand).

        Parameters
        ----------
        browser : :obj:`carta.browser.Browser`
            The browser to use to open the frontend.
        executable_path : string, optional
            A custom path to the CARTA backend executable. The default is ``"carta"``.
        remote_host : string, optional
            A remote host where the backend process should be launched, which must be accessible through passwordless ssh. By default the backend process is launched on the local host.
        params : iterable, optional
            Additional parameters to be passed to the backend process. By default scripting is enabled and the automatic browser is disabled. The parameters are appended to the end of the command, so a positional parameter for a data directory can be included. Example: ``["--verbosity", 5, "--port", 3010]``
        timeout : integer, optional
            The number of seconds to spend parsing the frontend for connection information. 10 seconds by default.
        token : :obj:`carta.token.Token`, optional
            The security token to use. Parsed from the backend output by default.
        frontend_url_timeout : integer
            How long to keep checking the backend output for the frontend URL. Default: 10 seconds.

        Returns
        -------
        :obj:`carta.session.Session`
            A session object connected to a new frontend session running in the browser provided.

        Raises
        ------
        CartaBadToken
            If an invalid token was provided.
        CartaBadUrl
            If an invalid URL was provided.
        CartaBadSession
            If the session object could not be created.
        """
        return browser.new_session_with_backend(executable_path, remote_host, params, timeout, token, frontend_url_timeout)

    def __repr__(self):
        return f"Session(session_id={self.session_id}, uri={self._protocol.frontend_url})"

    def call_action(self, path, *args, **kwargs):
        """Call an action on the frontend through the backend's scripting interface.

        This method is the core of the session class, and provides a generic interface for calling any action on the frontend. This is exposed as a public method to give developers the option of writing experimental functionality; wherever possible script writers should instead use the more user-friendly methods on the session and image objects which wrap this method.

        Parameters
        ----------
        path : string
            The full dot-separated path to a frontend action.
        *args
            A variable-length list of parameters to pass to the action. :obj:`carta.util.Macro` objects may be used to refer to frontend objects which will be evaluated dynamically. This parameter list will be serialized into a JSON string with :obj:`carta.util.CartaEncoder`.
        **kwargs
            Arbitrary keyword arguments. At present only three are used: *async* (boolean) is passed to indicate that the request should return a response as soon as the action is called, without waiting for the action to complete. *response_expected* (boolean) indicates that the action should return a JSON object. This is set automatically if *return_path* is set. *return_path* specifies a subobject of the action's response which should be returned instead of the whole response. *timeout* (boolean) is the maximum time in seconds to wait for an action request to complete (the default is 10).

        Returns
        -------
        None or an object
            If the action returns a JSON object, this method will return that response deserialized into a Python object.

        Raises
        ------
        CartaBadRequest
            If the request was invalid.
        CartaRequestFailed
            If the backend could not send the request to the frontend.
        CartaActionFailed
            If the action failed.
        CartaBadResponse
            If a request which was expected to have a JSON response did not have one, or if a JSON response could not be decoded.
        """
        return self._protocol.request_scripting_action(self.session_id, path, *args, **kwargs)

    def get_value(self, path):
        """Get the value of an attribute from a frontend store.

        Like the :obj:`carta.session.Session.call_action` method, this is exposed in the public API but is not intended to be used directly under normal circumstances.

        Parameters
        ----------
        path : string
            The full path to the attribute.

        Returns
        -------
        object
            The value of the attribute, deserialized from a JSON string.
        """
        path, parameter = split_action_path(path)
        macro = Macro(path, parameter)
        return self.call_action("fetchParameter", macro, response_expected=True)

    # FILE BROWSING

    def resolve_file_path(self, path):
        """Convert a file path to an absolute path.

        Parameters
        ----------
        path : string
            The file path, which may be absolute or relative to the current directory.

        Returns
        -------
        string
            The absolute file path, relative to the CARTA backend's root.
        """
        if path.startswith('/'):
            return path
        else:
            return f"{self.pwd()}/{path}"

    def pwd(self):
        """The current directory. This is a local property of the wrapper, and may not be in sync with the frontend's saved starting directory, which is changed whenever a file is opened to the file's parent directory.

        Returns
        -------
        string
            The session's current directory.
        """
        if self._pwd is None:
            self.call_action("fileBrowserStore.getFileList", Macro("fileBrowserStore", "startingDirectory"))
            directory = self.get_value("fileBrowserStore.fileList.directory")
            self._pwd = f"/{directory}"
        return self._pwd

    def ls(self):
        """The current directory listing.

        Returns
        -------
        list
            The list of files and subdirectories in the session's locally stored current directory.
        """
        self.call_action("fileBrowserStore.getFileList", self.pwd())
        file_list = self.get_value("fileBrowserStore.fileList")
        items = []
        if "files" in file_list:
            items.extend([f["name"] for f in file_list["files"]])
        if "subdirectories" in file_list:
            items.extend([f"{d['name']}/" for d in file_list["subdirectories"]])
        return sorted(items)

    def cd(self, path):
        """Change the current directory used by the wrapper.

        TODO: .. is not supported, but it can be now that we have made this value independent of the frontend.

        This does not affect the starting directory saved by the frontend. To change that directory, use :obj:`carta.session.Session.set_starting_directory`.

        Parameters
        ----------
        path : string
            The path to the new directory, which may be relative to the current directory or absolute (relative to the CARTA backend root).
        """
        self._pwd = self.resolve_file_path(path)

    def set_starting_directory(self, path):
        """Change the starting directory of the frontend.

        This is particularly useful for interactive sessions. If a new session object reconnects to an existing frontend session, this method allows the current directory in the frontend session to be reset to a known state. This ensures that any paths used in the script continue to work even if the current directory in the frontend changed during a previous execution.

        It should not be necessary to use this method in non-interactive scripts which do not reuse frontend sessions.

        This does not affect the current directory used by the wrapper. To change that directory, use :obj:`carta.session.Session.cd`.

        This method must be called before any methods that use the locally saved path.

        Parameters
        ----------
        path : string
            The path to the new directory, which must be absolute (relative to the CARTA backend root).

        """
        self.call_action("fileBrowserStore.saveStartingDirectory", path)

    # IMAGES

    @validate(String(), String(r"\d*"), Boolean(), NoneOr(Constant(ArithmeticExpression)))
    def open_image(self, path, hdu="", complex=False, expression=None):
        """Open a new image, replacing any existing images.

        Parameters
        ----------
        path : {0}
            The path to the image file, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.
        hdu : {1}
            The HDU to select inside the file.
        complex : {2}
            Whether the image is complex. Set to ``False`` by default.
        expression : {3}
            Arithmetic expression to use if opening a complex-valued image. By default, the amplitude will be shown if the image is complex.
        """
        return Image.new(self, path, hdu, False, complex, expression)

    @validate(String(), String(r"\d*"), Boolean(), NoneOr(Constant(ArithmeticExpression)))
    def append_image(self, path, hdu="", complex=False, expression=None):
        """Append a new image, keeping any existing images.

        Parameters
        ----------
        path : {0}
            The path to the image file, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.
        hdu : {1}
            The HDU to select inside the file.
        complex : {2}
            Whether the image is complex. Set to ``False`` by default.
        expression : {3}
            Arithmetic expression to use if appending a complex-valued image. By default, the amplitude will be shown if the image is complex.
        """
        return Image.new(self, path, hdu, True, complex, expression)

    def image_list(self):
        """Return the list of currently open images.

        Returns
        -------
        list of :obj:`carta.image.Image` objects.
        """
        return Image.from_list(self, self.get_value("frameNames"))

    def active_frame(self):
        """Return the currently active image.

        Returns
        -------
        :obj:`carta.image.Image`
            The currently active image.
        """
        frame_info = self.get_value("activeFrame.frameInfo")
        image_id = frame_info["fileId"]
        file_name = frame_info["fileInfo"]["name"]
        return Image(self, image_id, file_name)

    def clear_spatial_reference(self):
        """Clear the spatial reference."""
        self.call_action("clearSpatialReference")

    def clear_spectral_reference(self):
        """Clear the spectral reference."""
        self.call_action("clearSpectralReference")

    def clear_raster_scaling_reference(self):
        """Clear the raster scaling reference."""
        self.call_action("clearRasterScalingReference")

    # VIEWER MODES
    @validate(Constant(PanelMode))
    def set_viewer_mode(self, panel_mode):
        """
        Switch between single-panel mode and multiple-panel mode.

        Parameters
        ----------
        panel_mode : {0}
            The panel mode to adopt.
        """
        if panel_mode == PanelMode.SINGLE:
            multiple = False
        elif panel_mode == PanelMode.MULTIPLE:
            multiple = True
        self.call_action("widgetsStore.setImageMultiPanelEnabled", multiple)

    def previous_page(self):
        """Go to previous page in viewer."""
        self.call_action("widgetsStore.onPreviousPageClick")

    def next_page(self):
        """Go to next page in viewer."""
        self.call_action("widgetsStore.onNextPageClick")

    @validate(Number(1, 10, step=1), Number(1, 10, step=1), Constant(GridMode))
    def set_viewer_grid(self, rows, columns, grid_mode=GridMode.FIXED):
        """
        Set number of columns and rows in viewer grid.

        Parameters
        ----------
        rows : {0}
            Number of rows.
        columns : {1}
            Number of columns.
        grid_mode : {2}
            The grid mode to adopt. The default is :obj:`carta.constants.GridMode.FIXED`.
        """
        self.call_action("widgetsStore.setImageMultiPanelEnabled", True)
        self.call_action("preferenceStore.setPreference", "imagePanelRows", rows)
        self.call_action("preferenceStore.setPreference", "imagePanelColumns", columns)
        self.call_action("preferenceStore.setPreference", "imagePanelMode", grid_mode)

    # CANVAS AND OVERLAY
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
        self.call_action("overlayStore.setViewDimension", width, height)

    @validate(Constant(CoordinateSystem))
    def set_coordinate_system(self, system=CoordinateSystem.AUTO):
        """Set the coordinate system.

        Parameters
        ----------
        system : {0}
            The coordinate system.
        """
        self.call_action("overlayStore.global.setSystem", system)

    @validate(Constant(LabelType))
    def set_label_type(self, label_type):
        """Set the label type.

        Parameters
        ----------
        label_type : {0}
            The label type.
        """
        self.call_action("overlayStore.global.setLabelType", label_type)

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
            self.call_action("overlayStore.title.setCustomTitleString", title)
            self.call_action("overlayStore.title.setCustomText", True)
        if label_x is not None:
            self.call_action("overlayStore.labels.setCustomLabelX", label_x)
        if label_y is not None:
            self.call_action("overlayStore.labels.setCustomLabelX", label_y)
        if label_x is not None or label_y is not None:
            self.call_action("overlayStore.labels.setCustomText", True)

    def clear_text(self):
        """Clear all custom title and axis text."""
        self.call_action("overlayStore.title.setCustomText", False)
        self.call_action("overlayStore.labels.setCustomText", False)

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
            self.call_action(f"overlayStore.{component}.setFont", font)
        if font_size is not None:
            self.call_action(f"overlayStore.{component}.setFontSize", font_size)

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
            self.call_action(f"overlayStore.{Overlay.BEAM}.setBeamType", beam_type)
        if width is not None:
            self.call_action(f"overlayStore.{Overlay.BEAM}.setWidth", width)
        if shift_x is not None:
            self.call_action(f"overlayStore.{Overlay.BEAM}.setShiftX", shift_x)
        if shift_y is not None:
            self.call_action(f"overlayStore.{Overlay.BEAM}.setShiftY", shift_y)

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
        self.call_action(f"overlayStore.{component}.setColor", color)
        if component not in (Overlay.GLOBAL, Overlay.BEAM):
            self.call_action(f"overlayStore.{component}.setCustomColor", True)

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

        self.call_action(f"overlayStore.{component}.setCustomColor", False)

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
        if component in (Overlay.GLOBAL, Overlay.BEAM) or self.get_value(f"overlayStore.{component}.customColor"):
            return PaletteColor(self.get_value(f"overlayStore.{component}.color"))

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

    @validate(Number(min=0, interval=Number.EXCLUDE), OneOf(Overlay.GRID, Overlay.BORDER, Overlay.TICKS, Overlay.AXES, Overlay.COLORBAR))
    def set_width(self, width, component):
        """Set the line width of an overlay component.

        Parameters
        ----------
        component : {0}
            The overlay component.
        """
        self.call_action(f"overlayStore.{component}.setWidth", width)

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
        return self.get_value(f"overlayStore.{component}.width")

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

        self.call_action(f"overlayStore.{component}.setVisible", visible)

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

        return self.get_value(f"overlayStore.{component}.visible")

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

    def call_overlay_action(self, component, path, *args, **kwargs):
        """Helper method for calling overlay component actions.

        This method calls :obj:`carta.session.Session.call_action` after prepending this component's base path to the path parameter.

        Parameters
        ----------
        component : a member of :obj:`carta.constants.Overlay`
            The overlay component to use as the base of the path.
        path : string
            The path to an action relative to this overlay component.
        *args
            A variable-length list of parameters. These are passed unmodified to :obj:`carta.Session.call_action`.
        **kwargs
            Arbitrary keyword parameters. These are passed unmodified to :obj:`carta.Session.call_action`.
        """
        self.call_action(f"overlayStore.{component}.{path}", *args, **kwargs)

    def get_overlay_value(self, component, path):
        """Helper method for retrieving the values of overlay component attributes.

        This method calls :obj:`carta.session.Session.get_value` after prepending this component's base path to the path parameter.

        Parameters
        ----------
        component : a member of :obj:`carta.constants.Overlay`
            The overlay component to use as the base of the path.
        path : string
            The path to an attribute relative to this overlay component.

        Returns
        -------
        object
            The value of the attribute, deserialized from a JSON string.
        """
        return self.get_value(f"overlayStore.{component}.{path}")

    def toggle_labels(self):
        """Toggle the overlay labels."""
        self.call_action("overlayStore.toggleLabels")

    # PROFILES (TODO)

    @validate(Number(), Number())
    def set_cursor(self, x, y):
        """Set the curson position.

        TODO: this is a precursor to making z-profiles available, but currently the relevant functionality is not exposed by the frontend.

        Parameters
        ----------
        x : {0}
            The X position.
        y : {1}
            The Y position.

        """
        self.active_frame().call_action("regionSet.regions[0].setControlPoint", 0, [x, y])

    # SAVE IMAGE

    @validate(NoneOr(Color()))
    def rendered_view_url(self, background_color=None):
        """Get a data URL of the rendered active image.

        Parameters
        ----------
        background_color : {0}
            The background color. By default the background will be transparent.

        Returns
        -------
        string
            A data URL for the rendered image in PNG format, base64-encoded.

        """
        self.call_action("waitForImageData")
        args = ["getImageDataUrl"]
        if background_color:
            args.append(background_color)
        return self.call_action(*args, response_expected=True)

    @validate(NoneOr(Color()))
    def rendered_view_data(self, background_color=None):
        """Get the decoded data of the rendered active image.

        Parameters
        ----------
        background_color : {0}
            The background color. By default the background will be transparent.

        Returns
        -------
        bytes
            The decoded PNG image data.

        """
        uri = self.rendered_view_url(background_color)
        data = uri.split(",")[1]
        return base64.b64decode(data)

    @validate(String(), NoneOr(Color()))
    def save_rendered_view(self, file_name, background_color=None):
        """Save the decoded data of the rendered active image to a file.

        Parameters
        ----------
        file_name : {0}
            The name of the file.
        background_color : {1}
            The background color. By default the background will be transparent.
        """
        with open(file_name, 'wb') as f:
            f.write(self.rendered_view_data(background_color))

    def close(self):
        """Close any browser sessions and backend processes controlled by this session object.

        If this session opened a CARTA frontend session in a headless browser, this method will close the browser together with that session. If this session is interacting with a session running in an external browser, that browser session will be unaffected. This includes the new CARTA frontend session which is started automatically when :obj:`carta.session.Session.start_and_interact` is used: that frontend session is opened in the user's browser, which is not controlled by this object.

        If this session started a new backend process, this method will stop that process. If this session is interacting with an externally started backend process, that process will be unaffected.
        """

        if self._browser is not None:
            self._browser.close()

        if self._backend is not None:
            self._backend.stop()
