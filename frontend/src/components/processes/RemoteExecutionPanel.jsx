import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  ExclamationTriangleIcon,
  MinusCircleIcon,
  ServerIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

const API_BASE = '/api/remote-execution';

const VERDICT_META = {
  passed: { label: 'PASSED', text: 'text-green-700', badge: 'bg-green-100 text-green-800' },
  failed: { label: 'FAILED', text: 'text-red-700', badge: 'bg-red-100 text-red-800' },
  error: { label: 'ERROR', text: 'text-orange-700', badge: 'bg-orange-100 text-orange-800' },
  blocked: { label: 'BLOCKED', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800' },
  not_executed: { label: 'NOT EXECUTED', text: 'text-gray-700', badge: 'bg-gray-200 text-gray-800' },
  invalid: { label: 'INVALID TEST', text: 'text-purple-700', badge: 'bg-purple-100 text-purple-800' },
};

function resultVerdict(result) {
  if (result.verdict) return result.verdict;
  if (result.failed > 0) return 'failed';
  return result.status === 'completed' ? 'passed' : 'error';
}

function testContent(test) {
  return test.full_code || test.code || test.test_code || '';
}

export default function RemoteExecutionPanel({
  sessionId,
  selectedProcessName,
  testCodes = [],
  onResultsCollected,
}) {
  const [runnerStatus, setRunnerStatus] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const timeoutSeconds = 900;
  const [executionResults, setExecutionResults] = useState(null);

  const runnableTests = useMemo(
    () => testCodes.filter(test => (
      testContent(test).trim()
      && (test.execution_eligibility || 'eligible') === 'eligible'
      && test.oracle?.passed !== false
    )),
    [testCodes],
  );

  const checkRunner = useCallback(async () => {
    setIsChecking(true);
    try {
      const response = await fetch(`${API_BASE}/runner-status`);
      const data = await response.json();
      setRunnerStatus(data);
      if (!response.ok || !data.configured) {
        toast.error(data.error || 'Remote runner is not configured');
      }
    } catch (error) {
      setRunnerStatus({ success: false, configured: false, error: error.message });
      toast.error('Remote runner status could not be loaded');
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    checkRunner();
  }, [checkRunner]);

  const executeTests = useCallback(async () => {
    if (!selectedProcessName) {
      toast.error('Select a test code generation process');
      return;
    }
    if (runnableTests.length === 0) {
      toast.error('Select at least one test containing Python code');
      return;
    }
    if (!runnerStatus?.configured) {
      toast.error('Remote runner is not configured');
      return;
    }

    setIsExecuting(true);
    setExecutionResults(null);
    try {
      const testFiles = runnableTests.map((test, index) => ({
        test_id: String(test.test_id || test.id || `test-${index + 1}`),
        filename: test.filename || `${test.test_id || `test_${index + 1}`}.py`,
        content: testContent(test),
        execution_eligibility: test.execution_eligibility || 'eligible',
        eligibility_reason: test.eligibility_reason || null,
        oracle: test.oracle || null,
      }));
      const response = await fetch(`${API_BASE}/execute-tests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId || `remote-${Date.now()}`,
          process_name: selectedProcessName,
          timeout_seconds: timeoutSeconds,
          test_files: testFiles,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.error || `Remote execution failed (${response.status})`);
      }
      setExecutionResults(data);
      onResultsCollected?.(data);
      const unsuccessful = (data.summary?.failed || 0)
        + (data.summary?.error || 0)
        + (data.summary?.blocked || 0)
        + (data.summary?.not_executed || 0)
        + (data.summary?.invalid || 0);
      if (unsuccessful) {
        toast.error(
          `Remote execution: ${data.summary?.passed || 0} passed, ${unsuccessful} require attention`,
        );
      } else {
        toast.success(`${data.summary?.passed || 0} remote test completed`);
      }
    } catch (error) {
      toast.error(error.message || 'Remote execution failed');
      setExecutionResults({ success: false, error: error.message, results: [] });
    } finally {
      setIsExecuting(false);
    }
  }, [onResultsCollected, runnableTests, runnerStatus, selectedProcessName, sessionId, timeoutSeconds]);

  return (
    <div className="space-y-5">
      <div className="bg-gradient-to-r from-cyan-50 to-indigo-50 p-5 rounded-lg border border-cyan-200">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <ServerIcon className="w-8 h-8 text-cyan-700" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Remote ROS2 Execution</h3>
              <p className="text-sm text-gray-600 mt-1">
                Selected Python tests are uploaded to IFARLAB and executed in the ROS2 Docker harness.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={checkRunner}
            disabled={isChecking || isExecuting}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-cyan-200 rounded-md hover:bg-cyan-50 disabled:opacity-50"
          >
            <ArrowPathIcon className={clsx('w-4 h-4', isChecking && 'animate-spin')} />
            Check runner
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-4 text-xs">
          <div className="bg-white/80 rounded-md p-3 border border-cyan-100">
            <div className="text-gray-500">Status</div>
            <div className={clsx('font-semibold mt-1', runnerStatus?.configured ? 'text-green-700' : 'text-red-700')}>
              {runnerStatus?.configured ? 'Ready' : 'Not configured'}
            </div>
          </div>
          <div className="bg-white/80 rounded-md p-3 border border-cyan-100">
            <div className="text-gray-500">Host</div>
            <div className="font-mono mt-1 truncate">{runnerStatus?.host || '—'}</div>
          </div>
          <div className="bg-white/80 rounded-md p-3 border border-cyan-100">
            <div className="text-gray-500">Image</div>
            <div className="font-mono mt-1 truncate">{runnerStatus?.image || '—'}</div>
          </div>
          <div className="bg-white/80 rounded-md p-3 border border-cyan-100">
            <div className="text-gray-500">Authentication</div>
            <div className="font-semibold mt-1">{runnerStatus?.authentication || '—'}</div>
          </div>
        </div>
        {runnerStatus?.error && <p className="text-xs text-red-700 mt-3">{runnerStatus.error}</p>}
      </div>

      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h4 className="font-semibold text-gray-900">Selected test files</h4>
            <p className="text-sm text-gray-500 mt-1">
              {runnableTests.length} of {testCodes.length} selected tests contain executable code.
            </p>
          </div>
          <div className="text-right text-sm text-gray-700">
            <div className="font-medium">Harness timeout</div>
            <div className="mt-1 text-xs text-gray-500">10 min / test · managed remotely</div>
          </div>
        </div>
        <p className="mt-3 rounded bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Tests run sequentially against the shared robot. The harness may remain silent while a test is running;
          timeout cleanup and robot reset can make a timed-out test take about 15 minutes before a result returns.
        </p>

        <div className="mt-4 max-h-48 overflow-y-auto border border-gray-200 rounded-md divide-y">
          {runnableTests.length ? runnableTests.map((test, index) => (
            <div key={test.test_id || index} className="px-3 py-2 flex items-center justify-between text-sm">
              <span className="font-medium text-gray-800">{test.test_name || test.filename || test.test_id || `Test ${index + 1}`}</span>
              <div className="flex items-center gap-2">
                {test.oracle && (
                  <span className={clsx(
                    'text-xs font-semibold px-2 py-0.5 rounded',
                    test.oracle.passed ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700',
                  )}>
                    Oracle {test.oracle.passed ? 'PASS' : 'FAIL'} · {test.oracle.score ?? 0}
                  </span>
                )}
                <span className="text-xs text-gray-500">{testContent(test).length.toLocaleString()} chars</span>
              </div>
            </div>
          )) : (
            <div className="px-3 py-5 text-sm text-gray-500 text-center">Select tests above to enable remote execution.</div>
          )}
        </div>

        <button
          type="button"
          onClick={executeTests}
          disabled={isExecuting || !runnerStatus?.configured || runnableTests.length === 0}
          className="mt-4 flex items-center justify-center gap-2 w-full px-4 py-3 bg-cyan-700 text-white rounded-md hover:bg-cyan-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isExecuting ? <ArrowPathIcon className="w-5 h-5 animate-spin" /> : <CloudArrowUpIcon className="w-5 h-5" />}
          {isExecuting ? `Uploading and running ${runnableTests.length} tests...` : 'Upload and run on IFARLAB'}
        </button>
      </div>

      {executionResults && (
        <div className="bg-white p-5 rounded-lg border border-gray-200">
          <h4 className="font-semibold text-gray-900">Execution results</h4>
          {executionResults.summary && (
            <>
              <div className="flex flex-wrap gap-3 mt-3 text-sm">
                <span className="px-3 py-1 rounded bg-gray-100">Total: {executionResults.summary.total}</span>
                <span className="px-3 py-1 rounded bg-green-100 text-green-800">Passed: {executionResults.summary.passed}</span>
                <span className="px-3 py-1 rounded bg-red-100 text-red-800">Failed: {executionResults.summary.failed}</span>
                <span className="px-3 py-1 rounded bg-orange-100 text-orange-800">Errors: {executionResults.summary.error || 0}</span>
                <span className="px-3 py-1 rounded bg-amber-100 text-amber-800">Blocked: {executionResults.summary.blocked || 0}</span>
                <span className="px-3 py-1 rounded bg-gray-200 text-gray-800">Not executed: {executionResults.summary.not_executed || 0}</span>
                <span className="px-3 py-1 rounded bg-purple-100 text-purple-800">Invalid: {executionResults.summary.invalid || 0}</span>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                Failed means an assertion did not match its expected result. Error, Blocked, and Not executed
                indicate that a valid functional verdict could not be produced.
              </p>
            </>
          )}
          <div className="space-y-3 mt-4">
            {(executionResults.results || []).map((result, index) => {
              const verdict = resultVerdict(result);
              const verdictMeta = VERDICT_META[verdict] || VERDICT_META.error;
              return (
                <div key={result.execution_id || `${result.test_id}-${index}`} className="border border-gray-200 rounded-md p-3">
                  <div className="flex items-center gap-2">
                    {verdict === 'passed' && <CheckCircleIcon className="w-5 h-5 text-green-600" />}
                    {verdict === 'failed' && <XCircleIcon className="w-5 h-5 text-red-600" />}
                    {(verdict === 'error' || verdict === 'blocked') && <ExclamationTriangleIcon className="w-5 h-5 text-amber-600" />}
                    {(verdict === 'not_executed' || verdict === 'invalid') && <MinusCircleIcon className="w-5 h-5 text-gray-600" />}
                    <span className="font-medium text-sm">{result.filename || result.test_id}</span>
                    <span className={clsx('ml-auto text-xs font-semibold', verdictMeta.text)}>
                      {verdictMeta.label}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    {result.exit_code !== null && result.exit_code !== undefined && (
                      <span className="rounded bg-gray-100 px-2 py-1 text-gray-700">Exit {result.exit_code}</span>
                    )}
                    {result.reset_status && (
                      <span className={clsx(
                        'rounded px-2 py-1',
                        result.reset_status === 'failed'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-cyan-100 text-cyan-800',
                      )}>
                        Reset: {result.reset_status}
                      </span>
                    )}
                  </div>
                  {result.artifacts?.[0]?.remote_path && (
                    <p className="text-xs text-gray-500 mt-2 font-mono">{result.artifacts[0].remote_path}</p>
                  )}
                  {(result.logs || result.error) && (
                    <pre className="mt-3 p-3 bg-gray-950 text-gray-100 rounded text-xs overflow-x-auto whitespace-pre-wrap max-h-64">
                      {result.logs || result.error}
                    </pre>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
