import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { 
  PlayIcon,
  StopIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  CubeIcon,
  ChartBarIcon,
  EyeIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

/**
 * RobotTestExecutionPanel - Robot test execution with Docker integration
 * Features:
 * - Process selection
 * - Test case selection with checkboxes
 * - Visual test selection (Gazebo display)
 * - Parallel execution settings (1-20 containers)
 * - Real-time progress tracking
 * - Results display with validation details
 */
export default function RobotTestExecutionPanel({ sessionId, disabled = false }) {
  // Docker availability
  const [dockerAvailable, setDockerAvailable] = useState(false);
  const [isCheckingDocker, setIsCheckingDocker] = useState(true);

  // Process and test selection
  const [processNames, setProcessNames] = useState([]);
  const [selectedProcessName, setSelectedProcessName] = useState('');
  const [availableTests, setAvailableTests] = useState([]);
  const [selectedTestIds, setSelectedTestIds] = useState([]);
  const [isLoadingTests, setIsLoadingTests] = useState(false);

  // Execution settings
  const [visualTestId, setVisualTestId] = useState('');
  const [maxParallel, setMaxParallel] = useState(5);
  const [dockerImage, setDockerImage] = useState('stlc-robot-ros2:latest');

  // Execution state
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [progress, setProgress] = useState(null);
  const [results, setResults] = useState(null);

  // Polling interval
  const [progressInterval, setProgressInterval] = useState(null);

  /**
   * Check Docker availability on component mount
   */
  useEffect(() => {
    checkDockerHealth();
  }, []);

  /**
   * Fetch available process names when Docker is available
   */
  useEffect(() => {
    if (dockerAvailable) {
      fetchProcessNames();
    }
  }, [dockerAvailable]);

  /**
   * Fetch tests when process is selected
   */
  useEffect(() => {
    if (selectedProcessName) {
      fetchAvailableTests(selectedProcessName);
    } else {
      setAvailableTests([]);
      setSelectedTestIds([]);
      setVisualTestId('');
    }
  }, [selectedProcessName]);

  /**
   * Clear progress polling on unmount
   */
  useEffect(() => {
    return () => {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
    };
  }, [progressInterval]);

  /**
   * Check if Docker is available
   */
  const checkDockerHealth = async () => {
    setIsCheckingDocker(true);
    try {
      const response = await fetch('/api/robot-execution/health');
      const data = await response.json();
      setDockerAvailable(data.docker_available);
      if (!data.docker_available) {
        toast.error('Docker is not available. Please start Docker Desktop.');
      }
    } catch (error) {
      console.error('Error checking Docker health:', error);
      setDockerAvailable(false);
      toast.error('Failed to check Docker status');
    } finally {
      setIsCheckingDocker(false);
    }
  };

  /**
   * Fetch available process names from session history
   */
  const fetchProcessNames = async () => {
    try {
      // Use the new endpoint that returns process names with generated tests
      const response = await fetch('/api/processes/test-code-generation/process-names');
      const data = await response.json();
      
      if (data.success && data.process_names) {
        setProcessNames(data.process_names);
        if (data.process_names.length === 0) {
          toast.info('No processes with generated tests found. Please generate test codes first.');
        }
      }
    } catch (error) {
      console.error('Error fetching process names:', error);
      toast.error('Failed to fetch process names');
    }
  };

  /**
   * Fetch available tests for selected process
   */
  const fetchAvailableTests = async (processName) => {
    setIsLoadingTests(true);
    try {
      const response = await fetch(
        `/api/processes/test-code-generation/tests/${encodeURIComponent(processName)}`
      );
      const data = await response.json();

      if (data.success && data.tests) {
        // Filter only successful tests
        const successfulTests = data.tests.filter(test => test.status === 'success');
        
        // Tests now have unique_id - no deduplication needed
        setAvailableTests(successfulTests);
        
        // Auto-select all tests using unique_id
        const uniqueIds = successfulTests.map(test => test.unique_id);
        setSelectedTestIds(uniqueIds);
        
        // Set first test as visual test by default
        if (uniqueIds.length > 0) {
          setVisualTestId(uniqueIds[0]);
        }
        
        toast.success(`Found ${successfulTests.length} test codes for "${processName}"`);
      } else {
        setAvailableTests([]);
        setSelectedTestIds([]);
        setVisualTestId('');
        toast.error('No tests found for this process');
      }
    } catch (error) {
      console.error('Error fetching tests:', error);
      setAvailableTests([]);
      toast.error('Failed to fetch tests');
    } finally {
      setIsLoadingTests(false);
    }
  };

  /**
   * Toggle test selection using unique_id
   */
  const toggleTestSelection = (uniqueId) => {
    setSelectedTestIds(prev => {
      if (prev.includes(uniqueId)) {
        const newSelection = prev.filter(id => id !== uniqueId);
        // If visual test was unselected, clear it
        if (uniqueId === visualTestId) {
          setVisualTestId(newSelection.length > 0 ? newSelection[0] : '');
        }
        return newSelection;
      } else {
        return [...prev, uniqueId];
      }
    });
  };

  /**
   * Select all tests
   */
  const selectAllTests = () => {
    const allTestIds = availableTests.map(test => test.test_id);
    setSelectedTestIds(allTestIds);
    if (allTestIds.length > 0 && !visualTestId) {
      setVisualTestId(allTestIds[0]);
    }
  };

  /**
   * Deselect all tests
   */
  const deselectAllTests = () => {
    setSelectedTestIds([]);
    setVisualTestId('');
  };

  /**
   * Execute batch tests
   */
  const executeBatchTests = async () => {
    if (selectedTestIds.length === 0) {
      toast.error('Please select at least one test to execute');
      return;
    }

    if (!dockerAvailable) {
      toast.error('Docker is not available');
      return;
    }

    setIsExecuting(true);
    setProgress(null);
    setResults(null);

    try {
      // Start batch execution
      const response = await fetch('/api/robot-execution/execute-batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          process_name: selectedProcessName,
          test_ids: selectedTestIds,
          max_parallel: maxParallel,
          visual_test_id: visualTestId || null,
          docker_image: dockerImage,
          enable_gazebo_recording: false
        })
      });

      const data = await response.json();

      if (data.session_id) {
        setCurrentSessionId(data.session_id);
        toast.success(`Batch execution started: ${data.session_id}`);
        
        // Start polling for progress
        const interval = setInterval(() => {
          pollProgress(data.session_id);
        }, 3000); // Poll every 3 seconds
        
        setProgressInterval(interval);
      } else {
        throw new Error('No session ID returned');
      }
    } catch (error) {
      console.error('Error starting batch execution:', error);
      toast.error('Failed to start batch execution');
      setIsExecuting(false);
    }
  };

  /**
   * Poll execution progress
   */
  const pollProgress = async (sessionId) => {
    try {
      const response = await fetch(`/api/robot-execution/progress/${sessionId}`);
      const data = await response.json();

      setProgress(data);

      // Check if execution is complete
      if (data.status === 'completed' || data.status === 'failed') {
        // Stop polling
        if (progressInterval) {
          clearInterval(progressInterval);
          setProgressInterval(null);
        }

        // Fetch final results
        await fetchResults(sessionId);
        setIsExecuting(false);

        if (data.status === 'completed') {
          toast.success('Batch execution completed!');
        } else {
          toast.error('Batch execution failed');
        }
      }
    } catch (error) {
      console.error('Error polling progress:', error);
    }
  };

  /**
   * Fetch execution results
   */
  const fetchResults = async (sessionId) => {
    try {
      const response = await fetch(`/api/robot-execution/results/${sessionId}`);
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Error fetching results:', error);
      toast.error('Failed to fetch results');
    }
  };

  /**
   * Stop execution
   */
  const stopExecution = () => {
    if (progressInterval) {
      clearInterval(progressInterval);
      setProgressInterval(null);
    }
    setIsExecuting(false);
    toast.info('Execution monitoring stopped');
  };

  /**
   * Format duration in seconds to readable string
   */
  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">🤖 Robot Test Execution</h2>
            <p className="text-blue-100 mt-1">Execute robot tests in Docker containers with real-time monitoring</p>
          </div>
          <CubeIcon className="w-16 h-16 opacity-50" />
        </div>
      </div>

      {/* Docker Status */}
      <div className={clsx(
        'p-4 rounded-lg border-2',
        dockerAvailable 
          ? 'bg-green-50 border-green-200' 
          : 'bg-red-50 border-red-200'
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {dockerAvailable ? (
              <CheckCircleIcon className="w-6 h-6 text-green-600" />
            ) : (
              <XCircleIcon className="w-6 h-6 text-red-600" />
            )}
            <div>
              <p className={clsx(
                'font-semibold',
                dockerAvailable ? 'text-green-800' : 'text-red-800'
              )}>
                Docker Status: {dockerAvailable ? 'Available' : 'Unavailable'}
              </p>
              <p className="text-sm text-gray-600">
                {dockerAvailable 
                  ? 'Ready to execute robot tests' 
                  : 'Please start Docker Desktop to continue'}
              </p>
            </div>
          </div>
          <button
            onClick={checkDockerHealth}
            disabled={isCheckingDocker}
            className="px-4 py-2 bg-white rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
          >
            {isCheckingDocker ? 'Checking...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Process Selection */}
      {dockerAvailable && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Process
          </label>
          <select
            value={selectedProcessName}
            onChange={(e) => setSelectedProcessName(e.target.value)}
            disabled={disabled || isExecuting}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">-- Select a process --</option>
            {processNames.map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Test Selection */}
      {selectedProcessName && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800">
              Available Tests ({availableTests.length})
            </h3>
            <div className="space-x-2">
              <button
                onClick={selectAllTests}
                disabled={disabled || isExecuting}
                className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
              >
                Select All
              </button>
              <button
                onClick={deselectAllTests}
                disabled={disabled || isExecuting}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
              >
                Deselect All
              </button>
            </div>
          </div>

          {isLoadingTests ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-gray-600 mt-4">Loading tests...</p>
            </div>
          ) : availableTests.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No tests found for this process
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {availableTests.map((test) => (
                <div
                  key={test.unique_id}
                  className={clsx(
                    'p-4 rounded-lg border-2 cursor-pointer transition-all',
                    selectedTestIds.includes(test.unique_id)
                      ? 'bg-blue-50 border-blue-300'
                      : 'bg-gray-50 border-gray-200 hover:border-gray-300'
                  )}
                  onClick={() => !disabled && !isExecuting && toggleTestSelection(test.unique_id)}
                >
                  <div className="flex items-start space-x-3">
                    <input
                      type="checkbox"
                      checked={selectedTestIds.includes(test.unique_id)}
                      onChange={() => {}}
                      className="mt-1 w-5 h-5 text-blue-600"
                      disabled={disabled || isExecuting}
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <p className="font-semibold text-gray-800">{test.test_id}</p>
                          <span className="text-xs text-gray-400 font-mono">({test.unique_id.slice(0, 8)}...)</span>
                        </div>
                        {visualTestId === test.unique_id && (
                          <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full flex items-center space-x-1">
                            <EyeIcon className="w-4 h-4" />
                            <span>Visual Test</span>
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{test.test_case_name}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Execution Settings */}
      {selectedTestIds.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-800">Execution Settings</h3>

          {/* Visual Test Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <div className="flex items-center space-x-2">
                <EyeIcon className="w-5 h-5" />
                <span>Visual Test (Gazebo Display)</span>
              </div>
            </label>
            <select
              value={visualTestId}
              onChange={(e) => setVisualTestId(e.target.value)}
              disabled={disabled || isExecuting}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">-- No visual test (headless only) --</option>
              {selectedTestIds.map((testId, index) => {
                const test = availableTests.find(t => t.test_id === testId);
                return (
                  <option key={`${testId}-${index}`} value={testId}>
                    {test?.test_id} - {test?.test_case_name}
                  </option>
                );
              })}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              This test will run in GUI mode with Gazebo visualization
            </p>
          </div>

          {/* Parallel Execution */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Cog6ToothIcon className="w-5 h-5" />
                  <span>Parallel Containers: {maxParallel}</span>
                </div>
                <span className="text-xs text-gray-500">
                  (Headless tests only)
                </span>
              </div>
            </label>
            <input
              type="range"
              min="1"
              max="20"
              value={maxParallel}
              onChange={(e) => setMaxParallel(parseInt(e.target.value))}
              disabled={disabled || isExecuting}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>10</span>
              <span>20</span>
            </div>
          </div>

          {/* Docker Image */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Docker Image
            </label>
            <input
              type="text"
              value={dockerImage}
              onChange={(e) => setDockerImage(e.target.value)}
              disabled={disabled || isExecuting}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="stlc-robot-ros2:latest"
            />
          </div>

          {/* Execute Button */}
          <button
            onClick={executeBatchTests}
            disabled={disabled || isExecuting || !dockerAvailable}
            className={clsx(
              'w-full py-3 px-6 rounded-lg font-semibold text-white transition-all',
              'flex items-center justify-center space-x-2',
              isExecuting
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700'
            )}
          >
            {isExecuting ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Executing...</span>
              </>
            ) : (
              <>
                <PlayIcon className="w-5 h-5" />
                <span>Execute {selectedTestIds.length} Test{selectedTestIds.length !== 1 ? 's' : ''}</span>
              </>
            )}
          </button>

          {isExecuting && (
            <button
              onClick={stopExecution}
              className="w-full py-2 px-4 rounded-lg font-semibold text-red-600 border-2 border-red-600 hover:bg-red-50 transition-all flex items-center justify-center space-x-2"
            >
              <StopIcon className="w-5 h-5" />
              <span>Stop Monitoring</span>
            </button>
          )}
        </div>
      )}

      {/* Progress Display */}
      {progress && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Execution Progress</h3>
          
          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Progress: {progress.progress_percentage?.toFixed(1) || 0}%</span>
              <span>{progress.completed_tests || 0} / {progress.total_tests || 0} tests</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-600 to-purple-600 h-4 transition-all duration-500 flex items-center justify-center"
                style={{ width: `${progress.progress_percentage || 0}%` }}
              >
                {progress.progress_percentage > 10 && (
                  <span className="text-xs text-white font-semibold">
                    {progress.progress_percentage?.toFixed(0)}%
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Status Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-green-50 rounded-lg p-4 border-2 border-green-200">
              <div className="flex items-center space-x-2 mb-1">
                <CheckCircleIcon className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-green-800">Passed</span>
              </div>
              <p className="text-2xl font-bold text-green-600">{progress.passed_tests || 0}</p>
            </div>

            <div className="bg-red-50 rounded-lg p-4 border-2 border-red-200">
              <div className="flex items-center space-x-2 mb-1">
                <XCircleIcon className="w-5 h-5 text-red-600" />
                <span className="text-sm font-medium text-red-800">Failed</span>
              </div>
              <p className="text-2xl font-bold text-red-600">{progress.failed_tests || 0}</p>
            </div>

            <div className="bg-blue-50 rounded-lg p-4 border-2 border-blue-200">
              <div className="flex items-center space-x-2 mb-1">
                <ClockIcon className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-blue-800">Elapsed</span>
              </div>
              <p className="text-2xl font-bold text-blue-600">
                {formatDuration(progress.elapsed_time)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Results Display */}
      {results && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800">Execution Results</h3>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">Success Rate:</span>
              <span className={clsx(
                'px-3 py-1 rounded-full text-sm font-bold',
                results.success_rate >= 80 ? 'bg-green-100 text-green-700' :
                results.success_rate >= 50 ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              )}>
                {results.success_rate?.toFixed(1) || 0}%
              </span>
            </div>
          </div>

          {/* Results Summary */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Total Tests</p>
              <p className="text-2xl font-bold text-gray-800">{results.results?.length || 0}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Total Duration</p>
              <p className="text-2xl font-bold text-gray-800">{formatDuration(results.total_duration)}</p>
            </div>
          </div>

          {/* Individual Test Results */}
          <div className="space-y-3">
            {results.results?.map((result, index) => (
              <div
                key={index}
                className={clsx(
                  'p-4 rounded-lg border-2',
                  result.result === 'PASSED' 
                    ? 'bg-green-50 border-green-200' 
                    : 'bg-red-50 border-red-200'
                )}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {result.result === 'PASSED' ? (
                      <CheckCircleIcon className="w-6 h-6 text-green-600" />
                    ) : (
                      <XCircleIcon className="w-6 h-6 text-red-600" />
                    )}
                    <div>
                      <p className="font-semibold text-gray-800">{result.test_id}</p>
                      <p className="text-sm text-gray-600">{result.test_case_name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={clsx(
                      'px-3 py-1 rounded-full text-sm font-bold',
                      result.result === 'PASSED' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    )}>
                      {result.result}
                    </span>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatDuration(result.execution_time)}
                    </p>
                  </div>
                </div>

                {/* Validation Details */}
                {result.validation_results && result.validation_results.length > 0 && (
                  <div className="mt-3 space-y-1">
                    <p className="text-xs font-semibold text-gray-700">Validation Results:</p>
                    {result.validation_results.map((validation, vIdx) => (
                      <div key={vIdx} className="flex items-center space-x-2 text-xs">
                        {validation.passed ? (
                          <CheckCircleIcon className="w-4 h-4 text-green-600" />
                        ) : (
                          <XCircleIcon className="w-4 h-4 text-red-600" />
                        )}
                        <span className="text-gray-700">{validation.check_name}:</span>
                        <span className={validation.passed ? 'text-green-700' : 'text-red-700'}>
                          {validation.message}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
