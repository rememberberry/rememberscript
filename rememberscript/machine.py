import traceback
from types import FunctionType
from .strings import process_string, match_trigger

def get_list(obj, key):
    if key not in obj:
        return []
    return obj[key] if isinstance(obj[key], list) else [obj[key]]

class RememberMachine:
    """A finite state machine (FSM) that is initialized with a script,
    receives messages and yields replies. This class is build using
    concurrent coroutines for use with asyncio. """
    def __init__(self, script, storage=None):
        self._script = script
        self._storage = storage or {}

    def init(self):
        """Sets the current state to the init state
        Note: one never enters into the init state, we just are in it,
        therefore pre-reply-actions and state triggers dont apply"""
        self.curr_state = self._get_state('init')
        assert self.curr_state is not None

    async def reply(self, msg):
        """Processes a message and yields any number of replies in this way:
        1. Run any =exit actions in the current state
        2. Evaluates all global and local triggers and finds the highest
           likelihood one
        3. Run any = action on the transition
        4. Assign new state as the curr state
        5. Run any =enter actions on the new state

        Note: this is an async generator coroutine"""
        self._storage['msg'] = msg

        for action in get_list(self.curr_state, '=exit'):
            async for msg in self._evaluate_action(action):
                yield msg

        transitions = [(await self._evaluate_trigger(t, msg), *rest) 
                       for t, *rest in self._get_triggers()]
        _, next_state, transition_actions = max(transitions, key=lambda x: x[0])
        for action in transition_actions:
            async for msg in self._evaluate_action(action):
                yield msg

        self.curr_state = self._get_state(next_state)
        for action in get_list(self.curr_state, '=enter'):
            async for msg in self._evaluate_action(action):
                yield msg

    def _get_state(self, name):
        if name == 'next':
            # Reserved keyword for next state in script
            return self._script[self._script.index(self.curr_state)+1]
        if name == 'prev':
            # Reserved keyword for next state in script
            return self._script[self._script.index(self.curr_state)-1]
        if name == 'back':
            # TODO: implement context stack
            raise NotImplementedError

        for state in self._script:
            if state.get('name', None) == name:
                return state
        return None

    def _get_triggers(self):
        """Returns triples of local and global triggers 
        with (trigger, state_name, actions)"""
        # Get triggers local to this state
        local_transitions = get_list(self.curr_state, '=>')
        local_triggers = [(trigger, trans.get('to', 'next'), get_list(trans, '='))
                          for trans in local_transitions
                          for trigger in get_list(trans, '?')]

        # Get triggers reachable from anywhere
        global_triggers = [(trigger, state.get('name', 'next'), [])
                           for state in self._script
                           for trigger in get_list(state, '?')]

        return local_triggers + global_triggers

    async def _evaluate_action(self, action):
        async for msg in process_string(action, self._storage):
            yield msg

    async def _evaluate_trigger(self, trigger, msg):
        self._storage['weight'] = 1.0 # set default weight
        match = await match_trigger(msg, trigger, self._storage)
        weight = self._storage['weight']
        del self._storage['weight']

        assert isinstance(match, bool), match
        return weight if match else 0.0
