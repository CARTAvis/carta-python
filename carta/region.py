"""This module contains a region class which represents a single region loaded in the session, and a region set class which represents all regions associated with an image, which may be shared by all spatially matched regions.

Region objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.image.Image` object.
"""
from .util import BasePathMixin


class Region(BasePathMixIn):
    """Utility object which provides access to one region associated with an image.
    
    # TODO find out what happens to region IDs when you match/unmatch or delete.
    """
    def __init__(self, image, index, region_id):
        self.image = image
        self.session = image.session
        self.index = index # TODO does it actually make sense to keep this?
        self.region_id = region_id # TODO does it actually make sense to keep this?
        
        
        self._region = Macro("", self._base_path)

    @property
    def _base_path(self):
        # TODO this is a problem; we can attempt a horrendous hackaround:
        # get all region IDs
        # then look up the index on the Python side
        
        return f"{image._base_path}.regionSet.regions[{index}]"
    

        
