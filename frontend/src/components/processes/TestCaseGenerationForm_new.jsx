import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import PropTypes from 'prop-types';

export default function TestCaseGenerationForm({ onRun, process, sessionId }) {
  const [availableProcessTitles, setAvailableProcessTitles] = useState([]);
  const [selectedProcessTitle, setSelectedProcessTitle] = useState('');
  const [selectedProcessData, setSelectedProcessData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load available process titles on component mount
  useEffect(() => {
    loadProcessTitles();
  }, []);

  // Load process data when a process title is selected
  useEffect(() => {
    if (selectedProcessTitle) {
      const selectedProcess = availableProcessTitles.find(p => p.process_title === selectedProcessTitle);
      if (selectedProcess) {
        loadProcessData(selectedProcess.session_id);
      }
    } else {
      setSelectedProcessData(null);
    }
  }, [selectedProcessTitle, availableProcessTitles]);

  const loadProcessTitles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch('/api/processes/test-scenario-generation/process-titles');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.status === 'success') {
        setAvailableProcessTitles(result.process_titles || []);
        console.log('[TestCaseGeneration] Loaded process titles:', result.process_titles);
      } else {
        throw new Error(result.message || 'Failed to load process titles');
      }
      
    } catch (error) {
      console.error('[TestCaseGeneration] Error loading process titles:', error);
      setError('Failed to load available test scenario processes');
      toast.error('Failed to load available test scenario processes');
    } finally {
      setIsLoading(false);
    }
  };

  const loadProcessData = async (sessionId) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`/api/processes/test-scenario-generation/process-data/${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.status === 'success') {
        setSelectedProcessData(result.data);
        console.log('[TestCaseGeneration] Loaded process data:', result.data);
      } else {
        throw new Error(result.message || 'Failed to load process data');
      }
      
    } catch (error) {
      console.error('[TestCaseGeneration] Error loading process data:', error);
      setError('Failed to load test scenario data');
      toast.error('Failed to load test scenario data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateTestCases = async () => {
    if (!selectedProcessData) {
      toast.error('Please select a test scenario process first');
      return;
    }

    try {
      setIsLoading(true);
      
      // Call the parent onRun function with the selected process data
      const testCaseConfig = {
        sessionId: sessionId,
        sourceSessionId: selectedProcessData.session_id, // Reference to the original test scenario
        processTitle: `Test Cases for ${selectedProcessData.process_title}`,
        testType: selectedProcessData.test_type,
        testCategory: selectedProcessData.test_category,
        testScenarios: selectedProcessData.test_scenarios
      };

      console.log('[TestCaseGeneration] Generating test cases with config:', testCaseConfig);
      
      if (onRun && typeof onRun === 'function') {
        await onRun('test-case-generation', testCaseConfig);
        toast.success('Test case generation started successfully!');
      } else {
        toast.error('Test case generation function not available');
      }
      
    } catch (error) {
      console.error('[TestCaseGeneration] Error generating test cases:', error);
      toast.error('Failed to start test case generation');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <form className="space-y-6">
        {/* Process Title Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Test Scenario Process <span className="text-red-500">*</span>
          </label>
          <select
            value={selectedProcessTitle}
            onChange={(e) => setSelectedProcessTitle(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            disabled={isLoading}
          >
            <option value="">Select a test scenario process...</option>
            {availableProcessTitles.map((process, index) => (
              <option key={index} value={process.process_title}>
                {process.process_title} ({process.test_type} - {process.test_category})
              </option>
            ))}
          </select>
          {isLoading && (
            <p className="text-sm text-gray-500 mt-1">Loading available processes...</p>
          )}
          {error && (
            <p className="text-sm text-red-500 mt-1">{error}</p>
          )}
        </div>

        {/* Selected Process Data Display */}
        {selectedProcessData && (
          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Selected Test Scenario Details</h3>
            
            {/* Process Information - Read Only */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Process Title</label>
                <input
                  type="text"
                  value={selectedProcessData.process_title}
                  className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm"
                  readOnly
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Test Type</label>
                <input
                  type="text"
                  value={selectedProcessData.test_type}
                  className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm"
                  readOnly
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Test Category</label>
                <input
                  type="text"
                  value={selectedProcessData.test_category}
                  className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm"
                  readOnly
                />
              </div>
            </div>

            {/* Test Scenarios Display */}
            {selectedProcessData.test_scenarios && selectedProcessData.test_scenarios.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Test Scenarios ({selectedProcessData.test_scenarios.length} scenarios)
                </label>
                <div className="max-h-96 overflow-y-auto border border-gray-300 rounded-md">
                  {selectedProcessData.test_scenarios.map((scenario, index) => (
                    <div key={index} className="p-3 border-b border-gray-200 last:border-b-0 bg-white">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 mb-1">
                            Scenario #{index + 1}
                          </h4>
                          <p className="text-sm text-gray-700 whitespace-pre-wrap">
                            {scenario.scenario || scenario}
                          </p>
                          {scenario.description && (
                            <p className="text-sm text-gray-600 mt-2 italic">
                              {scenario.description}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Generate Test Cases Button */}
            <div className="pt-4">
              <button
                type="button"
                onClick={handleGenerateTestCases}
                className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
                disabled={!selectedProcessData || isLoading}
              >
                {isLoading ? 'Generating...' : 'Generate Test Cases'}
              </button>
            </div>
          </div>
        )}

        {!selectedProcessData && !isLoading && selectedProcessTitle && (
          <div className="text-center py-8">
            <p className="text-gray-500">No data found for the selected process.</p>
          </div>
        )}
      </form>
    </div>
  );
}

TestCaseGenerationForm.propTypes = {
  onRun: PropTypes.func,
  process: PropTypes.object,
  sessionId: PropTypes.string.isRequired
};
