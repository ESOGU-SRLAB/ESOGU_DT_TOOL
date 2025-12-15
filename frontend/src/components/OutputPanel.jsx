import React from 'react';
import ReactMarkdown from 'react-markdown';
import { useSelector } from 'react-redux';
import { Gantt, ViewMode } from 'gantt-task-react';
import "gantt-task-react/dist/index.css";
import '../styles/markdown.css'; // Import markdown styling
import TestReportViewer from './reports/TestReportViewer';

// Helper function to safely render children in ReactMarkdown components
const safeRenderChildren = (children) => {
  if (children === null || children === undefined) {
    return '';
  }
  
  // If it's a string or number, return as is
  if (typeof children === 'string' || typeof children === 'number' || typeof children === 'boolean') {
    return children;
  }
  
  // If it's a React element, return the children directly for React to render
  if (React.isValidElement(children)) {
    return children;
  }
  
  // If it's an array, process each item
  if (Array.isArray(children)) {
    return children.map((child, index) => {
      if (React.isValidElement(child)) {
        return React.cloneElement(child, { key: index });
      }
      return safeRenderChildren(child);
    });
  }
  
  // If it's a DOM node, return its text content
  if (children && typeof children === 'object' && children.nodeType) {
    return children.textContent || '';
  }
  
  // For other objects, try to convert to JSON, but handle circular references
  if (typeof children === 'object') {
    try {
      return JSON.stringify(children);
    } catch (error) {
      // If JSON.stringify fails (circular reference), return a safe representation
      if (error.message.includes('circular')) {
        return '[Circular Object]';
      }
      return '[Complex Object]';
    }
  }
  
  return String(children);
};

