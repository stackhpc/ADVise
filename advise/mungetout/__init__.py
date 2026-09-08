# -*- coding: utf-8 -*-
import importlib.metadata

try:
    __version__ = importlib.metadata.version(__name__)
except:  # noqa E722
    __version__ = 'unknown'
