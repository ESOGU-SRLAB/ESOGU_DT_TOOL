import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { 
  CogIcon, 
  ArrowPathIcon, 
  PlayIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import { useSelector } from 'react-redux';
import PropTypes from 'prop-types';
import { useModels } from '../../hooks/useModels';

// Custom hook to manage model information
function useModelInfo(selectedModel) {
  const modelDescriptions = {
    'llama3.2:1b': [
      'Ultra-lightweight 1B parameter model',
      'Optimized for speed and low resource usage',
      'Good for simple tasks and quick responses'
    ],
    'llama3.2:3b': [
      '3B parameter model with balanced performance',
      'Good balance of speed and capability',
      'Suitable for most general tasks'
    ],
    'codegeex4:9b': [
      'Specialized code generation model',
      'Excellent for programming tasks',
      'Supports multiple programming languages'
    ],
    'codellama:7b': [
      'Meta\'s code-focused language model',
      'Optimized for code completion and generation',
      'Strong performance on programming tasks'
    ],
    'gemini-2.5-flash': [
      'Google\'s fast multimodal AI model',
      'Excellent balance of speed and quality',
      'Supports text, image, and code tasks'
    ],
    'gemini-2.5-pro': [
      'Google\'s most capable AI model',
      'Advanced reasoning and analysis',
      'Premium performance for complex tasks'
    ]
  };
  
  return modelDescriptions[selectedModel] || [];
}

export default function TestExecutionForm({ 
  sessionId,
  onSetOutput,
  managedFiles = [],
  disabled = false,
  process,
  onTestCaseGeneration // Yeni prop - TabPanel'den gelen form state handler
}) {
  // Redux state for API keys
  const apiKeys = useSelector((state) => state.apiKey.apiKeys);
  
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
  
  // Component state
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('llama3.2:1b');

  const [isExecuting, setIsExecuting] = useState(false);
  const [mcpStatus, setMcpStatus] = useState(null);
  const [availableProcessNames, setAvailableProcessNames] = useState([]);
  const [selectedProcessName, setSelectedProcessName] = useState('');
  
  // New states for record-based execution
  const [processRecords, setProcessRecords] = useState([]);
  const [selectedRecords, setSelectedRecords] = useState([]);
  const [isLoadingRecords, setIsLoadingRecords] = useState(false);
  const [showCodePreview, setShowCodePreview] = useState(false);
  
  // New states for individual test execution
  const [individualTests, setIndividualTests] = useState([]);
  const [selectedTests, setSelectedTests] = useState([]);
  const [isLoadingTests, setIsLoadingTests] = useState(false);

  // Model info hook kullanımı
  const modelInfo = useModelInfo(selectedModel);

  // Handle model change
  const handleModelChange = (e) => {
    const selectedModel = e.target.value;
    setSelectedModel(selectedModel);
    console.log('Model changed to:', selectedModel);
  };

  // Fetch process records - Not used anymore but kept for potential future use
  const fetchProcessRecords = useCallback(async (processName) => {
    if (!processName) {
      setProcessRecords([]);
      return;
    }

    setIsLoadingRecords(true);
    try {
      const response = await fetch(`http://localhost:8000/api/test-execution/process/${encodeURIComponent(processName)}/records`);
      const data = await response.json();

      if (data.success) {
        setProcessRecords(data.records || []);
        setSelectedRecords([]); // Clear previous selections
        // Removed toast notification
      } else {
        setProcessRecords([]);
      }
    } catch (error) {
      console.error('Error fetching process records:', error);
      setProcessRecords([]);
    } finally {
      setIsLoadingRecords(false);
    }
  }, []);

  // Fetch individual tests
  const fetchIndividualTests = useCallback(async (processName) => {
    if (!processName) {
      setIndividualTests([]);
      return;
    }

    setIsLoadingTests(true);
    try {
      const response = await fetch(`http://localhost:8000/api/test-execution/process/${encodeURIComponent(processName)}/individual-tests`);
      const data = await response.json();

      if (data.success) {
        setIndividualTests(data.tests || []);
        setSelectedTests([]); // Clear previous selections
        toast.success(`Found ${data.tests.length} individual tests for process: ${processName}`);
      } else {
        setIndividualTests([]);
        toast.error('Failed to load individual tests');
      }
    } catch (error) {
      console.error('Error fetching individual tests:', error);
      setIndividualTests([]);
      toast.error('Failed to load individual tests');
    } finally {
      setIsLoadingTests(false);
    }
  }, []);

  // Handle record selection
  const handleRecordSelection = (recordId, isSelected) => {
    setSelectedRecords(prev => {
      if (isSelected) {
        return [...prev, recordId];
      } else {
        return prev.filter(id => id !== recordId);
      }
    });
  };

  // Handle select all
  const handleSelectAll = (selectAll) => {
    if (selectAll) {
      setSelectedRecords(processRecords.map(record => record.id));
    } else {
      setSelectedRecords([]);
    }
  };

  // Handle individual test selection
  const handleTestSelection = (testId, isSelected) => {
    setSelectedTests(prev => {
      const newSelection = isSelected 
        ? [...prev, testId]
        : prev.filter(id => id !== testId);
      
      return newSelection;
    });
  };

  // Handle select all tests
  const handleSelectAllTests = (selectAll) => {
    if (selectAll) {
      setSelectedTests(individualTests.map(test => test.test_id));
    } else {
      setSelectedTests([]);
    }
  };

  // Check MCP status
  const checkMcpStatus = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/test-execution/mcp/status');
      const data = await response.json();
      setMcpStatus(data);
    } catch (error) {
      console.error('Error checking MCP status:', error);
      setMcpStatus({ status: 'error', message: error.message });
    }
  }, []);

  // Fetch available process names
  const fetchProcessNames = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/test-execution/process-names');
      const data = await response.json();
      setAvailableProcessNames(data.process_names || []);
    } catch (error) {
      console.error('Error fetching process names:', error);
      toast.error('Failed to load process names');
    }
  }, []);



  // Execute tests - Moved from Execute Selected button to Run Process
  const executeTests = async () => {
    // Check if tests are selected
    if (selectedTests.length === 0) {
      toast.error('Please select at least one test to execute');
      return;
    }

    // API key kontrolü - seçilen modelin tipine göre
    const selectedModelInfo = availableModels.find(m => m.key === selectedModel);
    let apiKey = null;
    
    if (selectedModelInfo?.type === 'api') {
      // Gemini modeller için Google API key kullan
      if (selectedModel.startsWith('gemini')) {
        apiKey = apiKeys.google;
        if (!apiKey) {
          toast.error('Gemini API key is required. Please configure it in API Settings.');
          return;
        }
      }
      // Diğer API modeller için uygun key'i bul
      else if (!selectedModelInfo?.apiKeyStatus?.hasKey) {
        toast.error('API key is required for this model. Please configure it in API Settings.');
        return;
      }
    }

    // Validation - process name is required
    if (!selectedProcessName) {
      toast.error('Please select a test code generation process');
      return;
    }

    setIsExecuting(true);
    
    // Create initial output with loading state
    const selectedCount = selectedTests.length;
    
    const loadingOutput = {
      status: 'running',
      content: `🔄 **Executing ${selectedCount} Selected Test${selectedCount > 1 ? 's' : ''}**

⚙️ **Configuration:**
- Model: ${selectedModelInfo?.name || selectedModel}
- Type: ${selectedModelInfo?.type || 'unknown'}
- Process: ${selectedProcessName}
- Selected tests: ${selectedCount}

🧠 **Context-Aware Execution:**
✅ Source code context is automatically extracted from the database
✅ AI will receive both the test code AND the source code being tested
✅ This enables smarter execution with full understanding of the test context

📋 **Execution Strategy:**
Each test will be executed individually to avoid context limit issues.
This ensures reliable execution even with many tests.

⏳ Please wait while the tests are being executed one by one...

**Progress:** Executing tests (this may take a few moments)...`,
      timestamp: new Date().toISOString(),
      model: selectedModel,
      processType: 'Test Execution'
    };

    if (onSetOutput) {
      onSetOutput('test-execution', loadingOutput);
    }

    try {
      const requestBody = {
        test_ids: selectedTests,
        model: selectedModel,
        ...(apiKey ? { api_key: apiKey } : {})
      };
      const endpoint = 'http://localhost:8000/api/test-execution/execute-selected-tests';

      console.log('[TestExecution] Sending request:', {
        endpoint,
        requestBody,
        selectedTests,
        selectedModel
      });

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      console.log('[TestExecution] Response status:', response.status, response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('[TestExecution] Error response:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      console.log('[TestExecution] Result:', result);

      if (result.success) {
        // Parse batch results to show summary
        const output = result.terminal_output || '';
        
        // Check if this is a batch execution result
        const isBatchResult = output.includes('BATCH TEST EXECUTION RESULTS');
        
        let executionSummary;
        
        if (isBatchResult) {
          // Extract summary from batch results
          const summaryMatch = output.match(/Total Tests: (\d+)\s+✅ Successful: (\d+)\s+❌ Failed: (\d+)\s+Success Rate: ([\d.]+)%/);
          
          if (summaryMatch) {
            const [, total, successful, failed, successRate] = summaryMatch;
            
            executionSummary = `✅ **Batch Test Execution Completed**

📊 **Execution Summary:**
- **Total Tests:** ${total}
- **Successful:** ✅ ${successful}
- **Failed:** ❌ ${failed}
- **Success Rate:** ${successRate}%
- **Model Used:** ${result.model_used || selectedModel}
- **Model Type:** ${selectedModelInfo?.type || 'Unknown'}
- **Timestamp:** ${new Date(result.timestamp).toLocaleString()}

---

📋 **Execution Strategy:**
Each test was executed individually to avoid context limit issues.

---

📤 **Detailed Results:**

\`\`\`
${output}
\`\`\`

---

${failed === '0' 
  ? '🎉 **All tests passed successfully!**' 
  : `⚠️ **${failed} test(s) failed.** Please review the detailed results above.`}`;
          } else {
            // Fallback if parsing fails
            executionSummary = `✅ **Test Execution Completed**

📤 **Results:**

\`\`\`
${output}
\`\`\``;
          }
        } else {
          // Single test or old format
          executionSummary = `✅ **Test Execution Completed Successfully**

📊 **Execution Summary:**
- **Tests Executed:** ${selectedCount} test${selectedCount > 1 ? 's' : ''}
- **Model Used:** ${result.model_used || selectedModel}
- **Model Type:** ${selectedModelInfo?.type || 'Unknown'}
- **Timestamp:** ${new Date(result.timestamp).toLocaleString()}
- **Status:** ✓ Success

---

📤 **Test Execution Output:**

\`\`\`
${output}
\`\`\`

---

🏁 **Execution completed successfully!**`;
        }

        const successOutput = {
          status: 'completed',
          content: executionSummary,
          timestamp: result.timestamp,
          model: result.model_used || selectedModel,
          model_used: result.model_used,
          processType: 'Test Execution'
        };

        if (onSetOutput) {
          onSetOutput('test-execution', successOutput);
        }
        
        // Show appropriate toast message
        if (isBatchResult && output.includes('❌ Failed:')) {
          const failedMatch = output.match(/❌ Failed: (\d+)/);
          const failedCount = failedMatch ? failedMatch[1] : '0';
          if (failedCount !== '0') {
            toast.warning(`Execution complete: ${failedCount} test(s) failed`);
          } else {
            toast.success(`All ${selectedCount} tests executed successfully!`);
          }
        } else {
          toast.success(`${selectedCount} test${selectedCount > 1 ? 's' : ''} executed successfully!`);
        }
      } else {
        // Check if it's a context length error
        const isContextError = result.error && (
          result.error.includes('context length') || 
          result.error.includes('context overflows') ||
          result.error.includes('tokens when context')
        );
        
        let errorContent;
        if (isContextError) {
          errorContent = `❌ **Context Length Exceeded**

🔴 **Error Type:** Model Context Limit Exceeded

**Problem:**
The selected tests are too large for the current model's context window.

**Error Details:**
\`\`\`
${result.error}
\`\`\`

**💡 Solutions:**

1. **Use a Larger Model:**
   - Switch to a model with larger context (e.g., 8K, 16K, or 32K tokens)
   - Gemini models support up to 128K tokens
   - Larger local models (70B+) often have bigger context windows

2. **Reduce Test Selection:**
   - Currently selected: ${selectedCount} tests
   - Try selecting fewer tests (10-15 recommended for 4K context models)
   - Run tests in smaller batches

3. **Use Gemini API:**
   - Gemini models have much larger context windows
   - Better for executing many tests at once

**Current Selection:**
- Tests: ${selectedCount}
- Approximate size: Check the size indicator above the test list`;
        } else {
          errorContent = `❌ **Test Execution Failed**

🔴 **Error Details:**
\`\`\`
${result.error || 'Unknown error occurred'}
\`\`\`

**Troubleshooting:**
- Check if the backend services are running
- Verify your model is loaded in LM Studio
- Ensure your API key is valid (for Gemini models)

**Configuration:**
- Model: ${selectedModel}
- Tests: ${selectedCount}`;
        }

        const errorOutput = {
          status: 'error',
          content: errorContent,
          timestamp: new Date().toISOString(),
          model: selectedModel,
          processType: 'Test Execution'
        };

        if (onSetOutput) {
          onSetOutput('test-execution', errorOutput);
        }
        
        if (isContextError) {
          toast.error('Context limit exceeded! Try fewer tests or a larger model.');
        } else {
          toast.error('Test execution failed');
        }
      }
    } catch (error) {
      console.error('Execution error:', error);
      
      const errorOutput = {
        status: 'error',
        content: `❌ Connection Error\n\n🔴 **Network Error:**\n${error.message}\n\nPlease ensure the backend services are running:\n- Main Backend: http://localhost:8000\n- MCP Server: http://localhost:8001`,
        timestamp: new Date().toISOString(),
        model: selectedModel,
        processType: 'Test Execution'
      };

      if (onSetOutput) {
        onSetOutput('test-execution', errorOutput);
      }
      
      toast.error('Execution failed: Connection error');
    } finally {
      setIsExecuting(false);
    }
  };

  // Load data on component mount
  useEffect(() => {
    fetchProcessNames();
    checkMcpStatus();
  }, []); // Remove functions from dependency array since they have empty deps

  // Update TabPanel form state to enable/disable Run Process button
  useEffect(() => {
    if (onTestCaseGeneration) {
      const canRun = selectedTests.length > 0 && selectedProcessName && !isExecuting;
      onTestCaseGeneration({
        canRun,
        isRunning: isExecuting,
        handleRun: canRun ? executeTests : null
      });
    }
  }, [onTestCaseGeneration, selectedTests, selectedProcessName, isExecuting]);



  return (
    <div className="space-y-6">
      {/* Status Section */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <CogIcon className="w-5 h-5 mr-2 text-gray-600" />
          Test Execution Configuration
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Process Info */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Selected Process Information
              </label>
              <div className="bg-gray-50 rounded-lg p-3 border">
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Process Name:</span> {selectedProcessName || 'Not selected'}
                </p>
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Status:</span> 
                  <span className={clsx(
                    'ml-2 px-2 py-1 rounded-full text-xs',
                    selectedProcessName && selectedTests.length > 0
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  )}>
                    {selectedProcessName && selectedTests.length > 0 ? 'Ready' : 'Not Ready'}
                  </span>
                </p>
              </div>
            </div>

            {/* Context-Aware Execution Info */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                🧠 Context-Aware Execution
              </label>
              <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                <div className="space-y-2">
                  <div className="flex items-start gap-2 text-xs text-blue-800">
                    <span className="text-green-600 font-bold">✓</span>
                    <span>Source code automatically extracted from database</span>
                  </div>
                  <div className="flex items-start gap-2 text-xs text-blue-800">
                    <span className="text-green-600 font-bold">✓</span>
                    <span>AI receives both test code and source code</span>
                  </div>
                  <div className="flex items-start gap-2 text-xs text-blue-800">
                    <span className="text-green-600 font-bold">✓</span>
                    <span>Tests executed with full context understanding</span>
                  </div>
                </div>
                <p className="text-xs text-blue-700 mt-2 pt-2 border-t border-blue-200">
                  <strong>Note:</strong> Source code context helps AI better understand what each test validates, leading to more accurate execution results.
                </p>
              </div>
            </div>

            {/* MCP Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center justify-between">
                MCP Server Status
                <button
                  onClick={checkMcpStatus}
                  className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                  title="Refresh MCP Status"
                >
                  <ArrowPathIcon className="w-4 h-4" />
                </button>
              </label>
              <div className="bg-gray-50 rounded-lg p-3 border">
                <div className="flex items-center">
                  <div className={clsx(
                    'w-3 h-3 rounded-full mr-3',
                    mcpStatus?.status === 'error' ? 'bg-red-500' : 'bg-green-500'
                  )} />
                  <span className="text-sm text-gray-700">
                    {mcpStatus?.status === 'error' ? 'Offline' : 'Online'}
                  </span>
                </div>
                {mcpStatus?.message && (
                  <p className="text-xs text-gray-500 mt-1">{mcpStatus.message}</p>
                )}
              </div>
            </div>
          </div>

          {/* AI Model Configuration */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                AI Model <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedModel}
                onChange={handleModelChange}
                disabled={disabled || isExecuting || modelsLoading}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {!modelsLoading && availableModels.length === 0 && (
                  <option value="">No models available</option>
                )}
                {availableModels.map(model => (
                  <option key={model.key} value={model.key}>
                    {model.displayName || model.name}
                  </option>
                ))}
              </select>
              {modelsLoading && (
                <p className="text-xs text-gray-500 mt-1">
                  Loading available models...
                </p>
              )}
              {modelsError && (
                <p className="text-xs text-red-600 mt-1">
                  ⚠️ Error loading models: {modelsError}
                </p>
              )}
            </div>

            {/* Model Information */}
            {selectedModel && modelInfo.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <h4 className="text-sm font-medium text-blue-900 mb-2">Model Information</h4>
                <ul className="text-xs text-blue-800 space-y-1">
                  {modelInfo.map((info, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-blue-600 mr-2">•</span>
                      <span>{info}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Test Code Selection Section */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <DocumentTextIcon className="w-5 h-5 mr-2 text-gray-600" />
          Test Code Selection
        </h3>
        
        <div className="space-y-4">
          {/* Process Name Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Test Code Generation Process Name <span className="text-red-500">*</span>
            </label>
            <div className="flex space-x-2">
              <select
                value={selectedProcessName}
                onChange={(e) => {
                  setSelectedProcessName(e.target.value);
                  if (e.target.value) {
                    fetchIndividualTests(e.target.value);
                  }
                }}
                disabled={disabled || isLoading}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50"
              >
                <option value="">Select a test code generation process...</option>
                {availableProcessNames.map(process => (
                  <option key={process.name} value={process.name}>
                    {process.name} ({process.count} records)
                  </option>
                ))}
              </select>
              <button
                onClick={fetchProcessNames}
                disabled={isLoading}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
                title="Refresh process names"
              >
                <ArrowPathIcon className="w-4 h-4" />
              </button>
            </div>
            {availableProcessNames.length === 0 && (
              <p className="text-xs text-gray-500 mt-1">
                No test code generation processes found. Generate some test code first in the Test Code Generation tab.
              </p>
            )}
            {selectedProcessName && (
              <p className="text-xs text-green-600 mt-1">
                ✓ Test code loaded from process: {selectedProcessName}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Individual Tests Selection Section */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <DocumentTextIcon className="w-5 h-5 mr-2 text-gray-600" />
            Individual Tests Selection
          </h3>
          <div className="flex space-x-2">
            {selectedProcessName && (
              <button
                onClick={() => fetchIndividualTests(selectedProcessName)}
                disabled={isLoadingTests}
                className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50 flex items-center"
              >
                <ArrowPathIcon className="w-3 h-3 mr-1" />
                Reload
              </button>
            )}
            {individualTests.length > 0 && (
              <span className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded">
                {individualTests.length} tests found
              </span>
            )}
          </div>
        </div>

        {selectedProcessName && (
            <div className="space-y-4">
              {/* Select All Tests */}
              {individualTests.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={selectedTests.length === individualTests.length}
                        onChange={(e) => handleSelectAllTests(e.target.checked)}
                        className="mr-2 rounded"
                      />
                      <span className="text-sm font-medium text-gray-700">
                        Select All ({individualTests.length} tests)
                      </span>
                    </label>
                    <div className="flex items-center space-x-2">
                      <span className={clsx(
                        "text-xs font-medium px-2 py-1 rounded",
                        selectedTests.length > 0 
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-600"
                      )}>
                        {selectedTests.length} selected
                      </span>
                    </div>
                  </div>
                  
                  {/* Size/Token Estimate - Info Only */}
                  {selectedTests.length > 0 && (() => {
                    const selectedTestObjects = individualTests.filter(t => selectedTests.includes(t.test_id));
                    const totalChars = selectedTestObjects.reduce((sum, test) => sum + test.full_code.length, 0);
                    const approxTokens = Math.ceil(totalChars / 4);
                    
                    return (
                      <div className="p-2 rounded text-xs bg-blue-50 border border-blue-200">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-blue-900">
                            📊 Selection Info:
                          </span>
                          <span className="text-blue-800">
                            {(totalChars / 1000).toFixed(1)}K chars (~{approxTokens.toLocaleString()} tokens)
                          </span>
                        </div>
                        <p className="text-blue-700 mt-1">
                          ℹ️ Each test will be executed individually, avoiding context limit issues.
                        </p>
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Loading State */}
              {isLoadingTests && (
                <div className="flex items-center justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                  <span className="ml-2 text-gray-600">Loading individual tests...</span>
                </div>
              )}

              {/* Individual Tests List */}
              {!isLoadingTests && individualTests.length > 0 && (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {individualTests.map((test, index) => (
                    <div
                      key={test.test_id}
                      className={clsx(
                        'p-3 border rounded-lg cursor-pointer transition-colors',
                        selectedTests.includes(test.test_id)
                          ? 'border-indigo-300 bg-indigo-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      )}
                      onClick={() => handleTestSelection(test.test_id, !selectedTests.includes(test.test_id))}
                    >
                      <div className="flex items-start space-x-3">
                        <input
                          type="checkbox"
                          checked={selectedTests.includes(test.test_id)}
                          onChange={(e) => handleTestSelection(test.test_id, e.target.checked)}
                          className="mt-1 rounded"
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="text-sm font-medium text-gray-900 truncate">
                              {test.test_name || `Test ${test.test_index + 1}`}
                            </h4>
                            <span className="text-xs text-gray-500 ml-2">
                              #{test.test_index + 1}
                            </span>
                          </div>
                          <p className="text-xs text-gray-600 mb-1">
                            Session: {test.session_id}
                          </p>
                          
                          {/* Test Code Snippet */}
                          <div className="text-xs text-gray-700 bg-gray-100 rounded p-2 font-mono mb-2">
                            {test.code_snippet}
                          </div>
                          
                          {/* Source Code Context Expander */}
                          {test.source_code && (
                            <details className="mt-2" onClick={(e) => e.stopPropagation()}>
                              <summary className="cursor-pointer text-xs font-medium text-blue-700 hover:text-blue-900 flex items-center gap-1">
                                <span>📄 View Source Code Context</span>
                                <span className="text-blue-600">(Click to expand)</span>
                              </summary>
                              <div className="mt-2 bg-blue-50 border border-blue-200 rounded p-2">
                                <p className="text-xs text-blue-700 mb-2">
                                  <strong>Source code for this test:</strong>
                                </p>
                                <div className="bg-white border border-blue-300 rounded p-2 max-h-64 overflow-y-auto">
                                  <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap">
                                    {test.source_code.length > 500 
                                      ? test.source_code.substring(0, 500) + "\n\n... (truncated, full source code will be sent to AI)"
                                      : test.source_code}
                                  </pre>
                                </div>
                              </div>
                            </details>
                          )}
                          
                          {!test.source_code && (
                            <p className="text-xs text-gray-500 italic mt-1">
                              ℹ️ No source code context available for this test
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* No Tests Found */}
              {!isLoadingTests && individualTests.length === 0 && selectedProcessName && (
                <div className="text-center p-8 text-gray-500">
                  <DocumentTextIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p className="text-sm">No individual tests found for this process.</p>
                  <p className="text-xs mt-1">Make sure the process contains generated_tests array.</p>
                </div>
              )}
            </div>
          )}
      </div>
    </div>
  );
}

TestExecutionForm.propTypes = {
  sessionId: PropTypes.string,
  onSetOutput: PropTypes.func,
  managedFiles: PropTypes.array,
  disabled: PropTypes.bool,
  process: PropTypes.object,
  onTestCaseGeneration: PropTypes.func // Yeni prop type
};