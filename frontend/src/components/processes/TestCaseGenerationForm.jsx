import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import PropTypes from 'prop-types';
import { useSelector } from 'react-redux';
import { useModels } from '../../hooks/useModels';

export default function TestCaseGenerationForm({ 
  onRun, 
  onTestCaseGeneration, // New prop for test case generation
  process, 
  sessionId, 
  onFinalPromptChange, 
  aiModels = [], 
  onAIModelUpdate,
  managedFiles = [],
  fileProcessMappings = {}
}) {
  // Redux API key - Google için
  const apiKey = useSelector((state) => state.apiKey.apiKeys.google);
  
  console.log('[TestCaseGeneration] API Key from Redux:', apiKey ? 'SET' : 'NOT SET');
  
  const [availableProcessTitles, setAvailableProcessTitles] = useState([]);
  const [selectedProcessTitle, setSelectedProcessTitle] = useState('');
  const [selectedProcessData, setSelectedProcessData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processPrompt, setProcessPrompt] = useState(''); // State to store the loaded prompt
  const [createPrompts, setCreatePrompts] = useState({}); // State to store available create prompts
  const [selectedCreatePrompts, setSelectedCreatePrompts] = useState([]); // State to store selected create prompts
  const [finalPrompt, setFinalPrompt] = useState(''); // State to store the final combined prompt
    // New states for test scenarios and AI model
  const [selectedTestScenarios, setSelectedTestScenarios] = useState([]);
  const [selectedAIModel, setSelectedAIModel] = useState('llama3.2:3b');
  
  // States for test case generation
  const [isGenerating, setIsGenerating] = useState(false);
  const [testCaseResults, setTestCaseResults] = useState([]);
  const [generationSummary, setGenerationSummary] = useState(null);

  // Token counting utility function (simple word-based approximation)
  const countTokens = (text) => {
    if (!text || typeof text !== 'string') return 0;
    return text.split(/\s+/).filter(word => word.length > 0).length;
  };

  // Calculate total tokens from selected files
  const calculateTotalTokens = () => {
    const selectedFiles = managedFiles.filter(file => 
      fileProcessMappings[file.id]?.includes(process.id)
    );
    
    let totalTokens = 0;
    selectedFiles.forEach(file => {
      if (file.content && typeof file.content === 'string') {
        totalTokens += countTokens(file.content);
      }
    });
    
    return totalTokens;
  };

  const totalTokens = calculateTotalTokens();
  const TOKEN_LIMIT = 4000;
  const exceedsLimit = totalTokens > TOKEN_LIMIT;

  // Model mapping for test case generation
  const modelMapping = {
    "codegeex4:9b": "codegeex4-all-9b",
    "codellama:7b": "codellama-7b-instruct",
    "deepseek-coder:6.7b": "deepseek-coder-6.7b-instruct",
    "gemma2:2b": "gemma-2-2b-it",
    "gemma3:4b": "gemma-3-4b-it",
    "llama3.2:3b": "llama-3.2-3b-instruct",
    "qwen2.5:7b": "qwen2.5-7b-instruct-1m",
    "qwen2.5-7b-instruct-1m": "qwen2.5-7b-instruct-1m",
    "qwen2.5-coder:3b": "qwen2.5-coder-3b-instruct",
    "stable-code:3b": "stable-code-instruct-3b",
    "starcoder2:7b": "starcoder2-7b"
  };
  // Merkezi model hook'unu kullan
  const { 
    models: availableModels, 
    loading: modelsLoading, 
    error: modelsError,
    getModelDescriptions
  } = useModels({ 
    autoFetch: true,
    includeDescriptions: true 
  });

  // Load available process titles on component mount
  useEffect(() => {
    // First test database connection, then load process titles
    testConnection();
  }, []);

  const testConnection = async () => {
    try {
      console.log('[TestCaseGeneration] Testing database connection...');
      
      const response = await fetch('/api/processes/test-scenario-generation/test-connection');
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('[TestCaseGeneration] Connection test failed:', errorText);
        throw new Error(`Connection test failed: ${response.status} - ${errorText}`);
      }
      
      const result = await response.json();
      console.log('[TestCaseGeneration] Connection test result:', result);
      
      if (result.status === 'success') {
        console.log('[TestCaseGeneration] Database connection successful, loading process titles...');
        loadProcessTitles();
      } else {
        throw new Error(result.message || 'Connection test failed');
      }
      
    } catch (error) {
      console.error('[TestCaseGeneration] Connection test error:', error);
      setError(`Database connection failed: ${error.message}`);
      toast.error(`Database connection failed: ${error.message}`);
    }
  };  // Load process data when a process title is selected
  useEffect(() => {
    if (selectedProcessTitle) {
      const selectedProcess = availableProcessTitles.find(p => p.process_title === selectedProcessTitle);
      if (selectedProcess) {
        loadProcessData(selectedProcess.session_id);
      }
    }
  }, [selectedProcessTitle, availableProcessTitles]);
  const loadProcessTitles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('[TestCaseGeneration] Fetching process titles from:', '/api/processes/test-scenario-generation/process-titles');
      
      const response = await fetch('/api/processes/test-scenario-generation/process-titles');
      
      console.log('[TestCaseGeneration] Response status:', response.status);
      console.log('[TestCaseGeneration] Response ok:', response.ok);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('[TestCaseGeneration] Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }
      
      const result = await response.json();
      console.log('[TestCaseGeneration] API Response:', result);
      
      if (result.status === 'success') {
        setAvailableProcessTitles(result.process_titles || []);
        console.log('[TestCaseGeneration] Loaded process titles:', result.process_titles);
      } else {
        throw new Error(result.message || 'Failed to load process titles');
      }
      
    } catch (error) {
      console.error('[TestCaseGeneration] Error loading process titles:', error);
      setError(`Failed to load available test scenario processes: ${error.message}`);
      toast.error(`Failed to load available test scenario processes: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };
  const loadProcessData = async (sessionId) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`/api/processes/test-scenario-generation/process-data/${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();        if (result.status === 'success') {
        setSelectedProcessData(result.data);
        setSelectedTestScenarios([]); // Reset selected test scenarios
        console.log('[TestCaseGeneration] Loaded process data:', result.data);
        
        // Load test scenarios from MongoDB output structure
        await loadTestScenarios(sessionId);
        
        // Load the prompt for the test type
        if (result.data.test_type) {
          loadProcessPrompt(result.data.test_type);
        }
      } else {
        throw new Error(result.message || 'Failed to load process data');
      }
      
    } catch (error) {
      console.error('[TestCaseGeneration] Error loading process data:', error);
      setError('Failed to load test scenario data');
      toast.error('Failed to load test scenario data');
    } finally {
      setIsLoading(false);
    }
  };
  const loadProcessPrompt = async (testType) => {
    try {
      console.log('[TestCaseGeneration] Loading prompt for test type:', testType);
      
      // Use the correct endpoint for test case generation prompt
      const response = await fetch(`/api/prompts/test-case-generation`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
        if (result.status === 'success') {        
        setProcessPrompt(result.prompt_text); // Changed from result.prompt to result.prompt_text
        // Note: create_prompts are not available in this endpoint, so we set empty object
        setCreatePrompts({});
        setSelectedCreatePrompts([]); // Reset selected prompts
          // Create initial final prompt with JSON structure (enhanced for Test Case Generation)
        const jsonStructure = `

## JSON OUTPUT STRUCTURE:

You MUST respond with a valid JSON object in this exact structure:

\`\`\`json
{
    "TestCases": [
          {
              "ScenarioID": "<Dynamic Source Scenario ID>",
              "TestCaseID": "<Dynamic Test Case ID>",
              "Title": "<Scenario Title>",
              "Description": "<Detailed scenario description at least 3 sentences. This is the most important part of the test scenario!>",
              "Objective": "<Objective or goal of the scenario>",
              "Category": "<Category of the test case>",
              "Comments": "<Any inconsistency or additional notes>"
          }
        ],
    "Summary": {
        "TotalTestCases": 1,
        "Coverage": "<Brief description of test case coverage>"
    }
}
\`\`\`

## Guidelines for JSON Structure:
- Ensure the ScenarioID matches the source test scenario
- TestCaseID must be unique within the scope of its ScenarioID
- Generate 7-8 comprehensive test cases covering different aspects
- Include both positive and negative test cases where appropriate
- Each test case should be executable and practical

## Example JSON output:
    {
        "ScenarioID": "Scenario_1",
        "TestCaseID": "TestCase_1",
        "Title": "Verify Login Functionality",
        "Description": "Test the login functionality to ensure users can log in with valid credentials and receive appropriate error messages for invalid inputs. Additionally, ensure session management operates correctly post-login.",
        "Objective": "Validate user authentication mechanism.",
        "Category": "Functional Tests",
        "Comments": "Ensure edge cases for invalid inputs are covered."
    }
`;
        
        const initialFinalPrompt = result.prompt_text + jsonStructure; // Changed from result.prompt
        setFinalPrompt(initialFinalPrompt); // Initialize final prompt with main prompt + JSON structure
        
        // Notify parent about initial final prompt
        if (onFinalPromptChange && typeof onFinalPromptChange === 'function') {
          onFinalPromptChange(initialFinalPrompt);
        }
        
        console.log('[TestCaseGeneration] Loaded prompt:', result.prompt_text.substring(0, 100) + '...'); // Changed from result.prompt
        console.log('[TestCaseGeneration] Create prompts not available in this endpoint');
      }else {
        console.warn('[TestCaseGeneration] No prompt found in response');
        setProcessPrompt('Prompt bulunamadı');
        setCreatePrompts({});
        setSelectedCreatePrompts([]);
        setFinalPrompt('');
      }
      
    } catch (error) {
      console.error('[TestCaseGeneration] Error loading process prompt:', error);
      setProcessPrompt('Prompt yüklenirken hata oluştu');
      setCreatePrompts({});
      setSelectedCreatePrompts([]);
      setFinalPrompt('');
    }
  };
  // New function to load test scenarios from MongoDB output structure
  const loadTestScenarios = async (sessionId) => {
    try {
      console.log('[TestCaseGeneration] Loading test scenarios from MongoDB output for session:', sessionId);
      
      const response = await fetch(`/api/processes/test-scenario-generation/test-scenarios/${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('[TestCaseGeneration] Test scenarios response:', result);
      
      if (result.status === 'success' && result.test_scenarios) {
        // Update the selected process data with the fetched test scenarios
        setSelectedProcessData(prevData => ({
          ...prevData,
          test_scenarios: result.test_scenarios
        }));
        console.log('[TestCaseGeneration] Loaded test scenarios from output:', result.test_scenarios);
      } else {
        console.warn('[TestCaseGeneration] No test scenarios found in output for session:', sessionId);
        console.warn('[TestCaseGeneration] Response:', result);
        // Keep existing data structure but with empty scenarios
        setSelectedProcessData(prevData => ({
          ...prevData,
          test_scenarios: []
        }));
      }
      
    } catch (error) {
      console.error('[TestCaseGeneration] Error loading test scenarios from output:', error);
      // Don't show error toast here as it's not critical - keep existing process data
      setSelectedProcessData(prevData => ({
        ...prevData,
        test_scenarios: []
      }));
    }
  };

  // Handle checkbox selection for create prompts
  const handleCreatePromptSelection = (promptKey, isSelected) => {
    let newSelectedPrompts;
    if (isSelected) {
      newSelectedPrompts = [...selectedCreatePrompts, promptKey];
    } else {
      newSelectedPrompts = selectedCreatePrompts.filter(key => key !== promptKey);
    }
    
    setSelectedCreatePrompts(newSelectedPrompts);
    updateFinalPrompt(newSelectedPrompts);
  };  // Update final prompt by combining main prompt with selected create prompts (Enhanced version)
  const updateFinalPrompt = (selectedPrompts) => {
    let combinedPrompt = processPrompt;
    
    if (selectedPrompts.length > 0) {
      const selectedPromptTexts = selectedPrompts.map(key => {
        const promptTitle = key;
        const promptText = createPrompts[key] || '';
        return `\n\n**${promptTitle}:**\n${promptText}`;
      });
      
      combinedPrompt += '\n\n--- Additional Specific Test Case Requirements ---' + selectedPromptTexts.join('');
    }
    
    // Enhanced JSON structure for Test Case Generation (similar to Test Scenario Generation)
    const jsonStructure = `

## ENHANCED JSON OUTPUT STRUCTURE:

You MUST respond with a valid JSON object in this exact structure:

\`\`\`json
{
    "TestCases": [
        {
            "ScenarioID": "<Dynamic Source Scenario ID>",
            "TestCaseID": "<Dynamic Test Case ID>",
            "Title": "<Clear and descriptive test case title>",
            "Description": "<Detailed test case description explaining what is being tested and why it's important>",
            "Objective": "<Specific objective of this test case>",
            "Comments": "<Additional notes, assumptions, or considerations>"
        }
    ],
    "Summary": {
        "TotalTestCases": 1,
        "Coverage": "<Brief description of test case coverage>"
    }
}
\`\`\`

## Guidelines for Enhanced Test Case Generation:
- Generate 7-8 comprehensive test cases covering different aspects
- Ensure each TestCaseID is unique within the scenario scope
- Include both positive and negative test cases where appropriate
- Make prerequisites realistic and achievable in a testing environment
- Write clear, actionable test steps that any tester can follow
- Include proper validation steps and expected results
- Consider edge cases and error conditions
- Ensure JSON output is valid and properly formatted

## Example Enhanced JSON output:
\`\`\`json
{
    "TestCases": [
        {
            "ScenarioID": "TS_001",
            "TestCaseID": "TC_001_001",
            "Title": "Verify Login with Valid Credentials",
            "Description": "Test that a user can successfully log in with valid username and password, ensuring proper authentication and session management.",
            "Objective": "Validate user authentication mechanism with correct credentials",
            "Comments": "Ensure session timeout is properly configured"
        }
    ],
    "Summary": {
        "TotalTestCases": 1,
        "Coverage": "Authentication functionality validation"
    }
}
\`\`\`

Generate comprehensive test cases now following the exact JSON structure above.`;
    
    combinedPrompt += jsonStructure;
    
    setFinalPrompt(combinedPrompt);
    
    // Notify parent component about the final prompt change
    if (onFinalPromptChange && typeof onFinalPromptChange === 'function') {
      onFinalPromptChange(combinedPrompt);
    }
  };
  // Handle AI model selection
  const handleAIModelChange = (selectedModel) => {
    setSelectedAIModel(selectedModel);
    // Use the mapped model name when communicating with backend
    const mappedModel = modelMapping[selectedModel] || selectedModel;
    if (onAIModelUpdate) {
      onAIModelUpdate(process?.id || 'test-case-generation', mappedModel);
    }
  };

  // Handle individual test scenario selection
  const handleTestScenarioSelection = (scenarioId, isSelected) => {
    let newSelectedScenarios;
    if (isSelected) {
      newSelectedScenarios = [...selectedTestScenarios, scenarioId];
    } else {
      newSelectedScenarios = selectedTestScenarios.filter(id => id !== scenarioId);
    }
    setSelectedTestScenarios(newSelectedScenarios);
  };

  // Handle Select All test scenarios
  const handleSelectAllTestScenarios = (isSelectAll) => {
    if (isSelectAll && selectedProcessData?.test_scenarios) {
      const allScenarioIds = selectedProcessData.test_scenarios.map(scenario => scenario.scenario_id);
      setSelectedTestScenarios(allScenarioIds);
    } else {
      setSelectedTestScenarios([]);
    }
  };
  // Handle process title change to reset all selections
  const handleProcessTitleChange = (processTitle) => {
    setSelectedProcessTitle(processTitle);
    setSelectedProcessData(null);
    setSelectedTestScenarios([]);
    setSelectedCreatePrompts([]);
    setProcessPrompt('');
    setCreatePrompts({});
    setFinalPrompt('');
    
    // Let the useEffect handle the actual data loading with proper session_id
    // Don't call loadProcessData directly here
  };

  // Generate test cases for selected scenarios
  const generateTestCases = async () => {
    if (selectedTestScenarios.length === 0) {
      toast.error('Please select at least one test scenario');
      return;
    }

    if (!processPrompt) {
      toast.error('Process prompt is required');
      return;
    }

    setIsGenerating(true);
    setTestCaseResults([]);
    setGenerationSummary(null);

    try {      console.log('[TestCaseGeneration] Starting test case generation...');
      
      // Get selected scenarios data
      const selectedScenariosData = selectedProcessData.test_scenarios.filter(
        scenario => selectedTestScenarios.includes(scenario.scenario_id || scenario.ScenarioID)
      );

      // Get selected files content (from File Management)
      const selectedFiles = managedFiles
        .filter(file => fileProcessMappings[file.id]?.includes('test-case-generation'))
        .map(file => ({
          name: file.name,
          content: file.content || '',
          type: file.type
        }));

      console.log('[TestCaseGeneration] Selected scenarios:', selectedScenariosData.length);
      console.log('[TestCaseGeneration] Selected files:', selectedFiles.length);
      console.log('[TestCaseGeneration] AI Model:', selectedAIModel);

      const requestData = {
        selected_scenarios: selectedScenariosData,
        process_prompt: finalPrompt, // Use the combined prompt with JSON structure
        selected_files: selectedFiles,
        ai_model: modelMapping[selectedAIModel] || selectedAIModel,
        session_id: sessionId,
        selected_process_title: selectedProcessData?.process_title || '',  // Seçilen process title'ı ekle (1. fonksiyon)
        api_key: apiKey  // API key eklendi
      };

      const response = await fetch('/api/processes/test-scenario-generation/generate-test-cases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('[TestCaseGeneration] Test cases generated:', result);

      if (result.status === 'success') {
        setTestCaseResults(result.test_case_results || []);
        setGenerationSummary(result.summary || {});
        toast.success(`Generated test cases for ${result.summary?.successful_scenarios || 0} scenarios`);
      } else {
        throw new Error(result.message || 'Failed to generate test cases');
      }

    } catch (error) {
      console.error('[TestCaseGeneration] Error generating test cases:', error);
      toast.error(`Failed to generate test cases: ${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // Handle run process - integrate test case generation
  const handleRunProcess = async () => {
    // First validate test case generation requirements
    if (selectedTestScenarios.length === 0) {
      toast.error('Please select at least one test scenario before running the process');
      return;
    }

    if (!processPrompt) {
      toast.error('Process prompt is required');
      return;
    }

    if (!finalPrompt) {
      toast.error('Final prompt is required');
      return;
    }

    // Start test case generation
    setIsGenerating(true);
    setTestCaseResults([]);
    setGenerationSummary(null);

    try {      console.log('[TestCaseGeneration] Starting test case generation via Run Process...');
      
      // Get selected scenarios data
      const selectedScenariosData = selectedProcessData.test_scenarios.filter(
        scenario => selectedTestScenarios.includes(scenario.scenario_id || scenario.ScenarioID)
      );

      // Get selected files content (from File Management)
      const selectedFiles = managedFiles
        .filter(file => fileProcessMappings[file.id]?.includes('test-case-generation'))
        .map(file => ({
          name: file.name,
          content: file.content || '',
          type: file.type
        }));

      console.log('[TestCaseGeneration] Selected scenarios:', selectedScenariosData.length);
      console.log('[TestCaseGeneration] Selected files:', selectedFiles.length);
      console.log('[TestCaseGeneration] AI Model:', selectedAIModel);
      console.log('[TestCaseGeneration] API Key:', apiKey ? 'SET' : 'NOT SET');

      const requestData = {
        selected_scenarios: selectedScenariosData,
        process_prompt: finalPrompt, // Use the combined prompt with JSON structure
        selected_files: selectedFiles,
        ai_model: modelMapping[selectedAIModel] || selectedAIModel,
        session_id: sessionId,
        selected_process_title: selectedProcessData?.process_title || '',  // Seçilen process title'ı ekle (2. fonksiyon)
        api_key: apiKey  // API key eklendi
      };

      console.log('[TestCaseGeneration] Request data:', {
        ...requestData,
        api_key: apiKey ? 'SET' : 'NOT SET',
        selected_scenarios: `[${selectedScenariosData.length} scenarios]`,
        process_prompt: `[${finalPrompt.length} chars]`
      });

      // Call test case generation API (no timeout - let backend handle long operations)
      const response = await fetch('/api/processes/test-scenario-generation/generate-test-cases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('[TestCaseGeneration] Test cases generated:', result);

      if (result.status === 'success') {
        // Store results in state for potential debugging
        setTestCaseResults(result.test_case_results || []);
        setGenerationSummary(result.summary || {});
          // Call the original onRun function with test case generation results
        if (onRun) {
          onRun('test-case-generation', {
            type: 'test-case-generation',
            data: result,
            selectedScenarios: selectedScenariosData,
            selectedFiles: selectedFiles,
            aiModel: selectedAIModel,
            processPrompt: processPrompt,
            finalPrompt: finalPrompt,
            sessionId: sessionId
          });
        }
        
        toast.success(`Generated test cases for ${result.summary?.successful_scenarios || 0} scenarios`);
      } else {
        throw new Error(result.message || 'Failed to generate test cases');
      }

    } catch (error) {
      console.error('[TestCaseGeneration] Error generating test cases:', error);
      toast.error(`Failed to generate test cases: ${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };  // Expose handleRunProcess to parent component and update form state
  useEffect(() => {
    if (onTestCaseGeneration && typeof onTestCaseGeneration === 'function') {
      // Calculate if form can run based on requirements
      const hasSelectedScenarios = selectedTestScenarios.length > 0;
      const hasPrompts = processPrompt && finalPrompt;
      
      // Seçenek 1: Token limiti aşımında da çalıştırmaya izin ver (ÖNERİLEN)
      // Sistem otomatik olarak yüksek kapasiteli model (qwen2.5-7b-instruct-1m) kullanacak
      // Bu yaklaşım kullanıcı deneyimini bozmaz ve sistem akıllı model seçimi yapar
      const canRun = hasSelectedScenarios && hasPrompts;
      
      // Update parent component's form state
      onTestCaseGeneration({
        canRun,
        isRunning: isGenerating,
        handleRun: handleRunProcess,
        tokenInfo: {
          totalTokens,
          exceedsLimit,
          selectedModel: selectedAIModel,
          autoModelSwitch: exceedsLimit ? 'qwen2.5-7b-instruct-1m' : selectedAIModel
        }
      });
    }
  }, [onTestCaseGeneration, selectedTestScenarios, processPrompt, finalPrompt, isGenerating, selectedProcessData, managedFiles, fileProcessMappings, selectedAIModel, sessionId, totalTokens, exceedsLimit]);

  return (
    <div className="max-w-4xl mx-auto p-4">
      <form className="space-y-6">
        {/* Process Title Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Test Scenario Process <span className="text-red-500">*</span>
          </label>
          <select
            value={selectedProcessTitle}
            onChange={(e) => handleProcessTitleChange(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            disabled={isLoading}
          >
            <option value="">Select a test scenario process...</option>
            {availableProcessTitles.map((process, index) => (
              <option key={index} value={process.process_title}>
                {process.process_title} ({process.test_type} - {process.test_category})
              </option>
            ))}
          </select>
          {isLoading && (
            <p className="text-sm text-gray-500 mt-1">Loading available processes...</p>
          )}
          {error && (
            <p className="text-sm text-red-500 mt-1">{error}</p>
          )}
        </div>

        {/* Selected Process Data Display */}
        {selectedProcessData && (
          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Selected Test Scenario Details</h3>
            
            {/* Process Information - Read Only */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Process Title</label>
                <input
                  type="text"
                  value={selectedProcessData.process_title}
                  className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm"
                  readOnly
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Test Type</label>
                <input
                  type="text"
                  value={selectedProcessData.test_type}
                  className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm"
                  readOnly
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Test Category</label>
                <input
                  type="text"
                  value={selectedProcessData.test_category}
                  className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm"
                  readOnly
                />
              </div>
            </div>            {/* Test Scenarios Selection with Checkboxes */}
            {selectedProcessData.test_scenarios && selectedProcessData.test_scenarios.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-sm font-medium text-gray-700">
                    Select Test Scenarios ({selectedProcessData.test_scenarios.length} available)
                  </label>
                  <div className="flex items-center space-x-4">
                    <button
                      type="button"
                      onClick={() => handleSelectAllTestScenarios(true)}
                      className="text-sm text-indigo-600 hover:text-indigo-800"
                    >
                      Select All
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectAllTestScenarios(false)}
                      className="text-sm text-gray-600 hover:text-gray-800"
                    >
                      Clear All
                    </button>
                  </div>
                </div>
                  <div className="max-h-96 overflow-y-auto border border-gray-300 rounded-md bg-white">
                  {selectedProcessData.test_scenarios.map((scenario, index) => {
                    const scenarioId = scenario.scenario_id || scenario.ScenarioID || `scenario_${index}`;
                    const scenarioTitle = scenario.scenario || scenario.Title || `Scenario ${index + 1}`;
                    const scenarioDescription = scenario.description || scenario.Description || '';
                    const scenarioObjective = scenario.objective || scenario.Objective || '';
                    const scenarioCategory = scenario.category || scenario.Category || '';
                    
                    return (
                      <div key={scenarioId} className="p-3 border-b border-gray-200 last:border-b-0">
                        <div className="flex items-start">
                          <input
                            type="checkbox"
                            id={`scenario-${scenarioId}`}
                            checked={selectedTestScenarios.includes(scenarioId)}
                            onChange={(e) => handleTestScenarioSelection(scenarioId, e.target.checked)}
                            className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                          />
                          <label 
                            htmlFor={`scenario-${scenarioId}`} 
                            className="ml-3 flex-1 cursor-pointer"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <h4 className="font-medium text-gray-900 mb-1">
                                  {scenarioTitle}
                                </h4>
                                <p className="text-sm text-gray-700 mb-2">
                                  {scenarioDescription}
                                </p>
                                {scenarioObjective && (
                                  <p className="text-xs text-gray-600 mb-1">
                                    <span className="font-medium">Objective:</span> {scenarioObjective}
                                  </p>
                                )}
                                {scenarioCategory && (
                                  <p className="text-xs text-gray-500">
                                    <span className="font-medium">Category:</span> {scenarioCategory}
                                  </p>
                                )}
                              </div>
                            </div>
                          </label>
                        </div>
                      </div>
                    );
                  })}
                </div>
                
                {selectedTestScenarios.length > 0 && (
                  <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-md">
                    <p className="text-sm font-medium text-green-800">
                      Selected scenarios: {selectedTestScenarios.length} of {selectedProcessData.test_scenarios.length}
                    </p>
                  </div>
                )}
              </div>
            )}            {/* AI Model Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700">AI Model</label>
              <select
                value={selectedAIModel}
                onChange={(e) => handleAIModelChange(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                disabled={modelsLoading}
              >
                <option value="">
                  {modelsLoading ? "Loading models..." : "Default model: llama3.2:3b"}
                </option>
                {availableModels && availableModels.map(m => (
                  <option key={m.key} value={m.key}>{m.displayName}</option>
                ))}
              </select>
              {modelsError && (
                <p className="mt-1 text-sm text-red-600">
                  Error loading models: {modelsError}
                </p>
              )}
              
              {/* Token Information Panel */}
              {totalTokens > 0 && (
                <div className={`mt-3 p-3 rounded-md ${exceedsLimit ? 'bg-yellow-50 border border-yellow-200' : 'bg-blue-50 border border-blue-200'}`}>
                  <div className="flex items-center">
                    <div className={`flex-shrink-0 ${exceedsLimit ? 'text-yellow-400' : 'text-blue-400'}`}>
                      {exceedsLimit ? (
                        <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <div className="ml-3">
                      <h3 className={`text-sm font-medium ${exceedsLimit ? 'text-yellow-800' : 'text-blue-800'}`}>
                        Token Analysis
                      </h3>
                      <div className={`mt-1 text-sm ${exceedsLimit ? 'text-yellow-700' : 'text-blue-700'}`}>
                        <p>Selected files contain approximately <strong>{totalTokens.toLocaleString()}</strong> tokens</p>
                        {exceedsLimit && (
                          <p className="mt-1">
                            <strong>⚠️ Large content detected!</strong> The system will automatically use <strong>qwen2.5-7b-instruct-1m</strong> model for optimal processing of large documents.
                            <br />
                            <span className="text-green-600 font-medium">✅ Process can still be run - model will be switched automatically!</span>
                          </p>
                        )}
                        {!exceedsLimit && (
                          <p className="mt-1">
                            <span className="text-green-600 font-medium">✅ Content size is within normal limits.</span> Your selected model <strong>{selectedAIModel}</strong> will be used.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="mt-2 text-sm text-blue-600 font-semibold">
                Currently selected model: {selectedAIModel || 'llama3.2:3b'}
              </div>
            </div>{/* Process Prompt Display */}
            {selectedProcessData && (
              <div className="bg-blue-50 border-l-4 border-blue-400 text-blue-700 p-4 rounded-md">
                <p className="font-medium">Base Prompt</p>
                <p className="text-sm mt-1 whitespace-pre-wrap">
                  {processPrompt || 'Prompt bulunamadı'}
                </p>
              </div>
            )}

            {/* Create Prompts Selection */}
            {Object.keys(createPrompts).length > 0 && (
              <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                <p className="font-medium text-gray-900 mb-3">Additional Test Case Requirements</p>
                <p className="text-sm text-gray-600 mb-4">Select additional prompts to include in your test case generation:</p>
                  <div className="space-y-3">
                  {Object.entries(createPrompts).map(([promptKey, promptText]) => (
                    <div key={promptKey} className="flex items-start">
                      <input
                        type="checkbox"
                        id={`create-prompt-${promptKey}`}
                        checked={selectedCreatePrompts.includes(promptKey)}
                        onChange={(e) => handleCreatePromptSelection(promptKey, e.target.checked)}
                        className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      <label 
                        htmlFor={`create-prompt-${promptKey}`} 
                        className="ml-3 flex-1 cursor-pointer"
                        title={promptText} // Show full text on hover
                      >
                        <span className="block text-sm font-medium text-gray-900">{promptKey}</span>
                      </label>
                    </div>
                  ))}
                </div>

                {selectedCreatePrompts.length > 0 && (
                  <div className="mt-4 p-3 bg-white border rounded-md">
                    <p className="text-sm font-medium text-gray-900 mb-2">Selected prompts: {selectedCreatePrompts.length}</p>
                    <ul className="text-xs text-gray-600 list-disc list-inside space-y-1">
                      {selectedCreatePrompts.map(promptKey => (
                        <li key={promptKey}>{promptKey}</li>
                      ))}
                    </ul>
                  </div>                )}              </div>
            )}            {/* Generate Test Cases Section - Removed, functionality moved to Run Process button */}            {/* Test Case Generation Results - Moved to Process Results panel */}

            {/* Generate Test Cases Button - Removed as requested */}
          </div>
        )}

        {!selectedProcessData && !isLoading && selectedProcessTitle && (
          <div className="text-center py-8">
            <p className="text-gray-500">No data found for the selected process.</p>
          </div>
        )}
      </form>
    </div>
  );
}

TestCaseGenerationForm.propTypes = {
  onRun: PropTypes.func,
  onTestCaseGeneration: PropTypes.func, // New prop for test case generation
  process: PropTypes.object,
  sessionId: PropTypes.string.isRequired,
  onFinalPromptChange: PropTypes.func,
  aiModels: PropTypes.oneOfType([PropTypes.array, PropTypes.object]),
  onAIModelUpdate: PropTypes.func,
  managedFiles: PropTypes.array,
  fileProcessMappings: PropTypes.object
};
