"""
test_scenario_generation.py
---------------------------
STLC'nin Test Scenario Generation adımına ait işlemleri yönetir.
"""

import logging
import os
import json
import time
import uuid
import traceback
from utils.model_client import LLMClient
from core.prompt_manager import get_prompts_for_step, save_session_data, get_base_prompt
from core.file_handler import FileHandler
from utils.validation import validate_output_format
from utils.text_splitter import count_tokens

logger = logging.getLogger(__name__)

from services.test_scenario_analytics_service import test_scenario_analytics

logger = logging.getLogger(__name__)

def get_model_specific_prompt(model_name, test_type, test_category, scoring_elements, instruction_elements):
    """
    Tüm modeller için özelleştirilmiş prompt döndürür.
    Kullanıcının seçtiği bilgilere göre custom test scenario generation prompt'u oluşturur.
    """
    # Tüm modeller için aynı optimize edilmiş prompt yapısını kullan
    return create_optimized_prompt(test_type, test_category, scoring_elements, instruction_elements)

def create_optimized_prompt(test_type, test_category, scoring_elements, instruction_elements):
    """
    Tüm LLM modelleri için özelleştirilmiş prompt oluşturur.
    Clear, concise ve structured prompts ile optimum sonuç alır.
    Enhanced JSON structure with comprehensive test scenario fields.
    """
    
    # Model için özelleştirilmiş instruction format
    system_instruction = """You are an expert test scenario generation assistant. Your task is to create comprehensive test scenarios based on the provided requirements. Follow the instructions precisely and generate well-structured test scenarios in the specified JSON format."""
    
    # Scoring elements'i filtrele ve formatla
    selected_scoring = [key for key, value in scoring_elements.items() if value]
    scoring_text = "\n".join([f"• {element}" for element in selected_scoring]) if selected_scoring else "• Standard test coverage criteria"
    
    # Instruction elements'i filtrele ve formatla
    selected_instructions = [key for key, value in instruction_elements.items() if value]
    instruction_text = "\n".join([f"• {element}" for element in selected_instructions]) if selected_instructions else "• Follow standard testing procedures"
    
    # Enhanced prompt structure with comprehensive JSON format
    optimized_prompt = f"""{system_instruction}

## TASK SPECIFICATION
Generate test scenarios for **{test_type}** testing under **{test_category}** category.

## REQUIREMENTS TO CONSIDER
### Scoring Elements:
{scoring_text}

### Testing Instructions:
{instruction_text}

## ENHANCED JSON STRUCTURE
You MUST respond with a valid JSON object following this exact structure:

```json
{{
    "TestScenarios": [
        {{
            "ScenarioID": "TS-001",
            "Title": "Clear, descriptive test scenario title",
            "Description": "Comprehensive description explaining what this scenario tests and its importance",
            "Objective": "Specific testing objective and expected outcome",
            "Category": "{test_category}",
            "Comments": "Additional notes, edge cases, special considerations, or dependencies"
        }}
    ]
}}
```

## COMPREHENSIVE REQUIREMENTS
1. **Generate 10-15 test scenarios** covering different aspects of the system
2. **Each scenario must have unique ScenarioID** (TS-001, TS-002, etc.)
3. **Titles should be specific and descriptive** of the functionality being tested
4. **Descriptions must explain the purpose and scope** of each test scenario
5. **Objectives should be clear, measurable, and testable**
6. **Comments should include relevant notes** about edge cases or special considerations
7. **Include both positive and negative test cases** where appropriate
8. **Ensure ISTQB compliance** and follow industry best practices
9. **Focus on practical, executable scenarios** that provide real testing value

## IMPORTANT GUIDELINES
- Generate comprehensive scenarios that cover different testing aspects
- Ensure each scenario tests unique functionality or conditions
- Include proper validation steps in your test scenarios
- Consider edge cases and error conditions
- Ensure JSON output is valid and properly formatted

Generate the test scenarios now following the exact JSON structure above:"""

    return optimized_prompt

