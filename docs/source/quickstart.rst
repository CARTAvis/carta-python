CARTA scripting quick start
===========================

Installation
------------

This package is not yet published on PyPi, but can be installed from a local checkout of the repository. The protocol buffer definitions and associated files are in a submodule.

Ensure that you're using a Python 3 installation and its corresponding ``pip``, either using a ``virtualenv`` or the appropriate system executable, which may be called ``pip3``.

.. code-block:: shell

    git clone --recursive https://github.com/idia-astro/carta-python.git
    cd carta-python
    pip install .

The required Python library dependencies (``grpcio``, ``grpcio-tools``, ``google-api-python-client``) should be installed automatically. To create new frontend sessions which are controlled by the wrapper instead of connecting to existing frontend sessions, you also need to install the ``selenium`` Python library.

You need access to a CARTA backend executable, either on the local host or on a remote host which you can access through SSH. You must be able to access the frontend served by this backend instance. SDM invocation (a multi-user system with web-based authentication) is not currently supported. The CARTA version must be ``3.0.0-beta.1b`` or newer. You must run the backend executable with the ``--grpc_port`` commandline parameter to enable the gRPC interface. The recommended default port value is ``50051``.

If you want to create browser sessions from the wrapper, you also need to make sure that your desired browser is installed, together with a corresponding web driver. At present only Chrome (or Chromium) can be used for headless sessions.

Connecting to an existing session
---------------------------------

Use this option if you want to use scripting to control a CARTA session which you already have open in your browser.

.. code-block:: python
    
    from carta.client import Session

    session = Session.interact("localhost", 50051, 1, "GRPC SECURITY TOKEN")

The host, port and security token values must match your running backend process. For simplicity you have the option of using an environment variable, ``CARTA_GRPC_TOKEN``, to run CARTA with a fixed gRPC token. Otherwise, a randomly generated token will be printed by the backend when it starts. The session ID must match the running frontend session -- you can find it by mousing over the status indicator at the top right of the CARTA window in your browser.

Creating a new session
----------------------

Use these options if you want to write a non-interactive script which starts a new session in a headless browser (and optionally also a new backend process), performs a series of actions, and saves output, with no input from you.

The wrapper automatically parses the gRPC host and port and the session ID from the frontend. If the wrapper also starts the backend process, it parses the frontend URL and gRPC token from the backend output. If you want to connect to an existing backend process, you must provide the frontend URL and the security token.

The wrapper can start a backend process on a remote host if your Unix user has the appropriate permissions to ssh to the remote host without entering a password.

These commands are further customisable with optional parameters. See the API reference for more information.

.. code-block:: python
    
    from carta.client import Session
    from carta.browser import ChromeHeadless

    # New session, connect to an existing backend
    session = Session.connect(ChromeHeadless(), "FRONTEND URL", "GRPC SECURITY TOKEN")

    # New session, start local backend
    session = Session.new(ChromeHeadless())

    # New session, start remote backend
    session = Session.new(ChromeHeadless(), remote_host="REMOTE HOSTNAME OR IP")

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
