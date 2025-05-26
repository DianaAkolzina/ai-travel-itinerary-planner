import json
import re

class JSONRepairer:
    """Utility class for repairing malformed JSON"""
    
    @staticmethod
    def smart_comma_repair(json_str: str) -> str:
        """Smart comma repair focusing on common LLM JSON issues"""
        print("🔧 Applying smart comma repair...")
        
        # Split into lines for easier processing
        lines = json_str.split('\n')
        repaired_lines = []
        
        for i, line in enumerate(lines):
            current_line = line.rstrip()
            
            # Look ahead to next non-empty line
            next_line = None
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    next_line = lines[j].strip()
                    break
            
            if next_line:
                # Check if we need a comma
                needs_comma = False
                
                # Case 1: String value followed by property
                if (current_line.endswith('"') and next_line.startswith('"') and 
                    ':' in next_line and not current_line.endswith(',"')):
                    needs_comma = True
                
                # Case 2: Array end followed by property
                if (current_line.endswith(']') and next_line.startswith('"') and 
                    ':' in next_line and not current_line.endswith('],')):
                    needs_comma = True
                
                # Case 3: Object end followed by object start
                if (current_line.endswith('}') and next_line.startswith('{') and 
                    not current_line.endswith('},')):
                    needs_comma = True
                
                # Case 4: Object end followed by property
                if (current_line.endswith('}') and next_line.startswith('"') and 
                    ':' in next_line and not current_line.endswith('},')):
                    needs_comma = True
                
                # Add comma if needed
                if needs_comma:
                    current_line += ','
                    print(f"🔧 Added comma to line {i + 1}")
            
            repaired_lines.append(current_line)
        
        repaired_json = '\n'.join(repaired_lines)
        print("🔧 Smart comma repair completed")
        return repaired_json
    
    @staticmethod
    def repair_json_basic(json_str: str) -> str:
        """Basic JSON repair for common issues"""
        print("🔧 Applying basic JSON repairs...")
        
        # Fix missing commas after values before new properties
        json_str = re.sub(r'("\s*)\n(\s*")', r'\1,\n\2', json_str)
        json_str = re.sub(r'(\]\s*)\n(\s*")', r'\1,\n\2', json_str)
        json_str = re.sub(r'(\}\s*)\n(\s*")', r'\1,\n\2', json_str)
        
        # Fix missing commas between array elements
        json_str = re.sub(r'(\})\s*\n\s*(\{)', r'\1,\n  \2', json_str)
        
        # Remove trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        return json_str
    
    @staticmethod
    def repair_json_aggressive(json_str: str) -> str:
        """More aggressive JSON repair with comprehensive error handling"""
        print("🔧 Applying aggressive JSON repairs...")
        
        try:
            # First apply basic repairs
            json_str = JSONRepairer.repair_json_basic(json_str)
            
            # Find the main JSON array - look for [ ... ]
            array_match = re.search(r'\[.*\]', json_str, re.DOTALL)
            if array_match:
                json_str = array_match.group()
                print("🔧 Extracted main JSON array")
            else:
                print("⚠️ No JSON array found, working with full string")
            
            # Clean up the string
            json_str = json_str.strip()
            
            # Ensure it starts with [ and ends with ]
            if not json_str.startswith('['):
                # Find first [
                bracket_pos = json_str.find('[')
                if bracket_pos != -1:
                    json_str = json_str[bracket_pos:]
            
            if not json_str.endswith(']'):
                # Find last ]
                bracket_pos = json_str.rfind(']')
                if bracket_pos != -1:
                    json_str = json_str[:bracket_pos + 1]
            
            # Balance braces { }
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            if open_braces > close_braces:
                missing_braces = open_braces - close_braces
                # Add missing closing braces before the final ]
                if json_str.endswith(']'):
                    json_str = json_str[:-1] + '}' * missing_braces + ']'
                else:
                    json_str = json_str + '}' * missing_braces
                print(f"🔧 Added {missing_braces} missing closing braces")
            
            # Balance brackets [ ]
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')
            if open_brackets > close_brackets:
                missing_brackets = open_brackets - close_brackets
                json_str = json_str + ']' * missing_brackets
                print(f"🔧 Added {missing_brackets} missing closing brackets")
            
            # Fix trailing commas before closing braces/brackets
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix missing commas between objects
            json_str = re.sub(r'(\})\s*(\{)', r'\1,\2', json_str)
            
            # Remove any text after the final closing bracket
            final_bracket = json_str.rfind(']')
            if final_bracket != -1:
                json_str = json_str[:final_bracket + 1]
            
            print("🔧 Aggressive JSON repair completed successfully")
            return json_str
            
        except Exception as e:
            print(f"❌ Error in aggressive JSON repair: {e}")
            # Return original string if repair fails
            return json_str
    
    @staticmethod
    def character_level_repair(json_str: str) -> str:
        """Character-by-character JSON repair for stubborn cases"""
        print("🔧 Applying character-level repair...")
        
        try:
            # Try to parse and catch the exact error location
            json.loads(json_str)
            return json_str  # If it parses, return as-is
        except json.JSONDecodeError as e:
            error_pos = getattr(e, 'pos', 0)
            print(f"🔧 JSON error at position {error_pos}")
            
            # Get context around the error
            start = max(0, error_pos - 50)
            end = min(len(json_str), error_pos + 50)
            context = json_str[start:end]
            print(f"🔧 Error context: ...{context}...")
            
            # Common fixes based on error position
            repaired = json_str
            
            # If error is around a quote, likely missing comma
            if error_pos < len(json_str):
                char_at_error = json_str[error_pos]
                
                # Look backwards for the last meaningful character
                for i in range(error_pos - 1, -1, -1):
                    char = json_str[i]
                    if char in '"]}':
                        # Check if next non-whitespace char needs comma
                        next_meaningful = None
                        for j in range(error_pos, len(json_str)):
                            if json_str[j] not in ' \t\n\r':
                                next_meaningful = json_str[j]
                                break
                        
                        if next_meaningful in '"{':
                            # Insert comma after the closing character
                            repaired = json_str[:i+1] + ',' + json_str[i+1:]
                            print(f"🔧 Inserted comma at position {i+1}")
                            break
                    elif not char.isspace():
                        break
            
            return repaired
