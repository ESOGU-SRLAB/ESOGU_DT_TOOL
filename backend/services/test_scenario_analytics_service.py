"""
Test Scenario Generation Analytics Service
------------------------------------------
Provides comprehensive analytics and tracking for test scenario generation process
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from core.database import get_db
from core.prompt_manager import save_session_data

logger = logging.getLogger(__name__)

class TestScenarioAnalytics:
    """Service for tracking and analyzing test scenario generation performance"""
    
    def __init__(self):
        self.db = get_db()
        self.analytics_collection = self.db["test_scenario_analytics"]
        self.quality_collection = self.db["test_scenario_quality"]
        self.file_history_collection = self.db["test_scenario_file_history"]
    
    def track_generation_session(
        self,
        session_id: str,
        test_metadata: Dict[str, Any],
        generation_result: Dict[str, Any],
        processing_stats: Dict[str, Any],
        file_analysis: Dict[str, Any],
        prompt_metadata: Dict[str, Any]
    ) -> bool:
        """
        Track a complete test scenario generation session with comprehensive analytics
        
        Args:
            session_id: Unique session identifier
            test_metadata: Test type, category, scoring/instruction elements
            generation_result: Generated scenarios and metadata
            processing_stats: Processing time, tokens, model info
            file_analysis: File processing information
            prompt_metadata: Prompt generation details
        """
        try:
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(generation_result)
            
            analytics_record = {
                "session_id": session_id,
                "process_type": "test_scenario_generation",
                "timestamp": datetime.now(),
                "test_metadata": test_metadata,
                "generation_analytics": {
                    "total_scenarios_generated": generation_result.get("total_scenarios", 0),
                    "generation_method": generation_result.get("extraction_method", "json_parse"),
                    "model_used": processing_stats.get("model_used", "unknown"),
                    "model_fallback_required": processing_stats.get("model_fallback", False),
                    "processing_time_seconds": processing_stats.get("processing_time", 0),
                    "token_usage": processing_stats.get("token_usage", {})
                },
                "file_analysis": file_analysis,
                "quality_metrics": quality_metrics,
                "prompt_metadata": prompt_metadata
            }
            
            # Insert analytics record
            result = self.analytics_collection.insert_one(analytics_record)
            
            # Track individual scenario quality
            if "test_scenarios" in generation_result:
                self._track_individual_scenarios(session_id, generation_result["test_scenarios"])
            
            # Track file processing history
            if file_analysis.get("files_processed", 0) > 0:
                self._track_file_processing(session_id, file_analysis)
            
            logger.info(f"Analytics tracked for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to track analytics for session {session_id}: {e}")
            return False
    
    def _calculate_quality_metrics(self, generation_result: Dict[str, Any]) -> Dict[str, float]:
        """Calculate quality metrics for generated scenarios"""
        try:
            scenarios = generation_result.get("test_scenarios", {}).get("TestScenarios", [])
            total_scenarios = len(scenarios)
            
            if total_scenarios == 0:
                return {"response_quality_score": 0.0}
            
            # Check completeness of scenarios
            complete_scenarios = 0
            for scenario in scenarios:
                required_fields = ["ScenarioID", "Title", "Description", "Objective"]
                if all(field in scenario and scenario[field] for field in required_fields):
                    complete_scenarios += 1
            
            completeness_score = complete_scenarios / total_scenarios if total_scenarios > 0 else 0
            
            # JSON parsing success (if we got here, parsing was successful)
            json_parse_success = True
            
            # Coverage score based on number of scenarios
            expected_scenarios = 8  # Target number
            coverage_score = min(total_scenarios / expected_scenarios, 1.0)
            
            # Overall quality score
            response_quality_score = (
                (0.4 * completeness_score) +
                (0.3 * (1.0 if json_parse_success else 0.0)) +
                (0.3 * coverage_score)
            )
            
            return {
                "response_quality_score": round(response_quality_score, 3),
                "json_parse_success": json_parse_success,
                "scenario_completeness_score": round(completeness_score, 3),
                "coverage_score": round(coverage_score, 3)
            }
            
        except Exception as e:
            logger.error(f"Error calculating quality metrics: {e}")
            return {"response_quality_score": 0.0}
    
    def _track_individual_scenarios(self, session_id: str, test_scenarios: Dict[str, Any]):
        """Track quality metrics for individual scenarios"""
        try:
            scenarios = test_scenarios.get("TestScenarios", [])
            
            for scenario in scenarios:
                quality_assessment = self._assess_scenario_quality(scenario)
                
                quality_record = {
                    "session_id": session_id,
                    "scenario_id": scenario.get("ScenarioID", "unknown"),
                    "timestamp": datetime.now(),
                    "scenario_data": {
                        "title": scenario.get("Title", ""),
                        "description": scenario.get("Description", ""),
                        "category": scenario.get("Category", ""),
                        "test_type": "derived_from_session"  # Could be enhanced
                    },
                    "quality_assessment": quality_assessment,
                    "validation_flags": self._validate_scenario_structure(scenario)
                }
                
                self.quality_collection.insert_one(quality_record)
                
        except Exception as e:
            logger.error(f"Error tracking individual scenarios: {e}")
    
    def _assess_scenario_quality(self, scenario: Dict[str, Any]) -> Dict[str, float]:
        """Assess quality of an individual scenario"""
        try:
            # Completeness score
            required_fields = ["ScenarioID", "Title", "Description", "Objective"]
            complete_fields = sum(1 for field in required_fields if scenario.get(field))
            completeness_score = complete_fields / len(required_fields)
            
            # Clarity score (based on description length and content)
            description = scenario.get("Description", "")
            clarity_score = min(len(description.split()) / 20, 1.0)  # Target ~20 words
            
            # Testability score (presence of clear objectives and steps)
            testability_score = 0.5  # Base score
            if scenario.get("Objective"):
                testability_score += 0.3
            if len(description) > 50:  # Detailed description
                testability_score += 0.2
            
            # ISTQB compliance score (structured format, clear naming)
            istqb_score = 0.5  # Base score
            if scenario.get("ScenarioID", "").startswith(("TS", "TEST")):
                istqb_score += 0.3
            if scenario.get("Category") in ["Functional", "Non-Functional"]:
                istqb_score += 0.2
            
            return {
                "completeness_score": round(completeness_score, 3),
                "clarity_score": round(clarity_score, 3),
                "testability_score": round(min(testability_score, 1.0), 3),
                "istqb_compliance_score": round(min(istqb_score, 1.0), 3)
            }
            
        except Exception as e:
            logger.error(f"Error assessing scenario quality: {e}")
            return {"completeness_score": 0.0}
    
    def _validate_scenario_structure(self, scenario: Dict[str, Any]) -> Dict[str, bool]:
        """Validate scenario structure against ISTQB standards"""
        return {
            "has_clear_objective": bool(scenario.get("Objective")),
            "has_prerequisites": "prerequisite" in scenario.get("Description", "").lower(),
            "has_test_steps": "step" in scenario.get("Description", "").lower(),
            "has_expected_results": "expect" in scenario.get("Description", "").lower(),
            "follows_naming_convention": scenario.get("ScenarioID", "").startswith(("TS", "TEST"))
        }
    
    def _track_file_processing(self, session_id: str, file_analysis: Dict[str, Any]):
        """Track file processing history"""
        try:
            file_history_record = {
                "session_id": session_id,
                "timestamp": datetime.now(),
                "files_processed": file_analysis.get("files_processed_details", []),
                "processing_summary": {
                    "total_files": file_analysis.get("files_processed", 0),
                    "successful_processing": file_analysis.get("files_processed", 0),
                    "total_tokens_extracted": file_analysis.get("total_tokens", 0),
                    "total_content_size": file_analysis.get("total_file_size", 0),
                    "context_relevance_score": file_analysis.get("context_relevance", 0.8)
                }
            }
            
            self.file_history_collection.insert_one(file_history_record)
            
        except Exception as e:
            logger.error(f"Error tracking file processing: {e}")
    
    def get_session_analytics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve analytics for a specific session"""
        try:
            return self.analytics_collection.find_one({"session_id": session_id})
        except Exception as e:
            logger.error(f"Error retrieving session analytics: {e}")
            return None
    
    def get_quality_trends(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get quality trends over recent sessions"""
        try:
            pipeline = [
                {"$sort": {"timestamp": -1}},
                {"$limit": limit},
                {"$project": {
                    "session_id": 1,
                    "timestamp": 1,
                    "test_metadata.test_type": 1,
                    "quality_metrics": 1,
                    "generation_analytics.total_scenarios_generated": 1
                }}
            ]
            
            return list(self.analytics_collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"Error retrieving quality trends: {e}")
            return []
    
    def get_test_type_statistics(self) -> Dict[str, Any]:
        """Get statistics by test type"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$test_metadata.test_type",
                    "total_sessions": {"$sum": 1},
                    "avg_scenarios": {"$avg": "$generation_analytics.total_scenarios_generated"},
                    "avg_quality": {"$avg": "$quality_metrics.response_quality_score"},
                    "total_scenarios": {"$sum": "$generation_analytics.total_scenarios_generated"}
                }},
                {"$sort": {"total_sessions": -1}}
            ]
            
            results = list(self.analytics_collection.aggregate(pipeline))
            return {"test_type_stats": results}
            
        except Exception as e:
            logger.error(f"Error retrieving test type statistics: {e}")
            return {}

class _LazyTestScenarioAnalytics:
    """Preserve the legacy singleton API without connecting during app import."""

    def __init__(self):
        self._instance = None

    def __getattr__(self, name):
        if self._instance is None:
            self._instance = TestScenarioAnalytics()
        return getattr(self._instance, name)


test_scenario_analytics = _LazyTestScenarioAnalytics()
