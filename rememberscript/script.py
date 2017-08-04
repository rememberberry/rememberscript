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

StateType = Dict[str, Any]
ScriptType = Dict[str, List[StateType]]

def load_script(yaml_path: str, py_path: str, storage: StorageType) -> ScriptType:
    """Loads a single script yaml and py file,
    Saves the local variables in the py file to 'storage'
    """
    script = None
    with open(yaml_path, 'r') as yaml_data:
        print('loading yaml script at %s' % yaml_path)
        script = yaml.load(yaml_data.read())

    if not os.path.exists(py_path):
        print('python script at %s did not exist' % py_path)
        return script

    with open(py_path, 'r') as py_data:
        print('loading python script at %s' % py_path)
        # Run the .py file and populate self._storage with
        # the resulting local variables
        exec(py_data.read(), {'__name__': '__main__'}, storage)

    return script


def load_scripts_dir(path: str, storage: StorageType) -> Dict[str, ScriptType]:
    """Loads all scripts in a dir"""
    scripts = {}
    for yaml_filename in glob.glob(os.path.join(path, '*.yaml')):
        story_name = os.path.basename(yaml_filename).split('.yaml')[0]
        # NOTE: use 'pyr' extension instead of 'py' to indicate that
        # they are not executable on their own or part of any module
        py_filename = yaml_filename.split('.yaml')[0] + '.pyr'
        scripts[story_name] = load_script(yaml_filename, py_filename, storage)
    return scripts


def _maybe_nested_str(obj, key):
    if isinstance(obj.get(key, ''), str):
        return

    error_msg = '%s was not a maybe_nested_str' % key
    obj = obj[key]

    assert isinstance(obj, list), error_msg
    for item_outer in obj:
        if isinstance(item_outer, list):
            for item_inner in item_outer:
                assert isinstance(item_inner, str), error_msg
        else:
            assert isinstance(item_outer, str), error_msg


def _validate_transition(transition):
    assert isinstance(transition, dict), 'Transition should be dict'
    assert isinstance(transition.get('->', ''), str), '"to" should be str'
    for key in ['?', '=']:
        _maybe_nested_str(transition, key)


def _validate_state(state):
    assert isinstance(state, dict), 'State should be dict'
    assert isinstance(state.get('name', ''), str), 'Name should be string'
    if '=>' in state:
        trans = state['=>']
        trans = [trans] if isinstance(trans, dict) else trans
        for t in trans:
            _validate_transition(t)
    for key in ['=enter', '=exit', '?']:
        _maybe_nested_str(state, key)

    assert isinstance(state.get('response_type', ''), str), 'Response type must be str'


def validate_script(script):
    """Validate a loaded yaml script"""
    assert isinstance(script, dict), 'Script should be dict'
    assert 'init' in script, "There needs to be an 'init' story in the script"

    for _, states in script.items():
        assert len(states) > 0 and states[0]['name'] == 'init', 'First state should be init'
        assert isinstance(states, list), 'States should be list'
        for state in states:
            _validate_state(state)

    #TODO: validate that referenced states exist