def create_customise_test_prompt(test_type, test_category, base_test_prompt, document_content):
    """
    Create a customized test prompt based on the base test prompt, test type, category, and document content.
    This generates the generatedCustomPrompt that will be combined with scoring and instruction elements.
    Returns structured JSON format with custom_test_prompt key.
    """
      # Return the structured JSON request for custom prompt generation
    customised_prompt = f"""IMPORTANT: You must respond ONLY with a valid JSON object. Do not include any explanatory text, markdown formatting, or additional content outside the JSON.

You are an expert prompt engineer in software test process. Generate a customized prompt to generate test scenario based on the provided context and documents.

**CONTEXT:**
- Test Type: {test_type}
- Test Category: {test_category}
- Base Test Prompt: {base_test_prompt if base_test_prompt else "Use general testing principles"}
- Document Content: {document_content if document_content else "No specific document content provided"}

**ROLE FOR TEST SCENARIO GENERATION (select the most relevant):**
- ISTQB Test Analyst: Apply equivalence partitioning, boundary value analysis, decision tables, and state transition testing to derive positive, negative, and edge-case scenarios with traceability to requirements.
- ISTQB Technical Test Analyst: Design structural and non-functional scenarios covering code paths, concurrency, performance, security, and reliability; define measurable pass/fail criteria.
- ISTQB Test Manager: Establish risk-based test strategy with entry/exit criteria, coverage targets, and resource priorities; monitor KPIs and report to stakeholders.
- ISTQB Test Automation Engineer: Translate scenarios into maintainable, data-driven automation scripts integrated into CI/CD pipelines using appropriate frameworks.
- ISTQB Agile Tester: Write Given-When-Then acceptance scenarios within Scrum/Kanban teams, balancing automation with exploratory testing across sprints.

**REQUIREMENTS FOR THE CUSTOM PROMPT CONTENT:**
1. Analyze the provided documents and extract key insights relevant to the test type and category to generate a custom test prompt.
2. Incorporate the base test prompt as a foundation and enhance it with document-specific context.
3. Identify important elements, requirements, or specifications from the documents.
4. Create context-aware content that reflects the specific domain and requirements found in the documents.
5. Ensure the content is relevant to {test_type} testing in the {test_category} category.
6. Focus on document analysis and context extraction, not on test scenario creation instructions.

**OUTPUT FORMAT - RESPOND ONLY WITH THIS JSON STRUCTURE (NO OTHER TEXT):**
{{"custom_test_prompt": "Your generated custom prompt content here."}}

Start your response immediately with the JSON object:"""

    return customised_prompt

