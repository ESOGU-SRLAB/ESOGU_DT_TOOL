import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { toast } from 'react-hot-toast';
import { 
  DocumentCheckIcon,
  ArrowPathIcon,
  CalendarIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import { useSelector } from 'react-redux';
import { useModels } from '../../hooks/useModels';

/**
 * TestClosureForm Component
 * Handles AI-powered test cycle closure report generation
 */
export default function TestClosureForm({ onComplete, onSetOutput }) {
  const { models, loading: modelsLoading } = useModels();
  const apiKeys = useSelector((state) => state.apiKey.apiKeys);
  
  // State management
  const [sessions, setSessions] = useState([]);
  const [selectedSessions, setSelectedSessions] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingMetrics, setFetchingMetrics] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [report, setReport] = useState(null);

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
      const params = new URLSearchParams();
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);

      const response = await fetch(
        `http://localhost:8000/api/test-closure/available-sessions?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        setSessions(data.sessions || []);
        toast.success(`Found ${data.total_count} sessions`);
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
      const response = await fetch('http://localhost:8000/api/test-closure/metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_ids: selectedSessions,
          date_from: dateFrom || null,
          date_to: dateTo || null
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
   * Generate AI-powered closure report
   */
  const generateClosureReport = async () => {
    if (selectedSessions.length === 0) {
      toast.error('Please select at least one session');
      return;
    }

    if (!selectedModel) {
      toast.error('Please select a model');
      return;
    }

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
        date_from: dateFrom || null,
        date_to: dateTo || null,
        model: selectedModel,
        api_key: apiKeyToUse
      };
      
      console.log('[TestClosure] Sending request to backend:');
      console.log('  - Endpoint:', 'http://localhost:8000/api/test-closure/generate-report');
      console.log('  - Selected Model:', selectedModel);
      console.log('  - Model Object:', models.find(m => m.key === selectedModel));
      console.log('  - Request Body:', JSON.stringify(requestBody, null, 2));
      
      const response = await fetch('http://localhost:8000/api/test-closure/generate-report', {
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
        toast.success('Closure report generated successfully');
        
        // Show success output in OutputPanel
        const successOutput = {
          status: 'completed',
          content: data.report_content,
          timestamp: new Date().toISOString(),
          model: selectedModel,
          processType: 'Test Closure',
          metrics: data.metrics,
          sessions_analyzed: data.sessions_analyzed
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
  };

  /**
   * Download report as markdown file
   */
  const downloadReport = () => {
    if (!report) return;

    const blob = new Blob([report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test-closure-report-${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Report downloaded');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg p-6 text-white">
        <div className="flex items-center gap-3">
          <DocumentCheckIcon className="w-8 h-8" />
          <div>
            <h2 className="text-2xl font-bold">Test Closure</h2>
            <p className="text-purple-100 mt-1">
              AI-powered test cycle closure report generation
            </p>
          </div>
        </div>
      </div>

      {/* Date Range Filter */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <CalendarIcon className="w-5 h-5" />
          Date Range Filter
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              From Date
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              To Date
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={fetchAvailableSessions}
              disabled={loading}
              className="w-full px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-300 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <ArrowPathIcon className="w-5 h-5" />
                  Refresh Sessions
                </>
              )}
            </button>
          </div>
        </div>
      </div>

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
            {sessions.map((session) => (
              <div
                key={session.session_id}
                onClick={() => toggleSession(session.session_id)}
                className={clsx(
                  'p-4 border rounded-lg cursor-pointer transition-all',
                  selectedSessions.includes(session.session_id)
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-gray-200 hover:border-purple-300'
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={selectedSessions.includes(session.session_id)}
                      onChange={() => {}}
                      className="w-5 h-5 text-purple-600 rounded"
                    />
                    <div>
                      <p className="font-medium text-gray-900">
                        {session.session_id.substring(0, 8)}...
                      </p>
                      <p className="text-sm text-gray-500">
                        {new Date(session.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-700">
                      {session.process_count} processes
                    </p>
                    <p className="text-xs text-gray-500">
                      {session.processes.join(', ')}
                    </p>
                  </div>
                </div>
              </div>
            ))}
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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          onClick={calculateMetrics}
          disabled={selectedSessions.length === 0 || fetchingMetrics}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 flex items-center justify-center gap-2 font-medium"
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

        <button
          onClick={generateClosureReport}
          disabled={selectedSessions.length === 0 || !selectedModel || generatingReport}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 flex items-center justify-center gap-2 font-medium"
        >
          {generatingReport ? (
            <>
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
              Generating AI Report...
            </>
          ) : (
            <>
              <DocumentCheckIcon className="w-5 h-5" />
              Generate AI Closure Report
            </>
          )}
        </button>
      </div>

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
  onSetOutput: PropTypes.func
};
