import json
import re
from typing import Tuple
import asyncio

# -----------------------
# Basic JSON Cleanups
# -----------------------

def repair_json_basic(json_str: str) -> str:
    """Apply simple regex-based JSON repairs for common newline/comma issues."""
    print("Applying basic JSON repairs...")
    json_str = re.sub(r'(")\s*\n\s*(")', r'\1,\n\2', json_str)
    json_str = re.sub(r'(\])\s*\n\s*(")', r'\1,\n\2', json_str)
    json_str = re.sub(r'(\})\s*\n\s*(")', r'\1,\n\2', json_str)
    json_str = re.sub(r'(\})\s*\n\s*(\{)', r'\1,\n\2', json_str)
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    return json_str

# -----------------------
# Smarter Comma Detection
# -----------------------

def smart_comma_repair(json_str: str) -> str:
    """Attempts to insert missing commas between JSON lines using structure clues."""
    print("Applying smart comma repair...")
    lines = json_str.split('\n')
    repaired = []

    for i, line in enumerate(lines):
        current = line.rstrip()
        next_line = next((l.strip() for l in lines[i + 1:] if l.strip()), None)
        if next_line:
            needs_comma = (
                (current.endswith('"') and next_line.startswith('"') and ':' in next_line and not current.endswith('",')) or
                (current.endswith(']') and next_line.startswith('"') and ':' in next_line and not current.endswith('],')) or
                (current.endswith('}') and next_line.startswith('{') and not current.endswith('},')) or
                (current.endswith('}') and next_line.startswith('"') and ':' in next_line and not current.endswith('},'))
            )
            if needs_comma:
                current += ','
                print(f"Added comma to line {i + 1}")
        repaired.append(current)

    return '\n'.join(repaired)

# -----------------------
# Targeted Character-Level Fix
# -----------------------

def character_level_repair(json_str: str) -> str:
    """Locates the error position and tries inserting a comma before a next valid JSON element."""
    print("Applying character-level repair...")
    try:
        json.loads(json_str)
        return json_str  
    except json.JSONDecodeError as e:
        error_pos = getattr(e, 'pos', 0)
        print(f" JSON error at position {error_pos}")
        for i in range(error_pos - 1, -1, -1):
            if json_str[i] in '"]}':
                for j in range(error_pos, len(json_str)):
                    if json_str[j] not in ' \t\n\r':
                        if json_str[j] in '"{[':
                            repaired = json_str[:i+1] + ',' + json_str[i+1:]
                            print(f" Inserted comma at position {i + 1}")
                            return repaired
                        break
                break
        return json_str

# -----------------------
# Fallback Heuristic Fixer
# -----------------------

def repair_json_aggressive(json_str: str) -> str:
    """Heuristically repairs broken JSON by trimming to the main object, balancing brackets, and deduplicating commas."""
    print("Applying aggressive JSON repairs...")
    try:
        json_str = repair_json_basic(json_str)
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        json_str = match.group() if match else json_str.strip()

        json_str += '}' * (json_str.count('{') - json_str.count('}'))
        json_str += ']' * (json_str.count('[') - json_str.count(']'))

        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        json_str = re.sub(r'\}\s*\{', r'},\n{', json_str)

        return json_str

    except Exception as e:
        print(f"Error in aggressive JSON repair: {e}")
        return json_str

# -----------------------
# Fixing comma patterns between lines
# -----------------------

def fix_missing_commas(json_str: str) -> str:
    """Fixes missing commas between dictionary/object entries based on structure."""
    print("Fixing missing commas...")
    lines = json_str.split('\n')
    fixed = []

    for i, line in enumerate(lines):
        fixed.append(line)
        if i < len(lines) - 1:
            curr, nxt = lines[i].strip(), lines[i + 1].strip()
            if curr and nxt:
                if (curr.endswith('"') or curr.endswith(']') or curr.endswith('}')) and nxt.startswith('"') and not curr.endswith(','):
                    fixed[-1] = line + ','
                if curr.endswith('}') and nxt.startswith('{') and not curr.endswith(','):
                    fixed[-1] = line + ','

    return '\n'.join(fixed)

# -----------------------
# Validate and Repair JSON
# -----------------------

async def validate_and_repair_json(json_str: str) -> Tuple[dict, bool]:
    """Validates JSON string. If invalid, applies repair steps in order and retries parsing."""
    try:
        return json.loads(json_str), False
    except json.JSONDecodeError:
        repair_strategies = [
            repair_json_basic,
            fix_missing_commas,
            smart_comma_repair,
            character_level_repair,
            repair_json_aggressive,
        ]

        for repair in repair_strategies:
            try:
                repaired = repair(json_str)
                parsed = json.loads(repaired)
                print(f"Successfully repaired JSON using {repair.__name__}")
                return parsed, True
            except Exception as e:
                print(f"{repair.__name__} failed: {e}")
                continue

        print("All repairs failed, retrying with LLM...")
        from app.services.llm_service import LLMService
        llm_service = LLMService()
        response = await llm_service._call_ollama(
            "Repeat the last itinerary in valid JSON only with no comments or explanations"
        )
        return await validate_and_repair_json(response)
