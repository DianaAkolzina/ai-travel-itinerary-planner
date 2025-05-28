import json
import re


def smart_comma_repair(json_str: str) -> str:
    print("🔧 Applying smart comma repair...")
    lines = json_str.split('\n')
    repaired_lines = []
    for i, line in enumerate(lines):
        current_line = line.rstrip()
        next_line = next((l.strip() for l in lines[i + 1:] if l.strip()), None)
        if next_line:
            needs_comma = False
            if current_line.endswith('"') and next_line.startswith('"') and ':' in next_line:
                if not current_line.endswith('",'):
                    needs_comma = True
            if current_line.endswith(']') and next_line.startswith('"') and ':' in next_line:
                if not current_line.endswith('],'):
                    needs_comma = True
            if current_line.endswith('}') and next_line.startswith('{'):
                if not current_line.endswith('},'):
                    needs_comma = True
            if current_line.endswith('}') and next_line.startswith('"') and ':' in next_line:
                if not current_line.endswith('},'):
                    needs_comma = True
            if needs_comma:
                current_line += ','
                print(f"🔧 Added comma to line {i + 1}")
        repaired_lines.append(current_line)
    return '\n'.join(repaired_lines)


def character_level_repair(json_str: str) -> str:
    print("🔧 Applying character-level repair...")
    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError as e:
        error_pos = getattr(e, 'pos', 0)
        print(f"🔧 JSON error at position {error_pos}")
        repaired = json_str
        if error_pos < len(json_str):
            for i in range(error_pos - 1, -1, -1):
                if json_str[i] in '"]}':
                    for j in range(error_pos, len(json_str)):
                        if json_str[j] not in ' \t\n\r':
                            if json_str[j] in '"{':
                                repaired = json_str[:i+1] + ',' + json_str[i+1:]
                                print(f"🔧 Inserted comma at position {i + 1}")
                                return repaired
                            break
                    break
                elif not json_str[i].isspace():
                    break
        return repaired


def repair_json_basic(json_str: str) -> str:
    print("🔧 Applying basic JSON repairs...")
    json_str = re.sub(r'(\"\s*)\n(\s*\")', r'\1,\n\2', json_str)
    json_str = re.sub(r'(\]\s*)\n(\s*\")', r'\1,\n\2', json_str)
    json_str = re.sub(r'(\}\s*)\n(\s*\")', r'\1,\n\2', json_str)
    json_str = re.sub(r'(\})\s*\n\s*(\{)', r'\1,\n\2', json_str)
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    return json_str


def fix_missing_commas(json_str: str) -> str:
    print("🔧 Fixing missing commas...")
    lines = json_str.split('\n')
    fixed_lines = []
    for i, line in enumerate(lines):
        fixed_lines.append(line)
        if i < len(lines) - 1:
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            if current_line and next_line:
                if (current_line.endswith('"') or current_line.endswith(']') or current_line.endswith('}')) and next_line.startswith('"'):
                    if not current_line.endswith(','):
                        fixed_lines[-1] = line + ','
                if current_line.endswith('}') and next_line.startswith('{'):
                    if not current_line.endswith(','):
                        fixed_lines[-1] = line + ','
    return '\n'.join(fixed_lines)


def repair_json_aggressive(json_str: str) -> str:
    print("🔧 Applying aggressive JSON repairs...")
    try:
        json_str = repair_json_basic(json_str)
        object_match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if object_match:
            json_str = object_match.group()
            print("🔧 Extracted main JSON object")
        else:
            print("⚠️ No top-level JSON object found, using entire string")
        json_str = json_str.strip()
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
            print(f"🔧 Added {open_braces - close_braces} missing closing braces")
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        if open_brackets > close_brackets:
            json_str += ']' * (open_brackets - close_brackets)
            print(f"🔧 Added {open_brackets - close_brackets} missing closing brackets")
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        json_str = re.sub(r'(\})\s*(\{)', r'\1,\2', json_str)
        return json_str
    except Exception as e:
        print(f"❌ Error in aggressive JSON repair: {e}")
        return json_str

import json
from typing import Tuple

async def validate_and_repair_json(json_str: str) -> Tuple[dict, bool]:
    try:
        parsed = json.loads(json_str)
        return parsed, False
    except json.JSONDecodeError:
        repair_functions = [
            repair_json_basic,
            fix_missing_commas,
            smart_comma_repair,
            character_level_repair,
            repair_json_aggressive
        ]
        for repair_func in repair_functions:
            try:
                repaired_json = repair_func(json_str)
                parsed = json.loads(repaired_json)
                print(f"✅ Successfully repaired JSON using {repair_func.__name__}")
                return parsed, True
            except json.JSONDecodeError:
                continue

        # Retry by asking the LLM again
        print("🔁 All repairs failed, retrying with LLM...")
        from app.services.llm_service import LLMService
        llm_service = LLMService()
        new_response = await llm_service._call_ollama(
            "Repeat the last itinerary in valid JSON only with no comments or explanations"
        )
        return await validate_and_repair_json(new_response)

