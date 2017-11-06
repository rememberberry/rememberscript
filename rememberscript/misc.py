from typing import List, Any, Tuple

def get_list(obj: Any, key: str, default: List[Any]=[]) -> List[Any]:
    """Returns a list of items at key in object, converts to list if existing 
    item is not list"""
    if key not in obj:
        return default
    return obj[key] if isinstance(obj[key], list) else [obj[key]]

