"""
test_reporting_prompt_init_v3.py
---------------------------------
Initialize test reporting prompt with JSON output and few-shot examples
"""

from core.database import get_db
from datetime import datetime


def initialize_test_reporting_prompt():
    """Initialize test reporting prompt with JSON structured output"""
    db = get_db()
    
    # Create collection if it doesn't exist
    if "test_reporting_prompt" not in db.list_collection_names():
        db.create_collection("test_reporting_prompt")
        print("✅ test_reporting_prompt collection created.")
    
    # JSON-focused prompt with few-shot examples
    prompt = {
        "process_type": "test_reporting",
        "prompt_text": """You are an expert Test Manager analyzing STLC (Software Testing Life Cycle) processes.

## 📋 ANALYSIS CONTEXT
- **Depth**: {analysis_depth} | **Sessions**: {session_count} | **Processes**: {process_types}
- **Period**: {date_range}

## 📊 RAW SESSION DATA
{session_data}

---

## 🎯 OUTPUT FORMAT: STRUCTURED JSON

You MUST return a valid JSON object with the following structure. Here are examples:

### EXAMPLE 1: Single Session Report

```json
{
  "reportType": "single-session",
  "executiveSummary": {
    "sessionsAnalyzed": 1,
    "processesCount": 3,
    "overallQuality": 8.5,
    "qualityJustification": "High-quality test scenarios with good coverage, minor gaps in edge cases",
    "criticalInsight": "Test case optimization achieved 35% reduction while maintaining coverage"
  },
  "sessions": [
    {
      "sessionName": "Sprint 3 Testing",
      "sessionId": "abc123...",
      "timestamp": "2025-11-07T10:00:00",
      "qualityScore": 8.5,
      "status": "good",
      "processes": [
        {
          "processType": "test_scenario_generation",
          "processName": "Test Scenario Generation",
          "metrics": [
            {"name": "Scenarios Generated", "value": "45", "trend": "up", "notes": "15% increase from baseline"},
            {"name": "Coverage Types", "value": "Functional(25), Edge(15), Negative(5)", "trend": "stable", "notes": "Well-balanced distribution"},
            {"name": "Completeness", "value": "92%", "trend": "up", "notes": "Most scenarios have clear steps"}
          ],
          "quality": {
            "score": 8.0,
            "completeness": 9,
            "clarity": 8,
            "coverage": 8,
            "depth": 7
          },
          "strengths": [
            "Comprehensive functional coverage",
            "Clear preconditions and expected results",
            "Good edge case identification"
          ],
          "weaknesses": [
            "Limited performance test scenarios",
            "Some scenarios lack specific test data"
          ],
          "modelUsed": "gemini-2.5-flash"
        },
        {
          "processType": "test_case_generation",
          "processName": "Test Case Generation",
          "metrics": [
            {"name": "Test Cases Generated", "value": "180", "trend": "up", "notes": "4x scenarios"},
            {"name": "Positive/Negative Ratio", "value": "120/60", "trend": "stable", "notes": "2:1 ratio maintained"},
            {"name": "Complexity Distribution", "value": "Simple(60), Medium(90), Complex(30)", "trend": "stable", "notes": "Balanced mix"}
          ],
          "quality": {
            "score": 8.5,
            "completeness": 9,
            "clarity": 9,
            "coverage": 8,
            "depth": 8
          },
          "strengths": [
            "Well-structured test cases",
            "Clear test data specifications",
            "Good balance of positive/negative tests"
          ],
          "weaknesses": [
            "Some boundary value tests missing",
            "Limited error handling scenarios"
          ],
          "modelUsed": "llama3.2:3b"
        }
      ]
    }
  ],
  "crossSessionAnalysis": null,
  "qualityAssessment": {
    "completeness": {"score": 9, "reason": "All required test artifacts generated"},
    "clarity": {"score": 8, "reason": "Clear descriptions, minor ambiguities in edge cases"},
    "coverage": {"score": 8, "reason": "Good functional coverage, gaps in performance testing"},
    "depth": {"score": 7, "reason": "Adequate detail level, some scenarios need more specifics"}
  },
  "risks": {
    "high": [
      {"issue": "Performance testing not covered", "impact": "Critical bottlenecks may go undetected", "mitigation": "Add performance test scenarios for core features"}
    ],
    "medium": [
      {"issue": "Incomplete test data specifications", "impact": "Execution delays during testing phase", "mitigation": "Review and complete test data for all cases"}
    ],
    "low": [
      {"issue": "Minor documentation gaps", "impact": "Small delays in test execution", "mitigation": "Add missing preconditions to 5 scenarios"}
    ]
  },
  "recommendations": {
    "immediate": [
      {"action": "Add performance test scenarios", "outcome": "Critical bottlenecks identified early", "priority": 1},
      {"action": "Complete test data specifications", "outcome": "Smooth test execution", "priority": 2}
    ],
    "shortTerm": [
      {"action": "Review boundary value coverage", "outcome": "Improved edge case detection", "priority": 3}
    ],
    "longTerm": [
      {"action": "Establish test scenario templates", "outcome": "Consistent quality across sprints", "priority": 4}
    ]
  },
  "metrics": {
    "totalSessions": 1,
    "totalProcesses": 3,
    "totalArtifacts": 225,
    "averageQuality": 8.5,
    "coverageRate": "85%",
    "processSummary": [
      {"process": "Test Scenario Generation", "count": 45, "quality": 8.0},
      {"process": "Test Case Generation", "count": 180, "quality": 8.5}
    ]
  }
}
```

### EXAMPLE 2: Multi-Session Comparison Report

```json
{
  "reportType": "multi-session",
  "executiveSummary": {
    "sessionsAnalyzed": 3,
    "processesCount": 4,
    "overallQuality": 7.8,
    "qualityJustification": "Improving trend across sessions, Session 3 shows 25% quality improvement",
    "criticalInsight": "Test case optimization effectiveness increased from 15% to 35% reduction rate"
  },
  "sessions": [
    {
      "sessionName": "Sprint 1 Testing",
      "sessionId": "session1",
      "timestamp": "2025-11-01",
      "qualityScore": 7.0,
      "status": "review",
      "processes": [
        {
          "processType": "test_scenario_generation",
          "processName": "Test Scenario Generation",
          "metrics": [
            {"name": "Scenarios Generated", "value": "30", "trend": "stable", "notes": "Baseline"},
            {"name": "Coverage Types", "value": "Functional(20), Edge(8), Negative(2)", "trend": "stable", "notes": "Focus on functional"}
          ],
          "quality": {"score": 7.0, "completeness": 7, "clarity": 7, "coverage": 7, "depth": 6},
          "modelUsed": "llama3.2:3b"
        }
      ]
    },
    {
      "sessionName": "Sprint 2 Testing",
      "sessionId": "session2",
      "timestamp": "2025-11-04",
      "qualityScore": 7.5,
      "status": "good",
      "processes": [
        {
          "processType": "test_scenario_generation",
          "processName": "Test Scenario Generation",
          "metrics": [
            {"name": "Scenarios Generated", "value": "38", "trend": "up", "notes": "27% increase"},
            {"name": "Coverage Types", "value": "Functional(22), Edge(12), Negative(4)", "trend": "up", "notes": "Better balance"}
          ],
          "quality": {"score": 7.5, "completeness": 8, "clarity": 8, "coverage": 7, "depth": 7},
          "modelUsed": "gemini-2.5-flash"
        }
      ]
    },
    {
      "sessionName": "Sprint 3 Testing",
      "sessionId": "session3",
      "timestamp": "2025-11-07",
      "qualityScore": 8.5,
      "status": "excellent",
      "processes": [
        {
          "processType": "test_scenario_generation",
          "processName": "Test Scenario Generation",
          "metrics": [
            {"name": "Scenarios Generated", "value": "45", "trend": "up", "notes": "50% increase from Sprint 1"},
            {"name": "Coverage Types", "value": "Functional(25), Edge(15), Negative(5)", "trend": "up", "notes": "Excellent balance"}
          ],
          "quality": {"score": 8.5, "completeness": 9, "clarity": 9, "coverage": 8, "depth": 8},
          "modelUsed": "gemini-2.5-flash"
        }
      ]
    }
  ],
  "crossSessionAnalysis": {
    "trends": [
      {"metric": "Quality Score", "trend": "up", "change": "+21%", "sessions": [7.0, 7.5, 8.5], "insight": "Consistent improvement across all sessions"},
      {"metric": "Scenario Count", "trend": "up", "change": "+50%", "sessions": [30, 38, 45], "insight": "Increased productivity while maintaining quality"},
      {"metric": "Edge Case Coverage", "trend": "up", "change": "+88%", "sessions": [8, 12, 15], "insight": "Significantly improved edge case identification"}
    ],
    "bestPractices": [
      {"session": "Sprint 3 Testing", "practice": "Comprehensive coverage planning before generation", "impact": "Highest quality score achieved"},
      {"session": "Sprint 2 Testing", "practice": "Model selection based on complexity", "impact": "Better balance of test types"}
    ],
    "regressions": [
      {"session": "Sprint 1 Testing", "issue": "Low edge case coverage", "impact": "Potential bugs missed", "resolved": true}
    ],
    "comparison": [
      {
        "sessionName": "Sprint 1 Testing",
        "quality": 7.0,
        "coverage": "75%",
        "issuesFound": 5,
        "status": "review"
      },
      {
        "sessionName": "Sprint 2 Testing",
        "quality": 7.5,
        "coverage": "82%",
        "issuesFound": 3,
        "status": "good"
      },
      {
        "sessionName": "Sprint 3 Testing",
        "quality": 8.5,
        "coverage": "92%",
        "issuesFound": 1,
        "status": "excellent"
      }
    ]
  },
  "qualityAssessment": {
    "completeness": {"score": 8, "reason": "Improving coverage across sessions"},
    "clarity": {"score": 8, "reason": "Clear improvement in documentation quality"},
    "coverage": {"score": 8, "reason": "92% coverage achieved in latest session"},
    "depth": {"score": 7, "reason": "Good detail level, minor improvements needed"}
  },
  "risks": {
    "high": [],
    "medium": [
      {"issue": "Model consistency varies", "impact": "Quality fluctuations possible", "mitigation": "Standardize on gemini-2.5-flash for critical processes"}
    ],
    "low": [
      {"issue": "Documentation format variations", "impact": "Minor readability issues", "mitigation": "Create documentation templates"}
    ]
  },
  "recommendations": {
    "immediate": [
      {"action": "Adopt Sprint 3 best practices across all future sprints", "outcome": "Maintain high quality standards", "priority": 1}
    ],
    "shortTerm": [
      {"action": "Standardize model selection criteria", "outcome": "Consistent quality output", "priority": 2}
    ],
    "longTerm": [
      {"action": "Establish quality baselines and KPIs", "outcome": "Track improvement trends systematically", "priority": 3}
    ]
  },
  "metrics": {
    "totalSessions": 3,
    "totalProcesses": 3,
    "totalArtifacts": 113,
    "averageQuality": 7.8,
    "coverageRate": "83%",
    "processSummary": [
      {"process": "Test Scenario Generation", "count": 113, "quality": 7.8}
    ]
  }
}
```

---

## 📝 YOUR TASK

Based on the RAW SESSION DATA and INTERMEDIATE SUMMARIES provided above, generate a comprehensive test report in **EXACTLY THE SAME JSON FORMAT** as the examples.

### JSON Schema Requirements:

1. **reportType**: "single-session" or "multi-session"
2. **executiveSummary**: High-level overview with scores and insights
3. **sessions**: Array of session objects with processes and metrics
4. **crossSessionAnalysis**: Only for multi-session (trends, comparisons, best practices)
5. **qualityAssessment**: 4 dimensions rated 1-10 with reasons
6. **risks**: Categorized by severity (high/medium/low)
7. **recommendations**: Categorized by urgency (immediate/shortTerm/longTerm)
8. **metrics**: Overall statistics and process summary

### Important Rules:

- **trend** values: "up" | "down" | "stable"
- **status** values: "excellent" | "good" | "review" | "critical"
- **scores**: Use 1-10 scale
- **dates**: ISO 8601 format
- **All strings**: Use actual session names, not IDs
- **Be data-driven**: Every metric must come from raw data
- **No placeholders**: Use real values, not "X" or "N/A"

### Analysis Depth Adaptation:

- **summary**: Focus on executiveSummary, top 3 metrics, critical risks only
- **detailed**: All sections with key metrics and insights (RECOMMENDED)
- **deep**: All sections with extensive metrics, examples, and detailed reasoning

Generate the JSON report now. Return ONLY valid JSON, no markdown code blocks, no explanations.""",
        "system_suffix": """Analysis Depth: {analysis_depth}
Sessions: {session_count}
Process Types: {process_types}
Date Range: {date_range}

RAW SESSION DATA:
{session_data}

INTERMEDIATE SUMMARIES:
{intermediate_summaries}

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no extra text.""",
        "description": "Test reporting prompt with JSON structured output and few-shot examples",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    # Update or insert
    result = db.test_reporting_prompt.update_one(
        {"process_type": "test_reporting"},
        {"$set": prompt},
        upsert=True
    )
    
    if result.matched_count > 0:
        print("✅ Test reporting prompt UPDATED with JSON few-shot examples.")
    else:
        print("✅ Test reporting prompt INSERTED with JSON few-shot examples.")
    
    return prompt


if __name__ == "__main__":
    # Run initialization
    initialize_test_reporting_prompt()
