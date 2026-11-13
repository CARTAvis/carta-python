"""Open an HI cube and a dust map of the Small Magellanic Cloud, and change how they are shown.

This is the complete example for the "Open images and change how they look"
tutorial. It downloads two public images from the Astropy data server, starts
a CARTA backend and a headless browser, and saves the result as PNG files.
"""

from pathlib import Path
from urllib.request import urlretrieve

from carta.browser import Chrome
from carta.constants import Colormap, PanelMode, Scaling
from carta.session import Session

DATA_URL = "https://www.astropy.org/astropy-data/tutorials/FITS-cubes/"
DATA_DIR = Path("carta-tutorial-data").resolve()
HI_CUBE = DATA_DIR / "reduced_TAN_C14.fits"
DUST_MAP = DATA_DIR / "herschel-350.fits.gz"

# Download the data once. CARTA opens gzip-compressed FITS files directly.
DATA_DIR.mkdir(exist_ok=True)
for path in (HI_CUBE, DUST_MAP):
    if not path.exists():
        urlretrieve(DATA_URL + path.name, path)

# Start a CARTA backend and connect to it from a headless Chrome browser
session = Session.start_and_create(Chrome())

# Open the HI cube. Absolute paths are relative to the backend's top-level folder.
hi = session.open_image(str(HI_CUBE))
print("Shape (velocity, y, x):", hi.shape)

# Go to the channel closest to 160 km/s, near the velocity of the SMC.
# The spectral axis is the third axis in the FITS header, in m/s.
header = hi.header
velocity = 160_000
channel = round((velocity - header["CRVAL3"]) / header["CDELT3"] + header["CRPIX3"] - 1)
hi.set_channel(channel)

# Change the colormap and the scaling, and clip to the brightest 99.5% of pixels
hi.raster.set_colormap(Colormap.INFERNO)
hi.raster.set_scaling(Scaling.SQRT)
hi.raster.set_clip(rank=99.5)
session.save_rendered_view("hi_channel.png", background_color="white")

# Add the dust map. The image is in the first extension, so select HDU 1.
dust = session.open_image(str(DUST_MAP), hdu="1", append=True)
dust.raster.set_colormap(Colormap.VIRIDIS)
dust.raster.set_scaling(Scaling.LOG)

# Match the dust map to the HI cube on the sky. The two images use different
# coordinate systems (Galactic and equatorial); CARTA converts between them.
hi.make_spatial_reference()
dust.set_spatial_matching(True)

# Show both images side by side and save the view of the active image
session.set_viewer_mode(PanelMode.MULTIPLE)
session.save_rendered_view("dust_matched.png", background_color="white")

session.close()
