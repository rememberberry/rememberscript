import traceback
from types import FunctionType
from typing import List, Any, Tuple, AsyncIterator, Union
from .strings import process_action, match_trigger
from .storage import StorageType
from .script import ScriptType, StateType

Triggers = List[Tuple[str, str, List[str]]]

def get_list(obj: Any, key: str, default: List[Any]=[]) -> List[Any]:
    """Returns a list of items at key in object, converts to list if existing 
    item is not list"""
    if key not in obj:
        return default
    return obj[key] if isinstance(obj[key], list) else [obj[key]]

class RememberMachine:
    """A finite state machine (FSM) that is initialized with a script,
    receives messages and yields replies. This class is build using
    concurrent coroutines for use with asyncio. """
    def __init__(self, script: ScriptType, storage: StorageType=None) -> None:
        self._script = script
        self._storage = storage or {}
        self.curr_story: List[StateType] = []
        self.curr_state: Union[StateType, None] = None
        self.story_state_stack: List[Tuple[List[StateType], StateType]] = []

    def init(self):
        """Sets the current state to the init state
        Note: one never enters into the init state, we just are in it,
        therefore pre-reply-actions and state triggers dont apply"""
        self._set_state('init')
        assert self.curr_state is not None

    async def reply(self, msg: str) -> AsyncIterator[str]:
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
            async for m in self._evaluate_action(action):
                yield m

        transitions = [(await self._evaluate_trigger(t, msg), next_state, actions)
                       for t, next_state, actions in self._get_triggers()]
        _, next_state, transition_actions = max(transitions, key=lambda x: x[0])
        for action in transition_actions:
            async for m in self._evaluate_action(action):
                yield m

        self._set_state(next_state)
        for action in get_list(self.curr_state, '=enter'):
            async for m in self._evaluate_action(action):
                yield m

    def _set_state(self, name_or_story: str) -> None:
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
        story = self.curr_story
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
        else:
            raise ValueError('No such state or story: %s' % name_or_story)

    def _get_triggers(self) -> Triggers:
        """Returns triples of local and global triggers 
        with (trigger, state_name, actions)"""
        # Get triggers local to this state
        local_transitions = get_list(self.curr_state, '=>')
        # Have a default trigger with weight 0, so that any other successful
        # trigger with weight > 0 overrides it
        default_trigger = '{{True}}[[weight = 0]]'
        loc: Triggers = [(trigger, trans.get('->', 'next'), get_list(trans, '='))
                         for trans in local_transitions
                         for trigger in get_list(trans, '?', [default_trigger])]

        # Get triggers reachable from anywhere
        glob: Triggers = [(trigger, story[0].get('name', 'next'), [])
                          for story in self._script.values()
                          for trigger in get_list(story[0], '?')]

        return loc + glob

    async def _evaluate_action(self, action: str) -> AsyncIterator[Union[str]]:
        async for msg in process_action(action, self._storage):
            yield msg

    async def _evaluate_trigger(self, trigger: str, msg: str) -> float:
        self._storage['weight'] = 1.0 # set default weight
        match: bool = await match_trigger(msg, trigger, self._storage)
        weight = self._storage['weight']
        del self._storage['weight']

        return weight if match else -1.0
