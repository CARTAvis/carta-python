"""This module contains functionality for interacting with color blending images and their layers."""

from .constants import Colormap, ColormapSet, ImageType
from .image import Image
from .util import BasePathMixin, CartaActionFailed, Macro
from .validation import (
    Boolean,
    Constant,
    Coordinate,
    InstanceOf,
    IterableOf,
    Number,
    validate,
)


class Layer(BasePathMixin):
    """This object represents a single layer in a color blending object.

    Parameters
    ----------
    colorblending : :obj:`carta.colorblending.ColorBlending`
        The color blending object.
    layer_id : integer
        The layer ID.

    Attributes
    ----------
    colorblending : :obj:`carta.colorblending.ColorBlending`
        The color blending object.
    layer_id : integer
        The layer ID.
    session : :obj:`carta.session.Session`
        The session object associated with this layer.
    """

    def __init__(self, colorblending, layer_id):
        self.colorblending = colorblending
        self.layer_id = layer_id
        self.session = colorblending.session

        self._base_path = f"{self.colorblending._base_path}.frames[{layer_id}]"
        self._frame = Macro("", self._base_path)

    @classmethod
    def from_list(cls, colorblending, layer_ids):
        """
        Create a list of Layer objects from a list of layer IDs.

        Parameters
        ----------
        colorblending : :obj:`carta.colorblending.ColorBlending`
            The color blending object.
        layer_ids : list of integer
            The layer IDs.

        Returns
        -------
        list of :obj:`carta.colorblending.Layer`
            A list of new Layer objects.
        """
        return [cls(colorblending, layer_id) for layer_id in layer_ids]

    def __repr__(self):
        """A human-readable representation of this object."""
        session_id = self.session.session_id
        cb_imageview_id = self.colorblending.imageview_id
        cb_name = self.colorblending.file_name
        repr_content = [
            f"{session_id}:{cb_imageview_id}:{cb_name}",
            f"{self.layer_id}:{self.file_name}",
        ]
        return ":".join(repr_content)

    @property
    def file_name(self):
        """The name of the image.

        Returns
        -------
        string
            The image name.
        """
        return self.get_value("frameInfo.fileInfo.name")

    @property
    def image_id(self):
        """The ID of the image.

        Returns
        -------
        integer
            The image ID.
        """
        return self.get_value("frameInfo.fileId")

    @validate(Number(0, 1))
    def set_alpha(self, alpha):
        """Set the alpha value for the layer in the color blending.

        Parameters
        ----------
        alpha : {0}
            The alpha value.
        """
        self.colorblending.call_action("setAlpha", self.layer_id, alpha)

    @validate(Constant(Colormap), Boolean())
    def set_colormap(self, colormap, invert=False):
        """Set the colormap for the layer in the color blending.

        Parameters
        ----------
        colormap : {0}
            The colormap.
        invert : {1}
            Whether the colormap should be inverted. This is false by default.
        """
        self.call_action("renderConfig.setColorMap", colormap)
        self.call_action("renderConfig.setInverted", invert)


