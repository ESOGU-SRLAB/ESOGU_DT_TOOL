import React, { useState, useEffect, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';
import { toast } from 'react-hot-toast';
import { 
  DocumentCheckIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import { useSelector } from 'react-redux';
import { useModels } from '../../hooks/useModels';

// Process metadata with icons, labels, and colors
const PROCESS_METADATA = {
  test_scenario_generation: { 
    icon: '📝', 
    label: 'Test Scenarios',
    shortLabel: 'Scenarios',
    color: 'blue',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700'
  },
  test_case_generation: { 
    icon: '🧪', 
    label: 'Test Cases',
    shortLabel: 'Cases',
    color: 'green',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700'
  },
  test_case_optimization: { 
    icon: '⚡', 
    label: 'Test Case Optimization',
    shortLabel: 'Optimization',
    color: 'yellow',
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-700'
  },
  test_code_generation: { 
    icon: '💻', 
    label: 'Test Code Generation',
    shortLabel: 'Code Gen',
    color: 'purple',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-700'
  },
  test_execution: { 
    icon: '🚀', 
    label: 'Test Execution',
    shortLabel: 'Execution',
    color: 'red',
    bgColor: 'bg-red-100',
    textColor: 'text-red-700'
  },
  code_review: { 
    icon: '🔍', 
    label: 'Code Review',
    shortLabel: 'Review',
    color: 'indigo',
    bgColor: 'bg-indigo-100',
    textColor: 'text-indigo-700'
  }
};

// Model metadata for display
const MODEL_METADATA = {
  'gemini-2.5-pro': { icon: '🤖', shortName: 'Gemini Pro', color: 'blue' },
  'gemini-2.5-flash': { icon: '⚡', shortName: 'Gemini Flash', color: 'blue' },
  'gemini-1.5-pro': { icon: '🤖', shortName: 'Gemini 1.5', color: 'blue' },
  'llama-3.2-3b-instruct': { icon: '🦙', shortName: 'Llama 3.2', color: 'purple' },
  'llama3.2:1b': { icon: '🦙', shortName: 'Llama 1B', color: 'purple' },
  'gpt-4': { icon: '🧠', shortName: 'GPT-4', color: 'green' },
  'gpt-3.5-turbo': { icon: '💬', shortName: 'GPT-3.5', color: 'green' },
  'default': { icon: '🔮', shortName: 'AI Model', color: 'gray' }
};

/**
 * TestClosureForm Component
 * Handles AI-powered test cycle closure report generation
 */
export default function TestClosureForm({ onComplete, onSetOutput, onSetFormState }) {
  const { models, loading: modelsLoading } = useModels();
  const apiKeys = useSelector((state) => state.apiKey.apiKeys);
  
  // State management
  const [sessions, setSessions] = useState([]);
  const [selectedSessions, setSelectedSessions] = useState([]);
  const [expandedSessions, setExpandedSessions] = useState([]); // Track expanded session cards
  const [selectedModel, setSelectedModel] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingMetrics, setFetchingMetrics] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [report, setReport] = useState(null);
  const [qualityEvaluation, setQualityEvaluation] = useState(null); // Store quality metrics
  const hasFetchedRef = useRef(false); // Track if initial fetch has been done
  
  // Prompt preview and edit state
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [promptPreview, setPromptPreview] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');
  const [isLoadingPrompt, setIsLoadingPrompt] = useState(false);
  const [pendingGeneration, setPendingGeneration] = useState(false);

  // Auto-select first available model when models load
  useEffect(() => {
    if (!modelsLoading && models.length > 0 && !selectedModel) {
      const localModel = models.find(m => m.type === 'local');
      const modelToSelect = localModel || models[0];
      setSelectedModel(modelToSelect.key);
      console.log('[TestClosure] Auto-selected model:', modelToSelect.key, modelToSelect.name);
    }
  }, [models, modelsLoading, selectedModel]);

  // Fetch available sessions on mount
  useEffect(() => {
    fetchAvailableSessions();
  }, []);

  /**
   * Fetch available sessions from backend
   */
  const fetchAvailableSessions = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        '/api/test-closure/available-sessions'
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        // Sort sessions by timestamp or created_at in descending order (newest first)
        const sortedSessions = (data.sessions || []).sort((a, b) => {
          // Try timestamp first (from Test Reporting), fallback to created_at (from Test Closure)
          const dateA = new Date(a.timestamp || a.created_at || 0);
          const dateB = new Date(b.timestamp || b.created_at || 0);
          return dateB - dateA; // Descending order (newest first)
        });
        
        setSessions(sortedSessions);
        // Show toast only once (not on strict mode re-mount)
        if (!hasFetchedRef.current) {
          toast.success(`Found ${data.total_count} sessions`);
          hasFetchedRef.current = true;
        }
      } else {
        toast.error('Failed to fetch sessions');
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
      toast.error(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Toggle session selection
   */
  const toggleSession = (sessionId) => {
    setSelectedSessions(prev => 
      prev.includes(sessionId)
        ? prev.filter(id => id !== sessionId)
        : [...prev, sessionId]
    );
  };

  /**
   * Toggle session expand/collapse
   */
  const toggleSessionExpand = (sessionId) => {
    setExpandedSessions(prev => {
      if (prev.includes(sessionId)) {
        return prev.filter(id => id !== sessionId);
      } else {
        return [...prev, sessionId];
      }
    });
  };

  /**
   * Get model metadata for display
   */
  const getModelMetadata = (modelName) => {
    if (!modelName) return MODEL_METADATA.default;
    
    // Try exact match first
    if (MODEL_METADATA[modelName]) {
      return MODEL_METADATA[modelName];
    }
    
    // Try partial match
    for (const [key, meta] of Object.entries(MODEL_METADATA)) {
      if (modelName.includes(key) || key.includes(modelName)) {
        return meta;
      }
    }
    
    return MODEL_METADATA.default;
  };

  /**
   * Get process metadata for display
   */
  const getProcessMetadata = (processType) => {
    return PROCESS_METADATA[processType] || {
      icon: '❓',
      label: processType,
      shortLabel: processType,
      color: 'gray',
      bgColor: 'bg-gray-100',
      textColor: 'text-gray-700'
    };
  };

  /**
   * Format timestamp for display
   */
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown date';
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return 'Invalid date';
    }
  };

  /**
   * Select all sessions
   */
  const selectAllSessions = () => {
    setSelectedSessions(sessions.map(s => s.session_id));
  };

  /**
   * Clear all selections
   */
  const clearSelections = () => {
    setSelectedSessions([]);
  };

  /**
   * Calculate metrics only (without AI report)
   */
  const calculateMetrics = async () => {
    if (selectedSessions.length === 0) {
      toast.error('Please select at least one session');
      return;
    }

    setFetchingMetrics(true);
    setMetrics(null);

    try {
      const response = await fetch('/api/test-closure/metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_ids: selectedSessions
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setMetrics(data.metrics);
        toast.success('Metrics calculated successfully');
      } else {
        toast.error(data.error || 'Failed to calculate metrics');
      }
    } catch (error) {
      console.error('Error calculating metrics:', error);
      toast.error(`Error: ${error.message}`);
    } finally {
      setFetchingMetrics(false);
    }
  };

  /**
   * Load prompt and show editor
   */
  const loadPrompt = async (shouldGenerateAfter = false) => {
    console.log('[TestClosure] loadPrompt called, shouldGenerateAfter:', shouldGenerateAfter);
    
    if (selectedSessions.length === 0) {
      toast.error('Please select at least one session');
      return false;
    }

    console.log('[TestClosure] Loading prompt for sessions:', selectedSessions);
    setIsLoadingPrompt(true);
    setPendingGeneration(shouldGenerateAfter);

    try {
      const response = await fetch('/api/test-closure/preview-prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_ids: selectedSessions
        })
      });

      console.log('[TestClosure] Response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to load prompt');
      }

      const data = await response.json();
      console.log('[TestClosure] Response data:', data);

      if (data.success) {
        console.log('[TestClosure] Setting prompt, length:', data.prompt?.length);
        setPromptPreview(data.prompt);
        setCustomPrompt(data.prompt);
        setShowPromptEditor(true);
        console.log('[TestClosure] showPromptEditor set to true');
        
        const chunkingNote = data.uses_chunking ? ' (using chunking for large dataset)' : '';
        toast.success(`Prompt loaded${chunkingNote} - ${data.estimated_tokens} tokens estimated`);
        return true;
      } else {
        toast.error('Failed to load prompt');
        return false;
      }
    } catch (error) {
      console.error('[TestClosure] Error loading prompt:', error);
      toast.error(`Error: ${error.message}`);
      return false;
    } finally {
      setIsLoadingPrompt(false);
      console.log('[TestClosure] loadPrompt finished');
    }
  };

  /**
   * Internal function to actually generate the report (after prompt review)
   * Defined first because generateClosureReport depends on it
   */
  const generateClosureReportInternal = useCallback(async () => {
    console.log('[TestClosure] generateClosureReportInternal called');
    // Get API key from Redux store based on model type
    let apiKeyToUse = null;
    if (selectedModel.startsWith('gemini')) {
      apiKeyToUse = apiKeys?.google;
      if (!apiKeyToUse) {
        toast.error('Google API key required for Gemini models. Please set it in Settings.');
        return;
      }
    } else if (selectedModel.startsWith('gpt') || selectedModel.startsWith('o1')) {
      apiKeyToUse = apiKeys?.openai;
      if (!apiKeyToUse) {
        toast.error('OpenAI API key required for GPT models. Please set it in Settings.');
        return;
      }
    }

    setGeneratingReport(true);
    setReport(null);
    setMetrics(null);

    // Show initial loading state in output
    const loadingOutput = {
      status: 'running',
      content: `🔄 **Generating Test Closure Report**

⚙️ **Configuration:**
- Sessions: ${selectedSessions.length} selected
- Model: ${models.find(m => m.key === selectedModel)?.name || selectedModel}
- Custom Prompt: ${customPrompt && customPrompt !== promptPreview ? 'Yes (edited)' : 'No (default)'}

📋 **Selected Sessions:**
${sessions.filter(s => selectedSessions.includes(s.session_id)).map(s => `  • ${s.session_id.substring(0, 8)}... (${s.process_count} processes)`).join('\n')}

⏳ **Status:** Generating closure report...

This may take a few moments depending on the amount of data.`,
      timestamp: new Date().toISOString(),
      model: selectedModel,
      processType: 'Test Closure'
    };

    if (onSetOutput) {
      onSetOutput('test-closure', loadingOutput);
    }

    // Auto-load model in LM Studio if it's a local model
    if (!selectedModel.startsWith('gemini') && !selectedModel.startsWith('gpt')) {
      try {
        console.log('[TestClosure] Auto-loading model in LM Studio:', selectedModel);
        
        // Try to load the model directly (skip health check due to CORS)
        // LM Studio backend will handle this through proxy
        console.log('[TestClosure] Skipping LM Studio health check (CORS issue)');
        console.log('[TestClosure] Backend will attempt to use model:', selectedModel);
        toast(`Preparing to use model: ${selectedModel}`, { 
          icon: '⚙️',
          duration: 3000 
        });
      } catch (err) {
        console.warn('[TestClosure] Error in model preparation:', err.message);
      }
    }

    try {
      const requestBody = {
        session_ids: selectedSessions,
        model: selectedModel,
        api_key: apiKeyToUse,
        custom_prompt: customPrompt && customPrompt !== promptPreview ? customPrompt : null
      };
      
      console.log('[TestClosure] Sending request to backend:');
      console.log('  - Endpoint:', '/api/test-closure/generate-report');
      console.log('  - Selected Model:', selectedModel);
      console.log('  - Using Custom Prompt:', !!requestBody.custom_prompt);
      
      const response = await fetch('/api/test-closure/generate-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setReport(data.report_content);
        setMetrics(data.metrics);
        setQualityEvaluation(data.quality_evaluation); // Store quality metrics
        toast.success('Closure report generated successfully');
        
        // Show success output in OutputPanel
        const successOutput = {
          status: 'completed',
          content: data.report_content,
          timestamp: new Date().toISOString(),
          model: selectedModel,
          processType: 'Test Closure',
          metrics: data.metrics,
          sessions_analyzed: data.sessions_analyzed,
          quality_evaluation: data.quality_evaluation // Include quality metrics
        };

        if (onSetOutput) {
          onSetOutput('test-closure', successOutput);
        }
        
        // Call onComplete callback if provided
        if (onComplete) {
          onComplete({
            report: data.report_content,
            metrics: data.metrics,
            sessions_analyzed: data.sessions_analyzed
          });
        }
      } else {
        const errorMsg = data.error || 'Failed to generate report';
        
        // Show error in OutputPanel
        const errorOutput = {
          status: 'error',
          content: `# ❌ Test Closure Report Generation Failed\n\n**Error:** ${errorMsg}\n\n**Troubleshooting:**\n- If using LM Studio: Ensure LM Studio is running and a model is loaded\n- If using Gemini: Check your API key in Settings\n- Verify that sessions contain valid data`,
          timestamp: new Date().toISOString(),
          model: selectedModel,
          processType: 'Test Closure'
        };

        if (onSetOutput) {
          onSetOutput('test-closure', errorOutput);
        }
        
        // Check for specific error types
        if (errorMsg.includes('No models loaded') || errorMsg.includes('model_not_found')) {
          toast.error('Model not loaded in LM Studio. Tried to load automatically but failed. Please manually load the model in LM Studio or select a Gemini model.', {
            duration: 8000
          });
        } else if (errorMsg.includes('Connection refused') || errorMsg.includes('ECONNREFUSED')) {
          toast.error('Cannot connect to LM Studio. Please ensure LM Studio is running on port 1234.', {
            duration: 5000
          });
        } else if (errorMsg.includes('API key') || errorMsg.includes('Unauthorized')) {
          toast.error('API key error. Please check your API key in Settings.', {
            duration: 5000
          });
        } else {
          toast.error(`Error: ${errorMsg}`);
        }
      }
    } catch (error) {
      console.error('Error generating report:', error);
      
      // Show error in OutputPanel
      const catchErrorOutput = {
        status: 'error',
        content: `# ❌ Test Closure Report Generation Failed\n\n**Error:** ${error.message}\n\n**Troubleshooting:**\n- Check if backend server is running on port 8000\n- If using LM Studio: Ensure it's running on port 1234\n- Try selecting a different model`,
        timestamp: new Date().toISOString(),
        model: selectedModel,
        processType: 'Test Closure'
      };

      if (onSetOutput) {
        onSetOutput('test-closure', catchErrorOutput);
      }
      
      // Better error messages for common issues
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        toast.error('Cannot connect to backend server. Please ensure the backend is running on port 8000.', {
          duration: 5000
        });
      } else if (error.message.includes('No models loaded')) {
        toast.error('LM Studio error: No model loaded. Please load a model in LM Studio or use a Gemini model.', {
          duration: 6000
        });
      } else {
        toast.error(`Error: ${error.message}`);
      }
    } finally {
      setGeneratingReport(false);
    }
  }, [selectedSessions, selectedModel, customPrompt, promptPreview, apiKeys, models, onSetOutput, onComplete, sessions]);

  /**
   * Generate AI-powered closure report
   * Defined after generateClosureReportInternal because it depends on it
   */
  const generateClosureReport = useCallback(async () => {
    console.log('[TestClosure] generateClosureReport called');
    console.log('[TestClosure] showPromptEditor:', showPromptEditor);
    console.log('[TestClosure] selectedSessions:', selectedSessions);
    console.log('[TestClosure] selectedModel:', selectedModel);
    
    if (selectedSessions.length === 0) {
      toast.error('Please select at least one session');
      return;
    }

    if (!selectedModel) {
      toast.error('Please select a model');
      return;
    }

    // Show prompt editor first if not already shown
    if (!showPromptEditor) {
      console.log('[TestClosure] Showing prompt editor first...');
      const loaded = await loadPrompt(true);
      console.log('[TestClosure] loadPrompt returned:', loaded);
      if (!loaded) {
        return; // Failed to load prompt
      }
      return; // Prompt will be shown, user can then click Continue & Generate
    }

    // If we're here, prompt is already shown and user clicked Continue & Generate
    console.log('[TestClosure] Continuing with report generation...');
    await generateClosureReportInternal();
  }, [selectedSessions, selectedModel, showPromptEditor, loadPrompt, generateClosureReportInternal]);

  // Track form state for main button - must be after generateClosureReport definition
  useEffect(() => {
    const canRun = selectedSessions.length > 0 && selectedModel && !generatingReport;
    
    if (onSetFormState) {
      onSetFormState({
        canRun,
        isRunning: generatingReport,
        handleRun: canRun ? generateClosureReport : null
      });
    }
  }, [selectedSessions, selectedModel, generatingReport, onSetFormState, generateClosureReport]);

  /**
   * Download report as markdown file with quality metrics
   */
  const downloadReport = () => {
    if (!report) return;

    // Prepare enhanced report with quality metrics
    let enhancedReport = report;
    
    if (qualityEvaluation) {
      const qualitySection = `\n\n---\n\n# 📊 Closure Report Quality Metrics\n\n**Generated for Academic Research & Quality Assessment**\n\n## Overall Quality Score\n\n**Overall Score:** ${(qualityEvaluation.overall_score * 100).toFixed(2)}%\n\n## Quality Dimensions\n\n| Dimension | Score | Description |\n|-----------|-------|-------------|\n| **Completeness** | ${(qualityEvaluation.completeness * 100).toFixed(2)}% | Presence of required sections (IEEE 829, ISO/IEC/IEEE 29119-3) |\n| **Coverage** | ${(qualityEvaluation.coverage * 100).toFixed(2)}% | Faithfulness to test execution data |\n| **Clarity** | ${(qualityEvaluation.clarity * 100).toFixed(2)}% | Statistical readability and absence of ambiguity |\n| **Depth** | ${(qualityEvaluation.depth * 100).toFixed(2)}% | Analytical vs descriptive content ratio |\n| **Consistency** | ${(qualityEvaluation.consistency * 100).toFixed(2)}% | Numeric constraint validation |\n\n## Evaluation Methodology\n\n**Standards Compliance:**\n- ISO/IEC/IEEE 29119-3:2013 (Software Testing Standard - Part 3: Test Documentation)\n- IEEE 829-2008 (Standard for Software and System Test Documentation)\n- ISTQB Foundation Level v4.0 (2023)\n- ISTQB Test Manager (Advanced Level) 2012\n\n**Evaluation Approach:**\n- Model-Agnostic: Independent of LLM used for generation\n- Fully Deterministic: Reproducible metrics based on structural analysis\n- Standards-Based: Aligned with international testing standards\n\n**Quality Dimension Weights:**\n${Object.entries(qualityEvaluation.weights_used || {}).map(([key, value]) => `- ${key.charAt(0).toUpperCase() + key.slice(1)}: ${(value * 100).toFixed(0)}%`).join('\n')}\n\n## Detailed Calculation\n\n${qualityEvaluation.calculation_details ? JSON.stringify(qualityEvaluation.calculation_details, null, 2) : 'N/A'}\n\n---\n\n**Report Metadata:**\n- Generation Time: ${new Date().toISOString()}\n- Model Used: ${selectedModel || 'Unknown'}\n- Sessions Analyzed: ${metrics?.total_sessions || 0}\n- Evaluation Method: Deterministic Quality Evaluator v1.0\n`;
      
      enhancedReport = report + qualitySection;
    }

    const blob = new Blob([enhancedReport], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test-closure-report-${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Report downloaded with quality metrics');
  };

  return (
    <div className="space-y-6">
      {/* Session Selection */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Select Sessions ({selectedSessions.length} selected)
          </h3>
          <div className="flex gap-2">
            <button
              onClick={selectAllSessions}
              className="px-3 py-1 text-sm bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
            >
              Select All
            </button>
            <button
              onClick={clearSelections}
              className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            >
              Clear
            </button>
          </div>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <ClockIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No sessions found. Try adjusting the date range.</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {sessions.map((session) => {
              const isSelected = selectedSessions.includes(session.session_id);
              const isExpanded = expandedSessions.includes(session.session_id);
              const shortSessionId = session.session_id.length > 12 
                ? session.session_id.substring(0, 8)
                : session.session_id;
              
              return (
                <div
                  key={session.session_id}
                  className={clsx(
                    'border rounded-lg transition-all',
                    isSelected ? 'border-purple-300 bg-purple-50' : 'border-gray-200 bg-white'
                  )}
                >
                  {/* Main Card Header */}
                  <div 
                    className="p-3 cursor-pointer hover:bg-gray-50"
                    onClick={() => toggleSession(session.session_id)}
                  >
                    <div className="flex items-start space-x-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onClick={(e) => {
                          e.stopPropagation();
                        }}
                        onChange={(e) => {
                          toggleSession(session.session_id);
                        }}
                        className="mt-1 rounded cursor-pointer"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-gray-900 truncate flex-1" title={session.session_id}>
                            Session {shortSessionId}
                          </h4>
                          <div className="flex items-center gap-2">
                            <span className={clsx(
                              'text-xs font-medium px-2 py-1 rounded flex-shrink-0',
                              session.process_count > 1 ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                            )}>
                              {session.process_count} {session.process_count === 1 ? 'process' : 'processes'}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleSessionExpand(session.session_id);
                              }}
                              className="text-gray-500 hover:text-gray-700 p-1"
                              title={isExpanded ? 'Collapse' : 'Expand details'}
                            >
                              {isExpanded ? '▼' : '▶'}
                            </button>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
                          <span>📅 {formatTimestamp(session.timestamp || session.created_at)}</span>
                          <span>•</span>
                          <span>📋 {session.processes.join(', ')}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Expandable Details Section */}
                  {isExpanded && (
                    <div className="border-t border-gray-200 bg-gray-50 p-3 space-y-2">
                      <h5 className="text-xs font-semibold text-gray-700 mb-2">Process Details:</h5>
                      {session.processes.map((processType, idx) => {
                        const processMeta = getProcessMetadata(processType);
                        
                        return (
                          <div 
                            key={idx}
                            className="bg-white p-2 rounded border border-gray-200 text-xs"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-base">{processMeta.icon}</span>
                              <span className="font-medium text-gray-900">{processMeta.label}</span>
                              <span className={clsx(
                                'px-2 py-0.5 rounded text-xs font-medium ml-auto',
                                processMeta.bgColor,
                                processMeta.textColor
                              )}>
                                {processMeta.shortLabel}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Model Selection */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          AI Model Selection
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Model
            </label>
            <select
              value={selectedModel || ''}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
              disabled={modelsLoading}
            >
              <option value="">Select a model...</option>
              {models.map((model) => (
                <option key={model.key} value={model.key}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Quick Actions
        </h3>
        <button
          onClick={calculateMetrics}
          disabled={selectedSessions.length === 0 || fetchingMetrics}
          className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 flex items-center justify-center gap-2 font-medium"
        >
          {fetchingMetrics ? (
            <>
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
              Calculating...
            </>
          ) : (
            <>
              <CheckCircleIcon className="w-5 h-5" />
              Calculate Metrics Only
            </>
          )}
        </button>
      </div>

      {/* Loading Prompt Modal */}
      {isLoadingPrompt && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-8 max-w-md">
            <div className="flex flex-col items-center">
              <ArrowPathIcon className="w-12 h-12 text-purple-600 animate-spin mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Loading Prompt...</h3>
              <p className="text-sm text-gray-500 text-center">
                Generating prompt with international standards (ISO/IEC/IEEE 29119-3, IEEE 829, ISTQB)
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Prompt Editor Modal */}
      {showPromptEditor && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <div>
                <h3 className="text-xl font-semibold text-gray-900">Review & Edit AI Prompt</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Review the prompt generated following <strong>ISO/IEC/IEEE 29119-3</strong>, <strong>IEEE 829</strong>, and <strong>ISTQB</strong> standards
                </p>
              </div>
              <button
                onClick={() => {
                  setShowPromptEditor(false);
                  setPendingGeneration(false);
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <XCircleIcon className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6">
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                className="w-full h-full min-h-[500px] p-4 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Enter your custom prompt here..."
              />
              <div className="mt-2 text-sm text-gray-500 flex items-center justify-between">
                <span>{customPrompt.length} characters • ~{Math.ceil(customPrompt.length / 4)} tokens (estimated)</span>
                {customPrompt !== promptPreview && (
                  <span className="text-purple-600 font-medium">✏️ Modified</span>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
              <button
                onClick={() => setCustomPrompt(promptPreview)}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Reset to Original
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowPromptEditor(false);
                    setPendingGeneration(false);
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setShowPromptEditor(false);
                    if (pendingGeneration) {
                      // Continue with generation
                      setTimeout(() => generateClosureReportInternal(), 100);
                    } else {
                      toast.success('Prompt saved. You can generate the report now.');
                    }
                  }}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  {pendingGeneration ? 'Continue & Generate' : 'Use This Prompt'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Metrics Display */}
      {metrics && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Test Metrics Summary
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {/* Test Scenarios */}
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-blue-600 font-medium">Test Scenarios</p>
              <p className="text-3xl font-bold text-blue-900 mt-2">
                {metrics.test_scenarios?.total || 0}
              </p>
            </div>

            {/* Test Cases */}
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-sm text-green-600 font-medium">Test Cases</p>
              <p className="text-3xl font-bold text-green-900 mt-2">
                {metrics.test_cases?.total_generated || 0}
              </p>
              <p className="text-xs text-green-600 mt-1">
                {metrics.test_cases?.total_optimized || 0} optimized
              </p>
            </div>

            {/* Test Execution */}
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-sm text-purple-600 font-medium">Tests Executed</p>
              <p className="text-3xl font-bold text-purple-900 mt-2">
                {metrics.test_execution?.total_executed || 0}
              </p>
              <p className="text-xs text-purple-600 mt-1">
                {metrics.test_execution?.pass_rate || 0}% pass rate
              </p>
            </div>

            {/* Defects */}
            <div className="bg-red-50 rounded-lg p-4">
              <p className="text-sm text-red-600 font-medium">Defects Found</p>
              <p className="text-3xl font-bold text-red-900 mt-2">
                {metrics.defects?.total || 0}
              </p>
              <p className="text-xs text-red-600 mt-1">
                {metrics.defects?.critical || 0} critical
              </p>
            </div>
          </div>

          {/* Detailed Results */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-2">Pass/Fail Breakdown</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Passed:</span>
                  <span className="font-medium text-green-600">
                    {metrics.test_execution?.passed || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Failed:</span>
                  <span className="font-medium text-red-600">
                    {metrics.test_execution?.failed || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Skipped:</span>
                  <span className="font-medium text-gray-600">
                    {metrics.test_execution?.skipped || 0}
                  </span>
                </div>
              </div>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-2">Coverage</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Scenario Coverage:</span>
                  <span className="font-medium text-blue-600">
                    {metrics.coverage?.scenario_coverage || 0}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Optimization Rate:</span>
                  <span className="font-medium text-green-600">
                    {metrics.test_cases?.optimization_rate || 0}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Closure Quality Metrics Display */}
      {qualityEvaluation && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📊 Closure Report Quality Assessment
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            Based on international testing standards (ISO/IEC/IEEE 29119-3, IEEE 829, ISTQB)
          </p>
          
          {/* Overall Score */}
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-6 mb-6">
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-2">Overall Quality Score</p>
              <p className="text-5xl font-bold text-purple-900">
                {(qualityEvaluation.overall_score * 100).toFixed(1)}%
              </p>
              <div className="mt-4 bg-gray-200 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-purple-500 to-blue-500 h-full transition-all duration-500"
                  style={{ width: `${qualityEvaluation.overall_score * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Quality Dimensions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Completeness */}
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
              <p className="text-xs text-blue-600 font-medium mb-2">📋 Completeness</p>
              <p className="text-2xl font-bold text-blue-900">
                {(qualityEvaluation.completeness * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-600 mt-2">
                Required sections present
              </p>
            </div>

            {/* Coverage */}
            <div className="bg-green-50 rounded-lg p-4 border border-green-200">
              <p className="text-xs text-green-600 font-medium mb-2">🎯 Coverage</p>
              <p className="text-2xl font-bold text-green-900">
                {(qualityEvaluation.coverage * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-600 mt-2">
                Data faithfulness
              </p>
            </div>

            {/* Clarity */}
            <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
              <p className="text-xs text-yellow-600 font-medium mb-2">✨ Clarity</p>
              <p className="text-2xl font-bold text-yellow-900">
                {(qualityEvaluation.clarity * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-600 mt-2">
                Readability & precision
              </p>
            </div>

            {/* Depth */}
            <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
              <p className="text-xs text-purple-600 font-medium mb-2">🔬 Depth</p>
              <p className="text-2xl font-bold text-purple-900">
                {(qualityEvaluation.depth * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-600 mt-2">
                Analytical content
              </p>
            </div>

            {/* Consistency */}
            <div className="bg-red-50 rounded-lg p-4 border border-red-200">
              <p className="text-xs text-red-600 font-medium mb-2">✓ Consistency</p>
              <p className="text-2xl font-bold text-red-900">
                {(qualityEvaluation.consistency * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-600 mt-2">
                Numeric accuracy
              </p>
            </div>
          </div>

          {/* Evaluation Methodology */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">📚 Evaluation Methodology</h4>
            <div className="text-xs text-gray-600 space-y-1">
              <p><strong>Approach:</strong> Model-Agnostic, Fully Deterministic</p>
              <p><strong>Standards:</strong> ISO/IEC/IEEE 29119-3, IEEE 829, ISTQB Foundation & Test Manager</p>
              <p><strong>Weights Used:</strong> {Object.entries(qualityEvaluation.weights_used || {}).map(([k, v]) => `${k}: ${(v * 100).toFixed(0)}%`).join(', ')}</p>
            </div>
          </div>

          {/* Academic Use Note */}
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-800">
              ℹ️ <strong>For Academic Research:</strong> These metrics are calculated using a deterministic, standards-based methodology suitable for academic studies and quality assessment. All scores are reproducible and model-agnostic.
            </p>
          </div>
        </div>
      )}

      {/* Report Display */}
      {report && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              AI-Generated Closure Report
            </h3>
            <button
              onClick={downloadReport}
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download Report
            </button>
          </div>
          
          <div className="prose max-w-none bg-gray-50 rounded-lg p-6 max-h-[600px] overflow-y-auto">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800">
              {report}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

TestClosureForm.propTypes = {
  onComplete: PropTypes.func,
  onSetOutput: PropTypes.func,
  onSetFormState: PropTypes.func
};
