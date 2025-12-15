"""
test_reporting_prompt_init.py
------------------------------
Initialize improved test reporting prompt in MongoDB
"""

from core.database import get_db
from datetime import datetime


def initialize_test_reporting_prompt():
    """Initialize test reporting prompt in MongoDB with improved compact format"""
    db = get_db()
    
    # Create collection if it doesn't exist
    if "test_reporting_prompt" not in db.list_collection_names():
        db.create_collection("test_reporting_prompt")
        print("✅ test_reporting_prompt collection created.")
    
    # Improved prompt with compact, visual-heavy structure
    prompt = {
        "process_type": "test_reporting",
        "prompt_text": """You are an expert Test Manager analyzing STLC (Software Testing Life Cycle) processes.

## 📋 ANALYSIS CONTEXT
- **Depth**: {analysis_depth} | **Sessions**: {session_count} | **Processes**: {process_types}
- **Period**: {date_range}

## 📊 SESSION DATA
{session_data}

---

## 🎯 REQUIRED OUTPUT FORMAT

### 1️⃣ EXECUTIVE SUMMARY (3-5 lines max)
**Quick Stats**: Sessions analyzed, processes covered, key metrics  
**Quality Score**: Overall rating (1-10) with brief justification  
**Critical Insight**: Single most important finding

### 2️⃣ KEY FINDINGS BY PROCESS
For each process type, provide a **compact table**:

**Requirement Analysis:**
| Metric | Value | Trend | Notes |
|--------|-------|-------|-------|
| Requirements Analyzed | X | ↑/↓/→ | Brief note |
| Coverage Rate | X% | ↑/↓/→ | Brief note |

**Test Scenario Generation:**
| Metric | Value | Trend | Notes |
|--------|-------|-------|-------|
| Scenarios Created | X | ↑/↓/→ | Brief note |
| Coverage Types | X | ↑/↓/→ | List types |

**Test Case Generation:**
| Metric | Value | Trend | Notes |
|--------|-------|-------|-------|
| Total Test Cases | X | ↑/↓/→ | Brief note |
| Positive/Negative Ratio | X:Y | ↑/↓/→ | Balance check |

### 3️⃣ CROSS-SESSION COMPARISON (if multiple sessions)
Use **session names** (not IDs) and show evolution:

| Session Name | Quality | Coverage | Issues | Status |
|--------------|---------|----------|--------|---------|
| Session A | 8/10 | 85% | 3 | ✅ Good |
| Session B | 6/10 | 70% | 7 | ⚠️ Review |

**Trend Analysis**: 1-2 sentences on improvement/regression patterns

### 4️⃣ QUALITY ASSESSMENT
Rate each dimension (1-10):
- ✅ **Completeness**: X/10 - Brief reason
- 📝 **Clarity**: X/10 - Brief reason  
- 🎯 **Coverage**: X/10 - Brief reason
- 🔍 **Depth**: X/10 - Brief reason

### 5️⃣ MODEL PERFORMANCE (if multiple models used)
| Model | Usage | Avg Output Quality | Recommendation |
|-------|-------|-------------------|----------------|
| Gemini 2.5 | 60% | 8.5/10 | ✅ Recommended for X |
| Llama 3.2 | 40% | 7.0/10 | ⚠️ Use for Y only |

### 6️⃣ RISK ASSESSMENT
**🔴 High Risk**: 
- Issue 1 - Impact: X, Mitigation: Y
- Issue 2 - Impact: X, Mitigation: Y

**🟡 Medium Risk**:
- Issue 1 - Impact: X, Mitigation: Y

**🟢 Low Risk**: 
- Minor concerns (list briefly)

### 7️⃣ ACTIONABLE RECOMMENDATIONS
**🚨 Immediate Actions** (Priority 1):
1. Action item - Expected outcome
2. Action item - Expected outcome

**📋 Short-term Improvements** (Priority 2):
1. Action item - Expected outcome

**💡 Long-term Enhancements** (Priority 3):
1. Action item - Expected outcome

### 8️⃣ METRICS DASHBOARD
```
📊 OVERALL STATISTICS
├─ Total Sessions: X
├─ Total Processes: X  
├─ Total Test Artifacts: X
├─ Average Quality: X/10
└─ Coverage Rate: X%

🎯 PROCESS BREAKDOWN
├─ Requirement Analysis: X items (Quality: X/10)
├─ Test Scenarios: X items (Quality: X/10)
├─ Test Cases: X items (Quality: X/10)
├─ Test Optimization: X% reduction
└─ Test Execution: X% pass rate
```

---

## ⚙️ OUTPUT RULES
1. **Be Concise**: Remove unnecessary words, use tables over paragraphs
2. **Use Session Names**: Replace IDs with readable names (e.g., "Sprint 3 Testing" not "c79e169f...")
3. **Visual Hierarchy**: Use emojis (📊📈✅⚠️🔴) and formatting (bold, tables)
4. **Data-Driven**: Every claim must have a number/metric
5. **Actionable**: Every finding → specific recommendation
6. **Depth Adaptation**:
   - **summary**: Only sections 1, 3, 7, 8 (ultra-compact)
   - **detailed**: All sections, moderate detail (RECOMMENDED)
   - **deep**: All sections, with examples and deep insights

## 🎨 STYLING TIPS
- Use **bold** for key terms
- Use tables for comparisons
- Use tree structure (├─└─) for hierarchies
- Use trend arrows (↑↓→) for changes
- Keep paragraphs under 2 lines
- Avoid redundant phrases like "It is important to note that..."

Generate the report now using this exact structure.""",
        "system_suffix": """Analysis Depth: {analysis_depth}
Sessions: {session_count}
Process Types: {process_types}
Date Range: {date_range}

Session Data:
{session_data}""",
        "description": "Improved compact test reporting prompt with visual hierarchy and session name mapping",
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
        print("✅ Test reporting prompt UPDATED successfully.")
    else:
        print("✅ Test reporting prompt INSERTED successfully.")
    
    return prompt


if __name__ == "__main__":
    # Run initialization
    initialize_test_reporting_prompt()
