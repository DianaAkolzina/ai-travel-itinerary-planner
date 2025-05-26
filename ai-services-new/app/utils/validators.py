def validate_parsed_plan(plan, expected_days):
    """Validate that the parsed plan is reasonable"""
    if not isinstance(plan, list):
        print("⚠️ Plan is not a list")
        return False
    
    if len(plan) == 0:
        print("⚠️ Plan is empty")
        return False
    
    if len(plan) > expected_days * 2:  
        print(f"⚠️ Way too many days in plan: {len(plan)} (expected around {expected_days})")
        return False
  
    for i, day in enumerate(plan):
        if not isinstance(day, dict):
            print(f"⚠️ Day {i+1} is not a dictionary")
            return False
        
        required_fields = ['town', 'place', 'activities']
        for field in required_fields:
            if field not in day:
                print(f"⚠️ Day {i+1} missing field: {field}")
                return False
        
        if not isinstance(day['activities'], list):
            print(f"⚠️ Day {i+1} activities is not a list")
            return False
    
    print(f"✅ Plan validation passed: {len(plan)} days")
    return True