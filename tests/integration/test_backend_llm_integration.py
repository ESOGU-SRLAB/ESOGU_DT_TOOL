#!/usr/bin/env python3
"""
Test script to replicate the exact backend LLM call
"""

import sys
import os

# Add backend directory to path so we can import from backend
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.append(backend_dir)

from utils.model_client import get_llm_instance, LLMClient
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_langchain_client():
    """Test the LangChain ChatOpenAI client"""
    print("=== Testing LangChain ChatOpenAI Client ===")
    
    try:
        # This is how our backend creates the LLM client
        llm = get_llm_instance()
        print(f"LLM instance created successfully: {llm}")
        
        # Test with a simple message
        test_message = "Hello, this is a test. Please respond with 'LangChain test successful'."
        print(f"Sending test message: {test_message}")
        
        response = llm.invoke(test_message)
        print(f"Response: {response}")
        print(f"Response content: {response.content}")
        
    except Exception as e:
        print(f"Error with LangChain client: {e}")
        import traceback
        traceback.print_exc()

async def test_direct_client():
    """Test the direct LLMClient"""
    print("\n=== Testing Direct LLMClient ===")
    
    try:
        # Test the direct client
        client = LLMClient(model_name="llama-3.2-3b-instruct")
        
        test_prompt = "Hello, this is a test. Please respond with 'Direct client test successful'."
        print(f"Sending test prompt: {test_prompt}")
        
        response = await client.generate_response(test_prompt)
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Error with direct client: {e}")
        import traceback
        traceback.print_exc()

async def test_scenario_generation():
    """Test the scenario generation process"""
    print("\n=== Testing Scenario Generation Process ===")
    
    try:
        from stlc.test_scenario_generation import run_step
        
        # Test data similar to what would come from frontend
        test_data = {
            "model": "llama3.2:3b",
            "files": [],
            "final_prompt": "Generate test scenarios for a simple login functionality. Include positive and negative test cases for username and password validation.",
            "test_type": "functional",
            "test_category": "authentication",
            "process_title": "Login Test Scenarios",
            "session_id": "test-session-123"
        }
        
        print(f"Testing scenario generation with data: {test_data}")
        
        result = await run_step(test_data)
        print(f"Scenario generation result: {result}")
        
    except Exception as e:
        print(f"Error with scenario generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test LangChain client
    test_langchain_client()
    
    # Test direct client
    asyncio.run(test_direct_client())
    
    # Test scenario generation
    asyncio.run(test_scenario_generation())
