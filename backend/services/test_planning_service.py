from utils.file_handler import FileHandler
from utils.model_client import LLMClient
from utils.text_processor import TextProcessor
from core.prompt_manager import get_base_prompt, save_session_data, get_test_planning_system_suffix
import logging
import os
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('test_planning_service.log')
    ]
)

logger = logging.getLogger("TestPlanningService")
logger.debug("Test log message - If you see this, logging is working!")

class TestPlanningService:
    def __init__(self):
        self.file_handler = FileHandler()
        self.model_client = LLMClient()
        self.text_processor = TextProcessor()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("TestPlanningService initialized")

    def normalize_prompt(self, text):
        return ' '.join(text.strip().split()).lower()

    async def run_test_planning(self, files, model_key=None, custom_prompt=None, session_id=None, api_key=None):
        try:
            self.logger.debug(f"Starting test planning for {len(files)} files with model: {model_key}")
            
            if not files:
                raise ValueError("No files provided for test planning")
                
            file_paths = await self.file_handler.save_files(files)
            self.logger.debug(f"Files saved: {file_paths}")
            
            if not file_paths:
                raise ValueError("Failed to save uploaded files")

            # Dosya içeriklerini ayır: requirement ve kod dosyaları
            requirement_doc_content = ""
            code_files_content = ""
            for path in file_paths:
                filename = os.path.basename(path).lower()
                content = self.file_handler.read_file(path)
                if "requirement" in filename or "spec" in filename or filename.endswith('.md') or filename.endswith('.txt'):
                    requirement_doc_content += content + "\n"
                else:
                    code_files_content += f"\n\n### File: {os.path.basename(path)}\n\n{content}"

            model_client = LLMClient()
            self.logger.info(f"Model key: {model_key}")
            model_name = None
            if model_key:
                model_name = model_client.get_model_identifier(model_key)
                model_client = LLMClient(model_name, api_key, use_case='test_planning')  # API key ve use_case eklendi
                self.logger.info(f"Using model: {model_name} for test planning with API key provided: {bool(api_key)}")
            else:
                self.logger.info("No model specified, using default model")

            # Bugünün tarihini al
            today = datetime.now().strftime("%Y-%m-%d")

            used_prompt = None
            prompt_source = None
            base_prompt = get_base_prompt("test_planning")
            system_suffix = get_test_planning_system_suffix()

            if custom_prompt:
                used_prompt = custom_prompt
                prompt_source = "custom_parameter"
                self.logger.info("Using custom prompt provided by user in this request")
            else:
                if base_prompt:
                    used_prompt = base_prompt
                    prompt_source = "base_db"
                    self.logger.info("Using base prompt from database")
                else:
                    raise ValueError("No prompt found in database for test_planning process. Please add a prompt to the database.")
            # Token management similar to requirement_analysis_service
            prompt_base_length = len((used_prompt + system_suffix).split())
            code_length = len(code_files_content.split())
            req_length = len(requirement_doc_content.split())
            total_estimated_tokens = prompt_base_length + code_length + req_length
            
            self.logger.debug(f"Estimated token usage: base={prompt_base_length}, code={code_length}, req={req_length}, total={total_estimated_tokens}")
            
            # If total is too large, truncate content to fit within limits
            MAX_INPUT_TOKENS = 95000  # Gemini 2.5 Flash supports up to 100K tokens
            if total_estimated_tokens > MAX_INPUT_TOKENS:
                self.logger.warning(f"Input too large ({total_estimated_tokens} tokens), truncating content...")
                
                # Reserve space for the base prompt
                available_tokens = MAX_INPUT_TOKENS - prompt_base_length - 200  # buffer
                
                # Split available tokens between code and requirements (prioritize requirements)
                if req_length > available_tokens // 2:
                    req_tokens = available_tokens // 2
                    code_tokens = available_tokens - req_tokens
                else:
                    req_tokens = req_length
                    code_tokens = available_tokens - req_tokens
                
                # Truncate content if needed (cleanly)
                if req_length > req_tokens:
                    req_words = requirement_doc_content.split()
                    requirement_doc_content = " ".join(req_words[:req_tokens])
                    
                if code_length > code_tokens:
                    code_words = code_files_content.split()
                    code_files_content = " ".join(code_words[:code_tokens])
                
                self.logger.info(f"Content truncated - req: {len(requirement_doc_content.split())} tokens, code: {len(code_files_content.split())} tokens")

            today = datetime.now().strftime("%Y-%m-%d")
            
            # Add system suffix to the prompt
            full_prompt = used_prompt + system_suffix
            planning_prompt = full_prompt.format(
                code=code_files_content,
                requirement_document=requirement_doc_content,
                today=today
            )

            MAX_TOKENS = 95000  # Utilize Gemini 2.5's full capacity
            if len(planning_prompt.split()) > MAX_TOKENS:
                self.logger.debug(f"Token limit exceeded: {len(planning_prompt.split())} > {MAX_TOKENS}")
                chunks = self.text_processor.chunk_text(planning_prompt)
                all_plans = []
                for i, chunk in enumerate(chunks):
                    self.logger.debug(f"Processing chunk {i+1}/{len(chunks)}")
                    plan = await model_client.generate_response(chunk)
                    if plan:
                        all_plans.append(plan)
                final_plan = self._combine_plans(all_plans)
            else:
                self.logger.debug(f"Using single plan. Token count: {len(planning_prompt.split())}")
                final_plan = await model_client.generate_response(planning_prompt, max_tokens=90000)
            
            if not final_plan:
                raise ValueError("Failed to generate test planning")

            # Parse and process JSON response
            final_plan = self._process_test_planning_response(final_plan, today)
                
            file_names = [os.path.basename(path) for path in file_paths]
            files_header = "Files analyzed:\n" + "\n".join(file_names)

            edited_prompt = False
            if custom_prompt and base_prompt:
                edited_prompt = (self.normalize_prompt(custom_prompt) != self.normalize_prompt(base_prompt))
            elif custom_prompt and not base_prompt:
                edited_prompt = True
            
            session_data = {
                "session_id": session_id,
                "output": {
                    "files": files_header,
                    "plan": final_plan
                },
                "edited_prompt": edited_prompt,
                "used_prompt": used_prompt,
                "used_model": model_name
            }
            save_session_data(session_data, process_type="test_planning")
            
            for path in file_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temporary file {path}: {str(e)}")
            
            return {
                "status": "success",
                "plans": [{
                    "files": files_header,
                    "plan": final_plan
                }],
                "prompt_info": {
                    "source": prompt_source
                },
                "session_id": session_id or "unknown"
            }

        except Exception as e:
            self.logger.error(f"Error in run_test_planning: {str(e)}")
            raise

    def _combine_file_contents(self, file_paths):
        combined_content = ""
        for path in file_paths:
            code_content = self.file_handler.read_file(path)
            combined_content += f"\n\n### File: {os.path.basename(path)}\n\n{code_content}"
        return combined_content

    def _combine_plans(self, plans):
        # Clean each plan and join them properly
        cleaned_plans = []
        for plan in plans:
            if plan:
                cleaned = self._format_planning_output(plan)
                if cleaned.strip():
                    cleaned_plans.append(cleaned)
        
        if not cleaned_plans:
            return "No test planning results generated."
        
        return "\n\n".join(cleaned_plans)
    
    def _format_planning_output(self, text):
        """Clean and format test planning output for better UI presentation"""
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize line breaks
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove extra spaces and tabs
            cleaned_line = ' '.join(line.split())
            
            # Skip empty lines at the beginning and end, but preserve structure
            if cleaned_line or (cleaned_lines and cleaned_lines[-1]):
                cleaned_lines.append(cleaned_line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
        
        # Join with single line breaks and ensure proper spacing
        result = '\n'.join(cleaned_lines)
        
        # Remove any technical truncation messages that might have slipped through
        technical_messages = [
            '[Response truncated due to token limit]',
            '[Content truncated due to length. Please provide a brief analysis.]',
            '[Brief analysis requested due to token limits.]',
            '[Analysis based on truncated input due to token limits]',
            '[Content truncated due to size limits]'
        ]
        
        for msg in technical_messages:
            result = result.replace(msg, '').strip()
        
        return result
    
    def _process_test_planning_response(self, response, today):
        """Process LLM response and ensure it's in the correct JSON format with calculated dates"""
        import re
        import json
        from datetime import datetime, timedelta
        
        if not response:
            return ""
        
        self.logger.debug("Processing test planning response...")
        
        # Try to extract JSON from the response
        json_match = re.search(r'\[[\s\S]*\]', response)
        
        if json_match:
            try:
                json_str = json_match.group(0)
                # Parse JSON
                tasks = json.loads(json_str)
                
                # Validate it's a list
                if not isinstance(tasks, list):
                    self.logger.warning("Parsed JSON is not a list, treating as text response")
                    return self._format_planning_output(response)
                
                # Process dates in each task
                base_date = datetime.strptime(today, "%Y-%m-%d")
                current_end_date = base_date  # Track the last end date for sequential tasks
                
                for task in tasks:
                    if isinstance(task, dict):
                        duration = task.get("Duration (days)", 5)  # Default 5 days if not specified
                        
                        # Try to parse duration as integer
                        try:
                            duration = int(duration)
                        except (ValueError, TypeError):
                            self.logger.warning(f"Invalid duration value: {duration}, using default 5 days")
                            duration = 5
                        
                        # Ensure minimum duration of 1 day
                        if duration < 1:
                            duration = 1
                        
                        # Calculate Start Date
                        if "Start Date" in task:
                            start_date_str = task["Start Date"]
                            calculated_start = self._calculate_date(start_date_str, base_date)
                            
                            # If calculated start is same as base_date and we have previous tasks,
                            # start after the last task
                            if calculated_start == base_date and current_end_date > base_date:
                                task["Start Date"] = current_end_date.strftime("%Y-%m-%d")
                            else:
                                task["Start Date"] = calculated_start
                        else:
                            # No start date specified, use end of previous task
                            task["Start Date"] = current_end_date.strftime("%Y-%m-%d")
                        
                        # Calculate End Date based on Start Date + Duration
                        start_date = datetime.strptime(task["Start Date"], "%Y-%m-%d")
                        end_date = start_date + timedelta(days=duration - 1)  # -1 because start day is included
                        task["End Date"] = end_date.strftime("%Y-%m-%d")
                        
                        # Update current_end_date for next task (add 1 day gap)
                        current_end_date = end_date + timedelta(days=1)
                        
                        self.logger.debug(f"Task '{task.get('Task Name', 'Unknown')}': {task['Start Date']} to {task['End Date']} ({duration} days)")
                
                # Convert back to formatted JSON string for display
                formatted_json = json.dumps(tasks, indent=2, ensure_ascii=False)
                self.logger.info("Successfully processed test planning JSON response")
                return formatted_json
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON from response: {e}")
                # Fallback to text formatting
                return self._format_planning_output(response)
        else:
            self.logger.warning("No JSON array found in response, treating as text")
            # If no JSON found, return formatted text
            return self._format_planning_output(response)
    
    def _calculate_date(self, date_expression, base_date):
        """Calculate actual date from expressions like '{today}+5' or direct dates"""
        import re
        from datetime import timedelta
        
        if not date_expression:
            return base_date.strftime("%Y-%m-%d")
        
        # Check if it's a date offset expression like "{today}+5"
        offset_match = re.search(r'\{today\}\s*\+\s*(\d+)', str(date_expression))
        
        if offset_match:
            days_offset = int(offset_match.group(1))
            calculated_date = base_date + timedelta(days=days_offset)
            return calculated_date.strftime("%Y-%m-%d")
        
        # Check if it's already a proper date format (YYYY-MM-DD)
        date_match = re.match(r'\d{4}-\d{2}-\d{2}', str(date_expression))
        if date_match:
            return str(date_expression)
        
        # Try to parse as integer (days offset without format)
        try:
            days_offset = int(date_expression)
            calculated_date = base_date + timedelta(days=days_offset)
            return calculated_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
        
        # If nothing matches, use base date
        self.logger.warning(f"Could not parse date expression: {date_expression}, using base date")
        return base_date.strftime("%Y-%m-%d") 