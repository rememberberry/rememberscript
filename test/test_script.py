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


async def replies_test(replies, *correct):
    for reply in correct:
        assert await replies.__anext__() == reply, reply
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()


@pytest.mark.asyncio
async def test_bot1():
    """Test a simple login script"""
    storage = {}
    m = get_machine('script1')
    assert len(m._get_triggers()) == 2

    await replies_test(m.reply(''), 'Welcome!', 'Set a username:')
    await replies_test(m.reply('user'), 'Thanks, we\'re all set up', 'Lets study')

    assert 'username' in m._storage
    assert m._storage['username'] == 'user'


@pytest.mark.asyncio
async def test_weight():
    """Test trigger weights"""
    storage = {}
    m = get_machine('script2')
    assert len(m._get_triggers()) == 2

    await replies_test(m.reply(''), 'state2')


@pytest.mark.asyncio
async def test_next_prev():
    """Test trigger to next"""
    storage = {}
    m = get_machine('script3')

    await replies_test(m.reply(''), 'state1')
    await replies_test(m.reply(''), 'to init')


@pytest.mark.asyncio
async def test_stories():
    """Test trigger to next"""
    storage = {}
    m = get_machine('script4')

    await replies_test(m.reply(''), 'in other')
    await replies_test(m.reply(''), 'in init')
    await replies_test(m.reply(''), 'going to foo', 'in foo')
