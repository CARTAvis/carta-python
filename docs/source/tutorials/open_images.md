# Open images and change how they look

In this tutorial you open an HI data cube of the Small Magellanic Cloud (SMC), go to one velocity channel, change its colormap and scaling, then add a dust map of the same region and match the two images on the sky. Each step is one call that does what you would otherwise do by hand in the CARTA GUI.

## Before you start

- Install carta-python with the browser extra and make sure the CARTA backend can start from Python. See the {doc}`../quickstart`.
- The example downloads two public images from the [Astropy data server](https://www.astropy.org/astropy-data/), about 55 MB in all:
  - [reduced_TAN_C14.fits](https://www.astropy.org/astropy-data/tutorials/FITS-cubes/reduced_TAN_C14.fits), a 21 cm HI cube of the Magellanic Clouds from the [HI4PI survey](https://doi.org/10.1051/0004-6361/201629178) (150 × 150 pixels, 450 velocity channels).
  - [herschel-350.fits.gz](https://www.astropy.org/astropy-data/tutorials/FITS-cubes/herschel-350.fits.gz), a Herschel SPIRE dust map of the SMC.

## Step by step

### Download the data

The script downloads the two files into a `carta-tutorial-data` folder in the current directory, and skips the download if the files are already there. The dust map stays compressed: CARTA opens gzip-compressed FITS files directly.

```{literalinclude} ../../examples/open_images.py
:language: python
:start-at: "# Download the data once"
:end-before: "# Start a CARTA backend"
```

### Start a session

{meth}`Session.start_and_create <carta.session.Session.start_and_create>` starts a CARTA backend on your computer and opens the CARTA frontend in a headless Chrome browser, so no window appears. The other ways to connect, for example to a CARTA session that is already open in your browser, are described in the {doc}`../quickstart`.

```{literalinclude} ../../examples/open_images.py
:language: python
:start-at: "# Start a CARTA backend"
:end-before: "# Open the HI cube"
```

### Open the cube

{meth}`Session.open_image <carta.session.Session.open_image>` does the same as **File > Open image** in the GUI. It returns an {class}`~carta.image.Image` object, which you use for everything else you do to that image.

Paths are relative to the backend's top-level folder. A backend started from Python uses `/` as its top-level folder, so absolute paths on your computer work as they are.

```{literalinclude} ../../examples/open_images.py
:language: python
:start-at: "# Open the HI cube"
:end-before: "# Go to the channel"
```

### Go to a velocity channel

{meth}`Image.set_channel <carta.image.Image.set_channel>` does the same as moving the channel slider in the **Animator** widget. Channels are counted from 0.

To find the channel for a given velocity, the example reads the spectral axis from the FITS header through {attr}`Image.header <carta.image.Image.header>`:

```{literalinclude} ../../examples/open_images.py
:language: python
:start-at: "# Go to the channel"
:end-before: "# Change the colormap"
```

### Change the colormap and scaling

Settings from the **Render Configuration** widget are on the image's `raster` attribute, a {class}`~carta.raster.Raster` object. Use the {class}`~carta.constants.Colormap` and {class}`~carta.constants.Scaling` enums rather than strings, so that a typo raises an error straight away.

{meth}`Session.save_rendered_view <carta.session.Session.save_rendered_view>` saves the active image, as it is shown, to a PNG file.

```{literalinclude} ../../examples/open_images.py
:language: python
:start-at: "# Change the colormap"
:end-before: "# Add the dust map"
```

### Add a second image

`append=True` does the same as **File > Append image**: the new image is added and the cube stays open. Without it, `open_image` closes the images that are already open.

The dust map is stored in the first FITS extension, not in the primary HDU, so the example selects it with `hdu="1"`.

```{literalinclude} ../../examples/open_images.py
:language: python
:start-at: "# Add the dust map"
:end-before: "# Match the dust map"
```

### Match the images on the sky

Matching does the same as the matching buttons in the **Image List** widget. One image is the spatial reference, and the other images follow its position and zoom:

```{literalinclude} ../../examples/open_images.py
:language: python
:start-at: "# Match the dust map"
:end-before: "# Show both images"
```

Images can also be matched in the spectral axis ({meth}`~carta.image.Image.set_spectral_matching`) and in their raster scaling ({meth}`~carta.image.Image.set_raster_scaling_matching`).

### Show both images and close the session

{meth}`Session.set_viewer_mode <carta.session.Session.set_viewer_mode>` switches between showing one image and showing several side by side. When you are done, {meth}`Session.close <carta.session.Session.close>` closes the browser and stops the backend that the script started.

```{literalinclude} ../../examples/open_images.py
:language: python
:start-at: "# Show both images"
```

## Complete example

```{literalinclude} ../../examples/open_images.py
:language: python
```

## Common problems

- **The image does not open.** Check that the path is relative to the backend's top-level folder. If you connect to a backend that someone else started, its top-level folder is probably not `/`; use {meth}`Session.ls <carta.session.Session.ls>` and {meth}`Session.cd <carta.session.Session.cd>` to find the file.
- **`set_channel` raises a validation error.** The channel must be between 0 and {attr}`Image.depth <carta.image.Image.depth>` minus 1.
- **The image opens with the wrong data.** For a FITS file with several extensions, pass the HDU number as a string, for example `hdu="1"`.

## See also

- {mod}`carta.session`: opening images and saving the rendered view.
- {mod}`carta.image`: channels, matching, and the image header.
- {mod}`carta.raster`: colormap, scaling and clipping.
