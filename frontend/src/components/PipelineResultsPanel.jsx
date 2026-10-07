import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

// ─── helpers ──────────────────────────────────────────────────────────────────

function StatusDot({ status }) {
  const cfg = {
    completed: 'bg-green-500',
    running:   'bg-blue-500 animate-pulse',
    error:     'bg-red-500',
    pending:   'bg-gray-300',
  };
  return (
    <span
      className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${cfg[status] || 'bg-gray-200'}`}
    />
  );
}

function StatusBadge({ status, duration }) {
  const cfg = {
    completed: 'bg-green-100 text-green-700',
    running:   'bg-blue-100 text-blue-700',
    error:     'bg-red-100 text-red-700',
    pending:   'bg-gray-100 text-gray-500',
  };
  const label = {
    completed: `Done${duration ? ` · ${duration.toFixed(1)}s` : ''}`,
    running:   'Running…',
    error:     'Failed',
    pending:   'Pending',
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cfg[status] || ''}`}>
      {label[status] || status}
    </span>
  );
}

function ChevronIcon({ open }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
    >
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}

// Renders markdown safely
function MD({ content }) {
  if (!content) return null;
  return (
    <div className="prose prose-sm max-w-full break-words overflow-x-auto text-gray-700">
      <ReactMarkdown
        className="whitespace-pre-wrap break-words overflow-wrap-anywhere"
        components={{
          p:          ({ children }) => <p className="break-words mb-2 last:mb-0">{children}</p>,
          li:         ({ children }) => <li className="break-words">{children}</li>,
          td:         ({ children }) => <td className="break-words max-w-xs px-2 py-1">{children}</td>,
          th:         ({ children }) => <th className="break-words px-2 py-1 font-semibold">{children}</th>,
          h1:         ({ children }) => <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0">{children}</h1>,
          h2:         ({ children }) => <h2 className="text-lg font-semibold mb-2 mt-3">{children}</h2>,
          h3:         ({ children }) => <h3 className="text-base font-medium mb-2 mt-2">{children}</h3>,
          ul:         ({ children }) => <ul className="list-disc pl-6 mb-3 space-y-1">{children}</ul>,
          ol:         ({ children }) => <ol className="list-decimal pl-6 mb-3 space-y-1">{children}</ol>,
          blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic my-3">{children}</blockquote>,
          code:       ({ children }) => <code className="bg-gray-100 px-1 rounded text-sm font-mono">{children}</code>,
          pre:        ({ children }) => <pre className="bg-gray-100 p-3 rounded overflow-x-auto mb-3 text-sm">{children}</pre>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// ─── per-step renderers ────────────────────────────────────────────────────────

function renderCodeReview(output) {
  const reviews = output?.reviews || output?.review;
  if (Array.isArray(reviews) && reviews.length > 0) {
    return reviews.map((r, i) => (
      <div key={i} className="mb-4">
        {reviews.length > 1 && (
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
            Review {i + 1}
          </p>
        )}
        <MD content={typeof r === 'string' ? r : r?.review || JSON.stringify(r, null, 2)} />
      </div>
    ));
  }
  if (typeof reviews === 'string') return <MD content={reviews} />;
  return <JsonFallback data={output} />;
}

function renderRequirementAnalysis(output) {
  const analysis = output?.analysis || output?.result?.analysis;
  if (Array.isArray(analysis)) {
    return analysis.map((item, i) => (
      <div key={i} className="mb-4">
        {item.files && (
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
            Files: {item.files}
          </p>
        )}
        <MD content={typeof item === 'string' ? item : item?.result || JSON.stringify(item, null, 2)} />
      </div>
    ));
  }
  const text = typeof output?.result === 'string' ? output.result : null;
  if (text) return <MD content={text} />;
  return <JsonFallback data={output} />;
}

function renderTestPlanning(output) {
  const plans = output?.plans;
  if (Array.isArray(plans) && plans.length > 0) {
    return plans.map((p, i) => <MD key={i} content={typeof p === 'string' ? p : JSON.stringify(p, null, 2)} />);
  }
  const plan = output?.plan;
  if (typeof plan === 'string') return <MD content={plan} />;
  return <JsonFallback data={output} />;
}

function renderEnvironmentSetup(output) {
  const setups = output?.setups;
  if (Array.isArray(setups) && setups.length > 0) {
    return setups.map((s, i) => <MD key={i} content={typeof s === 'string' ? s : JSON.stringify(s, null, 2)} />);
  }
  const text = output?.setup || output?.result;
  if (typeof text === 'string') return <MD content={text} />;
  return <JsonFallback data={output} />;
}

function renderTestScenarioGeneration(output) {
  // output may be { test_scenarios: { TestScenarios: [...], Summary: {...} } }
  // or { scenarios: [...] }
  const ts = output?.test_scenarios || output?.TestScenarios;
  const scenarios = (ts && (ts.TestScenarios || ts)) || output?.scenarios;
  const summary = (ts && ts.Summary) || output?.Summary || output?.summary;

  if (Array.isArray(scenarios) && scenarios.length > 0) {
    return (
      <div>
        {summary && (
          <div className="mb-4 bg-indigo-50 rounded-lg p-3 text-sm">
            {Object.entries(summary).map(([k, v]) => (
              <div key={k} className="flex gap-2">
                <span className="font-medium text-indigo-700 capitalize">{k.replace(/_/g, ' ')}:</span>
                <span className="text-indigo-900">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))}
          </div>
        )}
        {scenarios.map((sc, i) => (
          <div key={i} className="border rounded-lg mb-3 overflow-hidden">
            <div className="px-3 py-2 bg-gray-50 border-b flex items-center gap-2">
              <span className="text-xs font-bold text-gray-500">{sc.ID || `TS-${i + 1}`}</span>
              <span className="font-medium text-sm text-gray-800">{sc.Title || sc.title || sc.Name || `Scenario ${i + 1}`}</span>
              {(sc.Priority || sc.priority) && (
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${
                  (sc.Priority || sc.priority)?.toLowerCase() === 'high'
                    ? 'bg-red-100 text-red-700'
                    : (sc.Priority || sc.priority)?.toLowerCase() === 'medium'
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-green-100 text-green-700'
                }`}>
                  {sc.Priority || sc.priority}
                </span>
              )}
            </div>
            <div className="px-3 py-2 text-sm text-gray-700">
              {(sc.Description || sc.description) && (
                <p className="mb-1">{sc.Description || sc.description}</p>
              )}
              {(sc['Expected Result'] || sc.expected_result || sc.ExpectedResult) && (
                <p className="text-xs text-gray-500">
                  <span className="font-medium">Expected:</span>{' '}
                  {sc['Expected Result'] || sc.expected_result || sc.ExpectedResult}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  }
  return <JsonFallback data={output} />;
}

function renderTestCaseGeneration(output) {
  const results = output?.test_case_results || output?.data?.test_case_results || output?.data?.data?.test_case_results;
  const summary = output?.summary || output?.data?.summary;

  if (!results && !summary) return <JsonFallback data={output} />;

  const totalCases = Array.isArray(results)
    ? results.reduce((acc, r) => acc + (r?.test_cases?.length || 0), 0)
    : 0;

  return (
    <div>
      {summary && (
        <div className="mb-4 grid grid-cols-3 gap-3 text-center">
          {Object.entries(summary).slice(0, 6).map(([k, v]) => (
            <div key={k} className="bg-blue-50 rounded-lg p-2">
              <div className="text-lg font-bold text-blue-700">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</div>
              <div className="text-xs text-blue-500 capitalize">{k.replace(/_/g, ' ')}</div>
            </div>
          ))}
        </div>
      )}
      {!summary && totalCases > 0 && (
        <p className="text-sm text-gray-500 mb-3">{totalCases} test case(s) generated</p>
      )}
      {Array.isArray(results) && results.map((r, i) => (
        <details key={i} className="border rounded-lg mb-2 overflow-hidden">
          <summary className="px-3 py-2 bg-gray-50 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-100 flex items-center gap-2">
            <span>{r.scenario_id || r.scenario_title || `Scenario ${i + 1}`}</span>
            <span className="ml-auto text-xs text-gray-400">{r.test_cases?.length || 0} cases</span>
          </summary>
          <div className="px-3 py-2 divide-y divide-gray-100">
            {(r.test_cases || []).map((tc, j) => (
              <div key={j} className="py-2">
                <p className="text-sm font-medium text-gray-700">{tc.title || tc.name || `TC-${j + 1}`}</p>
                {tc.description && <p className="text-xs text-gray-500 mt-0.5">{tc.description}</p>}
                {tc.steps && (
                  <ol className="list-decimal list-inside mt-1 text-xs text-gray-600 space-y-0.5">
                    {(Array.isArray(tc.steps) ? tc.steps : [tc.steps]).map((s, k) => (
                      <li key={k}>{typeof s === 'object' ? (s.action || JSON.stringify(s)) : s}</li>
                    ))}
                  </ol>
                )}
              </div>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}

function renderTestCaseOptimization(output) {
  const unique = output?.unique_test_cases || output?.data?.unique_test_cases;
  const similar = output?.similar_test_cases || output?.data?.similar_test_cases;
  const stats = {
    'Unique Cases': Array.isArray(unique) ? unique.length : (output?.total_unique_test_cases || '—'),
    'Similar Cases': Array.isArray(similar) ? similar.length : (output?.total_similar_test_cases || '—'),
    'Total Comparisons': output?.total_comparisons || output?.data?.total_comparisons || '—',
    'Total Cases': output?.total_test_cases || output?.data?.total_test_cases || '—',
  };

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 mb-4 text-center">
        {Object.entries(stats).map(([k, v]) => (
          <div key={k} className={`rounded-lg p-3 ${k === 'Unique Cases' ? 'bg-green-50' : k === 'Similar Cases' ? 'bg-yellow-50' : 'bg-gray-50'}`}>
            <div className={`text-2xl font-bold ${k === 'Unique Cases' ? 'text-green-600' : k === 'Similar Cases' ? 'text-yellow-600' : 'text-gray-600'}`}>{String(v)}</div>
            <div className={`text-xs mt-0.5 ${k === 'Unique Cases' ? 'text-green-500' : k === 'Similar Cases' ? 'text-yellow-500' : 'text-gray-400'}`}>{k}</div>
          </div>
        ))}
      </div>
      {Array.isArray(unique) && unique.length > 0 && (
        <details className="border rounded-lg mb-2">
          <summary className="px-3 py-2 bg-green-50 cursor-pointer text-sm font-medium text-green-700 hover:bg-green-100">
            ✅ Unique Test Cases ({unique.length})
          </summary>
          <div className="px-3 py-2 divide-y divide-gray-100 text-sm">
            {unique.map((tc, i) => (
              <div key={i} className="py-1.5 text-gray-700">{tc.title || tc.name || tc.test_case_id || JSON.stringify(tc)}</div>
            ))}
          </div>
        </details>
      )}
      {Array.isArray(similar) && similar.length > 0 && (
        <details className="border rounded-lg mb-2">
          <summary className="px-3 py-2 bg-yellow-50 cursor-pointer text-sm font-medium text-yellow-700 hover:bg-yellow-100">
            ⚠️ Similar/Duplicate Cases ({similar.length})
          </summary>
          <div className="px-3 py-2 divide-y divide-gray-100 text-sm">
            {similar.map((tc, i) => (
              <div key={i} className="py-1.5 text-gray-700">{tc.title || tc.name || tc.test_case_id || JSON.stringify(tc)}</div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function renderTestCodeGeneration(output) {
  const summary = output?.summary || output?.result?.summary;
  const tests = output?.generated_tests || output?.result?.generated_tests;
  const env = output?.environment_info || output?.result?.environment_info;

  return (
    <div>
      {summary && (
        <div className="mb-4 grid grid-cols-3 gap-3 text-center">
          {[
            { label: 'Total', value: summary.total_test_cases, color: 'bg-gray-50 text-gray-600' },
            { label: 'Generated', value: summary.generated_count, color: 'bg-green-50 text-green-600' },
            { label: 'Failed', value: summary.failed_count, color: 'bg-red-50 text-red-600' },
          ].map(({ label, value, color }) => value !== undefined && (
            <div key={label} className={`rounded-lg p-2 ${color.split(' ')[0]}`}>
              <div className={`text-2xl font-bold ${color.split(' ')[1]}`}>{value}</div>
              <div className="text-xs text-gray-400 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}
      {env && (
        <div className="mb-4 text-xs bg-gray-50 rounded p-2 text-gray-600">
          <span className="font-medium">Language:</span> {env.language || '—'}{' '}
          <span className="font-medium ml-2">Framework:</span> {env.framework || '—'}
        </div>
      )}
      {Array.isArray(tests) && tests.map((t, i) => (
        <details key={i} className="border rounded-lg mb-2 overflow-hidden">
          <summary className="px-3 py-2 bg-gray-50 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-100 flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full flex-shrink-0 ${
              t.status === 'success' || t.status === 'generated' ? 'bg-green-400' : 'bg-red-400'
            }`} />
            <span className="flex-1 truncate">{t.title || t.test_case_id || `Test ${i + 1}`}</span>
            {t.framework && <span className="text-xs text-gray-400">{t.framework}</span>}
            {t.oracle && (
              <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
                t.oracle.passed ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
              }`}>
                Oracle {t.oracle.score ?? 0}
              </span>
            )}
          </summary>
          <div className="bg-gray-900 text-gray-100 text-xs p-3 overflow-x-auto">
            <pre className="whitespace-pre-wrap font-mono">{t.code || t.test_code || '// No code available'}</pre>
          </div>
          {t.explanation && (
            <div className="px-3 py-2 text-xs text-gray-500 border-t bg-gray-50">{t.explanation}</div>
          )}
        </details>
      ))}
    </div>
  );
}

function renderTestExecution(output) {
  const results = output?.execution_results;
  const summary = output?.summary;

  return (
    <div>
      {summary && (
        <div className="mb-4 grid grid-cols-3 gap-3 text-center">
          {[
            { label: 'Total', value: summary.total, color: 'bg-gray-50 text-gray-600' },
            { label: 'Passed', value: summary.successful || summary.passed, color: 'bg-green-50 text-green-600' },
            { label: 'Failed', value: summary.failed, color: 'bg-red-50 text-red-600' },
          ].map(({ label, value, color }) => value !== undefined && (
            <div key={label} className={`rounded-lg p-2 ${color.split(' ')[0]}`}>
              <div className={`text-2xl font-bold ${color.split(' ')[1]}`}>{value}</div>
              <div className="text-xs text-gray-400 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}
      {Array.isArray(results) && results.map((r, i) => (
        <details key={i} className="border rounded-lg mb-2">
          <summary className={`px-3 py-2 cursor-pointer text-sm font-medium hover:opacity-90 flex items-center gap-2 ${
            r.status === 'passed' || r.status === 'success'
              ? 'bg-green-50 text-green-700'
              : r.status === 'failed' || r.status === 'error'
              ? 'bg-red-50 text-red-700'
              : 'bg-gray-50 text-gray-700'
          }`}>
            <span>{r.status === 'passed' || r.status === 'success' ? '✅' : r.status === 'failed' || r.status === 'error' ? '❌' : '⏸️'}</span>
            <span className="flex-1 truncate">{r.test_id || r.title || `Test ${i + 1}`}</span>
          </summary>
          {r.output && (
            <div className="px-3 py-2 text-xs text-gray-600 border-t bg-gray-50 font-mono whitespace-pre-wrap overflow-x-auto">
              {r.output}
            </div>
          )}
        </details>
      ))}
      {!results && !summary && <JsonFallback data={output} />}
    </div>
  );
}

function renderReport(output) {
  const content = output?.report_content || output?.content;
  if (typeof content === 'string') return <MD content={content} />;
  return <JsonFallback data={output} />;
}

function renderTestClosure(output) {
  const qe = output?.quality_evaluation;
  const content = output?.report_content || output?.content;
  const score = qe?.overall_score;

  return (
    <div>
      {score !== undefined && (
        <div className="mb-4 flex items-center gap-4 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg">
          <div className="text-center">
            <div className="text-3xl font-bold text-indigo-600">{typeof score === 'number' ? score.toFixed(1) : score}</div>
            <div className="text-xs text-indigo-400">Overall Score</div>
          </div>
          {qe && (
            <div className="flex-1 grid grid-cols-3 gap-2 text-center text-xs">
              {['completeness', 'coverage', 'clarity', 'depth', 'consistency'].map(k =>
                qe[k] !== undefined && (
                  <div key={k} className="bg-white rounded p-1.5 shadow-sm">
                    <div className="font-bold text-indigo-700">{typeof qe[k] === 'number' ? qe[k].toFixed(1) : qe[k]}</div>
                    <div className="text-gray-400 capitalize">{k}</div>
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}
      {content && <MD content={content} />}
      {!content && !score && <JsonFallback data={output} />}
    </div>
  );
}

function JsonFallback({ data }) {
  return (
    <pre className="text-xs bg-gray-50 rounded p-3 overflow-x-auto text-gray-700 whitespace-pre-wrap">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function renderStepOutput(stepId, output) {
  if (!output || Object.keys(output).length === 0) {
    return <p className="text-sm text-gray-400 italic">No output data available.</p>;
  }

  switch (stepId) {
    case 'code-review':              return renderCodeReview(output);
    case 'requirement-analysis':     return renderRequirementAnalysis(output);
    case 'test-planning':            return renderTestPlanning(output);
    case 'environment-setup':        return renderEnvironmentSetup(output);
    case 'test-scenario-generation': return renderTestScenarioGeneration(output);
    case 'test-case-generation':     return renderTestCaseGeneration(output);
    case 'test-case-optimization':   return renderTestCaseOptimization(output);
    case 'test-code-generation':     return renderTestCodeGeneration(output);
    case 'test-execution':           return renderTestExecution(output);
    case 'test-reporting':           return renderReport(output);
    case 'test-closure':             return renderTestClosure(output);
    default:                         return <JsonFallback data={output} />;
  }
}

// ─── main component ───────────────────────────────────────────────────────────

export default function PipelineResultsPanel({ processes, pipelineStatus, pipelineResults }) {
  const [expandedSteps, setExpandedSteps] = useState(new Set());

  function toggle(stepId) {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  }

  const hasAnyActivity = Object.values(pipelineStatus || {}).some(s => s && s !== 'idle');

  if (!hasAnyActivity) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-8">
        <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-indigo-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0H3" />
          </svg>
        </div>
        <p className="text-gray-500 font-medium">No pipeline running</p>
        <p className="text-sm text-gray-400 mt-1">Start the pipeline to see step-by-step results here.</p>
      </div>
    );
  }

  const pipelineSteps = (processes || []).filter(p =>
    pipelineStatus && pipelineStatus[p.id] !== undefined
  );

  return (
    <div className="space-y-3">
      {pipelineSteps.map((process) => {
        const stepId = process.id;
        const status = pipelineStatus?.[stepId] || 'pending';
        const result = pipelineResults?.[stepId];
        const isExpanded = expandedSteps.has(stepId);
        const canExpand = status === 'completed' || status === 'error';

        // Border color on left edge per status
        const borderColor = {
          completed: 'border-l-green-400',
          running:   'border-l-blue-400',
          error:     'border-l-red-400',
          pending:   'border-l-gray-200',
        }[status] || 'border-l-gray-200';

        return (
          <div
            key={stepId}
            className={`border border-l-4 ${borderColor} rounded-lg bg-white shadow-sm overflow-hidden`}
          >
            {/* Header */}
            <div
              className={`flex items-center gap-3 px-4 py-3 ${canExpand ? 'cursor-pointer hover:bg-gray-50' : ''}`}
              onClick={() => canExpand && toggle(stepId)}
            >
              <StatusDot status={status} />
              <span className="flex-1 text-sm font-medium text-gray-800">{process.name}</span>
              <StatusBadge status={status} duration={result?.duration_seconds} />
              {canExpand && <ChevronIcon open={isExpanded} />}
            </div>

            {/* Error message (always visible when failed) */}
            {status === 'error' && result?.error && (
              <div className="px-4 pb-3">
                <div className="bg-red-50 border border-red-200 rounded p-2 text-xs text-red-700 font-mono">
                  {result.error}
                </div>
              </div>
            )}

            {/* Expandable body */}
            {isExpanded && canExpand && (
              <div className="border-t border-gray-100 px-4 py-4">
                {result?.output
                  ? renderStepOutput(stepId, result.output)
                  : (
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                      <svg className="animate-spin h-4 w-4 text-gray-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Loading result…
                    </div>
                  )
                }
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
