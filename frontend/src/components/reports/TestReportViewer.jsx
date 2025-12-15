import React from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * TestReportViewer - Renders test reports in JSON or Markdown format
 * Supports structured JSON with interactive components
 */
const TestReportViewer = ({ output, isLoading }) => {
  const [parsedReport, setParsedReport] = React.useState(null);
  const [parseError, setParseError] = React.useState(null);
  const [expandedSessions, setExpandedSessions] = React.useState({});
  const [expandedProcesses, setExpandedProcesses] = React.useState({});

  React.useEffect(() => {
    if (!output || isLoading) {
      setParsedReport(null);
      setParseError(null);
      return;
    }

    try {
      // Try to parse as JSON
      const parsed = JSON.parse(output);
      setParsedReport(parsed);
      setParseError(null);
      
      // Auto-expand first session
      if (parsed.sessions && parsed.sessions.length > 0) {
        setExpandedSessions({ 0: true });
      }
    } catch (err) {
      // Not JSON, will render as markdown
      setParsedReport(null);
      setParseError(null);
    }
  }, [output, isLoading]);

  const toggleSession = (index) => {
    setExpandedSessions(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const toggleProcess = (sessionIndex, processIndex) => {
    const key = `${sessionIndex}-${processIndex}`;
    setExpandedProcesses(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const getStatusColor = (status) => {
    const colors = {
      excellent: 'bg-green-100 text-green-800 border-green-300',
      good: 'bg-blue-100 text-blue-800 border-blue-300',
      review: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      critical: 'bg-red-100 text-red-800 border-red-300'
    };
    return colors[status] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  const getTrendIcon = (trend) => {
    if (trend === 'up') return '📈';
    if (trend === 'down') return '📉';
    return '➡️';
  };

  const getRiskColor = (severity) => {
    const colors = {
      high: 'bg-red-50 border-l-4 border-red-500',
      medium: 'bg-yellow-50 border-l-4 border-yellow-500',
      low: 'bg-blue-50 border-l-4 border-blue-500'
    };
    return colors[severity] || 'bg-gray-50 border-l-4 border-gray-500';
  };

  // Render JSON structured report
  if (parsedReport) {
    return (
      <div className="test-report-json">
        {/* Executive Summary */}
        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg p-6 mb-6 border border-indigo-200">
          <h2 className="text-2xl font-bold text-indigo-900 mb-4">📊 Executive Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="text-sm text-gray-600">Sessions Analyzed</div>
              <div className="text-3xl font-bold text-indigo-600">{parsedReport.executiveSummary.sessionsAnalyzed}</div>
            </div>
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="text-sm text-gray-600">Processes Count</div>
              <div className="text-3xl font-bold text-blue-600">{parsedReport.executiveSummary.processesCount}</div>
            </div>
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="text-sm text-gray-600">Overall Quality</div>
              <div className="text-3xl font-bold text-green-600">{parsedReport.executiveSummary.overallQuality}/10</div>
            </div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <div className="text-sm font-semibold text-gray-700 mb-2">Quality Justification</div>
            <p className="text-gray-700">{parsedReport.executiveSummary.qualityJustification}</p>
          </div>
          <div className="bg-indigo-100 rounded-lg p-4 mt-4">
            <div className="flex items-start">
              <span className="text-2xl mr-3">💡</span>
              <div>
                <div className="text-sm font-semibold text-indigo-900 mb-1">Critical Insight</div>
                <p className="text-indigo-800">{parsedReport.executiveSummary.criticalInsight}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Overall Metrics */}
        {parsedReport.metrics && (
          <div className="bg-white rounded-lg p-6 mb-6 border border-gray-200 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 mb-4">📈 Overall Metrics</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-sm text-gray-600">Total Artifacts</div>
                <div className="text-2xl font-bold text-gray-900">{parsedReport.metrics.totalArtifacts}</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-sm text-gray-600">Average Quality</div>
                <div className="text-2xl font-bold text-gray-900">{parsedReport.metrics.averageQuality}/10</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-sm text-gray-600">Coverage Rate</div>
                <div className="text-2xl font-bold text-gray-900">{parsedReport.metrics.coverageRate}</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-sm text-gray-600">Total Processes</div>
                <div className="text-2xl font-bold text-gray-900">{parsedReport.metrics.totalProcesses}</div>
              </div>
            </div>
          </div>
        )}

        {/* Sessions */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">🎯 Session Details</h2>
          {parsedReport.sessions?.map((session, sessionIndex) => (
            <div key={sessionIndex} className="bg-white rounded-lg border border-gray-200 shadow-sm mb-4">
              <div 
                className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => toggleSession(sessionIndex)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <span className="text-2xl">{expandedSessions[sessionIndex] ? '📂' : '📁'}</span>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{session.sessionName}</h3>
                      <div className="text-sm text-gray-500">{session.timestamp}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(session.status)}`}>
                      {session.status.toUpperCase()}
                    </span>
                    <span className="text-lg font-bold text-gray-700">{session.qualityScore}/10</span>
                  </div>
                </div>
              </div>

              {expandedSessions[sessionIndex] && (
                <div className="border-t border-gray-200 p-4 bg-gray-50">
                  {session.processes?.map((process, processIndex) => {
                    const processKey = `${sessionIndex}-${processIndex}`;
                    return (
                      <div key={processIndex} className="bg-white rounded-lg border border-gray-200 mb-3 overflow-hidden">
                        <div 
                          className="p-3 cursor-pointer hover:bg-gray-50 transition-colors"
                          onClick={() => toggleProcess(sessionIndex, processIndex)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span>{expandedProcesses[processKey] ? '🔽' : '▶️'}</span>
                              <span className="font-semibold text-gray-900">{process.processName}</span>
                              <span className="text-sm text-gray-500">({process.modelUsed})</span>
                            </div>
                            <span className="text-sm font-bold text-blue-600">Quality: {process.quality.score}/10</span>
                          </div>
                        </div>

                        {expandedProcesses[processKey] && (
                          <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-4">
                            {/* Metrics */}
                            {process.metrics && process.metrics.length > 0 && (
                              <div>
                                <h4 className="font-semibold text-gray-900 mb-2">📊 Metrics</h4>
                                <div className="space-y-2">
                                  {process.metrics.map((metric, idx) => (
                                    <div key={idx} className="flex items-center justify-between bg-white p-3 rounded border border-gray-200">
                                      <div className="flex items-center space-x-2">
                                        <span>{getTrendIcon(metric.trend)}</span>
                                        <span className="font-medium text-gray-800">{metric.name}:</span>
                                        <span className="text-gray-700">{metric.value}</span>
                                      </div>
                                      {metric.notes && (
                                        <span className="text-sm text-gray-500 italic">{metric.notes}</span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Quality Breakdown */}
                            {process.quality && (
                              <div>
                                <h4 className="font-semibold text-gray-900 mb-2">⭐ Quality Assessment</h4>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                  <div className="bg-white p-2 rounded text-center border border-gray-200">
                                    <div className="text-xs text-gray-600">Completeness</div>
                                    <div className="text-lg font-bold text-blue-600">{process.quality.completeness}/10</div>
                                  </div>
                                  <div className="bg-white p-2 rounded text-center border border-gray-200">
                                    <div className="text-xs text-gray-600">Clarity</div>
                                    <div className="text-lg font-bold text-blue-600">{process.quality.clarity}/10</div>
                                  </div>
                                  <div className="bg-white p-2 rounded text-center border border-gray-200">
                                    <div className="text-xs text-gray-600">Coverage</div>
                                    <div className="text-lg font-bold text-blue-600">{process.quality.coverage}/10</div>
                                  </div>
                                  <div className="bg-white p-2 rounded text-center border border-gray-200">
                                    <div className="text-xs text-gray-600">Depth</div>
                                    <div className="text-lg font-bold text-blue-600">{process.quality.depth}/10</div>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Strengths & Weaknesses */}
                            <div className="grid md:grid-cols-2 gap-4">
                              {process.strengths && process.strengths.length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-green-700 mb-2">✅ Strengths</h4>
                                  <ul className="space-y-1">
                                    {process.strengths.map((strength, idx) => (
                                      <li key={idx} className="text-sm text-gray-700 flex items-start">
                                        <span className="text-green-500 mr-2">•</span>
                                        <span>{strength}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {process.weaknesses && process.weaknesses.length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-orange-700 mb-2">⚠️ Weaknesses</h4>
                                  <ul className="space-y-1">
                                    {process.weaknesses.map((weakness, idx) => (
                                      <li key={idx} className="text-sm text-gray-700 flex items-start">
                                        <span className="text-orange-500 mr-2">•</span>
                                        <span>{weakness}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Cross Session Analysis */}
        {parsedReport.crossSessionAnalysis && (
          <div className="bg-white rounded-lg p-6 mb-6 border border-gray-200 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 mb-4">📊 Cross-Session Analysis</h2>
            
            {/* Trends */}
            {parsedReport.crossSessionAnalysis.trends && (
              <div className="mb-4">
                <h3 className="font-semibold text-gray-900 mb-3">📈 Trends</h3>
                <div className="space-y-3">
                  {parsedReport.crossSessionAnalysis.trends.map((trend, idx) => (
                    <div key={idx} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <span>{getTrendIcon(trend.trend)}</span>
                          <span className="font-semibold text-gray-900">{trend.metric}</span>
                        </div>
                        <span className="text-lg font-bold text-blue-600">{trend.change}</span>
                      </div>
                      <p className="text-sm text-gray-700 italic">{trend.insight}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Session Comparison Table */}
            {parsedReport.crossSessionAnalysis.comparison && (
              <div className="mb-4">
                <h3 className="font-semibold text-gray-900 mb-3">📋 Session Comparison</h3>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 px-4 py-2 text-left">Session</th>
                        <th className="border border-gray-300 px-4 py-2 text-center">Quality</th>
                        <th className="border border-gray-300 px-4 py-2 text-center">Coverage</th>
                        <th className="border border-gray-300 px-4 py-2 text-center">Issues</th>
                        <th className="border border-gray-300 px-4 py-2 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {parsedReport.crossSessionAnalysis.comparison.map((comp, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="border border-gray-300 px-4 py-2 font-medium">{comp.sessionName}</td>
                          <td className="border border-gray-300 px-4 py-2 text-center font-bold text-blue-600">{comp.quality}</td>
                          <td className="border border-gray-300 px-4 py-2 text-center">{comp.coverage}</td>
                          <td className="border border-gray-300 px-4 py-2 text-center">{comp.issuesFound}</td>
                          <td className="border border-gray-300 px-4 py-2 text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(comp.status)}`}>
                              {comp.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Risks */}
        {parsedReport.risks && (
          <div className="bg-white rounded-lg p-6 mb-6 border border-gray-200 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 mb-4">⚠️ Risk Assessment</h2>
            {['high', 'medium', 'low'].map(severity => (
              parsedReport.risks[severity] && parsedReport.risks[severity].length > 0 && (
                <div key={severity} className="mb-4">
                  <h3 className="font-semibold text-gray-900 mb-2 capitalize">{severity} Priority Risks</h3>
                  <div className="space-y-2">
                    {parsedReport.risks[severity].map((risk, idx) => (
                      <div key={idx} className={`p-4 rounded-lg ${getRiskColor(severity)}`}>
                        <div className="font-semibold text-gray-900 mb-1">{risk.issue}</div>
                        <div className="text-sm text-gray-700 mb-2">Impact: {risk.impact}</div>
                        <div className="text-sm text-gray-600 italic">Mitigation: {risk.mitigation}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        )}

        {/* Recommendations */}
        {parsedReport.recommendations && (
          <div className="bg-white rounded-lg p-6 mb-6 border border-gray-200 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 mb-4">💡 Recommendations</h2>
            {['immediate', 'shortTerm', 'longTerm'].map(timeframe => (
              parsedReport.recommendations[timeframe] && parsedReport.recommendations[timeframe].length > 0 && (
                <div key={timeframe} className="mb-4">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    {timeframe === 'immediate' ? '🔴 Immediate Actions' : 
                     timeframe === 'shortTerm' ? '🟡 Short-term Actions' : 
                     '🟢 Long-term Actions'}
                  </h3>
                  <div className="space-y-2">
                    {parsedReport.recommendations[timeframe].map((rec, idx) => (
                      <div key={idx} className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="font-semibold text-gray-900">{rec.action}</div>
                            <div className="text-sm text-gray-600 mt-1">Expected Outcome: {rec.outcome}</div>
                          </div>
                          <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-medium">
                            P{rec.priority}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        )}
      </div>
    );
  }

  // Fallback to markdown rendering
  return (
    <div className="test-report-markdown-compact">
      <ReactMarkdown>{output || ''}</ReactMarkdown>
    </div>
  );
};

export default TestReportViewer;
