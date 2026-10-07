import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  PlayIcon,
  StopIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

/**
 * ParallelDockerExecutionPanel
 * 
 * Real-time monitoring dashboard for parallel Docker test execution
 * Shows live progress, statistics, and individual test results
 */
export default function ParallelDockerExecutionPanel({
  processName,
  selectedTests,
  additionalPackages,
  dockerTimeout,
  onExecutionComplete,
  onSetOutput
}) {
  // Execution state
  const [isExecuting, setIsExecuting] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [maxParallel, setMaxParallel] = useState(5);
  
  // Progress state
  const [progress, setProgress] = useState(null);
  const [results, setResults] = useState(null);
  
  // Polling interval
  const [pollingInterval, setPollingInterval] = useState(null);
  
  // Start parallel execution
  const startExecution = async () => {
    if (selectedTests.length === 0) {
      toast.error('Please select at least one test');
      return;
    }
    
    setIsExecuting(true);
    setProgress(null);
    setResults(null);
    
    const startOutput = {
      status: 'running',
      content: `🐳 **Starting Parallel Docker Execution**

📊 **Configuration:**
- Total Tests: ${selectedTests.length}
- Parallel Containers: ${maxParallel}
- Process: ${processName}
- Timeout per test: ${dockerTimeout}s
- Additional Packages: ${additionalPackages || 'None'}

🚀 **Execution Mode:**
✅ Tests run in isolated Docker containers
✅ Multiple tests execute simultaneously
✅ Real-time progress monitoring
✅ Automatic resource cleanup

⏳ Initializing containers and starting execution...`,
      timestamp: new Date().toISOString(),
      processType: 'Parallel Docker Execution'
    };
    
    if (onSetOutput) {
      onSetOutput('test-execution', startOutput);
    }
    
    try {
      const response = await fetch('/api/docker-execution/parallel/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          process_name: processName,
          test_ids: selectedTests,
          language: 'python',
          max_parallel: maxParallel,
          timeout: dockerTimeout,
          additional_packages: additionalPackages 
            ? additionalPackages.split(',').map(p => p.trim()).filter(p => p)
            : null
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSessionId(data.session_id);
        toast.success(`Parallel execution started: ${data.total_tests} tests`);
        
        // Start polling for progress
        startProgressPolling(data.session_id);
      } else {
        throw new Error(data.message || 'Failed to start execution');
      }
      
    } catch (error) {
      console.error('Execution start error:', error);
      toast.error('Failed to start parallel execution');
      setIsExecuting(false);
      
      const errorOutput = {
        status: 'error',
        content: `❌ **Execution Start Failed**\n\n${error.message}`,
        timestamp: new Date().toISOString(),
        processType: 'Parallel Docker Execution'
      };
      
      if (onSetOutput) {
        onSetOutput('test-execution', errorOutput);
      }
    }
  };
  
  // Poll for execution progress
  const startProgressPolling = (sessionId) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `/api/docker-execution/parallel/progress/${sessionId}`
        );
        const data = await response.json();
        
        setProgress(data);
        
        // Check if execution is complete
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          clearInterval(interval);
          setPollingInterval(null);
          setIsExecuting(false);
          
          // Fetch final results
          await fetchResults(sessionId);
        }
        
      } catch (error) {
        console.error('Progress polling error:', error);
      }
    }, 2000); // Poll every 2 seconds
    
    setPollingInterval(interval);
  };
  
  // Fetch detailed results
  const fetchResults = async (sessionId) => {
    try {
      const response = await fetch(
        `/api/docker-execution/parallel/results/${sessionId}`
      );
      const data = await response.json();
      
      setResults(data);
      
      // Generate completion output
      const stats = data.statistics;
      const jobs = data.jobs || [];
      
      const passedJobs = jobs.filter(j => j.status === 'completed');
      const failedJobs = jobs.filter(j => j.status === 'failed');
      
      const completionOutput = {
        status: stats.failed === 0 ? 'success' : 'warning',
        content: `🐳 **Parallel Docker Execution ${stats.failed === 0 ? 'Completed Successfully' : 'Completed with Failures'}**

📊 **Final Statistics:**
- Total Tests: ${stats.total_tests}
- ✅ Passed: ${stats.completed}
- ❌ Failed: ${stats.failed}
- 📈 Success Rate: ${stats.success_rate}%
- ⏱️ Total Time: ${data.execution_time.total_seconds?.toFixed(2)}s

---

${passedJobs.length > 0 ? `✅ **Passed Tests (${passedJobs.length}):**\n${passedJobs.map(j => `- ${j.test_name} (${j.duration?.toFixed(2)}s)`).join('\n')}\n\n` : ''}${failedJobs.length > 0 ? `❌ **Failed Tests (${failedJobs.length}):**\n${failedJobs.map(j => `- ${j.test_name}: ${j.error || 'Unknown error'}`).join('\n')}\n\n` : ''}---

${stats.failed === 0 
  ? '🎉 **All tests passed successfully!**' 
  : `⚠️ **${stats.failed} test(s) failed.** Review the failures above.`}`,
        timestamp: new Date().toISOString(),
        processType: 'Parallel Docker Execution'
      };
      
      if (onSetOutput) {
        onSetOutput('test-execution', completionOutput);
      }
      
      if (stats.failed === 0) {
        toast.success(`All ${stats.total_tests} tests passed!`);
      } else {
        toast.warning(`${stats.completed} passed, ${stats.failed} failed`);
      }
      
      if (onExecutionComplete) {
        onExecutionComplete(data);
      }
      
    } catch (error) {
      console.error('Error fetching results:', error);
      toast.error('Failed to fetch execution results');
    }
  };
  
  // Cancel execution
  const cancelExecution = async () => {
    if (!sessionId) return;
    
    try {
      await fetch(
        `/api/docker-execution/parallel/cancel/${sessionId}`,
        { method: 'POST' }
      );
      
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
      
      setIsExecuting(false);
      toast.info('Execution cancelled');
      
    } catch (error) {
      console.error('Cancel error:', error);
      toast.error('Failed to cancel execution');
    }
  };
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);
  
  return (
    <div className="space-y-4">
      {/* Configuration Panel */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-blue-900 mb-3 flex items-center">
          <CpuChipIcon className="w-5 h-5 mr-2" />
          Parallel Execution Configuration
        </h4>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Parallel Containers
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={maxParallel}
              onChange={(e) => setMaxParallel(parseInt(e.target.value))}
              disabled={isExecuting}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            />
            <p className="text-xs text-gray-500 mt-1">
              Run up to {maxParallel} tests simultaneously
            </p>
          </div>
          
          <div className="flex items-end">
            {!isExecuting ? (
              <button
                onClick={startExecution}
                disabled={selectedTests.length === 0}
                className={clsx(
                  'w-full px-4 py-2 rounded-lg font-medium transition-all',
                  'flex items-center justify-center space-x-2',
                  selectedTests.length === 0
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow-md'
                )}
              >
                <PlayIcon className="w-5 h-5" />
                <span>Start Parallel Execution</span>
              </button>
            ) : (
              <button
                onClick={cancelExecution}
                className="w-full px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-all flex items-center justify-center space-x-2"
              >
                <StopIcon className="w-5 h-5" />
                <span>Cancel Execution</span>
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Progress Monitor */}
      {progress && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-semibold text-gray-900 flex items-center">
              <ArrowPathIcon className={clsx('w-5 h-5 mr-2', isExecuting && 'animate-spin')} />
              Execution Progress
            </h4>
            <span className={clsx(
              'px-3 py-1 rounded-full text-xs font-medium',
              progress.status === 'running' && 'bg-blue-100 text-blue-800',
              progress.status === 'completed' && 'bg-green-100 text-green-800',
              progress.status === 'failed' && 'bg-red-100 text-red-800'
            )}>
              {progress.status.toUpperCase()}
            </span>
          </div>
          
          {/* Statistics Grid */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-gray-900">
                {progress.total_tests}
              </div>
              <div className="text-xs text-gray-600 mt-1">Total Tests</div>
            </div>
            
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {progress.running}
              </div>
              <div className="text-xs text-blue-600 mt-1 flex items-center justify-center">
                <ClockIcon className="w-3 h-3 mr-1" />
                Running
              </div>
            </div>
            
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-600">
                {progress.completed}
              </div>
              <div className="text-xs text-green-600 mt-1 flex items-center justify-center">
                <CheckCircleIcon className="w-3 h-3 mr-1" />
                Passed
              </div>
            </div>
            
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-red-600">
                {progress.failed}
              </div>
              <div className="text-xs text-red-600 mt-1 flex items-center justify-center">
                <XCircleIcon className="w-3 h-3 mr-1" />
                Failed
              </div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Progress</span>
              <span className="font-medium text-gray-900">
                {progress.completed + progress.failed} / {progress.total_tests}
                {' '}
                ({Math.round(((progress.completed + progress.failed) / progress.total_tests) * 100)}%)
              </span>
            </div>
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full flex">
                <div
                  className="bg-green-500 transition-all duration-300"
                  style={{ width: `${(progress.completed / progress.total_tests) * 100}%` }}
                />
                <div
                  className="bg-red-500 transition-all duration-300"
                  style={{ width: `${(progress.failed / progress.total_tests) * 100}%` }}
                />
              </div>
            </div>
          </div>
          
          {/* Success Rate */}
          {(progress.completed + progress.failed) > 0 && (
            <div className="mt-4 flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <span className="text-sm text-gray-700">Success Rate</span>
              <span className={clsx(
                'text-lg font-bold',
                progress.success_rate >= 80 ? 'text-green-600' :
                progress.success_rate >= 50 ? 'text-yellow-600' :
                'text-red-600'
              )}>
                {progress.success_rate.toFixed(1)}%
              </span>
            </div>
          )}
          
          {/* Elapsed Time */}
          <div className="mt-3 text-xs text-gray-500 text-center">
            Elapsed: {progress.elapsed_time?.toFixed(1)}s
          </div>
        </div>
      )}
      
      {/* Detailed Results */}
      {results && !isExecuting && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">
            Detailed Results
          </h4>
          
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {results.jobs.map((job) => (
              <div
                key={job.job_id}
                className={clsx(
                  'p-3 rounded-lg border-l-4 text-sm',
                  job.status === 'completed' && 'bg-green-50 border-green-500',
                  job.status === 'failed' && 'bg-red-50 border-red-500'
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">
                      {job.test_name}
                    </div>
                    {job.duration && (
                      <div className="text-xs text-gray-500 mt-1">
                        Duration: {job.duration.toFixed(2)}s
                      </div>
                    )}
                    {job.error && (
                      <div className="text-xs text-red-600 mt-1">
                        Error: {job.error}
                      </div>
                    )}
                  </div>
                  <div>
                    {job.status === 'completed' ? (
                      <CheckCircleIcon className="w-5 h-5 text-green-600" />
                    ) : (
                      <XCircleIcon className="w-5 h-5 text-red-600" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
