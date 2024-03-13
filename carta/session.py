"""
This is the main module of the CARTA Python wrapper. It contains a session class which represents a CARTA frontend session.

The user can interact with an existing CARTA session open in their browser by creating a session object using the :obj:`carta.session.Session.interact` classmethod.

Alternatively, the user can create a new session which runs in a headless browser controlled by the wrapper. The user can connect to an existing CARTA backend instance (using the :obj:`carta.session.Session.connect` classmethod), or first start a new CARTA backend instance which is also controlled by the wrapper (using the :obj:`carta.session.Session.new` classmethod). The backend can be started either on the local host or on a remote host which the user can access with passwordless SSH.
"""

import base64
import posixpath

from .image import Image
from .constants import PanelMode, GridMode, ComplexComponent, Polarization
from .backend import Backend
from .protocol import Protocol
from .util import Macro, split_action_path, CartaBadID, CartaBadSession, CartaBadUrl
from .validation import validate, String, Number, Color, Constant, Boolean, NoneOr, IterableOf, MapOf, Union
from .wcs_overlay import WCSOverlay


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
    wcs : :obj:`carta.wcs_overlay.WCSOverlay`
        Sub-object with functions related to the WCS overlay.

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

        # Sub-objects grouping related functions
        self.wcs = WCSOverlay(self)

    def __del__(self):
        """Delete this session object."""
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
        """A human-readable representation of this session object."""
        return f"Session(session_id={self.session_id}, uri={self._protocol.frontend_url if self._protocol else None})"

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

    def get_value(self, path, return_path=None):
        """Get the value of an attribute from a frontend store.

        Like the :obj:`carta.session.Session.call_action` method, this is exposed in the public API but is not intended to be used directly under normal circumstances.

        Parameters
        ----------
        path : string
            The full path to the attribute.
        return_path : string, optional
            Specifies a subobject of the attribute value which should be returned instead of the whole object.

        Returns
        -------
        object
            The value of the attribute, deserialized from a JSON string.
        """
        path, parameter = split_action_path(path)
        macro = Macro(path, parameter)

        kwargs = {"response_expected": True}
        if return_path is not None:
            kwargs["return_path"] = return_path

        return self.call_action("fetchParameter", macro, **kwargs)

    # FILE BROWSING

    def resolve_file_path(self, path):
        """Convert a file path to an absolute path.

        This function prepends the session's current directory to a relative path, and normalizes the path to remove redundant separators and references.

        Parameters
        ----------
        path : string
            The file path, which may be absolute or relative to the current directory.

        Returns
        -------
        string
            The absolute file path, relative to the CARTA backend's root.
        """
        path = posixpath.join(self.pwd(), path)
        path = posixpath.normpath(path)
        return path

    def pwd(self):
        """The current directory.

        This is the frontend file browser's currently saved starting directory. Whenever an image file is opened with the frontend's file browser (which may happen if the wrapper is connected to an interactive session), this directory is changed to the file's parent directory. By default, this directory is not changed if an image is opened through the wrapper (which bypasses the file browser).

        Returns
        -------
        string
            The session's current directory.
        """
        self.call_action("fileBrowserStore.getFileList", Macro("fileBrowserStore", "startingDirectory"))
        directory = self.get_value("fileBrowserStore.fileList.directory")
        return f"/{directory}".rstrip("/")

    def ls(self):
        """The current directory listing.

        Returns
        -------
        list
            The list of files and subdirectories in the frontend file browser's current starting directory.
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
        """Change the current directory.

        This function changes the frontend file browser's starting directory.

        Parameters
        ----------
        path : string
            The path to the new directory, which may be relative to the current directory or absolute (relative to the CARTA backend root).
        """
        path = self.resolve_file_path(path)
        self.call_action("fileBrowserStore.saveStartingDirectory", path)

    # IMAGES

    @validate(String(), String(r"\d*"), Boolean(), Boolean(), Boolean())
    def open_image(self, path, hdu="", append=False, make_active=True, update_directory=False):
        """Open or append a new image.

        Parameters
        ----------
        path : {0}
            The path to the image file, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.
        hdu : {1}
            The HDU to select inside the file.
        append : {2}
            Whether the image should be appended to existing images. By default this is ``False`` and any existing open images are closed.
        make_active : {3}
            Whether the image should be made active in the frontend. This only applies if an image is being appended. The default is ``True``.
        update_directory : {4}
            Whether the starting directory of the frontend file browser should be updated to the parent directory of the image. The default is ``False``.

        Returns
        -------
        :obj:`carta.image.Image`
            The opened image.
        """
        directory, file_name = posixpath.split(path)
        return Image.new(self, directory, file_name, hdu, append, False, make_active=make_active, update_directory=update_directory)

    @validate(String(), Constant(ComplexComponent), Boolean(), Boolean(), Boolean())
    def open_complex_image(self, path, component=ComplexComponent.AMPLITUDE, append=False, make_active=True, update_directory=False):
        """Open or append a new complex-valued image.

        Parameters
        ----------
        path : {0}
            The path to the complex-valued image file, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.
        component : {1}
            The complex component to select when opening the image. The default is :obj:`carta.constants.ComplexComponent.AMPLITUDE`.
        append : {2}
            Whether the image should be appended to existing images. By default this is ``False`` and any existing open images are closed.
        make_active : {3}
            Whether the image should be made active in the frontend. This only applies if an image is being appended. The default is ``True``.
        update_directory : {4}
            Whether the starting directory of the frontend file browser should be updated to the parent directory of the image. The default is ``False``.

        Returns
        -------
        :obj:`carta.image.Image`
            The opened image.
        """
        directory, file_name = posixpath.split(path)
        expression = f'{component}("{file_name}")'
        return Image.new(self, directory, expression, "", append, True, make_active=make_active, update_directory=update_directory)

    @validate(String(), String(), Boolean(), Boolean(), Boolean())
    def open_LEL_image(self, expression, directory=".", append=False, make_active=True, update_directory=False):
        """Open or append a new image via the Lattice Expression Language (LEL) interface.

        Parameters
        ----------
        expression : {0}
            The LEL arithmetic expression.
        directory : {1}
            The base directory for the LEL expression, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory. Defaults to the session's current directory.
        append : {2}
            Whether the image should be appended to existing images. By default this is ``False`` and any existing open images are closed.
        make_active : {3}
            Whether the image should be made active in the frontend. This only applies if an image is being appended. The default is ``True``.
        update_directory : {4}
            Whether the starting directory of the frontend file browser should be updated to the base directory of the LEL expression. The default is ``False``.

        Returns
        -------
        :obj:`carta.image.Image`
            The opened image.
        """
        return Image.new(self, directory, expression, "", append, True, make_active=make_active, update_directory=update_directory)

    @validate(IterableOf(String()), Boolean())
    def open_images(self, image_paths, append=False):
        """Open multiple images

        This is a utility function for adding multiple images in a single command. It assumes that the images are not complex-valued or LEL expressions, and that the default HDU can be used for each image. For more complicated use cases, the methods for opening individual images should be used.

        Parameters
        ----------
        image_paths : {0}
            The image paths, either relative to the session's current directory or absolute paths relative to the CARTA backend's root directory.
        append : {1}
            Whether the images should be appended to existing images. By default this is ``False`` and any existing open images are closed.

        Returns
        -------
        list of :obj:`carta.image.Image` objects
            The list of opened images.
        """
        images = []
        for path in image_paths[:1]:
            images.append(self.open_image(path, append=append))
        for path in image_paths[1:]:
            images.append(self.open_image(path, append=True))
        return images

    @validate(Union(IterableOf(String(), min_size=2), MapOf(Constant(Polarization), String(), min_size=2)), Boolean())
    def open_hypercube(self, image_paths, append=False):
        """Open multiple images merged into a polarization hypercube.

        Parameters
        ----------
        image_paths : {0}
            The image paths, either relative to the session's current directory or absolute paths relative to the CARTA backend's root directory. If this is a list of paths, the polarizations will be deduced from the image headers or names. If this is a dictionary, the polarizations must be used as keys.
        append : {1}
            Whether the hypercube should be appended to existing images. By default this is ``False`` and any existing open images are closed.

        Returns
        -------
        :obj:`carta.image.Image`
            The opened hypercube.

        Raises
        ------
        ValueError
            If explicit polarizations are not provided, and cannot be deduced from the image headers or names.
        """
        stokes_images = []

        if isinstance(image_paths, dict):
            for stokes, path in image_paths.items():
                directory, file_name = posixpath.split(path)
                directory = self.resolve_file_path(directory)
                stokes_images.append({"directory": directory, "file": file_name, "hdu": "", "polarizationType": stokes.proto_index})
        else:
            stokes_guesses = set()

            for path in image_paths:
                directory, file_name = posixpath.split(path)
                directory = self.resolve_file_path(directory)

                stokes_guess = self.call_action("fileBrowserStore.getStokesFile", directory, file_name, "")

                if not stokes_guess:
                    raise ValueError(f"Could not deduce polarization for {path}. Please use a dictionary to specify the polarization mapping explicitly.")

                stokes_guesses.add(stokes_guess["polarizationType"])
                stokes_images.append(stokes_guess)

            if len(stokes_guesses) < len(stokes_images):
                raise ValueError("Duplicate polarizations deduced for provided images. Please use a dictionary to specify the polarization mapping explicitly.")

        output_directory = self.pwd()
        output_hdu = ""
        command = "appendConcatFile" if append else "openConcatFile"
        image_id = self.call_action(command, stokes_images, output_directory, output_hdu)
        return Image(self, image_id)

    def image_list(self):
        """Return the list of currently open images.

        Returns
        -------
        list of :obj:`carta.image.Image` objects
            The list of images open in this session.
        """
        return Image.from_list(self, self.get_value("frameNames"))

    def active_frame(self):
        """Return the currently active image.

        Returns
        -------
        :obj:`carta.image.Image`
            The currently active image.
        """
        image_id = self.get_value("activeFrame.frameInfo.fileId")
        return Image(self, image_id)

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
