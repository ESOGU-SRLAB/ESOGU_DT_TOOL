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
import RobotTestExecutionPanel from './processes/RobotTestExecutionPanel';
import TestReportingForm from './processes/TestReportingForm';
import TestClosureForm from './processes/TestClosureForm';
import CodeReviewForm from './processes/CodeReviewForm';
import RequirementAnalysisForm from './processes/RequirementAnalysisForm';
import TestPlanningForm from './processes/TestPlanningForm';
import EnvironmentSetupForm from './processes/EnvironmentSetupForm';
import ApiSettingsModal from './ApiSettingsModal';
import PipelineFileSelector from './PipelineFileSelector';
import GlobalAIConfig from './GlobalAIConfig';
import TestExecutionMethodSelector from './TestExecutionMethodSelector';
import PipelineResultsPanel from './PipelineResultsPanel';

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
  pipelineResults = {},
  onRun,
  onSetOutput, // Add this new prop
  onRegisterPipelineExecutor, // Pipeline executor kaydı için
  validationError,
  output,
  outputs,
  isPipelineEnabled = true, // Auto-selection için eklendi
  onTogglePipeline = () => {}, // Auto-selection için eklendi
  managedFiles,
  fileProcessMappings,
  onFileProcessMapping,
  onFileDelete,
  sessionId,
  selectedFileIds,
  setSelectedFileIds,
  onGeneratePrompt,
  pipelineModel = 'qwen2.5-7b-instruct-1m',
  onPipelineModelChange,
  testExecutionMethod = 'ai',
  onTestExecutionMethodChange,
  dockerAvailable = false,
  dockerConfig = { language: 'python', packages: '', timeout: 300 },
  onDockerConfigChange,
  robotConfig = { robotType: 'generic', simulationPrecision: 'medium' },
  onRobotConfigChange,
  ros2Available = false,
  ros2Config = { visualCount: 0, timeout: 120 },
  onRos2ConfigChange,
  ros2ContainerName = '',
  remoteRos2Config = { timeout: 300 },
  onRemoteRos2ConfigChange,
}) {
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [tempPrompt, setTempPrompt] = useState('');
  const [showHelp, setShowHelp] = useState(false);
  const [isApiSettingsOpen, setIsApiSettingsOpen] = useState(false);
  
  // Pipeline expanded states no longer needed — per-step cards removed
  
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

  // Pipeline çalıştırma fonksiyonu - her process türü için doğru handler'ı çağırır
  const executePipelineStep = useCallback(async (processId, pipelineConfigs) => {
    console.log(`[TabPanel] Executing pipeline step: ${processId}`);
    
    // Process-specific handler'ları kontrol et
    switch (processId) {
      case 'test-scenario-generation':
        if (testScenarioFormState.handleRun) {
          console.log('[TabPanel] Running test-scenario-generation via form handler');
          await testScenarioFormState.handleRun();
          return 'completed';
        }
        break;
        
      case 'test-case-generation':
        if (testCaseFormState.handleRun) {
          console.log('[TabPanel] Running test-case-generation via form handler');
          await testCaseFormState.handleRun();
          return 'completed';
        }
        break;
        
      case 'test-case-optimization':
        if (testCaseOptimizationFormState.handleRun) {
          console.log('[TabPanel] Running test-case-optimization via form handler');
          await testCaseOptimizationFormState.handleRun();
          return 'completed';
        }
        break;
        
      case 'test-execution':
        if (testExecutionFormState.handleRun) {
          console.log('[TabPanel] Running test-execution via form handler');
          await testExecutionFormState.handleRun();
          return 'completed';
        }
        break;
        
      case 'test-reporting':
        if (testReportingFormState.handleRun) {
          console.log('[TabPanel] Running test-reporting via form handler');
          await testReportingFormState.handleRun();
          return 'completed';
        }
        break;
        
      case 'test-closure':
        if (testClosureFormState.handleRun) {
          console.log('[TabPanel] Running test-closure via form handler');
          await testClosureFormState.handleRun();
          return 'completed';
        }
        break;
        
      default:
        // Bu process için özel handler yok, App.jsx'teki fallback mantığı kullanılacak
        console.log(`[TabPanel] No custom handler for ${processId}, falling back to App.jsx logic`);
        return false;
    }
    
    // Handler bulunamadı veya çalışmadı
    console.warn(`[TabPanel] Handler for ${processId} not available yet`);
    return false;
  }, [
    testScenarioFormState,
    testCaseFormState,
    testCaseOptimizationFormState,
    testExecutionFormState,
    testReportingFormState,
    testClosureFormState
  ]);

  // Pipeline executor'u parent'a kaydet
  useEffect(() => {
    if (onRegisterPipelineExecutor) {
      console.log('[TabPanel] Registering pipeline executor with parent');
      onRegisterPipelineExecutor(executePipelineStep);
    }
  }, [onRegisterPipelineExecutor, executePipelineStep]);

  // Aktif tab değiştiğinde veya ilk açılışta base prompt'u otomatik yükle
  useEffect(() => {
    if (
      activeTab &&
      activeTab !== 'files' &&
      activeTab !== 'pipeline' &&
      activeTab !== 'test-case-optimization' && // Test Case Optimization kendi prompt'unu yönetir
      !processPrompts[activeTab]
    ) {
      // Code review, requirement-analysis, test-planning, environment-setup, test-execution, test-reporting, test-closure için endpoint
      if (activeTab === 'code-review' || activeTab === 'requirement-analysis' || activeTab === 'test-planning' || 
          activeTab === 'environment-setup' || activeTab === 'test-execution' || 
          activeTab === 'test-reporting' || activeTab === 'test-closure') {
        let endpoint;
        if (activeTab === 'code-review') {
          endpoint = '/api/prompts/code-review';
        } else if (activeTab === 'requirement-analysis') {
          endpoint = '/api/prompts/requirement-analysis';
        } else if (activeTab === 'test-planning') {
          endpoint = '/api/prompts/test-planning';
        } else if (activeTab === 'environment-setup') {
          endpoint = '/api/prompts/environment-setup';
        } else if (activeTab === 'test-execution') {
          endpoint = '/api/prompts/test-execution';
        } else if (activeTab === 'test-reporting') {
          endpoint = '/api/prompts/test-reporting';
        } else if (activeTab === 'test-closure') {
          endpoint = '/api/prompts/test-closure';
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
        fetch(`/api/prompts/${activeTab}`)
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
          endpoint = '/api/prompts/code-review';
        } else if (processId === 'requirement-analysis') {
          endpoint = '/api/prompts/requirement-analysis';
        } else if (processId === 'test-planning') {
          endpoint = '/api/prompts/test-planning';
        } else if (processId === 'environment-setup') {
          endpoint = '/api/prompts/environment-setup';
        } else if (processId === 'test-execution') {
          endpoint = '/api/prompts/test-execution';
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
      const response = await fetch(`/api/prompts/${processId}`);
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
          endpoint = '/api/prompts/code-review';
        } else if (processId === 'requirement-analysis') {
          endpoint = '/api/prompts/requirement-analysis';
        } else if (processId === 'test-planning') {
          endpoint = '/api/prompts/test-planning';
        } else if (processId === 'environment-setup') {
          endpoint = '/api/prompts/environment-setup';
        } else if (processId === 'test-execution') {
          endpoint = '/api/prompts/test-execution';
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
      const response = await fetch(`/api/prompts/${processId}`);
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

        {/* Test Execution Method Selector - Only for test-execution */}
        {processId === 'test-execution' && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Execution Method</h3>
            <TestExecutionMethodSelector
              method={testExecutionMethod}
              onMethodChange={onTestExecutionMethodChange}
              dockerAvailable={dockerAvailable}
              dockerConfig={dockerConfig}
              onDockerConfigChange={onDockerConfigChange}
              robotConfig={robotConfig}
              onRobotConfigChange={onRobotConfigChange}
              ros2Available={ros2Available}
              ros2Config={ros2Config}
              onRos2ConfigChange={onRos2ConfigChange}
              ros2ContainerName={ros2ContainerName}
              remoteRos2Config={remoteRos2Config}
              onRemoteRos2ConfigChange={onRemoteRos2ConfigChange}
              selectedProcesses={selectedProcesses}
            />
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
              ) : processId === 'test-execution' && testExecutionMethod === 'robot' ? (
                <RobotTestExecutionPanel
                  sessionId={sessionId}
                  disabled={isDisabled}
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
                  onSetFormState={processId === 'test-closure' ? setTestClosureFormState : undefined}
                  onTestCaseGeneration={
                    processId === 'test-case-generation' ? setTestCaseFormState : 
                    processId === 'test-execution' ? setTestExecutionFormState : 
                    processId === 'test-reporting' ? setTestReportingFormState :
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
      // For all other processes including test-reporting and test-closure, use MongoDB prompt
      promptText = currentPrompt?.prompt_text || currentPrompt?.content || process?.defaultPrompt || '';
    }
    
    const isDisabled = pipelineStatus[processId] === 'running';

    // Debug logging for test-scenario-generation and test-closure
    if (processId === 'test-scenario-generation') {
      console.log('[TabPanel] renderPromptSection for test-scenario-generation:', {
        currentPrompt,
        promptTextLength: promptText?.length || 0,
        hasPromptText: !!promptText
      });
    }
    
    if (processId === 'test-closure') {
      console.log('[TabPanel] renderPromptSection for test-closure:', {
        testClosureFormState,
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
      {/* Header bar — API Settings + pipeline lock indicator */}
      <div className="bg-white border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
          <div className="flex items-center space-x-4">
            {/* Locked-steps badge */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-200">
              <svg className="h-3.5 w-3.5 text-indigo-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
              <span className="text-xs font-medium text-indigo-700">11 steps active</span>
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
            Configure steps individually or use Global AI Config
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
                  <button
                    onClick={() => {
                      // Eğer herhangi bir process çalışıyorsa ve aktif tab o değilse, geçişe izin verme
                      if (anyProcessRunning && tab.id !== activeTab && isCurrentTabRunning) {
                        alert('Bir süreç çalışırken başka bir taba geçemezsiniz.');
                        return;
                      }
                      setActiveTab(tab.id);
                    }}
                    data-tab={tab.id}
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
                {/* Pipeline File Selection & Mapping - EN ÜSTTE */}
                <PipelineFileSelector
                  managedFiles={managedFiles}
                  fileProcessMappings={fileProcessMappings}
                  selectedProcesses={selectedProcesses}
                  processes={processes}
                  onFileProcessMapping={onFileProcessMapping}
                  onFileDelete={onFileDelete}
                  onFileUpload={onFileUpload}
                />

                {/* Global AI Model — single dropdown, applied to every step */}
                <GlobalAIConfig
                  selectedModel={pipelineModel}
                  onModelChange={onPipelineModelChange}
                />

                {/* Test Execution Method — AI / Docker / Robot Simulation */}
                <TestExecutionMethodSelector
                  method={testExecutionMethod}
                  onMethodChange={onTestExecutionMethodChange}
                  dockerAvailable={dockerAvailable}
                  dockerConfig={dockerConfig}
                  onDockerConfigChange={onDockerConfigChange}
                  robotConfig={robotConfig}
                  onRobotConfigChange={onRobotConfigChange}
                  ros2Available={ros2Available}
                  ros2Config={ros2Config}
                  onRos2ConfigChange={onRos2ConfigChange}
                  ros2ContainerName={ros2ContainerName}
                  remoteRos2Config={remoteRos2Config}
                  onRemoteRos2ConfigChange={onRemoteRos2ConfigChange}
                  selectedProcesses={selectedProcesses}
                />

                {/* Pipeline Progress — visible once any step has a status */}
                {Object.values(pipelineStatus).some(s => s && s !== 'idle') && (
                  <div className="border rounded-lg bg-white shadow-sm overflow-hidden">
                    <div className="px-4 py-3 bg-gradient-to-r from-indigo-50 to-blue-50 border-b border-indigo-100 flex items-center justify-between">
                      <h3 className="font-semibold text-gray-900 text-sm">Pipeline Progress</h3>
                      <span className="text-xs text-gray-500">
                        {Object.values(pipelineStatus).filter(s => s === 'completed').length} / {processes.filter(p => selectedProcesses.has(p.id)).length} steps done
                      </span>
                    </div>
                    <div className="divide-y divide-gray-100">
                      {processes.filter(p => selectedProcesses.has(p.id)).map(process => {
                        const status = pipelineStatus[process.id];
                        const statusMeta = {
                          'pending':   { dot: 'bg-gray-300',  text: 'text-gray-400', label: 'Pending'   },
                          'running':   { dot: 'bg-blue-500 animate-pulse', text: 'text-blue-600', label: 'Running…' },
                          'completed': { dot: 'bg-green-500', text: 'text-green-700', label: 'Done'     },
                          'error':     { dot: 'bg-red-500',   text: 'text-red-700',   label: 'Failed'   },
                        }[status] || { dot: 'bg-gray-200', text: 'text-gray-400', label: '—' };

                        return (
                          <div key={process.id} className="flex items-center px-4 py-2 gap-3">
                            <span className={`h-2 w-2 rounded-full flex-shrink-0 ${statusMeta.dot}`} />
                            <span className="flex-1 text-sm text-gray-700">{process.name}</span>
                            <span className={`text-xs font-medium ${statusMeta.text}`}>{statusMeta.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

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
                    
                    // Special handling for Test Closure
                    if (activeTab === 'test-closure') {
                      console.log('[TabPanel] Test Closure button clicked');
                      console.log('[TabPanel] testClosureFormState:', testClosureFormState);
                      if (testClosureFormState.handleRun && typeof testClosureFormState.handleRun === 'function') {
                        console.log('[TabPanel] Calling testClosureFormState.handleRun()');
                        testClosureFormState.handleRun();
                      } else {
                        console.warn('[TabPanel] handleRun is not available or not a function');
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
                    // PIPELINE MODE
                    // All 11 steps are always active and auto-configured —
                    // no manual configuration gate needed.

                    // Warn about unmapped files (optional — proceed anyway)
                    const unmappedFiles = managedFiles.filter(file => 
                      !fileProcessMappings[file.id] || fileProcessMappings[file.id].length === 0
                    );
                    
                    if (unmappedFiles.length > 0) {
                      const unmappedNames = unmappedFiles.map(f => f.name).join(', ');
                      const proceed = confirm(
                        `⚠️ Warning: ${unmappedFiles.length} file(s) are not mapped to any step:\n\n${unmappedNames}\n\nDo you want to continue without mapping them?`
                      );
                      if (!proceed) return;
                    }
                    
                    // All validated — start pipeline
                    console.log('[TabPanel] Starting pipeline');
                    onRun(null);
                  }
                }}
                disabled={
                  (activeTab === 'pipeline' && Array.from(selectedProcesses).some(id => pipelineStatus[id] === 'running')) ||
                  (activeTab === 'test-scenario-generation' && (!testScenarioFormState.canRun || testScenarioFormState.isRunning)) ||
                  (activeTab === 'test-case-generation' && (!testCaseFormState.canRun || testCaseFormState.isRunning)) ||
                  (activeTab === 'test-case-optimization' && !testCaseOptimizationFormState.canRun && !testCaseOptimizationFormState.isRunning) ||
                  (activeTab === 'test-execution' && (!testExecutionFormState.canRun || testExecutionFormState.isRunning)) ||
                  (activeTab === 'test-reporting' && (!testReportingFormState.canRun || testReportingFormState.isRunning)) ||
                  (activeTab === 'test-closure' && (!testClosureFormState.canRun || testClosureFormState.isRunning)) ||
                  (activeTab !== 'pipeline' && activeTab !== 'test-scenario-generation' && activeTab !== 'test-case-generation' && activeTab !== 'test-case-optimization' && activeTab !== 'test-execution' && activeTab !== 'test-reporting' && activeTab !== 'test-closure' && activeTab !== 'test-code-generation' && pipelineStatus[activeTab] === 'running')
                }
                className={clsx(
                  "w-full py-3 px-4 rounded-md text-white font-medium transition-colors shadow-sm flex items-center justify-center",
                  (activeTab === 'pipeline' && Array.from(selectedProcesses).some(id => pipelineStatus[id] === 'running')) ||
                  (activeTab === 'test-scenario-generation' && (!testScenarioFormState.canRun || testScenarioFormState.isRunning)) ||
                  (activeTab === 'test-case-generation' && (!testCaseFormState.canRun || testCaseFormState.isRunning)) ||
                  (activeTab === 'test-case-optimization' && !testCaseOptimizationFormState.canRun && !testCaseOptimizationFormState.isRunning) ||
                  (activeTab === 'test-execution' && (!testExecutionFormState.canRun || testExecutionFormState.isRunning)) ||
                  (activeTab === 'test-closure' && (!testClosureFormState.canRun || testClosureFormState.isRunning)) ||
                  (activeTab !== 'pipeline' && activeTab !== 'test-scenario-generation' && activeTab !== 'test-case-generation' && activeTab !== 'test-case-optimization' && activeTab !== 'test-execution' && activeTab !== 'test-code-generation' && activeTab !== 'test-closure' && pipelineStatus[activeTab] === 'running')
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
                ) : activeTab === 'test-closure' ? (
                  testClosureFormState.isRunning ? (
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
              {activeTab === 'pipeline' ? 'Pipeline Results' : 
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
            ) : activeTab === 'pipeline' ? (
              <PipelineResultsPanel
                processes={processes}
                pipelineStatus={pipelineStatus}
                pipelineResults={pipelineResults}
              />
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
