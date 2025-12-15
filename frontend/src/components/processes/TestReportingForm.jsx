import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { 
  DocumentChartBarIcon, 
  ArrowPathIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import { useSelector } from 'react-redux';
import PropTypes from 'prop-types';
import { useModels } from '../../hooks/useModels';

// Process metadata with icons, labels, and colors
const PROCESS_METADATA = {
  test_scenario_generation: { 
    icon: '📝', 
    label: 'Test Scenarios',
    shortLabel: 'Scenarios',
    color: 'blue',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    fields: ['category', 'test_type', 'process_title']
  },
  test_case_generation: { 
    icon: '🧪', 
    label: 'Test Cases',
    shortLabel: 'Cases',
    color: 'green',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    fields: ['based_on', 'updated_at']
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
  },
  requirement_analysis: { 
    icon: '📋', 
    label: 'Requirement Analysis',
    shortLabel: 'Requirements',
    color: 'pink',
    bgColor: 'bg-pink-100',
    textColor: 'text-pink-700'
  },
  test_planning: { 
    icon: '📊', 
    label: 'Test Planning',
    shortLabel: 'Planning',
    color: 'cyan',
    bgColor: 'bg-cyan-100',
    textColor: 'text-cyan-700'
  },
  environment_setup: {
    icon: '⚙️',
    label: 'Environment Setup',
    shortLabel: 'Env Setup',
    color: 'gray',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700'
  }
};

// Model metadata for display
const MODEL_METADATA = {
  'gemini-2.5-pro': { icon: '🤖', shortName: 'Gemini Pro', color: 'blue' },
  'gemini-2.5-flash': { icon: '⚡', shortName: 'Gemini Flash', color: 'blue' },
  'gemini-1.5-pro': { icon: '🤖', shortName: 'Gemini 1.5', color: 'blue' },
  'llama-3.2-3b-instruct': { icon: '🦙', shortName: 'Llama 3.2', color: 'purple' },
  'llama3.2:1b': { icon: '🦙', shortName: 'Llama 1B', color: 'purple' },
  'default': { icon: '🔮', shortName: 'AI Model', color: 'gray' }
};

const ANALYSIS_DEPTHS = [
  { value: 'summary', label: 'Summary', description: 'Quick overview with key metrics' },
  { value: 'detailed', label: 'Detailed', description: 'Comprehensive analysis (recommended)' },
  { value: 'deep', label: 'Deep Analysis', description: 'In-depth insights and recommendations' }
];

export default function TestReportingForm({ 
  sessionId,
  onSetOutput,
  disabled = false,
  process,
  onTestCaseGeneration
}) {
  // Redux state for API keys
  const apiKeys = useSelector((state) => state.apiKey.apiKeys);
  
  // Model selection hook
  const { 
    models: availableModels, 
    loading: modelsLoading, 
    error: modelsError
  } = useModels({ 
    autoFetch: true,
    includeDescriptions: true 
  });
  
  // Component state
  const [selectedModel, setSelectedModel] = useState('');
  const [analysisDepth, setAnalysisDepth] = useState('detailed');
  const [availableSessions, setAvailableSessions] = useState([]);
  const [selectedSessions, setSelectedSessions] = useState([]); // Changed to array for multiple selection
  const [expandedSessions, setExpandedSessions] = useState([]); // NEW: Track expanded session cards
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState({
    status: 'idle', // idle | fetching | chunking | analyzing | synthesizing | completed | error
    currentProcess: '',
    currentChunk: 0,
    totalChunks: 0,
    message: ''
  });

  // Auto-select first available LOCAL model when models load (prefer LM Studio over Gemini)
  useEffect(() => {
    if (!modelsLoading && availableModels.length > 0 && !selectedModel) {
      // Prefer local models (LM Studio) over API models
      const localModel = availableModels.find(m => m.type === 'local');
      const modelToSelect = localModel || availableModels[0];
      setSelectedModel(modelToSelect.key);
      console.log('[TestReporting] Auto-selected model:', modelToSelect.key, modelToSelect.name);
    }
  }, [availableModels, modelsLoading, selectedModel]);

  // Fetch available sessions on mount
  const fetchSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      const response = await fetch('http://localhost:8000/api/test-reporting/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          process_names: null, // Fetch all
          date_from: null,
          date_to: null
        }),
      });

      const data = await response.json();

      if (data.success) {
        setAvailableSessions(data.sessions || []);
        toast.success(`Found ${data.sessions.length} sessions`);
      } else {
        toast.error('Failed to load sessions');
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
      toast.error('Failed to load sessions');
    } finally {
      setIsLoadingSessions(false);
    }
  }, []); // Removed selectedSession dependency

  useEffect(() => {
    fetchSessions();
  }, []);

  // Handle session selection toggle
  const toggleSession = (sessionId) => {
    setSelectedSessions(prev => {
      if (prev.includes(sessionId)) {
        return prev.filter(id => id !== sessionId);
      } else {
        return [...prev, sessionId];
      }
    });
  };

  // Handle session expand/collapse toggle
  const toggleSessionExpand = (sessionId) => {
    setExpandedSessions(prev => {
      if (prev.includes(sessionId)) {
        return prev.filter(id => id !== sessionId);
      } else {
        return [...prev, sessionId];
      }
    });
  };

  // Handle select all sessions
  const selectAllSessions = () => {
    setSelectedSessions(availableSessions.map(s => s.session_id));
  };

  // Handle clear all sessions
  const clearAllSessions = () => {
    setSelectedSessions([]);
  };

  // Helper: Get model metadata
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

  // Helper: Get process metadata
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

  // Helper: Format timestamp
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown date';
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    } catch (err) {
      console.error('Date formatting error:', err, timestamp);
      return 'Invalid date';
    }
  };


  // Get selected sessions data
  const selectedSessionsData = availableSessions.filter(s => selectedSessions.includes(s.session_id));

  // Generate report
  const generateReport = async () => {
    // Validation
    if (selectedSessions.length === 0) {
      toast.error('Please select at least one session');
      return;
    }

    // API key check for Gemini models
    const selectedModelInfo = availableModels.find(m => m.key === selectedModel);
    let apiKey = null;
    
    if (selectedModelInfo?.type === 'api') {
      if (selectedModel.startsWith('gemini')) {
        apiKey = apiKeys.google;
        if (!apiKey) {
          toast.error('Gemini API key is required. Please configure it in API Settings.');
          return;
        }
      }
    }

    setIsGenerating(true);
    setGenerationProgress({
      status: 'fetching',
      currentProcess: '',
      currentChunk: 0,
      totalChunks: 0,
      message: 'Fetching session data...'
    });

    // Show initial loading state in output
    const loadingOutput = {
      status: 'running',
      content: `🔄 **Generating Comprehensive Test Report**

⚙️ **Configuration:**
- Sessions: ${selectedSessions.length} selected
- Model: ${selectedModelInfo?.name || selectedModel}
- Analysis Depth: ${analysisDepth}

📋 **Selected Sessions:**
${selectedSessionsData.map(s => `  • ${s.process_name || s.session_id} (${Object.keys(s.processes).length} processes)`).join('\n')}

⏳ **Status:** Fetching session data...

This may take a few moments depending on the amount of data and selected analysis depth.`,
      timestamp: new Date().toISOString(),
      model: selectedModel,
      processType: 'Test Reporting'
    };

    if (onSetOutput) {
      onSetOutput('test-reporting', loadingOutput);
    }

    try {
      const requestBody = {
        session_ids: selectedSessions, // Changed to array
        model: selectedModel,
        analysis_depth: analysisDepth,
        ...(apiKey ? { api_key: apiKey } : {})
      };

      console.log('[TestReporting] Sending request:', requestBody);
      console.log('[TestReporting] Selected model state:', selectedModel);
      console.log('[TestReporting] Selected model info:', selectedModelInfo);
      console.log('[TestReporting] API key provided:', apiKey ? 'Yes' : 'No');

      const response = await fetch('http://localhost:8000/api/test-reporting/generate-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      console.log('[TestReporting] Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('[TestReporting] Error response:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      console.log('[TestReporting] Result:', result);

      if (result.success) {
        setGenerationProgress({
          status: 'completed',
          currentProcess: '',
          currentChunk: 0,
          totalChunks: 0,
          message: 'Report generated successfully!'
        });

        const successOutput = {
          status: 'completed',
          content: result.report_content,
          timestamp: new Date().toISOString(),
          model: selectedModel,
          model_used: result.metadata?.model_used || selectedModel,
          processType: 'Test Reporting',
          metadata: result.metadata
        };

        if (onSetOutput) {
          onSetOutput('test-reporting', successOutput);
        }
        
        toast.success('Comprehensive report generated successfully!');
      } else {
        setGenerationProgress({
          status: 'error',
          currentProcess: '',
          currentChunk: 0,
          totalChunks: 0,
          message: result.error || 'Report generation failed'
        });

        const errorOutput = {
          status: 'error',
          content: `❌ **Report Generation Failed**

🔴 **Error Details:**
\`\`\`
${result.error || 'Unknown error occurred'}
\`\`\`

**Troubleshooting:**
- Check if the backend services are running
- Verify your model is loaded in LM Studio (for local models)
- Ensure your API key is valid (for Gemini models)
- Verify the selected sessions have data for analysis

**Configuration:**
- Sessions: ${selectedSessions.length} selected
- Analysis Depth: ${analysisDepth}
- Model: ${selectedModelInfo?.name || selectedModel} (${selectedModel})`,
          timestamp: new Date().toISOString(),
          model: selectedModel,
          model_used: selectedModel,
          processType: 'Test Reporting'
        };

        if (onSetOutput) {
          onSetOutput('test-reporting', errorOutput);
        }
        
        toast.error('Report generation failed');
      }
    } catch (error) {
      console.error('Report generation error:', error);
      
      setGenerationProgress({
        status: 'error',
        currentProcess: '',
        currentChunk: 0,
        totalChunks: 0,
        message: error.message
      });

      const errorOutput = {
        status: 'error',
        content: `❌ **Connection Error**

🔴 **Network Error:**
${error.message}

Please ensure the backend services are running:
- Main Backend: http://localhost:8000
- LM Studio (if using local models): http://localhost:1234

**Check:**
1. Backend server is running
2. Selected model (${selectedModelInfo?.name || selectedModel}) is loaded in LM Studio
3. Network connectivity

**Configuration:**
- Model: ${selectedModelInfo?.name || selectedModel} (${selectedModel})
- Sessions: ${selectedSessions.length}`,
        timestamp: new Date().toISOString(),
        model: selectedModel,
        model_used: selectedModel,
        processType: 'Test Reporting'
      };

      if (onSetOutput) {
        onSetOutput('test-reporting', errorOutput);
      }
      
      toast.error('Report generation failed: Connection error');
    } finally {
      setIsGenerating(false);
    }
  };

  // Update form state for Run Process button
  useEffect(() => {
    if (onTestCaseGeneration) {
      const canRun = selectedSessions.length > 0 && !isGenerating;
      onTestCaseGeneration({
        canRun,
        isRunning: isGenerating,
        handleRun: canRun ? generateReport : null
      });
    }
  }, [onTestCaseGeneration, selectedSessions, isGenerating]);

  return (
    <div className="space-y-6">
      {/* Session Selection */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <ClockIcon className="w-5 h-5 mr-2 text-gray-600" />
          Session Selection
        </h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Sessions <span className="text-red-500">*</span>
              </label>
              <p className="text-xs text-gray-500">
                Select one or more sessions to compare and generate a comprehensive report
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={selectAllSessions}
                disabled={isLoadingSessions || isGenerating || availableSessions.length === 0}
                className="px-3 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 disabled:opacity-50"
              >
                Select All
              </button>
              <button
                onClick={clearAllSessions}
                disabled={isLoadingSessions || isGenerating || selectedSessions.length === 0}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
              >
                Clear All
              </button>
              <button
                onClick={fetchSessions}
                disabled={isLoadingSessions || isGenerating}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
                title="Refresh sessions"
              >
                <ArrowPathIcon className={clsx('w-4 h-4', isLoadingSessions && 'animate-spin')} />
              </button>
            </div>
          </div>

          {isLoadingSessions && (
            <div className="text-center p-8">
              <ArrowPathIcon className="w-8 h-8 mx-auto mb-2 text-indigo-500 animate-spin" />
              <p className="text-sm text-gray-500">Loading sessions...</p>
            </div>
          )}

          {!isLoadingSessions && availableSessions.length === 0 && (
            <div className="text-center p-8 text-gray-500">
              <DocumentChartBarIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p className="text-sm">No sessions found. Complete some STLC processes first.</p>
            </div>
          )}

          {!isLoadingSessions && availableSessions.length > 0 && (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {availableSessions.map(session => {
                const isSelected = selectedSessions.includes(session.session_id);
                const isExpanded = expandedSessions.includes(session.session_id);
                const processCount = Object.keys(session.processes).length;
                const processDetails = session.process_details || [];
                const modelsUsed = session.models_used || [];
                
                // Shorten session ID
                const shortSessionId = session.session_id.length > 12 
                  ? session.session_id.substring(0, 8)
                  : session.session_id;
                
                // Display name: use process_name if available, otherwise use session_id
                const displayName = session.process_name || `Session ${shortSessionId}`;
                
                return (
                  <div
                    key={session.session_id}
                    className={clsx(
                      'border rounded-lg transition-all',
                      isSelected ? 'border-indigo-300 bg-indigo-50' : 'border-gray-200 bg-white'
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
                          onChange={() => {}}
                          disabled={isGenerating}
                          className="mt-1 rounded"
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <h4 className="text-sm font-semibold text-gray-900 truncate flex-1" title={displayName}>
                              {displayName}
                            </h4>
                            <div className="flex items-center gap-2">
                              <span className={clsx(
                                'text-xs font-medium px-2 py-1 rounded flex-shrink-0',
                                processCount > 1 ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                              )}>
                                {processCount} {processCount === 1 ? 'process' : 'processes'}
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
                            {session.process_name && (
                              <>
                                <span className="font-mono" title={session.session_id}>{shortSessionId}</span>
                                <span>•</span>
                              </>
                            )}
                            <span>📅 {formatTimestamp(session.timestamp)}</span>
                            {modelsUsed.length > 0 && (
                              <>
                                <span>•</span>
                                <div className="flex items-center gap-1">
                                  {modelsUsed.slice(0, 2).map((model, idx) => {
                                    const modelMeta = getModelMetadata(model);
                                    return (
                                      <span key={idx} className="inline-flex items-center gap-1" title={model}>
                                        {modelMeta.icon}
                                      </span>
                                    );
                                  })}
                                  {modelsUsed.length > 2 && (
                                    <span className="text-xs text-gray-400">+{modelsUsed.length - 2}</span>
                                  )}
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Expandable Details Section */}
                    {isExpanded && processDetails.length > 0 && (
                      <div className="border-t border-gray-200 bg-gray-50 p-3 space-y-2">
                        <h5 className="text-xs font-semibold text-gray-700 mb-2">Process Details:</h5>
                        {processDetails.map((detail, idx) => {
                          const processMeta = getProcessMetadata(detail.type);
                          const modelMeta = getModelMetadata(detail.model);
                          
                          return (
                            <div 
                              key={idx}
                              className="bg-white p-2 rounded border border-gray-200 text-xs"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-base">{processMeta.icon}</span>
                                  <span className="font-medium text-gray-900">{processMeta.shortLabel}</span>
                                  {detail.item_count > 0 && (
                                    <span className={clsx(
                                      'px-2 py-0.5 rounded text-xs font-medium',
                                      processMeta.bgColor,
                                      processMeta.textColor
                                    )}>
                                      {detail.item_count} items
                                    </span>
                                  )}
                                </div>
                                <span className="text-gray-500" title={detail.model}>
                                  {modelMeta.icon} {modelMeta.shortName}
                                </span>
                              </div>
                              
                              {/* Process-specific details */}
                              <div className="ml-6 space-y-1 text-gray-600">
                                {detail.category && (
                                  <div>📂 Category: <span className="font-medium">{detail.category}</span></div>
                                )}
                                {detail.test_type && (
                                  <div>🏷️ Type: <span className="font-medium">{detail.test_type}</span></div>
                                )}
                                {detail.process_title && detail.process_title !== session.process_name && (
                                  <div>📝 Title: <span className="font-medium">{detail.process_title}</span></div>
                                )}
                                {detail.based_on && (
                                  <div>🔗 Based on: <span className="font-medium">{detail.based_on}</span></div>
                                )}
                                {detail.updated_at && (
                                  <div>🔄 Updated: <span className="font-medium">{formatTimestamp(detail.updated_at)}</span></div>
                                )}
                                {detail.timestamp && (
                                  <div>⏰ {formatTimestamp(detail.timestamp)}</div>
                                )}
                                {detail.edited_prompt && (
                                  <div className="text-amber-600">✏️ Custom prompt used</div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                        
                        {/* Models Summary */}
                        {modelsUsed.length > 0 && (
                          <div className="pt-2 border-t border-gray-200">
                            <div className="text-xs text-gray-600 flex items-center gap-2 flex-wrap">
                              <span className="font-medium">Models used:</span>
                              {modelsUsed.map((model, idx) => {
                                const modelMeta = getModelMetadata(model);
                                return (
                                  <span 
                                    key={idx}
                                    className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-gray-200 rounded"
                                    title={model}
                                  >
                                    {modelMeta.icon} <span className="font-medium">{modelMeta.shortName}</span>
                                  </span>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {selectedSessions.length > 0 && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm font-medium text-green-900">
                ✓ {selectedSessions.length} session{selectedSessions.length > 1 ? 's' : ''} selected for comparison
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Report Configuration */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <DocumentChartBarIcon className="w-5 h-5 mr-2 text-gray-600" />
          Report Configuration
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* AI Model Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              AI Model <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={disabled || isGenerating || modelsLoading}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50"
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
              <p className="text-xs text-gray-500 mt-1">Loading models...</p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              💡 Gemini models recommended for comprehensive reports (larger context)
            </p>
          </div>

          {/* Analysis Depth */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Analysis Depth
            </label>
            <select
              value={analysisDepth}
              onChange={(e) => setAnalysisDepth(e.target.value)}
              disabled={disabled || isGenerating}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50"
            >
              {ANALYSIS_DEPTHS.map(depth => (
                <option key={depth.value} value={depth.value}>
                  {depth.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {ANALYSIS_DEPTHS.find(d => d.value === analysisDepth)?.description}
            </p>
          </div>
        </div>
      </div>

      {/* Generation Progress */}
      {isGenerating && (
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
            <ArrowPathIcon className="w-5 h-5 mr-2 text-gray-600 animate-spin" />
            Generating Report...
          </h3>
          
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className="flex-1 bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: generationProgress.status === 'completed' ? '100%' : '50%' }}
                />
              </div>
              <span className="text-xs text-gray-600">
                {generationProgress.status === 'completed' ? '100%' : '50%'}
              </span>
            </div>
            
            <div className="flex items-start space-x-2">
              <div className="flex-shrink-0 mt-1">
                {generationProgress.status === 'completed' ? (
                  <CheckCircleIcon className="w-5 h-5 text-green-500" />
                ) : generationProgress.status === 'error' ? (
                  <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />
                ) : (
                  <ArrowPathIcon className="w-5 h-5 text-indigo-500 animate-spin" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {generationProgress.message || 'Processing...'}
                </p>
                {generationProgress.currentProcess && (
                  <p className="text-xs text-gray-600 mt-1">
                    Current: {generationProgress.currentProcess}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

TestReportingForm.propTypes = {
  sessionId: PropTypes.string,
  onSetOutput: PropTypes.func,
  disabled: PropTypes.bool,
  process: PropTypes.object,
  onTestCaseGeneration: PropTypes.func
};
