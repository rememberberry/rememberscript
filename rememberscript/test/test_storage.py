import os
import pytest
from rememberscript.storage import FileStorage

@pytest.mark.asyncio
async def test_filestorage():
    filename = 'test.bin'
    if os.path.exists(filename):
        os.remove(filename)
    storage = FileStorage(filename)
    storage['hello'] = 3
    storage['_hello'] = 3
    def test_fun():
        pass
    storage['test_fun'] = test_fun
    class TestClass:
        pass
    storage['TestClass'] = TestClass
    storage['pytest'] = pytest

    await storage.sync()

    storage = FileStorage(filename)
    await storage.load()
    assert storage.get('hello', None) == 3
    assert '_hello' not in storage
    assert 'test_fun' not in storage
    assert 'TestClass' not in storage
    assert 'pytest' not in storage
    os.remove(filename)
