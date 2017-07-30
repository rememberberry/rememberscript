import re
from types import FunctionType

EVAL_START = '{{'
EVAL_END = '}}'
EXEC_START = '[['
EXEC_END = ']]'

def is_str_empty(string):
    """Check whether string is empty (except for execs and evals)"""
    return ((string.startswith(EVAL_START) or string.startswith(EXEC_START)) and
            (string.endswith(EVAL_END) or string.endswith(EXEC_END)))

esc = lambda x: re.escape(x)

async def execute_string(string, storage):
    """Executes {% %} blocks in the string and removes them"""
    execs = re.compile('%s(.*?)%s' % (esc(EXEC_START), esc(EXEC_END))).findall(string)
    for ex in execs:
        # Exec with session storage to store local variables
        exec(ex, {}, storage)

        # Remove code block
        exec_block = EXEC_START + ex + EXEC_END
        start = string.index(exec_block)
        end = start + len(exec_block)
        string = string[:start] + string[end:]
    return string


async def evaluate_split_string(string, storage):
    """Evaluates {@ @} blocks and yields the string parts and evaluated
    results in order"""
    evals = re.compile('%s(.*?)%s' % (esc(EVAL_START), esc(EVAL_END))).findall(string)
    for ev in evals:
        # Eval with session storage to provide local variables
        eval_result = eval(ev, {}, storage)

        # yield the string up to the eval block and the eval result
        eval_block = EVAL_START + ev + EVAL_END
        start = string.index(eval_block)
        end = start + len(eval_block)
        if start > 0:
            yield string[:start]
        if eval_result is not None:
            yield eval_result
        string = string[end:]

    # yield what's left of the string
    if len(string) > 0:
        yield string


async def process_string(string, storage=None):
    """Processes code blocks in a string and yields results by:
        1. Exec code wrapped in '{%...%}' and remove code from remaining string
        2. Evaluate code wrapped in '{@...@}' and substitute in the 
           original string and yield it/them

    storage -- optional storage used for execs and evals, defaults to {}
    """
    storage = {} if storage is None else storage
    is_empty_str = is_str_empty(string)
    string = await execute_string(string, storage)

    if len(string) == 0:
        return

    parts = [part async for part in evaluate_split_string(string, storage)]
    if len(parts) == 1 and isinstance(parts[0], FunctionType):
        func = parts[0]
        async for result in func(storage):
            if result is not None:
                yield result
    elif len(parts) == 1:
        yield parts[0]
    else:
        parts = map(lambda x: str(x) if not isinstance(x, str) else x, parts)
        yield ''.join(parts)


async def match_trigger(string, trigger, storage=None):
    storage = {} if storage is None else storage
    trigger = await execute_string(trigger, storage)
    parts = [part async for part in evaluate_split_string(trigger, storage)]
    if len(parts) == 1 and isinstance(parts[0], bool):
        return parts[0]

    regex_parts = []
    match_functions = []
    for part in parts:
        if isinstance(part, FunctionType):
            regex_parts.append('(?P<call%i>.*?)' % len(match_functions))
            match_functions.append(part)
        elif isinstance(part, list):
            # Note: the '?:' marks the group as non-capture
            # since we're not interested in what was matched
            regex_parts.append('(?:' + '|'.join(part) + ')')
        else:
            regex_parts.append(str(part))

    regex = re.compile(''.join(regex_parts))
    m = regex.match(string)
    if m is None:
        return False

    # Check that the matching functions succeed
    for i, fun in enumerate(match_functions):
        match = m.group('call%i' % i)
        if not await fun(match, storage):
            return False

    # Add the matches to storage as match0 ... matchN-1
    for i in range(0, len(m.groups())):
        storage['match%i' % i] = m.group(i+1)

    # Add any named groups to storage
    storage.update(m.groupdict().items())

    return True
