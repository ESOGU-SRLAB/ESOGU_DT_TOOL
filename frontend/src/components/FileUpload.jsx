import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { clsx } from 'clsx';

const FILE_TYPES = [
  'Requirement Document',
  'Source Code',
  'Project AST',
  'UML',
];

export default function FileUpload({ 
  onFileUpload,
  managedFiles = [],
  onFileDelete,
  processes = []
}) {
  const [uploadedFiles, setUploadedFiles] = useState([]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      const filesWithTempId = acceptedFiles.map(file => ({
        id: Date.now() + Math.random(),
        file: file,
        name: file.name,
        type: '', // Henüz seçilmedi
        size: file.size
      }));
      setUploadedFiles(prev => [...prev, ...filesWithTempId]);
    },
    multiple: true
  });

  const handleFileTypeChange = (fileId, fileType) => {
    setUploadedFiles(prev => 
      prev.map(file => 
        file.id === fileId ? { ...file, type: fileType } : file
      )
    );
  };

  const handleConfirmUpload = (fileId) => {
    const file = uploadedFiles.find(f => f.id === fileId);
    if (file && file.type) {
      onFileUpload([file.file], file.type);
      setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
    } else {
      alert('Please select a file type before confirming upload');
    }
  };

  const handleRemoveFile = (fileId) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 mb-4">File Upload</h3>
        
        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={clsx(
            'border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer',
            isDragActive ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-gray-400'
          )}
        >
          <input {...getInputProps()} />
          <p className="text-sm text-gray-600">
            {isDragActive 
              ? 'Drop the files here...' 
              : 'Drag and drop files here, or click to select files'
            }
          </p>
        </div>
      </div>

      {/* Pending Files - Tip seçimi için */}
      {uploadedFiles.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Select File Types</h3>
          <div className="space-y-4">
            {uploadedFiles.map((file) => (
              <div key={file.id} className="p-4 rounded-lg border border-yellow-200 bg-yellow-50">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="font-medium">{file.name}</span>
                    <span className="ml-2 text-sm text-gray-500">
                      ({(file.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  <button
                    onClick={() => handleRemoveFile(file.id)}
                    className="text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                </div>
                <div className="flex items-center gap-4">
                  <select
                    value={file.type}
                    onChange={(e) => handleFileTypeChange(file.id, e.target.value)}
                    className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  >
                    <option value="">Choose a file type...</option>
                    {FILE_TYPES.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleConfirmUpload(file.id)}
                    disabled={!file.type}
                    className={clsx(
                      'px-4 py-2 rounded-md text-sm font-medium',
                      file.type 
                        ? 'bg-indigo-600 text-white hover:bg-indigo-700' 
                        : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    )}
                  >
                    Confirm Upload
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Uploaded Files - Onaylanmış dosyalar */}
      {managedFiles.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Uploaded Files</h3>
          <p className="text-sm text-gray-600 mb-4">
            ℹ️ Go to <strong>Pipeline</strong> tab to map files to processes
          </p>
          <div className="space-y-3">
            {managedFiles.map((file) => (
              <div key={file.id} className="p-4 rounded-lg border border-gray-200 bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-gray-900">{file.name}</span>
                      <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">
                        {file.type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      {file.size ? `${(file.size / 1024).toFixed(1)} KB` : 'Unknown size'}
                    </p>
                  </div>
                  <button
                    onClick={() => onFileDelete(file.id)}
                    className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