async def generate_prompt(input_data, max_retries=3):
    """
    This function generates a specialized test prompt based on the provided inputs, including a document's type, content, and a selected test name.
    The generated prompt is customized to align with the selected test name and the document's characteristics, ensuring precise and context-specific test scenario generation.
    The resulting prompt is designed to guide the creation of high-quality test scenarios that adhere to ISTQB standards and methodologies.
    The function handles potential connection errors and retries the request up to a maximum. Max retries can be adjusted as needed but the default is 3.
    """
    logger.info(f"[DEBUG] generate_prompt called with input_data: {input_data}")
    
    # Form verilerini al
    test_type = input_data.get("testType", "")
    test_category = input_data.get("testCategory", "")
    model_name = input_data.get("model", "llama3.2:3b")
    test_prompt = input_data.get("testPrompt", "")  # Base test prompt from frontend
    file_contents = input_data.get("fileContents", [])  # Array of file contents from fileProcessMappings
    process_title = input_data.get("process_title", "")  # Get process title directly from user input without fallback
    session_id = input_data.get("session_id")  # Get session_id if available
    api_key = input_data.get("api_key")  # API key extraction
    
    # Diğer modüller gibi base prompt kontrolü ekle
    if not test_prompt:
        base_prompt = get_base_prompt("test_scenario_generation")
        if base_prompt:
            test_prompt = base_prompt
            logger.info("Using base prompt from database for test scenario generation")
        else:
            test_prompt = "Generate comprehensive test scenarios for the provided code/requirements following ISTQB standards"
            logger.warning("No base prompt found in database, using default prompt")
    
    logger.info(f"[DEBUG] Parsed values - test_type: '{test_type}', test_category: '{test_category}', model_name: '{model_name}'")
    logger.info(f"[DEBUG] Received testPrompt length: {len(test_prompt)}, fileContents count: {len(file_contents)}")
      # Combine all file contents into document_content
    document_content = ""
    if file_contents and isinstance(file_contents, list) and len(file_contents) > 0:
        # Handle case where fileContents is a list of strings
        valid_contents = [content for content in file_contents if content and isinstance(content, str)]
        if valid_contents:
            document_content = "\n\n--- FILE SEPARATOR ---\n\n".join(valid_contents)
        else:
            logger.warning("[DEBUG] fileContents list contains no valid string content")
    else:
        logger.warning(f"[DEBUG] No valid fileContents received. Type: {type(file_contents)}, Value: {file_contents}")
    
    logger.info(f"[DEBUG] Combined document_content length: {len(document_content)}")
    
    # Token sayısını hesapla ve modelin context length'ini LM Studio'dan dinamik olarak sorgula
    total_token_count = 0
    # Sabit eşik: küçük modeller için güvenli token limiti (30k)
    QWEN_SWITCH_THRESHOLD = 30_000

    if document_content:
        total_token_count = count_tokens(document_content)
        logger.info(f"[DEBUG] Total token count for file contents (tiktoken): {total_token_count}")

        if total_token_count > QWEN_SWITCH_THRESHOLD and model_name != "qwen2.5-7b-instruct-1m":
            logger.warning(
                f"[DEBUG] Token count ({total_token_count}) exceeds threshold ({QWEN_SWITCH_THRESHOLD}), "
                f"switching from '{model_name}' to qwen2.5-7b-instruct-1m"
            )
            model_name = "qwen2.5-7b-instruct-1m"
        else:
            logger.info(
                f"[DEBUG] Token count ({total_token_count}) within threshold ({QWEN_SWITCH_THRESHOLD}), "
                f"using selected model: {model_name}"
            )

    logger.info(f"Generating prompt for test_type: {test_type}, category: {test_category}, model: {model_name}")
    logger.info(f"[DEBUG] Final model selection: {model_name} (token count: {total_token_count})")

    # Create a customised test prompt based on the provided inputs (without scoring/instruction elements)
    customised_prompt = create_customise_test_prompt(test_type, test_category, test_prompt, document_content)
    
    # Initialize the number of attempts
    attempts = 0

    # Try to generate a specialized test prompt using the LLM model
    while attempts < max_retries:
        # Attempt to connect to the LLM model and generate a specialized test prompt
        try:            # LLM Client'ı başlat ve model mapping yap (diğer servislerdeki gibi)
            model_client = LLMClient(api_key=api_key)
            actual_model = model_client.get_model_identifier(model_name)
            llm_client = LLMClient(model_name=actual_model, api_key=api_key, use_case='test_scenario_generation')
            logger.info(f"Using model: {model_name} -> {actual_model}")
            
            logger.info(f"Calling LLM to generate custom prompt... (Attempt {attempts + 1}/{max_retries})")
            
            # Generate response without JSON mode constraint
            # skip_chunking=True: bağlam bütünlüğü kritik, tüm prompt tek seferde gönderilir
            resp = await llm_client.generate_response(
                customised_prompt,
                temperature=0.3,
                max_tokens=2048,
                skip_chunking=True
            )
            logger.info(f"LLM response received. Length: {len(resp) if resp else 0}")
            logger.debug(f"Raw LLM response: {resp[:500] if resp else 'EMPTY'}")
            
            # Clean up response - remove explanatory text before JSON
            if resp and isinstance(resp, str):
                # Look for JSON pattern in the response
                import re
                json_pattern = r'\{[\s\S]*?"custom_test_prompt"[\s\S]*?\}'
                json_match = re.search(json_pattern, resp)
                
                if json_match:
                    resp = json_match.group(0)
                    logger.info("Extracted JSON from mixed response")
            
            # Try to parse as JSON first
            try:
                # Parse the JSON text into a Python dictionary
                generated_customise_prompt = json.loads(resp)  # JSON string to dict
                
                # Check if the parsed JSON contains the required key
                if "custom_test_prompt" in generated_customise_prompt:
                    generated_custom_prompt = generated_customise_prompt["custom_test_prompt"]
                    logger.info(f"Successfully generated custom prompt from JSON. Preview: {generated_custom_prompt[:200] if generated_custom_prompt else 'EMPTY'}")
                    # Generate or use provided session_id
                    if not session_id:
                        session_id = str(uuid.uuid4())
                        logger.info(f"[DEBUG] Generated new session_id in generate_prompt: {session_id}")
                    
                    return {"status": "success", "generated_custom_prompt": generated_custom_prompt, "session_id": session_id}
                else:
                    raise KeyError("Expected 'custom_test_prompt' key not found in the response.")
            except json.JSONDecodeError:
                # If JSON parsing fails, treat the entire response as the custom prompt
                logger.info("Response is not valid JSON, using entire response as custom prompt")
                if resp and len(resp.strip()) > 0:
                    logger.info(f"Using raw response as custom prompt. Preview: {resp[:200]}")
                    # Generate or use provided session_id
                    if not session_id:
                        session_id = str(uuid.uuid4())
                        logger.info(f"[DEBUG] Generated new session_id in generate_prompt: {session_id}")
                    
                    return {"status": "success", "generated_custom_prompt": resp.strip(), "session_id": session_id}
                else:
                    raise ValueError("Empty or invalid response received from LLM")

        except (json.JSONDecodeError, KeyError) as e:
            # JSON parsing error or missing key - this is now acceptable since we handle raw responses
            attempts += 1
            logger.warning(f"JSON parsing or key error (attempt {attempts}/{max_retries}): {e}")
            # Only retry if we got an empty or invalid response
            if attempts >= max_retries:
                error_msg = f"Error: All attempts failed. Last error: {e}"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg, "generated_custom_prompt": ""}
                
        except (ConnectionError, TimeoutError) as e:
            # Connection or timeout error
            attempts += 1
            logger.warning(f"Connection/timeout error (attempt {attempts}/{max_retries}): {e}")
            # Retry if attempts are within the limit
            if attempts >= max_retries:
                error_msg = f"Error: All attempts failed due to connection issues. Last error: {e}"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg, "generated_custom_prompt": ""}
                
        except ValueError as e:
            # Empty response or validation error
            attempts += 1
            logger.warning(f"Value error (attempt {attempts}/{max_retries}): {e}")
            if attempts >= max_retries:
                error_msg = f"Error: All attempts failed due to empty/invalid responses. Last error: {e}"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg, "generated_custom_prompt": ""}
                
        except Exception as e:
            # Any other unexpected error
            attempts += 1
            logger.error(f"Unexpected error (attempt {attempts}/{max_retries}): {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Retry if attempts are within the limit
            if attempts >= max_retries:
                error_msg = f"Error: All attempts failed due to an unexpected error. Last error: {e}"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg, "generated_custom_prompt": ""}

