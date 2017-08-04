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
    def __init__(self, filename=None):
        self.filename = filename
        self._dict = {}

    async def load(self):
        """Sync from filename, overwrites exisiting dict entries but doens't
        delete existing"""
        if not self.filename:
            return
        if os.path.exists(self.filename):
            async with aiofiles.open(self.filename, mode='rb') as f:
                self._dict.update(pickle.loads(await f.read()).items())

    async def sync(self):
        """Sync to filename"""
        if not self.filename:
            return
        # Remove private variables, functions and classes and any other
        # unpickleable object
        sync_vars = {key: var for key, var in self._dict.items() if _sync_var(key, var)}

        # Dump to file
        async with aiofiles.open(self.filename, mode='wb') as f:
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

    def __repr__(self):
        return repr(self._dict)

    def __str__(self):
        return str(self._dict)
