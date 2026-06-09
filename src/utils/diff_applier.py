import copy
import logging
import re
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

def parse_json_path(path: str) -> List[Union[str, int]]:
    """
    Parses a JSON path string into a list of keys and indices.
    Examples:
        'professional_summary' -> ['professional_summary']
        'professional_experience[0].highlights[1]' -> ['professional_experience', 0, 'highlights', 1]
        'skills["Software Development"]' -> ['skills', 'Software Development']
    """
    parts = []
    # Match dot-separated string, or a bracketed number, or bracketed string
    for token in re.finditer(r'([^.\[\]]+)|\[(\d+)\]|\["([^"]+)"\]|\[\'([^\']+)\'\]', path):
        if token.group(1) is not None:
            parts.append(token.group(1))
        elif token.group(2) is not None:
            parts.append(int(token.group(2)))
        elif token.group(3) is not None:
            parts.append(token.group(3))
        elif token.group(4) is not None:
            parts.append(token.group(4))
    return parts

def apply_diffs(base_resume: Dict[str, Any], diffs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Applies a list of JSON diffs to a deep copy of the base_resume.
    Each diff should contain:
        - action: 'replace'
        - section: A JSON path string
        - new_value: The value to set
    """
    tailored_resume = copy.deepcopy(base_resume)
    
    for diff in diffs:
        action = diff.get("action")
        path_str = diff.get("section")
        new_value = diff.get("new_value")
        
        if not path_str:
            logger.warning("Diff is missing 'section' path.")
            continue
            
        if action not in ("replace", "update", "add", "insert", "remove", "delete", "rename"):
            logger.warning(f"Unsupported action '{action}' for path {path_str}.")
            continue
            
        path = parse_json_path(path_str)
        if not path:
            logger.warning(f"Failed to parse path: {path_str}")
            continue
            
        current = tailored_resume
        try:
            for i in range(len(path) - 1):
                key = path[i]
                current = current[key]
                
            final_key = path[-1]
            
            if action in ("replace", "update"):
                current[final_key] = new_value
            elif action in ("add", "insert"):
                if isinstance(current, list) and isinstance(final_key, int):
                    current.insert(final_key, new_value)
                elif isinstance(current, dict):
                    # Check if they are trying to append to a list but omitted the index
                    if final_key in current and isinstance(current[final_key], list) and not isinstance(new_value, list):
                        current[final_key].append(new_value)
                    else:
                        current[final_key] = new_value
            elif action in ("remove", "delete"):
                if isinstance(current, list) and isinstance(final_key, int):
                    if 0 <= final_key < len(current):
                        current.pop(final_key)
                elif isinstance(current, dict):
                    if final_key in current:
                        del current[final_key]
            elif action == "rename":
                if isinstance(current, dict):
                    if final_key in current:
                        current[new_value] = current.pop(final_key)
            
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Failed to apply diff at path {path_str}: {str(e)}")
            continue

    return tailored_resume