async def run_step(input_data):
    """
    Test scenario generation işlemini çalıştırır.
    Custom prompt + seçilen dosyalar kullanarak test senaryoları üretir.
    """
    try:
        logger.info(f"[DEBUG] run_step called with input_data keys: {list(input_data.keys())}")
        
        # Form verilerini al
        model_name = input_data.get("model", "")
        files = input_data.get("files", [])
        api_key = input_data.get("api_key")  # API key extraction
        final_prompt = input_data.get("final_prompt", "")
        test_type = input_data.get("test_type", "")
        test_category = input_data.get("test_category", "")        # Gelen session_id'yi kullan veya yeni oluştur
        session_id = input_data.get("session_id")
        # Get process_title directly from user input without fallback
        process_title = input_data.get("process_title", "")
        
        logger.info(f"[DEBUG] Input parameters: model={model_name}, files_count={len(files)}, test_type={test_type}, test_category={test_category}")
        logger.info(f"[DEBUG] Final prompt length: {len(final_prompt) if final_prompt else 0}")
        logger.info(f"[DEBUG] Using session_id: {session_id}")        # Validation
        if not final_prompt:
            # Diğer modüller gibi base prompt kontrolü ekle
            base_prompt = get_base_prompt("test_scenario_generation")
            if base_prompt:
                final_prompt = base_prompt
                logger.info("Using base prompt from database for test scenario generation")
            else:
                raise ValueError("Final prompt is required and no base prompt found in database")
            
        if not model_name:
            raise ValueError("Model name is required")
            
        # Validate required fields
        if not process_title or process_title.strip() == "":
            raise ValueError("Process title is required")
        
        # Combine all file contents into document_content
        file_contents = ""
        processed_files = 0
        file_names = []  # Track filenames for database storage
        
        if files and len(files) > 0:
            for file in files:
                try:
                    # File object'ten content okuma
                    if hasattr(file, 'read'):
                        content = file.read()
                        if isinstance(content, bytes):
                            content = content.decode('utf-8')
                        file_name = getattr(file, 'filename', f'file_{processed_files + 1}')
                    else:
                        # String path ise dosyadan oku
                        with open(file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        file_name = file
                    
                    file_contents += f"\n\n=== FILE: {file_name} ===\n{content}\n"
                    processed_files += 1
                    file_names.append(file_name)  # Add filename to list
                    logger.info(f"[DEBUG] Processed file: {file_name}, content length: {len(content)}")
                    
                except Exception as e:
                    logger.warning(f"[DEBUG] Could not read file {file}: {e}")
                    continue
        else:
            logger.info(f"[DEBUG] No files provided - assuming final_prompt already contains file contents")

        logger.info(f"[DEBUG] Total files processed: {processed_files}, total content length: {len(file_contents)}")        
        # Token sayısını hesapla (tiktoken ile doğru sayım)
        total_token_count = 0
        if file_contents.strip():
            total_token_count = count_tokens(file_contents)
            logger.info(f"[DEBUG] Total token count for file contents (tiktoken): {total_token_count}")

        # Prompt token sayısını da hesapla
        prompt_token_count = count_tokens(final_prompt) if final_prompt else 0
        total_combined_tokens = total_token_count + prompt_token_count

        logger.info(f"[DEBUG] Final prompt tokens: {prompt_token_count}")
        logger.info(f"[DEBUG] Combined total tokens: {total_combined_tokens}")

        # Sabit eşik: küçük modeller için güvenli token limiti (30k)
        QWEN_SWITCH_THRESHOLD = 30_000

        if total_combined_tokens > QWEN_SWITCH_THRESHOLD and model_name != "qwen2.5-7b-instruct-1m":
            logger.warning(
                f"[DEBUG] Combined token count ({total_combined_tokens}) exceeds threshold ({QWEN_SWITCH_THRESHOLD}), "
                f"switching from '{model_name}' to qwen2.5-7b-instruct-1m"
            )
            model_name = "qwen2.5-7b-instruct-1m"
        else:
            logger.info(f"[DEBUG] Combined token count ({total_combined_tokens}) within threshold ({QWEN_SWITCH_THRESHOLD}), using selected model: {model_name}")# Test senaryosu üretme prompt'u oluştur - Sadeleştirilmiş versiyon
        if file_contents.strip():
            # Eğer dosyalar varsa, onları da ekle
            test_scenario_prompt = f"""IMPORTANT: You must respond ONLY with valid JSON. Do not include any explanatory text, markdown formatting, or additional content outside the JSON.

{final_prompt}

## FILE CONTENTS TO ANALYZE:
{file_contents}

## STRICT OUTPUT REQUIREMENTS:
Respond ONLY with a valid JSON object with this EXACT structure (no other text):

{{
  "TestScenarios": [
    {{
      "ScenarioID": "TS_001",
      "Title": "Clear and descriptive test scenario title",
      "Description": "Detailed description of what this test scenario covers and why it's important",
      "Objective": "What this test aims to verify or validate",
      "Category": "{test_category}",
      "Comments": "Additional notes, assumptions, or considerations"
    }}
  ],
  "Summary": {{
    "TotalScenarios": 1,
    "Categories": {{"{test_category}": 1}},
    "Coverage": "Brief description of what aspects are covered by these scenarios"
  }}
}}

Generate between 5-8 comprehensive test scenarios. Start your response immediately with the JSON object."""
        else:
            # Dosya yoksa, final_prompt'u doğrudan kullan
            test_scenario_prompt = f"""IMPORTANT: You must respond ONLY with valid JSON. Do not include any explanatory text, markdown formatting, or additional content outside the JSON.

{final_prompt}

## STRICT OUTPUT REQUIREMENTS:
Respond ONLY with a valid JSON object with this EXACT structure (no other text):

{{
  "TestScenarios": [
    {{
      "ScenarioID": "TS_001",
      "Title": "Clear and descriptive test scenario title",
      "Description": "Detailed description of what this test scenario covers and why it's important",
      "Objective": "What this test aims to verify or validate",
      "Category": "{test_category}",
      "Comments": "Additional notes, assumptions, or considerations"
    }}
  ],
  "Summary": {{
    "TotalScenarios": 1,
    "Categories": {{"{test_category}": 1}},
    "Coverage": "Brief description of what aspects are covered by these scenarios"
  }}
}}

Generate between 5-8 comprehensive test scenarios. Start your response immediately with the JSON object."""
        
        logger.info(f"[DEBUG] Sending request to LLM model: {model_name}")

        # LLM client'ı oluştur ve model mapping yap (diğer servislerdeki gibi)
        model_client = LLMClient(api_key=api_key)
        logger.info(f"Model key: {model_name}")
        actual_model = None
        if model_name:
            actual_model = model_client.get_model_identifier(model_name)
            llm_client = LLMClient(model_name=actual_model, api_key=api_key, use_case='test_scenario_generation')
            logger.info(f"Using model: {model_name} -> {actual_model} for test scenario generation")
        else:
            llm_client = LLMClient(api_key=api_key, use_case='test_scenario_generation')
            logger.info("No model specified, using default model")
        
        logger.info(f"[DEBUG] LLM Client initialized with actual model: {actual_model}")
        logger.info(f"[DEBUG] Prompt being sent to LLM (first 200 chars): {test_scenario_prompt[:200]}")
        
        # JSON formatını zorlamak için response_format kullan (eğer destekleniyorsa)
        # skip_chunking=True: bağlam bütünlüğü kritik, tüm prompt tek seferde gönderilir
        try:
            response = await llm_client.generate_response(
                test_scenario_prompt,
                temperature=0.2,  # Daha deterministic output için düşük temperature
                max_tokens=4000,
                response_format={"type": "json_object"},  # JSON formatını zorla
                skip_chunking=True
            )
        except Exception as json_format_error:
            logger.warning(f"[DEBUG] JSON format not supported, falling back to normal mode: {json_format_error}")
            # Fallback: Normal mode ile dene
            response = await llm_client.generate_response(
                test_scenario_prompt,
                temperature=0.2,
                max_tokens=4000,
                skip_chunking=True
            )
        
        if not response:
            raise ValueError("No response from LLM")

        logger.info(f"[DEBUG] Received LLM response length: {len(response)}")        # JSON response'u parse et - İyileştirilmiş versiyon
        try:
            import re
            import json
            
            logger.info(f"[DEBUG] Raw LLM response (first 500 chars): {response[:500]}")
            
            # 1. İlk olarak temiz JSON arayalım
            cleaned_response = response.strip()
            
            # 2. Markdown kod bloklarını temizle
            if '```json' in cleaned_response:
                # ```json ile başlayan blokları bul
                json_blocks = re.findall(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                if json_blocks:
                    cleaned_response = json_blocks[0].strip()
                    logger.info(f"[DEBUG] Extracted JSON from markdown block")
            elif '```' in cleaned_response:
                # Genel ``` bloklarını temizle
                cleaned_response = re.sub(r'```.*?```', '', cleaned_response, flags=re.DOTALL).strip()
                
            # 3. Açıklayıcı metinleri temizle
            lines = cleaned_response.split('\n')
            json_started = False
            json_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('{') or json_started:
                    json_started = True
                    json_lines.append(line)
                    if line.endswith('}') and json_lines.count('{') <= json_lines.count('}'):
                        break
            
            if json_lines:
                cleaned_response = '\n'.join(json_lines)
                logger.info(f"[DEBUG] Extracted JSON lines, result length: {len(cleaned_response)}")
            
            # 4. JSON parsing'i dene
            try:
                test_scenarios = json.loads(cleaned_response)
                logger.info(f"[DEBUG] Successfully parsed cleaned JSON")
                
            except json.JSONDecodeError:
                # 5. Regex ile JSON pattern arama (geliştirilmiş)
                json_pattern = r'\{[\s\S]*?"TestScenarios"[\s\S]*?\}'
                json_matches = re.finditer(json_pattern, response)
                
                best_match = None
                for match in json_matches:
                    candidate = match.group(0)
                    # Brace balansını kontrol et
                    open_braces = candidate.count('{')
                    close_braces = candidate.count('}')
                    
                    if open_braces == close_braces:
                        best_match = candidate
                        break
                    elif open_braces > close_braces:
                        # Eksik closing brace'leri ekle
                        missing = open_braces - close_braces
                        candidate += '}' * missing
                        best_match = candidate
                        break
                
                if best_match:
                    logger.info(f"[DEBUG] Found valid JSON pattern with regex")
                    test_scenarios = json.loads(best_match)
                else:
                    # 6. Son çare: Manuel JSON oluşturma
                    logger.warning(f"[DEBUG] Could not parse JSON, attempting manual extraction")
                    raise json.JSONDecodeError("Could not parse response as JSON", response, 0)
            
            # Validate structure — auto-wrap if top-level is a list
            if "TestScenarios" not in test_scenarios:
                # Model may have returned the array directly or used a different key
                # Try common alternative keys first
                alt_keys = ["testScenarios", "test_scenarios", "scenarios", "Scenarios",
                            "Tests", "tests", "TestCases", "items"]
                found_key = None
                for alt in alt_keys:
                    if alt in test_scenarios and isinstance(test_scenarios[alt], list):
                        found_key = alt
                        break

                if found_key:
                    test_scenarios = {"TestScenarios": test_scenarios[found_key]}
                    logger.warning(f"[DEBUG] Remapped key '{found_key}' -> 'TestScenarios'")
                elif isinstance(test_scenarios, list):
                    # Top-level is already a list
                    test_scenarios = {"TestScenarios": test_scenarios}
                    logger.warning("[DEBUG] Top-level was list, wrapped in TestScenarios")
                else:
                    # Last resort: create minimal scenarios from the raw text
                    logger.warning("[DEBUG] Could not find TestScenarios key — building fallback scenario")
                    test_scenarios = {
                        "TestScenarios": [{
                            "ScenarioID": "TS-001",
                            "Title": "General Functionality Test",
                            "Category": test_category or "Functional",
                            "Priority": "High",
                            "ObjectiveDescription": "Verify general system functionality based on provided requirements",
                            "Preconditions": "System is initialized and running",
                            "Steps": "1. Setup system\n2. Execute primary workflow\n3. Verify output",
                            "ExpectedResults": "System behaves as specified in requirements",
                            "Comments": "Auto-generated fallback — LLM response did not contain structured JSON"
                        }]
                    }

            scenarios = test_scenarios["TestScenarios"]
            if not isinstance(scenarios, list):
                raise ValueError("TestScenarios must be a list")
            
            logger.info(f"[DEBUG] Validation passed - found {len(scenarios)} scenarios")
              # Add summary if not present
            if "Summary" not in test_scenarios:
                categories = {}
                for scenario in scenarios:
                    cat = scenario.get("Category", "Unknown")
                    categories[cat] = categories.get(cat, 0) + 1
                
                test_scenarios["Summary"] = {
                    "TotalScenarios": len(scenarios),
                    "Categories": categories,
                    "Coverage": f"Generated {len(scenarios)} test scenarios covering various aspects of the provided files"
                }
                logger.info(f"[DEBUG] Added summary with {len(scenarios)} scenarios")
            
            logger.info(f"[DEBUG] Successfully generated {len(scenarios)} test scenarios")            # Save session data to database for tracking
            # Use passed session ID or generate a new one if not provided
            if not session_id:                # Import UUID module for generating unique session IDs
                import uuid
                session_id = str(uuid.uuid4())  # Generate a UUID format session ID
                logger.info(f"[DEBUG] No session_id provided, generated new UUID: {session_id}")
            
            try:                # Get model name from metadata (or fallback to input model)
                actual_model_used = actual_model or model_name
                
                session_data = {
                    "session_id": session_id,
                    "output": {
                        "test_scenarios": test_scenarios,
                        "metadata": {
                            "model_used": actual_model_used,
                            "files_processed": processed_files,
                            "file_names": file_names,  # Add filenames to metadata
                            "total_scenarios": len(scenarios),
                            "test_type": test_type,
                            "test_category": test_category,
                            "generation_timestamp": time.time()
                        }
                    },
                    "edited_prompt": False,  # Could be enhanced to track if prompt was modified
                    "used_prompt": final_prompt[:1000] if final_prompt else "",  # Truncate for storage
                    "used_model": actual_model_used,  # Use the same model name from metadata
                    "process_title": process_title,  # Save process title at the same level as edited_prompt and used_model
                    "selected_category": test_category,  # Add test category for optimization service
                    "selected_test_type": test_type  # Add test type for optimization service
                }
                save_session_data(session_data, process_type="test_scenario_generation")
                logger.info(f"[DEBUG] Session data saved for test scenario generation: {session_id}")
            except Exception as save_error:
                logger.error(f"[DEBUG] Failed to save session data: {save_error}")
                # Continue without failing the main process
            
            # Enhanced Analytics Tracking
            if test_scenario_analytics:
                try:
                    # Collect analytics data
                    test_metadata = {
                        "test_type": test_type,
                        "test_category": test_category,
                        "scoring_elements": input_data.get("scoring_elements", []),
                        "instruction_elements": input_data.get("instruction_elements", [])
                    }
                    
                    generation_result = {
                        "test_scenarios": test_scenarios,
                        "total_scenarios": len(scenarios),
                        "extraction_method": "json_parse"  # Could be enhanced to track actual method
                    }
                    
                    processing_stats = {
                        "model_used": model_name,
                        "processing_time": time.time() - int(session_id.split('_')[-1]) if 'test_scenario_' in session_id else 0,
                        "token_usage": {
                            "input_tokens": count_tokens(final_prompt) if final_prompt else 0,
                            "output_tokens": count_tokens(str(test_scenarios)) if test_scenarios else 0
                        }
                    }
                    
                    file_analysis = {
                        "files_processed": processed_files,
                        "total_file_size": len(file_contents) if file_contents else 0,
                        "context_included": bool(file_contents and file_contents.strip())
                    }
                    
                    prompt_metadata = {
                        "prompt_generation_session_id": input_data.get("prompt_session_id", ""),
                        "base_prompt_modified": False,
                        "custom_prompt_generated": True,
                        "final_prompt_length": len(final_prompt) if final_prompt else 0
                    }
                    
                    # Track comprehensive analytics
                    test_scenario_analytics.track_generation_session(
                        session_id=session_id,
                        test_metadata=test_metadata,
                        generation_result=generation_result,
                        processing_stats=processing_stats,
                        file_analysis=file_analysis,
                        prompt_metadata=prompt_metadata
                    )
                    logger.info(f"[DEBUG] Comprehensive analytics tracked for session: {session_id}")
                    
                except Exception as analytics_error:
                    logger.error(f"[DEBUG] Failed to track analytics: {analytics_error}")
                    # Continue without failing the main process
            
            return {
                "status": "success",
                "test_scenarios": test_scenarios,
                "metadata": {
                    "model_used": model_name,
                    "files_processed": processed_files,
                    "total_scenarios": len(scenarios),
                    "test_type": test_type,
                    "test_category": test_category,
                    "session_id": session_id
                }
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[DEBUG] JSON parsing error: {e}")
            logger.error(f"[DEBUG] Response that failed to parse: {response[:1000]}")
              # Create a fallback response with improved scenario extraction
            try:
                logger.info(f"[DEBUG] Attempting improved fallback scenario extraction")
                
                # Improved fallback: Try to extract structured information from the response
                fallback_scenarios = []
                
                # Split response into lines and look for pattern indicators
                lines = response.split('\n')
                current_scenario = None
                scenario_count = 0
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Look for scenario indicators
                    if any(indicator in line.lower() for indicator in [
                        'scenarioid', 'scenario_id', 'ts_', 'test_scenario', 
                        '"title":', 'verify ', 'test ', 'validate '
                    ]):
                        
                        # If we have a current scenario, save it
                        if current_scenario and current_scenario.get('Title'):
                            if 'ScenarioID' not in current_scenario:
                                current_scenario['ScenarioID'] = f"Process_Test_Scenario_{scenario_count + 1}"
                            fallback_scenarios.append(current_scenario)
                            scenario_count += 1
                        
                        # Start new scenario
                        current_scenario = {
                            'Category': test_category or 'Functional',
                            'Comments': 'Generated from improved fallback extraction'
                        }
                        
                        # Extract title from line
                        if '"title":' in line.lower():
                            title_match = re.search(r'"title":\s*"([^"]+)"', line, re.IGNORECASE)
                            if title_match:
                                current_scenario['Title'] = title_match.group(1)
                        elif any(word in line.lower() for word in ['verify', 'test', 'validate']):
                            current_scenario['Title'] = line.replace('"', '').replace(',', '').strip()
                    
                    # Look for other fields if we have a current scenario
                    elif current_scenario:
                        if '"description":' in line.lower():
                            desc_match = re.search(r'"description":\s*"([^"]+)"', line, re.IGNORECASE)
                            if desc_match:
                                current_scenario['Description'] = desc_match.group(1)
                        elif '"objective":' in line.lower():
                            obj_match = re.search(r'"objective":\s*"([^"]+)"', line, re.IGNORECASE)
                            if obj_match:
                                current_scenario['Objective'] = obj_match.group(1)
                        elif 'description' in current_scenario.get('Description', '') and len(current_scenario['Description']) < 200:
                            # Continue building description
                            current_scenario['Description'] += ' ' + line.replace('"', '').replace(',', '').strip()
                
                # Add last scenario
                if current_scenario and current_scenario.get('Title'):
                    if 'ScenarioID' not in current_scenario:
                        current_scenario['ScenarioID'] = f"Process_Test_Scenario_{scenario_count + 1}"
                    fallback_scenarios.append(current_scenario)
                
                # If we still don't have good scenarios, create basic ones from content
                if len(fallback_scenarios) < 3:
                    logger.info(f"[DEBUG] Creating basic scenarios from response content")
                    basic_scenarios = [
                        {
                            'ScenarioID': 'Process_Test_Scenario_1',
                            'Title': 'Basic Functional Test',
                            'Description': 'This scenario tests the basic functionality of the system based on the provided requirements and documentation.',
                            'Objective': 'Verify that core system functions work as expected',
                            'Category': test_category or 'Functional',
                            'Comments': 'Generated from basic fallback extraction'
                        },
                        {
                            'ScenarioID': 'Process_Test_Scenario_2',
                            'Title': 'Input Validation Test',
                            'Description': 'This scenario tests input validation and error handling mechanisms of the system.',
                            'Objective': 'Verify that the system properly validates inputs and handles errors',
                            'Category': test_category or 'Functional',
                            'Comments': 'Generated from basic fallback extraction'
                        },
                        {
                            'ScenarioID': 'Process_Test_Scenario_3',
                            'Title': 'End-to-End Workflow Test',
                            'Description': 'This scenario tests the complete workflow from start to finish to ensure all components work together.',
                            'Objective': 'Verify that the complete system workflow functions correctly',
                            'Category': test_category or 'Functional',
                            'Comments': 'Generated from basic fallback extraction'
                        }
                    ]
                    fallback_scenarios.extend(basic_scenarios)
                
                if fallback_scenarios:
                    logger.info(f"[DEBUG] Fallback extraction found {len(fallback_scenarios)} scenarios")
                    
                    fallback_response = {
                        "TestScenarios": fallback_scenarios,
                        "Summary": {
                            "TotalScenarios": len(fallback_scenarios),
                            "Categories": {test_category or 'Functional': len(fallback_scenarios)},
                            "Coverage": f"Fallback extraction - {len(fallback_scenarios)} scenarios"
                        }
                    }
                    
                    return {
                        "status": "success",
                        "test_scenarios": fallback_response,
                        "metadata": {
                            "model_used": model_name,
                            "files_processed": processed_files,
                            "total_scenarios": len(fallback_scenarios),
                            "test_type": test_type,
                            "test_category": test_category,
                            "extraction_method": "fallback"
                        }
                    }
                
            except Exception as fallback_error:
                logger.error(f"[DEBUG] Fallback extraction also failed: {fallback_error}")
            
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    except Exception as e:
        logger.error(f"[DEBUG] Error in test scenario generation run_step: {str(e)}")
        logger.error(f"[DEBUG] Error type: {type(e).__name__}")
        import traceback
        logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": str(e),
            "test_scenarios": None
        }

def get_llm_instance(model_name, temperature=0.7):
    """
    Model adına göre uygun LLM instance'ını döndürür.
    """
    try:
        # LLM Client kullanarak instance oluştur
        llm_client = LLMClient()
        actual_model = llm_client.get_model_identifier(model_name)
        
        logger.info(f"Creating LLM instance for model: {model_name} -> {actual_model}")
        
        # Model özelliklerini ayarla
        llm_client.model_name = actual_model
        llm_client.original_key = model_name
        llm_client.temperature = temperature
        
        return llm_client
        
    except Exception as e:
        logger.error(f"Error creating LLM instance for {model_name}: {str(e)}")
        raise ValueError(f"Failed to initialize LLM model: {model_name}")
