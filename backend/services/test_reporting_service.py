"""
test_reporting_service.py
-------------------------
Comprehensive Test Reporting Service
Handles multi-process analysis, chunking, and AI-powered report generation
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
from core.database import get_database

logger = logging.getLogger(__name__)


class TestReportingService:
    """
    Service for generating comprehensive test reports from STLC processes
    """
    
    # Process configuration: max items per chunk
    CHUNK_SIZES = {
        "test_scenario_generation": 20,  # 20 scenarios per chunk
        "test_case_generation": 50,      # 50 test cases per chunk
        "test_case_optimization": 30,    # 30 optimized cases per chunk
        "test_code_generation": 30,      # 30 test codes per chunk
        "test_execution": 30,            # 30 execution results per chunk
        "default": 25
    }
    
    # Maximum character size per chunk (fallback)
    MAX_CHUNK_CHARS = 50000
    
    def __init__(self):
        self.db = None
    
    async def initialize(self):
        """Initialize database connection"""
        if self.db is None:
            self.db = await get_database()
    
    async def fetch_available_sessions(
        self, 
        process_names: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch available sessions from session_history
        
        Args:
            process_names: Filter by specific process names
            date_from: ISO date string (e.g., "2025-11-01")
            date_to: ISO date string
            
        Returns:
            List of session summaries with process counts
        """
        await self.initialize()
        collection = self.db["session_history"]
        
        # Build query
        query = {}
        
        # Date filter (MongoDB uses 'created_at' field)
        if date_from or date_to:
            query["created_at"] = {}
            if date_from:
                query["created_at"]["$gte"] = date_from
            if date_to:
                query["created_at"]["$lte"] = date_to
        
        # Fetch all matching sessions (sort by created_at descending)
        cursor = collection.find(query).sort("created_at", -1)
        sessions = await cursor.to_list(length=None)
        
        # Process and enrich session data
        result = []
        for session in sessions:
            session_id = session.get("session_id", "unknown")
            # MongoDB stores timestamp in 'created_at' field
            created_at = session.get("created_at", "")
            processes = session.get("processes", {})
            
            # Filter by process names if specified
            if process_names:
                processes = {k: v for k, v in processes.items() if k in process_names}
            
            # Count available processes and collect detailed metadata
            process_summary = {}
            process_details = []
            models_used = set()
            
            for process_name, process_data in processes.items():
                if isinstance(process_data, dict) and process_data.get("output"):
                    # Count items in output (scenarios, cases, etc.)
                    output = process_data.get("output", {})
                    count = self._count_process_items(process_name, output)
                    process_summary[process_name] = count
                    
                    # Collect detailed metadata for each process
                    detail = {
                        "type": process_name,
                        "timestamp": process_data.get("timestamp"),
                        "model": process_data.get("used_model"),
                        "edited_prompt": process_data.get("edited_prompt", False),
                        "item_count": count
                    }
                    
                    # Add process-specific fields
                    if process_name == "test_scenario_generation":
                        detail.update({
                            "category": process_data.get("selected_category"),
                            "test_type": process_data.get("selected_test_type"),
                            "process_title": process_data.get("process_title")
                        })
                    elif process_name == "test_case_generation":
                        detail.update({
                            "based_on": process_data.get("selected_process_title"),
                            "updated_at": process_data.get("updated_at")
                        })
                    elif process_name == "code_review":
                        detail.update({
                            "prompt_length": len(process_data.get("used_prompt", ""))
                        })
                    elif process_name == "requirement_analysis":
                        detail.update({
                            "prompt_length": len(process_data.get("used_prompt", ""))
                        })
                    elif process_name == "test_planning":
                        detail.update({
                            "prompt_length": len(process_data.get("used_prompt", ""))
                        })
                    
                    process_details.append(detail)
                    
                    # Track unique models used
                    if detail["model"]:
                        models_used.add(detail["model"])
            
            if process_summary:  # Only include sessions with data
                # Get process_name, fallback to process_title if available
                process_name_display = session.get("process_name")
                
                # If no process_name, try to extract from processes
                if not process_name_display:
                    # Check for process_title in any process
                    for proc_name, proc_data in processes.items():
                        if isinstance(proc_data, dict):
                            process_title = proc_data.get("process_title")
                            if process_title:
                                process_name_display = process_title
                                break
                
                # Format timestamp to ISO format if it's a datetime object
                formatted_timestamp = created_at
                if hasattr(created_at, 'isoformat'):
                    formatted_timestamp = created_at.isoformat()
                
                result.append({
                    "session_id": session_id,
                    "timestamp": formatted_timestamp,
                    "process_name": process_name_display or None,
                    "processes": process_summary,
                    "process_details": process_details,  # NEW: Detailed process metadata
                    "models_used": list(models_used)  # NEW: Unique models used in session
                })
        
        return result
    
    def _count_process_items(self, process_name: str, output: Dict[str, Any]) -> int:
        """Count items in a process output"""
        if process_name == "test_scenario_generation":
            scenarios = output.get("test_scenarios", [])
            return len(scenarios) if isinstance(scenarios, list) else 0
        
        elif process_name == "test_case_generation":
            test_cases = output.get("test_cases", [])
            return len(test_cases) if isinstance(test_cases, list) else 0
        
        elif process_name == "test_case_optimization":
            optimized_cases = output.get("optimized_test_cases", [])
            return len(optimized_cases) if isinstance(optimized_cases, list) else 0
        
        elif process_name == "test_code_generation":
            generated_tests = output.get("generated_tests", [])
            return len(generated_tests) if isinstance(generated_tests, list) else 0
        
        elif process_name == "test_execution":
            # Count from terminal output or results
            terminal_output = output.get("terminal_output", "")
            if "Total Tests:" in terminal_output:
                match = re.search(r'Total Tests: (\d+)', terminal_output)
                if match:
                    return int(match.group(1))
            return 1  # At least one execution
        
        # Default: check if output exists
        return 1 if output else 0
    
    async def fetch_session_data(
        self, 
        session_id: str, 
        selected_processes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch specific session data for selected processes
        
        Args:
            session_id: Session ID to fetch
            selected_processes: List of process names to include (None = all processes)
            
        Returns:
            Dictionary with session metadata and process data
        """
        await self.initialize()
        collection = self.db["session_history"]
        
        # Fetch session document
        session = await collection.find_one({"session_id": session_id})
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Extract process data
        processes_data = session.get("processes", {})
        selected_data = {}
        
        # If selected_processes is None, fetch all processes
        if selected_processes is None:
            process_names = list(processes_data.keys())
        else:
            process_names = selected_processes
        
        for process_name in process_names:
            if process_name in processes_data:
                process_data = processes_data[process_name]
                selected_data[process_name] = {
                    "input": process_data.get("input", {}),
                    "output": process_data.get("output", {}),
                    "metadata": process_data.get("metadata", {}),
                    "timestamp": process_data.get("timestamp", "")
                }
        
        return {
            "session_id": session_id,
            "session_timestamp": session.get("timestamp", ""),
            "process_name": session.get("process_name", ""),
            "processes": selected_data
        }
    
    def create_chunks(
        self, 
        process_name: str, 
        process_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from process data based on smart chunking strategy
        
        Args:
            process_name: Name of the process
            process_data: Process output data
            
        Returns:
            List of chunks with metadata
        """
        output = process_data.get("output", {})
        chunks = []
        
        # Get chunk size for this process type
        chunk_size = self.CHUNK_SIZES.get(process_name, self.CHUNK_SIZES["default"])
        
        # Process-specific chunking
        if process_name == "test_scenario_generation":
            scenarios = output.get("test_scenarios", [])
            chunks = self._chunk_list(scenarios, chunk_size, "scenarios")
        
        elif process_name == "test_case_generation":
            test_cases = output.get("test_cases", [])
            chunks = self._chunk_list(test_cases, chunk_size, "test_cases")
        
        elif process_name == "test_case_optimization":
            optimized_cases = output.get("optimized_test_cases", [])
            before_count = output.get("original_count", 0)
            after_count = len(optimized_cases) if isinstance(optimized_cases, list) else 0
            
            chunks = self._chunk_list(optimized_cases, chunk_size, "optimized_cases")
            # Add metadata to each chunk
            for chunk in chunks:
                chunk["optimization_metadata"] = {
                    "before_count": before_count,
                    "after_count": after_count,
                    "reduction_percentage": ((before_count - after_count) / before_count * 100) if before_count > 0 else 0
                }
        
        elif process_name == "test_code_generation":
            generated_tests = output.get("generated_tests", [])
            chunks = self._chunk_list(generated_tests, chunk_size, "generated_tests")
        
        elif process_name == "test_execution":
            # For execution, use the full terminal output
            terminal_output = output.get("terminal_output", "")
            chunks = [{
                "chunk_index": 0,
                "total_chunks": 1,
                "data_type": "execution_output",
                "data": terminal_output,
                "metadata": {
                    "model_used": output.get("model_used", "unknown"),
                    "timestamp": output.get("timestamp", "")
                }
            }]
        
        else:
            # Generic chunking: convert output to JSON string and chunk by size
            output_str = json.dumps(output, indent=2)
            chunks = self._chunk_by_size(output_str, self.MAX_CHUNK_CHARS, "generic_output")
        
        # Add process name to all chunks
        for chunk in chunks:
            chunk["process_name"] = process_name
        
        return chunks
    
    def _chunk_list(
        self, 
        items: List[Any], 
        chunk_size: int, 
        data_type: str
    ) -> List[Dict[str, Any]]:
        """Chunk a list into smaller lists"""
        if not isinstance(items, list):
            return []
        
        chunks = []
        total_chunks = (len(items) + chunk_size - 1) // chunk_size  # Ceiling division
        
        for i in range(0, len(items), chunk_size):
            chunk_items = items[i:i + chunk_size]
            chunks.append({
                "chunk_index": len(chunks),
                "total_chunks": total_chunks,
                "data_type": data_type,
                "data": chunk_items,
                "item_count": len(chunk_items)
            })
        
        return chunks
    
    def _chunk_by_size(
        self, 
        text: str, 
        max_size: int, 
        data_type: str
    ) -> List[Dict[str, Any]]:
        """Chunk text by character size"""
        chunks = []
        total_chunks = (len(text) + max_size - 1) // max_size
        
        for i in range(0, len(text), max_size):
            chunk_text = text[i:i + max_size]
            chunks.append({
                "chunk_index": len(chunks),
                "total_chunks": total_chunks,
                "data_type": data_type,
                "data": chunk_text,
                "char_count": len(chunk_text)
            })
        
        return chunks
    
    def create_intermediate_prompt(
        self, 
        chunk: Dict[str, Any],
        analysis_depth: str = "detailed"
    ) -> str:
        """
        Create analysis prompt for a single chunk
        
        Args:
            chunk: Chunk data with metadata
            analysis_depth: "summary" | "detailed" | "deep"
            
        Returns:
            Formatted prompt for LLM
        """
        process_name = chunk.get("process_name", "unknown")
        data_type = chunk.get("data_type", "unknown")
        chunk_index = chunk.get("chunk_index", 0)
        total_chunks = chunk.get("total_chunks", 1)
        
        # Base context
        prompt = f"""You are an expert Test Manager analyzing STLC (Software Testing Life Cycle) process data.

**Process:** {process_name.replace('_', ' ').title()}
**Data Type:** {data_type}
**Chunk:** {chunk_index + 1} of {total_chunks}

"""
        
        # Add specific instructions based on process type
        if process_name == "test_scenario_generation":
            prompt += """Analyze these test scenarios and provide:

1. **Key Metrics:**
   - Total scenarios in this chunk
   - Test types distribution
   - Coverage areas

2. **Quality Indicators:**
   - Scenario completeness (have clear preconditions, steps, expected results)
   - Scenario depth and detail level
   - Edge case coverage

3. **Notable Patterns:**
   - Common test types
   - Testing focus areas
   - Any gaps or missing coverage

4. **Issues or Concerns:**
   - Unclear or ambiguous scenarios
   - Missing critical test areas
   - Duplicate or redundant scenarios

"""
        
        elif process_name == "test_case_generation":
            prompt += """Analyze these test cases and provide:

1. **Key Metrics:**
   - Total test cases in this chunk
   - Test case complexity distribution
   - Coverage metrics

2. **Quality Indicators:**
   - Test case clarity and completeness
   - Test data specifications
   - Expected results precision

3. **Notable Patterns:**
   - Common test case types
   - Testing approach (positive/negative/boundary)
   - Requirement traceability

4. **Issues or Concerns:**
   - Missing test data
   - Unclear assertions
   - Potential gaps in coverage

"""
        
        elif process_name == "test_case_optimization":
            optimization_meta = chunk.get("optimization_metadata", {})
            prompt += f"""Analyze these optimized test cases and provide:

**Optimization Context:**
- Before: {optimization_meta.get('before_count', 'N/A')} test cases
- After: {optimization_meta.get('after_count', 'N/A')} test cases
- Reduction: {optimization_meta.get('reduction_percentage', 0):.1f}%

1. **Optimization Impact:**
   - Quality of reduction (appropriate vs over-optimized)
   - Coverage preservation
   - Critical test case retention

2. **Quality Indicators:**
   - Redundancy elimination effectiveness
   - Essential test case preservation
   - Edge case handling

3. **Notable Patterns:**
   - Types of test cases removed
   - Consolidation strategies used
   - Coverage optimization approach

4. **Issues or Concerns:**
   - Potentially over-aggressive optimization
   - Missing critical edge cases
   - Coverage gaps introduced

"""
        
        elif process_name == "test_code_generation":
            prompt += """Analyze these generated test codes and provide:

1. **Key Metrics:**
   - Total test codes in this chunk
   - Programming language/framework used
   - Code structure quality

2. **Quality Indicators:**
   - Code readability and maintainability
   - Test framework usage
   - Assertion quality

3. **Notable Patterns:**
   - Common testing patterns used
   - Code organization approach
   - Test data handling

4. **Issues or Concerns:**
   - Code quality issues
   - Missing assertions or validations
   - Potential runtime errors

"""
        
        elif process_name == "test_execution":
            prompt += """Analyze these test execution results and provide:

1. **Key Metrics:**
   - Total tests executed
   - Pass/fail statistics
   - Success rate

2. **Quality Indicators:**
   - Execution reliability
   - Error patterns
   - Performance metrics

3. **Notable Patterns:**
   - Common failure types
   - Success patterns
   - Execution stability

4. **Issues or Concerns:**
   - Critical failures
   - Flaky tests
   - Performance bottlenecks

"""
        
        else:
            prompt += f"""Analyze this {process_name} data and provide:

1. Key metrics and statistics
2. Quality indicators
3. Notable patterns
4. Issues or concerns

"""
        
        # Add the actual data
        data = chunk.get("data")
        if isinstance(data, (list, dict)):
            data_str = json.dumps(data, indent=2)
        else:
            data_str = str(data)
        
        # Truncate if too long (safety measure)
        if len(data_str) > 100000:
            data_str = data_str[:100000] + "\n\n... (truncated for length)"
        
        # Analysis depth instructions
        depth_instruction = ""
        if analysis_depth == "summary":
            depth_instruction = "\n**Analysis Level: SUMMARY** - Provide only high-level key findings and critical metrics. Be concise.\n"
        elif analysis_depth == "detailed":
            depth_instruction = "\n**Analysis Level: DETAILED** - Provide comprehensive analysis with supporting data and examples. This is the recommended level.\n"
        elif analysis_depth == "deep":
            depth_instruction = "\n**Analysis Level: DEEP** - Provide in-depth analysis with extensive insights, patterns, edge cases, and detailed recommendations.\n"
        
        prompt += f"""
{depth_instruction}
**Data to Analyze:**

```json
{data_str}
```

Please provide analysis according to the specified analysis level, focusing on the points above.
"""
        
        return prompt
    
    def create_final_synthesis_prompt(
        self,
        intermediate_summaries: List[Dict[str, Any]],
        session_metadata: Dict[str, Any],
        analysis_depth: str = "detailed",
        raw_session_data: List[Dict[str, Any]] = None
    ) -> str:
        """
        Create final synthesis prompt from all intermediate summaries
        Supports both single session and multi-session comparison
        
        Args:
            intermediate_summaries: List of {session_id, process, chunk_index, summary} dicts
            session_metadata: Session info (can contain multiple sessions)
            analysis_depth: Level of analysis
            raw_session_data: Optional raw session data for direct LLM access
            
        Returns:
            Final synthesis prompt
        """
        comparison_mode = session_metadata.get("comparison_mode", False)
        
        if comparison_mode:
            # Multi-session comparison mode
            sessions = session_metadata.get("sessions", [])
            
            # Group summaries by session and process
            session_summaries = {}
            for summary in intermediate_summaries:
                session_id = summary.get("session_id", "unknown")
                process = summary.get("process_name", "unknown")
                
                if session_id not in session_summaries:
                    session_summaries[session_id] = {}
                if process not in session_summaries[session_id]:
                    session_summaries[session_id][process] = []
                    
                session_summaries[session_id][process].append(summary.get("summary", ""))
            
            # Build comparison prompt
            prompt = f"""You are a Senior Test Manager creating a comprehensive STLC **COMPARISON REPORT** across multiple test sessions.

**Comparison Overview:**
- Number of Sessions: {len(sessions)}
- Total Processes Analyzed: {len(set(s.get('process_name') for s in intermediate_summaries))}

**Sessions Being Compared:**
"""
            for i, session in enumerate(sessions, 1):
                prompt += f"\n{i}. **{session.get('process_name', 'Unnamed')}**\n"
                prompt += f"   - Session ID: {session.get('session_id', 'N/A')}\n"
                prompt += f"   - Date: {session.get('session_timestamp', 'N/A')}\n"
            
            prompt += """
You have received BOTH raw session data AND intermediate analysis summaries.

---

## RAW SESSION DATA (For Your Reference)

"""
            
            # Add raw session data if provided
            if raw_session_data:
                for session_info in raw_session_data:
                    session_id = session_info.get("session_id", "unknown")
                    session_data = session_info.get("data", {})
                    session_name = session_data.get("process_name", session_id)
                    
                    prompt += f"\n### Session: {session_name}\n"
                    prompt += f"- **Session ID**: {session_id}\n"
                    prompt += f"- **Timestamp**: {session_data.get('session_timestamp', 'N/A')}\n"
                    prompt += f"- **Processes**: {len(session_data.get('processes', {}))}\n\n"
                    
                    # Add process-level metrics
                    for process_name, process_data in session_data.get("processes", {}).items():
                        output = process_data.get("output", {})
                        metadata = process_data.get("metadata", {})
                        
                        prompt += f"#### {process_name.replace('_', ' ').title()}\n"
                        
                        # Extract key metrics based on process type
                        if process_name == "requirement_analysis":
                            req_count = len(output.get("requirements", []))
                            prompt += f"- Requirements Analyzed: {req_count}\n"
                            
                        elif process_name == "test_scenario_generation":
                            scenarios = output.get("test_scenarios", [])
                            prompt += f"- Scenarios Generated: {len(scenarios)}\n"
                            if scenarios and isinstance(scenarios, list) and len(scenarios) > 0:
                                # Count by category if available
                                categories = {}
                                for scenario in scenarios:
                                    cat = scenario.get("category", "Unknown")
                                    categories[cat] = categories.get(cat, 0) + 1
                                prompt += f"- Categories: {', '.join(f'{k}({v})' for k, v in categories.items())}\n"
                        
                        elif process_name == "test_case_generation":
                            test_cases = output.get("test_cases", [])
                            prompt += f"- Test Cases Generated: {len(test_cases)}\n"
                            if test_cases and isinstance(test_cases, list):
                                # Count positive vs negative
                                positive = sum(1 for tc in test_cases if tc.get("test_type", "").lower() == "positive")
                                negative = len(test_cases) - positive
                                prompt += f"- Positive/Negative: {positive}/{negative}\n"
                        
                        elif process_name == "test_case_optimization":
                            unique = len(output.get("unique_test_cases", []))
                            similar = len(output.get("similar_test_cases", []))
                            total = output.get("total_test_cases", unique + similar)
                            reduction = ((similar / total * 100) if total > 0 else 0)
                            prompt += f"- Original Test Cases: {total}\n"
                            prompt += f"- Unique Test Cases: {unique}\n"
                            prompt += f"- Duplicates Removed: {similar}\n"
                            prompt += f"- Reduction Rate: {reduction:.1f}%\n"
                        
                        elif process_name == "test_code_generation":
                            tests = output.get("generated_tests", [])
                            prompt += f"- Test Code Files Generated: {len(tests)}\n"
                        
                        # Add model info
                        model_used = metadata.get("model_used", "Unknown")
                        prompt += f"- Model Used: {model_used}\n"
                        prompt += f"- Timestamp: {process_data.get('timestamp', 'N/A')}\n\n"
            
            prompt += """
---

## INTERMEDIATE ANALYSIS SUMMARIES

The following are AI-generated summaries of the above raw data:

"""
            
            # Add summaries organized by session
            for session_id, processes in session_summaries.items():
                session_info = next((s for s in sessions if s.get('session_id') == session_id), {})
                prompt += f"\n### Session: {session_info.get('process_name', session_id)}\n\n"
                
                for process_name, summaries in processes.items():
                    prompt += f"#### {process_name.replace('_', ' ').title()}\n\n"
                    for i, summary in enumerate(summaries, 1):
                        if len(summaries) > 1:
                            prompt += f"**Part {i}:**\n{summary}\n\n"
                        else:
                            prompt += f"{summary}\n\n"
            
            prompt += """
---

## YOUR TASK: Generate Comparison Report

Use BOTH the raw data metrics AND the intermediate summaries to create your comprehensive comparison report.

## Required Comparison Report Structure

Please generate a comprehensive comparison report with the following sections:

### 📊 Executive Summary
- Overall comparison overview
- Key trends across sessions
- Most significant improvements
- Critical regressions or issues
- Recommendation priority

### 🔄 Session-by-Session Comparison

For each session, provide:
- Session name and timestamp
- Key metrics and statistics
- Quality assessment
- Unique characteristics

### 📈 Cross-Session Analysis

For each process type, compare:
- Metric trends (improving/declining/stable)
- Quality evolution
- Best practices observed
- Common patterns and anti-patterns

### 💡 Insights & Recommendations

Provide:
- **What Improved:** Highlight positive trends and improvements
- **What Regressed:** Identify declining metrics or quality issues
- **What Remained Consistent:** Note stable aspects
- **Actionable Next Steps:** Specific, prioritized recommendations for future sessions

### 📋 Comparative Metrics Dashboard

Create comparison tables showing:
- Session-by-session metrics
- Process-by-process comparison
- Trends and deltas
- Performance scores

### ⚠️ Risk Assessment

Identify:
- Cross-session quality concerns
- Regression risks
- Process consistency issues
- Mitigation recommendations

---

**Formatting Guidelines:**
- Use clear Markdown formatting
- Include emojis for visual clarity
- Use comparison tables extensively
- Show trends with arrows (↑ ↓ →)
- Highlight regressions with 🔴 and improvements with 🟢
- Use bullet points for detailed lists
- Include session names for clarity

**Analysis Depth Level: {analysis_depth.upper()}**
"""
            if analysis_depth == "summary":
                prompt += """
- Provide HIGH-LEVEL overview only
- Focus on critical findings and trends
- Keep sections concise (2-3 key points each)
- Prioritize executive summary and actionable recommendations
"""
            elif analysis_depth == "detailed":
                prompt += """
- Provide COMPREHENSIVE analysis with supporting data (RECOMMENDED)
- Include specific examples from each session
- Balance breadth and depth across all sections
- Provide detailed metrics and comparisons
"""
            elif analysis_depth == "deep":
                prompt += """
- Provide IN-DEPTH investigation with extensive insights
- Include detailed pattern analysis and edge cases
- Extensive examples and data points
- Deep dive into quality indicators and trends
- Comprehensive recommendations with implementation details
"""
            
            prompt += """
**Analysis Focus:**
- Emphasize differences and changes between sessions
- Identify patterns and trends
- Provide data-driven insights
- Recommend specific actions

Generate the comprehensive comparison report now.
"""
        
        else:
            # Single session mode (original logic)
            # Group summaries by process
            process_summaries = {}
            for summary in intermediate_summaries:
                process = summary.get("process_name", "unknown")
                if process not in process_summaries:
                    process_summaries[process] = []
                process_summaries[process].append(summary.get("summary", ""))
            
            # Build prompt
            prompt = f"""You are a Senior Test Manager creating a comprehensive STLC report.

**Session Information:**
- Session ID: {session_metadata.get('session_id', 'N/A')}
- Date: {session_metadata.get('session_timestamp', 'N/A')}
- Process Name: {session_metadata.get('process_name', 'N/A')}
- Processes Analyzed: {len(process_summaries)}

You have received BOTH raw session data AND intermediate analysis summaries.

---

## RAW SESSION DATA (For Your Reference)

"""
            
            # Add raw session data if provided (single session)
            if raw_session_data and len(raw_session_data) > 0:
                session_info = raw_session_data[0]
                session_data = session_info.get("data", {})
                
                for process_name, process_data in session_data.get("processes", {}).items():
                    output = process_data.get("output", {})
                    metadata = process_data.get("metadata", {})
                    
                    prompt += f"\n### {process_name.replace('_', ' ').title()}\n"
                    
                    # Extract key metrics
                    if process_name == "requirement_analysis":
                        req_count = len(output.get("requirements", []))
                        prompt += f"- Requirements Analyzed: {req_count}\n"
                        
                    elif process_name == "test_scenario_generation":
                        scenarios = output.get("test_scenarios", [])
                        prompt += f"- Scenarios Generated: {len(scenarios)}\n"
                        
                    elif process_name == "test_case_generation":
                        test_cases = output.get("test_cases", [])
                        prompt += f"- Test Cases Generated: {len(test_cases)}\n"
                        if test_cases and isinstance(test_cases, list):
                            positive = sum(1 for tc in test_cases if tc.get("test_type", "").lower() == "positive")
                            negative = len(test_cases) - positive
                            prompt += f"- Positive/Negative: {positive}/{negative}\n"
                    
                    elif process_name == "test_case_optimization":
                        unique = len(output.get("unique_test_cases", []))
                        similar = len(output.get("similar_test_cases", []))
                        total = output.get("total_test_cases", unique + similar)
                        reduction = ((similar / total * 100) if total > 0 else 0)
                        prompt += f"- Original: {total}, Unique: {unique}, Removed: {similar} ({reduction:.1f}% reduction)\n"
                    
                    elif process_name == "test_code_generation":
                        tests = output.get("generated_tests", [])
                        prompt += f"- Test Code Files: {len(tests)}\n"
                    
                    prompt += f"- Model: {metadata.get('model_used', 'Unknown')}\n\n"
            
            prompt += """
---

## INTERMEDIATE ANALYSIS SUMMARIES

The following are AI-generated summaries of the above raw data:

"""
            
            # Add each process summary
            for process_name, summaries in process_summaries.items():
                prompt += f"\n### {process_name.replace('_', ' ').title()}\n\n"
                for i, summary in enumerate(summaries, 1):
                    if len(summaries) > 1:
                        prompt += f"**Part {i}:**\n{summary}\n\n"
                    else:
                        prompt += f"{summary}\n\n"
            
            prompt += """
---

## YOUR TASK: Generate Executive Report

Use BOTH the raw data metrics AND the intermediate summaries to create your comprehensive report.

## Required Report Structure

Please generate a comprehensive executive report with the following sections:

### 📊 Executive Summary
- Overall test quality score (X/10)
- Key achievements across all processes
- Critical issues that need immediate attention
- High-level statistics

### 📈 Process Breakdown

For each analyzed process, provide:
- Key metrics and statistics
- Quality assessment
- Strengths and weaknesses
- Notable findings

### 💡 Insights & Recommendations

Provide:
- **What Went Well:** Highlight successful aspects
- **What Needs Improvement:** Identify gaps and issues
- **Actionable Next Steps:** Specific, prioritized recommendations

### 📋 Metrics Dashboard

Create a summary table with key metrics across all processes:
- Coverage metrics
- Quality scores
- Efficiency indicators
- Success rates

### ⚠️ Risk Assessment

Identify:
- Critical risks in the testing process
- Quality concerns
- Process gaps
- Mitigation recommendations

---

**Formatting Guidelines:**
- Use clear Markdown formatting
- Include emojis for visual clarity
- Use tables for metrics
- Use bullet points for lists
- Highlight critical items with ⚠️ or 🔴
- Highlight positive items with ✅ or 🟢

**Analysis Depth Level: {analysis_depth.upper()}**
"""
            if analysis_depth == "summary":
                prompt += """
- Provide HIGH-LEVEL overview only
- Focus on critical findings and key metrics
- Keep sections concise (2-3 key points each)
- Prioritize executive summary and top recommendations
"""
            elif analysis_depth == "detailed":
                prompt += """
- Provide COMPREHENSIVE analysis with supporting data (RECOMMENDED)
- Include specific examples and evidence
- Balance breadth and depth across all sections
- Provide detailed process breakdown and metrics
"""
            elif analysis_depth == "deep":
                prompt += """
- Provide IN-DEPTH investigation with extensive insights
- Deep dive into each process with pattern analysis
- Include edge cases, anomalies, and detailed examples
- Extensive quality assessment and recommendations
- Implementation-ready action plans
"""
            
            prompt += """
Generate the comprehensive report now.
"""
        
        return prompt
    
    async def save_report(
        self,
        session_ids: List[str],  # Changed to support multiple sessions
        report_content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Save generated report to session_history
        Supports both single and multi-session reports
        
        Args:
            session_ids: List of session IDs (can be single or multiple)
            report_content: Generated report markdown
            metadata: Report metadata (processes, model, tokens, etc.)
            
        Returns:
            Report ID
        """
        await self.initialize()
        collection = self.db["session_history"]
        
        report_id = f"rep_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        report_data = {
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "report_content": report_content,
            "metadata": metadata,
            "session_ids": session_ids  # Store all related session IDs
        }
        
        # Update all related session documents
        for session_id in session_ids:
            await collection.update_one(
                {"session_id": session_id},
                {"$push": {"reports": report_data}}
            )
        
        logger.info(f"Report saved: {report_id} for {len(session_ids)} session(s)")
        return report_id


# Singleton instance
test_reporting_service = TestReportingService()
