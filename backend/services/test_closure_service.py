"""
test_closure_service.py
-----------------------
Test Closure Service - AI-Powered Test Cycle Closure Report Generation
Aggregates all STLC process data and generates comprehensive closure reports
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from core.database import get_database

logger = logging.getLogger(__name__)


class TestClosureService:
    """
    Service for generating AI-powered test closure reports
    Aggregates data from all STLC processes and creates comprehensive closure analysis
    """
    
    def __init__(self):
        self.db = None
    
    async def initialize(self):
        """Initialize database connection"""
        if self.db is None:
            self.db = await get_database()
    
    async def fetch_sessions_for_closure(
        self,
        session_ids: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch sessions for test closure analysis
        
        Args:
            session_ids: Specific session IDs to include
            date_from: Start date (ISO format)
            date_to: End date (ISO format)
            
        Returns:
            List of session documents
        """
        await self.initialize()
        collection = self.db["session_history"]
        
        # Build query
        query = {}
        
        if session_ids:
            query["session_id"] = {"$in": session_ids}
        
        if date_from or date_to:
            query["created_at"] = {}
            if date_from:
                query["created_at"]["$gte"] = date_from
            if date_to:
                query["created_at"]["$lte"] = date_to
        
        # Fetch sessions
        cursor = collection.find(query).sort("created_at", -1)
        sessions = await cursor.to_list(length=None)
        
        return sessions
    
    def aggregate_test_metrics(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate test execution metrics from sessions
        
        Returns comprehensive metrics including:
        - Test scenario counts
        - Test case counts
        - Execution results (pass/fail)
        - Coverage metrics
        - Defect analysis
        """
        metrics = {
            "total_sessions": len(sessions),
            "test_scenarios": {
                "total": 0,
                "by_type": {},
                "by_category": {}
            },
            "test_cases": {
                "total_generated": 0,
                "total_optimized": 0,
                "optimization_rate": 0,
                "by_scenario": {}
            },
            "test_execution": {
                "total_executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "pass_rate": 0,
                "execution_time": 0
            },
            "coverage": {
                "scenario_coverage": 0,
                "requirement_coverage": 0,
                "code_coverage": "N/A"
            },
            "defects": {
                "total": 0,
                "critical": 0,
                "major": 0,
                "minor": 0,
                "from_failed_tests": []
            },
            "effort": {
                "test_planning": 0,
                "test_design": 0,
                "test_execution": 0,
                "total_hours": 0
            },
            "models_used": set(),
            "session_ids": [],
            "date_range": {
                "start": None,
                "end": None
            }
        }
        
        # Process each session
        for session in sessions:
            session_id = session.get("session_id", "unknown")
            metrics["session_ids"].append(session_id)
            
            # Update date range
            created_at = session.get("created_at")
            if created_at:
                if not metrics["date_range"]["start"] or created_at < metrics["date_range"]["start"]:
                    metrics["date_range"]["start"] = created_at
                if not metrics["date_range"]["end"] or created_at > metrics["date_range"]["end"]:
                    metrics["date_range"]["end"] = created_at
            
            processes = session.get("processes", {})
            
            # Aggregate Test Scenario Generation
            if "test_scenario_generation" in processes:
                tsg = processes["test_scenario_generation"]
                output = tsg.get("output", {})
                
                # Track model used
                model = tsg.get("used_model")
                if model:
                    metrics["models_used"].add(model)
                
                # Count scenarios
                test_scenarios = output.get("test_scenarios", {})
                scenarios = test_scenarios.get("TestScenarios", [])
                metrics["test_scenarios"]["total"] += len(scenarios)
                
                # Count by type and category
                test_type = output.get("metadata", {}).get("test_type", "Unknown")
                test_category = output.get("metadata", {}).get("test_category", "Unknown")
                
                metrics["test_scenarios"]["by_type"][test_type] = \
                    metrics["test_scenarios"]["by_type"].get(test_type, 0) + len(scenarios)
                
                for scenario in scenarios:
                    category = scenario.get("Category", "Unknown")
                    metrics["test_scenarios"]["by_category"][category] = \
                        metrics["test_scenarios"]["by_category"].get(category, 0) + 1
            
            # Aggregate Test Case Generation
            if "test_case_generation" in processes:
                tcg = processes["test_case_generation"]
                output = tcg.get("output", {})
                
                # Track model used
                model = tcg.get("used_model")
                if model:
                    metrics["models_used"].add(model)
                
                # Count test cases
                data = output.get("data", {})
                test_case_results = data.get("test_case_results", [])
                
                for result in test_case_results:
                    test_cases = result.get("test_cases", [])
                    metrics["test_cases"]["total_generated"] += len(test_cases)
                    
                    # Track by scenario
                    scenario_id = result.get("scenario_id", "unknown")
                    if scenario_id not in metrics["test_cases"]["by_scenario"]:
                        metrics["test_cases"]["by_scenario"][scenario_id] = {
                            "generated": 0,
                            "optimized": 0
                        }
                    metrics["test_cases"]["by_scenario"][scenario_id]["generated"] += len(test_cases)
            
            # Aggregate Test Case Optimization
            if "test_case_optimization" in processes:
                tco = processes["test_case_optimization"]
                output = tco.get("output", {})
                
                # Track model used
                model = tco.get("used_model")
                if model:
                    metrics["models_used"].add(model)
                
                # Count optimized test cases
                optimized_test_cases = output.get("optimized_test_cases", [])
                metrics["test_cases"]["total_optimized"] += len(optimized_test_cases)
            
            # Aggregate Test Code Generation
            if "test_code_generation" in processes:
                tcg = processes["test_code_generation"]
                
                # Track model used
                model = tcg.get("used_model")
                if model:
                    metrics["models_used"].add(model)
            
            # Aggregate Test Execution
            if "test_execution" in processes:
                te = processes["test_execution"]
                output = te.get("output", {})
                
                # Track model used
                model = te.get("used_model")
                if model:
                    metrics["models_used"].add(model)
                
                # Parse execution results
                terminal_output = output.get("terminal_output", "")
                execution_results = self._parse_execution_results(terminal_output)
                
                metrics["test_execution"]["total_executed"] += execution_results["total"]
                metrics["test_execution"]["passed"] += execution_results["passed"]
                metrics["test_execution"]["failed"] += execution_results["failed"]
                metrics["test_execution"]["skipped"] += execution_results["skipped"]
                
                # Track failed tests as defects
                for failed_test in execution_results["failed_tests"]:
                    metrics["defects"]["from_failed_tests"].append({
                        "session_id": session_id,
                        "test_name": failed_test,
                        "severity": "major"  # Default severity
                    })
            
            # Aggregate Test Reporting
            if "test_reporting" in processes:
                tr = processes["test_reporting"]
                
                # Track model used
                model = tr.get("used_model")
                if model:
                    metrics["models_used"].add(model)
        
        # Calculate derived metrics
        if metrics["test_cases"]["total_generated"] > 0:
            metrics["test_cases"]["optimization_rate"] = round(
                (metrics["test_cases"]["total_optimized"] / metrics["test_cases"]["total_generated"]) * 100, 
                2
            )
        
        if metrics["test_execution"]["total_executed"] > 0:
            metrics["test_execution"]["pass_rate"] = round(
                (metrics["test_execution"]["passed"] / metrics["test_execution"]["total_executed"]) * 100,
                2
            )
        
        # Defect counts from failed tests
        metrics["defects"]["total"] = len(metrics["defects"]["from_failed_tests"])
        metrics["defects"]["major"] = len(metrics["defects"]["from_failed_tests"])  # All failures as major by default
        
        # Coverage calculation
        if metrics["test_scenarios"]["total"] > 0:
            metrics["coverage"]["scenario_coverage"] = 100  # Assuming all scenarios are covered
        
        # Convert set to list for JSON serialization
        metrics["models_used"] = list(metrics["models_used"])
        
        return metrics
    
    def _parse_execution_results(self, terminal_output: str) -> Dict[str, Any]:
        """
        Parse test execution terminal output to extract results
        
        Returns:
            Dictionary with execution statistics
        """
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failed_tests": []
        }
        
        if not terminal_output:
            return results
        
        # Try to parse pytest output
        import re
        
        # Look for pytest summary line: "X passed, Y failed, Z skipped"
        summary_pattern = r'(\d+)\s+passed'
        failed_pattern = r'(\d+)\s+failed'
        skipped_pattern = r'(\d+)\s+skipped'
        
        passed_match = re.search(summary_pattern, terminal_output)
        failed_match = re.search(failed_pattern, terminal_output)
        skipped_match = re.search(skipped_pattern, terminal_output)
        
        if passed_match:
            results["passed"] = int(passed_match.group(1))
        if failed_match:
            results["failed"] = int(failed_match.group(1))
        if skipped_match:
            results["skipped"] = int(skipped_match.group(1))
        
        results["total"] = results["passed"] + results["failed"] + results["skipped"]
        
        # Extract failed test names
        failed_test_pattern = r'FAILED\s+([\w\.\:\/]+)'
        failed_tests = re.findall(failed_test_pattern, terminal_output)
        results["failed_tests"] = failed_tests
        
        return results
    
    def generate_closure_prompt(self, metrics: Dict[str, Any]) -> str:
        """
        Generate AI prompt for test closure report generation
        
        Args:
            metrics: Aggregated test metrics
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an ISTQB-certified Test Manager generating a comprehensive Test Closure Report.

# TEST CYCLE INFORMATION
- Total Sessions Analyzed: {metrics['total_sessions']}
- Session IDs: {', '.join(metrics['session_ids'][:5])}{'...' if len(metrics['session_ids']) > 5 else ''}
- Date Range: {metrics['date_range']['start']} to {metrics['date_range']['end']}
- Models Used: {', '.join(metrics['models_used'])}

# TEST EXECUTION SUMMARY
## Test Scenarios
- Total Scenarios Generated: {metrics['test_scenarios']['total']}
- Scenarios by Type: {json.dumps(metrics['test_scenarios']['by_type'], indent=2)}
- Scenarios by Category: {json.dumps(metrics['test_scenarios']['by_category'], indent=2)}

## Test Cases
- Total Test Cases Generated: {metrics['test_cases']['total_generated']}
- Total Test Cases Optimized: {metrics['test_cases']['total_optimized']}
- Optimization Rate: {metrics['test_cases']['optimization_rate']}%

## Test Execution Results
- Total Tests Executed: {metrics['test_execution']['total_executed']}
- Passed: {metrics['test_execution']['passed']} ({metrics['test_execution']['pass_rate']}%)
- Failed: {metrics['test_execution']['failed']}
- Skipped: {metrics['test_execution']['skipped']}

## Coverage Analysis
- Scenario Coverage: {metrics['coverage']['scenario_coverage']}%
- Requirement Coverage: {metrics['coverage']['requirement_coverage']}%

## Defect Summary
- Total Defects Identified: {metrics['defects']['total']}
- Critical: {metrics['defects']['critical']}
- Major: {metrics['defects']['major']}
- Minor: {metrics['defects']['minor']}

# FAILED TESTS (Potential Defects)
{json.dumps(metrics['defects']['from_failed_tests'][:10], indent=2)}

# YOUR TASK
Generate a comprehensive Test Closure Report with the following sections:

1. **Executive Summary** (2-3 paragraphs)
   - Overall test cycle assessment
   - Key achievements and challenges
   - Final recommendation (Ready for Production / Needs More Testing)

2. **Test Execution Analysis** (detailed)
   - Analysis of test scenario and case generation
   - Test optimization effectiveness
   - Execution results interpretation
   - Coverage assessment

3. **Quality Assessment** (critical analysis)
   - Pass rate analysis (Is {metrics['test_execution']['pass_rate']}% acceptable?)
   - Defect severity analysis
   - Risk areas identified
   - Quality gates status

4. **Lessons Learned** (insights)
   - What went well in this test cycle
   - Challenges encountered
   - Areas for improvement in future cycles

5. **Recommendations** (actionable)
   - Immediate actions required (if any defects)
   - Process improvements for next cycle
   - Tool/automation suggestions
   - Training or resource needs

6. **Test Closure Criteria** (checklist)
   - Exit criteria met? (Yes/No with explanation)
   - Outstanding issues and risks
   - Sign-off recommendation

Please provide a well-structured, professional report suitable for stakeholders.
Use markdown formatting for better readability.
Be analytical and provide insights, not just data repetition.
"""
        return prompt
    
    async def generate_closure_report(
        self,
        session_ids: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete test closure report with aggregated metrics
        
        Args:
            session_ids: Specific sessions to analyze
            date_from: Start date filter
            date_to: End date filter
            
        Returns:
            Dictionary containing metrics and AI prompt
        """
        # Fetch sessions
        sessions = await self.fetch_sessions_for_closure(
            session_ids=session_ids,
            date_from=date_from,
            date_to=date_to
        )
        
        if not sessions:
            return {
                "success": False,
                "error": "No sessions found for the specified criteria",
                "metrics": None,
                "prompt": None
            }
        
        # Aggregate metrics
        metrics = self.aggregate_test_metrics(sessions)
        
        # Generate AI prompt
        prompt = self.generate_closure_prompt(metrics)
        
        return {
            "success": True,
            "metrics": metrics,
            "prompt": prompt,
            "sessions_analyzed": len(sessions)
        }


# Singleton instance
test_closure_service = TestClosureService()
