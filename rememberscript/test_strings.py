"""Test the string functions"""
import pytest
import os
from rememberscript.strings import process_string, match_trigger

async def dummy(storage):
    yield 'hello'
    yield 'world'

@pytest.mark.asyncio
async def test_string_processing():
    storage = {}
    result = [a async for a in process_string('hello world', storage)]
    assert len(result) == 1 and result[0] == 'hello world'
    assert len(storage) == 0

    result = [a async for a in process_string('hello {@42@}', storage)]
    assert len(result) == 1 and result[0] == 'hello 42'
    assert len(storage) == 0

    result = [a async for a in process_string('{@42@}', storage)]
    assert len(result) == 1 and result[0] == 42
    assert len(storage) == 0

    result = [a async for a in process_string('{@"hello world"@} hello {@42@}',
                                              storage)]
    assert len(result) == 1 and result[0] == 'hello world hello 42'
    assert len(storage) == 0

    storage = {}
    result = [a async for a in process_string('{%hello = 42%}', storage)]
    assert len(result) == 0
    assert storage.get('hello', None) == 42

    storage = {}
    result = [a async for a in process_string('{%hello = 4%}{%world = 2%}', storage)]
    assert len(result) == 0
    assert storage.get('hello', None) == 4 and storage.get('world') == 2

    storage = {}
    result = [a async for a in process_string('hello{%hello = 42%}world', storage)]
    assert len(result) == 1 and result[0] == 'helloworld'
    assert storage.get('hello', None) == 42

    result = [a async for a in process_string('{%hello = 4%}{@"hello world"@} hello {@42@}{%world=2%}',
                                              storage)]
    assert len(result) == 1 and result[0] == 'hello world hello 42'
    assert storage.get('hello', None) == 4 and storage.get('world', None) == 2

    result = [a async for a in process_string('{@dummy@}', {'dummy': dummy})]
    assert len(result) == 2 and result[0] == 'hello' and result[1] == 'world'


async def my_matching_fn(string, storage):
    return string == 'hello'


@pytest.mark.asyncio
async def test_match_trigger():
    # Special case with just one evaluated bool result
    assert await match_trigger('hello world', '{@True@}') == True
    assert await match_trigger('hello world', '{@False@}') == False

    # Matching with evaluated strings
    assert await match_trigger('hello world', 'hello world') == True
    assert await match_trigger('world hello', 'hello world') == False
    assert await match_trigger('hello', '{@"hello"@}') == True
    assert await match_trigger('hello world', 'hello {@"world"@}') == True

    # Matching against arrays
    assert await match_trigger('hello', '{@words@}', {'words': ['hello']}) == True
    words = ['hello', 'world']
    assert await match_trigger('hello world', '{@words@} {@words@}', {'words': words}) == True

    # Matching against regex
    storage = {}
    assert await match_trigger('hello world', '(\w+) world', storage) == True
    assert storage.get('match0', None) == 'hello'

    # Matching against regex named group
    storage = {}
    assert await match_trigger('hello world', '(?P<myvar>\w+) world', storage) == True
    assert storage.get('myvar', None) == 'hello'

    # Match using python functions
    storage = {'my_matching_fn': my_matching_fn}
    assert await match_trigger('hello world', '{@my_matching_fn@} world', storage) == True

    # Test set weight
    storage = {}
    assert await match_trigger('hello world', 'hello world{%weight=2%}', storage) == True
    assert storage.get('weight', None) == 2