// Test Case Optimization Results Component
function TestCaseOptimizationResults({ sessionId, liveResults }) {
  const [optimizationResults, setOptimizationResults] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (liveResults) {
      setOptimizationResults(liveResults);
      setLoading(false);
      setError(null);
    } else if (sessionId) {
      fetchOptimizationResults();
    }
  }, [sessionId, liveResults]);
  const fetchOptimizationResults = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // First try to get the process title from the session
      let processTitle = null;
      
      if (sessionId) {
        try {
          const sessionResponse = await fetch(`http://localhost:8000/api/processes/test-scenario-generation/session/${sessionId}`);
          if (sessionResponse.ok) {
            const sessionData = await sessionResponse.json();
            processTitle = sessionData?.processes?.test_case_generation?.selected_process_title || 
                          sessionData?.selected_process_title;
          }
        } catch (err) {
          console.warn('Could not fetch session data, trying alternative approach:', err);
        }
      }
      
      // If no process title from session, get available process titles and use the first one
      if (!processTitle) {
        try {
          const titlesResponse = await fetch('http://localhost:8000/api/test-case-optimization/process-titles');
          if (titlesResponse.ok) {
            const titlesData = await titlesResponse.json();
            if (titlesData.success && titlesData.data.length > 0) {
              processTitle = titlesData.data[0]; // Use first available process title
              console.log('Using first available process title:', processTitle);
            }
          }
        } catch (err) {
          console.warn('Could not fetch process titles:', err);
        }
      }
      
      if (!processTitle) {
        setError('No process title available for optimization results');
        return;
      }

      // Fetch optimization results for this process title
      const response = await fetch(`http://localhost:8000/api/test-case-optimization/results/${encodeURIComponent(processTitle)}`);
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setOptimizationResults(data.data);
        } else {
          setError('No optimization results found');
        }
      } else if (response.status === 404) {
        setError('No optimization results available yet. Run Test Case Optimization first.');
      } else {
        throw new Error(`Failed to fetch optimization results: ${response.status}`);
      }
    } catch (err) {
      console.error('Error fetching optimization results:', err);
      setError(`Error loading optimization results: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500"></div>
          <span className="ml-2 text-gray-600">Loading optimization results...</span>
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
        <div className="text-yellow-800">
          <p className="font-medium">Test Case Optimization</p>
          <p className="text-sm mt-1">{error}</p>
          <div className="flex space-x-2 mt-2">
            <button
              onClick={fetchOptimizationResults}
              className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded text-sm hover:bg-yellow-200"
            >
              Retry
            </button>
            <button
              onClick={() => window.open('/test-case-optimization', '_blank')}
              className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm hover:bg-blue-200"
            >
              Go to Optimization
            </button>
          </div>
        </div>
      </div>
    );
  }
  if (!optimizationResults) {
    return (
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <div className="text-blue-800">
          <p className="font-medium">Test Case Optimization</p>
          <p className="text-sm mt-1">No optimization results available yet. Run Test Case Optimization to see results here.</p>
          <div className="flex space-x-2 mt-2">
            <button
              onClick={fetchOptimizationResults}
              className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm hover:bg-blue-200"
            >
              Check Again
            </button>
            <button
              onClick={() => window.open('/#test-case-optimization', '_blank')}
              className="px-3 py-1 bg-green-100 text-green-800 rounded text-sm hover:bg-green-200"
            >
              Go to Optimization
            </button>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      {/* Refresh Button */}
      <div className="flex justify-end">
        <button
          onClick={fetchOptimizationResults}
          disabled={loading}
          className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:bg-gray-400"
        >
          {loading ? 'Loading...' : 'Refresh Results'}
        </button>
      </div>
      
      {/* Summary Stats */}
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <h4 className="font-medium text-blue-800 mb-2">Optimization Summary</h4>
        <div className="grid grid-cols-3 gap-4 text-sm text-blue-700">
          <div>
            <p className="font-medium">Original Test Cases</p>
            <p className="text-lg">{optimizationResults.total_test_cases || ((optimizationResults.unique_test_cases?.length || 0) + (optimizationResults.similar_test_cases?.length || 0))}</p>
          </div>
          <div>
            <p className="font-medium">Unique Test Cases</p>
            <p className="text-lg text-green-600">{optimizationResults.unique_test_cases?.length || 0}</p>
          </div>
          <div>
            <p className="font-medium">Duplicates Removed</p>
            <p className="text-lg text-red-600">{optimizationResults.similar_test_cases?.length || 0}</p>
          </div>
        </div>
      </div>

      {/* Unique Test Cases */}
      <div className="bg-green-50 border border-green-200 rounded-md p-4">
        <h4 className="font-medium text-green-800 mb-2">
          ✅ Unique Test Cases ({optimizationResults.unique_test_cases?.length || 0})
        </h4>
        <details className="cursor-pointer">
          <summary className="text-sm text-green-700 hover:text-green-900">Click to view details</summary>
          <div className="mt-2 space-y-2">
            {optimizationResults.unique_test_cases?.map((testCase, index) => (
              <div key={index} className="bg-white p-3 rounded border border-green-200">
                <h5 className="font-medium text-gray-900">{testCase.TestCaseID}: {testCase.Title}</h5>
                <p className="text-sm text-gray-600 mt-1">{testCase.Description}</p>
                <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {testCase.Objective}</p>
              </div>
            )) || <p className="text-sm text-gray-500">No unique test cases found.</p>}
          </div>
        </details>
      </div>      {/* Similar Test Cases */}
      {optimizationResults.similar_test_cases?.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <h4 className="font-medium text-yellow-800 mb-2">
            🔄 Similar Test Cases Found ({optimizationResults.similar_test_cases.length})
          </h4>
          <details className="cursor-pointer">
            <summary className="text-sm text-yellow-700 hover:text-yellow-900">Click to view duplicates</summary>
            <div className="mt-2 space-y-3">
              {optimizationResults.similar_test_cases.map((duplicate, index) => (
                <div key={index} className="bg-white p-4 rounded border border-yellow-200">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-red-50 p-3 rounded border border-red-200">
                      <h5 className="font-medium text-red-700 mb-2">🗑️ Duplicate (Removed)</h5>
                      <p className="font-medium text-gray-900">{duplicate.DuplicateCase.TestCaseID}: {duplicate.DuplicateCase.Title}</p>
                      <p className="text-sm text-gray-600 mt-1"><strong>Description:</strong> {duplicate.DuplicateCase.Description}</p>
                      <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {duplicate.DuplicateCase.Objective}</p>
                    </div>
                    <div className="bg-green-50 p-3 rounded border border-green-200">
                      <h5 className="font-medium text-green-700 mb-2">✅ Kept (Original)</h5>
                      <p className="font-medium text-gray-900">{duplicate.MatchedWith.TestCaseID}: {duplicate.MatchedWith.Title}</p>
                      <p className="text-sm text-gray-600 mt-1"><strong>Description:</strong> {duplicate.MatchedWith.Description}</p>
                      <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {duplicate.MatchedWith.Objective}</p>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-yellow-200">
                    <p className="text-xs text-gray-600">
                      <strong>Reason:</strong> These test cases were found to be contextually similar based on their titles, descriptions, and objectives.
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}{/* Comparison Logs Summary */}
      <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
        <h4 className="font-medium text-gray-800 mb-2">
          📊 Comparison Logs ({optimizationResults.total_comparisons || optimizationResults.comparison_logs?.length || 0} comparisons)
        </h4>
        {optimizationResults.comparison_logs?.length > 0 ? (
          <details className="cursor-pointer">
            <summary className="text-sm text-gray-700 hover:text-gray-900">Click to view detailed comparison logs</summary>
            <div className="mt-2 max-h-96 overflow-y-auto">
              <div className="space-y-3">
                {optimizationResults.comparison_logs.map((log, index) => (
                  <div key={index} className="bg-white p-3 rounded border border-gray-200">
                    <div className="flex justify-between items-start mb-2">
                      <h6 className="font-medium text-gray-900">Comparison #{index + 1}</h6>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        log.is_same || log.result?.is_same
                          ? 'bg-red-100 text-red-800' 
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {log.is_same || log.result?.is_same ? 'Similar' : 'Different'}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div className="bg-blue-50 p-2 rounded">
                        <h6 className="font-medium text-blue-800 mb-1">Test Case 1</h6>
                        {(() => {
                          // Flexible key lookup for test case 1
                          const testCase1 = log.test_case_1 || log.Case1 || log.TestCase1 || log.case1;
                          return testCase1 ? (
                            <div className="space-y-1">
                              {Object.entries(testCase1).map(([key, value]) => 
                                value ? (
                                  <div key={key}>
                                    <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                  </div>
                                ) : null
                              )}
                            </div>
                          ) : (
                            <p className="text-gray-500 text-xs">No test case data available</p>
                          );
                        })()}
                      </div>
                      
                      <div className="bg-purple-50 p-2 rounded">
                        <h6 className="font-medium text-purple-800 mb-1">Test Case 2</h6>
                        {(() => {
                          // Flexible key lookup for test case 2
                          const testCase2 = log.test_case_2 || log.Case2 || log.TestCase2 || log.case2;
                          return testCase2 ? (
                            <div className="space-y-1">
                              {Object.entries(testCase2).map(([key, value]) => 
                                value ? (
                                  <div key={key}>
                                    <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                  </div>
                                ) : null
                              )}
                            </div>
                          ) : (
                            <p className="text-gray-500 text-xs">No test case data available</p>
                          );
                        })()}
                      </div>
                    </div>
                    
                    {log.prompt_sent && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                          View prompt sent to LLM
                        </summary>
                        <div className="mt-1 bg-gray-100 p-2 rounded text-xs">
                          <pre className="whitespace-pre-wrap">{log.prompt_sent}</pre>
                        </div>
                      </details>
                    )}
                    
                    {log.llm_response && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                          View LLM response
                        </summary>
                        <div className="mt-1 bg-gray-100 p-2 rounded text-xs">
                          <pre className="whitespace-pre-wrap">{log.llm_response}</pre>
                        </div>
                      </details>
                    )}
                    
                    {/* Debug: Show raw log data */}
                    <details className="mt-2">
                      <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                        View raw comparison data (debug)
                      </summary>
                      <div className="mt-1 bg-gray-50 p-2 rounded text-xs">
                        <pre className="whitespace-pre-wrap">{JSON.stringify(log, null, 2)}</pre>
                      </div>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          </details>
        ) : (
          <p className="text-sm text-gray-600">
            No detailed comparison logs available.
          </p>
        )}
      </div>
    </div>
  );
}

// JSON'dan XML'e dönüştürme fonksiyonu
function jsonToXml(jsonData) {
  try {
    // JSON string ise parse et
    const data = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
    
    // Eğer bir dizi ise
    if (Array.isArray(data)) {
      let xml = '<TestPlan>\n';
      
      data.forEach(task => {
        xml += '  <Task>\n';
        for (const key in task) {
          // Key adını XML tag formatına çevir (boşlukları kaldır)
          const tagName = key.replace(/\s+/g, '');
          xml += `    <${tagName}>${task[key]}</${tagName}>\n`;
        }
        xml += '  </Task>\n';
      });
      
      xml += '</TestPlan>';
      return xml;
    } else {
      // Tek bir obje ise
      let xml = '<TestPlan>\n  <Task>\n';
      
      for (const key in data) {
        const tagName = key.replace(/\s+/g, '');
        xml += `    <${tagName}>${data[key]}</${tagName}>\n`;
      }
      
      xml += '  </Task>\n</TestPlan>';
      return xml;
    }
  } catch (error) {
    console.error('JSON to XML conversion error:', error);
    return `<!-- Error converting JSON to XML: ${error.message} -->`;
  }
}

// JSON formatını Gantt Chart için task listesine dönüştürme
function jsonToGanttTasks(jsonData) {
  try {
    // JSON string ise parse et
    const data = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
    
    if (!Array.isArray(data)) {
      console.error('Gantt data is not an array');
      return [];
    }
    
    // Gantt Chart için task listesi oluştur
    const tasks = [];
    let lastEndDate = null;  // Track last task's end date for sequential planning
    
    for (let index = 0; index < data.length; index++) {
      const task = data[index];
      
      try {
        // Tarihleri parse et
        let startDate = parseDate(task["Start Date"]);
        let endDate = parseDate(task["End Date"]);
        
        // Tarihlerin geçerli olduğunu kontrol et
        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
          console.error(`Invalid date in task ${index}:`, {
            taskName: task["Task Name"],
            startDate: task["Start Date"],
            endDate: task["End Date"]
          });
          continue; // Bu task'ı atla
        }
        
        // End date start date'ten önce olamaz
        if (endDate < startDate) {
          console.warn(`End date before start date in task ${index}, swapping`);
          [startDate, endDate] = [endDate, startDate];
        }
        
        // Aynı gün başlayıp biten task'lar için minimum 1 gün ekle
        if (startDate.getTime() === endDate.getTime()) {
          console.warn(`Task ${index} starts and ends on same day, adding 1 day duration`);
          endDate = new Date(startDate);
          endDate.setDate(endDate.getDate() + 1);
        }
        
        // If this task starts same as previous task (LLM error), fix it sequentially
        if (lastEndDate && startDate.getTime() === lastEndDate.getTime() - (24 * 60 * 60 * 1000)) {
          console.warn(`Task ${index} overlaps with previous task, adjusting to sequential`);
          startDate = new Date(lastEndDate);
          // Keep the duration if specified
          const duration = task["Duration (days)"] || 1;
          endDate = new Date(startDate);
          endDate.setDate(endDate.getDate() + parseInt(duration) - 1);
        }
        
        tasks.push({
          id: `task-${index}`,
          name: task["Task Name"] || `Task ${index + 1}`,
          start: startDate,
          end: endDate,
          progress: 0, // Varsayılan ilerleme
          type: 'task',
          isDisabled: false,
          styles: { progressColor: '#0275d8', progressSelectedColor: '#0275d8' }
        });
        
        // Update lastEndDate for next iteration
        lastEndDate = new Date(endDate);
        lastEndDate.setDate(lastEndDate.getDate() + 1); // Add 1 day gap
        
      } catch (taskError) {
        console.error(`Error processing task ${index}:`, taskError, task);
        // Bu task'ı atla, diğerlerine devam et
      }
    }
    
    console.log(`Successfully converted ${tasks.length} tasks for Gantt chart`);
    return tasks;
    
  } catch (error) {
    console.error('JSON to Gantt conversion error:', error);
    return [];
  }
}

// Tarih formatlarını işleme
function parseDate(dateStr) {
  if (!dateStr) {
    console.warn('Empty date string, using current date');
    return new Date();
  }
  
  // String'e çevir (number veya object olabilir)
  const dateString = String(dateStr).trim();
  
  // YYYY-MM-DD formatını kontrol et
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
    const date = new Date(dateString + 'T00:00:00');
    if (isNaN(date.getTime())) {
      console.error('Invalid date format:', dateString);
      return new Date();
    }
    return date;
  }
  
  // {today}+N veya today+N formatını işle
  const todayPlusMatch = dateString.match(/\{?today\}?\s*\+\s*(\d+)/i);
  if (todayPlusMatch) {
    const daysToAdd = parseInt(todayPlusMatch[1], 10) || 0;
    const result = new Date();
    result.setDate(result.getDate() + daysToAdd);
    console.log(`Parsed ${dateString} as ${result.toISOString().split('T')[0]}`);
    return result;
  }
  
  // ISO string formatı
  if (dateString.includes('T') || dateString.includes('Z')) {
    const date = new Date(dateString);
    if (!isNaN(date.getTime())) {
      return date;
    }
  }
  
  // Son çare: Date constructor'a gönder
  const fallbackDate = new Date(dateString);
  if (!isNaN(fallbackDate.getTime())) {
    return fallbackDate;
  }
  
  // Hiçbir şey işe yaramazsa bugünün tarihini döndür
  console.error('Could not parse date:', dateString, '- using current date');
  return new Date();
}

// Görevlerin toplam süresine göre uygun görünümü ve sütun genişliğini seçen fonksiyon
function getGanttViewModeAndColumnWidth(tasks) {
  if (!tasks || tasks.length === 0) {
    return { viewMode: ViewMode.Week, columnWidth: 50 };
  }
  // En erken başlangıç ve en geç bitiş tarihini bul
  const minDate = new Date(Math.min(...tasks.map(t => t.start)));
  const maxDate = new Date(Math.max(...tasks.map(t => t.end)));
  const diffDays = Math.ceil((maxDate - minDate) / (1000 * 60 * 60 * 24));

  if (diffDays > 365) {
    return { viewMode: ViewMode.Year, columnWidth: 60 };
  } else if (diffDays > 90) {
    return { viewMode: ViewMode.Month, columnWidth: 60 };
  } else if (diffDays > 30) {
    return { viewMode: ViewMode.Week, columnWidth: 50 };
  } else {
    return { viewMode: ViewMode.Day, columnWidth: 40 };
  }
}

export default function OutputPanel({ output, outputs, activeTab, processes, outputFormats, hideFooter, hideHeader, testCaseOptimizationResults }) {
  const { status: codeReviewStatus, reviews, error: codeReviewError } = useSelector(state => state.codeReview || {});
  const { status: reqStatus, result: reqResult, error: reqError } = useSelector(state => state.requirementAnalysis || {});
  const { status: testPlanningStatus, plans, error: testPlanningError } = useSelector(state => state.testPlanning || {});
  const { status: envSetupStatus, setups, error: envSetupError } = useSelector(state => state.environmentSetup || {});

  const processId = activeTab !== 'pipeline' && activeTab !== 'files' ? activeTab : null;
  const selectedProcess = processes?.find(p => p.id === processId);
  
  // Get output from outputs object (new way) or from output prop (legacy way)
  const processOutput = processId && outputs && outputs[processId] 
    ? outputs[processId] 
    : (processId && output && output.processId === processId ? output : null);
    
  const processName = selectedProcess?.name || '';
  const headerTitle = processId ? `${processName} Output` : 'Output';
  
  // Seçilen output formatını al
  const selectedOutputFormat = outputFormats?.[processId];

  const getSampleOutput = () => {
    if (!processId) return null;
    const samples = {
      'code-review': {
        content: "## Code Review Results\n\n### main.js\n- Function `calculateTotal()` lacks input validation\n- Consider adding error handling for edge cases\n\n### utils.js\n- Good use of modular design\n- Line 42: Potential memory leak in event listener",
        status: 'sample',
        timestamp: new Date().toISOString()
      },
      'test-planning': {
        content: "## Test Planning Document\n\n### Test Objectives\n1. Validate user authentication flows\n2. Verify data integrity across transactions\n\n### Test Scenarios\n- Login with valid credentials\n- Login with invalid credentials\n- Password reset flow",
        status: 'sample',
        timestamp: new Date().toISOString()
      },
      'requirement-analysis': {
        content: "## Requirements Analysis\n\n### Functional Requirements\n- User registration system\n- Product catalog browsing\n- Shopping cart functionality\n\n### Non-Functional Requirements\n- System should support 1000 concurrent users\n- Page load time < 2 seconds",
        status: 'sample',
        timestamp: new Date().toISOString()
      },
      'environment-setup': {
        content: "## Environment Setup Guide\n\n### Development Environment\n```\nnpm install\nnpm run setup-dev\n```\n\n### Testing Environment\n```\ndocker-compose up -d\nnpm run setup-test\n```",
        status: 'sample',
        timestamp: new Date().toISOString()
      },
      'test-scenario-generation': {
        content: "## Generated Test Scenarios\n\n### User Authentication\n1. **TC001**: Verify login with valid username and password\n2. **TC002**: Verify login with invalid credentials\n3. **TC003**: Verify password reset functionality\n\n### Shopping Cart\n1. **TC004**: Add single item to cart\n2. **TC005**: Add multiple items to cart",
        status: 'sample',
        timestamp: new Date().toISOString()
      },
      'test-execution': {
        content: "# Test Execution Output\n\nRun this process to see actual output here.",
        status: 'sample',
        timestamp: new Date().toISOString()
      }
    };
    return samples[processId] || {
      content: `# ${processName} Output\n\nRun this process to see actual output here.`,
      status: 'sample',
      timestamp: new Date().toISOString()
    };
  };

  const displayOutput = processOutput || (processId && !output ? getSampleOutput() : output);

  // Debug logging
  console.log('[OutputPanel] Render state:', {
    activeTab,
    processId,
    hasOutputs: !!outputs,
    outputsKeys: outputs ? Object.keys(outputs) : [],
    processOutput,
    displayOutput: displayOutput ? { status: displayOutput.status, hasContent: !!displayOutput.content } : null
  });

  const renderCodeReviewOutput = () => {
    if (codeReviewStatus === 'loading') {
      return <div>Loading code review results...</div>;
    }
    
    if (codeReviewError) {
      return <div className="text-red-600">Error: {codeReviewError}</div>;
    }
    
    if (reviews.length === 0) {
      return <div>No code review results available</div>;
    }
    
    return (
      <div className="prose prose-sm max-w-full break-words overflow-x-auto">
        {reviews.map((review, index) => (
          <div key={index} className="mb-4">
            <ReactMarkdown 
              className="whitespace-pre-wrap break-words overflow-wrap-anywhere"
              components={{
                p: ({children}) => <p className="break-words mb-2 last:mb-0">{safeRenderChildren(children)}</p>,
                li: ({children}) => <li className="break-words">{safeRenderChildren(children)}</li>,
                td: ({children}) => <td className="break-words max-w-xs px-2 py-1">{safeRenderChildren(children)}</td>,
                th: ({children}) => <th className="break-words px-2 py-1 font-semibold">{safeRenderChildren(children)}</th>,
                h1: ({children}) => <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0">{safeRenderChildren(children)}</h1>,
                h2: ({children}) => <h2 className="text-lg font-semibold mb-2 mt-3">{safeRenderChildren(children)}</h2>,
                h3: ({children}) => <h3 className="text-md font-medium mb-2 mt-2">{safeRenderChildren(children)}</h3>,
                ul: ({children}) => <ul className="list-disc pl-6 mb-3 space-y-1">{safeRenderChildren(children)}</ul>,
                ol: ({children}) => <ol className="list-decimal pl-6 mb-3 space-y-1">{safeRenderChildren(children)}</ol>,
                blockquote: ({children}) => <blockquote className="border-l-4 border-gray-300 pl-4 italic my-3">{safeRenderChildren(children)}</blockquote>,
                code: ({children}) => <code className="bg-gray-100 px-1 rounded text-sm">{safeRenderChildren(children)}</code>,
                pre: ({children}) => <pre className="bg-gray-100 p-3 rounded overflow-x-auto mb-3">{safeRenderChildren(children)}</pre>
              }}
            >
              {review}
            </ReactMarkdown>
          </div>
        ))}
      </div>
    );
  };

  const renderTestScenarioContent = (content) => {
    // Test scenario content'i JSON'dan parse etmeye çalış
    try {
      // Markdown content'ten JSON kısmını çıkar
      const jsonMatch = content.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch) {
        const jsonData = JSON.parse(jsonMatch[1]);
        
        if (jsonData.TestScenarios && Array.isArray(jsonData.TestScenarios)) {
          return (
            <div className="space-y-6">
              {/* Summary Section */}
              {jsonData.Summary && (
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                  <h4 className="font-semibold text-blue-900 mb-2">Summary</h4>
                  <div className="text-sm text-blue-800">
                    <p><strong>Total Scenarios:</strong> {jsonData.Summary.TotalScenarios}</p>
                    {jsonData.Summary.Categories && (
                      <div className="mt-2">
                        <strong>Categories:</strong>
                        <ul className="ml-4 mt-1">
                          {Object.entries(jsonData.Summary.Categories).map(([category, count]) => (
                            <li key={category}>{category}: {count} scenarios</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {jsonData.Summary.Coverage && (
                      <p className="mt-2"><strong>Coverage:</strong> {jsonData.Summary.Coverage}</p>
                    )}
                  </div>
                </div>
              )}
              
              {/* Test Scenarios Grid */}
              <div className="space-y-6 test-scenario-content overflow-safe">
                {jsonData.TestScenarios.map((scenario, index) => (
                  <div key={scenario.ScenarioID || index} className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 w-full overflow-safe">
                    <div className="flex items-start justify-between mb-3 gap-2">
                      <h4 className="text-lg font-semibold text-gray-900 test-scenario-text flex-1 min-w-0">
                        {index + 1}. {scenario.Title}
                      </h4>
                      <div className="flex flex-col items-end space-y-1 flex-shrink-0">
                        {scenario.ScenarioID && (
                          <span className="inline-block px-2 py-1 text-xs font-mono bg-gray-100 text-gray-700 rounded">
                            {scenario.ScenarioID}
                          </span>
                        )}
                        {scenario.Category && (
                          <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                            {scenario.Category}
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="space-y-3 w-full overflow-safe">
                      {scenario.Description && (
                        <div className="w-full overflow-safe">
                          <strong className="text-sm text-gray-700">Description:</strong>
                          <p className="text-sm text-gray-600 mt-1 test-scenario-text leading-relaxed">
                            {scenario.Description}
                          </p>
                        </div>
                      )}
                      
                      {scenario.Objective && (
                        <div className="w-full overflow-safe">
                          <strong className="text-sm text-gray-700">Objective:</strong>
                          <p className="text-sm text-gray-600 mt-1 test-scenario-text leading-relaxed">
                            {scenario.Objective}
                          </p>
                        </div>
                      )}
                      
                      {scenario.Comments && (
                        <div className="w-full overflow-safe">
                          <strong className="text-sm text-gray-700">Comments:</strong>
                          <p className="text-sm text-gray-600 mt-1 test-scenario-text leading-relaxed">
                            {scenario.Comments}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Raw JSON Section (Collapsible) */}
              <details className="mt-6 w-full">
                <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                  View Raw JSON Output
                </summary>
                <div className="mt-2 bg-gray-100 rounded p-4 w-full overflow-hidden">
                  <pre className="text-xs font-mono whitespace-pre-wrap break-words w-full max-w-full overflow-wrap-anywhere word-break-break-word">
                    {JSON.stringify(jsonData, null, 2)}
                  </pre>
                </div>
              </details>
            </div>
          );
        }
      }        // Fallback to markdown if JSON parsing fails
      return (
        <div className="prose prose-sm max-w-full text-gray-600 break-words w-full overflow-hidden">
          <ReactMarkdown 
            className="whitespace-pre-wrap break-words overflow-wrap-anywhere w-full max-w-full"            components={{
              p: ({children}) => <p className="break-words w-full max-w-full overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</p>,
              li: ({children}) => <li className="break-words w-full max-w-full overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</li>,
              td: ({children}) => <td className="break-words max-w-xs overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</td>,
              th: ({children}) => <th className="break-words overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</th>,
              strong: ({children}) => <strong className="break-words overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</strong>
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      );        } catch (error) {
      console.error('Error parsing test scenario content:', error);
      // Fallback to markdown
      return (
        <div className="prose prose-sm max-w-full text-gray-600 break-words w-full overflow-hidden">
          <ReactMarkdown            className="whitespace-pre-wrap break-words overflow-wrap-anywhere w-full max-w-full"
            components={{
              p: ({children}) => <p className="break-words w-full max-w-full overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</p>,
              li: ({children}) => <li className="break-words w-full max-w-full overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</li>,
              td: ({children}) => <td className="break-words max-w-xs overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</td>,
              th: ({children}) => <th className="break-words overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</th>,
              strong: ({children}) => <strong className="break-words overflow-wrap-anywhere word-break-break-word">{safeRenderChildren(children)}</strong>
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      );
    }
  };
  
  const renderTestExecutionResults = (content) => {
    // Parse batch test execution results
    try {
      // Check if this is a batch execution result
      if (!content || !content.includes('BATCH TEST EXECUTION RESULTS')) {
        return null; // Return null to use default rendering
      }
      
      // Extract summary
      const summaryMatch = content.match(/Total Tests: (\d+)\s+✅ Successful: (\d+)\s+❌ Failed: (\d+)\s+Success Rate: ([\d.]+)%/);
      
      if (!summaryMatch) {
        return null; // Fallback to default rendering
      }
      
      const [, total, successful, failed, successRate] = summaryMatch;
      
      // Extract individual test results using regex
      const testResultPattern = /={80}\nTEST #(\d+): (.+?) (✅|❌)\nStatus: (PASSED|FAILED)\nTest ID: (.+?)\nSession: (.+?) \| Index: (\d+)\n={80}\n\n(?:OUTPUT:\n([\s\S]*?)\n\n|ERROR:\n([\s\S]*?)\n\n(?:OUTPUT:\n([\s\S]*?)\n\n)?)/g;
      
      const tests = [];
      let match;
      
      while ((match = testResultPattern.exec(content)) !== null) {
        const [, testNumber, testName, statusIcon, status, testId, sessionId, testIndex, output, error, errorOutput] = match;
        
        tests.push({
          testNumber: parseInt(testNumber),
          testName: testName.trim(),
          status: status,
          success: status === 'PASSED',
          testId: testId.trim(),
          sessionId: sessionId.trim(),
          testIndex: parseInt(testIndex),
          output: output ? output.trim() : (errorOutput ? errorOutput.trim() : ''),
          error: error ? error.trim() : null
        });
      }
      
      return (
        <div className="space-y-6">
          {/* Context-Aware Execution Info */}
          <div className="rounded-lg p-4 border bg-blue-50 border-blue-200">
            <h4 className="font-semibold mb-2 text-blue-900">
              🧠 Context-Aware Execution
            </h4>
            <div className="space-y-2 text-sm text-blue-800">
              <div className="flex items-start gap-2">
                <span className="text-green-600 font-bold">✓</span>
                <span>Source code context automatically extracted from database</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-green-600 font-bold">✓</span>
                <span>AI received both test code and source code being tested</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-green-600 font-bold">✓</span>
                <span>Each test executed with full understanding of the context</span>
              </div>
            </div>
            
            {/* Source Code Display */}
            <details className="mt-3">
              <summary className="cursor-pointer text-sm font-medium text-blue-900 hover:text-blue-700 flex items-center gap-2">
                <span>📄 View Source Code Context</span>
                <span className="text-xs text-blue-600">(Click to expand)</span>
              </summary>
              <div className="mt-3 bg-white border border-blue-200 rounded p-3">
                <p className="text-xs text-blue-700 mb-2">
                  <strong>Note:</strong> The source code was extracted from the session when tests were generated.
                  This context helps the AI understand what the tests are validating.
                </p>
                <div className="bg-gray-50 border border-gray-300 rounded p-3 max-h-96 overflow-y-auto">
                  <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap">
                    {/* Extract source code info from content if available */}
                    {content.includes('Source Code Context:') 
                      ? content.split('Source Code Context:')[1]?.split('================================================================================')[0]?.trim() || 'Source code context was provided to AI during execution'
                      : 'Source code context was provided to AI during execution'}
                  </pre>
                </div>
              </div>
            </details>
          </div>
          
          {/* Summary Section */}
          <div className={`rounded-lg p-4 border ${
            failed === '0' 
              ? 'bg-green-50 border-green-200' 
              : 'bg-yellow-50 border-yellow-200'
          }`}>
            <h4 className={`font-semibold mb-3 ${
              failed === '0' ? 'text-green-900' : 'text-yellow-900'
            }`}>
              📊 Batch Execution Summary
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-gray-600 font-medium">Total Tests</p>
                <p className="text-2xl font-bold text-gray-900">{total}</p>
              </div>
              <div>
                <p className="text-gray-600 font-medium">Successful</p>
                <p className="text-2xl font-bold text-green-600">✅ {successful}</p>
              </div>
              <div>
                <p className="text-gray-600 font-medium">Failed</p>
                <p className="text-2xl font-bold text-red-600">❌ {failed}</p>
              </div>
              <div>
                <p className="text-gray-600 font-medium">Success Rate</p>
                <p className="text-2xl font-bold text-indigo-600">{successRate}%</p>
              </div>
            </div>
          </div>
          
          {/* Individual Test Results */}
          <div className="space-y-4">
            <h4 className="font-semibold text-gray-900 text-lg">Individual Test Results</h4>
            
            {tests.map((test) => (
              <details 
                key={test.testId} 
                className={`bg-white rounded-lg border shadow-sm ${
                  test.success 
                    ? 'border-green-200 hover:border-green-300' 
                    : 'border-red-200 hover:border-red-300'
                }`}
              >
                <summary className="cursor-pointer p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg font-semibold text-gray-900">
                          {test.success ? '✅' : '❌'} Test #{test.testNumber}: {test.testName}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className={`px-2 py-1 rounded-full font-medium ${
                          test.success 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {test.status}
                        </span>
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded font-mono">
                          Index: {test.testIndex}
                        </span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded font-mono text-xs">
                          Session: {test.sessionId.substring(0, 8)}...
                        </span>
                      </div>
                    </div>
                  </div>
                </summary>
                
                <div className="px-4 pb-4 pt-2 border-t border-gray-100">
                  {test.error && (
                    <div className="mb-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-semibold text-red-700">❌ Error:</span>
                      </div>
                      <div className="bg-red-50 border border-red-200 rounded p-3">
                        <pre className="text-xs font-mono text-red-800 whitespace-pre-wrap break-words">
                          {test.error}
                        </pre>
                      </div>
                    </div>
                  )}
                  
                  {test.output && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-semibold text-gray-700">📤 Output:</span>
                      </div>
                      <div className="bg-gray-50 border border-gray-200 rounded p-3">
                        <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                          {test.output}
                        </pre>
                      </div>
                    </div>
                  )}
                  
                  {!test.output && !test.error && (
                    <p className="text-sm text-gray-500 italic">No output available</p>
                  )}
                  
                  {/* Test Metadata */}
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-medium text-gray-600 hover:text-gray-800">
                      View Test Metadata
                    </summary>
                    <div className="mt-2 bg-gray-100 rounded p-2 text-xs font-mono">
                      <div><strong>Test ID:</strong> {test.testId}</div>
                      <div><strong>Session ID:</strong> {test.sessionId}</div>
                      <div><strong>Test Index:</strong> {test.testIndex}</div>
                      <div><strong>Test Number:</strong> {test.testNumber}</div>
                    </div>
                  </details>
                </div>
              </details>
            ))}
          </div>
          
          {/* Raw Output Toggle */}
          <details className="mt-6">
            <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
              View Raw Output
            </summary>
            <div className="mt-2 bg-gray-100 rounded p-4 overflow-hidden">
              <pre className="text-xs font-mono whitespace-pre-wrap break-words max-w-full overflow-wrap-anywhere word-break-break-word">
                {content}
              </pre>
            </div>
          </details>
        </div>
      );
      
    } catch (error) {
      console.error('Error parsing test execution results:', error);
      return null; // Fallback to default rendering
    }
  };

  const renderTestCaseContent = (output) => {
    // Test case generation sonuçlarını handle et - Enhanced JSON parsing
    try {
      console.log('[OutputPanel] Processing test case output:', output);
      
      // Handle nested data structure: check both output.data.test_case_results and output.data.data.test_case_results
      let results, summary;
      
      if (output && output.data) {
        // Try direct data access first (for outputs[activeTab])
        if (output.data.test_case_results) {
          results = output.data.test_case_results;
          summary = output.data.summary;
        }
        // Try nested data access (for nested data structure from TestCaseGenerationForm)
        else if (output.data.data && output.data.data.test_case_results) {
          results = output.data.data.test_case_results;
          summary = output.data.data.summary;
        }
        // Try rawData access (backwards compatibility)
        else if (output.rawData && output.rawData.test_case_results) {
          results = output.rawData.test_case_results;
          summary = output.rawData.summary;
        }
      }
      
      console.log('[OutputPanel] Extracted results:', results ? results.length : 'none');
      console.log('[OutputPanel] Extracted summary:', summary);
      
      if (results && results.length > 0) {
        
        return (
          <div className="space-y-6">
            {/* Summary Section */}
            {summary && (
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <h4 className="font-semibold text-green-900 mb-2">Test Case Generation Summary</h4>
                <div className="text-sm text-green-800">
                  <p><strong>Total Scenarios Processed:</strong> {summary.scenarios_processed || 0}</p>
                  <p><strong>Successful Scenarios:</strong> {summary.successful_scenarios || 0}</p>
                  <p><strong>Failed Scenarios:</strong> {summary.failed_scenarios || 0}</p>
                  <p><strong>Total Test Cases Generated:</strong> {summary.total_test_cases || 0}</p>
                  <p><strong>Model Used:</strong> {summary.model_used || 'Unknown'}</p>
                </div>
              </div>
            )}
            
            {/* Test Case Results */}
            <div className="space-y-6">
              {results.map((result, index) => {
                console.log('[OutputPanel] Processing result:', result);
                
                // Enhanced test case parsing - handle both old text format and new JSON format
                let testCases = result.test_cases || [];
                
                // If test_cases is a string (old format), try to parse it
                if (typeof testCases === 'string') {
                  try {
                    const parsed = JSON.parse(testCases);
                    if (parsed.TestCases && Array.isArray(parsed.TestCases)) {
                      testCases = parsed.TestCases;
                    } else if (Array.isArray(parsed)) {
                      testCases = parsed;
                    }
                  } catch (e) {
                    console.warn('[OutputPanel] Failed to parse test cases as JSON:', e);
                    testCases = [];
                  }
                }
                
                // If still no valid test cases and we have a raw_response, try to extract
                if ((!testCases || testCases.length === 0) && result.raw_response) {
                  try {
                    // Try to find JSON pattern in raw response
                    const jsonMatch = result.raw_response.match(/\{[\s\S]*?"TestCases"[\s\S]*?\}/);
                    if (jsonMatch) {
                      const parsed = JSON.parse(jsonMatch[0]);
                      if (parsed.TestCases && Array.isArray(parsed.TestCases)) {
                        testCases = parsed.TestCases;
                      }
                    }
                  } catch (e) {
                    console.warn('[OutputPanel] Failed to extract JSON from raw response:', e);
                  }
                }
                
                return (
                  <div key={result.scenario_id || index} className="bg-white rounded-lg border border-gray-200 shadow-sm">
                    {/* Scenario Header */}
                    <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 rounded-t-lg">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="text-lg font-semibold text-gray-900">
                            {result.scenario_title || `Scenario ${index + 1}`}
                          </h4>
                          <p className="text-sm text-gray-600">
                            Scenario ID: {result.scenario_id} • 
                            Status: <span className={`font-medium ${result.status === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                              {result.status}
                            </span> • 
                            Test Cases: {result.test_cases_count || testCases?.length || 0}
                          </p>
                        </div>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          result.status === 'success' 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {result.status === 'success' ? 'Success' : 'Failed'}
                        </span>
                      </div>
                      
                      {result.status === 'error' && result.error && (
                        <div className="mt-3 bg-red-50 border border-red-200 rounded-md p-3">
                          <p className="text-sm text-red-700">
                            <strong>Error:</strong> {result.error}
                          </p>
                        </div>
                      )}
                      
                      {/* Show summary info if available */}
                      {result.summary && (
                        <div className="mt-3 bg-blue-50 border border-blue-200 rounded-md p-3">
                          <p className="text-sm text-blue-700">
                            <strong>Summary:</strong> {result.summary.Coverage || 'Test case coverage information'}
                          </p>
                          {result.summary.Categories && (
                            <p className="text-sm text-blue-700 mt-1">
                              <strong>Categories:</strong> {Object.entries(result.summary.Categories).map(([cat, count]) => `${cat} (${count})`).join(', ')}
                            </p>
                          )}
                        </div>
                      )}
                    </div>                  
                  {/* Test Cases */}
                  {testCases && testCases.length > 0 && (
                    <div className="p-4">
                      <h5 className="font-medium text-gray-900 mb-4">
                        Generated Test Cases ({testCases.length})
                      </h5>
                      <div className="space-y-4">
                        {testCases.map((testCase, tcIndex) => (
                          <details key={tcIndex} className="bg-gray-50 rounded-lg border border-gray-200">
                            <summary className="cursor-pointer p-4 hover:bg-gray-100 rounded-lg">
                              <div className="flex items-center justify-between">
                                <div>
                                  <h6 className="font-medium text-gray-900">
                                    {testCase.TestCaseID || `TC_${tcIndex + 1}`}: {testCase.Title || 'Untitled Test Case'}
                                  </h6>
                                  <p className="text-sm text-gray-600 mt-1">
                                    {testCase.Category || 'General'}
                                  </p>
                                </div>
                                <div className="text-sm text-gray-500">
                                  Click to expand
                                </div>
                              </div>
                            </summary>
                            
                            <div className="px-4 pb-4 pt-2 border-t border-gray-200 bg-white rounded-b-lg">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Left Column */}
                                <div className="space-y-3">
                                  <div>
                                    <h6 className="font-medium text-gray-900 mb-1">Description</h6>
                                    <p className="text-sm text-gray-700">
                                      {testCase.Description || 'No description provided'}
                                    </p>
                                  </div>
                                  
                                  <div>
                                    <h6 className="font-medium text-gray-900 mb-1">Objective</h6>
                                    <p className="text-sm text-gray-700">
                                      {testCase.Objective || 'No objective specified'}
                                    </p>
                                  </div>
                                  
                                </div>
                                
                                {/* Right Column */}
                                <div className="space-y-3">
                                  {testCase.Comments && (
                                    <div>
                                      <h6 className="font-medium text-gray-900 mb-1">Comments</h6>
                                      <p className="text-sm text-gray-600 italic">
                                        {testCase.Comments}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </details>
                        ))}
                      </div>
                    </div>
                  )}
                    {/* Raw Response and JSON Output (for debugging) */}
                  <div className="px-4 pb-4 space-y-3">
                    {/* Raw LLM Response */}
                    {result.raw_response && (
                      <details className="mt-3">
                        <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
                          View Raw LLM Response
                        </summary>
                        <div className="mt-2 bg-gray-100 rounded-md p-3">
                          <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-48">
                            {result.raw_response}
                          </pre>
                        </div>
                      </details>
                    )}
                    
                    {/* Raw JSON Output (parsed test cases) */}
                    {testCases && testCases.length > 0 && (
                      <details className="mt-3">
                        <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
                          View Raw JSON Output
                        </summary>
                        <div className="mt-2 bg-gray-100 rounded-md p-3">
                          <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-48 w-full max-w-full overflow-wrap-anywhere word-break-break-word">
                            {JSON.stringify({ TestCases: testCases }, null, 2)}
                          </pre>
                        </div>
                      </details>
                    )}
                    
                    {/* Complete Result JSON (including metadata) */}
                    <details className="mt-3">
                      <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
                        View Complete Result JSON
                      </summary>
                      <div className="mt-2 bg-gray-100 rounded-md p-3">
                        <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-48 w-full max-w-full overflow-wrap-anywhere word-break-break-word">
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      </div>
                    </details>
                  </div>
                </div>
              ); // Closing the results.map function
              })} 
            </div>
          </div>
        );
      }
      
      // No valid data found, return debug information
      console.warn('[OutputPanel] No test case results found in output:', output);
      return (
        <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
          <h4 className="font-medium text-yellow-800 mb-2">⚠️ No Test Case Results Found</h4>
          <div className="text-sm text-yellow-700">
            <p>The test case generation completed but no results could be displayed.</p>
            <p className="mt-2">Possible reasons:</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>Data structure mismatch between frontend and backend</li>
              <li>Results are stored in an unexpected format</li>
              <li>API timeout occurred during processing</li>
            </ul>
            <details className="mt-3">
              <summary className="cursor-pointer font-medium">View Debug Information</summary>
              <pre className="mt-2 bg-yellow-100 rounded p-2 text-xs overflow-auto max-h-32">
                {JSON.stringify(output, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      );
      
    } catch (error) {
      console.error('[OutputPanel] Error rendering test case content:', error);
      return (
        <div className="bg-red-50 rounded-lg p-4 border border-red-200">
          <h4 className="font-medium text-red-800 mb-2">❌ Error Displaying Results</h4>
          <p className="text-sm text-red-700">
            An error occurred while displaying the test case generation results: {error.message}
          </p>
        </div>
      );
    }
  };

  const renderTestCaseOptimizationContent = (output) => {
    // Test case optimization sonuçlarını handle et
    try {
      console.log('[OutputPanel] Processing test case optimization output:', output);
      
      if (output && output.results) {
        const results = output.results;
        
        return (
          <div className="space-y-4">
            <section>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium">Test Case Optimization Results</h3>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  output.status === 'completed' 
                    ? 'bg-green-100 text-green-800' 
                    : output.status === 'error'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {output.status === 'completed' ? 'Success' : 
                   output.status === 'error' ? 'Error' : 'Processing'}
                </span>
              </div>
              
              {/* Summary Stats */}
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-4">
                <h4 className="font-medium text-blue-800 mb-2">Optimization Summary</h4>
                <div className="grid grid-cols-3 gap-4 text-sm text-blue-700">
                  <div>
                    <p className="font-medium">Original Test Cases</p>
                    <p className="text-lg">
                      {results.total_test_cases || 
                       ((results.unique_test_cases?.length || 0) + 
                       (results.similar_test_cases?.length || 0))}
                    </p>
                  </div>
                  <div>
                    <p className="font-medium">Unique Test Cases</p>
                    <p className="text-lg text-green-600">{results.unique_test_cases?.length || 0}</p>
                  </div>
                  <div>
                    <p className="font-medium">Duplicates Removed</p>
                    <p className="text-lg text-red-600">{results.similar_test_cases?.length || 0}</p>
                  </div>
                </div>
              </div>

              {/* Unique Test Cases */}
              <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-4">
                <h4 className="font-medium text-green-800 mb-2">
                  ✅ Unique Test Cases ({results.unique_test_cases?.length || 0})
                </h4>
                <details className="cursor-pointer">
                  <summary className="text-sm text-green-700 hover:text-green-900">Click to view details</summary>
                  <div className="mt-2 space-y-2">
                    {results.unique_test_cases?.map((testCase, index) => (
                      <div key={index} className="bg-white p-3 rounded border border-green-200">
                        <h5 className="font-medium text-gray-900">{testCase.TestCaseID}: {testCase.Title}</h5>
                        <p className="text-sm text-gray-600 mt-1">{testCase.Description}</p>
                        <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {testCase.Objective}</p>
                      </div>
                    )) || <p className="text-sm text-gray-500">No unique test cases found.</p>}
                  </div>
                </details>
              </div>

              {/* Similar Test Cases */}
              {results.similar_test_cases?.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
                  <h4 className="font-medium text-yellow-800 mb-2">
                    🔄 Similar Test Cases Found ({results.similar_test_cases.length})
                  </h4>
                  <details className="cursor-pointer">
                    <summary className="text-sm text-yellow-700 hover:text-yellow-900">Click to view duplicates</summary>
                    <div className="mt-2 space-y-3">
                      {results.similar_test_cases.map((duplicate, index) => (
                        <div key={index} className="bg-white p-4 rounded border border-yellow-200">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-red-50 p-3 rounded border border-red-200">
                              <h5 className="font-medium text-red-700 mb-2">🗑️ Duplicate (Removed)</h5>
                              <p className="font-medium text-gray-900">{duplicate.DuplicateCase.TestCaseID}: {duplicate.DuplicateCase.Title}</p>
                              <p className="text-sm text-gray-600 mt-1"><strong>Description:</strong> {duplicate.DuplicateCase.Description}</p>
                              <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {duplicate.DuplicateCase.Objective}</p>
                            </div>
                            <div className="bg-green-50 p-3 rounded border border-green-200">
                              <h5 className="font-medium text-green-700 mb-2">✅ Kept (Original)</h5>
                              <p className="font-medium text-gray-900">{duplicate.MatchedWith.TestCaseID}: {duplicate.MatchedWith.Title}</p>
                              <p className="text-sm text-gray-600 mt-1"><strong>Description:</strong> {duplicate.MatchedWith.Description}</p>
                              <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {duplicate.MatchedWith.Objective}</p>
                            </div>
                          </div>
                          <div className="mt-3 pt-3 border-t border-yellow-200">
                            <p className="text-xs text-gray-600">
                              <strong>Reason:</strong> These test cases were found to be contextually similar based on their titles, descriptions, and objectives.
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}

              {/* Comparison Logs */}
              <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                <h4 className="font-medium text-gray-800 mb-2">
                  📊 Comparison Logs ({results.total_comparisons || results.comparison_logs?.length || 0} comparisons)
                </h4>
                {results.comparison_logs?.length > 0 ? (
                  <details className="cursor-pointer">
                    <summary className="text-sm text-gray-700 hover:text-gray-900">Click to view detailed comparison logs</summary>
                    <div className="mt-2 max-h-96 overflow-y-auto">
                      <div className="space-y-3">
                        {results.comparison_logs.map((log, index) => (
                          <div key={index} className="bg-white p-3 rounded border border-gray-200">
                            <div className="flex justify-between items-start mb-2">
                              <h6 className="font-medium text-gray-900">Comparison #{index + 1}</h6>
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                log.is_same || log.result?.is_same
                                  ? 'bg-red-100 text-red-800' 
                                  : 'bg-green-100 text-green-800'
                              }`}>
                                {log.is_same || log.result?.is_same ? 'Similar' : 'Different'}
                              </span>
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                              <div className="bg-blue-50 p-2 rounded">
                                <h6 className="font-medium text-blue-800 mb-1">Test Case 1</h6>
                                {(() => {
                                  // Esnek key kontrolü - Case1, test_case_1, TestCase1 vb. tüm varyasyonları destekle
                                  const testCase1 = log.test_case_1 || log.Case1 || log.TestCase1 || log.case1;
                                  return testCase1 ? (
                                    <div className="space-y-1">
                                      {Object.entries(testCase1).map(([key, value]) => 
                                        value ? (
                                          <div key={key}>
                                            <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                          </div>
                                        ) : null
                                      )}
                                    </div>
                                  ) : (
                                    <p className="text-gray-500 text-xs">No test case data available</p>
                                  );
                                })()}
                              </div>
                              
                              <div className="bg-purple-50 p-2 rounded">
                                <h6 className="font-medium text-purple-800 mb-1">Test Case 2</h6>
                                {(() => {
                                  // Esnek key kontrolü - Case2, test_case_2, TestCase2 vb. tüm varyasyonları destekle
                                  const testCase2 = log.test_case_2 || log.Case2 || log.TestCase2 || log.case2;
                                  return testCase2 ? (
                                    <div className="space-y-1">
                                      {Object.entries(testCase2).map(([key, value]) => 
                                        value ? (
                                          <div key={key}>
                                            <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                          </div>
                                        ) : null
                                      )}
                                    </div>
                                  ) : (
                                    <p className="text-gray-500 text-xs">No test case data available</p>
                                  );
                                })()}
                              </div>
                            </div>
                            
                            {log.prompt_sent && (
                              <details className="mt-2">
                                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                                  View prompt sent to LLM
                                </summary>
                                <div className="mt-1 bg-gray-100 p-2 rounded text-xs">
                                  <pre className="whitespace-pre-wrap">{log.prompt_sent}</pre>
                                </div>
                              </details>
                            )}
                            
                            {log.llm_response && (
                              <details className="mt-2">
                                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                                  View LLM response
                                </summary>
                                <div className="mt-1 bg-gray-100 p-2 rounded text-xs">
                                  <pre className="whitespace-pre-wrap">{log.llm_response}</pre>
                                </div>
                              </details>
                            )}
                            
                            {/* Debug: Show raw log data */}
                            <details className="mt-2">
                              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                                View raw comparison data (debug)
                              </summary>
                              <div className="mt-1 bg-gray-50 p-2 rounded text-xs">
                                <pre className="whitespace-pre-wrap">{JSON.stringify(log, null, 2)}</pre>
                              </div>
                            </details>
                          </div>
                        ))}
                      </div>
                    </div>
                  </details>
                ) : (
                  <p className="text-sm text-gray-600">
                    No detailed comparison logs available.
                  </p>
                )}
              </div>
            </section>
            
            <section>
              <h3 className="text-lg font-medium mb-3">Execution Details</h3>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-gray-600">
                  <p><strong>Status:</strong> {output.status || 'completed'}</p>
                  <p><strong>Process:</strong> Test Case Optimization</p>
                  <p><strong>Last Updated:</strong> {new Date(output.timestamp).toLocaleString()}</p>
                </div>
              </div>
            </section>
          </div>
        );
      }
    } catch (error) {
      console.error('Error rendering test case optimization content:', error);
    }
    
    return null;
  };

  const renderContent = () => {
    // Test Case Optimization için özel gösterim
    if (activeTab === 'test-case-optimization') {
      // Use testCaseOptimizationResults if available, otherwise check outputs
      if (testCaseOptimizationResults) {
        return (
          <div className="space-y-4">
            <section>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium">Test Case Optimization Results</h3>
                <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                  Success
                </span>
              </div>
              
              {/* Optimization Summary */}
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-4">
                <h4 className="font-medium text-blue-800 mb-2">Optimization Summary</h4>
                <div className="grid grid-cols-3 gap-4 text-sm text-blue-700">
                  <div>
                    <p className="font-medium">Original Test Cases</p>
                    <p className="text-lg">
                      {testCaseOptimizationResults.total_test_cases || 
                       ((testCaseOptimizationResults.unique_test_cases?.length || 0) + 
                       (testCaseOptimizationResults.similar_test_cases?.length || 0))}
                    </p>
                  </div>
                  <div>
                    <p className="font-medium">Unique Test Cases</p>
                    <p className="text-lg text-green-600">{testCaseOptimizationResults.unique_test_cases?.length || 0}</p>
                  </div>
                  <div>
                    <p className="font-medium">Duplicates Removed</p>
                    <p className="text-lg text-red-600">{testCaseOptimizationResults.similar_test_cases?.length || 0}</p>
                  </div>
                </div>
              </div>

              {/* Unique Test Cases */}
              <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-4">
                <h4 className="font-medium text-green-800 mb-2">
                  ✅ Unique Test Cases ({testCaseOptimizationResults.unique_test_cases?.length || 0})
                </h4>
                <details className="cursor-pointer">
                  <summary className="text-sm text-green-700 hover:text-green-900">Click to view details</summary>
                  <div className="mt-2 space-y-2">
                    {testCaseOptimizationResults.unique_test_cases?.map((testCase, index) => (
                      <div key={index} className="bg-white p-3 rounded border border-green-200">
                        <h5 className="font-medium text-gray-900">{testCase.TestCaseID}: {testCase.Title}</h5>
                        <p className="text-sm text-gray-600 mt-1">{testCase.Description}</p>
                        <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {testCase.Objective}</p>
                      </div>
                    )) || <p className="text-sm text-gray-500">No unique test cases found.</p>}
                  </div>
                </details>
              </div>

              {/* Similar Test Cases */}
              {testCaseOptimizationResults.similar_test_cases?.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
                  <h4 className="font-medium text-yellow-800 mb-2">
                    🔄 Similar Test Cases Found ({testCaseOptimizationResults.similar_test_cases.length})
                  </h4>
                  <details className="cursor-pointer">
                    <summary className="text-sm text-yellow-700 hover:text-yellow-900">Click to view duplicates</summary>
                    <div className="mt-2 space-y-3">
                      {testCaseOptimizationResults.similar_test_cases.map((duplicate, index) => (
                        <div key={index} className="bg-white p-4 rounded border border-yellow-200">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-red-50 p-3 rounded border border-red-200">
                              <h5 className="font-medium text-red-700 mb-2">🗑️ Duplicate (Removed)</h5>
                              <p className="font-medium text-gray-900">{duplicate.DuplicateCase?.TestCaseID}: {duplicate.DuplicateCase?.Title}</p>
                              <p className="text-sm text-gray-600 mt-1"><strong>Description:</strong> {duplicate.DuplicateCase?.Description}</p>
                              <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {duplicate.DuplicateCase?.Objective}</p>
                            </div>
                            <div className="bg-green-50 p-3 rounded border border-green-200">
                              <h5 className="font-medium text-green-700 mb-2">✅ Kept (Original)</h5>
                              <p className="font-medium text-gray-900">{duplicate.MatchedWith?.TestCaseID}: {duplicate.MatchedWith?.Title}</p>
                              <p className="text-sm text-gray-600 mt-1"><strong>Description:</strong> {duplicate.MatchedWith?.Description}</p>
                              <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {duplicate.MatchedWith?.Objective}</p>
                            </div>
                          </div>
                          <div className="mt-3 pt-3 border-t border-yellow-200">
                            <p className="text-xs text-gray-600">
                              <strong>Reason:</strong> These test cases were found to be contextually similar based on their titles, descriptions, and objectives.
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}

              {/* Comparison Logs */}
              <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                <h4 className="font-medium text-gray-800 mb-2">
                  📊 Comparison Logs ({testCaseOptimizationResults.total_comparisons || testCaseOptimizationResults.comparison_logs?.length || 0} comparisons)
                </h4>
                {testCaseOptimizationResults.comparison_logs?.length > 0 ? (
                  <details className="cursor-pointer">
                    <summary className="text-sm text-gray-700 hover:text-gray-900">Click to view detailed comparison logs</summary>
                    <div className="mt-2 max-h-96 overflow-y-auto">
                      <div className="space-y-3">
                        {testCaseOptimizationResults.comparison_logs.map((log, index) => (
                          <div key={index} className="bg-white p-3 rounded border border-gray-200">
                            <div className="flex justify-between items-start mb-2">
                              <h6 className="font-medium text-gray-900">Comparison #{index + 1}</h6>
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                log.is_same || log.result?.is_same
                                  ? 'bg-red-100 text-red-800' 
                                  : 'bg-green-100 text-green-800'
                              }`}>
                                {log.is_same || log.result?.is_same ? 'Similar' : 'Different'}
                              </span>
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                              <div className="bg-blue-50 p-2 rounded">
                                <h6 className="font-medium text-blue-800 mb-1">Test Case 1</h6>
                                {(() => {
                                  // Flexible key lookup for test case 1
                                  const testCase1 = log.test_case_1 || log.Case1 || log.TestCase1 || log.case1;
                                  return testCase1 ? (
                                    <div className="space-y-1">
                                      {Object.entries(testCase1).map(([key, value]) => 
                                        value ? (
                                          <div key={key}>
                                            <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                          </div>
                                        ) : null
                                      )}
                                    </div>
                                  ) : (
                                    <p className="text-gray-500 text-xs">No test case data available</p>
                                  );
                                })()}
                              </div>
                              
                              <div className="bg-purple-50 p-2 rounded">
                                <h6 className="font-medium text-purple-800 mb-1">Test Case 2</h6>
                                {(() => {
                                  // Flexible key lookup for test case 2
                                  const testCase2 = log.test_case_2 || log.Case2 || log.TestCase2 || log.case2;
                                  return testCase2 ? (
                                    <div className="space-y-1">
                                      {Object.entries(testCase2).map(([key, value]) => 
                                        value ? (
                                          <div key={key}>
                                            <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                          </div>
                                        ) : null
                                      )}
                                    </div>
                                  ) : (
                                    <p className="text-gray-500 text-xs">No test case data available</p>
                                  );
                                })()}
                              </div>
                            </div>
                            
                            {log.prompt_sent && (
                              <details className="mt-2">
                                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                                  View prompt sent to LLM
                                </summary>
                                <div className="mt-1 bg-gray-100 p-2 rounded text-xs">
                                  <pre className="whitespace-pre-wrap">{log.prompt_sent}</pre>
                                </div>
                              </details>
                            )}
                            
                            {log.llm_response && (
                              <details className="mt-2">
                                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                                  View LLM response
                                </summary>
                                <div className="mt-1 bg-gray-100 p-2 rounded text-xs">
                                  <pre className="whitespace-pre-wrap">{log.llm_response}</pre>
                                </div>
                              </details>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </details>
                ) : (
                  <p className="text-sm text-gray-600">
                    No detailed comparison logs available.
                  </p>
                )}
              </div>

              <section>
                <h3 className="text-lg font-medium mb-3">Execution Details</h3>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
                  <div className="text-gray-600">
                    <p><strong>Status:</strong> Completed</p>
                    <p><strong>Process:</strong> Test Case Optimization</p>
                    <p><strong>Last Updated:</strong> {new Date().toLocaleString()}</p>
                  </div>
                </div>
              </section>
            </section>
          </div>
        );
      } else if (outputs && outputs[activeTab] && outputs[activeTab].type === 'test-case-optimization') {
        const optimizationOutput = outputs[activeTab];
        return (
          <div className="space-y-4">
            <section>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium">Test Case Optimization Results</h3>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  optimizationOutput.status === 'completed' 
                    ? 'bg-green-100 text-green-800' 
                    : optimizationOutput.status === 'error'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {optimizationOutput.status === 'completed' ? 'Success' : 
                   optimizationOutput.status === 'error' ? 'Error' : 'Processing'}
                </span>
              </div>
              
              {optimizationOutput.results && (
                <>
                  {/* Optimization Summary */}
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-4">
                    <h4 className="font-medium text-blue-800 mb-2">Optimization Summary</h4>
                    <div className="grid grid-cols-3 gap-4 text-sm text-blue-700">
                      <div>
                        <p className="font-medium">Original Test Cases</p>
                        <p className="text-lg">
                          {optimizationOutput.results.total_test_cases || 
                           ((optimizationOutput.results.unique_test_cases?.length || 0) + 
                           (optimizationOutput.results.similar_test_cases?.length || 0))}
                        </p>
                      </div>
                      <div>
                        <p className="font-medium">Unique Test Cases</p>
                        <p className="text-lg text-green-600">{optimizationOutput.results.unique_test_cases?.length || 0}</p>
                      </div>
                      <div>
                        <p className="font-medium">Duplicates Removed</p>
                        <p className="text-lg text-red-600">{optimizationOutput.results.similar_test_cases?.length || 0}</p>
                      </div>
                    </div>
                  </div>

                  {/* Unique Test Cases */}
                  <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-4">
                    <h4 className="font-medium text-green-800 mb-2">
                      ✅ Unique Test Cases ({optimizationOutput.results.unique_test_cases?.length || 0})
                    </h4>
                    <details className="cursor-pointer">
                      <summary className="text-sm text-green-700 hover:text-green-900">Click to view details</summary>
                      <div className="mt-2 space-y-2">
                        {optimizationOutput.results.unique_test_cases?.map((testCase, index) => (
                          <div key={index} className="bg-white p-3 rounded border border-green-200">
                            <h5 className="font-medium text-gray-900">{testCase.TestCaseID}: {testCase.Title}</h5>
                            <p className="text-sm text-gray-600 mt-1">{testCase.Description}</p>
                            <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {testCase.Objective}</p>
                          </div>
                        )) || <p className="text-sm text-gray-500">No unique test cases found.</p>}
                      </div>
                    </details>
                  </div>                  {/* Similar Test Cases */}
                  {optimizationOutput.results.similar_test_cases?.length > 0 && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
                      <h4 className="font-medium text-yellow-800 mb-2">
                        🔄 Similar Test Cases Found ({optimizationOutput.results.similar_test_cases.length})
                      </h4>
                      <details className="cursor-pointer">
                        <summary className="text-sm text-yellow-700 hover:text-yellow-900">Click to view duplicates</summary>
                        <div className="mt-2 space-y-3">
                          {optimizationOutput.results.similar_test_cases.map((duplicate, index) => (
                            <div key={index} className="bg-white p-4 rounded border border-yellow-200">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="bg-red-50 p-3 rounded border border-red-200">
                                  <h5 className="font-medium text-red-700 mb-2">🗑️ Duplicate (Removed)</h5>
                                  <p className="font-medium text-gray-900">{duplicate.DuplicateCase.TestCaseID}: {duplicate.DuplicateCase.Title}</p>
                                  <p className="text-sm text-gray-600 mt-1"><strong>Description:</strong> {duplicate.DuplicateCase.Description}</p>
                                  <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {duplicate.DuplicateCase.Objective}</p>
                                </div>
                                <div className="bg-green-50 p-3 rounded border border-green-200">
                                  <h5 className="font-medium text-green-700 mb-2">✅ Kept (Original)</h5>
                                  <p className="font-medium text-gray-900">{duplicate.MatchedWith.TestCaseID}: {duplicate.MatchedWith.Title}</p>
                                  <p className="text-sm text-gray-600 mt-1"><strong>Description:</strong> {duplicate.MatchedWith.Description}</p>
                                  <p className="text-xs text-gray-500 mt-1"><strong>Objective:</strong> {duplicate.MatchedWith.Objective}</p>
                                </div>
                              </div>
                              <div className="mt-3 pt-3 border-t border-yellow-200">
                                <p className="text-xs text-gray-600">
                                  <strong>Reason:</strong> These test cases were found to be contextually similar based on their titles, descriptions, and objectives.
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}{/* Comparison Logs Summary */}
                  <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                    <h4 className="font-medium text-gray-800 mb-2">
                      📊 Comparison Logs ({optimizationOutput.results.total_comparisons || optimizationOutput.results.comparison_logs?.length || 0} comparisons)
                    </h4>
                    {optimizationOutput.results.comparison_logs?.length > 0 ? (
                      <details className="cursor-pointer">
                        <summary className="text-sm text-gray-700 hover:text-gray-900">Click to view detailed comparison logs</summary>
                        <div className="mt-2 max-h-96 overflow-y-auto">
                          <div className="space-y-3">
                            {optimizationOutput.results.comparison_logs.map((log, index) => (
                              <div key={index} className="bg-white p-3 rounded border border-gray-200">
                                <div className="flex justify-between items-start mb-2">
                                  <h6 className="font-medium text-gray-900">Comparison #{index + 1}</h6>
                                  <span className={`px-2 py-1 text-xs rounded-full ${
                                    log.is_same || log.result?.is_same
                                      ? 'bg-red-100 text-red-800' 
                                      : 'bg-green-100 text-green-800'
                                  }`}>
                                    {log.is_same || log.result?.is_same ? 'Similar' : 'Different'}
                                  </span>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                                  <div className="bg-blue-50 p-2 rounded">
                                    <h6 className="font-medium text-blue-800 mb-1">Test Case 1</h6>
                                    {(() => {
                                      // Flexible key lookup for test case 1
                                      const testCase1 = log.test_case_1 || log.Case1 || log.TestCase1 || log.case1;
                                      return testCase1 ? (
                                        <div className="space-y-1">
                                          {Object.entries(testCase1).map(([key, value]) => 
                                            value ? (
                                              <div key={key}>
                                                <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                              </div>
                                            ) : null
                                          )}
                                        </div>
                                      ) : (
                                        <p className="text-gray-500 text-xs">No test case data available</p>
                                      );
                                    })()}
                                  </div>
                                  
                                  <div className="bg-purple-50 p-2 rounded">
                                    <h6 className="font-medium text-purple-800 mb-1">Test Case 2</h6>
                                    {(() => {
                                      // Flexible key lookup for test case 2
                                      const testCase2 = log.test_case_2 || log.Case2 || log.TestCase2 || log.case2;
                                      return testCase2 ? (
                                        <div className="space-y-1">
                                          {Object.entries(testCase2).map(([key, value]) => 
                                            value ? (
                                              <div key={key}>
                                                <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                              </div>
                                            ) : null
                                          )}
                                        </div>
                                      ) : (
                                        <p className="text-gray-500 text-xs">No test case data available</p>
                                      );
                                    })()}
                                  </div>
                                </div>
                                
                                {log.prompt_sent && (
                                  <details className="mt-2">
                                    <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                                      View prompt sent to LLM
                                    </summary>
                                    <div className="mt-1 bg-gray-100 p-2 rounded text-xs">
                                      <pre className="whitespace-pre-wrap">{log.prompt_sent}</pre>
                                    </div>
                                  </details>
                                )}
                                
                                {log.llm_response && (
                                  <details className="mt-2">
                                    <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                                      View LLM response
                                    </summary>
                                    <div className="mt-1 bg-gray-100 p-2 rounded text-xs">
                                      <pre className="whitespace-pre-wrap">{log.llm_response}</pre>
                                    </div>
                                  </details>
                                )}
                                
                                {/* Debug: Show raw log data */}
                                <details className="mt-2">
                                  <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                                    View raw comparison data (debug)
                                  </summary>
                                  <div className="mt-1 bg-gray-50 p-2 rounded text-xs">
                                    <pre className="whitespace-pre-wrap">{JSON.stringify(log, null, 2)}</pre>
                                  </div>
                                </details>
                              </div>
                            ))}
                          </div>
                        </div>
                      </details>
                    ) : (
                      <p className="text-sm text-gray-600">
                        No detailed comparison logs available.
                      </p>
                    )}
                  </div>
                </>
              )}
            </section>

            <section>
              <h3 className="text-lg font-medium mb-3">Execution Details</h3>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-gray-600">
                  <p><strong>Status:</strong> {optimizationOutput.status || 'completed'}</p>
                  <p><strong>Process:</strong> Test Case Optimization</p>
                  <p><strong>Last Updated:</strong> {new Date(optimizationOutput.timestamp).toLocaleString()}</p>
                </div>
              </div>
            </section>
          </div>
        );
      } else {
        // No results yet
        return (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-gray-400 mb-4">
                <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012-2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Optimization Results</h3>
              <p className="text-gray-500">Run Test Case Optimization to see results here.</p>
            </div>
          </div>
        );
      }
    }

    // Test Code Generation için özel gösterim
    if (activeTab === 'test-code-generation' && outputs && outputs[activeTab]) {
      const testCodeOutput = outputs[activeTab];
      const result = testCodeOutput.result;
      
      return (
        <div className="space-y-4">
          <section>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium">Test Code Generation Results</h3>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                testCodeOutput.status === 'success' 
                  ? 'bg-green-100 text-green-800' 
                  : testCodeOutput.status === 'error'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-blue-100 text-blue-800'
              }`}>
                {testCodeOutput.status === 'success' ? 'Success' : 
                 testCodeOutput.status === 'error' ? 'Error' : 'Processing'}
              </span>
            </div>

            {result && result.summary && (
              <>
                {/* Generation Summary */}
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-4">
                  <h4 className="font-medium text-blue-800 mb-2">Generation Summary</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm text-blue-700">
                    <div>
                      <p className="font-medium">Total Test Cases</p>
                      <p className="text-lg">{result.summary.total_test_cases || 0}</p>
                    </div>
                    <div>
                      <p className="font-medium">Generated Successfully</p>
                      <p className="text-lg text-green-600">{result.summary.generated_count || 0}</p>
                    </div>
                    <div>
                      <p className="font-medium">Failed</p>
                      <p className="text-lg text-red-600">{result.summary.failed_count || 0}</p>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-blue-200">
                    <div className="grid grid-cols-3 gap-4 text-sm text-blue-700">
                      <div>
                        <p className="font-medium">Process Title</p>
                        <p>{result.summary.process_title || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="font-medium">AI Model</p>
                        <p>{result.summary.model_name || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="font-medium">Environment</p>
                        <p>{result.environment_info?.language || 'N/A'}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Generated Test Codes */}
                <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-4">
                  <h4 className="font-medium text-green-800 mb-2">
                    ✅ Generated Test Codes ({result.generated_tests?.length || 0})
                  </h4>
                  {result.generated_tests?.length > 0 ? (
                    <div className="space-y-3">
                      {result.generated_tests.map((test, index) => (
                        <details key={index} className="cursor-pointer">
                          <summary className="text-sm text-green-700 hover:text-green-900 font-medium">
                            {test.status === 'success' ? '✅' : '❌'} {test.test_case_id || `Test #${index + 1}`}: {test.title || 'Untitled Test'}
                          </summary>
                          <div className="mt-3 bg-white p-4 rounded border border-green-200">
                            {test.status === 'success' ? (
                              <>
                                <div className="mb-3">
                                  <h6 className="font-medium text-gray-900 mb-1">Test Information</h6>
                                  <div className="text-sm text-gray-600 space-y-1">
                                    <p><strong>Test Case ID:</strong> {test.test_case_id}</p>
                                    <p><strong>Title:</strong> {test.title}</p>
                                    {test.description && <p><strong>Description:</strong> {test.description}</p>}
                                    {test.framework && <p><strong>Framework:</strong> {test.framework}</p>}
                                  </div>
                                </div>
                                {test.code && (
                                  <div className="bg-gray-900 text-green-400 p-4 rounded font-mono text-sm overflow-x-auto">
                                    <pre className="whitespace-pre-wrap">{test.code}</pre>
                                  </div>
                                )}
                                {test.explanation && (
                                  <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded">
                                    <h6 className="font-medium text-blue-800 mb-1">Explanation</h6>
                                    <p className="text-sm text-blue-700">{test.explanation}</p>
                                  </div>
                                )}
                              </>
                            ) : (
                              <div className="bg-red-50 border border-red-200 rounded p-3">
                                <h6 className="font-medium text-red-800 mb-1">Generation Failed</h6>
                                <p className="text-sm text-red-700">{test.error || 'Unknown error occurred'}</p>
                              </div>
                            )}
                          </div>
                        </details>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No test codes generated.</p>
                  )}
                </div>

                {/* Environment Information */}
                {result.environment_info && (
                  <div className="bg-gray-50 border border-gray-200 rounded-md p-4 mb-4">
                    <h4 className="font-medium text-gray-800 mb-2">Environment Information</h4>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p><strong>Language:</strong> {result.environment_info.language}</p>
                      <p><strong>Framework:</strong> {result.environment_info.framework}</p>
                      {result.environment_info.dependencies?.length > 0 && (
                        <p><strong>Dependencies:</strong> {result.environment_info.dependencies.join(', ')}</p>
                      )}
                      {result.environment_info.setup_commands?.length > 0 && (
                        <p><strong>Setup Commands:</strong> {result.environment_info.setup_commands.join(', ')}</p>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}

            {testCodeOutput.status === 'error' && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <h4 className="font-medium text-red-800 mb-2">Generation Failed</h4>
                <p className="text-sm text-red-700">{result?.error || testCodeOutput.error || 'Unknown error occurred'}</p>
              </div>
            )}

            <section>
              <h3 className="text-lg font-medium mb-3">Execution Details</h3>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-gray-600">
                  <p><strong>Status:</strong> {testCodeOutput.status || 'completed'}</p>
                  <p><strong>Process:</strong> Test Code Generation</p>
                  <p><strong>Last Updated:</strong> {new Date(testCodeOutput.timestamp).toLocaleString()}</p>
                  <p><strong>Session ID:</strong> {testCodeOutput.sessionId || result.summary?.environment_session_id || 'N/A'}</p>
                </div>
              </div>
            </section>
          </section>
        </div>
      );
    }

    if (activeTab === 'test-scenario-generation' && outputs && outputs[activeTab]) {
      const testScenarioOutput = outputs[activeTab];
      return (
        <div className="space-y-4">
          <section>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium">Test Scenario Generation Results</h3>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                testScenarioOutput.status === 'completed' 
                  ? 'bg-green-100 text-green-800' 
                  : testScenarioOutput.status === 'error'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-blue-100 text-blue-800'
              }`}>
                {testScenarioOutput.status === 'completed' ? 'Success' : 
                 testScenarioOutput.status === 'error' ? 'Error' : 'Processing'}
              </span>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm overflow-hidden">
              <div className="max-w-full overflow-x-auto">
                {renderTestScenarioContent(testScenarioOutput.content)}
              </div>
            </div>
          </section>
          <section>
            <h3 className="text-lg font-medium mb-3">Execution Details</h3>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
              <div className="text-gray-600">
                <p><strong>Status:</strong> {testScenarioOutput.status}</p>
                <p><strong>Process:</strong> {testScenarioOutput.processType || 'Test Scenario Generation'}</p>
                <p><strong>Process ID:</strong> {testScenarioOutput.processId}</p>
                <p><strong>Last Updated:</strong> {new Date(testScenarioOutput.timestamp).toLocaleString()}</p>
              </div>
            </div>
          </section>
        </div>
      );
    }

    // Check for test-reporting specific output
    if (activeTab === 'test-reporting' && outputs && outputs[activeTab]) {
      const testReportOutput = outputs[activeTab];
      const isLoading = testReportOutput.status === 'loading' || testReportOutput.status === 'processing';
      
      return (
        <div className="space-y-6">
          <section>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium">Test Report</h3>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                testReportOutput.status === 'completed' 
                  ? 'bg-green-100 text-green-800' 
                  : testReportOutput.status === 'error'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-blue-100 text-blue-800'
              }`}>
                {testReportOutput.status === 'completed' ? 'Success' : 
                 testReportOutput.status === 'error' ? 'Error' : 'Processing'}
              </span>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
              <TestReportViewer 
                output={testReportOutput.content} 
                isLoading={isLoading}
              />
            </div>
          </section>
          
          <section>
            <h3 className="text-lg font-medium mb-3">Report Details</h3>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
              <div className="text-gray-600">
                <p><strong>Status:</strong> {testReportOutput.status}</p>
                <p><strong>Process:</strong> {testReportOutput.processType || 'Test Reporting'}</p>
                {testReportOutput.model_used && <p><strong>Model:</strong> {testReportOutput.model_used}</p>}
                {testReportOutput.metadata && testReportOutput.metadata.sessions_analyzed && (
                  <p><strong>Sessions Analyzed:</strong> {testReportOutput.metadata.sessions_analyzed}</p>
                )}
                {testReportOutput.metadata && testReportOutput.metadata.processes_included && (
                  <p><strong>Processes:</strong> {testReportOutput.metadata.processes_included.join(', ')}</p>
                )}
                <p><strong>Last Updated:</strong> {testReportOutput.timestamp ? new Date(testReportOutput.timestamp).toLocaleString() : new Date().toLocaleString()}</p>
              </div>
            </div>
          </section>
        </div>
      );
    }

    // Check for test-case-generation specific output
    console.log('[OutputPanel] Checking for test-case-generation output:', {
      activeTab,
      hasOutputs: !!outputs,
      outputKeys: outputs ? Object.keys(outputs) : [],
      hasActiveTabOutput: !!(outputs && outputs[activeTab])
    });
    
    if (activeTab === 'test-case-generation' && outputs && outputs[activeTab]) {
      const testCaseOutput = outputs[activeTab];
      console.log('[OutputPanel] Found test-case-generation output:', testCaseOutput);
      const testCaseContent = renderTestCaseContent(testCaseOutput);
      
      if (testCaseContent) {
        return (
          <div className="space-y-6">
            <section>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium">Test Case Generation Results</h3>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  testCaseOutput.status === 'completed' 
                    ? 'bg-green-100 text-green-800' 
                    : testCaseOutput.status === 'error'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {testCaseOutput.status === 'completed' ? 'Success' : 
                   testCaseOutput.status === 'error' ? 'Error' : 'Processing'}
                </span>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm overflow-hidden">
                <div className="max-w-full overflow-x-auto">
                  {testCaseContent}
                </div>
              </div>
            </section>
            
            {/* Test Case Optimization Output Section */}
            <section>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium">Test Case Optimization Output</h3>
                <div className="text-sm text-gray-500">Process Results</div>
              </div>
              <TestCaseOptimizationResults sessionId={testCaseOutput.sessionId} liveResults={testCaseOptimizationResults} />
            </section>
            
            <section>
              <h3 className="text-lg font-medium mb-3">Execution Details</h3>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-gray-600">
                  <p><strong>Status:</strong> {testCaseOutput.status}</p>
                  <p><strong>Process:</strong> Test Case Generation</p>
                  <p><strong>Process ID:</strong> {testCaseOutput.processId}</p>
                  <p><strong>Last Updated:</strong> {testCaseOutput.timestamp ? new Date(testCaseOutput.timestamp).toLocaleString() : new Date().toLocaleString()}</p>
                </div>
              </div>
            </section>
          </div>
        );
      }
    }
    
    // Use displayOutput instead of creating a new currentOutput
    let currentOutput = displayOutput || getSampleOutput() || {
      content: "# Output\n\nRun a process to see output here.",
      status: 'sample',
      timestamp: new Date().toISOString()
    };

    if (activeTab === 'code-review') {
      if (codeReviewStatus === 'loading') {
        return <div>Loading code review results...</div>;
      }
      if (codeReviewError) {
        return <div className="text-red-600">Error: {codeReviewError}</div>;
      }
      if (reviews && reviews.length > 0) {
        const reviewContent = reviews.map(review => review).join('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
        currentOutput = {
          content: reviewContent,
          status: 'completed',
          timestamp: new Date().toISOString(),
          processType: 'Code Review'
        };
      }
    }

    if (activeTab === 'requirement-analysis') {
      if (reqStatus === 'loading') {
        return <div>Loading requirement analysis results...</div>;
      }
      if (reqError) {
        return <div className="text-red-600">Error: {reqError}</div>;
      }
      if (reqResult && Array.isArray(reqResult.analysis) && reqResult.analysis.length > 0) {
        const analysisContent = reqResult.analysis.map(item => {
          // Clean and format the analysis result
          const cleanResult = item.result ? item.result.replace(/\n\s*\n\s*\n/g, '\n\n').trim() : '';
          return `**Files Analyzed:**\n${item.files}\n\n**Analysis:**\n${cleanResult}`;
        }).join('\n\n---\n\n');
        return (
          <div className="space-y-4">
            <section>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium">Process Results</h3>
              </div>              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm overflow-x-auto">
                <div className="prose prose-sm max-w-full text-gray-600 break-words">
                  <ReactMarkdown 
                    className="break-words overflow-wrap-anywhere leading-relaxed"
                    components={{
                      p: ({children}) => <p className="break-words mb-3 last:mb-0 leading-relaxed">{safeRenderChildren(children)}</p>,
                      li: ({children}) => <li className="break-words">{safeRenderChildren(children)}</li>,
                      td: ({children}) => <td className="break-words max-w-xs px-2 py-1">{safeRenderChildren(children)}</td>,
                      th: ({children}) => <th className="break-words px-2 py-1 font-semibold">{safeRenderChildren(children)}</th>,
                      h1: ({children}) => <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0">{safeRenderChildren(children)}</h1>,
                      h2: ({children}) => <h2 className="text-lg font-semibold mb-2 mt-3">{safeRenderChildren(children)}</h2>,
                      h3: ({children}) => <h3 className="text-md font-medium mb-2 mt-2">{safeRenderChildren(children)}</h3>,
                      ul: ({children}) => <ul className="list-disc pl-6 mb-3 space-y-1">{safeRenderChildren(children)}</ul>,
                      ol: ({children}) => <ol className="list-decimal pl-6 mb-3 space-y-1">{safeRenderChildren(children)}</ol>,
                      blockquote: ({children}) => <blockquote className="border-l-4 border-gray-300 pl-4 italic my-3">{safeRenderChildren(children)}</blockquote>,
                      code: ({children}) => <code className="bg-gray-100 px-1 rounded text-sm">{safeRenderChildren(children)}</code>,
                      pre: ({children}) => <pre className="bg-gray-100 p-3 rounded overflow-x-auto mb-3">{safeRenderChildren(children)}</pre>
                    }}
                  >
                    {analysisContent}
                  </ReactMarkdown>
                </div>
              </div>
            </section>
            <section>
              <h3 className="text-lg font-medium mb-3">Execution Details</h3>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-gray-600">
                  <p><strong>Status:</strong> completed</p>
                  <p><strong>Process:</strong> Requirement Analysis</p>
                  <p><strong>Last Updated:</strong> {new Date().toLocaleString()}</p>
                </div>
              </div>
            </section>
          </div>
        );
      }
      // Sample göster
      return (
        <div className="space-y-4">
          <section>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium">Process Results</h3>
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                Sample
              </span>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm overflow-x-auto">
              <div className="prose prose-sm max-w-full text-gray-600 break-words">
                <ReactMarkdown 
                  className="whitespace-pre-wrap break-words overflow-wrap-anywhere"
                  components={{
                    p: ({children}) => <p className="break-words">{safeRenderChildren(children)}</p>,
                    li: ({children}) => <li className="break-words">{safeRenderChildren(children)}</li>,
                    td: ({children}) => <td className="break-words max-w-xs">{safeRenderChildren(children)}</td>,
                    th: ({children}) => <th className="break-words">{safeRenderChildren(children)}</th>
                  }}
                >
                  {getSampleOutput().content}
                </ReactMarkdown>
              </div>
            </div>
          </section>
          <section>
            <h3 className="text-lg font-medium mb-3">Execution Details</h3>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
              <div className="text-gray-600">                <p><strong>Status:</strong> Not Run</p>
                <p><strong>Process:</strong> Requirement Analysis</p>
                <p><strong>Last Updated:</strong> {new Date().toLocaleString()}</p>
              </div>
            </div>
          </section>
        </div>
      );
    }

    if (activeTab === 'test-planning') {
      if (testPlanningStatus === 'loading') {
        return <div>Loading test planning results...</div>;
      }
      if (testPlanningError) {
        return <div className="text-red-600">Error: {testPlanningError}</div>;
      }
      if (plans && plans.length > 0) {
        // İlk plan'ı al
        let planContent = plans[0];
        let jsonContent = null;
        let filesSection = "";
        let ganttTasks = [];
        let ganttParseError = false;
        
        // JSON extraction - farklı formatları dene
        // 1. Markdown code block içinde JSON
        let jsonMatch = planContent.match(/```json\n([\s\S]*?)```/);
        
        // 2. Sadece JSON array
        if (!jsonMatch) {
          jsonMatch = planContent.match(/\[\s*\{[\s\S]*?\}\s*\]/);
          if (jsonMatch) {
            jsonContent = jsonMatch[0];
          }
        } else {
          jsonContent = jsonMatch[1];
        }
        
        // 3. Files section'ı bul
        const filesSectionMatch = planContent.match(/\*\*Files Analyzed:\*\*\n([\s\S]*?)\n\*\*Test Plan:\*\*/);
        if (filesSectionMatch) {
          filesSection = filesSectionMatch[1];
        } else {
          // Alternatif format
          const altFilesMatch = planContent.match(/Files analyzed:\n([\s\S]*?)(\n\n|\[)/);
          if (altFilesMatch) {
            filesSection = altFilesMatch[1];
          }
        }
        
        // JSON varsa Gantt Chart oluştur
        if (jsonContent) {
          console.log('[Test Planning] Extracted JSON content:', jsonContent.substring(0, 500));
          try {
            ganttTasks = jsonToGanttTasks(jsonContent);
            console.log('[Test Planning] Created Gantt tasks:', ganttTasks);
          } catch (e) {
            console.error('[Test Planning] Error creating Gantt tasks:', e);
            ganttParseError = true;
          }
        } else {
          console.warn('[Test Planning] No JSON content found in response');
        }
        
        // Eğer JSON ayrıştırılamadıysa, model çıktısını temizle ve göster
        if (!jsonContent || ganttParseError) {
          // Akademik metin veya beklenmedik formatta çıktı gelmiş olabilir
          // Temizle ve kullanıcıya göster
          let cleanedContent = planContent;
          
          // **Test Plan:** etiketini kaldır
          cleanedContent = cleanedContent.replace(/\*\*Test Plan:\*\*\n/, '');
          
          // Beklenmeyen akademik başlıkları kaldır
          cleanedContent = cleanedContent.replace(/^Title:.*$/gm, '');
          cleanedContent = cleanedContent.replace(/^\*\*Title:.*$/gm, '');
          
          return (
            <div className="mt-6">
              <div className="bg-yellow-100 text-yellow-800 p-4 rounded mb-4">
                <strong>⚠️ Uyarı:</strong> Model beklenen JSON formatında yanıt üretmedi. Lütfen farklı bir model deneyin veya prompt'u gözden geçirin.
              </div>
              <div className="bg-gray-100 p-4 rounded">
                <h3 className="font-semibold mb-2">Model Çıktısı:</h3>
                <div className="prose prose-sm max-w-full">
                  <ReactMarkdown 
                    className="whitespace-pre-wrap break-words"
                    components={{
                      p: ({children}) => <p className="break-words">{safeRenderChildren(children)}</p>,
                      li: ({children}) => <li className="break-words">{safeRenderChildren(children)}</li>
                    }}
                  >
                    {cleanedContent}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          );
        }
        
        return (
          <div className="space-y-6">
            <div className="prose prose-sm max-w-full text-gray-600 break-words overflow-x-auto">
              <h2>Files Analyzed</h2>
              <ReactMarkdown 
                className="whitespace-pre-wrap break-words overflow-wrap-anywhere"
                components={{
                  p: ({children}) => <p className="break-words">{safeRenderChildren(children)}</p>,
                  li: ({children}) => <li className="break-words">{safeRenderChildren(children)}</li>,
                  td: ({children}) => <td className="break-words max-w-xs">{safeRenderChildren(children)}</td>,
                  th: ({children}) => <th className="break-words">{safeRenderChildren(children)}</th>
                }}
              >
                {filesSection}
              </ReactMarkdown>
            </div>
            
            {/* JSON veya XML formatında göster */}
            <div className="bg-gray-100 rounded p-4 font-mono text-xs overflow-auto">
              <h2 className="text-lg font-medium mb-2">Test Plan {selectedOutputFormat === 'XML' ? '(XML Format)' : '(JSON Format)'}</h2>
              <pre className="whitespace-pre-wrap break-words">
                {selectedOutputFormat === 'XML' && jsonContent 
                  ? jsonToXml(jsonContent)
                  : jsonContent}
              </pre>
            </div>
            
            {/* Gantt Chart Görünümü */}
            {ganttTasks.length > 0 ? (
              <div className="mt-6">
                <h2 className="text-lg font-medium mb-2">Test Plan Gantt Chart</h2>
                <div className="border rounded-lg p-4 bg-white overflow-x-auto">
                  {(() => {
                    try {
                      // Tüm tarihlerin geçerli olduğunu kontrol et
                      const hasInvalidDates = ganttTasks.some(task => 
                        isNaN(task.start.getTime()) || isNaN(task.end.getTime())
                      );
                      
                      if (hasInvalidDates) {
                        console.error('Some tasks have invalid dates');
                        return (
                          <div className="bg-yellow-100 text-yellow-800 p-4 rounded">
                            <strong>⚠️ Bazı görevlerde geçersiz tarihler var:</strong>
                            <pre className="mt-2 whitespace-pre-wrap break-words text-xs bg-gray-50 p-2 rounded">
                              {JSON.stringify(ganttTasks.map(t => ({
                                name: t.name,
                                start: t.start.toISOString ? t.start.toISOString().split('T')[0] : 'Invalid',
                                end: t.end.toISOString ? t.end.toISOString().split('T')[0] : 'Invalid'
                              })), null, 2)}
                            </pre>
                          </div>
                        );
                      }
                      
                      const { viewMode, columnWidth } = getGanttViewModeAndColumnWidth(ganttTasks);
                      
                      return (
                        <div style={{ width: '100%', minWidth: '800px', height: '400px' }}>
                          <Gantt
                            tasks={ganttTasks}
                            viewMode={viewMode}
                            listCellWidth="150px"
                            columnWidth={columnWidth}
                            headerHeight={50}
                            rowHeight={40}
                            ganttHeight={400}
                          />
                        </div>
                      );
                    } catch (err) {
                      console.error('Gantt Chart render error:', err);
                      return (
                        <div className="bg-red-100 text-red-700 p-4 rounded">
                          <strong>❌ Gantt Chart render hatası:</strong>
                          <p className="mt-2 text-sm">{err.message}</p>
                          <details className="mt-2">
                            <summary className="cursor-pointer text-sm font-medium">JSON Çıktısını Göster</summary>
                            <pre className="mt-2 whitespace-pre-wrap break-words text-xs bg-gray-50 p-2 rounded">{jsonContent}</pre>
                          </details>
                        </div>
                      );
                    }
                  })()}
                </div>
              </div>
            ) : (
              jsonContent && (
                <div className="mt-6">
                  <div className="bg-yellow-100 text-yellow-800 p-4 rounded">
                    <strong>⚠️ Gantt Chart için görev bulunamadı</strong>
                    <p className="mt-2 text-sm">JSON parse edildi ancak geçerli görev oluşturulamadı.</p>
                    <details className="mt-2">
                      <summary className="cursor-pointer text-sm font-medium">JSON Çıktısını Göster</summary>
                      <pre className="mt-2 whitespace-pre-wrap break-words text-xs bg-gray-50 p-2 rounded">{jsonContent}</pre>
                    </details>
                  </div>
                </div>
              )
            )}
          </div>
        );
      }
      // Sample göster
      return (
        <div className="space-y-4">
          <section>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium">Process Results</h3>
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                Sample
              </span>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm overflow-x-auto">
              <div className="prose prose-sm max-w-full text-gray-600 break-words">
                <ReactMarkdown 
                  className="whitespace-pre-wrap break-words overflow-wrap-anywhere"
                  components={{
                    p: ({children}) => <p className="break-words">{safeRenderChildren(children)}</p>,
                    li: ({children}) => <li className="break-words">{safeRenderChildren(children)}</li>,
                    td: ({children}) => <td className="break-words max-w-xs">{safeRenderChildren(children)}</td>,
                    th: ({children}) => <th className="break-words">{safeRenderChildren(children)}</th>
                  }}
                >
                  {getSampleOutput().content}
                </ReactMarkdown>
              </div>
            </div>
          </section>
          <section>
            <h3 className="text-lg font-medium mb-3">Execution Details</h3>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
              <div className="text-gray-600">
                <p><strong>Status:</strong> Not Run</p>
                <p><strong>Process:</strong> Test Planning</p>
                <p><strong>Last Updated:</strong> {new Date().toLocaleString()}</p>
              </div>
            </div>
          </section>
        </div>
      );
    }

    if (activeTab === 'environment-setup') {
      if (envSetupStatus === 'loading') {
        return <div>Loading Environment setup results...</div>;
      }
      if (envSetupError) {
        return <div className="text-red-600">Error: {envSetupError}</div>;
      }
      if (setups && setups.length > 0) {
        // Enhanced formatting for environment setup
        let setupContent = setups[0];
        
        return (
          <div className="space-y-4">
            <div className="prose prose-sm max-w-full break-words overflow-x-auto">
              <ReactMarkdown 
                className="whitespace-pre-wrap break-words overflow-wrap-anywhere"
                components={{
                  p: ({children}) => <p className="break-words mb-2 last:mb-0">{safeRenderChildren(children)}</p>,
                  li: ({children}) => <li className="break-words">{safeRenderChildren(children)}</li>,
                  td: ({children}) => <td className="break-words max-w-xs px-2 py-1">{safeRenderChildren(children)}</td>,
                  th: ({children}) => <th className="break-words px-2 py-1 font-semibold">{safeRenderChildren(children)}</th>,
                  h1: ({children}) => <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0">{safeRenderChildren(children)}</h1>,
                  h2: ({children}) => <h2 className="text-lg font-semibold mb-2 mt-3">{safeRenderChildren(children)}</h2>,
                  h3: ({children}) => <h3 className="text-md font-medium mb-2 mt-2">{safeRenderChildren(children)}</h3>,
                  ul: ({children}) => <ul className="list-disc pl-6 mb-3 space-y-1">{safeRenderChildren(children)}</ul>,
                  ol: ({children}) => <ol className="list-decimal pl-6 mb-3 space-y-1">{safeRenderChildren(children)}</ol>,
                  blockquote: ({children}) => <blockquote className="border-l-4 border-gray-300 pl-4 italic my-3">{safeRenderChildren(children)}</blockquote>,
                  code: ({children}) => <code className="bg-gray-100 px-1 rounded text-sm">{safeRenderChildren(children)}</code>,
                  pre: ({children}) => <pre className="bg-gray-100 p-3 rounded overflow-x-auto mb-3">{safeRenderChildren(children)}</pre>
                }}
              >
                {setupContent}
              </ReactMarkdown>
            </div>
          </div>
        );
      }
    }

    if (activeTab === 'code-review') {
      const content = typeof currentOutput.content === 'string'
        ? currentOutput.content 
        : JSON.stringify(currentOutput.content || 'No content available');

    // Special handling for Test Scenario Generation - show only JSON
    if (currentOutput.processType === 'Test Scenario Generation') {
      // Extract JSON from markdown format
      const jsonMatch = content.match(/```json\n([\s\S]*?)\n```/);
      const jsonContent = jsonMatch ? jsonMatch[1] : content;
      
      return (
        <div className="space-y-4">
          <section>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium">Test Scenario Generation Results</h3>
              {currentOutput.status === 'sample' && (
                <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                  Sample
                </span>
              )}
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
              <div className="bg-gray-100 rounded p-4 overflow-x-auto">
                <pre className="whitespace-pre-wrap break-words text-xs font-mono max-w-full overflow-x-auto">
                  {jsonContent}
                </pre>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-lg font-medium mb-3">Execution Details</h3>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
              <div className="text-gray-600">
                <p><strong>Status:</strong> {currentOutput.status === 'sample' ? 'Not Run' : currentOutput.status}</p>
                <p><strong>Process:</strong> {processName || currentOutput.processType || 'Unknown'}</p>
                <p><strong>Last Updated:</strong> {new Date(currentOutput.timestamp).toLocaleString()}</p>
              </div>
            </div>          </section>
        </div>
      );
    }
    }
    
    // Check if this is a test execution result with batch format
    if (activeTab === 'test-execution' && currentOutput.content) {
      const executionResults = renderTestExecutionResults(currentOutput.content);
      if (executionResults) {
        return (
          <div className="space-y-4">
            <section>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium">Test Execution Results</h3>
                {currentOutput.status === 'sample' && (
                  <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                    Sample
                  </span>
                )}
                {currentOutput.status === 'completed' && (
                  <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                    Completed
                  </span>
                )}
                {currentOutput.status === 'error' && (
                  <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">
                    Error
                  </span>
                )}
              </div>
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                {executionResults}
              </div>
            </section>

            <section>
              <h3 className="text-lg font-medium mb-3">Execution Details</h3>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-gray-600 space-y-1">
                  <p><strong>Status:</strong> {currentOutput.status === 'sample' ? 'Not Run' : currentOutput.status}</p>
                  <p><strong>Process:</strong> Test Execution</p>
                  {currentOutput.model_used && <p><strong>Model:</strong> {currentOutput.model_used}</p>}
                  <p><strong>Last Updated:</strong> {new Date(currentOutput.timestamp).toLocaleString()}</p>
                </div>
              </div>
            </section>
          </div>
        );
      }
    }

    return (
      <div className="space-y-4">
        <section>
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-medium">Process Results</h3>
            {currentOutput.status === 'sample' && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                Sample
              </span>
            )}
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm overflow-x-auto">
            <div className="prose prose-sm max-w-full text-gray-600 break-words">
              {/* Önce açıklama kısmı, sonra kod bloğu */}
              <ReactMarkdown
                className="whitespace-pre-wrap break-words overflow-wrap-anywhere"
                components={{
                  p: ({children}) => <p className="break-words">{safeRenderChildren(children)}</p>,
                  li: ({children}) => <li className="break-words">{safeRenderChildren(children)}</li>,
                  td: ({children}) => <td className="break-words max-w-xs">{safeRenderChildren(children)}</td>,
                  th: ({children}) => <th className="break-words">{safeRenderChildren(children)}</th>,
                  code: ({ node, inline, className, children, ...props }) => {
                    const match = /language-(\w+)/.exec(className || '');
                    const isJson = match && match[1] === 'json';
                    
                    if (!inline && isJson) {
                      return (
                        <div className="bg-gray-100 rounded p-4 my-4 overflow-x-auto">
                          <pre className="whitespace-pre-wrap break-words text-xs font-mono max-w-full">
                            <code {...props}>
                              {safeRenderChildren(children)}
                            </code>
                          </pre>
                        </div>
                      );
                    }
                    
                    return (
                      <code className={className} {...props}>
                        {safeRenderChildren(children)}
                      </code>
                    );
                  }
                }}              >
                {typeof currentOutput.content === 'string' 
                  ? currentOutput.content.replace(/\{[\s\S]*\}/, '').trim()
                  : JSON.stringify(currentOutput.content || 'No content available')
                }
              </ReactMarkdown>
              {currentOutput.prettyJson && (
                <div className="bg-gray-100 rounded p-4 font-mono text-xs overflow-auto mt-4">
                  <pre className="whitespace-pre-wrap break-words">{currentOutput.prettyJson}</pre>
                </div>
              )}
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-lg font-medium mb-3">Execution Details</h3>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 shadow-sm">
            <div className="text-gray-600">
              <p><strong>Status:</strong> {currentOutput.status === 'sample' ? 'Not Run' : currentOutput.status}</p>
              <p><strong>Process:</strong> {processName || currentOutput.processType || 'Unknown'}</p>
              <p><strong>Last Updated:</strong> {new Date(currentOutput.timestamp).toLocaleString()}</p>
            </div>
          </div>
        </section>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {!hideHeader && (
        <div className="flex-none h-16 px-6 flex items-center justify-between border-b border-gray-200 bg-white">
          <h2 className="text-xl font-bold text-gray-900">{headerTitle}</h2>
          {processId && (
            <span className="px-3 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
              {processId}
            </span>
          )}
        </div>
      )}
      <div className={`flex-1 overflow-y-auto ${hideHeader ? 'p-4' : 'p-4'}`}>
        {renderContent()}
      </div>
      {!hideFooter && (
        <div className="flex-none h-16 px-6 flex items-center border-t border-gray-200 bg-white">
          <button
            className={`w-full py-3 px-4 rounded-md text-white font-medium transition-colors shadow-sm ${
              !displayOutput || displayOutput.status === 'sample'
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700'
            }`}
            disabled={!displayOutput || displayOutput.status === 'sample'}
          >            Install Output
          </button>
        </div>
      )}
    </div>  );
}
