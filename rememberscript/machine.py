import traceback
from types import FunctionType
from .strings import process_string, match_trigger

def get_list(obj, key, default=[]):
    if key not in obj:
        return default
    return obj[key] if isinstance(obj[key], list) else [obj[key]]

class RememberMachine:
    """A finite state machine (FSM) that is initialized with a script,
    receives messages and yields replies. This class is build using
    concurrent coroutines for use with asyncio. """
    def __init__(self, script, storage=None):
        self._script = script
        self._storage = storage or {}
        self.curr_story = None
        self.curr_state = None
        self.story_state_stack = []

    def init(self):
        """Sets the current state to the init state
        Note: one never enters into the init state, we just are in it,
        therefore pre-reply-actions and state triggers dont apply"""
        self._set_state('init')
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

        self._set_state(next_state)
        for action in get_list(self.curr_state, '=enter'):
            async for msg in self._evaluate_action(action):
                yield msg

    def _set_state(self, name_or_story):
        if name_or_story == 'next':
            # Reserved keyword for next state in script
            self.curr_state = self.curr_story[self.curr_story.index(self.curr_state)+1]
            return
        if name_or_story == 'prev':
            # Reserved keyword for next state in script
            self.curr_state = self.curr_story[self.curr_story.index(self.curr_state)-1]
            return
        if name_or_story == 'back':
            self.curr_story, self.curr_state = self.story_state_stack.pop()
            return

        # First check states in the local story
        story = self.curr_story or {}
        for state in story:
            if state.get('name', None) == name_or_story:
                self.curr_state = state
                return

        # Then check stories in the script
        if name_or_story in self._script:
            self.story_state_stack.append((self.curr_story, self.curr_state))
            self.curr_story = self._script[name_or_story]
            # Return the init state of the new story
            self._set_state('init')
            return

    def _get_triggers(self):
        """Returns triples of local and global triggers 
        with (trigger, state_name, actions)"""
        # Get triggers local to this state
        local_transitions = get_list(self.curr_state, '=>')
        # Have a default trigger with weight 0, so that any other successful
        # trigger with weight > 0 overrides it
        default_trigger = '{{True}}[[weight = 0]]'
        local_triggers = [(trigger, trans.get('->', 'next'), get_list(trans, '='))
                          for trans in local_transitions
                          for trigger in get_list(trans, '?', [default_trigger])]

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
        return weight if match else -1.0
