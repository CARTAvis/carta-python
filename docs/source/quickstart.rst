CARTA scripting quick start
===========================

Installation
------------

This package is not yet published on PyPi, but can be installed from a local checkout of the repository.

Ensure that you're using a Python 3 installation and its corresponding ``pip``, either using a ``virtualenv`` or the appropriate system executable, which may be called ``pip3``.

.. code-block:: shell

    git clone https://github.com/CARTAvis/carta-python.git
    cd carta-python
    pip install .

The required Python library dependencies should be installed automatically. To create new frontend sessions which are controlled by the wrapper instead of connecting to existing frontend sessions, you also need to install the ``selenium`` Python library.

You need access either to a CARTA backend executable, on the local host or on a remote host which you can access through SSH, or to a CARTA controller instance (a multi-user system with web-based authentication). You must be able to access the frontend served by this CARTA instance. If you are using your own backend executable, you must start it with the ``--enable_scripting`` commandline parameter to enable the scripting interface.

.. note::
   This version of the wrapper requires at least the 4.0 release versions of the CARTA backend, frontend and (optionally) controller. Older versions of these components may not work correctly and are not supported.

If you want to create browser sessions from the wrapper, you also need to make sure that your desired browser is installed, together with a corresponding web driver. At present only Chrome (or Chromium) can be used for headless sessions.

Connecting to an existing interactive session
---------------------------------------------

Use the ``interact`` method if you want to use scripting to control a CARTA session which you already have open in your browser.

.. code-block:: python
    
    from carta.session import Session
    from carta.token import BackendToken

    session = Session.interact("FRONTEND URL", 123456, BackendToken("SECURITY TOKEN"))

If you have launched a backend directly, the frontend URL and security token must match your running backend process. You have the option of using an environment variable, ``CARTA_AUTH_TOKEN``, to run CARTA with a fixed security token. Otherwise, a randomly generated token will be printed by the backend when it starts. If you include the security token in the URL, you may omit the security token parameter (it will be parsed from the URL automatically):

.. code-block:: python

    session = Session.interact("http://HOSTNAME:PORT?token=SECURITY_TOKEN", 123456)

The second parameter is the session ID, which must match the running frontend session -- you can find it by mousing over the status indicator at the top right of the CARTA window in your browser, or by reading the backend executable output.

To connect to a controller instance, you must authenticate to obtain a controller security token. We recommend using the helper functions provided to save the token to a file and load it from a file. You may also be able to copy this token from an existing browser cookie. This is a long-lived refresh token which will be used automatically to obtain access tokens from the controller as required. You will only have to authenticate again when the long-lived token expires. Token lifetime is configured by the host of the controller.

.. code-block:: python
    
    from carta.session import Session
    from carta.protocol import Protocol
    from carta.token import ControllerToken
    
    # Get a refresh token from the controller -- you only have to do this when the token expires
    # You will be prompted securely for a password
    # We recommend not automating this in a way that reveals the password!
    Protocol.request_refresh_token("FRONTEND URL", "USERNAME", "path/to/token")

    session = Session.interact("FRONTEND URL", 123456, ControllerToken.from_file("path/to/token"))

Creating a new interactive session
----------------------------------

Use the ``start_and_interact`` method if you want to start the backend process from an interactive Python session and connect to the default CARTA session which is automatically opened in your browser on startup.

This method parses the frontend URL and the session ID from the output of the backend process.

The wrapper can start the backend process on your local computer, or on a remote host if your Unix user has the appropriate permissions to ssh to the remote host without entering a password. This method cannot be used with a controller.

.. code-block:: python

    from carta.session import Session

    # New session, start local backend
    session = Session.start_and_interact()

    # New session, start remote backend
    session = Session.start_and_interact(remote_host="REMOTE HOSTNAME OR IP")

Creating a new non-interactive session
--------------------------------------

Use the ``create`` method if you want to write a non-interactive script which starts a new session in a headless browser, performs a series of actions, and saves output, with no input from you. The ``start_and_create`` method additionally starts a backend process first.

The wrapper automatically parses the session ID from the frontend. If the wrapper also starts the backend process, it parses the frontend URL from the backend output. If you want to connect to an existing backend process, you must provide the frontend URL and the security token. You may omit the token if it is included in the URL.

