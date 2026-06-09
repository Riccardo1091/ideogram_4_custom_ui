"""
Handles plain prompt text or structured JSON prompt parsing/formatting.
"""

import json
from typing import Dict, Any, Union

class PromptBuilder:
    @staticmethod
    def validate_and_parse_json(prompt_str: str) -> Union[Dict[str, Any], None]:
        """Soft-validates if the string is a valid JSON structured prompt."""
        try:
            parsed = json.loads(prompt_str)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return None

    @classmethod
    def build(cls, prompt: str, json_mode: bool = False) -> str:
        """
        Processes prompt input and returns a string finalized for the runtime.
        If json_mode is active, ensures input is formatted as valid JSON,
        otherwise formats it to look consistent.
        """
        if json_mode:
            parsed = cls.validate_and_parse_json(prompt)
            if parsed is not None:
                # Re-dump to guarantee compact layout or validated structure
                return json.dumps(parsed, ensure_ascii=False)
            else:
                # If not valid JSON, wrap it as a minimal JSON dictionary
                return json.dumps({"prompt": prompt}, ensure_ascii=False)
        else:
            return prompt.strip()
