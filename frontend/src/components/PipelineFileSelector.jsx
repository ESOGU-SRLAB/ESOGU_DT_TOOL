import React, { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import { 
  DocumentIcon,
  DocumentTextIcon,
  CodeBracketIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  PlusIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

/**
 * Pipeline File Selector Component
 * 
 * Pipeline'ın en üstünde gösterilen, tüm dosya ve process mapping'lerini
 * yöneten ana file management component'i.
 */
export default function PipelineFileSelector({
  managedFiles,
  fileProcessMappings,
  selectedProcesses,
  processes,
  onFileProcessMapping,
  onFileDelete,
  onFileUpload
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [editingFileId, setEditingFileId] = useState(null);
  const [tempMappings, setTempMappings] = useState({});

  // File icon helper
  const getFileIcon = (fileType) => {
    switch (fileType) {
      case 'Source Code':
        return <CodeBracketIcon className="h-5 w-5 text-blue-500" />;
      case 'Project AST':
        return <CodeBracketIcon className="h-5 w-5 text-purple-500" />;
      case 'Requirement Document':
        return <DocumentTextIcon className="h-5 w-5 text-green-500" />;
      default:
        return <DocumentIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  // Calculate file statistics
  const fileStats = {
    total: managedFiles.length,
    mapped: managedFiles.filter(file => 
      fileProcessMappings[file.id]?.length > 0
    ).length,
    unmapped: managedFiles.filter(file => 
      !fileProcessMappings[file.id] || fileProcessMappings[file.id].length === 0
    ).length
  };

  // Get selected processes as array
  const selectedProcessArray = Array.from(selectedProcesses);
  const selectedProcessDetails = selectedProcessArray.map(id => 
    processes.find(p => p.id === id)
  ).filter(Boolean);

  // Handle edit mode for a file
  const handleEditFile = (fileId) => {
    setEditingFileId(fileId);
    setTempMappings({
      ...tempMappings,
      [fileId]: fileProcessMappings[fileId] || []
    });
  };

  // Handle save mappings for a file
  const handleSaveMappings = (fileId) => {
    if (tempMappings[fileId]) {
      onFileProcessMapping(fileId, tempMappings[fileId]);
    }
    setEditingFileId(null);
  };

  // Handle cancel edit
  const handleCancelEdit = () => {
    setEditingFileId(null);
    setTempMappings({});
  };

  // Toggle process mapping in temp state
  const handleToggleProcessMapping = (fileId, processId) => {
    const currentMappings = tempMappings[fileId] || fileProcessMappings[fileId] || [];
    const newMappings = currentMappings.includes(processId)
      ? currentMappings.filter(id => id !== processId)
      : [...currentMappings, processId];
    
    setTempMappings({
      ...tempMappings,
      [fileId]: newMappings
    });
  };

  // Auto-map all files to all selected processes (quick action)
  const handleAutoMapAll = () => {
    managedFiles.forEach(file => {
      onFileProcessMapping(file.id, selectedProcessArray);
    });
    toast.success('All files have been mapped to all selected processes!');
  };

  // Clear all mappings
  const handleClearAll = () => {
    toast(
      (t) => (
        <div>
          <p className="font-medium mb-3">Are you sure you want to clear all file mappings?</p>
          <div className="flex space-x-2">
            <button
              onClick={() => {
                managedFiles.forEach(file => {
                  onFileProcessMapping(file.id, []);
                });
                toast.dismiss(t.id);
                toast.success('All file mappings cleared!');
              }}
              className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
            >
              Yes, Clear All
            </button>
            <button
              onClick={() => toast.dismiss(t.id)}
              className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        </div>
      ),
      {
        duration: Infinity,
        style: { maxWidth: '500px' }
      }
    );
  };

  return (
    <div className="border rounded-lg bg-white shadow-sm mb-4">
      {/* Header */}
      <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-blue-100 rounded transition-colors"
            >
              {isExpanded ? (
                <ChevronDownIcon className="h-5 w-5 text-blue-600" />
              ) : (
                <ChevronRightIcon className="h-5 w-5 text-blue-600" />
              )}
            </button>
            
            <div className="flex items-center space-x-2">
              <DocumentIcon className="h-6 w-6 text-blue-600" />
              <div>
                <h3 className="font-semibold text-gray-900">Pipeline File Selection & Mapping</h3>
                <p className="text-sm text-gray-600">
                  {fileStats.total} file{fileStats.total !== 1 ? 's' : ''} available
                  {fileStats.unmapped > 0 && (
                    <span className="ml-2 text-yellow-600 font-medium">
                      ({fileStats.unmapped} unmapped)
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center space-x-2">
            {managedFiles.length > 0 && selectedProcessArray.length > 0 && (
              <>
                <button
                  onClick={handleAutoMapAll}
                  className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  Map All to Pipeline
                </button>
                <button
                  onClick={handleClearAll}
                  className="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
                >
                  Clear All
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4">
          {/* No Files State */}
          {managedFiles.length === 0 ? (
            <div className="text-center py-8">
              <DocumentIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600 mb-4">No files uploaded yet</p>
              <button
                onClick={() => {
                  // Trigger file upload - switch to Files tab
                  const filesTab = document.querySelector('[data-tab="files"]');
                  if (filesTab) {
                    filesTab.click();
                  }
                }}
                className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors inline-flex items-center space-x-2"
              >
                <PlusIcon className="h-5 w-5" />
                <span>Go to Files Tab to Upload</span>
              </button>
            </div>
          ) : (
            <>
              {/* File List */}
              <div className="space-y-3">
                {managedFiles.map((file) => {
                  const fileMappings = fileProcessMappings[file.id] || [];
                  const isEditing = editingFileId === file.id;
                  const currentMappings = isEditing ? (tempMappings[file.id] || fileMappings) : fileMappings;
                  const mappedProcessNames = currentMappings
                    .map(id => processes.find(p => p.id === id)?.name)
                    .filter(Boolean);

                  return (
                    <div
                      key={file.id}
                      className={clsx(
                        'border rounded-lg p-4 transition-all',
                        fileMappings.length === 0 ? 'border-yellow-300 bg-yellow-50' : 'border-gray-200 bg-gray-50',
                        isEditing && 'ring-2 ring-indigo-500'
                      )}
                    >
                      {/* File Header */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-start space-x-3 flex-1">
                          {getFileIcon(file.type)}
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-gray-900 truncate">{file.name}</h4>
                            <p className="text-xs text-gray-500 mt-1">
                              {file.type} • {file.size ? `${(file.size / 1024).toFixed(1)} KB` : 'Unknown size'}
                            </p>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center space-x-2 ml-4">
                          {!isEditing ? (
                            <>
                              <button
                                onClick={() => handleEditFile(file.id)}
                                className="px-3 py-1 text-sm bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 transition-colors"
                              >
                                Edit Mapping
                              </button>
                              <button
                                onClick={() => {
                                  toast(
                                    (t) => (
                                      <div>
                                        <p className="font-medium mb-3">Delete {file.name}?</p>
                                        <div className="flex space-x-2">
                                          <button
                                            onClick={() => {
                                              onFileDelete(file.id);
                                              toast.dismiss(t.id);
                                              toast.success('File deleted successfully!');
                                            }}
                                            className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                                          >
                                            Delete
                                          </button>
                                          <button
                                            onClick={() => toast.dismiss(t.id)}
                                            className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                                          >
                                            Cancel
                                          </button>
                                        </div>
                                      </div>
                                    ),
                                    {
                                      duration: Infinity,
                                      style: { maxWidth: '400px' }
                                    }
                                  );
                                }}
                                className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                              >
                                <XMarkIcon className="h-5 w-5" />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => handleSaveMappings(file.id)}
                                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                              >
                                Save
                              </button>
                              <button
                                onClick={handleCancelEdit}
                                className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
                              >
                                Cancel
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Mapping Display/Edit */}
                      {!isEditing ? (
                        // Display Mode
                        <div className="ml-8">
                          {fileMappings.length === 0 ? (
                            <div className="flex items-center space-x-2 text-yellow-700">
                              <ExclamationTriangleIcon className="h-4 w-4" />
                              <span className="text-sm">Not mapped to any process</span>
                            </div>
                          ) : (
                            <div>
                              <p className="text-xs font-medium text-gray-700 mb-2">
                                Mapped to these processes:
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {mappedProcessNames.map((name, idx) => (
                                  <span
                                    key={idx}
                                    className="inline-flex items-center space-x-1 px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full"
                                  >
                                    <CheckCircleIcon className="h-3 w-3" />
                                    <span>{name}</span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        // Edit Mode
                        <div className="ml-8 space-y-2">
                          <p className="text-sm font-medium text-gray-700 mb-3">
                            ✓ Select processes where this file will be used:
                          </p>
                          <div className="grid grid-cols-2 gap-2">
                            {selectedProcessDetails.map((process) => {
                              const isSelected = currentMappings.includes(process.id);
                              return (
                                <label
                                  key={process.id}
                                  className={clsx(
                                    'flex items-center space-x-2 p-2 rounded cursor-pointer transition-colors',
                                    isSelected ? 'bg-indigo-100 border border-indigo-300' : 'bg-white border border-gray-200 hover:bg-gray-50'
                                  )}
                                >
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => handleToggleProcessMapping(file.id, process.id)}
                                    className="h-4 w-4 text-indigo-600 rounded"
                                  />
                                  <span className="text-sm text-gray-900">{process.name}</span>
                                </label>
                              );
                            })}
                          </div>
                          {selectedProcessDetails.length === 0 && (
                            <p className="text-sm text-gray-500 italic">
                              No processes selected in pipeline. Select processes from tabs above.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Summary Footer */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center space-x-4">
                    <span className="text-gray-600">
                      <span className="font-medium text-gray-900">{fileStats.mapped}</span> of{' '}
                      <span className="font-medium text-gray-900">{fileStats.total}</span> files mapped
                    </span>
                    {fileStats.unmapped > 0 && (
                      <span className="text-yellow-700 font-medium">
                        ⚠️ {fileStats.unmapped} file{fileStats.unmapped !== 1 ? 's' : ''} unmapped
                      </span>
                    )}
                  </div>
                  <div className="text-gray-500">
                    Mapping files to {selectedProcessArray.length} process{selectedProcessArray.length !== 1 ? 'es' : ''}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
