"""Test the RememberMachine class"""
import pytest
import os
from rememberscript import RememberMachine, load_scripts_dir, validate_script

def get_machine(name):
    path = os.path.join(os.path.dirname(__file__), 'scripts/%s/' % name)
    storage = {}
    script = load_scripts_dir(path, storage)
    validate_script(script)
    m = RememberMachine(script, storage)
    m.init()
    return m

@pytest.mark.asyncio
async def test_bot1():
    """Test a simple login script"""
    storage = {}
    m = get_machine('script1')
    assert len(m._get_triggers()) == 2

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
    storage = {}
    m = get_machine('script2')
    assert len(m._get_triggers()) == 2

    replies = m.reply('')
    assert await replies.__anext__() == 'state2'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()

@pytest.mark.asyncio
async def test_next_prev():
    """Test trigger to next"""
    storage = {}
    m = get_machine('script3')

    replies = m.reply('')
    assert await replies.__anext__() == 'state1'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()

    replies = m.reply('')
    assert await replies.__anext__() == 'to init'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()

@pytest.mark.asyncio
async def test_stories():
    """Test trigger to next"""
    storage = {}
    m = get_machine('script4')

    replies = m.reply('')
    assert await replies.__anext__() == 'in other'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()

    replies = m.reply('')
    assert await replies.__anext__() == 'in init'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()
    replies = m.reply('')
    assert await replies.__anext__() == 'going to foo'
    assert await replies.__anext__() == 'in foo'
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()
