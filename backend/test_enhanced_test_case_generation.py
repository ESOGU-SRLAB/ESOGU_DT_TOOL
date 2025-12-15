#!/usr/bin/env python3
"""
Test script for enhanced Test Case Generation with token limit support
"""

import requests
import json

def test_enhanced_test_case_generation():
    """Test the enhanced test case generation with token limit controls"""
    
    url = "http://localhost:8000/api/processes/test-scenario-generation/generate-test-cases"
    
    # Test with multiple scenarios and large file content
    payload = {
        "selected_scenarios": [
            {
                "scenario_id": "TS_001",
                "scenario": "User Authentication and Login Process",
                "description": "Test the complete user authentication system including login, session management, and security features",
                "objective": "Verify user authentication functionality works correctly with various input combinations",
                "category": "Functional"
            },
            {
                "scenario_id": "TS_002", 
                "scenario": "Data Validation and Error Handling",
                "description": "Test input validation mechanisms and error handling procedures throughout the application",
                "objective": "Ensure proper validation and error reporting for all user inputs",
                "category": "Negative Testing"
            }
        ],
        "process_prompt": """Acting as a senior ISTQB-certified test analyst, generate comprehensive and detailed test cases for the following test scenarios. 

Focus on creating practical, executable test cases that cover:
- Positive testing scenarios with valid inputs
- Negative testing scenarios with invalid inputs
- Boundary value analysis and edge cases
- Security considerations and authentication testing
- Data validation and error handling
- Integration points and system interactions

Each test case should include detailed test steps, clear expected results, realistic prerequisites, appropriate test data, and meaningful comments about testing considerations.""",
        "selected_files": [
            {
                "name": "user_auth.py",
                "content": """
# User Authentication System
import hashlib
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class UserAuthenticator:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.users = {}
        self.active_sessions = {}
    
    def register_user(self, username, email, password):
        \"\"\"Register a new user with validation\"\"\"
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        
        if not email or "@" not in email:
            raise ValueError("Valid email address is required")
        
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if username in self.users:
            raise ValueError("Username already exists")
        
        password_hash = generate_password_hash(password)
        
        user_data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.datetime.now(),
            "last_login": None,
            "failed_attempts": 0,
            "account_locked": False
        }
        
        self.users[username] = user_data
        return {"status": "success", "message": "User registered successfully"}
    
    def authenticate_user(self, username, password):
        \"\"\"Authenticate user credentials\"\"\"
        if not username or not password:
            return {"status": "error", "message": "Username and password are required"}
        
        user = self.users.get(username)
        if not user:
            return {"status": "error", "message": "Invalid credentials"}
        
        if user["account_locked"]:
            return {"status": "error", "message": "Account is locked due to multiple failed attempts"}
        
        if check_password_hash(user["password_hash"], password):
            # Reset failed attempts on successful login
            user["failed_attempts"] = 0
            user["last_login"] = datetime.datetime.now()
            
            # Generate JWT token
            token = self.generate_token(username)
            self.active_sessions[username] = token
            
            return {
                "status": "success", 
                "message": "Authentication successful",
                "token": token,
                "user_info": {
                    "username": username,
                    "email": user["email"],
                    "last_login": user["last_login"]
                }
            }
        else:
            # Increment failed attempts
            user["failed_attempts"] += 1
            if user["failed_attempts"] >= 5:
                user["account_locked"] = True
                return {"status": "error", "message": "Account locked due to multiple failed attempts"}
            
            return {"status": "error", "message": "Invalid credentials"}
    
    def generate_token(self, username):
        \"\"\"Generate JWT token for authenticated user\"\"\"
        payload = {
            "username": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            "iat": datetime.datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def validate_token(self, token):
        \"\"\"Validate JWT token\"\"\"
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            username = payload["username"]
            
            if username in self.active_sessions and self.active_sessions[username] == token:
                return {"status": "valid", "username": username}
            else:
                return {"status": "invalid", "message": "Token not found in active sessions"}
                
        except jwt.ExpiredSignatureError:
            return {"status": "expired", "message": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"status": "invalid", "message": "Invalid token"}
    
    def logout_user(self, username):
        \"\"\"Logout user and invalidate session\"\"\"
        if username in self.active_sessions:
            del self.active_sessions[username]
            return {"status": "success", "message": "User logged out successfully"}
        return {"status": "error", "message": "No active session found"}
    
    def reset_password(self, username, old_password, new_password):
        \"\"\"Reset user password with validation\"\"\"
        user = self.users.get(username)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        if not check_password_hash(user["password_hash"], old_password):
            return {"status": "error", "message": "Current password is incorrect"}
        
        if len(new_password) < 8:
            return {"status": "error", "message": "New password must be at least 8 characters long"}
        
        user["password_hash"] = generate_password_hash(new_password)
        
        # Invalidate all active sessions for this user
        if username in self.active_sessions:
            del self.active_sessions[username]
        
        return {"status": "success", "message": "Password reset successfully"}

class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, user_id, session_data):
        \"\"\"Create a new user session\"\"\"
        session_id = hashlib.md5(f"{user_id}_{datetime.datetime.now()}".encode()).hexdigest()
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.datetime.now(),
            "last_activity": datetime.datetime.now(),
            "data": session_data
        }
        return session_id
    
    def get_session(self, session_id):
        \"\"\"Retrieve session data\"\"\"
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Check if session has expired (24 hours)
        if datetime.datetime.now() - session["last_activity"] > datetime.timedelta(hours=24):
            del self.sessions[session_id]
            return None
        
        # Update last activity
        session["last_activity"] = datetime.datetime.now()
        return session
    
    def delete_session(self, session_id):
        \"\"\"Delete a session\"\"\"
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
"""
            },
            {
                "name": "data_validator.py", 
                "content": """
# Data Validation Module
import re
import datetime
from typing import Any, Dict, List, Optional

class DataValidator:
    \"\"\"Comprehensive data validation utility\"\"\"
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, Any]:
        \"\"\"Validate email format\"\"\"
        if not email:
            return {"valid": False, "error": "Email is required"}
        
        if not isinstance(email, str):
            return {"valid": False, "error": "Email must be a string"}
        
        email = email.strip().lower()
        
        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return {"valid": False, "error": "Invalid email format"}
        
        if len(email) > 254:  # RFC 5321 limit
            return {"valid": False, "error": "Email address too long"}
        
        return {"valid": True, "normalized_email": email}
    
    @staticmethod
    def validate_username(username: str) -> Dict[str, Any]:
        \"\"\"Validate username format and requirements\"\"\"
        if not username:
            return {"valid": False, "error": "Username is required"}
        
        if not isinstance(username, str):
            return {"valid": False, "error": "Username must be a string"}
        
        username = username.strip()
        
        if len(username) < 3:
            return {"valid": False, "error": "Username must be at least 3 characters long"}
        
        if len(username) > 50:
            return {"valid": False, "error": "Username must be less than 50 characters"}
        
        # Allow alphanumeric characters, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return {"valid": False, "error": "Username can only contain letters, numbers, underscores, and hyphens"}
        
        return {"valid": True, "normalized_username": username}
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        \"\"\"Validate password strength\"\"\"
        if not password:
            return {"valid": False, "error": "Password is required"}
        
        if not isinstance(password, str):
            return {"valid": False, "error": "Password must be a string"}
        
        if len(password) < 8:
            return {"valid": False, "error": "Password must be at least 8 characters long"}
        
        if len(password) > 128:
            return {"valid": False, "error": "Password must be less than 128 characters"}
        
        # Check password strength
        strength_score = 0
        feedback = []
        
        if re.search(r'[a-z]', password):
            strength_score += 1
        else:
            feedback.append("Include lowercase letters")
        
        if re.search(r'[A-Z]', password):
            strength_score += 1
        else:
            feedback.append("Include uppercase letters")
        
        if re.search(r'[0-9]', password):
            strength_score += 1
        else:
            feedback.append("Include numbers")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            strength_score += 1
        else:
            feedback.append("Include special characters")
        
        if strength_score < 3:
            return {
                "valid": False, 
                "error": "Password is too weak",
                "feedback": feedback,
                "strength_score": strength_score
            }
        
        return {"valid": True, "strength_score": strength_score}
    
    @staticmethod
    def validate_phone_number(phone: str) -> Dict[str, Any]:
        \"\"\"Validate phone number format\"\"\"
        if not phone:
            return {"valid": False, "error": "Phone number is required"}
        
        if not isinstance(phone, str):
            return {"valid": False, "error": "Phone number must be a string"}
        
        # Remove all non-digit characters
        digits_only = re.sub(r'[^0-9]', '', phone)
        
        if len(digits_only) < 10:
            return {"valid": False, "error": "Phone number must have at least 10 digits"}
        
        if len(digits_only) > 15:
            return {"valid": False, "error": "Phone number must have at most 15 digits"}
        
        return {"valid": True, "normalized_phone": digits_only}
    
    @staticmethod
    def validate_date(date_str: str, date_format: str = "%Y-%m-%d") -> Dict[str, Any]:
        \"\"\"Validate date format and value\"\"\"
        if not date_str:
            return {"valid": False, "error": "Date is required"}
        
        if not isinstance(date_str, str):
            return {"valid": False, "error": "Date must be a string"}
        
        try:
            parsed_date = datetime.datetime.strptime(date_str, date_format)
            
            # Check if date is not in the future (for birth dates, etc.)
            if parsed_date.date() > datetime.date.today():
                return {"valid": False, "error": "Date cannot be in the future"}
            
            return {"valid": True, "parsed_date": parsed_date}
            
        except ValueError:
            return {"valid": False, "error": f"Invalid date format. Expected: {date_format}"}
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        \"\"\"Validate that all required fields are present and not empty\"\"\"
        missing_fields = []
        empty_fields = []
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                empty_fields.append(field)
        
        if missing_fields or empty_fields:
            error_parts = []
            if missing_fields:
                error_parts.append(f"Missing fields: {', '.join(missing_fields)}")
            if empty_fields:
                error_parts.append(f"Empty fields: {', '.join(empty_fields)}")
            
            return {"valid": False, "error": "; ".join(error_parts)}
        
        return {"valid": True}
"""
            }
        ],
        "ai_model": "llama3.2:3b",
        "session_id": "enhanced-test-case-generation-test"
    }
    
    print("Testing Enhanced Test Case Generation with Token Limit Support...")
    print(f"URL: {url}")
    print(f"Processing {len(payload['selected_scenarios'])} scenarios")
    print(f"Files: {len(payload['selected_files'])} files with substantial content")
    print(f"AI Model: {payload['ai_model']}")
    
    # Calculate approximate tokens
    total_content = payload['process_prompt']
    for file_info in payload['selected_files']:
        total_content += file_info['content']
    
    estimated_tokens = len(total_content.split())
    print(f"Estimated total tokens: {estimated_tokens}")
    
    if estimated_tokens > 4000:
        print("⚠️ Content exceeds 4000 tokens - system should auto-switch to qwen2.5:7b-1m")
    
    try:
        response = requests.post(url, json=payload, timeout=1200)  # 20 minutes timeout
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            response_json = response.json()
            print(f"Response keys: {list(response_json.keys())}")
            
            # Check test case results
            if 'test_case_results' in response_json:
                results = response_json['test_case_results']
                print(f"\n=== ENHANCED TEST CASE RESULTS ({len(results)} scenarios) ===")
                
                for i, result in enumerate(results):
                    scenario_id = result.get('scenario_id', 'Unknown')
                    status = result.get('status', 'Unknown')
                    title = result.get('scenario_title', 'Unknown')
                    
                    print(f"\nScenario {i+1}: {scenario_id}")
                    print(f"  Title: {title}")
                    print(f"  Status: {status}")
                    
                    if status == 'success':
                        test_cases = result.get('test_cases', [])
                        print(f"  Generated: {len(test_cases)} test cases")
                        
                        # Show enhanced test case structure
                        for j, tc in enumerate(test_cases[:2]):  # Show first 2
                            tc_title = tc.get('Title', f'Test Case {j+1}')
                            tc_category = tc.get('Category', 'Unknown')
                            tc_priority = tc.get('Priority', 'Unknown')
                            tc_steps = tc.get('TestSteps', [])
                            
                            print(f"    TC{j+1}: {tc_title}")
                            print(f"         Category: {tc_category} | Priority: {tc_priority}")
                            print(f"         Test Steps: {len(tc_steps)} steps")
                            
                            # Check for enhanced fields
                            has_enhanced = all(field in tc for field in ['Comments'])
                            print(f"         Enhanced Structure: {'✅' if has_enhanced else '❌'}")
                    else:
                        error = result.get('error', 'Unknown error')
                        print(f"  Error: {error}")
            
            # Check summary
            if 'summary' in response_json:
                summary = response_json['summary']
                print(f"\n=== SUMMARY ===")
                print(f"Total scenarios processed: {summary.get('scenarios_processed', 0)}")
                print(f"Successful scenarios: {summary.get('successful_scenarios', 0)}")
                print(f"Failed scenarios: {summary.get('failed_scenarios', 0)}")
                print(f"Total test cases generated: {summary.get('total_test_cases', 0)}")
                print(f"Model used: {summary.get('model_used', 'Unknown')}")
                
                # Check if model was switched
                final_model = summary.get('model_used', 'Unknown')
                if estimated_tokens > 4000 and 'qwen2.5:7b-1m' in final_model:
                    print("✅ Token limit system working - model was automatically switched!")
                elif estimated_tokens > 4000:
                    print("⚠️ Token limit may not be working properly")
                else:
                    print("✅ Content within limits - no model switch needed")
                
        else:
            print(f"Error response ({response.status_code}): {response.text}")
            
    except requests.exceptions.Timeout:
        print("Request timed out after 300 seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_enhanced_test_case_generation()
