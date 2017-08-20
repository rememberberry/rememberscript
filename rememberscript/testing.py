import json
import pytest
from types import FunctionType

async def assert_replies(replies, *correct, debug_print=False):
    for reply in correct:
        n = json.loads(await replies.__anext__())
        if reply is None:
            continue
        if isinstance(reply, str):
            assert n['msg'] == reply, reply
        if isinstance(reply, FunctionType):
            assert reply(n), '%s %s' % (n, str(reply))
        if debug_print:
            print(n)
    with pytest.raises(StopAsyncIteration):
        await replies.__anext__()
