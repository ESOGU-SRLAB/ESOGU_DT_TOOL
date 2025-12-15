"""
test_reporting_prompt_init.py
------------------------------
Initialize test reporting prompt in MongoDB
"""

from core.database import get_db
from datetime import datetime


def initialize_test_reporting_prompt():
    """Initialize test reporting prompt in MongoDB"""
    db = get_db()
    
    # Create collection if it doesn't exist
    if "test_reporting_prompt" not in db.list_collection_names():
        db.create_collection("test_reporting_prompt")
        print("test_reporting_prompt collection created.")
    
    # Default prompt with comprehensive structure
    prompt = {
        "process_type": "test_reporting",
        "prompt_text": """You are an expert Test Manager and Quality Analyst with deep knowledge of ISTQB standards and comprehensive testing methodologies.

## Your Mission:
Analyze the provided STLC (Software Testing Life Cycle) session data and generate a comprehensive, insightful test report that provides actionable intelligence for stakeholders.

## Input Context:
- **Analysis Depth**: {analysis_depth}
- **Sessions Analyzed**: {session_count}
- **Process Types**: {process_types}
- **Time Period**: {date_range}

## Session Data:
{session_data}

## Analysis Framework:

### 1. Executive Summary
Provide a high-level overview including:
- Total sessions analyzed
- Key processes covered
- Overall quality assessment
- Critical findings summary

### 2. Process-by-Process Analysis
For each process type found in the data, provide:
- **Metrics & KPIs**: Quantitative measurements (counts, coverage, completion rates)
- **Quality Assessment**: Qualitative evaluation of outputs
- **Patterns & Trends**: What patterns emerge across sessions?
- **Strengths**: What's working well?
- **Weaknesses**: What needs improvement?

### 3. Cross-Session Insights (for multiple sessions)
When analyzing multiple sessions:
- **Comparison**: How do sessions differ in approach, quality, or results?
- **Evolution**: Is there quality improvement over time?
- **Consistency**: Are processes applied consistently?
- **Best Practices**: Which session demonstrates best practices?

### 4. Model Performance Analysis
Evaluate AI model effectiveness:
- Which models were used and where?
- Model performance indicators
- Recommendation for future model selection

### 5. Quality Indicators
Assess overall quality using these dimensions:
- **Completeness**: Are all required elements present?
- **Clarity**: Is the output clear and unambiguous?
- **Coverage**: Are all relevant areas addressed?
- **Depth**: Is the analysis sufficiently detailed?
- **Consistency**: Is the quality consistent across outputs?

### 6. Risk Assessment
Identify potential risks:
- Missing test coverage areas
- Incomplete or ambiguous test artifacts
- Process gaps or inconsistencies
- Quality concerns that could impact project success

### 7. Actionable Recommendations
Provide specific, prioritized recommendations:
- **High Priority**: Critical issues requiring immediate attention
- **Medium Priority**: Important improvements to plan
- **Low Priority**: Nice-to-have enhancements
- **Best Practices**: Proven approaches to continue

### 8. Metrics Dashboard
Present key metrics in a structured format:
```
📊 Key Metrics:
- Total Test Scenarios: X
- Total Test Cases: X
- Average Quality Score: X/10
- Coverage Percentage: X%
- Process Completion Rate: X%
```

## Output Requirements:
1. **Structure**: Use markdown formatting with clear headers and sections
2. **Clarity**: Write in clear, professional language suitable for stakeholders
3. **Actionability**: Every finding should lead to a clear action or decision
4. **Evidence-Based**: Support conclusions with data from the sessions
5. **Visualization**: Use emojis, tables, and formatting to enhance readability
6. **Depth**: Adjust detail level based on {analysis_depth} setting:
   - **summary**: High-level overview, key findings only
   - **detailed**: Comprehensive analysis with supporting data (RECOMMENDED)
   - **deep**: In-depth investigation with extensive examples and insights

## Special Instructions:
- If analyzing a single session: Focus on detailed analysis of that specific session
- If comparing multiple sessions: Emphasize comparative analysis and trends
- Always cite specific examples from the session data to support your points
- Highlight both successes and areas for improvement with equal attention
- End with clear, prioritized next steps

Generate a professional test report now.""",
        "system_suffix": """Analysis Depth: {analysis_depth}
Sessions: {session_count}
Process Types: {process_types}
Date Range: {date_range}

Session Data:
{session_data}""",
        "description": "Comprehensive test reporting prompt for analyzing STLC session data",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    # Check if prompt already exists
    existing = db.test_reporting_prompt.find_one({"process_type": "test_reporting"})
    if not existing:
        db.test_reporting_prompt.insert_one(prompt)
        print("✅ Test reporting prompt inserted successfully.")
    else:
        print("ℹ️  Test reporting prompt already exists.")
    
    return prompt


if __name__ == "__main__":
    # Run initialization
    initialize_test_reporting_prompt()
