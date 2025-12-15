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

  // Load process titles when environment setup is selected
  useEffect(() => {
    const fetchProcessTitles = async () => {
      if (!selectedEnvironmentId) {
        setProcessTitles([]);
        setSelectedProcessTitle('');
        return;
      }

      try {
        const response = await api.get('/api/processes/test-code-generation/process-titles', {
          params: { environment_setup_id: selectedEnvironmentId }
        });
        
        if (response.data.success === true) {
          setProcessTitles(response.data.data || []);
        }
      } catch (err) {
        console.error('Error fetching process titles:', err);
        toast.error('Error loading process titles');
      }
    };

    fetchProcessTitles();
  }, [selectedEnvironmentId]);

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
    console.log('🔍 Debug - API keys object keys:', Object.keys(apiKeys));
    console.log('🔍 Debug - Full API keys structure:', JSON.stringify(apiKeys, null, 2));
    
    let requiredApiKey = null;
    // Check if model requires API key (Gemini models only, not local LM Studio models)
    if (model.startsWith('gemini')) {
      requiredApiKey = apiKeys.google;  // Gemini uses google key
      console.log('🔍 Debug - Selected Google/Gemini key:', requiredApiKey ? `${requiredApiKey.substring(0, 10)}...` : 'NOT FOUND');
      
      if (!requiredApiKey) {
        console.log('❌ Debug - API key validation failed for Gemini');
        toast.error('Please configure Gemini API key in settings');
        return null;
      }
    }
    // Note: Local LM Studio models (including openai/gpt-oss-*) don't require API keys
    
    console.log('✅ Debug - API key validation passed');
    console.log('🔍 Debug - Session ID:', sessionId);

    const selectedFile = selectedFiles[0]; // Use first selected file
    
    return {
      environment_session_id: selectedEnvironmentId,
      process_title: selectedProcessTitle,
      model: model,
      selected_file: selectedFile,
      environment_name: environmentName,
      sessionId: sessionId, // Add session ID from props
      prompt: effectivePrompt,
      output_format: outputFormat
    };
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
        
        // Add API key if available - get from Redux store based on selected model
        let selectedApiKey = null;
        if (model.includes('gemini')) {
          selectedApiKey = apiKeys.google;  // Gemini uses google key in store
        } else if (model.includes('gpt') || model.includes('openai')) {
          selectedApiKey = apiKeys.openai;
        }
        
        if (selectedApiKey) {
          formData.append('api_key', selectedApiKey);
          console.log(`🔑 Added API key for model ${model}: ${selectedApiKey.substring(0, 10)}...`);
        } else {
          console.log(`⚠️ No API key found for model ${model}`);
        }
        
        // Add the selected file
        if (formDataObj.selected_file && formDataObj.selected_file.file) {
          formData.append('files', formDataObj.selected_file.file, formDataObj.selected_file.name);
        }
        
        // Call the test code generation API (no timeout - let backend handle long operations)
        const response = await api.post('/api/processes/test-code-generation/generate', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        
        if (response.data.success) {
            toast.success(`Test codes generated successfully! Generated ${response.data.generated_count} test cases.`);
            
            // Prepare formatted result for display
            const formattedResult = {
              summary: {
                generated_count: response.data.generated_count,
                total_test_cases: response.data.total_test_cases,
                failed_count: response.data.failed_count || 0,
                model_name: response.data.model_name,
                output_format: response.data.output_format,
                environment_session_id: response.data.environment_session_id,
                process_title: response.data.process_title,
                timestamp: response.data.timestamp
              },
              generated_tests: response.data.generated_tests || [],
              environment_info: response.data.environment_info || {}
            };
            
            // Set output for display in OutputPanel
            onSetOutput('test-code-generation', {
              type: 'test-code-generation',
              result: formattedResult,
              status: 'success',
              sessionId: sessionId,
              timestamp: new Date().toISOString()
            });
          }
      } catch (err) {
        console.error('Error executing test code generation:', err);
        
        const errorMessage = err.response?.data?.message || err.message || 'Error generating test codes';
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

  // Expose executeProcess function globally for TabPanel to access
  useEffect(() => {
    // Store the execution function on window for TabPanel to access
    window.testCodeGenerationExecute = executeProcess;
    
    return () => {
      // Cleanup
      delete window.testCodeGenerationExecute;
    };
  }, [selectedEnvironmentId, selectedProcessTitle, selectedFiles.length > 0, model, environmentName, effectivePrompt, outputFormat]);

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
              onChange={(e) => setSelectedProcessTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              disabled={disabled || !selectedEnvironmentId}
            >
              <option value="">Select Process Title</option>
              {processTitles.map((title, index) => (
                <option key={index} value={title}>
                  {title}
                </option>
              ))}
            </select>
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