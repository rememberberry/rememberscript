"""Persistent storage for RememberMachine"""
import os
import pickle
from collections import MutableMapping
from typing import MutableMapping as MutableMappingType
from typing import Any

StorageType = MutableMappingType[str, Any]

class Storage(MutableMapping):
    """A storage class that behaves like dict, but persists public entries to file
    Note: private entries start with an _ (underscore)"""
    def __init__(self, filename):
        self._filename = filename
        if os.path.exists(filename):
            self._dict = pickle.load(filename)
        else:
            self._dict = {}

    def __delitem__(self, key):
        del self._dict[key]

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, val):
        self._dict[key] = val

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def sync(self):
        """Sync to file"""
        # Remove private variables, functions and classes and any other
        # unpickleable object

        # Dump to file
        pickle.dump(self._dict, self._filename)
