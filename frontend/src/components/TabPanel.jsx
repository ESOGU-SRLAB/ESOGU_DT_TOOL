import React, { useState, useEffect, useCallback } from 'react';
import { clsx } from 'clsx';
import { QuestionMarkCircleIcon } from '@heroicons/react/24/outline';
import FileUpload from './FileUpload';
import PromptEditor from './PromptEditor';
import OutputPanel from './OutputPanel';
import TestScenarioGenerationForm from './processes/TestScenarioGenerationForm';
import TestCaseGenerationForm from './processes/TestCaseGenerationForm';
import TestCaseOptimization from './processes/TestCaseOptimization';
import TestCodeGeneration from './processes/TestCodeGeneration';
import TestExecutionForm from './processes/TestExecutionForm';
import TestReportingForm from './processes/TestReportingForm';
import TestClosureForm from './processes/TestClosureForm';
import CodeReviewForm from './processes/CodeReviewForm';
import RequirementAnalysisForm from './processes/RequirementAnalysisForm';
import TestPlanningForm from './processes/TestPlanningForm';
import EnvironmentSetupForm from './processes/EnvironmentSetupForm';
import ApiSettingsModal from './ApiSettingsModal';

export default function TabPanel({
  processes,
  activeTab,
  setActiveTab,
  selectedProcesses,
  processOrigins = {}, // Auto özelliği için eklendi
  onProcessSelect,
  processFiles,
  onFileUpload,
  onAIModelUpdate,
  onOutputFormatUpdate,
  onEnvironmentNameUpdate,
  aiModels,
  environmentNames,
  outputFormats,
  processPrompts,
  onPromptUpdate,
  pipelineStatus,
  onRun,
  onSetOutput, // Add this new prop
  validationError,
  output,
  outputs,
  isPipelineEnabled = true, // Auto-selection için eklendi
  onTogglePipeline = () => {}, // Auto-selection için eklendi
  managedFiles,
  fileProcessMappings,
  onFileProcessMapping,
  onFileDelete,
  sessionId, // Add sessionId prop
  selectedFileIds,
  setSelectedFileIds,
  onGeneratePrompt  // Add this line
}) {
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [tempPrompt, setTempPrompt] = useState('');
  const [showHelp, setShowHelp] = useState(false);
  const [isApiSettingsOpen, setIsApiSettingsOpen] = useState(false);
  
  // Test Scenario Generation form state tracking for main button
  const [testScenarioFormState, setTestScenarioFormState] = useState({
    canRun: false,
    isRunning: false,
    handleRun: null
  });

  // Test Case Generation form state tracking for main button
  const [testCaseFormState, setTestCaseFormState] = useState({
    canRun: false,
    isRunning: false,
    handleRun: null
  });

  // Test Case Generation combined prompt state
  const [testCaseGenerationCombinedPrompt, setTestCaseGenerationCombinedPrompt] = useState('');

  // Test Case Optimization form state tracking for main button
  const [testCaseOptimizationFormState, setTestCaseOptimizationFormState] = useState({
    canRun: false,
    isRunning: false,
    handleRun: null,
    prompt: ''
  });

  // Test Case Optimization results state for sidebar
  const [testCaseOptimizationResults, setTestCaseOptimizationResults] = useState(null);

  // Test Execution form state tracking for main button
  const [testExecutionFormState, setTestExecutionFormState] = useState({
    canRun: false,
    isRunning: false,
    handleRun: null
  });

  // Test Reporting form state tracking for main button
  const [testReportingFormState, setTestReportingFormState] = useState({
    canRun: false,
    isRunning: false,
    handleRun: null
  });

  // Test Closure form state tracking for main button
  const [testClosureFormState, setTestClosureFormState] = useState({
    canRun: false,
    isRunning: false,
    handleRun: null
  });

  // Stable callback for Test Case Optimization form state changes
  const handleTestCaseOptimizationStateChange = useCallback((handler) => {
    setTestCaseOptimizationFormState(prev => ({ ...prev, ...handler }));
  }, []);

  // Stable callback for Test Case Optimization results
  const handleTestCaseOptimizationResults = useCallback((results) => {
    setTestCaseOptimizationResults(results);
  }, []);

  // Stable callback for Test Case Optimization run function updates
  const handleTestCaseOptimizationRunFunction = useCallback((runFn) => {
    // canRun is true if we have a valid function (either run or stop)
    const canRun = !!runFn;
    setTestCaseOptimizationFormState(prev => ({ 
      ...prev, 
      handleRun: runFn,
      canRun: canRun
    }));
    console.log('TabPanel - TestCaseOptimization run function updated:', {
      hasFunction: !!runFn,
      canRun: canRun
    });
  }, []);

  // Stable callback for Test Case Optimization prompt changes
  const handleTestCaseOptimizationPromptChange = useCallback((prompt) => {
    setTestCaseOptimizationFormState(prev => ({ ...prev, prompt }));
  }, []);

  // Stable callback for Test Case Optimization running state changes
  const handleTestCaseOptimizationRunningStateChange = useCallback((isRunning) => {
    console.log('TabPanel - TestCaseOptimization running state changed:', isRunning);
    setTestCaseOptimizationFormState(prev => ({ 
      ...prev, 
      isRunning: isRunning,
      canRun: prev.handleRun !== null // Always allow if we have a function
    }));
  }, []);

  // Stable callback for Test Case Optimization loading state changes
  const handleTestCaseOptimizationLoadingChange = useCallback((loading) => {
    setTestCaseOptimizationFormState(prev => ({ ...prev, isRunning: loading }));
  }, []);

  // Aktif tab değiştiğinde veya ilk açılışta base prompt'u otomatik yükle
  useEffect(() => {
    if (
      activeTab &&
      activeTab !== 'files' &&
      activeTab !== 'pipeline' &&
      activeTab !== 'test-case-optimization' && // Test Case Optimization kendi prompt'unu yönetir
      !processPrompts[activeTab]
    ) {
      // Code review, requirement-analysis, test-planning, environment-setup, test-execution, test-reporting ve test-closure için yeni endpoint ve veri yapısı
      if (activeTab === 'code-review' || activeTab === 'requirement-analysis' || activeTab === 'test-planning' || activeTab === 'environment-setup' || activeTab === 'test-execution' || activeTab === 'test-reporting' || activeTab === 'test-closure') {
        let endpoint;
        if (activeTab === 'code-review') {
          endpoint = 'http://localhost:8000/api/prompts/code-review';
        } else if (activeTab === 'requirement-analysis') {
          endpoint = 'http://localhost:8000/api/prompts/requirement-analysis';
        } else if (activeTab === 'test-planning') {
          endpoint = 'http://localhost:8000/api/prompts/test-planning';
        } else if (activeTab === 'environment-setup') {
          endpoint = 'http://localhost:8000/api/prompts/environment-setup';
        } else if (activeTab === 'test-execution') {
          endpoint = 'http://localhost:8000/api/prompts/test-execution';
        } else if (activeTab === 'test-reporting') {
          endpoint = 'http://localhost:8000/api/prompts/test-reporting';
        } else if (activeTab === 'test-closure') {
          endpoint = 'http://localhost:8000/api/prompts/test-closure';
        }
        
        fetch(endpoint)
          .then(res => res.json())
          .then(data => {
            if (data && (data.prompt_text || data.base_prompt)) {
              onPromptUpdate(activeTab, {
                prompt_text: data.prompt_text || data.base_prompt,
                process_type: activeTab,
                isTemporary: false
              });
            }
          })
          .catch(err => {
            console.error('Base prompt fetch error:', err);
          });
      } else {
        // Diğer süreçler için eski mantık
        fetch(`http://localhost:8000/api/prompts/${activeTab}`)
          .then(res => res.json())
          .then(data => {
            // prompt_text varsa onu kullan, yoksa prompt'u kullan
            if (data && (data.prompt_text || data.prompt)) {
              onPromptUpdate(activeTab, {
                prompt_text: data.prompt_text || data.prompt,
                process_type: activeTab,
                isTemporary: false
              });
            }
          })
          .catch(err => {
            console.error('Base prompt fetch error:', err);
          });
      }
    }
  }, [activeTab]);

  const handleProcessToggle = (processId) => {
    onProcessSelect(processId);
    setActiveTab(processId);
  };

  const handleEditPrompt = async (processId) => {
    // Test case optimization için özel durum
    if (processId === 'test-case-optimization') {
      setEditingPrompt(processId);
      setTempPrompt(testCaseOptimizationFormState.prompt || '');
      return;
    }
    
    const currentPrompt = processPrompts[processId];
    // Eğer kullanıcı daha önce bir prompt kaydettiyse onu göster
    if (currentPrompt?.prompt_text) {
      setEditingPrompt(processId);
      setTempPrompt(currentPrompt.prompt_text);
      return;
    }
    // Code review, requirement-analysis, test-planning, environment-setup veya test-execution için yeni endpoint ve veri yapısı
    if (processId === 'code-review' || processId === 'requirement-analysis' || processId === 'test-planning' || processId === 'environment-setup' || processId === 'test-execution') {
      try {
        let endpoint;
        if (processId === 'code-review') {
          endpoint = 'http://localhost:8000/api/prompts/code-review';
        } else if (processId === 'requirement-analysis') {
          endpoint = 'http://localhost:8000/api/prompts/requirement-analysis';
        } else if (processId === 'test-planning') {
          endpoint = 'http://localhost:8000/api/prompts/test-planning';
        } else if (processId === 'environment-setup') {
          endpoint = 'http://localhost:8000/api/prompts/environment-setup';
        } else if (processId === 'test-execution') {
          endpoint = 'http://localhost:8000/api/prompts/test-execution';
        }
        const response = await fetch(endpoint);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'Base prompt fetch failed');
        }
        const data = await response.json();
        setEditingPrompt(processId);
        setTempPrompt(data.prompt_text || data.base_prompt);
      } catch (error) {
        setEditingPrompt(processId);
        setTempPrompt(`Error: ${error.message}`);
      }
      return;
    }
    // Diğer süreçler için eski mantık
    try {
      const response = await fetch(`http://localhost:8000/api/prompts/${processId}`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Base prompt fetch failed');
      }
      const data = await response.json();
      setEditingPrompt(processId);
      setTempPrompt(data.prompt_text || data.prompt);
    } catch (error) {
      setEditingPrompt(processId);
      setTempPrompt(`Error: ${error.message}`);
    }
  };
  
  const handleSavePrompt = (processId) => {
    // Test case optimization için özel durum
    if (processId === 'test-case-optimization') {
      // TestCaseOptimizationForm'un processPrompt state'ini güncelle
      setTestCaseOptimizationFormState(prev => ({ ...prev, prompt: tempPrompt }));
      setEditingPrompt(null);
      alert('Test Case Optimization prompt saved for this session.');
      return;
    }
    
    onPromptUpdate(processId, {
      prompt_text: tempPrompt,
      process_type: processId,
      isTemporary: true
    });
    setEditingPrompt(null);
    alert('Prompt saved locally. This will be used only for this session.');
  };
  
  const handleBackToBasePrompt = async (processId) => {
    // Test case optimization için özel durum
    if (processId === 'test-case-optimization') {
      // Default prompt'a geri dön
      const defaultPrompt = `You are given two test cases, each with a certain set of fields:
- Title
- Description  
- Objective

You will decide whether these two test cases are "contextually the same" based on the following criteria:

1. If both have the same Title (case-insensitive) OR their Titles are substantially similar in meaning,
2. AND they have either the same or very similar Description and/or Objective,
3. AND they serve essentially the same testing purpose for the same or very closely related scenarios,
4. THEN you should conclude that these two test cases are the same.
5. The order of importance Description > Objective > Title.

Otherwise, they are considered different.

Return your response **only** in valid JSON with the following format:

{
  "is_same": <true or false>
}

Where:
- is_same = true if the test cases meet the criteria above
- is_same = false otherwise

Important:
- Do not provide any additional text outside the JSON object.
- Do not explain your reasoning, only provide the final JSON response.`;
      
      setTestCaseOptimizationFormState(prev => ({ ...prev, prompt: defaultPrompt }));
      setEditingPrompt(null);
      alert('Restored to default Test Case Optimization prompt.');
      return;
    }
    
    // Code review, requirement-analysis, test-planning, environment-setup veya test-execution için yeni endpoint ve veri yapısı
    if (processId === 'code-review' || processId === 'requirement-analysis' || processId === 'test-planning' || processId === 'environment-setup' || processId === 'test-execution') {
      try {
        let endpoint;
        if (processId === 'code-review') {
          endpoint = 'http://localhost:8000/api/prompts/code-review';
        } else if (processId === 'requirement-analysis') {
          endpoint = 'http://localhost:8000/api/prompts/requirement-analysis';
        } else if (processId === 'test-planning') {
          endpoint = 'http://localhost:8000/api/prompts/test-planning';
        } else if (processId === 'environment-setup') {
          endpoint = 'http://localhost:8000/api/prompts/environment-setup';
        } else if (processId === 'test-execution') {
          endpoint = 'http://localhost:8000/api/prompts/test-execution';
        }
        const response = await fetch(endpoint);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'Base prompt fetch failed');
        }
        const data = await response.json();
        setTempPrompt(data.prompt_text || data.base_prompt);
      } catch (error) {
        alert('Base prompt alınamadı: ' + error.message);
      }
      return;
    }
    // Diğer süreçler için eski mantık
    try {
      const response = await fetch(`http://localhost:8000/api/prompts/${processId}`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Base prompt fetch failed');
      }
      const data = await response.json();
      setTempPrompt(data.prompt);
    } catch (error) {
      alert('Base prompt alınamadı: ' + error.message);
    }
  };

  const handleRun = (processId, files) => {
    // processId bilgisini çıktıya eklemek için
    onRun(processId, files);
  };

  const tabs = [
    { id: 'files', name: 'File Management' },
    { id: 'pipeline', name: 'Pipeline' },
    ...processes.map(process => ({
      id: process.id,
      name: process.name
    }))
  ];

    const ProcessFormComponents = {
    'code-review': CodeReviewForm,
    'requirement-analysis': RequirementAnalysisForm,
    'test-scenario-generation': TestScenarioGenerationForm,
    'test-case-generation': TestCaseGenerationForm,
    'test-case-optimization': TestCaseOptimization,
    'test-code-generation': TestCodeGeneration,
    'test-execution': TestExecutionForm,
    'test-reporting': TestReportingForm,
    'test-closure': TestClosureForm,
    'test-planning': TestPlanningForm,
    'environment-setup': EnvironmentSetupForm,
  };

  const renderHelpContent = () => (
    <ul className="list-disc pl-5 text-blue-700 space-y-1">
      {activeTab === 'files' ? (
        <>
          <li>You can upload all your files here</li>
          <li>Select processes to be used for each file</li>
          <li>You can delete or edit files</li>
        </>
      ) : activeTab === 'pipeline' ? (
        <>
          <li>Select processes using the checkboxes above</li>
          <li>Processes will run in the shown order</li>
          <li>Make sure all required inputs are provided</li>
          <li>Click "Start Pipeline" button</li>
        </>
      ) : (
        <>
          <li>Navigate between sections using the tabs above</li>
          <li>Complete each section before running the process</li>
          <li>Required fields are marked with an asterisk (*)</li>
          <li>Click "Run Process" button</li>
        </>
      )}
    </ul>
  );

  const renderProcessContent = (processId) => {
    const process = processes.find(p => p.id === processId);
    const FormComponent = ProcessFormComponents[processId];
    const isDisabled = pipelineStatus[processId] === 'running';
    return (
      <div className="space-y-6">
        {/* Process Description */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Process Description</h3>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="space-y-2 text-gray-600">
              {process?.details.map((detail, index) => (
                <div key={`detail-${index}`}>
                  {typeof detail === 'string' ? (
                    <p>{detail}</p>
                  ) : detail.type === 'table' ? (
                    <div className="mt-4">
                      <h4 className="font-medium mb-2">{detail.title}</h4>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Test Type</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Methodology</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {detail.data.map((row, idx) => (
                              <tr key={idx}>
                                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{row.testType}</td>
                                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">{row.category}</td>
                                <td className="px-4 py-4 text-sm text-gray-500">{row.methodology}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* File Selection Section - Hide for test-case-optimization only */}
        {processId !== 'test-case-optimization' && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Select Input Files</h3>
          <div className="space-y-4">
            {managedFiles.length === 0 ? (
              <p className="text-gray-500">No files uploaded yet. Please upload files in File Management.</p>
            ) : (
              <div className="space-y-2">
                {managedFiles.map(file => (
                  <div 
                    key={file.id} 
                    className="flex items-center p-3 hover:bg-gray-50 rounded-lg border border-gray-200"
                  >
                    <input
                      type="checkbox"
                      checked={fileProcessMappings[file.id]?.includes(processId) || false}
                      onChange={() => {
                        const currentProcesses = fileProcessMappings[file.id] || [];
                        // Eğer dosya henüz seçili değilse ve seçilmeye çalışılıyorsa
                        if (!currentProcesses.includes(processId)) {
                          // Seçilmeye çalışılan dosyanın türünü kontrol et
                          const fileType = file.type;
                          // Aktif süreç için seçilmiş olan diğer dosyaları bul
                          const selectedFiles = managedFiles.filter(f => 
                            fileProcessMappings[f.id]?.includes(processId)
                          );
                          
                          // UML veya Source Code kısıtlaması kontrol edilecek
                          if (fileType === 'UML') {
                            // Eğer zaten bir Source Code seçilmişse
                            const hasSourceCode = selectedFiles.some(f => f.type === 'Source Code');
                            if (hasSourceCode) {
                              window.alert('Bu süreç için zaten Source Code seçilmiş. UML ve Source Code aynı anda seçilemez.');
                              return;
                            }
                          } else if (fileType === 'Source Code') {
                            // Eğer zaten bir UML seçilmişse
                            const hasUML = selectedFiles.some(f => f.type === 'UML');
                            if (hasUML) {
                              window.alert('Bu süreç için zaten UML seçilmiş. UML ve Source Code aynı anda seçilemez.');
                              return;
                            }
                          }
                        }
                        
                        // Eğer kısıtlama yoksa, normal işleme devam et
                        const updatedProcesses = currentProcesses.includes(processId)
                          ? currentProcesses.filter(p => p !== processId)
                          : [...currentProcesses, processId];
                        onFileProcessMapping(file.id, updatedProcesses);
                      }}
                      className="h-4 w-4 text-indigo-600 rounded border-gray-300"
                      disabled={isDisabled}
                    />
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-700">{file.name}</p>
                      <p className="text-xs text-gray-500">{file.type}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        )}

        {/* Process Configuration */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Process Configuration</h3>
          <div className="bg-gray-50 rounded-lg p-4">
            {FormComponent ? (
              processId === 'test-case-optimization' ? (
                <TestCaseOptimization 
                  onPromptChange={handleTestCaseOptimizationPromptChange}
                  onRunFunction={handleTestCaseOptimizationRunFunction}
                  onLoadingChange={handleTestCaseOptimizationLoadingChange}
                  onRunningStateChange={handleTestCaseOptimizationRunningStateChange}
                  onOptimizationResults={handleTestCaseOptimizationResults}
                />
              ) : (
                <FormComponent 
                  process={process}
                  onAIModelUpdate={onAIModelUpdate}
                  onOutputFormatUpdate={onOutputFormatUpdate}
                  onEnvironmentNameUpdate={onEnvironmentNameUpdate}
                  aiModels={aiModels}
                  environmentNames={environmentNames}
                  outputFormats={outputFormats}
                  disabled={isDisabled}
                  managedFiles={managedFiles}
                  fileProcessMappings={fileProcessMappings}
                  onRun={onRun} // Change from onRunProcess to onRun to match component expectation
                  onSetOutput={onSetOutput} // Pass the new onSetOutput handler
                  sessionId={sessionId} // Pass global sessionId to forms
                  onFormStateChange={processId === 'test-scenario-generation' ? setTestScenarioFormState : undefined}
                  onTestCaseGeneration={
                    processId === 'test-case-generation' ? setTestCaseFormState : 
                    processId === 'test-execution' ? setTestExecutionFormState : 
                    processId === 'test-reporting' ? setTestReportingFormState :
                    processId === 'test-closure' ? setTestClosureFormState :
                    undefined
                  }
                  onTestCaseOptimization={processId === 'test-case-optimization' ? handleTestCaseOptimizationStateChange : undefined}
                  onPromptChange={processId === 'test-case-optimization' ? handleTestCaseOptimizationPromptChange : undefined}
                  currentPrompt={processId === 'test-case-optimization' ? (testCaseOptimizationFormState.prompt || '') : 
                               processId === 'test-code-generation' ? processPrompts[processId] : undefined}
                  onOptimizationResults={processId === 'test-case-optimization' ? handleTestCaseOptimizationResults : undefined}
                  onFinalPromptChange={processId === 'test-case-generation' ? setTestCaseGenerationCombinedPrompt : undefined}
                  onPromptUpdate={processId === 'test-code-generation' ? (newPrompt) => onPromptUpdate(processId, newPrompt) : undefined}
                  onGeneratePrompt={async (processIdFromForm, formData) => {
                    try {
                      console.log('[TabPanel] onGeneratePrompt called with:', { processIdFromForm, processId, hasFormData: !!formData });
                      // Use the processId from the form if provided, otherwise use the current processId
                      const finalProcessId = processIdFromForm || processId;
                      const response = await onGeneratePrompt(finalProcessId, formData);
                      console.log('[TabPanel] onGeneratePrompt response:', response);
                      
                      // For test-scenario-generation, App.jsx already handles the state update
                      // For other processes, we need to call onPromptUpdate
                      if (finalProcessId !== 'test-scenario-generation' && response?.prompt) {
                        onPromptUpdate(finalProcessId, response.prompt);
                      }
                      return response;
                    } catch (error) {
                      console.error('Error generating prompt:', error);
                      throw error;
                    }
                  }}
                />
              )
            ) : (
              <p className="text-gray-600">No specific configuration options available for {process?.name}</p>
            )}
          </div>
        </div>

        {/* Prompt Section */}
        {renderPromptSection(processId)}
      </div>
    );
  };

  const renderPromptSection = (processId) => {
    const process = processes.find(p => p.id === processId);
    const currentPrompt = processPrompts[processId];
    
    // For test-case-generation, use the combined prompt from the form
    let promptText;
    if (processId === 'test-case-generation' && testCaseGenerationCombinedPrompt) {
      promptText = testCaseGenerationCombinedPrompt;
    } else if (processId === 'test-case-optimization' && testCaseOptimizationFormState.prompt) {
      promptText = testCaseOptimizationFormState.prompt;
    } else {
      promptText = currentPrompt?.prompt_text || currentPrompt?.content || process?.defaultPrompt || '';
    }
    
    const isDisabled = pipelineStatus[processId] === 'running';

    // Debug logging only for test-scenario-generation
    if (processId === 'test-scenario-generation') {
      console.log('[TabPanel] renderPromptSection for test-scenario-generation:', {
        currentPrompt,
        promptTextLength: promptText?.length || 0,
        hasPromptText: !!promptText
      });
    }

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">Process Prompt</h3>
        {editingPrompt === processId ? (
          <div className="space-y-3">
            <PromptEditor
              value={tempPrompt}
              onChange={setTempPrompt}
              placeholder={`Customize prompt for ${process?.name}...`}
              disabled={isDisabled}
              className={isDisabled ? 'opacity-50 pointer-events-none' : ''}
            />
            <div className="flex space-x-2">
              <button
                onClick={() => handleSavePrompt(processId)}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                disabled={isDisabled}
                style={isDisabled ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
              >
                Save
              </button>
              <button
                onClick={() => setEditingPrompt(null)}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
                disabled={isDisabled}
                style={isDisabled ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
              >
                Cancel
              </button>
              <button
                onClick={() => handleBackToBasePrompt(processId)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                disabled={isDisabled}
                style={isDisabled ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
              >
                Back to Base Prompt
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-600 whitespace-pre-wrap">
                {promptText || (processId === 'test-case-generation' ? 
                  "Please select a test scenario process above to load the prompt." : 
                  processId === 'test-code-generation' ?
                  "Generate executable test code based on unique test cases, source code analysis, and environment setup configuration." :
                  "Prompt bulunamadı.")}
              </p>
            </div>
            <button
              onClick={() => handleEditPrompt(processId)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
              disabled={isDisabled}
              style={isDisabled ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
            >
              Edit
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full w-full">
      {/* Enable Auto-selection toggle - yeni eklendi */}
      <div className="bg-white border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="pipelineToggle"
                checked={isPipelineEnabled}
                onChange={() => onTogglePipeline(!isPipelineEnabled)}
                className="h-4 w-4 text-indigo-600 rounded"
              />
              <label htmlFor="pipelineToggle" className="text-sm text-gray-700">
                Enable Auto-selection
              </label>
            </div>
            
            {/* API Settings Button */}
            <button
              onClick={() => setIsApiSettingsOpen(true)}
              className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <svg className="h-4 w-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m0 0a2 2 0 012 2m-2-2a2 2 0 00-2 2m2-2V5a2 2 0 00-2-2m0 0V3m0 2H9M7 7a2 2 0 012-2m0 0a2 2 0 012 2m-2-2V3m0 4H3m4 0a2 2 0 012 2m-2-2v6a2 2 0 002 2m-2-2a2 2 0 00-2-2m2 2h4m-4 0a2 2 0 01-2-2m2 2v4m0-4h4" />
              </svg>
              API Settings
            </button>
          </div>
          <div className="text-xs text-gray-500">
            Auto-selected processes will be highlighted in yellow
          </div>
        </div>

        {/* Tabs Navigation */}
        <div className="flex space-x-1 overflow-x-auto px-4">
          {tabs.map((tab) => {
            const isDisabled = pipelineStatus[tab.id] === 'running';
            // Herhangi bir process çalışıyorsa ve aktif tab o değilse, tab geçişini engelle
            const anyProcessRunning = Object.values(pipelineStatus).includes('running');
            const isCurrentTabRunning = pipelineStatus[activeTab] === 'running';
            return (
              <div
                key={tab.id}
                className={clsx(
                  'relative group',
                  activeTab === tab.id && 'bg-indigo-50 rounded-t-lg'
                )}
              >
                <div className="flex items-center px-3 py-2">
                  {tab.id !== 'pipeline' && tab.id !== 'files' && (
                    <input
                      type="checkbox"
                      checked={selectedProcesses.has(tab.id)}
                      onChange={() => {
                        // Eğer herhangi bir process çalışıyorsa ve aktif tab o değilse, geçişe izin verme
                        if (anyProcessRunning && tab.id !== activeTab && isCurrentTabRunning) {
                          alert('Bir süreç çalışırken başka bir taba geçemezsiniz.');
                          return;
                        }
                        handleProcessToggle(tab.id);
                      }}
                      className={clsx(
                        "h-4 w-4 rounded mr-2",
                        processOrigins[tab.id] === 'auto' ? 'text-yellow-500 border-yellow-500' : 'text-indigo-600 border-gray-300'
                      )}
                      disabled={isDisabled && activeTab !== tab.id}
                    />
                  )}
                  <button
                    onClick={() => {
                      // Eğer herhangi bir process çalışıyorsa ve aktif tab o değilse, geçişe izin verme
                      if (anyProcessRunning && tab.id !== activeTab && isCurrentTabRunning) {
                        alert('Bir süreç çalışırken başka bir taba geçemezsiniz.');
                        return;
                      }
                      setActiveTab(tab.id);
                    }}
                    className={clsx(
                      'text-sm font-medium whitespace-nowrap transition-colors',
                      activeTab === tab.id
                        ? 'text-indigo-700'
                        : 'text-gray-500 hover:text-gray-700',
                      // Sadece aktif olmayan tablar için opacity-50 uygula
                      isDisabled && activeTab !== tab.id ? 'opacity-50 cursor-not-allowed' : ''
                    )}
                    disabled={isDisabled && activeTab !== tab.id}
                  >
                    {tab.name}
                  </button>
                  {/* Auto etiketi - yeni eklendi */}
                  {processOrigins[tab.id] === 'auto' && (
                    <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                      Auto
                    </span>
                  )}
                </div>
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel */}
        <div className="w-1/2 flex flex-col min-h-0 border-r border-gray-200">
          {/* Header */}
          <div className="flex-none h-16 px-6 flex items-center justify-between border-b border-gray-200 bg-white">
            <h2 className="text-xl font-bold text-gray-900">
              {activeTab === 'files' ? 'File Management' :
               activeTab === 'pipeline' ? 'Pipeline Configuration' : 
               processes.find(p => p.id === activeTab)?.name}
            </h2>
            <button
              onClick={() => setShowHelp(!showHelp)}
              className="text-gray-500 hover:text-gray-700 transition-colors"
              title="Show Help"
            >
              <QuestionMarkCircleIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {showHelp && (
              <div className="bg-blue-50 p-4 rounded-lg mb-4">
                <h3 className="font-medium text-blue-800 mb-2">
                  {activeTab === 'files' ? 'File Management Guide' :
                   activeTab === 'pipeline' ? 'Pipeline Guide' : 
                   'Process Guide'}
                </h3>
                {renderHelpContent()}
              </div>
            )}

            {activeTab === 'files' ? (
              <FileUpload
                onFileUpload={onFileUpload}
                managedFiles={managedFiles}
                onFileDelete={onFileDelete}
                processes={processes}
              />
            ) : activeTab === 'pipeline' ? (
              <div className="space-y-4">
                {processes
                  .filter(p => selectedProcesses.has(p.id))
                  .map((process, index) => (
                    <div key={process.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="text-gray-500">{index + 1}.</span>
                          <h3 className="font-medium">{process.name}</h3>
                          {/* Auto etiketi pipeline görünümü için - yeni eklendi */}
                          {processOrigins[process.id] === 'auto' && (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              Auto
                            </span>
                          )}
                        </div>
                        <span className={clsx(
                          'text-sm px-2 py-1 rounded-full',
                          pipelineStatus[process.id] === 'completed' ? 'bg-green-100 text-green-800' :
                          pipelineStatus[process.id] === 'running' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        )}>
                          {pipelineStatus[process.id] || 'Pending'}
                        </span>
                      </div>
                    </div>
                  ))}

                {validationError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
                    <h4 className="text-red-700 font-medium mb-2">Missing Required Inputs:</h4>
                    <pre className="text-red-600 text-sm whitespace-pre-wrap">{validationError}</pre>
                  </div>
                )}
              </div>
            ) : (
              renderProcessContent(activeTab)
            )}
          </div>

          {/* Footer */}
          <div className="flex-none h-16 px-6 flex items-center border-t border-gray-200 bg-white">
            {activeTab !== 'files' && (
              <button
                onClick={() => {
                  if (activeTab !== 'pipeline') {
                    // Special handling for Test Scenario Generation
                    if (activeTab === 'test-scenario-generation') {
                      if (testScenarioFormState.handleRun && typeof testScenarioFormState.handleRun === 'function') {
                        testScenarioFormState.handleRun();
                      }
                      return;
                    }
                    
                    // Special handling for Test Case Generation
                    if (activeTab === 'test-case-generation') {
                      if (testCaseFormState.handleRun && typeof testCaseFormState.handleRun === 'function') {
                        testCaseFormState.handleRun();
                      }
                      return;
                    }
                    
                    // Special handling for Test Case Optimization
                    if (activeTab === 'test-case-optimization') {
                      console.log('TabPanel - Run Process clicked for test-case-optimization:', {
                        canRun: testCaseOptimizationFormState.canRun,
                        isRunning: testCaseOptimizationFormState.isRunning,
                        handleRun: typeof testCaseOptimizationFormState.handleRun,
                        formState: testCaseOptimizationFormState
                      });
                      
                      if (testCaseOptimizationFormState.handleRun && typeof testCaseOptimizationFormState.handleRun === 'function') {
                        testCaseOptimizationFormState.handleRun();
                      }
                      return;
                    }
                    
                    // Special handling for Test Execution
                    if (activeTab === 'test-execution') {
                      if (testExecutionFormState.handleRun && typeof testExecutionFormState.handleRun === 'function') {
                        testExecutionFormState.handleRun();
                      }
                      return;
                    }
                    
                    // Special handling for Test Reporting
                    if (activeTab === 'test-reporting') {
                      if (testReportingFormState.handleRun && typeof testReportingFormState.handleRun === 'function') {
                        testReportingFormState.handleRun();
                      }
                      return;
                    }
                    
                    // Special handling for Test Code Generation
                    if (activeTab === 'test-code-generation') {
                      onRun(activeTab);
                      return;
                    }
                    
                    // Standard handling for other processes
                    const foundProcess = processes.find(p => p.id === activeTab);
                    const relevantFiles = managedFiles.filter(file => 
                      fileProcessMappings[file.id]?.includes(activeTab)
                    );
                    
                    // File validation for other processes
                    if (relevantFiles.length === 0) {
                      window.alert('Please select files for this process');
                      return;
                    }
                    
                    if (foundProcess) {
                      onRun(activeTab);
                    }
                  } else {
                    onRun();
                  }
                }}
                disabled={
                  (activeTab === 'pipeline' && selectedProcesses.size === 0) ||
                  (activeTab === 'test-scenario-generation' && (!testScenarioFormState.canRun || testScenarioFormState.isRunning)) ||
                  (activeTab === 'test-case-generation' && (!testCaseFormState.canRun || testCaseFormState.isRunning)) ||
                  (activeTab === 'test-case-optimization' && !testCaseOptimizationFormState.canRun && !testCaseOptimizationFormState.isRunning) ||
                  (activeTab === 'test-execution' && (!testExecutionFormState.canRun || testExecutionFormState.isRunning)) ||
                  (activeTab === 'test-reporting' && (!testReportingFormState.canRun || testReportingFormState.isRunning)) ||
                  (activeTab !== 'pipeline' && activeTab !== 'test-scenario-generation' && activeTab !== 'test-case-generation' && activeTab !== 'test-case-optimization' && activeTab !== 'test-execution' && activeTab !== 'test-reporting' && activeTab !== 'test-code-generation' && pipelineStatus[activeTab] === 'running')
                }
                className={clsx(
                  "w-full py-3 px-4 rounded-md text-white font-medium transition-colors shadow-sm flex items-center justify-center",
                  (activeTab === 'pipeline' && selectedProcesses.size === 0) || 
                  (activeTab === 'test-scenario-generation' && (!testScenarioFormState.canRun || testScenarioFormState.isRunning)) ||
                  (activeTab === 'test-case-generation' && (!testCaseFormState.canRun || testCaseFormState.isRunning)) ||
                  (activeTab === 'test-case-optimization' && !testCaseOptimizationFormState.canRun && !testCaseOptimizationFormState.isRunning) ||
                  (activeTab === 'test-execution' && (!testExecutionFormState.canRun || testExecutionFormState.isRunning)) ||
                  (activeTab !== 'pipeline' && activeTab !== 'test-scenario-generation' && activeTab !== 'test-case-generation' && activeTab !== 'test-case-optimization' && activeTab !== 'test-execution' && activeTab !== 'test-code-generation' && pipelineStatus[activeTab] === 'running')
                    ? "bg-gray-300 cursor-not-allowed" 
                    : "bg-indigo-600 hover:bg-indigo-700"
                )}
              >
                {activeTab === 'pipeline' ? (
                  Array.from(selectedProcesses).some(id => pipelineStatus[id] === 'running') ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 714 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      GENERATING
                    </>
                  ) : (
                    'Start Pipeline'
                  )
                ) : activeTab === 'test-scenario-generation' ? (
                  testScenarioFormState.isRunning ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0 1 4 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Generating Test Scenarios...
                    </>
                  ) : (
                    'Run Process'
                  )
                ) : activeTab === 'test-case-generation' ? (
                  testCaseFormState.isRunning ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0 1 4 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Generating Test Cases...
                    </>
                  ) : (
                    'Run Process'
                  )
                ) : activeTab === 'test-case-optimization' ? (
                  testCaseOptimizationFormState.isRunning ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0 1 4 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Stop Process
                    </>
                  ) : (
                    'Run Process'
                  )
                ) : activeTab === 'test-execution' ? (
                  testExecutionFormState.isRunning ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0 1 4 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Executing Tests...
                    </>
                  ) : (
                    'Run Process'
                  )
                ) : activeTab === 'test-reporting' ? (
                  testReportingFormState.isRunning ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0 1 4 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Generating Report...
                    </>
                  ) : (
                    'Generate Report'
                  )
                ) : (
                  pipelineStatus[activeTab] === 'running' ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0 1 4 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      GENERATING
                    </>
                  ) : (
                    'Run Process'
                  )
                )}
              </button>
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div className="w-1/2 flex flex-col min-h-0">
          {/* Header */}
          <div className="flex-none h-16 px-6 flex items-center justify-between border-b border-gray-200 bg-white">
            <h2 className="text-xl font-medium text-gray-900">
              {activeTab === 'pipeline' ? 'Pipeline Output' : 
               activeTab === 'files' ? '' : 
               `${processes.find(p => p.id === activeTab)?.name || activeTab} Output`}
            </h2>
            <div className="flex items-center space-x-2">
              {output && output.content && (
                <span className="text-xs font-medium text-gray-500">
                  {output.timestamp ? new Date(output.timestamp).toLocaleString() : ''}
                </span>
              )}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === 'files' ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-400 text-center">This is file management view. The output will be displayed when running processes.</p>
              </div>
            ) : (
              <OutputPanel 
                output={output}
                outputs={outputs}
                activeTab={activeTab}
                processes={processes}
                outputFormats={outputFormats}
                hideFooter={true}
                hideHeader={true}
                testCaseOptimizationResults={testCaseOptimizationResults}
              />
            )}
          </div>

          {/* Footer */}
          <div className="flex-none h-16 px-6 flex items-center border-t border-gray-200 bg-white">
            {activeTab !== 'files' && (
              <button
                className={`w-full py-3 px-4 rounded-md text-white font-medium transition-colors shadow-sm ${
                  !output || output.status === 'sample'
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-green-600 hover:bg-green-700'
                }`}
                disabled={!output || output.status === 'sample'}
              >
                Install Output
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* API Settings Modal */}
      <ApiSettingsModal 
        isOpen={isApiSettingsOpen}
        onClose={() => setIsApiSettingsOpen(false)}
      />
    </div>
  );
}