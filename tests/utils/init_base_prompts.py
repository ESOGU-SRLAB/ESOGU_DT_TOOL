from pymongo import MongoClient
import json

def initialize_base_prompts():
    client = MongoClient('mongodb://localhost:27017')
    db = client['stlc_database']
    collection = db['test_scenario_generation_prompt']
    
    # Check if collection has any data
    count = collection.count_documents({})
    print(f'Current collection count: {count}')
      # Define base prompts for different test types under categories
    base_prompts = [
        # FUNCTIONAL TESTING CATEGORY
        {
            "test_category": "Functional Testing",
            "test_type": "Frontend Testing",
            "base_prompt": """Generate comprehensive functional test scenarios for frontend applications. Focus on user interface interactions, form validations, navigation flows, and user experience aspects. 

Key testing areas to cover:
- User interface functionality
- Input validation and error handling
- Navigation and routing
- Data display and formatting
- User interactions and workflows

Each test scenario should verify that the frontend components work as expected and provide a seamless user experience.""",
            "scoring_elements": ["Test Coverage", "Edge Case Handling", "User Experience", "Error Scenarios"],
            "instruction_elements": ["Step-by-step validation", "Expected vs Actual results", "Boundary testing", "Cross-browser compatibility"]
        },
        {
            "test_category": "Functional Testing", 
            "test_type": "Backend Testing",
            "base_prompt": """Generate comprehensive functional test scenarios for backend services and APIs. Focus on business logic validation, data processing, API endpoints, and system integrations.

Key testing areas to cover:
- API endpoint functionality
- Data validation and processing
- Business logic implementation
- Database operations
- Service integrations
- Authentication and authorization

Each test scenario should verify that the backend services process requests correctly and return appropriate responses.""",
            "scoring_elements": ["API Coverage", "Data Integrity", "Business Logic", "Error Handling"],
            "instruction_elements": ["Request-response validation", "Database state verification", "Integration testing", "Performance considerations"]
        },
        {
            "test_category": "Functional Testing",
            "test_type": "API Testing",
            "base_prompt": """Generate comprehensive functional test scenarios for API endpoints. Focus on request-response validation, data integrity, and service communication.

Key testing areas to cover:
- Endpoint functionality validation
- Request parameter validation
- Response format verification
- Error handling and status codes
- Authentication and authorization
- Data consistency checks

Each test scenario should verify that APIs behave correctly under various conditions and handle edge cases appropriately.""",
            "scoring_elements": ["API Coverage", "Data Validation", "Error Handling", "Authentication"],
            "instruction_elements": ["Request-response validation", "Status code verification", "Data format checking", "Error scenario testing"]
        },
        
        # NON-FUNCTIONAL TESTING CATEGORY
        {
            "test_category": "Non-Functional Testing",
            "test_type": "Performance Testing",
            "base_prompt": """Generate comprehensive performance test scenarios to evaluate system performance under various load conditions. Focus on response times, throughput, and resource utilization.

Key testing areas to cover:
- System response times under load
- Throughput and concurrent user handling
- Resource utilization monitoring
- Performance bottleneck identification
- Scalability assessment
- Stress and spike testing

Each test scenario should measure and validate system performance metrics under different load patterns.""",
            "scoring_elements": ["Response Time", "Throughput", "Resource Usage", "Scalability"],
            "instruction_elements": ["Load simulation", "Performance metrics", "Monitoring setup", "Baseline comparison"]
        },
        {
            "test_category": "Non-Functional Testing",
            "test_type": "Security Testing",
            "base_prompt": """Generate comprehensive security test scenarios to identify vulnerabilities and verify security controls. Focus on authentication, authorization, data protection, and system hardening.

Key testing areas to cover:
- Authentication and session management
- Authorization and access controls
- Input validation and injection attacks
- Data encryption and protection
- Security configuration testing
- Vulnerability assessment

Each test scenario should identify potential security risks and verify proper implementation of security measures.""",
            "scoring_elements": ["Security Coverage", "Vulnerability Detection", "Access Control", "Data Protection"],
            "instruction_elements": ["Security validation", "Penetration testing", "Compliance checking", "Risk assessment"]
        },
        {
            "test_category": "Non-Functional Testing",
            "test_type": "Usability Testing",
            "base_prompt": """Generate comprehensive usability test scenarios to evaluate user experience and interface design. Focus on user workflow efficiency, accessibility, and overall user satisfaction.

Key testing areas to cover:
- User interface intuitiveness
- Navigation efficiency
- Accessibility compliance
- User workflow optimization
- Error message clarity
- Mobile responsiveness

Each test scenario should assess how effectively users can accomplish their tasks and identify areas for UX improvement.""",
            "scoring_elements": ["User Experience", "Accessibility", "Navigation Efficiency", "Error Handling"],
            "instruction_elements": ["User journey testing", "Accessibility validation", "Cross-device testing", "User feedback collection"]
        }
    ]
    
    # Insert base prompts if collection is empty
    if count == 0:
        result = collection.insert_many(base_prompts)
        print(f'Inserted {len(result.inserted_ids)} base prompts')
    else:
        print('Collection already has data. Skipping initialization.')
          # Show current data
    docs = list(collection.find({}, {"test_category": 1, "test_type": 1, "_id": 0}))
    print('Available base prompts:')
    for doc in docs:
        print(f"  - {doc.get('test_category')} > {doc.get('test_type')}")
    
    client.close()

if __name__ == "__main__":
    initialize_base_prompts()
