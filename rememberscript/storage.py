"""Persistent storage for RememberMachine"""
import os
import asyncio
import pickle
import inspect
from functools import partial
from collections import MutableMapping
from typing import MutableMapping as MutableMappingType
from typing import Any
from types import FunctionType

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

def _write(data, filename):
    with open(filename, 'wb') as f:
        f.write(data)

def _load(filename):
    if not os.path.exists(filename):
        return

    with open(filename, 'rb') as f:
        return f.read()

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
            data = await asyncio.get_event_loop().run_in_executor(
                None, partial(_load, self.filename))
            if data is not None:
                self._dict.update(pickle.loads(data).items())

    async def sync(self):
        """Sync to filename"""
        if not self.filename:
            return
        # Remove private variables, functions and classes and any other
        # unpickleable object
        sync_vars = {key: var for key, var in self._dict.items() if _sync_var(key, var)}

        # Dump to file (note: don't await)
        asyncio.get_event_loop().run_in_executor(
            None, partial(_write, pickle.dumps(sync_vars), self.filename))

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
