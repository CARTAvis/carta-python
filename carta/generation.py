"""This module contains functionality for making images from an image in the background, such as moment images.

The classes in this module should not be instantiated directly. When an image object is created, a moment images object is automatically created as a property.
"""

import time

from .constants import JobStatus, Moment, MomentMask, RegionType, SpectralSystem, SpectralType, SpectralUnit
from .region import Region
from .util import CartaScriptingException, CartaValidationFailed
from .validation import validate, Number, Constant, Boolean, IterableOf, NoneOr, InstanceOf

JOBS_PATH = "imageGenerationJobs"
"""The path of the frontend store that runs the jobs."""

CLOSED_REGION_TYPES = (RegionType.RECTANGLE, RegionType.ELLIPSE, RegionType.POLYGON)
"""The region types that moments can be made over."""


class CartaJobFailed(CartaScriptingException):
    """A job that makes images failed or was cancelled."""
    pass


def channel_settings(spectral_range, spectral_type, unit, spectral_system, channels):
    """Return the channel settings of a job, as the frontend reads them.

    This is an internal helper function which should not be used directly.

    Parameters
    ----------
    spectral_range : iterable of two numbers or None
        The first and last spectral value.
    spectral_type : :obj:`carta.constants.SpectralType` or None
        The spectral type of the values.
    unit : :obj:`carta.constants.SpectralUnit` or None
        The unit of the values.
    spectral_system : :obj:`carta.constants.SpectralSystem` or None
        The spectral system of the values.
    channels : iterable of two integers or None
        The first and last channel, as channel indices.

    Returns
    -------
    dict
        The settings. The dictionary is empty when neither a spectral range nor channels are given.

    Raises
    ------
    CartaValidationFailed
        If both a spectral range and channels are given, if a spectral type, unit or system is given without a spectral range, or if the unit is not a unit of the spectral type.
    """
    if spectral_range is not None and channels is not None:
        raise CartaValidationFailed("Give either a spectral range or channels, not both.")
    if spectral_range is None and (spectral_type is not None or unit is not None or spectral_system is not None):
        raise CartaValidationFailed("A spectral type, unit or system needs a spectral range.")
    if channels is not None:
        first, last = channels
        return {"channels": {"min": first, "max": last}}
    if spectral_range is None:
        return {}
    first, last = spectral_range
    spectral = {"min": first, "max": last}
    if spectral_type is not None:
        spectral_type = SpectralType(spectral_type)
        if unit is None:
            unit = spectral_type.default_unit
        elif SpectralUnit(unit) not in spectral_type.units:
            raise CartaValidationFailed(f"{unit} is not a unit of the spectral type {spectral_type}.")
        spectral["type"] = spectral_type
    if unit is not None:
        spectral["unit"] = SpectralUnit(unit)
    if spectral_system is not None:
        spectral["system"] = SpectralSystem(spectral_system)
    return {"spectralRange": spectral}


def open_images(image, path):
    """Return the images in a list of an image that are still open.

    This is an internal helper function which should not be used directly. The frontend keeps a closed image in the list of the image that it was made from. So this function leaves out the images that are not open any more.

    Parameters
    ----------
    image : :obj:`carta.image.Image` object
        The image that the images were made from.
    path : string
        The path of the list on the image, such as ``"momentImages"``.

    Returns
    -------
    list of :obj:`carta.image.Image` objects
        The open images, in the order of the list.
    """
    from .image import Image
    file_ids = image.get_value(path, return_path="frameInfo.fileId")
    open_ids = set(image.session.get_value("frames", return_path="frameInfo.fileId"))
    return [Image(image.session, file_id) for file_id in file_ids if file_id in open_ids]


class GenerationJob:
    """A job that makes images from an image in the background.

    This class should not be instantiated directly. Methods such as :obj:`carta.generation.MomentImages.generate` return a job.

    The job starts at once. A script can read its status and progress, wait for it, or cancel it. A large cube can take minutes, and :obj:`carta.generation.GenerationJob.wait` has no time limit.

    Parameters
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this job.
    job_id : integer
        The ID of this job in the frontend.

    Attributes
    ----------
    session : :obj:`carta.session.Session` object
        The session object associated with this job.
    job_id : integer
        The ID of this job in the frontend.
    """

    def __init__(self, session, job_id):
        self.session = session
        self.job_id = job_id

    def __repr__(self):
        """A human-readable representation of this job."""
        return f"{type(self).__name__}(job_id={self.job_id})"

    def _state(self):
        return self.session.call_action(f"{JOBS_PATH}.getJob", self.job_id, response_expected=True)

    @property
    def status(self):
        """The status of the job.

        Returns
        -------
        :obj:`carta.constants.JobStatus`
            The status.
        """
        return JobStatus(self._state()["status"])

    @property
    def progress(self):
        """The progress of the job, from 0 to 1.

        The progress is 0 while the frontend prepares the region of the job, and after the job fails or is cancelled.

        Returns
        -------
        float
            The progress.
        """
        return self._state()["progress"]

    @property
    def error(self):
        """The reason why the job failed.

        Returns
        -------
        string or None
            The reason, or ``None`` when the job did not fail.
        """
        return self._state().get("error")

    def cancel(self):
        """Cancel the job.

        Images that the backend still makes for the job are closed without being shown. Nothing happens when the job has already ended.
        """
        self.session.call_action(f"{JOBS_PATH}.cancelJob", self.job_id)

    @validate(Number.POSITIVE)
    def wait(self, poll_interval=1):
        """Wait until the job ends, and return the images that it made.

        This method has no time limit. It checks the status of the job every *poll_interval* seconds.

        Parameters
        ----------
        poll_interval : {0}
            The number of seconds between two checks of the status. The default is ``1``.

        Returns
        -------
        object
            The images that the job made. The subclass of the job says in which form.

        Raises
        ------
        CartaJobFailed
            If the job fails or is cancelled.
        """
        state = self._state()
        while state["status"] == JobStatus.RUNNING:
            time.sleep(poll_interval)
            state = self._state()
        if state["status"] == JobStatus.FAILED:
            raise CartaJobFailed(f"The job failed: {state.get('error') or 'no reason was given'}.")
        if state["status"] == JobStatus.CANCELLED:
            raise CartaJobFailed("The job was cancelled.")
        return self._images(state["images"])

    def _images(self, images):
        from .image import Image
        return [Image(self.session, image["fileId"]) for image in images]


