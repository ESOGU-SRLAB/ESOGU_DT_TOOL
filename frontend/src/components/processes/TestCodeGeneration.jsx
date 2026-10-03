import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { useSelector } from 'react-redux';
import api from '../../utils/api';
import { useApiKey } from '../../hooks/useApiKey';
import { useModels } from '../../hooks/useModels';
import { selectApiKeys } from '../../store/slices/apiKeySlice';

// Default prompt for test code generation
const defaultTestPrompt = `You are an expert test automation engineer. Generate executable test code based on the provided test cases and source code.

## Requirements:
1. Generate complete, executable test code using the appropriate framework
2. Use proper testing conventions and syntax
3. Include necessary imports and setup
4. Make tests specific to the test case objectives
5. Add meaningful assertions and validations
6. Include docstring explaining the test purpose
7. Make it ready to run without modifications

## Output Format:
Generate one test file per test case with proper naming conventions.
Each test should be independent and executable.

Please provide the generated test codes in the specified output format.`;

const TestCodeGeneration = ({ 
  process,
  managedFiles = [], 
  sessionId,
  onSetOutput = () => {},
  onRun = () => {},
  disabled = false,
  aiModels,
  outputFormats,
  onAIModelUpdate = () => {},
  onOutputFormatUpdate = () => {},
  onEnvironmentNameUpdate = () => {},
  environmentNames = [],
  onPromptUpdate = () => {},
  currentPrompt = '',
  fileProcessMappings = {}
}) => {
  // State management
  const [environmentSetups, setEnvironmentSetups] = useState([]);
  const [processTitles, setProcessTitles] = useState([]);
  const [selectedEnvironmentId, setSelectedEnvironmentId] = useState('');
  const [selectedProcessTitle, setSelectedProcessTitle] = useState('');
  const [environmentName, setEnvironmentName] = useState('');
  const [model, setModel] = useState('llama3.2:3b');
  const [outputFormat, setOutputFormat] = useState('JSON');
  const [maxTestCases, setMaxTestCases] = useState(''); // Empty string for "unlimited"
  const [maxInputTokens, setMaxInputTokens] = useState(64000);
  const [tokenEstimate, setTokenEstimate] = useState(null);
  const [isEstimatingTokens, setIsEstimatingTokens] = useState(false);
  const [capabilityFile, setCapabilityFile] = useState(null);
  const [capabilityStatus, setCapabilityStatus] = useState(null);
  
  // Use prop prompt if available, fallback to default
  const effectivePrompt = currentPrompt || defaultTestPrompt;
  
  // Model and API management
  const { hasValidKey } = useApiKey();
  const apiKeys = useSelector(selectApiKeys);
  
  // Debug API keys on component mount
  useEffect(() => {
    console.log('🔍 TestCodeGeneration - API Keys Debug:', {
      hasValidKey,
      apiKeysFromRedux: apiKeys,
      googleKey: apiKeys?.google ? `${apiKeys.google.substring(0, 15)}...` : 'NOT SET',
      openaiKey: apiKeys?.openai ? `${apiKeys.openai.substring(0, 15)}...` : 'NOT SET'
    });
  }, [apiKeys, hasValidKey]);
  
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

  // Filter source code files
  const sourceFiles = managedFiles.filter(file => 
    file.type === 'Source Code' && 
    (file.name.endsWith('.java') || file.name.endsWith('.py') || file.name.endsWith('.js') || file.name.endsWith('.ts'))
  );

  // Load environment setups on component mount
  useEffect(() => {
    const fetchEnvironmentSetups = async () => {
      try {
        const response = await api.get('/api/processes/test-code-generation/environment-setups');
        if (response.data.success === true) {
          setEnvironmentSetups(response.data.data || []);
        }
      } catch (err) {
        console.error('Error fetching environment setups:', err);
        toast.error('Error loading environment setups');
      }
    };

    fetchEnvironmentSetups();
  }, []);

  // Load process titles on component mount (independent of environment setup)
  useEffect(() => {
    const fetchProcessTitles = async () => {
      try {
        console.log('🔍 Fetching process titles...');
        const response = await api.get('/api/processes/test-code-generation/process-titles');
        
        console.log('✅ Process titles response:', response.data);
        
        if (response.data.success === true) {
          setProcessTitles(response.data.data || []);
          console.log(`✅ Loaded ${response.data.data?.length || 0} process titles`);
        }
      } catch (err) {
        console.error('❌ Error fetching process titles:', err);
        toast.error('Error loading process titles');
      }
    };

    fetchProcessTitles();
  }, []); // Load once on mount, not dependent on environment selection

  // Check test case count and warn user
  const checkTestCaseCount = async (processTitle) => {
    try {
      const response = await api.get(`/api/processes/test-code-generation/test-case-count/${encodeURIComponent(processTitle)}`);
      if (response.data.success && response.data.count) {
        const count = response.data.count;
        if (count > 50) {
          toast.warning(
            `⚠️ This process has ${count} unique test cases. Generation may take ${Math.ceil(count * 0.5 / 60)} minutes or more and might timeout. Consider processing in batches.`,
            { duration: 8000 }
          );
        } else if (count > 20) {
          toast.info(`ℹ️ This process has ${count} unique test cases. Generation may take several minutes.`, { duration: 5000 });
        }
      }
    } catch (err) {
      console.error('Error checking test case count:', err);
    }
  };

  // Initialize and sync prompt with parent
  useEffect(() => {
    if (!currentPrompt) {
      // Initialize with default prompt if no current prompt
      onPromptUpdate(defaultTestPrompt);
    } else {
      // Sync current prompt with parent
      onPromptUpdate(currentPrompt);
    }
  }, [currentPrompt]); // Only depend on currentPrompt to avoid infinite loop

  // Handle model change
  const handleModelChange = (e) => {
    const newModel = e.target.value;
    setModel(newModel);
    if (process && onAIModelUpdate) {
      onAIModelUpdate(process.id, newModel);
    }
  };

  // Handle output format change
  const handleOutputFormatChange = (e) => {
    const newFormat = e.target.value;
    setOutputFormat(newFormat);
    if (process && onOutputFormatUpdate) {
      onOutputFormatUpdate(process.id, newFormat);
    }
  };

  // Handle environment name change
  const handleEnvironmentNameChange = (e) => {
    const name = e.target.value;
    setEnvironmentName(name);
    if (process && onEnvironmentNameUpdate) {
      onEnvironmentNameUpdate(process.id, name);
    }
  };

  // Collect form data for Run Process
  const collectFormData = () => {
    if (!selectedEnvironmentId) {
      toast.error('Please select an environment setup');
      return null;
    }

    if (!selectedProcessTitle) {
      toast.error('Please select a process title');
      return null;
    }

    // Get selected files from fileProcessMappings
    const selectedFiles = managedFiles.filter(f => 
      fileProcessMappings[f.id]?.includes('test-code-generation')
    );

    if (selectedFiles.length === 0) {
      toast.error('Please select at least one source file');
      return null;
    }

    // Check if we have the required API key for selected model
    console.log('🔍 Debug - Current model:', model);
    console.log('🔍 Debug - Available API keys:', apiKeys);
    console.log('🔍 Debug - API key providers configured:', Object.keys(apiKeys).length);
    
    let requiredApiKey = null;
    // Check if model requires API key (Gemini models only, not local LM Studio models)
    if (model.startsWith('gemini')) {
      requiredApiKey = apiKeys.google;  // Gemini uses google key
      console.log('🔍 Debug - Google/Gemini key configured:', requiredApiKey ? 'YES' : 'NO');
      
      if (!requiredApiKey) {
        console.log('❌ Debug - API key validation failed for Gemini');
        toast.error('Please configure Gemini API key in settings');
        return null;
      }
    }
    // Note: Local LM Studio models (including openai/gpt-oss-*) don't require API keys
    
    console.log('✅ Debug - API key validation passed');
    console.log('🔍 Debug - Session ID:', sessionId);

    return {
      environment_session_id: selectedEnvironmentId,
      process_title: selectedProcessTitle,
      model: model,
      selected_files: selectedFiles,
      environment_name: environmentName,
      sessionId: sessionId, // Add session ID from props
      prompt: effectivePrompt,
      output_format: outputFormat
    };
  };

  const handleCapabilityFileChange = async (event) => {
    const file = event.target.files?.[0] || null;
    setCapabilityFile(file);
    setCapabilityStatus(null);
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      const approval = parsed?.meta?.approval || {};
      const hasCoreSchema = parsed?.schema_version && parsed?.api?.classes && parsed?.limits;
      if (!hasCoreSchema) {
        throw new Error('Missing schema_version, api.classes, or limits');
      }
      setCapabilityStatus({
        valid: true,
        approved: approval.approved === true,
        title: parsed?.meta?.title || file.name,
        image: parsed?.meta?.pinned_sources?.image?.tag || 'Not specified'
      });
    } catch (error) {
      setCapabilityStatus({ valid: false, error: error.message });
    }
  };

  const calculateTokenEstimate = async () => {
    if (!selectedEnvironmentId || !selectedProcessTitle || selectedFiles.length === 0) {
      toast.error('Select an environment, process title, and at least one source file first');
      return;
    }
    setIsEstimatingTokens(true);
    try {
      const estimateForm = new FormData();
      estimateForm.append('process_title', selectedProcessTitle);
      estimateForm.append('environment_session_id', selectedEnvironmentId);
      estimateForm.append('custom_prompt', effectivePrompt || '');
      estimateForm.append('max_input_tokens', String(maxInputTokens));
      selectedFiles.forEach((selectedFile) => {
        if (selectedFile?.file) {
          estimateForm.append('files', selectedFile.file, selectedFile.name);
        }
      });
      if (capabilityFile) {
        estimateForm.append('capability_file', capabilityFile, capabilityFile.name);
      }
      const response = await api.post(
        '/api/processes/test-code-generation/token-estimate',
        estimateForm,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      setTokenEstimate(response.data);
    } catch (error) {
      setTokenEstimate(null);
      toast.error(error.response?.data?.detail || error.message || 'Token estimation failed');
    } finally {
      setIsEstimatingTokens(false);
    }
  };

  // Component is ready when all required fields are filled
  const selectedFiles = managedFiles.filter(f => 
    fileProcessMappings[f.id]?.includes('test-code-generation')
  );
  const isFormReady = selectedEnvironmentId && selectedProcessTitle && selectedFiles.length > 0 && hasValidKey;

  // Handle process execution when onRun is called
  const executeProcess = async () => {
    // Validate required fields
    if (!environmentName || environmentName.trim() === '') {
      toast.error('Test Code Generation Process Name cannot be empty. Please enter a process name.');
      return;
    }

    const formDataObj = collectFormData();
    if (formDataObj) {
      try {
        // Create FormData object for multipart/form-data
        const formData = new FormData();
        
        // Add required form fields
        formData.append('process_title', formDataObj.process_title);
        formData.append('environment_session_id', formDataObj.environment_session_id);
        formData.append('model', formDataObj.model || 'llama3.2:3b');
        
        // Add optional fields
        if (formDataObj.prompt) {
          formData.append('custom_prompt', formDataObj.prompt);
        }
        
        // Ensure we have sessionId - get from props or generate one
        const effectiveSessionId = sessionId || `test-code-gen-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        console.log('🔍 Debug - Using session ID for execution:', effectiveSessionId);
        formData.append('session_id', effectiveSessionId);
        if (formDataObj.environment_name) {
          formData.append('environment_name', formDataObj.environment_name);
        }
        if (formDataObj.output_format) {
          formData.append('output_format', formDataObj.output_format);
        }
        
        // Add max_test_cases limit if specified
        if (maxTestCases && maxTestCases > 0) {
          formData.append('max_test_cases', maxTestCases);
          console.log(`⚠️ Limiting to ${maxTestCases} test cases`);
        }
        formData.append('max_input_tokens', String(maxInputTokens));

        if (capabilityFile) {
          formData.append('capability_file', capabilityFile, capabilityFile.name);
        }
        
        // Add API key if available - get from Redux store based on selected model
        let selectedApiKey = null;
        if (model.includes('gemini')) {
          selectedApiKey = apiKeys.google;  // Gemini uses google key in store
        } else if (model.includes('gpt') || model.includes('openai')) {
          selectedApiKey = apiKeys.openai;
        }
        
        if (selectedApiKey) {
          formData.append('api_key', selectedApiKey);
          console.log(`🔑 API key configured for model ${model}`);
        } else {
          console.log(`⚠️ No API key found for model ${model}`);
        }
        
        // Send every selected source file. Test generation needs the complete
        // implementation context instead of only the first selected file.
        (formDataObj.selected_files || []).forEach((selectedFile) => {
          if (selectedFile?.file) {
            formData.append('files', selectedFile.file, selectedFile.name);
          }
        });
        
        console.log('🚀 Test Code Generation - Sending API request...');
        console.log('📦 FormData contents:');
        for (let pair of formData.entries()) {
          if (pair[0] === 'api_key') {
            console.log(`  ${pair[0]}: ${pair[1] ? 'SET' : 'NOT SET'}`);
          } else if (pair[0] === 'files') {
            console.log(`  ${pair[0]}: ${pair[1].name} (${pair[1].size} bytes)`);
          } else {
            console.log(`  ${pair[0]}: ${pair[1]}`);
          }
        }
        
        // Call the test code generation API (no timeout - let backend handle long operations)
        const response = await api.post('/api/processes/test-code-generation/generate', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        
        console.log('✅ Test Code Generation - Response received:', response.data);
        console.log('✅ Response success field:', response.data?.success);
        
        if (response.data.success) {
            const excludedCount = (response.data.unsupported_count || 0) + (response.data.invalid_count || 0);
            if (excludedCount > 0) {
              toast.success(
                `${response.data.generated_count} executable tests generated; ${excludedCount} unsupported/invalid tests were blocked.`,
              );
            } else {
              toast.success(`Test codes generated successfully! Generated ${response.data.generated_count} test cases.`);
            }
            
            console.log('🎯 Test Code Generation - Full response data:', response.data);
            
            // Prepare formatted result for display
            const formattedResult = {
              summary: {
                generated_count: response.data.generated_count,
                total_test_cases: response.data.total_test_cases,
                failed_count: response.data.failed_count || 0,
                unsupported_count: response.data.unsupported_count || 0,
                invalid_count: response.data.invalid_count || 0,
                model_name: response.data.model_name,
                output_format: response.data.output_format,
                environment_session_id: response.data.environment_session_id,
                process_title: response.data.process_title,
                timestamp: response.data.timestamp
              },
              generated_tests: response.data.generated_tests || [],
              environment_info: response.data.environment_info || {}
            };
            
            console.log('🎯 Test Code Generation - Formatted result:', formattedResult);
            
            // Set output for display in OutputPanel
            const outputData = {
              type: 'test-code-generation',
              result: formattedResult,
              status: 'success',
              sessionId: sessionId,
              timestamp: new Date().toISOString()
            };
            
            console.log('🎯 Test Code Generation - Calling onSetOutput with:', outputData);
            onSetOutput('test-code-generation', outputData);
          }
      } catch (err) {
        console.error('Error executing test code generation:', err);
        
        const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Error generating test codes';
        toast.error(errorMessage);
        
        // Set error output
        onSetOutput('test-code-generation', {
          type: 'test-code-generation',
          error: errorMessage,
          status: 'error',
          sessionId: sessionId,
          timestamp: new Date().toISOString()
        });
      }
    }
  };

  // Register executeProcess on window so App.jsx can invoke it via window.testCodeGenerationExecute()
  useEffect(() => {
    window.testCodeGenerationExecute = executeProcess;
    return () => {
      window.testCodeGenerationExecute = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEnvironmentId, selectedProcessTitle, selectedFiles.length > 0, model, environmentName, effectivePrompt, outputFormat, capabilityFile, maxInputTokens]);

  return (
    <div className="max-w-2xl mx-auto p-4">
      <form className="space-y-6">
        {/* Process Configuration Section */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Process Configuration</h2>
          
          {/* Test Code Generation Process Name Field */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Test Code Generation Process Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={environmentName}
              onChange={handleEnvironmentNameChange}
              placeholder="e.g., Python Unit Tests - Shopping Cart Module"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              disabled={disabled}
            />
          </div>
          
          {/* AI Model Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">AI Model</label>
            <select
              value={model}
              onChange={handleModelChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              disabled={disabled}
            >
              <option value="llama3.2:3b">Default: llama3.2:3b</option>
              {availableModels && availableModels.map(m => (
                <option key={m.key} value={m.key}>{m.displayName}</option>
              ))}
            </select>
            {modelsError && (
              <p className="mt-1 text-sm text-red-600">
                Error loading models: {modelsError}
              </p>
            )}
          </div>
        </div>

        {/* Test Configuration Section */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Test Configuration</h2>
          
          {/* Environment Setup Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Environment Setup <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedEnvironmentId}
              onChange={(e) => setSelectedEnvironmentId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              disabled={disabled}
            >
              <option value="">Select Environment Setup</option>
              {environmentSetups.map(setup => (
                <option key={setup._id} value={setup._id}>
                  {setup.environment_name}
                </option>
              ))}
            </select>
          </div>

          {/* Process Title Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Process Title <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedProcessTitle}
              onChange={(e) => {
                const newTitle = e.target.value;
                setSelectedProcessTitle(newTitle);
                if (newTitle) {
                  checkTestCaseCount(newTitle);
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              disabled={disabled}
            >
              <option value="">Select Process Title</option>
              {processTitles.map((processInfo, index) => {
                // Support both old format (string) and new format (object)
                const processName = typeof processInfo === 'string' ? processInfo : processInfo.process_name;
                const testCaseCount = typeof processInfo === 'object' ? processInfo.test_case_count : null;
                const displayText = testCaseCount !== null 
                  ? `${processName} (${testCaseCount} test cases)`
                  : processName;
                
                return (
                  <option key={index} value={processName}>
                    {displayText}
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        {/* Robot Capability Contract */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Robot Capability Contract</h2>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Capability JSON (Recommended for robot tests)
          </label>
          <input
            type="file"
            accept=".json,application/json"
            onChange={handleCapabilityFileChange}
            className="block w-full text-sm text-gray-700 file:mr-4 file:rounded-md file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-indigo-700 hover:file:bg-indigo-100"
            disabled={disabled}
          />
          <p className="mt-2 text-xs text-gray-500">
            The backend treats this file as a closed-world API and safety-limit contract. Undeclared methods and out-of-range literal values are rejected.
          </p>
          {capabilityStatus?.valid && (
            <div className={`mt-3 rounded-md p-3 text-sm ${capabilityStatus.approved ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-800'}`}>
              <div className="font-medium">{capabilityStatus.title}</div>
              <div>Harness: {capabilityStatus.image}</div>
              <div>{capabilityStatus.approved ? 'Approved contract' : 'Draft contract — backend will block generation until manually approved'}</div>
            </div>
          )}
          {capabilityStatus && !capabilityStatus.valid && (
            <div className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-700">
              Invalid capability JSON: {capabilityStatus.error}
            </div>
          )}
        </div>

        {/* Batch Processing Options */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Batch Processing</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Test Cases (Optional)
            </label>
            <input
              type="number"
              min="1"
              placeholder="Leave empty for all test cases"
              value={maxTestCases}
              onChange={(e) => setMaxTestCases(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              disabled={disabled}
            />
            <p className="mt-2 text-sm text-gray-500">
              ⚠️ For processes with many test cases (50+), consider limiting to 10-20 at a time to avoid timeouts.
              Leave empty to process all test cases.
            </p>
          </div>

          <div className="mt-6 border-t border-gray-200 pt-5">
            <div className="flex items-center justify-between gap-4">
              <label className="block text-sm font-medium text-gray-700">
                Maximum input tokens per test case
              </label>
              <span className="font-mono text-sm font-semibold text-indigo-700">
                {maxInputTokens.toLocaleString()} tokens
              </span>
            </div>
            <input
              type="range"
              min="4096"
              max="64000"
              step="1024"
              value={maxInputTokens}
              onChange={(event) => {
                setMaxInputTokens(Number(event.target.value));
                setTokenEstimate(null);
              }}
              className="mt-3 w-full accent-indigo-600"
              disabled={disabled}
            />
            <div className="mt-1 flex justify-between text-xs text-gray-500">
              <span>4,096</span>
              <span>64,000 maximum</span>
            </div>
            <button
              type="button"
              onClick={calculateTokenEstimate}
              disabled={disabled || isEstimatingTokens}
              className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isEstimatingTokens ? 'Calculating…' : 'Calculate input tokens'}
            </button>

            {tokenEstimate && (
              <div className={`mt-4 rounded-md border p-3 text-sm ${tokenEstimate.fits_budget ? 'border-green-200 bg-green-50 text-green-900' : 'border-red-200 bg-red-50 text-red-900'}`}>
                <div className="font-semibold">
                  Largest single-test input: {tokenEstimate.max_tokens_per_test.toLocaleString()} / {tokenEstimate.max_input_tokens.toLocaleString()} tokens
                </div>
                <div className="mt-1">
                  Range across {tokenEstimate.test_case_count} test cases: {tokenEstimate.min_tokens_per_test.toLocaleString()}–{tokenEstimate.max_tokens_per_test.toLocaleString()} tokens
                </div>
                <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <span>Source files (raw)</span><span>{tokenEstimate.components.source_code_raw.toLocaleString()}</span>
                  <span>Source included</span><span>{tokenEstimate.components.source_code_included.toLocaleString()}</span>
                  <span>Custom prompt</span><span>{tokenEstimate.components.custom_prompt.toLocaleString()}</span>
                  <span>Largest test case</span><span>{tokenEstimate.components.largest_test_case.toLocaleString()}</span>
                  <span>Robot capabilities</span><span>{tokenEstimate.components.robot_capabilities.toLocaleString()}</span>
                </div>
                <p className="mt-2 text-xs">{tokenEstimate.note}</p>
              </div>
            )}
          </div>
        </div>

        {/* Output Format */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Output Format</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
            <select
              value={outputFormat}
              onChange={handleOutputFormatChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              disabled={disabled}
            >
              <option value="JSON">JSON</option>
              <option value="XML">XML</option>
            </select>
          </div>
        </div>
      </form>
    </div>
  );
};

export default TestCodeGeneration;
