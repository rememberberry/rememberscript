import json
import traceback
from copy import deepcopy
from types import FunctionType
from typing import List, Any, Tuple, AsyncIterator, Union
from .strings import process_action, match_trigger
from .storage import StorageType
from .misc import get_list
from .script import ScriptType, StateType, TransitionType, StoryType
from .script import (TRIGGER, ENTER_ACTION, EXIT_ACTION, ACTION, STATE_NAME,
                    TRANSITIONS, RETURN_TO, NOREPLY, EXTRA, TO)

Transition = Tuple[str, List[str], Union[str, None], dict]
Triggers = List[Tuple[str, Transition]]
StackTupleType = Tuple[StoryType, StateType, str]

def _make_msg(msg: Union[str, dict], extra: dict={}) -> str:
    msg = deepcopy(msg)
    if isinstance(msg, str) or not isinstance(msg, dict):
        msg = {'content': str(msg)}
    msg.update(extra.items())
    return json.dumps(msg)


class RememberMachine:
    """A finite state machine (FSM) that is initialized with a script,
    receives messages and yields replies. This class is build using
    concurrent coroutines for use with asyncio. """
    def __init__(self, script: ScriptType, storage: StorageType=None) -> None:
        self._script = script
        self._storage = storage or {}
        # Add storage itself as a private local variable, so it's accessible
        storage['_storage'] = storage
        self.curr_story: StoryType = []
        self.curr_state: Union[StateType, None] = None
        self.return_to: Union[str, None] = None
        self.story_state_stack: List[StackTupleType] = []

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

        for action in get_list(self.curr_state, EXIT_ACTION):
            extra = self.curr_state.get(EXTRA, {})
            async for m in self._evaluate_action(action, extra):
                yield m

        next_state, trans_actions, self.return_to, extra = await self._get_max_transition(msg)
        for action in trans_actions:
            async for m in self._evaluate_action(action, extra):
                yield m

        self._set_state(next_state)
        for action in get_list(self.curr_state, ENTER_ACTION):
            extra = self.curr_state.get(EXTRA, {})
            async for m in self._evaluate_action(action, extra):
                yield m

        if self.curr_state.get(NOREPLY, False):
            async for m in self.reply(''):
                yield m

    def _set_state(self, name_or_story: str) -> None:
        # Check for reserved keywords
        if name_or_story == 'next':
            # go to next state in script
            self.curr_state = self.curr_story[self.curr_story.index(self.curr_state)+1]
            return
        if name_or_story == 'prev':
            # go to prev state in script
            self.curr_state = self.curr_story[self.curr_story.index(self.curr_state)-1]
            return
        if name_or_story == 'loopback':
            # loop back to the same state in script
            return
        if name_or_story == 'return':
            # return to previous story in the stack
            story, state, return_to = self.story_state_stack.pop()
            if return_to:
                self.curr_story, self.curr_state = story, state
                self._set_state(return_to)
            else:
                self.curr_story, self.curr_state = story, state
            return

        # First check states in the local story
        for state in self.curr_story:
            if state.get(STATE_NAME, None) == name_or_story:
                self.curr_state = state
                return

        # Then check stories in the script
        if name_or_story in self._script:
            self.story_state_stack.append((self.curr_story, self.curr_state,
                                           self.return_to))
            self.curr_story = self._script[name_or_story]
            # Return the init state of the new story
            self._set_state('init')
            return
        else:
            raise ValueError('No such state or story: %s' % name_or_story)

    async def _get_max_transition(self, msg) -> Transition:
        """Returns triples of local and global triggers 
        with (trigger, state_name, actions, return_to)"""
        # Get triggers local to this state
        # Have a default trigger with weight 0, so that any other successful
        # trigger with weight > 0 overrides it
        default_trigger = ["{{True}}[[weight = 0]]"]
        default_return = self.curr_state.get(RETURN_TO, None)
        loc: Triggers = [(trigger, (trans.get(TO, 'next'), get_list(trans, ACTION),
                         trans.get(RETURN_TO, default_return), trans.get(EXTRA, {})))
                         for trans in get_list(self.curr_state, TRANSITIONS)
                         for trigger in get_list(trans, TRIGGER, default_trigger)]

        # Get triggers reachable from anywhere
        glob: Triggers = [(trigger, (story_name, [], default_return, {}))
                          for story_name, story in self._script.items()
                          for trigger in get_list(story[0], TRIGGER)]

        # If there are no successful local or global triggers, default to next state
        max_transition: Transition = ('next', [], None, {})
        max_weight = -1.0
        for trigger, transition in loc + glob:
            weight = await self._evaluate_trigger(trigger, msg)
            if weight > max_weight:
                max_transition = transition
                max_weight = weight
        return max_transition

    async def _evaluate_action(self, action: Union[str, dict], extra: dict) -> AsyncIterator[Union[str]]:
        if isinstance(action, dict):
            yield json.dumps(action)
            return
        async for msg in process_action(action, self._storage):
            yield _make_msg(msg, extra)

    async def _evaluate_trigger(self, trigger: str, msg: str) -> float:
        self._storage['weight'] = 1.0 # set default weight
        match: bool = await match_trigger(msg, trigger, self._storage)
        weight = self._storage['weight']
        del self._storage['weight']

        return weight if match else -1.0
