import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { useSelector } from 'react-redux';
import PropTypes from 'prop-types';
import processService from '../../services/processService';
import { useModels } from '../../hooks/useModels';

// Custom hook to manage model information
function useModelInfo(selectedModel) {
  const modelDescriptions = {
    "codegeex4:9b": [
      "A multilingual code generation model with 9B parameters.",
      "Supports tasks like code completion, commenting, and function calls.",
      "Trained on GLM-4-9B and can handle 128K token context."
    ],
    "codellama:7b": [
      "A code generation model based on Meta's Llama 2 architecture.",
      "Supports various languages like Python, C++, Java, PHP, TypeScript, C#, and Bash.",
      "Capable of code completion, debugging, and natural language descriptions."
    ],
    "deepseek-coder:6.7b": [
      "A 6.7B parameter model optimized for code generation and interpretation.",
      "Provides high-accuracy code in various programming languages.",
      "Efficient at code completion and bug-fixing tasks."
    ],
    "gemma2:2b": [
      "A lightweight 2B parameter model for code generation.",
      "Ideal for small projects and low-resource environments.",
      "Supports basic code completion and suggestions."
    ],
    "gemma3:4b": [
      "A 4B parameter model optimized for mid-sized projects.",
      "Can handle more complex code structures.",
      "Balanced performance in code generation and interpretation."
    ],
    "llama3.2:3b": [
      "A 3B parameter model optimized for fast and efficient code generation.",
      "Effective for small and medium-sized code completion tasks.",
      "Provides low-latency responses."
    ],
    "qwen2.5:7b": [
      "A multilingual 7B parameter model for code generation.",
      "Generates high-accuracy code in multiple programming languages.",
      "Efficient at code completion and interpretation."
    ],
    "qwen2.5:7b-1m": [
      "A high-capacity 7B parameter model optimized for processing large content (1M+ tokens).",
      "Auto-selected when file contents exceed 100,000 tokens.",
      "Ideal for analyzing very large documents and codebases."
    ],
    "qwen2.5-coder:3b": [
      "A lightweight 3B parameter model for code generation.",
      "Ideal for small projects and low-resource environments.",
      "Supports basic code completion and suggestions."
    ],
    "stable-code:3b": [
      "A 3B parameter model known for its stable and reliable code generation.",
      "Effective at code completion and bug fixing.",
      "Supports a variety of programming languages."
    ],
    "starcoder2:7b": [
      "A 7B parameter model with advanced code generation and analysis capabilities.",
      "Handles complex code structures and projects well.",
      "Excels in code completion and suggestion tasks."
    ]
  };

  return modelDescriptions[selectedModel] || [];
}

