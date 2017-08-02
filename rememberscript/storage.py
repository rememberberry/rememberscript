"""Persistent storage for RememberMachine"""
import os
import pickle
import inspect
from collections import MutableMapping
from typing import MutableMapping as MutableMappingType
from typing import Any
from types import FunctionType
import aiofiles

StorageType = MutableMappingType[str, Any]

def _sync_var(key, var):
    """Determines whether to sync a key-value pair or not
    Don't sync variables that
        * have private names (leading underscore)
        * is a function
        * is a class
        * is a module
    """
    return (not key.startswith('_') and
            not isinstance(var, FunctionType) and
            not inspect.isclass(var) and
            not inspect.ismodule(var))

class FileStorage(MutableMapping):
    """A storage class that behaves like dict, but persists public entries to file
    Note: private entries start with an _ (underscore)"""
    def __init__(self, filename):
        self._filename = filename
        self._dict = {}

    async def load(self):
        if os.path.exists(self._filename):
            async with aiofiles.open(self._filename, mode='rb') as f:
                self._dict = pickle.loads(await f.read())

    async def sync(self):
        """Sync to file"""
        # Remove private variables, functions and classes and any other
        # unpickleable object
        sync_vars = {key: var for key, var in self._dict.items() if _sync_var(key, var)}

        # Dump to file
        async with aiofiles.open(self._filename, mode='wb') as f:
            await f.write(pickle.dumps(sync_vars))

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
