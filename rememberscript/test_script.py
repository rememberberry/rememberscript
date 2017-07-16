"""Test the RememberMachine class"""
import pytest
import os
from rememberscript import RememberMachine, load_scripts_dir, validate_script

@pytest.mark.asyncio
async def test_bot1():
    """Test a simple login script"""
    path = os.path.join(os.path.dirname(__file__), 'scripts/script1/')
    storage = {}
    script = load_scripts_dir(path, storage)
    validate_script(script)
    m = RememberMachine(script, storage)
    m.init()
    assert len(m._get_triggers()) == 4

    replies = m.reply('')
    assert await replies.__anext__() == 'Welcome!'
    assert await replies.__anext__() == 'Set a username:'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()

    replies = m.reply('user')
    assert await replies.__anext__() == 'Thanks, we\'re all set up'
    assert await replies.__anext__() == 'Lets study'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()
    print(m._storage)
    assert 'username' in m._storage
    assert m._storage['username'] == 'user'

@pytest.mark.asyncio
async def test_weight():
    """Test trigger weights"""
    path = os.path.join(os.path.dirname(__file__), 'scripts/script2/')
    storage = {}
    script = load_scripts_dir(path, storage)
    validate_script(script)
    m = RememberMachine(script, storage)
    m.init()
    assert len(m._get_triggers()) == 2

    replies = m.reply('')
    assert await replies.__anext__() == 'state2'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()