The wrapper can start a backend process on a remote host if your Unix user has the appropriate permissions to ssh to the remote host without entering a password.

.. code-block:: python
    
    from carta.session import Session
    from carta.token import BackendToken
    from carta.browser import Chrome

    # New session, connect to an existing backend
    session = Session.create(Chrome(), "FRONTEND URL", BackendToken("SECURITY TOKEN"))

    # New session, start local backend
    session = Session.start_and_create(Chrome())

    # New session, start remote backend
    session = Session.start_and_create(Chrome(), remote_host="REMOTE HOSTNAME OR IP")

To connect to a controller instance, you must authenticate (synchronously) to obtain a controller security token. We recommend using the helper functions provided to save the token to a file and to load it from a file when you use it.

.. code-block:: python

    from carta.protocol import Protocol

    # Get a refresh token from the controller -- you only have to do this when the token expires
    # You will be prompted securely for a password
    # We recommend not automating this in a way that reveals the password!
    Protocol.request_refresh_token("FRONTEND URL", "USERNAME", "path/to/token")
    
This is a long-lived refresh token which will be used automatically to obtain access tokens from the controller as required. You will only have to authenticate again when the long-lived token expires. Token lifetime is configured by the host of the controller. 

.. code-block:: python

    from carta.session import Session
    from carta.browser import Chrome
    from carta.token import ControllerToken
    
    # New session, connect to an existing controller
    session = Session.create(Chrome(), "FRONTEND URL", ControllerToken.from_file("path/to/token"))
    
These commands are further customisable with optional parameters. See the API reference for more information.

Opening and appending images
----------------------------

Helper methods on the session object open images in the frontend and return image objects which you can use to interact with individual images.

.. code-block:: python

    # Open or append images
    img1 = session.open_image("data/hdf5/first_file.hdf5")
    img2 = session.append_image("data/fits/second_file.fits")
        
Changing image properties
-------------------------

Properties specific to individual images can be accessed through image objects:

.. code-block:: python

    import numpy as np
    from carta.constants import Colormap, Scaling

    # change the channel
    img.set_channel_stokes(10, 0, True)
    # various commands for handling spatial and spectral matching are also available

    # pan and zoom
    y, x = img.shape[-2:]
    img.set_center(x/2, y/2)
    img.set_zoom(4)

    # change colormap
    img.set_colormap(Colormap.VIRIDIS)
    # more advanced options
    img.set_colormap(Colormap.VIRIDIS, invert=True)
    img.set_scaling(Scaling.LOG, alpha=100, min=-0.5, max=30)

    # add contours
    levels = np.arange(5, 5 * 5, 4)
    img.configure_contours(levels)
    img.apply_contours()
    # use a constant colour
    img.set_contour_color("red")
    # or use a colourmap
    img.set_contour_colormap(Colormap.REDS)
    
Changing session properties
---------------------------

Properties which affect the whole session can be set through the session object:

.. code-block:: python

    from carta.constants import CoordinateSystem, PaletteColor, Overlay

    # change some overlay properties
    session.set_view_area(1000, 1000)
    session.set_coordinate_system(CoordinateSystem.FK5)
    session.set_color(PaletteColor.RED)
    session.set_color(PaletteColor.VIOLET, Overlay.TICKS)
    session.show(Overlay.TITLE)
    
Saving or displaying an image
-----------------------------

You can retrieve the encoded image data URI, or the raw decoded data, or save the data to a png file.

The image data can be displayed in a Jupyter notebook:

.. code-block:: python

    from IPython.display import Image

    picture = Image(data=session.rendered_view_data("white"))
    display(picture)

Or an image can be saved to a PNG:

.. code-block:: python

    session.save_rendered_view("my_img.png", "white")
    
.. warning::
    A current known limitation of interactive sessions is that if an image has not finished rendering in the browser when the data is retrieved, you may see a partially rendered image in the scripting interface. We recommend that you use a headless browser for noninteractive scripts, or that you verify that the image has rendered before saving or loading it from an interactive scripting session.
    
Closing images
--------------

.. code-block:: python

    # Close all images open in the session
    for img in session.image_list():
        img.close()
    
Closing the session
-------------------

This will shut down the browser and backend if they were started by the wrapper.

.. code-block:: python

    session.close()
