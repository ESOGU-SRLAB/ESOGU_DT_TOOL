"""
Robot Docker Executor Service
Executes ROS 2 robot tests in Docker containers
Supports both headless (parallel) and GUI (Gazebo visualization) modes
"""

import docker
import asyncio
import tempfile
import shutil
import os
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from services.ros2_test_validator import ROS2TestValidator
from models.robot_test_criteria import (
    RobotTestCriteria,
    TestExecutionResult,
    TestResult,
    BatchTestExecutionRequest,
    BatchTestExecutionResponse
)
from core.database import get_database

logger = logging.getLogger(__name__)


class RobotDockerExecutor:
    """
    Executes robot tests in Docker containers with ROS 2 validation
    Supports hybrid execution: headless batch + GUI visualization
    """
    
    def __init__(self):
        """Initialize Docker client and validator"""
        try:
            self.client = docker.from_env()
            self.client.ping()
            self.validator = ROS2TestValidator()
            self.is_available = True
            logger.info("✅ Robot Docker executor initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Docker client: {e}")
            self.client = None
            self.validator = ROS2TestValidator()
            self.is_available = False
    
    async def execute_test_in_container(
        self,
        test_code: str,
        criteria: RobotTestCriteria,
        docker_image: str = "stlc-robot-ros2:latest",
        headless: bool = True,
        timeout: int = 300,
        enable_recording: bool = False
    ) -> TestExecutionResult:
        """
        Execute a single robot test in Docker container
        
        Args:
            test_code: Robot test code to execute
            criteria: Test validation criteria
            docker_image: Docker image name
            headless: Run in headless mode (no Gazebo GUI)
            timeout: Execution timeout in seconds
            enable_recording: Record Gazebo simulation (GUI mode only)
            
        Returns:
            TestExecutionResult with validation results
        """
        
        if not self.is_available:
            return TestExecutionResult(
                test_case_id=criteria.test_case_id,
                test_name=criteria.test_name,
                result=TestResult.ERROR,
                overall_passed=False,
                execution_start_time=datetime.now().isoformat(),
                execution_end_time=datetime.now().isoformat(),
                execution_duration=0.0,
                docker_image=docker_image,
                headless_mode=headless,
                error_message="Docker not available"
            )
        
        temp_dir = None
        container = None
        
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="stlc_robot_test_")
            logger.info(f"📁 Created temp directory: {temp_dir}")
            
            # Generate validation script
            validation_script = self.validator.generate_validation_script(
                test_code=test_code,
                criteria=criteria
            )
            
            # Write validation script to file
            script_path = os.path.join(temp_dir, "test_runner.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(validation_script)
            
            logger.info(f"📝 Generated validation script: {script_path}")
            
            # Prepare environment variables
            env_vars = {
                "ROS_DOMAIN_ID": "42",
                "PYTHONUNBUFFERED": "1"
            }
            
            if headless:
                # Headless mode - disable display
                env_vars.update({
                    "DISPLAY": "",
                    "LIBGL_ALWAYS_SOFTWARE": "1",
                    "QT_QPA_PLATFORM": "offscreen"
                })
            else:
                # GUI mode - enable display
                env_vars.update({
                    "DISPLAY": ":0",
                    "QT_X11_NO_MITSHM": "1"
                })
            
            # Container configuration
            container_config = {
                "image": docker_image,
                "command": (
                    "bash -c 'source /opt/ros/humble/setup.bash && source "
                    f"{os.getenv('LEGACY_ROS2_SETUP_SCRIPT', '/opt/stlc_ros/install/setup.bash')} "
                    "&& python3 /test/test_runner.py'"
                ),
                "volumes": {
                    temp_dir: {'bind': '/test', 'mode': 'rw'}
                },
                "working_dir": "/test",
                "environment": env_vars,
                "detach": True,
                "remove": False,  # Keep for log retrieval
                "mem_limit": "4g",  # ROS 2 needs more memory
                "shm_size": "512m",  # Shared memory for ROS 2
                "network_mode": "bridge"
            }
            
            # Add X11 socket for GUI mode
            if not headless:
                # For Windows with VcXsrv or X410
                container_config["network_mode"] = "host"
                logger.info("🖥️  Running in GUI mode with X11 forwarding")
            else:
                logger.info("🔇 Running in headless mode")
            
            # Start container
            logger.info(f"🚀 Starting container with image: {docker_image}")
            container = self.client.containers.run(**container_config)
            logger.info(f"📦 Container started: {container.short_id}")
            
            # Wait for completion with timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result['StatusCode']
                logger.info(f"✅ Container execution completed with exit code: {exit_code}")
            except Exception as timeout_err:
                logger.error(f"⏱️  Container execution timeout: {timeout_err}")
                container.stop(timeout=10)
                exit_code = -1
            
            # Retrieve logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
            
            # Read validation results JSON
            validation_json_path = os.path.join(temp_dir, "validation_results.json")
            
            if os.path.exists(validation_json_path):
                with open(validation_json_path, 'r') as f:
                    validation_json = f.read()
                
                # Parse results
                container_info = {
                    "container_id": container.short_id,
                    "docker_image": docker_image,
                    "headless": headless
                }
                
                result = self.validator.parse_validation_results(
                    validation_json,
                    container_info
                )
                
                # Add stdout/stderr
                result.stdout = stdout
                result.stderr = stderr
                
                logger.info(f"📊 Validation results parsed: {result.result}")
                return result
            else:
                # No validation results file - execution failed
                logger.error("❌ Validation results file not found")
                return TestExecutionResult(
                    test_case_id=criteria.test_case_id,
                    test_name=criteria.test_name,
                    result=TestResult.ERROR,
                    overall_passed=False,
                    execution_start_time=datetime.now().isoformat(),
                    execution_end_time=datetime.now().isoformat(),
                    execution_duration=0.0,
                    docker_image=docker_image,
                    headless_mode=headless,
                    container_id=container.short_id if container else None,
                    stdout=stdout,
                    stderr=stderr,
                    error_message="Validation results file not found - test may have crashed"
                )
        
        except docker.errors.ImageNotFound:
            logger.error(f"❌ Docker image not found: {docker_image}")
            return TestExecutionResult(
                test_case_id=criteria.test_case_id,
                test_name=criteria.test_name,
                result=TestResult.ERROR,
                overall_passed=False,
                execution_start_time=datetime.now().isoformat(),
                execution_end_time=datetime.now().isoformat(),
                execution_duration=0.0,
                docker_image=docker_image,
                headless_mode=headless,
                error_message=f"Docker image not found: {docker_image}"
            )
        
        except Exception as e:
            logger.error(f"❌ Container execution error: {e}")
            return TestExecutionResult(
                test_case_id=criteria.test_case_id,
                test_name=criteria.test_name,
                result=TestResult.ERROR,
                overall_passed=False,
                execution_start_time=datetime.now().isoformat(),
                execution_end_time=datetime.now().isoformat(),
                execution_duration=0.0,
                docker_image=docker_image,
                headless_mode=headless,
                error_message=f"Execution error: {str(e)}"
            )
        
        finally:
            # Cleanup
            if container:
                try:
                    container.remove(force=True)
                    logger.info(f"🧹 Container removed: {container.short_id}")
                except:
                    pass
            
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"🧹 Temp directory cleaned: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")
    
    async def execute_batch_tests(
        self,
        request: BatchTestExecutionRequest,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Execute batch of robot tests with hybrid execution:
        - Headless tests run in parallel (bulk)
        - One visual test runs in Gazebo GUI (if specified)
        
        Args:
            request: Batch execution request
            session_id: Unique session identifier
            
        Returns:
            Execution summary with results
        """
        
        logger.info(f"🚀 Starting batch robot test execution: {session_id}")
        logger.info(f"📊 Total tests: {len(request.test_ids)}")
        logger.info(f"🔀 Max parallel: {request.max_parallel}")
        logger.info(f"🖥️  Visual test: {request.visual_test_id or 'None'}")
        
        # Get database
        db = await get_database()
        
        # Fetch test cases from database
        test_cases = await self._fetch_test_cases(
            db,
            request.process_name,
            request.test_ids
        )
        
        if not test_cases:
            logger.error("❌ No test cases found")
            return {
                "success": False,
                "error": "No test cases found for execution"
            }
        
        # Separate visual test from headless tests
        visual_test = None
        headless_tests = []
        
        for test_case in test_cases:
            test_id = test_case.get("test_case_id") or test_case.get("test_id")
            if test_id == request.visual_test_id:
                visual_test = test_case
            else:
                headless_tests.append(test_case)
        
        logger.info(f"📦 Headless tests: {len(headless_tests)}")
        logger.info(f"🖥️  Visual tests: {1 if visual_test else 0}")
        
        # Prepare execution tasks
        headless_task = None
        visual_task = None
        
        # Start headless batch execution
        if headless_tests:
            headless_task = asyncio.create_task(
                self._execute_headless_batch(
                    headless_tests,
                    request.docker_image,
                    request.max_parallel,
                    request.timeout_per_test,
                    session_id
                )
            )
        
        # Start visual test execution (if specified)
        if visual_test:
            visual_task = asyncio.create_task(
                self._execute_visual_test(
                    visual_test,
                    request.docker_image,
                    request.timeout_per_test,
                    request.enable_gazebo_recording,
                    session_id
                )
            )
        
        # Wait for both to complete
        results = {
            "headless_results": [],
            "visual_result": None
        }
        
        if headless_task:
            results["headless_results"] = await headless_task
        
        if visual_task:
            results["visual_result"] = await visual_task
        
        # Compile final results
        all_results = results["headless_results"]
        if results["visual_result"]:
            all_results.append(results["visual_result"])
        
        # Save to database
        await self._save_batch_results(
            db,
            session_id,
            request,
            all_results
        )
        
        # Calculate statistics
        passed_count = sum(1 for r in all_results if r.overall_passed)
        failed_count = sum(1 for r in all_results if not r.overall_passed and r.result != TestResult.ERROR)
        error_count = sum(1 for r in all_results if r.result == TestResult.ERROR)
        
        logger.info(f"✅ Batch execution completed: {session_id}")
        logger.info(f"📊 Results - Passed: {passed_count}, Failed: {failed_count}, Error: {error_count}")
        
        return {
            "success": True,
            "session_id": session_id,
            "total_tests": len(all_results),
            "passed": passed_count,
            "failed": failed_count,
            "errors": error_count,
            "results": [r.dict() for r in all_results]
        }
    
    async def _execute_headless_batch(
        self,
        test_cases: List[Dict],
        docker_image: str,
        max_parallel: int,
        timeout: int,
        session_id: str
    ) -> List[TestExecutionResult]:
        """Execute tests in headless mode with parallelization"""
        
        logger.info(f"🔇 Starting headless batch: {len(test_cases)} tests, {max_parallel} parallel")
        
        # Create semaphore for parallelization
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def execute_one(test_case: Dict) -> TestExecutionResult:
            async with semaphore:
                test_id = test_case.get("test_case_id") or test_case.get("test_id")
                logger.info(f"▶️  Executing headless test: {test_id}")
                
                # Extract criteria
                criteria = self.validator.extract_criteria_from_test_case(test_case)
                if not criteria:
                    logger.error(f"❌ Failed to extract criteria for: {test_id}")
                    return None
                
                # Get test code
                test_code = test_case.get("code", "")
                
                # Execute in container
                result = await self.execute_test_in_container(
                    test_code=test_code,
                    criteria=criteria,
                    docker_image=docker_image,
                    headless=True,
                    timeout=timeout
                )
                
                logger.info(f"{'✅' if result.overall_passed else '❌'} {test_id}: {result.result}")
                return result
        
        # Execute all tests in parallel
        tasks = [execute_one(tc) for tc in test_cases]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None and exceptions
        valid_results = [r for r in results if isinstance(r, TestExecutionResult)]
        
        logger.info(f"✅ Headless batch completed: {len(valid_results)}/{len(test_cases)} successful")
        return valid_results
    
    async def _execute_visual_test(
        self,
        test_case: Dict,
        docker_image: str,
        timeout: int,
        enable_recording: bool,
        session_id: str
    ) -> Optional[TestExecutionResult]:
        """Execute single test in GUI mode with Gazebo visualization"""
        
        test_id = test_case.get("test_case_id") or test_case.get("test_id")
        logger.info(f"🖥️  Starting visual test: {test_id}")
        
        # Extract criteria
        criteria = self.validator.extract_criteria_from_test_case(test_case)
        if not criteria:
            logger.error(f"❌ Failed to extract criteria for visual test: {test_id}")
            return None
        
        # Get test code
        test_code = test_case.get("code", "")
        
        # Execute in GUI container
        result = await self.execute_test_in_container(
            test_code=test_code,
            criteria=criteria,
            docker_image=docker_image,
            headless=False,  # GUI mode
            timeout=timeout,
            enable_recording=enable_recording
        )
        
        logger.info(f"🖥️  Visual test completed: {test_id} - {result.result}")
        return result
    
    async def _fetch_test_cases(
        self,
        db,
        process_name: str,
        test_ids: List[str]
    ) -> List[Dict]:
        """
        Fetch test codes from database using unique identifiers
        
        Args:
            db: Database connection
            process_name: Process name to filter by
            test_ids: List of unique_id values to fetch
        
        Returns:
            List of test dictionaries with test_code field
        """
        
        try:
            logger.info(f"📦 Fetching test codes for process: {process_name}, unique_ids: {test_ids}")
            
            # Query test code generation process using aggregation pipeline
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
            
            results = await db.session_history.aggregate(pipeline).to_list(length=None)
            
            if not results:
                logger.warning(f"⚠️ No test code generation session found for process: {process_name}")
                return []
            
            # Extract generated tests from the most recent session
            latest_session = results[0]
            generated_tests = latest_session.get("generated_tests", [])
            
            if not generated_tests:
                logger.warning(f"⚠️ No generated tests in session for process: {process_name}")
                return []
            
            # Filter and format tests using unique_id
            test_cases = []
            for test in generated_tests:
                unique_id = test.get("unique_id", "")
                if unique_id in test_ids:
                    formatted_test = {
                        "unique_id": unique_id,
                        "test_id": test.get("test_case_id", ""),
                        "test_case_name": test.get("title", ""),
                        "test_code": test.get("code", ""),
                        "status": test.get("status", "unknown"),
                        "description": test.get("description", ""),
                        "filename": test.get("filename", "")
                    }
                    test_cases.append(formatted_test)
                    logger.info(f"  ✅ Found test: {unique_id} / {formatted_test['test_id']} ({len(formatted_test['test_code'])} chars)")
            
            logger.info(f"📦 Fetched {len(test_cases)} test codes from database (requested: {len(test_ids)})")
            return test_cases
            
        except Exception as e:
            logger.error(f"❌ Error fetching test codes: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def _save_batch_results(
        self,
        db,
        session_id: str,
        request: BatchTestExecutionRequest,
        results: List[TestExecutionResult]
    ):
        """Save batch execution results to database"""
        
        try:
            # Prepare document
            batch_doc = {
                "session_id": session_id,
                "timestamp": datetime.now(),
                "process_name": request.process_name,
                "request": request.dict(),
                "results": [r.dict() for r in results],
                "summary": {
                    "total_tests": len(results),
                    "passed": sum(1 for r in results if r.overall_passed),
                    "failed": sum(1 for r in results if not r.overall_passed and r.result != TestResult.ERROR),
                    "errors": sum(1 for r in results if r.result == TestResult.ERROR)
                }
            }
            
            # Insert into database
            await db.robot_test_executions.insert_one(batch_doc)
            logger.info(f"💾 Saved batch results to database: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving batch results: {e}")
