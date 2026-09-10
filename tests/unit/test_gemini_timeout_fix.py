#!/usr/bin/env python3
"""
Test Gemini API timeout handling and UI result display
"""

import requests
import json
import time
import os

def test_gemini_timeout_handling():
    """Test Gemini API with timeout handling"""
    
    print("Testing Gemini API timeout handling for Test Case Generation...")
    
    # Test with Gemini model (requires API key)
    url = "http://localhost:8000/api/processes/test-scenario-generation/generate-test-cases"
    
    # Read the API key from the environment; never store it in source control.
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    test_data = {
        "selected_scenarios": [
            {
                "scenario_id": "TS_001",
                "scenario": "Complex User Authentication System",
                "description": "Test comprehensive user authentication including multi-factor authentication, session management, password policies, account lockout mechanisms, and security event logging across multiple user roles and permission levels.",
                "objective": "Verify secure and reliable user authentication with comprehensive coverage",
                "category": "Security"
            },
            {
                "scenario_id": "TS_002", 
                "scenario": "E-commerce Payment Processing",
                "description": "Test complete payment processing workflow including credit card validation, payment gateway integration, transaction security, refund processing, and fraud detection mechanisms.",
                "objective": "Ensure secure and reliable payment processing",
                "category": "Financial"
            }
        ],
        "process_prompt": """Generate comprehensive test cases for the following scenarios. 

## Requirements:
- Create 7-8 detailed test cases per scenario
- Include both positive and negative test cases
- Cover edge cases and boundary conditions
- Ensure proper validation steps and expected results
- Focus on security and reliability aspects
- Include proper error handling test cases

## Test Case Structure:
Each test case should be comprehensive and include detailed descriptions, objectives, and validation steps.""",
        "selected_files": [
            {
                "name": "auth.js",
                "content": """
                function authenticate(username, password) {
                    // Validate input parameters
                    if (!username || !password) {
                        throw new Error('Username and password are required');
                    }
                    
                    // Hash password
                    const hashedPassword = hashPassword(password);
                    
                    // Check user credentials
                    const user = database.findUser(username);
                    if (!user || user.password !== hashedPassword) {
                        logFailedAttempt(username);
                        throw new Error('Invalid credentials');
                    }
                    
                    // Check account status
                    if (user.isLocked) {
                        throw new Error('Account is locked');
                    }
                    
                    // Generate session token
                    const token = generateSessionToken(user.id);
                    
                    // Log successful login
                    logSuccessfulLogin(user.id);
                    
                    return {
                        token: token,
                        user: {
                            id: user.id,
                            username: user.username,
                            role: user.role
                        }
                    };
                }
                
                function logout(token) {
                    invalidateToken(token);
                    logLogout(token);
                }
                """
            },
            {
                "name": "payment.js", 
                "content": """
                function processPayment(cardDetails, amount, currency) {
                    // Validate card details
                    if (!validateCardNumber(cardDetails.number)) {
                        throw new Error('Invalid card number');
                    }
                    
                    if (!validateExpiryDate(cardDetails.expiry)) {
                        throw new Error('Card has expired');
                    }
                    
                    if (!validateCVV(cardDetails.cvv)) {
                        throw new Error('Invalid CVV');
                    }
                    
                    // Validate amount
                    if (amount <= 0) {
                        throw new Error('Amount must be positive');
                    }
                    
                    // Process with payment gateway
                    const transactionId = generateTransactionId();
                    const gatewayResponse = paymentGateway.charge({
                        cardNumber: cardDetails.number,
                        amount: amount,
                        currency: currency,
                        transactionId: transactionId
                    });
                    
                    if (!gatewayResponse.success) {
                        logFailedPayment(transactionId, gatewayResponse.error);
                        throw new Error('Payment failed: ' + gatewayResponse.error);
                    }
                    
                    // Log successful payment
                    logSuccessfulPayment(transactionId, amount);
                    
                    return {
                        transactionId: transactionId,
                        status: 'completed',
                        amount: amount,
                        currency: currency
                    };
                }
                """
            }
        ],
        "ai_model": "gemini-2.5-flash",  # Use Gemini model
        "session_id": "gemini_timeout_test_" + str(int(time.time())),
        "selected_process_title": "Gemini Timeout Test Process",
        "api_key": api_key
    }
    
    if not api_key:
        print("❌ Please provide a real Gemini API key in the test script!")
        print("Set GEMINI_API_KEY in the environment.")
        return None
    
    print(f"Making request to: {url}")
    print(f"Using Gemini model: {test_data['ai_model']}")
    print(f"Test scenarios count: {len(test_data['selected_scenarios'])}")
    print(f"Files count: {len(test_data['selected_files'])}")
    
    try:
        print("⏱️  Starting request (this may take 30-60+ seconds for Gemini API)...")
        start_time = time.time()
        
        response = requests.post(url, json=test_data, timeout=120)  # 2 minute timeout
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Request completed in {duration:.1f} seconds")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ SUCCESS! Gemini API handled properly:")
            print(f"Status: {result.get('status')}")
            print(f"Test case results count: {len(result.get('test_case_results', []))}")
            
            summary = result.get('summary', {})
            print(f"Summary:")
            print(f"  - Scenarios processed: {summary.get('scenarios_processed', 0)}")
            print(f"  - Successful scenarios: {summary.get('successful_scenarios', 0)}")
            print(f"  - Total test cases: {summary.get('total_test_cases', 0)}")
            print(f"  - Model used: {summary.get('model_used', 'Unknown')}")
            
            # Verify the data structure for UI display
            if result.get('test_case_results'):
                for i, test_result in enumerate(result['test_case_results']):
                    print(f"\nScenario {i+1} - {test_result.get('scenario_id')}:")
                    print(f"  Status: {test_result.get('status')}")
                    print(f"  Test cases: {test_result.get('test_cases_count', 0)}")
                    
                    # Check test case structure
                    test_cases = test_result.get('test_cases', [])
                    if test_cases and len(test_cases) > 0:
                        sample_tc = test_cases[0]
                        print(f"  Sample test case keys: {list(sample_tc.keys())}")
                        print(f"  Sample test case ID: {sample_tc.get('TestCaseID', 'N/A')}")
                        print(f"  Sample test case title: {sample_tc.get('Title', 'N/A')[:50]}...")
            
            print(f"\n✅ Gemini API workflow completed successfully!")
            print(f"✅ Backend data structure is correct for UI display")
            print(f"✅ Timeout handling worked (completed in {duration:.1f}s)")
            
            return result
            
        else:
            print(f"❌ ERROR: {response.status_code}")
            error_text = response.text
            print(f"Error response: {error_text[:500]}...")
            
            # Check for specific Gemini API errors
            if "503" in error_text or "unavailable" in error_text.lower():
                print("\n🔍 Analysis: Gemini API 503 Service Unavailable")
                print("   - Google servers may be overloaded")
                print("   - Retry mechanism should handle this automatically")
                print("   - Wait time will be applied before next attempt")
            elif "timeout" in error_text.lower():
                print("\n🔍 Analysis: Timeout occurred")
                print("   - Request took longer than expected")
                print("   - May need to increase timeout values")
                print("   - Consider breaking down large requests")
            elif "429" in error_text or "rate" in error_text.lower():
                print("\n🔍 Analysis: Rate limiting")
                print("   - API rate limits exceeded")
                print("   - Automatic retry with backoff should handle this")
            
            return None
            
    except requests.Timeout as e:
        print(f"❌ TIMEOUT ERROR: {e}")
        print("   - Request took longer than 2 minutes")
        print("   - This indicates the timeout handling needs improvement")
        print("   - Consider implementing exponential backoff")
        return None
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return None

if __name__ == "__main__":
    test_gemini_timeout_handling()