class MomentJob(GenerationJob):
    """A job that makes moment images.

    This class should not be instantiated directly. :obj:`carta.generation.MomentImages.generate` returns a job.
    """

    def _images(self, images):
        from .image import Image
        return {Moment(image["moment"]): Image(self.session, image["fileId"]) for image in images}

    @validate(Number.POSITIVE)
    def wait(self, poll_interval=1):
        """Wait until the job ends, and return the moment images that it made.

        This method has no time limit. It checks the status of the job every *poll_interval* seconds.

        Parameters
        ----------
        poll_interval : {0}
            The number of seconds between two checks of the status. The default is ``1``.

        Returns
        -------
        dict of :obj:`carta.constants.Moment` to :obj:`carta.image.Image` objects
            The new images, by the moment that each image shows. The backend leaves out the median coordinate when the mask gives no median.

        Raises
        ------
        CartaJobFailed
            If the job fails or is cancelled.
        """
        return super().wait(poll_interval)


class MomentImages:
    """Utility object for collecting image functions related to moment images.

    Parameters
    ----------
    image : :obj:`carta.image.Image` object
        The image that the moment images are made from.

    Attributes
    ----------
    image : :obj:`carta.image.Image` object
        The image that the moment images are made from.
    session : :obj:`carta.session.Session` object
        The session object associated with this object.
    """

    def __init__(self, image):
        self.image = image
        self.session = image.session

    @validate(
        IterableOf(Constant(Moment), min_size=1),
        NoneOr(InstanceOf(Region)),
        NoneOr(IterableOf(Number(), min_size=2, max_size=2)),
        NoneOr(Constant(SpectralType)),
        NoneOr(Constant(SpectralUnit)),
        NoneOr(Constant(SpectralSystem)),
        NoneOr(IterableOf(Number.ID, min_size=2, max_size=2)),
        Constant(MomentMask),
        NoneOr(IterableOf(Number(), min_size=2, max_size=2)),
        Boolean(),
    )
    def generate(self, moments, region=None, spectral_range=None, spectral_type=None, unit=None, spectral_system=None, channels=None, mask=MomentMask.NONE, pixel_range=None, keep=True):
        """Start a job that makes moment images of this image.

        The job runs in the background. Call :obj:`carta.generation.MomentJob.wait` on the returned job to get the new images.

        Give the channels either as spectral values with *spectral_range*, or as channel indices with *channels*. Give neither to use all channels. The spectral type, unit and system of the values default to those that the image shows. Giving them does not change what the image shows.

        Parameters
        ----------
        moments : {0}
            The moments to make.
        region : {1}
            A rectangle, ellipse or polygon region of this image. The moments are made over the region. The default is the whole image.
        spectral_range : {2}
            The first and last spectral value.
        spectral_type : {3}
            The spectral type of *spectral_range*. The default is the type that the image shows.
        unit : {4}
            The unit of *spectral_range*. The default is the default unit of *spectral_type*, or the unit that the image shows when *spectral_type* is not given.
        spectral_system : {5}
            The spectral system of *spectral_range*. The default is the system that the image shows.
        channels : {6}
            The first and last channel, as channel indices.
        mask : {7}
            How *pixel_range* masks the cube. The default is no mask.
        pixel_range : {8}
            The pixel range of the mask, in the brightness unit of the image. It is needed when *mask* is set.
        keep : {9}
            Whether to keep the moment images made from this image before. The default is ``True``. With ``False``, the earlier moment images are closed, as in the GUI.

        Returns
        -------
        :obj:`carta.generation.MomentJob`
            The job.

        Raises
        ------
        CartaValidationFailed
            If the region is not a rectangle, ellipse or polygon region of this image, if both *spectral_range* and *channels* are given, or if a mask is given without a pixel range.
        CartaActionFailed
            If the frontend cannot start the job, for example when this image already makes moment images.
        """
        settings = {"moments": list(moments), "mask": mask, "keep": keep}
        if region is not None:
            if region.region_type not in CLOSED_REGION_TYPES:
                raise CartaValidationFailed(f"Moments are made over a rectangle, ellipse or polygon region, not over a region of the type {region.region_type.name}.")
            if region.region_set.image.image_id != self.image.image_id:
                raise CartaValidationFailed("The region does not belong to this image.")
            settings["regionId"] = region.region_id
        if mask != MomentMask.NONE:
            if pixel_range is None:
                raise CartaValidationFailed("A mask needs a pixel range.")
        if pixel_range is not None:
            first, last = pixel_range
            settings["pixelRange"] = {"min": first, "max": last}
        settings.update(channel_settings(spectral_range, spectral_type, unit, spectral_system, channels))
        job_id = self.session.call_action(f"{JOBS_PATH}.startMoments", self.image.image_id, settings, response_expected=True)
        return MomentJob(self.session, job_id)

    @property
    def images(self):
        """The moment images made from this image that are still open.

        Returns
        -------
        list of :obj:`carta.image.Image` objects
            The images.
        """
        return open_images(self.image, "momentImages")

    def close_all(self):
        """Close the moment images made from this image."""
        for image in self.images:
            image.close()
