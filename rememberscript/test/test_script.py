"""Test the RememberMachine class"""
import pytest
import os
from rememberscript import RememberMachine, load_scripts_dir, validate_script
from rememberscript.testing import assert_replies

async def get_machine(name):
    path = os.path.join(os.path.dirname(__file__), 'scripts/%s/' % name)
    storage = {}
    script = load_scripts_dir(path, storage)
    await validate_script(script)
    m = RememberMachine(script, storage)
    m.init()
    return m


@pytest.mark.asyncio
async def test_bot1():
    """Test a simple login script"""
    storage = {}
    m = await get_machine('script1')

    await assert_replies(m.reply(''), 'Welcome!', 'Set a username:')
    await assert_replies(m.reply('user'), 'Thanks, we\'re all set up', 'Lets study')

    assert 'username' in m._storage
    assert m._storage['username'] == 'user'


@pytest.mark.asyncio
async def test_weight():
    """Test trigger weights"""
    storage = {}
    m = await get_machine('script2')

    await assert_replies(m.reply(''), 'state2')


@pytest.mark.asyncio
async def test_next_prev():
    """Test trigger to prev"""
    storage = {}
    m = await get_machine('script3')

    await assert_replies(m.reply(''), 'state1')
    await assert_replies(m.reply(''), 'to init')


@pytest.mark.asyncio
async def test_stories():
    """Test trigger to next"""
    storage = {}
    m = await get_machine('script4')

    await assert_replies(m.reply(''), 'in other')
    await assert_replies(m.reply(''), 'in init')
    await assert_replies(m.reply(''), 'going to foo', 'in foo')

@pytest.mark.asyncio
async def test_return_to():
    """Test trigger to return to"""
    storage = {}
    m = await get_machine('script5')

    await assert_replies(m.reply(''), 'in other')
    await assert_replies(m.reply(''), 'in foo')


@pytest.mark.asyncio
async def test_should_trigger():
    """Test should_trigger"""
    storage = {}
    m = await get_machine('script6')

    with pytest.raises(AssertionError):
        storage = {}
        m = await get_machine('script7')
