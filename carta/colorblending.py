"""This module contains functionality for interacting with color blending images and their layers."""

from .constants import Colormap, ColormapSet, ImageType, SpatialAxis
from .image import Image
from .image_base import ImageBase
from .util import BasePathMixin, CartaScriptingException, Macro
from .validation import (
    Boolean,
    Constant,
    Coordinate,
    InstanceOf,
    IterableOf,
    Number,
    Size,
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

    @property
    def image_view_order(self):
        """The image-view order of this layer's underlying frame.

        This is the position of the underlying frame in the session's image
        list. A layer does not occupy its own position in the image list;
        its parent color blending does (see
        :obj:`carta.colorblending.ColorBlending.image_view_order`).

        Returns
        -------
        integer
            The image-view order of the underlying frame.

        Raises
        ------
        RuntimeError
            If no matching frame entry exists in the image list.
        """
        return self.session._find_image_view_order(
            ImageType.FRAME, self.file_id
        )

    def __repr__(self):
        """A human-readable representation of this layer."""
        cls = type(self).__name__
        cb_id = self.colorblending.color_blending_id

        try:
            order = self.image_view_order
        except (CartaScriptingException, RuntimeError):
            return (
                f"[Closed] {cls}(image_view_order=None, "
                f"color_blending_id={cb_id}, layer_id={self.layer_id})"
            )

        try:
            name = self.file_name
        except CartaScriptingException:
            return (
                f"[Closed] {cls}(image_view_order={order}, "
                f"color_blending_id={cb_id}, layer_id={self.layer_id})"
            )

        return (
            f"{cls}(image_view_order={order}, color_blending_id={cb_id}, "
            f"layer_id={self.layer_id}, file_name={name!r})"
        )

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
    def file_id(self):
        """The frontend file id of the layer's underlying image.

        Returns
        -------
        integer
            The file id.
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


class ColorBlending(ImageBase, BasePathMixin):
    """This object represents a color blending image in a session.

    Parameters
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this color blending.
    color_blending_id : integer
        The id of the backing ``ColorBlendingStore`` on the frontend.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this color blending.
    color_blending_id : integer
        The id of the backing ``ColorBlendingStore`` on the frontend.
    """

    _image_type = ImageType.COLOR_BLENDING

    def __init__(self, session, color_blending_id):
        super().__init__(session)
        self.color_blending_id = color_blending_id

        path = "imageViewConfigStore.colorBlendingImageMap"
        self._base_path = f"{path}[{self.color_blending_id}]"
        self._frame = Macro("", self._base_path)

    @property
    def _stable_id(self):
        return self.color_blending_id

    def __repr__(self):
        """A human-readable representation of this color blending object."""
        cls = type(self).__name__

        try:
            order = self.image_view_order
        except (CartaScriptingException, RuntimeError):
            return (
                f"[Closed] {cls}(image_view_order=None, "
                f"color_blending_id={self.color_blending_id})"
            )

        try:
            name = self.file_name
        except CartaScriptingException:
            return (
                f"[Closed] {cls}(image_view_order={order}, "
                f"color_blending_id={self.color_blending_id})"
            )

        return (
            f"{cls}(image_view_order={order}, "
            f"color_blending_id={self.color_blending_id}, "
            f"file_name={name!r})"
        )

    # METADATA

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

    # LAYERS

    @property
    def alpha(self):
        """The alpha value list for the color blending layers.

        Returns
        -------
        list of float
            The alpha values.
        """
        return self.get_value("alpha")

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
                Image(self.session, current_layers[layer_index].file_id),
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

    # NAVIGATION

    @validate(Coordinate(), Coordinate())
    def set_center(self, x, y):
        """Set the center position, in image or world coordinates.

        World coordinates are interpreted according to the session's globally
        set coordinate system and any custom number formats. These can be
        changed using
        :obj:`carta.session.wcs.global_.set_coordinate_system` and
        :obj:`carta.session.wcs.numbers.set_format`.

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

    @validate(Size(), Constant(SpatialAxis))
    def zoom_to_size(self, size, axis):
        """Zoom to the given size along the specified axis.

        Numbers are interpreted as pixel sizes. Numeric strings with no units are interpreted as arcseconds.

        Parameters
        ----------
        size : {0}
            The size to zoom to.
        axis : {1}
            The spatial axis to use.

        Raises
        ------
        ValueError
            If an angular size is provided and the image has no valid WCS information.
        """
        self._base_frame.zoom_to_size(size, axis)

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

    # RENDERING

    @validate(Constant(ColormapSet))
    def set_colormap_set(self, colormap_set):
        """Set the colormap set for the color blending.

        Parameters
        ----------
        colormap_set : {0}
            The colormap set.
        """
        self.call_action("applyColormapSet", colormap_set)

    # VISIBILITY

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

    # CLOSE

    def close(self):
        """Close this color blending object."""
        self.session.call_action(
            "imageViewConfigStore.removeColorBlending", self._frame
        )
