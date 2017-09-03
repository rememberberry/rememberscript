"""
Contains functions for loading and validating scripts
Scripts are defined in .yaml files and .py files with the same name

Note: decided against using any validation library such as pykwalify, voluptuous or rx
since they are either not quite mature (pykwalify has showstopper bugs as of writing)
or not flexible enough to represent the schema needed
"""
import os
import glob
from typing import Dict, List, Any
import yaml
from .storage import StorageType


TRIGGER = '?'
ENTER_ACTION = '=>+'
EXIT_ACTION = '+=>'
ACTION = '+'
STATE_NAME = 'name'
TRANSITIONS = '=?>'
RETURN_TO = 'return=>'
NOREPLY = 'noreply'
EXTRA = 'extra'
TO = '=>'

StateType = Dict[str, Any]
TransitionType = Dict[str, Any]
StoryType = List[StateType]
ScriptType = Dict[str, StoryType]

def load_script(dir_path: str, story_name: str, storage: StorageType) -> ScriptType:
    """Loads a single script yaml and py file,
    Saves the local variables in the py file to 'storage'
    """
    yaml_path = os.path.join(dir_path, story_name+'.yaml')
    py_path = os.path.join(dir_path, story_name+'.pyr')
    script = None
    with open(yaml_path, 'r') as yaml_data:
        script = yaml.load(yaml_data.read())

    if not os.path.exists(py_path):
        return script

    with open(py_path, 'r') as py_data:
        # Run the .py file and populate storage with
        # the resulting local variables
        try:
            exec(py_data.read(), {'__name__': '__main__'}, storage)
        except:
            print('py_path: %s' % py_path)
            raise

    return script


def load_scripts_dir(path: str, storage: StorageType) -> Dict[str, ScriptType]:
    """Loads all scripts in a dir"""
    scripts = {}
    for yaml_filename in glob.glob(os.path.join(path, '*.yaml')):
        story_name = os.path.basename(yaml_filename).split('.yaml')[0]
        # NOTE: use 'pyr' extension instead of 'py' to indicate that
        # they are not executable on their own or part of any module
        dir_path = os.path.dirname(yaml_filename)
        scripts[story_name] = load_script(dir_path, story_name, storage)
    return scripts


def _maybe_nested_types(obj, key, types):
    for t in types:
        if key not in obj or isinstance(obj[key], t):
            return

    error_msg = '%s was not a maybe_nested_types: %s\n%s' % (key, str(obj[key]), obj)
    obj = obj[key]

    assert isinstance(obj, list), error_msg
    for item_outer in obj:
        items = item_outer if isinstance(item_outer, list) else [item_outer]
        for item in items:
            is_one_of = False
            for t in types:
                is_one_of = is_one_of or isinstance(item, t)
            assert is_one_of, error_msg


def _validate_transition(transition):
    valid_keys = {TO, ACTION, TRIGGER, RETURN_TO}
    key_diff = set(transition.keys()) - valid_keys
    assert len(key_diff) == 0, 'Unkown keys %s' % str(key_diff)
    assert isinstance(transition, dict), 'Transition should be dict'
    assert isinstance(transition.get(TO, ''), str), '"to" should be str'
    assert isinstance(transition.get(RETURN_TO, ''), str), '"return_to" should be str'
    assert isinstance(transition.get(EXTRA, {}), dict), 'extra type must be dict'
    _maybe_nested_types(transition, TRIGGER, [str])
    _maybe_nested_types(transition, ACTION, [str, dict])


def _validate_state(state):
    valid_keys = {STATE_NAME, TRIGGER, ENTER_ACTION, EXIT_ACTION, TRANSITIONS,
                  NOREPLY, EXTRA}
    assert len(set(state.keys()) - valid_keys) == 0
    assert isinstance(state, dict), 'State should be dict'
    assert isinstance(state.get(STATE_NAME, ''), str), 'Name should be string'
    if TRANSITIONS in state:
        trans = state[TRANSITIONS]
        trans = [trans] if isinstance(trans, dict) else trans
        for t in trans:
            _validate_transition(t)

    _maybe_nested_types(state, TO, [str])
    for key in [ENTER_ACTION, EXIT_ACTION]:
        _maybe_nested_types(state, key, [str, dict])

    assert isinstance(state.get(NOREPLY, False), bool), 'noreply type must be bool'
    assert isinstance(state.get(EXTRA, {}), dict), 'extra type must be dict'


def validate_script(script):
    """Validate a loaded yaml script"""
    assert isinstance(script, dict), 'Script should be dict'
    assert 'init' in script, "There needs to be an 'init' story in the script"

    for _, states in script.items():
        assert len(states) > 0 and states[0][STATE_NAME] == 'init', 'First state should be init'
        assert isinstance(states, list), 'States should be list'
        for state in states:
            _validate_state(state)

    #TODO: validate that referenced states exist