class ColorBlending(BasePathMixin):
    """This object represents a color blending image in a session.

    Parameters
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this color blending.
    store_id : integer
        The color blending store ID of the color blending image.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this color blending.
    store_id : integer
        The color blending store ID of the color blending image.
    """

    # Mirrors ColorBlendingStore.DEFAULT_LAYER_LIMIT in carta-frontend.
    MAX_INITIAL_LAYERS = 10

    def __init__(self, session, store_id):
        self.session = session
        self.store_id = store_id

        path = "imageViewConfigStore.colorBlendingImageMap"
        self._base_path = f"{path}[{self.store_id}]"
        self._frame = Macro("", self._base_path)

    @classmethod
    def _validate_initial_layer_count(cls, layer_count):
        if layer_count > cls.MAX_INITIAL_LAYERS:
            raise ValueError(
                "Color blending initialization supports at most "
                f"{cls.MAX_INITIAL_LAYERS} images (the base layer plus "
                f"{cls.MAX_INITIAL_LAYERS - 1} matched images)."
            )

    @classmethod
    def from_imageview_id(cls, session, imageview_id):
        """Create a color blending object from an image view ID.

        Parameters
        ----------
        session : :obj:`carta.session.Session`
            The session object.
        imageview_id : integer
            The image view ID, the index of the image within the list of
            currently open images, of the color blending image.

        Returns
        -------
        :obj:`carta.colorblending.ColorBlending`
            A new color blending object.
        """
        # Find the store ID for the given image view ID
        path = f"imageViewConfigStore.imageList[{imageview_id}]"
        image_type = session.get_value(f"{path}.type")
        if image_type != ImageType.COLOR_BLENDING:
            raise ValueError(
                "imageview_id does not refer to a color blending image."
            )
        store_id = session.get_value(f"{path}.store.id")
        return cls(session, store_id)

    @classmethod
    def from_images(cls, session, images):
        """Create a color blending object from a list of images.

        Parameters
        ----------
        session : :obj:`carta.session.Session`
            The session object.
        images : list of :obj:`carta.image.Image`
            The images to be blended.

        Returns
        -------
        :obj:`carta.colorblending.ColorBlending`
            A new color blending object.

        Raises
        ------
        ValueError
            If more images are provided than the frontend can include when
            initializing the color blending layers.
        """
        cls._validate_initial_layer_count(len(images))

        # Set the first image as the spatial reference
        session.call_action("setSpatialReference", images[0]._frame, False)
        # Align the other images to the spatial reference
        for image in images[1:]:
            success = image.call_action(
                "setSpatialReference", images[0]._frame
            )
            if not success:
                name = image.file_name
                raise CartaActionFailed(
                    f"Failed to set spatial reference for image {name}."
                )

        command = "imageViewConfigStore.createColorBlending"
        store_id = session.call_action(command, return_path="id")
        colorblending = cls(session, store_id)

        # The frontend initializes color blending from the current spatial
        # reference's secondarySpatialImages, which can include frames matched
        # before this helper was called. Rebuild the non-base layers so the
        # blend contains exactly the images requested here without clearing the
        # session-wide spatial matching state.
        for _ in colorblending.layer_list()[1:]:
            colorblending.delete_layer(1)
        for image in images[1:]:
            colorblending.add_layer(image)

        return colorblending

    @classmethod
    def from_files(cls, session, files, append=False):
        """Create a color blending object from a list of files.

        Parameters
        ----------
        session : :obj:`carta.session.Session`
            The session object.
        files : list of string
            The files to be blended.
        append : bool
            Whether the images should be appended to existing images.
            By default this is ``False`` and any existing open images
            are closed.

        Returns
        -------
        :obj:`carta.colorblending.ColorBlending`
            A new color blending object.
        """
        cls._validate_initial_layer_count(len(files))
        images = session.open_images(files, append=append)
        return cls.from_images(session, images)

    def __repr__(self):
        """A human-readable representation of this color blending object."""
        session_id = self.session.session_id
        return f"{session_id}:{self.imageview_id}:{self.file_name}"

    @property
    def _base_frame(self):
        return Image(self.session, self.get_value("frames[0].id"))

    @property
    def file_name(self):
        """The name of the image.

        Returns
        -------
        string
            The image name.
        """
        return self.get_value("filename")

    @property
    def imageview_id(self):
        """The image view ID of the color blending image.

        Returns
        -------
        integer
            The image view ID.
        """
        path = "imageViewConfigStore.imageList"
        length = self.session.get_value(f"{path}.length")
        for idx in range(length):
            entry = f"{path}[{idx}]"
            if (
                self.session.get_value(f"{entry}.type")
                == ImageType.COLOR_BLENDING
                and self.session.get_value(f"{entry}.store.id")
                == self.store_id
            ):
                return idx
        raise RuntimeError(
            "Could not find this color blending image in the image list."
        )

    @property
    def alpha(self):
        """The alpha value list for the color blending layers.

        Returns
        -------
        list of float
            The alpha values.
        """
        return self.get_value("alpha")

    def make_active(self):
        """Make this the active image."""
        self.session.call_action("setActiveImageByIndex", self.imageview_id)

    def layer_list(self):
        """
        Returns a list of Layer objects, each representing a layer in
        this color blending object.

        Returns
        -------
        list of :obj:`carta.colorblending.Layer`
            A list of Layer objects.
        """
        layer_count = self.get_value("frames.length")
        return Layer.from_list(self, list(range(layer_count)))

    def add_layer(self, image):
        """Add a new layer to the color blending.

        Parameters
        ----------
        image : :obj:`carta.image.Image`
            The image to add.
        """
        self.call_action("addSelectedFrame", image._frame)

    @validate(Number(0, None))
    def delete_layer(self, layer_index):
        """Delete a layer from the color blending.

        Parameters
        ----------
        layer_index : {0}
            The layer index. The base layer (layer_index = 0) cannot
            be deleted.
        """
        if layer_index == 0:
            raise ValueError("The base layer cannot be deleted.")
        self.call_action("deleteSelectedFrame", layer_index - 1)

    @validate(InstanceOf(Image), Number(1, None))
    def set_layer(self, image, layer_index):
        """Set a layer at a specified index in the color blending.

        Parameters
        ----------
        image : {0}
            The image to set.
        layer_index : {1}
            The layer index. The base layer (layer_index = 0) cannot
            be set.
        """
        self.call_action("setSelectedFrame", layer_index - 1, image._frame)

    @validate(IterableOf(Number(0, None), min_size=1))
    def set_layer_sequence(self, layer_indices):
        """Set which layers are included in the color blending and in what
        order.

        Parameters
        ----------
        layer_indices : {0}
            The layer indices to keep, in the desired order. The first index
            must be the base layer (index = 0). Existing alpha values are
            preserved.
        """
        current_layers = self.layer_list()
        max_current_layer_index = len(current_layers) - 1
        if any(
            layer_index > max_current_layer_index
            for layer_index in layer_indices
        ):
            raise ValueError(
                "layer_indices contains a layer index which does not exist."
            )

        if layer_indices[0] != 0:
            raise ValueError(
                "layer_indices must start with the base layer index 0."
            )

        if 0 in layer_indices[1:]:
            raise ValueError(
                "layer_indices must contain the base layer index 0 only once, "
                "as the first index."
            )

        if len(layer_indices) != len(set(layer_indices)):
            raise ValueError(
                "layer_indices must not contain duplicate layer indices."
            )

        current_layer_indices = list(range(len(current_layers)))
        if list(layer_indices) == current_layer_indices:
            return

        current_alpha_values = self.alpha
        target_layer_states = [
            (
                Image(self.session, current_layers[layer_index].image_id),
                current_alpha_values[layer_index],
            )
            for layer_index in layer_indices[1:]
        ]

        # Delete all layers except the base layer
        for _ in current_layers[1:]:
            # Delete layer at index 1 (the first non-base layer);
            # after deletion, the previous layer at index 2 shifts to index 1
            self.delete_layer(1)

        for target_layer_index, (image, alpha) in enumerate(
            target_layer_states, start=1
        ):
            self.add_layer(image)
            Layer(self, target_layer_index).set_alpha(alpha)

    @validate(Coordinate(), Coordinate())
    def set_center(self, x, y):
        """Set the center position, in image or world coordinates.

        World coordinates are interpreted according to the session's globally
        set coordinate system and any custom number formats. These can be
        changed using
        :obj:`carta.wcs_overlay.Global.set_coordinate_system` and
        :obj:`carta.wcs_overlay.Numbers.set_format`.

        Coordinates must either both be image coordinates or match the current
        number formats. Numbers are interpreted as image coordinates, and
        numeric strings with no units are interpreted as degrees.

        Parameters
        ----------
        x : {0}
            The X position.
        y : {1}
            The Y position.

        Raises
        ------
        ValueError
            If a mix of image and world coordinates is provided, if world
            coordinates are provided and the image has no valid WCS
            information, or if world coordinates do not match the session-wide
            number formats.
        """
        self._base_frame.set_center(x, y)

    @validate(Number(), Boolean())
    def set_zoom_level(self, zoom, absolute=True):
        """Set the zoom level.

        TODO: explain this more rigorously.

        Parameters
        ----------
        zoom : {0}
            The zoom level.
        absolute : {1}
            Whether the zoom level should be treated as absolute. By default
            it is adjusted by a scaling factor.
        """
        self._base_frame.set_zoom_level(zoom, absolute)

    @validate(Constant(ColormapSet))
    def set_colormap_set(self, colormap_set):
        """Set the colormap set for the color blending.

        Parameters
        ----------
        colormap_set : {0}
            The colormap set.
        """
        self.call_action("applyColormapSet", colormap_set)

    @validate(IterableOf(Number(0, 1)))
    def set_alpha(self, alpha_list):
        """Set the alpha value for the color blending layers.

        Parameters
        ----------
        alpha_list : {0}
            The alpha values.
        """
        layer_list = self.layer_list()
        if len(alpha_list) != len(layer_list):
            raise ValueError(
                f"alpha_list length ({len(alpha_list)}) does not match "
                f"the number of layers ({len(layer_list)})."
            )
        for alpha, layer in zip(alpha_list, layer_list):
            layer.set_alpha(alpha)

    @validate(Boolean())
    def set_raster_visible(self, state):
        """Set the raster component visibility.

        Parameters
        ----------
        state : {0}
            The desired visibility state.
        """
        is_visible = self.get_value("rasterVisible")
        if is_visible != state:
            self.call_action("toggleRasterVisible")

    @validate(Boolean())
    def set_contour_visible(self, state):
        """Set the contour component visibility.

        Parameters
        ----------
        state : {0}
            The desired visibility state.
        """
        is_visible = self.get_value("contourVisible")
        if is_visible != state:
            self.call_action("toggleContourVisible")

    @validate(Boolean())
    def set_vector_overlay_visible(self, state):
        """Set the vector overlay visibility.

        Parameters
        ----------
        state : {0}
            The desired visibility state.
        """
        is_visible = self.get_value("vectorOverlayVisible")
        if is_visible != state:
            self.call_action("toggleVectorOverlayVisible")

    def close(self):
        """Close this color blending object."""
        self.session.call_action(
            "imageViewConfigStore.removeColorBlending", self._frame
        )
