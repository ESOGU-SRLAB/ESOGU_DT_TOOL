import React from 'react';
import { clsx } from 'clsx';
import { BeakerIcon } from '@heroicons/react/24/outline';

/**
 * TestExecutionMethodSelector
 * ----------------------------
 * Pipeline test execution yöntemi seçici kartı.
 * GlobalAIConfig ile aynı kart pattern'ini kullanır.
 *
 * Props:
 *   method              {string}   "ai" | "docker" | "robot" | "ros2" | "ssh_docker"
 *   onMethodChange      {fn}       (newMethod: string) => void
 *   dockerAvailable     {boolean}  Docker Engine çalışıyor mu?
 *   dockerConfig        {object}   { language, packages, timeout }
 *   onDockerConfigChange {fn}      (field, value) => void
 *   robotConfig         {object}   { robotType, simulationPrecision }
 *   onRobotConfigChange  {fn}      (field, value) => void
 *   ros2Available       {boolean}  ROS2 container çalışıyor mu?
 *   ros2Config          {object}   { visualCount, timeout }
 *   onRos2ConfigChange  {fn}       (field, value) => void
 *   ros2ContainerName   {string}   Tespit edilen container ismi
 *   selectedProcesses   {Set}      Pipeline'da seçili adımlar
 */
export default function TestExecutionMethodSelector({
  method = 'ai',
  onMethodChange,
  dockerAvailable = false,
  dockerConfig = { language: 'python', packages: '', timeout: 300 },
  onDockerConfigChange,
  robotConfig = { robotType: 'generic', simulationPrecision: 'medium' },
  onRobotConfigChange,
  ros2Available = false,
  ros2Config = { visualCount: 0, timeout: 120 },
  onRos2ConfigChange,
  ros2ContainerName = '',
  remoteRos2Config = { timeout: 300 },
  onRemoteRos2ConfigChange,
  selectedProcesses,
}) {
  // test-execution adımı seçili değilse hiç render etme
  if (selectedProcesses && !selectedProcesses.has('test-execution')) {
    return null;
  }

  const dockerDisabled = !dockerAvailable;

  const methods = [
    {
      id: 'ai',
      label: 'AI Execution',
      icon: '🤖',
      activeColor: 'text-indigo-700',
      description: 'Tests are simulated by the AI model via MCP server',
      disabled: false,
      tooltip: null,
    },
    {
      id: 'docker',
      label: '🐳 Docker Execution',
      icon: '',
      activeColor: 'text-blue-700',
      description: 'Tests run in an isolated Docker container (real execution)',
      disabled: dockerDisabled,
      tooltip: dockerDisabled ? 'Docker is not running. Start Docker Engine to enable this option.' : null,
    },
    {
      id: 'robot',
      label: '🦾 Robot Simulation',
      icon: '',
      activeColor: 'text-green-700',
      description: 'Robot arm kinematic simulation via Docker container',
      disabled: dockerDisabled,
      tooltip: dockerDisabled ? 'Docker is not running. Start Docker Engine to enable this option.' : null,
    },
    {
      id: 'ros2',
      label: '🦿 ROS2 Docker',
      icon: '',
      activeColor: 'text-teal-700',
      description: 'Run tests inside ros2_colcon_workspace:humble container',
      disabled: !ros2Available,
      tooltip: !ros2Available ? 'ROS2 container is not running. Start it first (README_Docker.md Step 4).' : null,
    },
    {
      id: 'ssh_docker',
      label: '🌐 Remote ROS2',
      icon: '',
      activeColor: 'text-cyan-700',
      description: 'Transfer generated Python tests with SCP and run the remote ROS2 harness over SSH',
      disabled: false,
      tooltip: 'Requires server-side SSH_EXECUTION_HOST and SSH key configuration.',
    },
  ];

  const LANGUAGES = [
    { id: 'python',     label: 'Python'     },
    { id: 'javascript', label: 'JavaScript' },
    { id: 'java',       label: 'Java'       },
    { id: 'csharp',     label: 'C#'         },
    { id: 'go',         label: 'Go'         },
    { id: 'rust',       label: 'Rust'       },
  ];

  const ROBOT_TYPES = [
    { id: 'generic',       label: 'Generic 3-DOF',         desc: 'Simple 3-axis robotic arm' },
    { id: 'industrial',    label: 'Industrial 6-DOF',       desc: '6-axis industrial robot' },
    { id: 'collaborative', label: 'Collaborative 4-DOF',    desc: 'Human-robot cobot' },
  ];

  const PRECISIONS = [
    { id: 'low',    label: 'Low'    },
    { id: 'medium', label: 'Medium' },
    { id: 'high',   label: 'High'   },
  ];

  return (
    <div className="border rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-teal-50 to-cyan-50 border-b border-teal-100 flex items-center space-x-3 rounded-t-lg">
        <BeakerIcon className="h-5 w-5 text-teal-600 flex-shrink-0" />
        <div>
          <h3 className="font-semibold text-gray-900 text-sm">Test Execution Method</h3>
          <p className="text-xs text-gray-500">
            Select how the <span className="font-medium">test-execution</span> step will run in the pipeline
          </p>
        </div>
        {/* Docker status badge */}
        <span className={clsx(
          'ml-auto text-xs font-medium px-2 py-1 rounded-full flex-shrink-0',
          dockerAvailable
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-500'
        )}>
          {dockerAvailable ? '🐳 Docker Ready' : '🐳 Docker Offline'}
        </span>
        {/* ROS2 status badge */}
        <span className={clsx(
          'ml-1 text-xs font-medium px-2 py-1 rounded-full flex-shrink-0',
          ros2Available
            ? 'bg-teal-100 text-teal-700'
            : 'bg-gray-100 text-gray-500'
        )}>
          {ros2Available ? `🦿 ROS2: ${ros2ContainerName || 'Ready'}` : '🦿 ROS2 Offline'}
        </span>
      </div>

      {/* Method selector — pill tabs */}
      <div className="px-4 pt-3 pb-2">
        <div className="flex items-center bg-gray-100 p-1 rounded-lg gap-1">
          {methods.map(m => (
            <button
              key={m.id}
              type="button"
              disabled={m.disabled}
              title={m.tooltip ?? ''}
              onClick={() => !m.disabled && onMethodChange?.(m.id)}
              className={clsx(
                'flex-1 px-3 py-2 rounded-md text-xs font-medium transition-all duration-150',
                method === m.id
                  ? `bg-white shadow-sm ${m.activeColor}`
                  : 'text-gray-600 hover:text-gray-900',
                m.disabled && 'opacity-40 cursor-not-allowed hover:text-gray-600'
              )}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sub-config panel — changes based on selected method */}
      <div className="px-4 pb-4">
        {method === 'ai' && (
          <div className="mt-2 p-3 bg-indigo-50 rounded-lg text-xs text-indigo-700 border border-indigo-100">
            <p className="font-medium mb-1">AI Execution (MCP Server)</p>
            <p className="text-indigo-600 leading-relaxed">
              Tests are sent to the MCP server at <code className="bg-indigo-100 px-1 rounded">localhost:8001</code>.
              The AI model simulates test execution and returns terminal-style output.
              Uses the global AI model selected above.
            </p>
          </div>
        )}

        {method === 'docker' && (
          <div className="mt-2 space-y-3">
            <div className="p-3 bg-blue-50 rounded-lg text-xs text-blue-700 border border-blue-100">
              <p className="font-medium mb-1">Docker Execution</p>
              <p className="text-blue-600 leading-relaxed">
                Tests run in an isolated Docker container with real process execution.
                The container is automatically created, executed, and cleaned up.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3">
              {/* Language */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Language</label>
                <select
                  value={dockerConfig.language || 'python'}
                  onChange={e => onDockerConfigChange?.('language', e.target.value)}
                  className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {LANGUAGES.map(l => (
                    <option key={l.id} value={l.id}>{l.label}</option>
                  ))}
                </select>
              </div>

              {/* Timeout */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Timeout (s)</label>
                <input
                  type="number"
                  min={30}
                  max={900}
                  value={dockerConfig.timeout ?? 300}
                  onChange={e => onDockerConfigChange?.('timeout', parseInt(e.target.value, 10) || 300)}
                  className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Mem limit info */}
              <div className="flex flex-col justify-end">
                <span className="text-xs text-gray-400 bg-gray-50 border border-gray-200 rounded-md px-2 py-1.5 text-center">
                  512 MB limit
                </span>
              </div>
            </div>

            {/* Extra packages */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Additional Packages <span className="text-gray-400 font-normal">(comma-separated, e.g. numpy, requests)</span>
              </label>
              <input
                type="text"
                placeholder="numpy, pandas, requests"
                value={dockerConfig.packages || ''}
                onChange={e => onDockerConfigChange?.('packages', e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        )}

        {method === 'robot' && (
          <div className="mt-2 space-y-3">
            <div className="p-3 bg-green-50 rounded-lg text-xs text-green-700 border border-green-100">
              <p className="font-medium mb-1">Robot Arm Simulation</p>
              <p className="text-green-600 leading-relaxed">
                Tests run inside a Docker container with <code className="bg-green-100 px-1 rounded">roboticstoolbox-python</code>.
                Forward kinematics are computed for each <code className="bg-green-100 px-1 rounded">robot.move_to_position([...])</code> call.
                Packages: numpy, scipy, matplotlib, roboticstoolbox-python, spatialmath-python.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {/* Robot type */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Robot Type</label>
                <select
                  value={robotConfig.robotType || 'generic'}
                  onChange={e => onRobotConfigChange?.('robotType', e.target.value)}
                  className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-2 focus:ring-green-500 focus:border-transparent"
                >
                  {ROBOT_TYPES.map(r => (
                    <option key={r.id} value={r.id} title={r.desc}>{r.label}</option>
                  ))}
                </select>
              </div>

              {/* Simulation precision */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Simulation Precision</label>
                <select
                  value={robotConfig.simulationPrecision || 'medium'}
                  onChange={e => onRobotConfigChange?.('simulationPrecision', e.target.value)}
                  className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-2 focus:ring-green-500 focus:border-transparent"
                >
                  {PRECISIONS.map(p => (
                    <option key={p.id} value={p.id}>{p.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Robot type description */}
            {(() => {
              const rt = ROBOT_TYPES.find(r => r.id === (robotConfig.robotType || 'generic'));
              return rt ? (
                <p className="text-xs text-gray-500 italic">{rt.desc}</p>
              ) : null;
            })()}
          </div>
        )}
        {method === 'ros2' && (
          <div className="mt-2 space-y-3">
            <div className="p-3 bg-teal-50 rounded-lg text-xs text-teal-700 border border-teal-100">
              <p className="font-medium mb-1">ROS2 Docker Execution</p>
              <p className="text-teal-600 leading-relaxed">
                Tests are injected as Python scripts into the running
                <code className="bg-teal-100 px-1 rounded"> ros2_colcon_workspace:humble</code> container via
                <code className="bg-teal-100 px-1 rounded"> docker exec</code>.
                The first <strong>N</strong> tests run with DISPLAY forwarded (GUI visible); the rest run headless.
              </p>
              {ros2ContainerName && (
                <p className="mt-1 text-teal-700">Container: <strong>{ros2ContainerName}</strong></p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Görsel Çalıştırma Sayısı (N)
                </label>
                <input
                  type="number"
                  min={0}
                  value={ros2Config.visualCount ?? 0}
                  onChange={e => onRos2ConfigChange?.('visualCount', Math.max(0, parseInt(e.target.value, 10) || 0))}
                  className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-400 mt-0.5">İlk N test Gazebo/RViz görsel açar</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Timeout / test (s)</label>
                <input
                  type="number"
                  min={10}
                  max={600}
                  value={ros2Config.timeout ?? 120}
                  onChange={e => onRos2ConfigChange?.('timeout', parseInt(e.target.value, 10) || 120)}
                  className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>
        )}
        {method === 'ssh_docker' && (
          <div className="mt-2 space-y-3">
            <div className="p-3 bg-cyan-50 rounded-lg text-xs text-cyan-700 border border-cyan-100">
              <p className="font-medium mb-1">Remote ROS2 Harness</p>
              <p className="text-cyan-600 leading-relaxed">
                Generated Python tests are copied to the configured robot computer with SCP and executed in
                <code className="bg-cyan-100 px-1 rounded"> ros2-exec-harness:0.3.2</code> over SSH.
                SSH host, key, target directory, and image are configured on the backend.
              </p>
            </div>
            <div className="max-w-xs">
              <label className="block text-xs font-medium text-gray-600 mb-1">Timeout / test (s)</label>
              <input
                type="number"
                min={10}
                max={1900}
                value={remoteRos2Config.timeout ?? 300}
                onChange={e => onRemoteRos2ConfigChange?.('timeout', parseInt(e.target.value, 10) || 300)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
