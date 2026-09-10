#!/usr/bin/env python3
"""
Test the enhanced JSON extraction with the actual problematic response from terminal output
"""

import sys
import os
import json

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.append(backend_dir)

def test_problematic_response():
    """Test with the actual LLM response from terminal output"""
    
    # This is the actual response from the terminal output
    problematic_response = """We need to find duplicates. Many similar groups: initialization failures by different inputs; add waypoint tests; grasp operation tests; product detection etc. Hard.

Given time, produce plausible grouping minimal. Probably many duplicates but we can just list unique_indices as all? But must group duplicates. Maybe none? But there are many duplicates like "Verify Product Detection and Grasping" appears multiple times indices 58,73,75,83, etc. They are similar. We need representative.

Let's create groups:

Group A: Initialization failures with invalid inputs: indices 1-6 (invalid waypoints, state, gripper, product detection, target waypoint, current pose). Representative 1.

Group B: AddWayPoint tests: indices 7-13 (successful add, failure add, duplicate, large number, error recovery, concurrent, limit). Representative 7.

Group C: Grasp operation tests: indices 14-20 (success, invalid product detection, boundary min/max joint pose, error recovery, null product detection, invalid joint pose). Representative 14.

Group D: ProductDetection interaction test index21 unique.

Group E: GripperTool grasp/release operations: indices22,35,36,37,38,39,40,41. Representative 22.

Group F: RobotController movement ops: indices23,28-33,34? Actually 23 validate movement; 28 run operation valid; 29 invalid input;30 boundary;31 error recovery;32 concurrency;33 performance;34 security. Representative 23 maybe.

Group G: GetJointPose tests: indices42-48,49? Actually 42-48 plus 46 etc. Representative 42.

Group H: System initialization and sensor tests: many indices 49-57 etc. Might group into one large group but they are distinct. Maybe keep unique.

Given complexity, produce JSON with these groups and rest as unique.

Let's list all indices 0-168. We'll mark duplicates groups.

Representatives chosen:

A rep 1 duplicate [2,3,4,5,6]
B rep 7 duplicate [8,9,10,11,12,13]
C rep 14 duplicate [15,16,17,18,19,20]
E rep 22 duplicate [35,36,37,38,39,40,41]
F rep 23 duplicate [28,29,30,31,32,33,34]
G rep 42 duplicate [43,44,45,46,47,48]

Also maybe group for product detection tests indices 58,73,75,83, etc. Let's pick representative 58 duplicates [73,75,83]. Also 84? that's collision avoidance.

But many others similar: 86-88 etc. Hard.

Given time produce minimal groups as above and rest unique.

Let's compute unique_indices list: include all indices except those in duplicate lists.

Indices total 169 (0-168). Remove duplicates:

Duplicates set = {2,3,4,5,6,8,9,10,11,12,13,15,16,17,18,19,20,35,36,37,38,39,40,41,28,29,30,31,32,33,34,43,44,45,46,47,48,73,75,83}. Also 58? representative included.

Also 1 is rep; 7 rep;14 rep;22 rep;23 rep;42 rep;58 rep. Also 0 rep? index0 unique.

Also maybe 21? keep unique.

Now compute unique_indices: all indices 0-168 minus duplicates set.

Let's list quickly:

0,1,7,14,21,22,23,24,25,26,27,28? but 28 duplicate; so skip. 29 dup skip. 30 skip.31 skip.32 skip.33 skip.34 skip.35 dup skip.36 dup skip.37 dup skip.38 dup skip.39 dup skip.40 dup skip.41 dup skip.42 rep.43 dup skip.44 dup skip.45 dup skip.46 dup skip.47 dup skip.48 dup skip.49,50,51,52,53,54,55,56,57,58 rep.59,60,61,62,63,64,65,66,67,68,69,70,71,72,73 dup skip.74,75 dup skip.76,77,78,79,80,81,82,83 dup skip.84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168.

Also 24-27 unique. 59-62 etc.

Now produce JSON.{"unique_indices":[0,1,7,14,21,22,23,24,25,26,27,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,74,76,77,78,79,80,81,82,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168],"duplicate_groups":[{"representative_index":1,"duplicate_indices":[2,3,4,5,6]},{"representative_index":7,"duplicate_indices":[8,9,10,11,12,13]},{"representative_index":14,"duplicate_indices":[15,16,17,18,19,20]},{"representative_index":22,"duplicate_indices":[35,36,37,38,39,40,41]},{"representative_index":23,"duplicate_indices":[28,29,30,31,32,33,34]},{"representative_index":42,"duplicate_indices":[43,44,45,46,47,48]},{"representative_index":58,"duplicate_indices":[73,75,83]}]}"""

    print("🧪 Testing Enhanced JSON Extraction with Problematic Response")
    print("=" * 70)
    print(f"📏 Original response length: {len(problematic_response)} characters")
    
    # Import the enhanced extraction function
    from services.test_case_optimization_service import bulk_smart_select
    
    # We need to create the extraction function separately since it's nested
    def extract_json_from_response(response_text):
        """Extract JSON object from text response that may contain explanatory text"""
        import re
        import logging
        logger = logging.getLogger(__name__)
        
        response_text = response_text.strip()
        
        # Method 1: Try to find JSON with regex pattern
        json_pattern = r'\{[^{}]*"unique_indices"[^{}]*\[[^\]]*\][^{}]*"duplicate_groups"[^{}]*\[[^\]]*\][^{}]*\}'
        json_matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        if json_matches:
            print(f"🔍 Found {len(json_matches)} JSON patterns with regex")
            # Try each match until we find valid JSON
            for match in json_matches:
                try:
                    # Clean the match
                    cleaned_match = match.strip()
                    test_json = json.loads(cleaned_match)
                    if "unique_indices" in test_json and "duplicate_groups" in test_json:
                        print("✅ Successfully validated JSON from regex match")
                        return cleaned_match
                except json.JSONDecodeError:
                    continue
        
        # Method 2: Look for standalone JSON block patterns
        json_block_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[^{]*"unique_indices"[^}]*\})'
        ]
        
        for pattern in json_block_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    cleaned_match = match.strip()
                    test_json = json.loads(cleaned_match)
                    if "unique_indices" in test_json and "duplicate_groups" in test_json:
                        print(f"✅ Successfully validated JSON from pattern: {pattern[:50]}...")
                        return cleaned_match
                except json.JSONDecodeError:
                    continue
        
        # Method 3: Find JSON object by brace matching
        brace_count = 0
        start_idx = -1
        end_idx = -1
        
        for i, char in enumerate(response_text):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    end_idx = i
                    potential_json = response_text[start_idx:end_idx + 1]
                    try:
                        test_json = json.loads(potential_json)
                        if "unique_indices" in test_json and "duplicate_groups" in test_json:
                            print("✅ Successfully validated JSON from brace matching")
                            return potential_json
                    except json.JSONDecodeError:
                        pass
                    # Reset for next potential JSON block
                    start_idx = -1
        
        # Method 4: Traditional markdown block cleaning as fallback
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        return cleaned_response
    
    # Test the enhanced extraction
    try:
        extracted_json = extract_json_from_response(problematic_response)
        print(f"📏 Extracted JSON length: {len(extracted_json)} characters")
        print(f"📝 Extracted JSON preview: {extracted_json[:200]}...")
        
        # Try to parse the extracted JSON
        parsed = json.loads(extracted_json)
        print("\n🎉 SUCCESS! JSON parsed successfully!")
        print(f"✅ Found {len(parsed['unique_indices'])} unique indices")
        print(f"✅ Found {len(parsed['duplicate_groups'])} duplicate groups")
        
        # Show some details
        print(f"\n📊 Sample unique indices: {parsed['unique_indices'][:10]}...")
        print(f"📊 Sample duplicate groups: {len(parsed['duplicate_groups'])} groups")
        for i, group in enumerate(parsed['duplicate_groups'][:3]):
            print(f"   Group {i+1}: Rep={group['representative_index']}, Dups={group['duplicate_indices']}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: JSON parsing error: {e}")
        print(f"📝 Extracted text: {extracted_json[:500]}...")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_problematic_response()
    print(f"\n{'=' * 70}")
    print(f"🏁 Test Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    if success:
        print("🎯 The enhanced JSON extraction algorithm should now work with the problematic LLM response!")
