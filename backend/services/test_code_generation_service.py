"""
Test Code Generation Service
---------------------------
Generates executable test code based on unique test cases, source code, and environment setup
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.database import get_db
from utils.model_client import LLMClient
from utils.file_handler import FileHandler
from utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)

class TestCodeGenerationService:
    def __init__(self):
        self.db = get_db()
        self.session_collection = self.db["session_history"]
        self.file_handler = FileHandler()
        self.text_processor = TextProcessor()
        
    def get_environment_setups(self) -> List[Dict[str, Any]]:
        """
        Veritabanından environment_setup sonuçlarını getirir
        """
        try:
            logger.info(f"Database: {self.db.name}, Collection: {self.session_collection.name}")
            
            # Veritabanında kaç kayıt var kontrol et
            total_records = self.session_collection.count_documents({})
            step_records = self.session_collection.count_documents({"step": "environment_setup"})
            logger.info(f"Total records in session_history: {total_records}")
            logger.info(f"Records with step='environment_setup': {step_records}")
            # Use nested processes structure: processes.environment_setup
            pipeline = [
                {"$match": {"processes.environment_setup": {"$exists": True}}},
                {"$project": {
                    "session_id": 1,
                    "timestamp": "$processes.environment_setup.timestamp",
                    "setup_result": "$processes.environment_setup.output",
                    "environment_name": "$processes.environment_setup.environment_name",
                    "process_name": {"$literal": "Environment Setup"}
                }},
                {"$sort": {"timestamp": -1}}
            ]
            
            try:
                results = list(self.session_collection.aggregate(pipeline))
                logger.info(f"Found {len(results)} results from environment_setup query")
                
                # İlk 3 sonucu logla
                for i, result in enumerate(results[:3], 1):
                    env_name = result.get("environment_name", "NOT_SET")
                    proc_name = result.get("process_name", "NOT_SET")
                    logger.info(f"Result {i}: env={env_name}, proc={proc_name}, session={result.get('session_id', 'N/A')}")
            except Exception as agg_error:
                logger.error(f"Aggregation error: {str(agg_error)}")
                results = []
            
            formatted_results = []
            for result in results:
                session_id = result.get("session_id", "Unknown")
                timestamp = result.get("timestamp", "Unknown")
                setup_result = result.get("setup_result", {})
                files_analyzed = result.get("files_analyzed", [])
                environment_name = result.get("environment_name", "Unnamed Environment")
                process_name = result.get("process_name", "Unknown Process")
                
                # Environment setup sonucundan dil ve framework bilgilerini çıkar
                environment_info = self._parse_environment_setup(setup_result)
                
                formatted_results.append({
                    "_id": session_id,  # MongoDB için _id field
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "environment_name": environment_name,
                    "process_name": process_name,
                    "display_name": f"{environment_name} - {environment_info.get('language', 'Unknown')} ({timestamp})",
                    "environment_info": environment_info,
                    "files_analyzed": files_analyzed,
                    "setup_result": setup_result
                })
            
            logger.info(f"Found {len(formatted_results)} environment setup records")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting environment setups: {str(e)}")
            return []
    
    def _parse_environment_setup(self, setup_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Environment setup sonucunu parse ederek dil ve framework bilgilerini çıkarır
        """
        try:
            # Setup result'dan text'i al
            setup_text = ""
            if isinstance(setup_result, list) and setup_result:
                setup_text = setup_result[0].get("setup", "")
            elif isinstance(setup_result, dict):
                setup_text = setup_result.get("setup", "")
            elif isinstance(setup_result, str):
                setup_text = setup_result
            
            # Basit parsing ile dil ve framework tespiti
            environment_info = {
                "language": "unknown",
                "framework": "unknown",
                "dependencies": [],
                "setup_commands": []
            }
            
            setup_lower = setup_text.lower()
            
            # Dil tespiti
            if "python" in setup_lower:
                environment_info["language"] = "python"
                if "pytest" in setup_lower:
                    environment_info["framework"] = "pytest"
                elif "unittest" in setup_lower:
                    environment_info["framework"] = "unittest"
                else:
                    environment_info["framework"] = "pytest"  # Default
            elif "javascript" in setup_lower or "node" in setup_lower:
                environment_info["language"] = "javascript"
                if "jest" in setup_lower:
                    environment_info["framework"] = "jest"
                elif "mocha" in setup_lower:
                    environment_info["framework"] = "mocha"
                else:
                    environment_info["framework"] = "jest"  # Default
            elif "java" in setup_lower:
                environment_info["language"] = "java"
                if "junit" in setup_lower:
                    environment_info["framework"] = "junit"
                else:
                    environment_info["framework"] = "junit"  # Default
            elif "c#" in setup_lower or "csharp" in setup_lower:
                environment_info["language"] = "csharp"
                environment_info["framework"] = "nunit"
            
            return environment_info
            
        except Exception as e:
            logger.error(f"Error parsing environment setup: {str(e)}")
            return {"language": "unknown", "framework": "unknown", "dependencies": [], "setup_commands": []}
    
    def get_unique_test_cases_by_process_title(self, process_title: str) -> List[Dict[str, Any]]:
        """
        Process name'e göre unique test case'leri session_history'den getirir
        Path: session_history->processes->test_case_optimization->output->unique_test_cases
        OR: session_history->processes->test_case_generation->output->test_cases (fallback)
        """
        try:
            # First try: test_case_optimization (optimized test cases)
            query_optimized = {
                "processes.test_case_optimization.process_name": process_title
            }
            
            session = self.session_collection.find_one(query_optimized)
            
            if session:
                test_case_optimization = session.get("processes", {}).get("test_case_optimization", {})
                output = test_case_optimization.get("output", {})
                unique_cases = output.get("unique_test_cases", [])
                
                logger.info(f"Found {len(unique_cases)} unique test cases for process '{process_title}' from test_case_optimization")
                return unique_cases
            
            # Fallback: test_case_generation (generated test cases without optimization)
            logger.info(f"No test_case_optimization found, trying test_case_generation for process '{process_title}'")
            query_generated = {
                "processes.test_case_generation.selected_process_title": process_title
            }
            
            session = self.session_collection.find_one(query_generated)
            
            if session:
                test_case_generation = session.get("processes", {}).get("test_case_generation", {})
                output = test_case_generation.get("output", {})
                
                # Try two formats:
                # 1. New format: test_case_results (array of scenario results)
                test_case_results = output.get("test_case_results", [])
                
                # Extract unique test cases from all scenarios
                unique_cases = []
                for scenario_result in test_case_results:
                    test_cases = scenario_result.get("test_cases", [])
                    for test_case in test_cases:
                        unique_cases.append({
                            "test_case_id": test_case.get("test_case_id") or test_case.get("TestCaseID"),
                            "title": test_case.get("title") or test_case.get("Title"),
                            "scenario_id": test_case.get("scenario_id") or test_case.get("ScenarioID"),
                            "description": test_case.get("description") or test_case.get("Description", ""),
                            "priority": test_case.get("priority") or test_case.get("Priority", "Medium"),
                            "preconditions": test_case.get("preconditions") or test_case.get("Preconditions", []),
                            "steps": test_case.get("steps") or test_case.get("Steps", []),
                            "expected_result": test_case.get("expected_result") or test_case.get("ExpectedResult", "")
                        })
                
                # 2. Old format fallback: test_cases (direct array)
                if not unique_cases:
                    test_cases = output.get("test_cases", [])
                    for test_case in test_cases:
                        unique_cases.append({
                            "test_case_id": test_case.get("test_case_id") or test_case.get("TestCaseID"),
                            "title": test_case.get("title") or test_case.get("Title"),
                            "scenario_id": test_case.get("scenario_id") or test_case.get("ScenarioID"),
                            "description": test_case.get("description") or test_case.get("Description", ""),
                            "priority": test_case.get("priority") or test_case.get("Priority", "Medium"),
                            "preconditions": test_case.get("preconditions") or test_case.get("Preconditions", []),
                            "steps": test_case.get("steps") or test_case.get("Steps", []),
                            "expected_result": test_case.get("expected_result") or test_case.get("ExpectedResult", "")
                        })
                
                logger.info(f"Found {len(unique_cases)} test cases for process '{process_title}' from test_case_generation")
                return unique_cases
            else:
                logger.warning(f"No session found for process name: {process_title} (checked both test_case_optimization and test_case_generation)")
                return []
            
        except Exception as e:
            logger.error(f"Error getting unique test cases: {str(e)}")
            return []
    
    async def analyze_source_code(self, source_files: List, model_name: str = None, api_key: str = None) -> Dict[str, Any]:
        """
        Yüklenen source code'ları analiz eder
        """
        try:
            if not source_files:
                return {"error": "No source files provided"}
            
            # Dosyaları kaydet ve analiz et
            file_paths = await self.file_handler.save_files(source_files)
            
            code_analysis = {
                "files": [],
                "detected_language": "unknown",
                "structure_analysis": "",
                "imports_dependencies": [],
                "functions_classes": []
            }
            
            all_content = ""
            
            for file_path in file_paths:
                try:
                    content = self.file_handler.read_file(file_path)
                    file_name = file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
                    
                    code_analysis["files"].append({
                        "name": file_name,
                        "content": content[:2000],  # İlk 2000 karakter
                        "size": len(content)
                    })
                    
                    all_content += f"\n\n### {file_name} ###\n{content}\n"
                    
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
            
            # LLM ile kod analizi yap
            if all_content and api_key:
                analysis_prompt = f"""
                Analyze the following source code and provide:
                1. Primary programming language
                2. Code structure (classes, functions, modules)
                3. Import statements and dependencies
                4. Key patterns and frameworks used
                
                Source Code:
                {all_content[:5000]}  # İlk 5000 karakter
                
                Return analysis as JSON:
                {{
                    "detected_language": "python/javascript/java/csharp",
                    "imports_dependencies": ["list", "of", "imports"],
                    "functions_classes": ["main functions and classes"],
                    "structure_analysis": "Brief description of code structure"
                }}
                """
                
                try:
                    llm_client = LLMClient(model_name=model_name, api_key=api_key, use_case='test_code_generation')
                    analysis_response = await llm_client.generate_response(
                        analysis_prompt,
                        temperature=0.1,
                        max_tokens=90000  # Use Gemini 2.5 Flash full capacity
                    )
                    
                    if analysis_response:
                        # JSON parse etmeyi dene
                        try:
                            analysis_data = json.loads(analysis_response)
                            code_analysis.update(analysis_data)
                        except json.JSONDecodeError:
                            logger.warning("Could not parse LLM analysis response as JSON")
                            code_analysis["structure_analysis"] = analysis_response
                            
                except Exception as e:
                    logger.error(f"Error in LLM code analysis: {str(e)}")
            
            # Cleanup temp files
            for file_path in file_paths:
                try:
                    import os
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass
            
            return code_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing source code: {str(e)}")
            return {"error": str(e)}
    
    async def generate_test_codes(self, 
                                process_title: str, 
                                environment_session_id: str, 
                                source_files: List, 
                                model_name: str = "llama3.2:3b",
                                custom_prompt: str = None,
                                session_id: str = None,
                                environment_name: str = None,
                                output_format: str = "JSON",
                                api_key: str = None,
                                max_test_cases: int = None) -> Dict[str, Any]:
        """
        Ana test code generation fonksiyonu
        
        Args:
            max_test_cases: Optional limit on number of test cases to process (for batch processing)
        """
        try:
            # Validate required environment_name
            if not environment_name or environment_name.strip() == "":
                return {
                    "success": False, 
                    "error": "Test Code Generation Process Name is required and cannot be empty"
                }

            logger.info(f"🔍 Debug: Test code generation parameters:")
            logger.info(f"  - process_title: {process_title}")
            logger.info(f"  - environment_session_id: {environment_session_id}")
            logger.info(f"  - session_id: {session_id}")
            logger.info(f"  - environment_name: {environment_name}")
            logger.info(f"  - model_name: {model_name}")
            logger.info(f"  - api_key provided: {'Yes' if api_key else 'No'}")
            logger.info(f"  - max_test_cases: {max_test_cases if max_test_cases else 'unlimited'}")
            
            # 1. Environment setup bilgilerini al
            environment_setups = self.get_environment_setups()
            selected_env = None
            for env in environment_setups:
                if env["session_id"] == environment_session_id:
                    selected_env = env
                    break
            
            if not selected_env:
                return {"success": False, "error": "Selected environment setup not found"}
            
            # 2. Unique test case'leri al
            unique_test_cases = self.get_unique_test_cases_by_process_title(process_title)
            if not unique_test_cases:
                return {"success": False, "error": "No unique test cases found for this process"}
            
            # Apply max_test_cases limit if specified
            if max_test_cases and max_test_cases > 0:
                original_count = len(unique_test_cases)
                unique_test_cases = unique_test_cases[:max_test_cases]
                logger.info(f"⚠️ Limited test cases from {original_count} to {len(unique_test_cases)} due to max_test_cases limit")
            
            # 3. Source code'u analiz et
            code_analysis = await self.analyze_source_code(source_files, model_name, api_key)
            if "error" in code_analysis:
                return {"success": False, "error": f"Source code analysis failed: {code_analysis['error']}"}
            
            # 4. Her unique test case için test kodu üret - Gemini API optimizasyonu
            logger.info(f"🤖 Initializing LLM client for model: {model_name}")
            
            # Gemini API için özel timeout ayarları
            is_gemini = 'gemini' in model_name.lower()
            if is_gemini:
                logger.info(f"🔮 Gemini API detected - applying special configurations")
            
            try:
                llm_client = LLMClient(model_name=model_name, api_key=api_key, use_case='test_code_generation')
                logger.info(f"✅ LLM client initialized successfully")
            except Exception as client_error:
                logger.error(f"❌ Failed to initialize LLM client: {str(client_error)}")
                return {"success": False, "error": f"LLM client initialization failed: {str(client_error)}"}
            
            generated_tests = []
            environment_info = selected_env["environment_info"]
            successful_generations = 0
            
            # Gemini için batch processing yerine sequential processing
            total_cases = len(unique_test_cases)
            logger.info(f"📊 Processing {total_cases} test cases with {model_name}")
            
            for i, test_case in enumerate(unique_test_cases):
                try:
                    logger.info(f"🔄 Generating test code {i+1}/{total_cases}")
                    
                    # Gemini API için retry mekanizması
                    max_retries = 3 if is_gemini else 1
                    retry_count = 0
                    test_code = None
                    
                    while retry_count < max_retries and not test_code:
                        try:
                            test_code = await self._generate_single_test_code(
                                test_case, 
                                code_analysis, 
                                environment_info, 
                                llm_client,
                                i + 1,
                                custom_prompt
                            )
                            if test_code:
                                successful_generations += 1
                                generated_tests.append(test_code)
                                logger.info(f"✅ Successfully generated test {i+1}/{total_cases}")
                                break
                                
                        except Exception as retry_error:
                            retry_count += 1
                            error_msg = str(retry_error)
                            
                            # Gemini API özel hata handling
                            if is_gemini and ("503" in error_msg or "unavailable" in error_msg.lower()):
                                if retry_count < max_retries:
                                    wait_time = 2 ** retry_count  # Exponential backoff
                                    logger.warning(f"⏳ Gemini API unavailable, waiting {wait_time}s before retry {retry_count}/{max_retries}")
                                    await asyncio.sleep(wait_time)
                                    continue
                                else:
                                    logger.error(f"❌ Gemini API still unavailable after {max_retries} retries")
                            elif is_gemini and ("timeout" in error_msg.lower() or "TimeoutError" in error_msg):
                                if retry_count < max_retries:
                                    logger.warning(f"⏰ Gemini API timeout, retry {retry_count}/{max_retries}")
                                    continue
                                else:
                                    logger.error(f"❌ Gemini API timeout after {max_retries} retries")
                            else:
                                logger.error(f"❌ Error in test generation: {error_msg}")
                            
                            # Son retry ise hata kaydı yap
                            if retry_count >= max_retries:
                                generated_tests.append({
                                    "test_case_id": test_case.get("TestCaseID", f"TC_{i+1}"),
                                    "title": test_case.get("Title", "Unknown Test"),
                                    "status": "error",
                                    "error": error_msg,
                                    "code": None,
                                    "retry_count": retry_count
                                })
                    
                    # Gemini API için rate limiting
                    if is_gemini and i < total_cases - 1:  # Son case değilse
                        await asyncio.sleep(0.5)  # 500ms bekle
                        
                except Exception as e:
                    logger.error(f"❌ Critical error generating test code for test case {i+1}: {str(e)}")
                    generated_tests.append({
                        "test_case_id": test_case.get("TestCaseID", f"TC_{i+1}"),
                        "title": test_case.get("Title", "Unknown Test"),
                        "status": "error",
                        "error": str(e),
                        "code": None
                    })
            
            logger.info(f"📊 Generation complete: {successful_generations}/{total_cases} successful")
            
            # 5. Sonuçları kaydet
            result = {
                "success": True,
                "process_title": process_title,
                "environment_session_id": environment_session_id,
                "environment_info": environment_info,
                "total_test_cases": len(unique_test_cases),
                "generated_tests": generated_tests,
                "generated_count": len([t for t in generated_tests if t.get("status") == "success"]),
                "failed_count": len([t for t in generated_tests if t.get("status") == "error"]),
                "model_name": model_name,
                "custom_prompt": custom_prompt,
                "output_format": output_format,
                "timestamp": datetime.now().isoformat()
            }
            
            # Sonuçları veritabanına kaydet (both session_history and legacy collection)
            self._save_test_generation_results(result, session_id, environment_name)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in test code generation: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _generate_single_test_code(self, 
                                       test_case: Dict[str, Any], 
                                       code_analysis: Dict[str, Any], 
                                       environment_info: Dict[str, Any], 
                                       llm_client: LLMClient,
                                       test_number: int,
                                       custom_prompt: str = None) -> Dict[str, Any]:
        """
        Tek bir test case için test kodu üretir
        """
        try:
            language = environment_info.get("language", "python")
            framework = environment_info.get("framework", "pytest")
            
            # Test case bilgilerini hazırla
            test_case_info = {
                "id": test_case.get("TestCaseID", f"TC_{test_number}"),
                "title": test_case.get("Title", ""),
                "description": test_case.get("Description", ""),
                "objective": test_case.get("Objective", ""),
                "steps": test_case.get("TestSteps", []) if test_case.get("TestSteps") else []
            }
            
            # Framework'e özel template'ler
            framework_templates = {
                "pytest": {
                    "imports": "import pytest\nimport unittest.mock as mock",
                    "class_prefix": "class Test",
                    "method_prefix": "def test_",
                    "assertion_style": "assert"
                },
                "unittest": {
                    "imports": "import unittest\nfrom unittest import mock",
                    "class_prefix": "class Test",
                    "method_prefix": "def test_",
                    "assertion_style": "self.assertEqual"
                },
                "jest": {
                    "imports": "const request = require('supertest');\nconst { expect } = require('@jest/globals');",
                    "describe_prefix": "describe(",
                    "test_prefix": "test(",
                    "assertion_style": "expect"
                },
                "junit": {
                    "imports": "import org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;",
                    "class_prefix": "@Test\npublic class",
                    "method_prefix": "@Test\npublic void test",
                    "assertion_style": "assertEquals"
                }
            }
            
            template = framework_templates.get(framework, framework_templates["pytest"])
            
            # LLM prompt'u oluştur
            prompt = self._create_test_generation_prompt(
                test_case_info, 
                code_analysis, 
                environment_info, 
                template,
                custom_prompt
            )
            
            # Model tipine göre timeout ayarları
            is_gemini = hasattr(llm_client, 'is_gemini') and llm_client.is_gemini
            
            # Büyük modeller için daha uzun timeout (20B+ parametreli modeller yavaş olabilir)
            is_large_model = any(size in llm_client.model_name.lower() for size in ['20b', '30b', '70b', '120b'])
            
            if is_gemini:
                timeout_seconds = 180  # Gemini için 3 dakika
            elif is_large_model:
                timeout_seconds = 120  # Büyük local modeller için 2 dakika
            else:
                timeout_seconds = 60   # Küçük local modeller için 1 dakika
            
            logger.info(f"🚀 Sending request to {llm_client.model_name} with {timeout_seconds}s timeout")
            
            try:
                # LLM'den test kodu al - timeout ile
                response = await asyncio.wait_for(
                    llm_client.generate_response(
                        prompt,
                        temperature=0.2,
                        max_tokens=90000 if is_gemini else 8192
                    ),
                    timeout=timeout_seconds
                )
                
                if not response:
                    raise ValueError("No response from LLM")
                    
                logger.info(f"✅ Received response from {llm_client.model_name} (length: {len(response)})")
                
            except asyncio.TimeoutError:
                error_msg = f"Request to {llm_client.model_name} timed out after {timeout_seconds} seconds"
                logger.error(f"⏰ {error_msg}")
                raise TimeoutError(error_msg)
            except Exception as api_error:
                logger.error(f"🚨 API Error with {llm_client.model_name}: {str(api_error)}")
                raise
            
            # Test kodu response'unu temizle
            test_code = self._clean_test_code_response(response, language)
            
            return {
                "test_case_id": test_case_info["id"],
                "title": test_case_info["title"],
                "description": test_case_info["description"],
                "objective": test_case_info["objective"],
                "framework": framework,
                "language": language,
                "code": test_code,
                "status": "success",
                "filename": self._generate_filename(test_case_info["title"], language, test_number)
            }
            
        except Exception as e:
            logger.error(f"Error generating single test code: {str(e)}")
            return {
                "test_case_id": test_case.get("TestCaseID", f"TC_{test_number}"),
                "title": test_case.get("Title", "Unknown Test"),
                "status": "error",
                "error": str(e),
                "code": None
            }
    
    def _create_test_generation_prompt(self, 
                                     test_case_info: Dict[str, Any], 
                                     code_analysis: Dict[str, Any], 
                                     environment_info: Dict[str, Any], 
                                     template: Dict[str, Any],
                                     custom_prompt: str = None) -> str:
        """
        Test code generation için LLM prompt'u oluşturur
        """
        language = environment_info.get("language", "python")
        framework = environment_info.get("framework", "pytest")
        
        # Use custom prompt if provided, otherwise use default
        if custom_prompt and custom_prompt.strip():
            base_prompt = custom_prompt
        else:
            base_prompt = "You are an expert test automation engineer. Generate executable test code for the following test case."
        
        prompt = f"""
{base_prompt}

## TEST CASE TO IMPLEMENT:
- **ID**: {test_case_info['id']}
- **Title**: {test_case_info['title']}
- **Description**: {test_case_info['description']}
- **Objective**: {test_case_info['objective']}

## SOURCE CODE CONTEXT:
**Language**: {language}
**Files Analyzed**: {[f["name"] for f in code_analysis.get("files", [])]}
**Code Structure**: {code_analysis.get("structure_analysis", "Not available")}
**Dependencies**: {code_analysis.get("imports_dependencies", [])}

## TEST FRAMEWORK & ENVIRONMENT:
**Framework**: {framework}
**Language**: {language}
**Required Imports**: {template.get("imports", "")}

## REQUIREMENTS:
1. Generate complete, executable test code using {framework}
2. Use proper {framework} conventions and syntax
3. Include necessary imports and setup
4. Make the test specific to the test case objective
5. Add meaningful assertions
6. Include docstring explaining the test purpose
7. Make it ready to run without modifications

## OUTPUT FORMAT:
Return ONLY the executable test code, no explanations or markdown formatting.
"""
        
        return prompt.strip()
    
    def _clean_test_code_response(self, response: str, language: str) -> str:
        """
        LLM response'undan temiz test kodu çıkarır
        """
        try:
            # Markdown code blocks'ları temizle
            cleaned = response.strip()
            
            # ```python veya ``` ile başlıyorsa temizle
            if cleaned.startswith(f"```{language}"):
                cleaned = cleaned[len(f"```{language}"):].strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:].strip()
            
            # Son ``` varsa temizle
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning test code response: {str(e)}")
            return response
    
    def _generate_filename(self, title: str, language: str, test_number: int) -> str:
        """
        Test dosyası için uygun filename oluşturur
        """
        try:
            # Title'ı temizle ve filename uygun hale getir
            import re
            clean_title = re.sub(r'[^\w\s-]', '', title.lower())
            clean_title = re.sub(r'[-\s]+', '_', clean_title)
            
            # Dil uzantılarına göre filename oluştur
            extensions = {
                "python": ".py",
                "javascript": ".js", 
                "java": ".java",
                "csharp": ".cs"
            }
            
            extension = extensions.get(language, ".py")
            return f"test_{clean_title}_{test_number:02d}{extension}"
            
        except Exception as e:
            logger.error(f"Error generating filename: {str(e)}")
            return f"test_case_{test_number:02d}.py"
    
    def _save_test_generation_results(self, results: Dict[str, Any], session_id: str = None, environment_name: str = None):
        """
        Test generation sonuçlarını veritabanına processes.test_code_generation altına kaydet
        Cleaned structure - removes redundancies and unifies field names
        """
        try:
            logger.info(f"🔍 Debug: Attempting to save session with session_id: {session_id}")
            logger.info(f"🔍 Debug: Environment name: {environment_name}")
            logger.info(f"🔍 Debug: Results keys: {list(results.keys())}")
            
            # Session_id varsa session_history'ye kaydet
            if session_id:
                logger.info(f"📝 Creating clean session document for session_id: {session_id}")
                
                # Create clean, unified structure
                clean_structure = {
                    "status": "completed" if results.get("success") else "failed",
                    "timestamp": datetime.now().isoformat(),
                    "process_name": environment_name,  # Required field from frontend
                    "code_generation_process_name": environment_name,  # Required field for Test Execution
                    "model_name": results.get("model_name", "llama3.2:3b"),  # Unified field name
                    "input": {
                        "process_title": results.get("process_title"),
                        "model_name": results.get("model_name", "llama3.2:3b"),  # Unified field name
                        "environment_session_id": results.get("environment_session_id"),
                        "output_format": results.get("output_format", "JSON"),  # Add missing UI field
                        "total_test_cases": results.get("total_test_cases", 0)
                    },
                    "output": {
                        "success": results.get("success", False),
                        "generated_tests": results.get("generated_tests", []),
                        "generated_count": results.get("generated_count", 0),
                        "failed_count": results.get("failed_count", 0),
                        "environment_info": results.get("environment_info", {}),  # Keep only one copy
                        "data": results  # Backward compatibility
                    }
                }
                
                # Add custom_prompt only if provided
                if results.get("custom_prompt"):
                    clean_structure["input"]["custom_prompt"] = results.get("custom_prompt")
                
                # Use dot notation to safely update only test_code_generation process
                update_query = {
                    "$set": {
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                        "processes.test_code_generation": clean_structure
                    }
                }
                
                result = self.session_collection.update_one(
                    {"session_id": session_id},
                    update_query,
                    upsert=True
                )
                
                logger.info(f"✅ Clean structure saved - matched: {result.matched_count}, modified: {result.modified_count}, upserted: {result.upserted_id}")
                logger.info(f"Test generation results saved to session_history for session: {session_id}")
                
                # Verify save by querying back
                saved_doc = self.session_collection.find_one({"session_id": session_id})
                if saved_doc:
                    logger.info(f"✅ Verification: Clean document found in session_history with _id: {saved_doc.get('_id')}")
                else:
                    logger.error(f"❌ Verification failed: Document not found in session_history for session: {session_id}")
            else:
                logger.warning(f"⚠️ session_id is None or empty - skipping session_history save")
                logger.warning(f"⚠️ This means the results will not be saved to session_history collection")
            
            # Backward compatibility: ayrı collection'a da kaydet
            test_generation_collection = self.db["test_code_generation_results"]
            
            document = {
                **results,
                "session_id": session_id,
                "environment_name": environment_name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Upsert: process_title'a göre güncelle veya yeni oluştur
            test_generation_collection.update_one(
                {"process_title": results["process_title"]},
                {"$set": document},
                upsert=True
            )
            
            logger.info(f"Test generation results also saved to test_code_generation_results collection")
            
        except Exception as e:
            logger.error(f"Error saving test generation results: {str(e)}")

    def get_available_process_titles(self) -> List[Dict[str, Any]]:
        """
        Session history'den test case optimization process name'leri getirir
        Her process için unique test case sayısını da içerir
        Path: session_history->processes->test_case_optimization->process_name
        """
        try:
            # Session history'den process name ve unique test case sayılarını al
            pipeline = [
                {
                    "$match": {
                        "processes.test_case_optimization": {"$exists": True}
                    }
                },
                {
                    "$project": {
                        "process_name": "$processes.test_case_optimization.process_name",
                        "unique_test_cases_count": {
                            "$size": {
                                "$ifNull": ["$processes.test_case_optimization.output.unique_test_cases", []]
                            }
                        }
                    }
                },
                {
                    "$sort": {"process_name": 1}
                }
            ]
            
            results = list(self.session_collection.aggregate(pipeline))
            
            # Process name ve count bilgilerini dict olarak döndür
            process_info = [
                {
                    "process_name": r["process_name"],
                    "test_case_count": r["unique_test_cases_count"]
                }
                for r in results if r.get("process_name")
            ]
            
            logger.info(f"Found {len(process_info)} available process names with test case counts from session_history")
            return process_info
            
        except Exception as e:
            logger.error(f"Error getting available process titles: {str(e)}")
            return []
    
    def get_generated_tests_by_process_name(self, process_name: str) -> List[Dict[str, Any]]:
        """
        Get generated tests for a specific process name from session history
        Path: session_history->processes->test_code_generation->generated_tests
        
        Args:
            process_name: The process name to filter by (process_name field)
            
        Returns:
            List of generated tests with test_id, test_case_name, status, test_code
        """
        try:
            logger.info(f"Fetching generated tests for process: {process_name}")
            
            # Query session history for test_code_generation with matching process_name
            pipeline = [
                {
                    "$match": {
                        "processes.test_code_generation": {"$exists": True},
                        "processes.test_code_generation.process_name": process_name
                    }
                },
                {
                    "$project": {
                        "session_id": 1,
                        "timestamp": "$processes.test_code_generation.timestamp",
                        "generated_tests": "$processes.test_code_generation.output.generated_tests",
                        "process_name": "$processes.test_code_generation.process_name"
                    }
                },
                {
                    "$sort": {"timestamp": -1}
                },
                {
                    "$limit": 1  # Get the most recent session
                }
            ]
            
            results = list(self.session_collection.aggregate(pipeline))
            
            if not results:
                logger.warning(f"No generated tests found for process: {process_name}")
                return []
            
            # Extract generated tests from the most recent session
            latest_session = results[0]
            generated_tests = latest_session.get("generated_tests", [])
            
            # Format the tests for the response
            formatted_tests = []
            for test in generated_tests:
                formatted_test = {
                    "unique_id": test.get("unique_id", ""),
                    "test_id": test.get("test_case_id", ""),
                    "test_case_name": test.get("title", ""),
                    "status": test.get("status", "unknown"),
                    "test_code": test.get("code", ""),
                    "error": test.get("error", None),
                    "description": test.get("description", ""),
                    "filename": test.get("filename", "")
                }
                formatted_tests.append(formatted_test)
            
            logger.info(f"Found {len(formatted_tests)} generated tests for process: {process_name}")
            return formatted_tests
            
        except Exception as e:
            logger.error(f"Error getting generated tests for process {process_name}: {str(e)}")
            return []
    
    def get_process_names_with_generated_tests(self) -> List[str]:
        """
        Get list of unique process names that have generated tests
        Path: session_history->processes->test_code_generation->process_name
        
        Returns:
            List of unique process names (process_name values)
        """
        try:
            logger.info("Fetching process names with generated tests")
            
            # Query for distinct process_name values where test_code_generation exists
            pipeline = [
                {
                    "$match": {
                        "processes.test_code_generation": {"$exists": True},
                        "processes.test_code_generation.status": "completed"
                    }
                },
                {
                    "$group": {
                        "_id": "$processes.test_code_generation.process_name"
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
            
            results = list(self.session_collection.aggregate(pipeline))
            process_names = [r["_id"] for r in results if r.get("_id")]
            
            logger.info(f"Found {len(process_names)} process names with generated tests")
            return process_names
            
        except Exception as e:
            logger.error(f"Error getting process names with generated tests: {str(e)}")
            return []
