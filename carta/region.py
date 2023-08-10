"""This module contains a region class which represents a single region loaded in the session, and a region set class which represents all regions associated with an image, which may be shared by all spatially matched regions.

Region objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.image.Image` object.
"""
from .util import Macro, BasePathMixIn


class Region(BasePathMixIn):
    """Utility object which provides access to one region associated with an image.

    # TODO find out what happens to region IDs when you match/unmatch or delete.
    """

    def __init__(self, image, region_id):
        self.image = image
        self.session = image.session
        self.region_id = region_id

        self._base_path = f"{image._base_path}.regionSet.regionMap[{region_id}]"
        self._region = Macro("", self._base_path)

    # @classmethod
    # def new(???):
        # TODO create new region -- low-level method; use generic new region method directly?