export default function TestScenarioGenerationForm({ onGeneratePrompt, onRun, onRunProcess, process, managedFiles, fileProcessMappings, onFormStateChange, sessionId }) {
  // Redux API key - Google için
  const apiKey = useSelector((state) => state.apiKey.apiKeys.google);
  
  console.log('[DEBUG] API Key from Redux:', apiKey ? 'SET' : 'NOT SET');
  
  const [processTitle, setProcessTitle] = useState('');
  const [testCategory, setTestCategory] = useState('Select Test Category');
  const [testType, setTestType] = useState('');
  const [model, setModel] = useState('llama3.2:3b');
  const [modelInfo, setModelInfo] = useState([]);
  const [availableTestTypes, setAvailableTestTypes] = useState([]);
  const [scoringElements, setScoringElements] = useState({});
  const [scoringElementDetails, setScoringElementDetails] = useState({});
  const [instructionElements, setInstructionElements] = useState({});
  const [instructionElementDetails, setInstructionElementDetails] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTooltip, setActiveTooltip] = useState(null);
  const [testPrompt, setTestPrompt] = useState('Generate comprehensive test scenarios for login functionality including positive and negative test cases');
  const [isEditingPrompt, setIsEditingPrompt] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState('');
  const [generatedCustomPrompt, setGeneratedCustomPrompt] = useState(''); // Generated custom prompt'u saklamak için
  const [finalPrompt, setFinalPrompt] = useState(''); // Final combined prompt
  const [selectedFiles, setSelectedFiles] = useState([]); // Selected files for this process

  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState(null);

  // Initialize loading state to false on mount and add debugging
  useEffect(() => {
    console.log('[DEBUG] Component mounted, initializing isLoading to false');
    setIsLoading(false);
  }, []);

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

  const categoryNames = [
    'Select Test Category',
    'Functional',
    'Non-Functional'
  ];

  const allTestTypes = [
    { name: "Integration Testing", category: "Functional" },
    { name: "Input Data Variety Testing", category: "Functional" },
    { name: "Functional Testing", category: "Functional" },
    { name: "Edge Cases and Boundary Testing", category: "Functional" },
    { name: "User Interface (GUI) Testing", category: "Functional" },
    { name: "Performance and Load Testing", category: "Non-Functional" },
    { name: "Compatibility Testing", category: "Non-Functional" },
    { name: "Security Testing", category: "Non-Functional" }
  ];

  useEffect(() => {
    console.log('[DEBUG] testCategory useEffect triggered:', { testCategory });
    if (testCategory && testCategory !== 'Select Test Category') {
      const filteredTests = allTestTypes.filter(test => test.category === testCategory);
      console.log('[DEBUG] Setting availableTestTypes:', filteredTests);
      setAvailableTestTypes(filteredTests);
      setTestType('');
      // Reset scoring elements when category changes
      setScoringElements({});
      setScoringElementDetails({});
      // Explicitly set loading to false when clearing test type
      setIsLoading(false);
    } else {
      console.log('[DEBUG] Clearing availableTestTypes - category:', testCategory);
      setAvailableTestTypes([]);
      setTestType('');
      // Explicitly set loading to false when clearing test type
      setIsLoading(false);
    }
  }, [testCategory]);

  useEffect(() => {
    console.log('[DEBUG] testType useEffect triggered:', { testType, isLoading });
    
    async function fetchTestTypeData() {
      if (!testType) {
        console.log('[DEBUG] testType is empty, clearing states and setting isLoading to false');
        setScoringElements({});
        setScoringElementDetails({});
        setInstructionElements({});
        setInstructionElementDetails({});
        setTestPrompt('');
        setIsLoading(false); // Loading durumunu sıfırla
        return;
      }

      console.log('[DEBUG] testType is set, starting loading:', testType);
      setIsLoading(true);
      setError(null);
      try {
        const response = await processService.getTestTypeDetails(testType);
        
        // Set test prompt
        setTestPrompt(response.test_prompt || '');

        // Set scoring elements
        const scoringData = response.test_scoring_elements_and_prompts || {};
        setScoringElements(Object.keys(scoringData).reduce((acc, key) => ({
          ...acc,
          [key]: false
        }), {}));
        setScoringElementDetails(scoringData);

        // Set instruction elements
        const instructionData = response.test_instruction_elements_and_prompts || {};
        setInstructionElements(Object.keys(instructionData).reduce((acc, key) => ({
          ...acc,
          [key]: false
        }), {}));
        setInstructionElementDetails(instructionData);
      } catch (err) {
        setError(err.message);
        setScoringElements({});
        setScoringElementDetails({});
        setInstructionElementDetails({});
        setTestPrompt('');
      } finally {
        setIsLoading(false);
      }
    }

    fetchTestTypeData();
  }, [testType]);

  // Reset selected files when process changes
  useEffect(() => {
    setSelectedFiles([]);
  }, [process?.id]);

  const handleSavePrompt = () => {
    setTestPrompt(editedPrompt);
    setIsEditingPrompt(false);
    toast.success('Prompt saved successfully!');
  };
  
  const handleCancelEdit = () => {
    setIsEditingPrompt(false);
    setEditedPrompt('');
    toast('Edit cancelled.', { icon: '🛑' });
  };  

  const handleScoringElementChange = (element) => {
    setScoringElements(prev => ({
      ...prev,
      [element]: !prev[element]
    }));
  };

  const handleInstructionElementChange = (element) => {
    setInstructionElements(prev => ({
      ...prev,
      [element]: !prev[element]
    }));
  };

  // File selection handlers
  const handleFileSelection = (fileId) => {
    setSelectedFiles(prev => {
      if (prev.includes(fileId)) {
        return prev.filter(id => id !== fileId);
      } else {
        return [...prev, fileId];
      }
    });
  };

  const handleSelectAllFiles = () => {
    if (managedFiles && managedFiles.length > 0) {
      const allFileIds = managedFiles.map(file => file.id);
      setSelectedFiles(allFileIds);
    }
  };

  const handleDeselectAllFiles = () => {
    setSelectedFiles([]);
  };

  // Get available files for this process (those that are mapped to this process or all if no mapping)
  const getAvailableFiles = () => {
    if (!managedFiles) return [];
    
    if (process?.id && fileProcessMappings) {
      // Return files that are mapped to this specific process
      return managedFiles.filter(file => 
        fileProcessMappings[file.id]?.includes(process.id)
      );
    }
    
    // If no process mapping, return all managed files
    console.log('[DEBUG] Available files:', managedFiles.map(f => ({
      id: f.id,
      name: f.name,
      hasContent: !!f.content,
      contentLength: f.content?.length || 0
    })));
    return managedFiles;
  };

  const handleGeneratePrompt = async () => {
    console.log('[DEBUG] handleGeneratePrompt started');
    console.log('[DEBUG] Using global sessionId:', sessionId);
    
    // Check for missing fields and show specific error messages
    const missingFields = [];
    
    if (!processTitle || processTitle.trim() === '') missingFields.push('Process Title');
    if (!testCategory || testCategory === 'Select Test Category') missingFields.push('Test Category');
    if (!testType) missingFields.push('Test Type');
    if (!model) missingFields.push('AI Model');

    console.log('[DEBUG] Form validation:', {
      processTitle,
      testCategory,
      testType,
      model,
      missingFields
    });

    if (missingFields.length > 0) {
      const missingFieldsText = missingFields.join(', ');
      toast.error(`Please fill in the following required fields: ${missingFieldsText}`);
      return;
    }

    try {
      setIsLoading(true);
      
      // 1. Get file contents from selected files for this process
      const fileContents = [];
      console.log('[DEBUG] Initial data check:', {
        managedFiles: managedFiles?.length || 0,
        selectedFiles: selectedFiles.length,
        processId: process?.id
      });
      
      if (managedFiles && selectedFiles.length > 0) {
        // Find files that are both selected by user and available for this process
        const availableFiles = getAvailableFiles();
        const filesToProcess = availableFiles.filter(file => selectedFiles.includes(file.id));
        
        console.log('[DEBUG] Files to process:', filesToProcess.length);
        
        // Extract content from selected files
        for (const file of filesToProcess) {
          if (file.content && typeof file.content === 'string' && file.content.trim().length > 0) {
            fileContents.push(file.content);
            console.log('[DEBUG] Added file content:', {
              fileName: file.name,
              fileType: file.type,
              contentLength: file.content.length
            });
          } else {
            console.warn('[DEBUG] File has no content or invalid content:', {
              fileName: file.name,
              hasContent: !!file.content,
              contentType: typeof file.content,
              contentLength: file.content?.length || 0
            });
          }
        }
        
        if (selectedFiles.length > 0 && fileContents.length === 0) {
          toast.error('Selected files have no readable content. Please check your uploaded files.');
          return;
        }
      } else {
        console.warn('[DEBUG] No files selected for processing:', {
          hasManagedFiles: !!managedFiles,
          selectedFilesCount: selectedFiles.length
        });
      }

      console.log('[DEBUG] File contents extracted:', {
        selectedFileCount: selectedFiles.length,
        processedFileCount: fileContents.length,
        totalLength: fileContents.reduce((sum, content) => sum + content.length, 0)
      });

      // Show appropriate user message
      if (fileContents.length === 0) {
        if (selectedFiles.length === 0) {
          toast('⚠️ No files selected. Generating generic prompt...', { icon: '⚠️' });
          console.warn('[DEBUG] No files selected - will generate generic prompt');
        } else {
          toast('⚠️ Selected files have no readable content. Generating generic prompt...', { icon: '⚠️' });
          console.warn('[DEBUG] Selected files have no content - will generate generic prompt');
        }
      } else {
        toast(`📁 Using ${fileContents.length} selected file(s) for context-aware prompt generation...`, { icon: '📁' });
        console.log('[DEBUG] Using selected file contents for context-aware prompt generation');
      }

      // 2. Generate custom prompt with LLM using selected file contents
      toast('Generating custom prompt with AI...', { icon: '🤖' });
      
      const promptGenerationData = {
        testType,
        testCategory,
        model,
        testPrompt: testPrompt || 'Generate comprehensive test scenarios for the provided code', // Base test prompt
        fileContents: fileContents, // Include selected file contents array
        session_id: sessionId, // Use the existing session ID for consistency
        process_title: processTitle, // Use the user-entered process title directly
        api_key: apiKey  // API key eklendi
      };

      console.log('[DEBUG] Prompt generation data:', {
        ...promptGenerationData,
        fileContents: `[${fileContents.length} files with total ${fileContents.reduce((sum, content) => sum + content.length, 0)} characters]`,
        api_key: apiKey ? 'SET' : 'NOT SET'  // API key debug
      });

      // Use the regular generate-prompt endpoint with fileContents in JSON body
      const response = await processService.generateCustomPrompt(promptGenerationData);
      
      console.log('[DEBUG] Response from backend:', response);
      
      // Backend response'dan doğru field'ı al
      let generatedCustomPrompt = response.generated_custom_prompt || response.generated_prompt || '';
      
      // Eğer response JSON string ise parse et ve sadece value'yu al
      if (typeof generatedCustomPrompt === 'string' && generatedCustomPrompt.trim().startsWith('{')) {
        try {
          const parsed = JSON.parse(generatedCustomPrompt);
          if (parsed.custom_test_prompt) {
            generatedCustomPrompt = parsed.custom_test_prompt;
            console.log('[DEBUG] Extracted custom_test_prompt value from JSON response');
          }
        } catch (e) {
          console.log('[DEBUG] Response is not JSON, using as-is');
        }
      }
      
      // Eğer response'da açıklama metni varsa temizle
      if (typeof generatedCustomPrompt === 'string') {
        // "Here's a customized prompt..." gibi açıklama metinlerini temizle
        const jsonMatch = generatedCustomPrompt.match(/\{[\s\S]*"custom_test_prompt"[\s\S]*?\}$/);
        if (jsonMatch) {
          try {
            const parsed = JSON.parse(jsonMatch[0]);
            if (parsed.custom_test_prompt) {
              generatedCustomPrompt = parsed.custom_test_prompt;
              console.log('[DEBUG] Extracted custom_test_prompt from mixed response');
            }
          } catch (e) {
            console.log('[DEBUG] Failed to parse extracted JSON, using original response');
          }
        }
      }
      
      if (!generatedCustomPrompt) {
        throw new Error('No prompt generated by backend');
      }
      
      console.log('[DEBUG] Final generatedCustomPrompt preview:', generatedCustomPrompt.substring(0, 200) + '...');
      
      // Generated custom prompt'u state'e kaydet
      setGeneratedCustomPrompt(generatedCustomPrompt);
      
      console.log('[DEBUG] Using global session_id:', sessionId);

      // 3. Create final prompt: generatedCustomPrompt + selectedScoringElements + selectedInstructionElements
      const selectedScoringElements = Object.keys(scoringElements).filter(key => scoringElements[key]);
      const selectedInstructionElements = Object.keys(instructionElements).filter(key => instructionElements[key]);

      let finalCombinedPrompt = generatedCustomPrompt;

      if (selectedScoringElements.length > 0) {
        finalCombinedPrompt += "\n\n## SCORING ELEMENTS TO CONSIDER:\n";
        selectedScoringElements.forEach(element => {
          finalCombinedPrompt += `• ${element}: ${scoringElementDetails[element] || ''}\n`;
        });
      }

      if (selectedInstructionElements.length > 0) {
        finalCombinedPrompt += "\n\n## INSTRUCTION ELEMENTS TO FOLLOW:\n";
        selectedInstructionElements.forEach(element => {
          finalCombinedPrompt += `• ${element}: ${instructionElementDetails[element] || ''}\n`;
        });
      }

      // 5. Add JSON structure at the end (fixed structure)
      const jsonStructure = `

## JSON OUTPUT STRUCTURE:

You MUST respond with a valid JSON object in this exact structure:

\`\`\`json
{
    "TestScenarios": [
        {
            "ScenarioID": "${process?.title || 'Process'}_Test_Scenario_1",
            "Title": "<Scenario Title>",
            "Description": "<Detailed scenario description at least 3 sentences. This is the most important part of the generate test scenario!>",
            "Objective": "<Objective or goal of the scenario>",
            "Category": "${testCategory}",
            "Comments": "<Any inconsistency or additional notes>"
        }
    ]
}
\`\`\`

## Guidelines for JSON Structure:
- Ensure the ScenarioID is dynamic and matches the required format: ${process?.title || 'Process'}_Test_Scenario_X
- Description must be at least 3 sentences and detailed
- Generate maximum test scenarios covering different aspects
- Each scenario must have unique ScenarioID (increment the number)
- Include both positive and negative test cases where appropriate

## Example JSON output:
\`\`\`json
{
    "TestScenarios": [
        {
            "ScenarioID": "${process?.title || 'Process'}_ModelX_Test_Scenario_1",
            "Title": "Verify Login Functionality",
            "Description": "Test the login functionality to ensure that users can successfully log in with valid credentials and are rejected with incorrect credentials. Additionally, verify that the system displays appropriate error messages for failed login attempts to guide users in correcting their input. Furthermore, ensure that the login session is maintained correctly, allowing users to access their accounts seamlessly after a successful login.",
            "Objective": "Validate user authentication mechanism.",
            "Category": "${testCategory}",
            "Comments": ""
        }
    ]
}
\`\`\`

Generate the test scenarios now following the exact JSON structure above.`;

      // Add JSON structure to final prompt
      finalCombinedPrompt += jsonStructure;

      setFinalPrompt(finalCombinedPrompt);

      // 4. Parent component'e gönder (eğer callback varsa)
      if (onGeneratePrompt && typeof onGeneratePrompt === 'function') {
        try {
          const processIdToUse = process?.id || 'test-scenario-generation';
          console.log('[DEBUG] Calling onGeneratePrompt with processId:', processIdToUse);
          console.log('[DEBUG] FormData being sent:', {
            testType,
            testCategory,
            model,
            scoringElements: selectedScoringElements,
            instructionElements: selectedInstructionElements,
            hasFinalPrompt: !!finalCombinedPrompt,
            finalPromptLength: finalCombinedPrompt?.length || 0
          });
          
          const response = await onGeneratePrompt(processIdToUse, {
            testType,
            testCategory,
            model,
            scoringElements: selectedScoringElements,
            instructionElements: selectedInstructionElements,
            generatedCustomPrompt: generatedCustomPrompt,
            finalPrompt: finalCombinedPrompt
          });
          
          console.log('[DEBUG] onGeneratePrompt response:', response);
        } catch (callbackError) {
          console.error('[DEBUG] onGeneratePrompt callback error:', callbackError);
          // Callback hatası olsa bile success mesajı gösterelim çünkü API başarılı
        }
      } else {
        console.log('[DEBUG] onGeneratePrompt callback not provided or not a function');
      }

      toast.success('Custom prompt generated successfully!');
      
    } catch (error) {
      console.error('[DEBUG] Error in handleGeneratePrompt:', error);
      console.error('[DEBUG] Error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      
      // Daha detaylı hata mesajı göster
      let errorMessage = 'Failed to generate custom prompt';
      if (error.message) {
        errorMessage += `: ${error.message}`;
      }
      
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle running test scenario generation with the final prompt
  const handleRunTestScenarioGeneration = async () => {
    if (!finalPrompt || finalPrompt.trim().length === 0) {
      toast.error('Please generate a custom prompt first by clicking "Generate Prompt for Test Scenario Generation"');
      return;
    }

    if (!testType || !testCategory) {
      toast.error('Please select test type and category before running');
      return;
    }

    setIsRunning(true);
    setRunError(null);

    try {
      toast('🚀 Starting test scenario generation...', { icon: '🚀' });

      // Get selected files for processing
      const selectedFilesData = [];
      if (managedFiles && selectedFiles.length > 0) {
        const availableFiles = getAvailableFiles();
        const filesToProcess = availableFiles.filter(file => selectedFiles.includes(file.id));
        
        for (const file of filesToProcess) {
          if (file.content && typeof file.content === 'string' && file.content.trim().length > 0) {
            // Create a File object from the content
            const blob = new Blob([file.content], { type: 'text/plain' });
            const fileObj = new File([blob], file.name, { type: 'text/plain' });
            selectedFilesData.push(fileObj);
          }
        }
      }

      console.log('[DEBUG] Running with data:', {
        finalPromptLength: finalPrompt.length,
        selectedFilesCount: selectedFilesData.length,
        model,
        testType,
        testCategory
      });

      // Call the parent's onRun or onRunProcess if available, otherwise call service directly
      const runFunction = onRun || onRunProcess;
      if (runFunction && typeof runFunction === 'function') {
        const processIdToUse = process?.id || 'test-scenario-generation';
        
        console.log('[DEBUG] Using global sessionId for test scenario generation:', sessionId);
        console.log('[DEBUG] Process title value:', processTitle);
        console.log('[DEBUG] Process title type:', typeof processTitle);
        console.log('[DEBUG] Process title length:', processTitle?.length);
        
        const runConfig = {
          files: selectedFilesData,
          model: model || 'llama3.2:3b',
          finalPrompt: finalPrompt,
          testType: testType,
          testCategory: testCategory,
          process_title: processTitle, // Use the user-entered process title directly
          sessionId: sessionId, // Use global sessionId directly
          apiKey: apiKey // Add API key to config
        };

        console.log('[DEBUG] Calling run function with config:', {
          ...runConfig,
          files: `[${runConfig.files.length} files]`,
          finalPrompt: `[${runConfig.finalPrompt.length} characters]`,
          process_title: runConfig.process_title
        });

        await runFunction(processIdToUse, runConfig);
        toast.success('🎉 Test scenarios generated successfully!');
        
        // Return immediately to prevent fallback from running
        return;
      } else {
        // Fallback to direct service call
        const formData = new FormData();
        formData.append('model', model || 'llama3.2:3b');
        formData.append('final_prompt', finalPrompt);
        formData.append('test_category', testCategory);
        formData.append('test_type', testType);
        formData.append('process_title', processTitle); // Add missing process_title
        formData.append('session_id', `test_session_${Date.now()}`);
        if (apiKey) formData.append('api_key', apiKey); // Add API key

        // Add files to FormData
        selectedFilesData.forEach((file, index) => {
          formData.append('files', file);
        });

        const response = await processService.runTestScenarioGeneration(formData);
        
        if (response.status === 'success') {
          toast.success('🎉 Test scenarios generated successfully!');
          console.log('[DEBUG] Test scenarios generated:', response);
        } else {
          throw new Error(response.message || 'Failed to generate test scenarios');
        }
      }

    } catch (error) {
      console.error('[DEBUG] Error in handleRunTestScenarioGeneration:', error);
      setRunError(error.message);
      toast.error(`Failed to generate test scenarios: ${error.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleModelChange = (e) => {
    const selectedModel = e.target.value;
    console.log(`[TestScenarioGenerationForm] Model changed to: ${selectedModel}`);
    setModel(selectedModel);
    setModelInfo(useModelInfo(selectedModel));
  };

  // Notify parent about form state changes for main button
  useEffect(() => {
    if (onFormStateChange && typeof onFormStateChange === 'function') {
      const canRun = !!(generatedCustomPrompt && finalPrompt && testType && testCategory);
      onFormStateChange({
        canRun,
        isRunning,
        handleRun: handleRunTestScenarioGeneration,
        sessionId: sessionId
      });
    }
  }, [generatedCustomPrompt, finalPrompt, testType, testCategory, isRunning, sessionId, onFormStateChange]);

  return (
    <div className="max-w-2xl mx-auto p-4">
      <form className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700">Process Title <span className="text-red-500">*</span></label>
          <input
            type="text"
            value={processTitle}
            onChange={(e) => setProcessTitle(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            placeholder="Enter a descriptive title for this test scenario process"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Test Category</label>
          <select
            value={testCategory}
            onChange={(e) => setTestCategory(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
            {categoryNames.map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Test Type</label>
          <select
            value={testType}
            onChange={(e) => setTestType(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            disabled={!testCategory || testCategory === 'Select Test Category'}
          >
            <option value="">Select Test Type</option>
            {availableTestTypes.map(type => (
              <option key={type.name} value={type.name}>{type.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">AI Model</label>
          <select
            value={model}
            onChange={handleModelChange}
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
                        <strong>⚠️ Large content detected!</strong> The system will automatically use <strong>qwen2.5:7b-1m</strong> model for optimal processing of large documents.
                      </p>
                    )}
                    {!exceedsLimit && (
                      <p className="mt-1">Content size is within normal limits. Your selected model will be used.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div className="mt-2 text-sm text-blue-600 font-semibold">
            Currently selected model: {model || 'llama3.2:3b'}
          </div>

          {modelInfo.length > 0 && (
            <div className="mt-4 text-sm text-gray-600">
              <h4 className="font-medium">Model Bilgisi:</h4>
              <ul className="list-disc pl-5">
                {modelInfo.map((info, index) => (
                  <li key={index}>{info}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Select Input Files Section */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Select Input Files</label>
          {(() => {
            const availableFiles = getAvailableFiles();
            
            if (!availableFiles || availableFiles.length === 0) {
              return (
                <div className="mt-2 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-sm text-yellow-700">
                    📁 No files available. Please upload files in the File Management tab first.
                  </p>
                </div>
              );
            }

            return (
              <div className="mt-2 p-4 bg-gray-50 rounded-md">
                <div className="flex justify-between items-center mb-3">
                  <p className="text-sm text-gray-600">
                    Available files: {availableFiles.length} | Selected: {selectedFiles.length}
                  </p>
                  <div className="space-x-2">
                    <button
                      type="button"
                      onClick={handleSelectAllFiles}
                      className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Select All
                    </button>
                    <button
                      type="button"
                      onClick={handleDeselectAllFiles}
                      className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700"
                    >
                      Clear All
                    </button>
                  </div>
                </div>
                
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {availableFiles.map(file => (
                    <div key={file.id} className="flex items-center">
                      <input
                        type="checkbox"
                        id={`file-${file.id}`}
                        checked={selectedFiles.includes(file.id)}
                        onChange={() => handleFileSelection(file.id)}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <label htmlFor={`file-${file.id}`} className="ml-2 text-sm text-gray-700 flex-1 cursor-pointer">
                        <span className="font-medium">{file.name}</span>
                        {file.type && (
                          <span className="ml-2 text-xs text-gray-500">({file.type})</span>
                        )}
                        {file.content && (
                          <span className="ml-2 text-xs text-green-600">
                            ({file.content.length} chars)
                          </span>
                        )}
                      </label>
                    </div>
                  ))}
                </div>
                
                {selectedFiles.length > 0 && (
                  <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded">
                    <p className="text-sm text-blue-700">
                      ✅ {selectedFiles.length} file(s) selected for context-aware prompt generation
                    </p>
                  </div>
                )}
              </div>
            );
          })()}
        </div>

        {/* Display Test Prompt */}
        {/* {testPrompt && (
          <div className="mt-4">
            <h3 className="text-lg font-medium text-gray-900">Selected Test Type's Base Prompt</h3>
            <div className="mt-2 p-4 bg-gray-50 rounded-md">
              <p className="text-sm text-gray-600">{testPrompt}</p>
            </div>
          </div>
        )} */}
        {/* Editable Test Prompt */}
        {testPrompt && (
          <div className="mt-4">
            <h3 className="text-lg font-medium text-gray-900">Selected Test Type's Base Prompt</h3>
            {isEditingPrompt ? (
              <div className="mt-2 p-4 bg-gray-50 rounded-md space-y-3">
                <textarea
                  className="w-full p-2 border border-gray-300 rounded-md text-sm text-gray-700"
                  value={editedPrompt}
                  onChange={(e) => setEditedPrompt(e.target.value)}
                  rows={10}
                />
                <div className="flex space-x-2">
                  <button
                    onClick={handleSavePrompt}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-2 p-4 bg-gray-50 rounded-md space-y-3">
                <p className="text-sm text-gray-600 whitespace-pre-wrap">{testPrompt}</p>
                <button
                  onClick={() => {
                    setIsEditingPrompt(true);
                    setEditedPrompt(testPrompt);
                  }}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Edit
                </button>
              </div>
            )}
          </div>
        )}


        {/* Scoring Elements Section */}
        <div className="space-y-4">
          {scoringElementDetails && Object.keys(scoringElementDetails).length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900">Test Scoring Elements</h3>
              {isLoading ? (
                <div className="mt-4 text-gray-600">Loading scoring elements...</div>
              ) : error ? (
                <div className="mt-4 text-red-600">{error}</div>
              ) : Object.keys(scoringElements).length > 0 ? (
                <div className="mt-4 space-y-2">
                  {Object.entries(scoringElements).map(([element, checked]) => (
                    <div key={element} className="relative">
                      <label 
                        className="flex items-center group"
                        onMouseEnter={() => setActiveTooltip(element)}
                        onMouseLeave={() => setActiveTooltip(null)}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => handleScoringElementChange(element)}
                          className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="ml-2 text-sm text-gray-600">{element}</span>
                        {activeTooltip === element && scoringElementDetails[element] && (
                          <div className="absolute left-0 bottom-full mb-2 w-64 p-2 bg-gray-800 text-white text-sm rounded shadow-lg">
                            {scoringElementDetails[element]}
                          </div>
                        )}
                      </label>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 text-gray-600">No scoring elements available for the selected test type.</div>
              )}
            </div>
          )}

          {/* New Section: Scoring Elements Details */}
          {/* {Object.keys(scoringElementDetails).length > 0 && (
            <div className="mt-4">
              <h3 className="text-lg font-medium text-gray-900">Scoring Elements Details</h3>
              <div className="mt-2 p-4 bg-gray-50 rounded-md">
                {Object.entries(scoringElementDetails).map(([key, description]) => (
                  <p key={key} className="text-sm text-gray-600"><strong>{key}:</strong> {description}</p>
                ))}
              </div>
            </div>
          )} */}

          {/* Instruction Elements Section */}
          <div>
            {testType ? (
              instructionElementDetails && Object.keys(instructionElementDetails).length > 0 ? (
              <div>
                <h3 className="text-lg font-medium text-gray-900">Test Instruction Elements</h3>
                <div className="mt-4 space-y-2">
                  {Object.entries(instructionElements).map(([element, checked]) => (
                    <div key={element} className="relative">
                      <label 
                        className="flex items-center group"
                        onMouseEnter={() => setActiveTooltip(element)}
                        onMouseLeave={() => setActiveTooltip(null)}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => handleInstructionElementChange(element)}
                          className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="ml-2 text-sm text-gray-600">{element}</span>
                        {activeTooltip === element && instructionElementDetails[element] && (
                          <div className="absolute left-0 bottom-full mb-2 w-64 p-2 bg-gray-800 text-white text-sm rounded shadow-lg">
                            {instructionElementDetails[element]}
                          </div>
                        )}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
              ) : (
                <div className="mt-4 text-gray-600">No instruction elements available for the selected test type.</div>
              )
            ) : null}
          </div>



          {/* New Section: Instruction Elements Details */}
          {/* {Object.keys(instructionElementDetails).length > 0 && (
            <div className="mt-4">
              <h3 className="text-lg font-medium text-gray-900">Instruction Elements Details</h3>
              <div className="mt-2 p-4 bg-gray-50 rounded-md">
                {Object.entries(instructionElementDetails).map(([key, description]) => (
                  <p key={key} className="text-sm text-gray-600"><strong>{key}:</strong> {description}</p>
                ))}
              </div>
            </div>
          )} */}
        </div>

        <div className="pt-4 space-y-4">
          <button
            type="button"
            onClick={handleGeneratePrompt}
            disabled={isLoading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Generating...' : 'Generate Prompt for Test Scenario Generation'}
          </button>


        </div>

        {/* Generated Prompt Success Message */}
        {generatedCustomPrompt && (
          <div className="mt-6">
            <div className="p-4 bg-green-50 border border-green-200 rounded-md">
              <h3 className="text-lg font-medium text-green-800 mb-2">✅ Custom Prompt Generated Successfully</h3>
              <p className="text-sm text-green-700 mb-3">
                The final combined prompt has been generated and is now available in the <strong>Process Prompt</strong> section.
                You can view and edit it by switching to the <strong>Prompt</strong> tab.
              </p>
              <p className="text-sm text-green-700 font-medium">
                🚀 Ready to generate test scenarios! Click the "Run Process" button above.
              </p>
            </div>
          </div>
        )}

        {/* Run Error Message */}
        {runError && (
          <div className="mt-6">
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <h3 className="text-lg font-medium text-red-800 mb-2">❌ Test Scenario Generation Failed</h3>
              <p className="text-sm text-red-700">
                {runError}
              </p>
            </div>
          </div>
        )}


      </form>
    </div>
  );
}

TestScenarioGenerationForm.propTypes = {
  onGeneratePrompt: PropTypes.func,
  onRun: PropTypes.func,
  onRunProcess: PropTypes.func,
  process: PropTypes.object,
  managedFiles: PropTypes.array,
  fileProcessMappings: PropTypes.object,
  onFormStateChange: PropTypes.func,
  sessionId: PropTypes.string.isRequired // Add sessionId prop validation
};
