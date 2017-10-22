"""Persistent storage for RememberMachine"""
import os
import asyncio
import pickle
import json
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

def _dump(filename, data, mode=''):
    with open(filename, 'w'+mode) as f:
        f.write(data)

def _load(filename, mode=''):
    with open(filename, 'r'+mode) as f:
        return f.read()


class FileStorage(MutableMapping):
    """A storage class that behaves like dict, but persists public entries to file
    Note: private entries start with an _ (underscore)"""
    def __init__(self, filename=None, load_func=None, dump_func=None,
                 serializer=pickle, mode='b'):
        self.filename = filename
        self._dict = {}
        self._load_func = load_func or _load
        self._dump_func = dump_func or _dump
        self._serializer = serializer
        self._mode = mode

    async def load(self):
        """Sync from filename, overwrites exisiting dict entries but doesn't
        delete existing"""
        if not self.filename:
            return

        if inspect.iscoroutinefunction(self._load_func):
            data = await self._load_func(self.filename, self._mode)
        else:
            data = await asyncio.get_event_loop().run_in_executor(
                None, partial(self._load_func, self.filename, self._mode))

        if data is not None:
            self._dict.update(self._serializer.loads(data).items())

    async def sync(self):
        """Sync to filename"""
        if not self.filename:
            return

        # First run any sync hooks on the values
        for key, var in self._dict.items():
            if not hasattr(var, '__sync_hook__'):
                continue

            if inspect.iscoroutinefunction(var.__sync_hook__):
                await var.__sync_hook__()
            else:
                var.__sync_hook__()

        # Remove private variables, functions and classes and any other
        # unserializable object
        sync_vars = {key: var for key, var in self._dict.items() if _sync_var(key, var)}

        # Dump to file
        data = self._serializer.dumps(sync_vars)
        if inspect.iscoroutinefunction(self._dump_func):
            await self._dump_func(self.filename, data, self._mode)
        else:
            await asyncio.get_event_loop().run_in_executor(
                None, partial(self._dump_func, self.filename, data, self._mode))

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
