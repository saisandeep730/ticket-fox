"""Source adapters: BookMyShow and District, behind a common interface."""

from .base import SourceAdapter
from .bookmyshow import BookMyShowAdapter
from .district import DistrictAdapter

__all__ = ["SourceAdapter", "BookMyShowAdapter", "DistrictAdapter"]