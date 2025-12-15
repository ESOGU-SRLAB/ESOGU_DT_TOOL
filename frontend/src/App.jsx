import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import TabPanel from './components/TabPanel';
import { processes } from './data/processes';
import { processService } from './services/processService';
import { Provider } from 'react-redux';
import { store } from './store';
import { useDispatch, useSelector } from 'react-redux';
import { runCodeReview } from './store/slices/codeReviewSlice';
import { runRequirementAnalysis } from './store/slices/requirementAnalysisSlice';
import axios from 'axios';
import TestScenarioGenerationForm from "./components/processes/TestScenarioGenerationForm";
import TestCaseOptimization from "./components/processes/TestCaseOptimization";
import TestCodeGeneration from "./components/processes/TestCodeGeneration";
import { v4 as uuidv4 } from 'uuid';
import { runTestPlanning } from './store/slices/testPlanningSlice';
import { runEnvironmentSetup } from './store/slices/environmentSetupSlice';

// Create a separate component for the app contents
function AppContents() {
	const dispatch = useDispatch();
	const { status, reviews, error } = useSelector(state => state.codeReview);
	const apiKeys = useSelector(state => state.apiKey.apiKeys);  // API keys'i al

	// Session ID yönetimi - HER YENİLEMEDE YENİ OLUŞTUR
	const [sessionId, setSessionId] = useState(() => {
		const sid = uuidv4();
		localStorage.setItem('session_id', sid);
		return sid;
	});

	// Combined states from both App.jsx files
	const [selectedProcesses, setSelectedProcesses] = useState(new Set());
	const [processOrigins, setProcessOrigins] = useState({}); // { processId: 'manual' | 'auto' }
	const [processFiles, setProcessFiles] = useState({});
	const [aiModels, setAIModels] = useState({});  // New state for AI models
	const [environmentNames, setEnvironmentNames] = useState({});  // New state for environment names
	const [processPrompts, setProcessPrompts] = useState({});
	const [output, setOutput] = useState(null);
	const [pipelineStatus, setPipelineStatus] = useState({});
	const [activeTab, setActiveTab] = useState('pipeline');
	const [validationError, setValidationError] = useState(null);
	const [isPipelineEnabled, setIsPipelineEnabled] = useState(true);
	
	// Centralized file management states from first App.jsx
	const [managedFiles, setManagedFiles] = useState([]);
	const [fileProcessMappings, setFileProcessMappings] = useState({});
	const [selectedFileIds, setSelectedFileIds] = useState(new Set());

	// Output state'ini bir obje olarak tutacağız
	const [outputs, setOutputs] = useState({});

	const [generatedPrompt, setGeneratedPrompt] = useState("");
	// Çıktı formatlarını takip etmek için state ekliyoruz
	const [outputFormats, setOutputFormats] = useState({});

	// Combined file upload function that supports both direct and centralized file management
	const handleFileUpload = async (processIdOrFiles, fileTypeOrInfo) => {
		console.log('[App] File upload triggered');
		
		if (Array.isArray(processIdOrFiles)) {
			try {
				const files = processIdOrFiles;
				const fileType = fileTypeOrInfo;
				console.log(`[App] Centralized file upload with type: ${fileType}`);
				
				// Read file contents asynchronously
				const newFiles = await Promise.all(Array.from(files).map(async (file) => {
					const content = await readFileContent(file);
					console.log(`[App] File content read for ${file.name}:`, {
						name: file.name,
						size: file.size,
						contentLength: content.length,
						contentPreview: content.substring(0, 100) + '...'
					});
					return {
						id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
						name: file.name,
						type: fileType || file.type,
						size: file.size,
						file: file, // Orijinal File nesnesini sakla
						content: content, // Dosya içeriğini ekle
						uploadDate: new Date().toISOString()
					};
				}));
	
				setManagedFiles(prev => [...prev, ...newFiles]);
			} catch (error) {
				console.error('File upload error:', error);
				setValidationError('An error occurred while uploading the file');
			}
		} else {
			const processId = processIdOrFiles;
			const fileInfo = fileTypeOrInfo;
			console.log(`[App] Direct file upload for process ${processId}: ${fileInfo.file.name} (type: ${fileInfo.type})`);
			
			setProcessFiles(prev => ({
				...prev,
				[processId]: [...(prev[processId] || []), fileInfo]
			}));
		}
	};

	// Helper function to read file content
	const readFileContent = (file) => {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = (event) => {
				resolve(event.target.result);
			};
			reader.onerror = (error) => {
				console.error('File reading error:', error);
				reject(error);
			};
			reader.readAsText(file);
		});
	};

	const handlePromptUpdate = (processId, newPrompt) => {
		console.log(`[App] Prompt updated for process ${processId}:`, newPrompt);
		
		// Ensure consistent structure
		const updatedPrompt = typeof newPrompt === 'object' ? newPrompt : { content: newPrompt };
		
		setProcessPrompts(prev => ({
			...prev,
			[processId]: updatedPrompt
		}));
	};

	const handleAIModelUpdate = (processId, model) => {
		console.log(`[App] AI Model updated for process ${processId}:`, model);
		setAIModels(prev => ({
			...prev,
			[processId]: model
		}));
	};

	const handleOutputFormatUpdate = (processId, format) => {
		console.log(`[App] Output format updated for process ${processId}:`, format);
		setOutputFormats(prev => ({
			...prev,
			[processId]: format
		}));
	};

	const handleEnvironmentNameUpdate = (processId, environmentName) => {
		console.log(`[App] Environment name updated for process ${processId}:`, environmentName);
		setEnvironmentNames(prev => ({
			...prev,
			[processId]: environmentName
		}));
	};

	// Complex process selection function from second App.jsx with automatic selection features
	const handleProcessSelect = (processId) => {
		console.log(`[App] Process ${processId} selection triggered`);
		setSelectedProcesses(prevSelected => {
			const newSet = new Set(prevSelected);
			const newOrigins = { ...processOrigins };
			const wasSelected = newSet.has(processId);

			// Toggle selection
			if (wasSelected) {
				newSet.delete(processId);
				delete newOrigins[processId];
				console.log(`[App] Removed ${processId} manually`);
			} else {
				newSet.add(processId);
				newOrigins[processId] = 'manual';
				console.log(`[App] Added ${processId} manually`);
			}

			// Pipeline etkin değilse sadece seçimi güncelle
			if (!isPipelineEnabled) {
				setProcessOrigins(newOrigins);
				return newSet;
			}

			// Process indeksleri
			const testPlanningIndex = processes.findIndex(p => p.id === 'test-planning');
			const envSetupIndex = processes.findIndex(p => p.id === 'environment-setup');
			
			// Mevcut süreçlerin durumları
			const isTestPlanningSelected = newSet.has('test-planning');
			const isEnvSetupSelected = newSet.has('environment-setup');
			const isTestPlanningManual = isTestPlanningSelected && newOrigins['test-planning'] === 'manual';
			const isEnvSetupManual = isEnvSetupSelected && newOrigins['environment-setup'] === 'manual';

			// Tüm süreçlerin indeksleriyle birlikte listesi
			const allProcesses = Array.from(newSet).map(id => ({
				id,
				index: processes.findIndex(p => p.id === id)
			}));

			// Test Planning ve Environment Setup dışındaki süreçler
			const otherProcesses = allProcesses.filter(
				item => item.id !== 'test-planning' && item.id !== 'environment-setup'
			);

			// Sadece bir süreç varsa ve bu requirement-analysis veya test-scenario-generation ise
			const hasOnlyRequirementAnalysis = otherProcesses.length === 1 && 
				otherProcesses[0].id === 'requirement-analysis';
			
			const hasOnlyTestScenarioGeneration = otherProcesses.length === 1 && 
				otherProcesses[0].id === 'test-scenario-generation';

			console.log(`[App] Has only requirement-analysis: ${hasOnlyRequirementAnalysis}`);
			console.log(`[App] Has only test-scenario-generation: ${hasOnlyTestScenarioGeneration}`);

			// Ardışık süreçleri kontrol et (herhangi iki süreç arasında)
			let hasConsecutive = false;
			
			// Tüm süreç çiftlerini kontrol et
			for (let i = 0; i < otherProcesses.length; i++) {
				for (let j = i + 1; j < otherProcesses.length; j++) {
					const indexA = otherProcesses[i].index;
					const indexB = otherProcesses[j].index;
					
					// Eğer herhangi iki süreç ardışıksa
					if (Math.abs(indexA - indexB) === 1) {
						hasConsecutive = true;
						console.log(`[App] Found consecutive pair: ${otherProcesses[i].id} (${indexA}) and ${otherProcesses[j].id} (${indexB})`);
						break;
					}
				}
				if (hasConsecutive) break;
			}

			// Requirement-analysis veya test-planning seçildiğinde
			const hasRequirementAnalysis = otherProcesses.some(p => p.id === 'requirement-analysis');
			const isRequirementAnalysisAndTestPlanning = hasRequirementAnalysis && isTestPlanningSelected;
			
			// Environment-setup veya test-scenario-generation seçildiğinde
			const hasTestScenarioGeneration = otherProcesses.some(p => p.id === 'test-scenario-generation');
			const isEnvSetupAndTestScenarioGeneration = hasTestScenarioGeneration && isEnvSetupSelected;
			
			console.log(`[App] Has requirement-analysis: ${hasRequirementAnalysis}`);
			console.log(`[App] Is requirement-analysis and test-planning: ${isRequirementAnalysisAndTestPlanning}`);
			console.log(`[App] Has test-scenario-generation: ${hasTestScenarioGeneration}`);
			console.log(`[App] Is environment-setup and test-scenario-generation: ${isEnvSetupAndTestScenarioGeneration}`);
			
			// Requirement-analysis VE test-planning seçili ise, sadece environment-setup eklensin
			if (isRequirementAnalysisAndTestPlanning && !isEnvSetupManual && !isEnvSetupSelected) {
				newSet.add('environment-setup');
				newOrigins['environment-setup'] = 'auto';
				console.log('[App] Added only environment-setup as auto (due to requirement-analysis AND test-planning)');
			}
			// Environment-setup VE test-scenario-generation seçili ise, sadece test-planning eklensin
			else if (isEnvSetupAndTestScenarioGeneration && !isTestPlanningManual && !isTestPlanningSelected) {
				newSet.add('test-planning');
				newOrigins['test-planning'] = 'auto';
				console.log('[App] Added only test-planning as auto (due to environment-setup AND test-scenario-generation)');
			}
			// Herhangi başka iki süreç arasında ardışıklık varsa
			else if (hasConsecutive) {
				if (!isTestPlanningManual && !isTestPlanningSelected) {
					newSet.add('test-planning');
					newOrigins['test-planning'] = 'auto';
					console.log('[App] Added test-planning as auto (due to consecutive processes)');
				}
				if (!isEnvSetupManual && !isEnvSetupSelected) {
					newSet.add('environment-setup');
					newOrigins['environment-setup'] = 'auto';
					console.log('[App] Added environment-setup as auto (due to consecutive processes)');
				}
			}
			// Hiçbir ardışık süreç yoksa VE özel senaryolardan hiçbiri yoksa
			// otomatik eklenmiş süreçleri kaldır
			if (!hasConsecutive && 
					!isRequirementAnalysisAndTestPlanning &&
					!isEnvSetupAndTestScenarioGeneration) {
				if (newOrigins['test-planning'] === 'auto') {
					newSet.delete('test-planning');
					delete newOrigins['test-planning'];
					console.log('[App] Removed auto test-planning - no consecutive processes');
				}
				if (newOrigins['environment-setup'] === 'auto') {
					newSet.delete('environment-setup');
					delete newOrigins['environment-setup'];
					console.log('[App] Removed auto environment-setup - no consecutive processes');
				}
			}

			console.log(`[App] Final selectedProcesses: ${Array.from(newSet)}`);
			console.log(`[App] Final processOrigins: ${JSON.stringify(newOrigins)}`);
			setProcessOrigins(newOrigins);
			return newSet;
		});
	};

	const validatePipeline = () => {
		console.log('[App] Validating pipeline');
		const missingInputs = [];
		
		selectedProcesses.forEach(processId => {
			const process = processes.find(p => p.id === processId);
			const files = processFiles[processId] || [];
			
			const missingRequiredInputs = process.inputs.filter(input => {
				return !files.some(file => file.type === input);
			});
			
			if (missingRequiredInputs.length > 0) {
				missingInputs.push({
					process: process.name,
					inputs: missingRequiredInputs
				});
			}
		});
		
		console.log(`[App] Validation result: ${missingInputs.length > 0 ? JSON.stringify(missingInputs) : 'Valid'}`);
		return missingInputs;
	};

	// File management functions from first App.jsx
	const handleFileDelete = (fileId) => {
		console.log(`[App] Deleting file: ${fileId}`);
		setManagedFiles(prev => prev.filter(f => f.id !== fileId));
		setFileProcessMappings(prev => {
			const newMappings = { ...prev };
			delete newMappings[fileId];
			return newMappings;
		});
	};

	const handleFileProcessMapping = (fileId, processes) => {
		console.log(`[App] Mapping file ${fileId} to processes: ${processes}`);
		setFileProcessMappings(prev => ({
			...prev,
			[fileId]: processes
		}));
		
		// Automatically update process files
		processes.forEach(processId => {
			const fileInfo = managedFiles.find(f => f.id === fileId);
			if (fileInfo) {
				setProcessFiles(prev => ({
					...prev,
					[processId]: [...(prev[processId] || []), fileInfo]
				}));
			}
		});
	};

	// Enhanced process run function that combines both implementations
	const handleProcessRun = async (processId, filesArg) => {
		console.log(`[App] Starting process with processId: '${processId}'`);
		
		try {
			setPipelineStatus(prev => ({
				...prev,
				[processId]: 'running'
			}));
			console.log(`[App] Pipeline status set to 'running' for ${processId}`);
			
			// Determine files to use - support both direct file passing and centralized file management
			let files = filesArg;
			if (!files) {
				const relevantFiles = managedFiles.filter(file => 
					fileProcessMappings[file.id]?.includes(processId)
				);
				
				if (relevantFiles.length > 0) {
					files = relevantFiles;
					console.log(`[App] Using ${relevantFiles.length} files from centralized management`);
				} else {
					files = processFiles[processId] || [];
					console.log(`[App] Using ${files.length} files from process-specific storage`);
				}
			}
			
			// --- CODE REVIEW KONTROLÜ ---
			if (
				(processId === 'requirement-analysis' || processId === 'test-planning') &&
				files.length > 0
			) {
				const hasRequirementDoc = files.some(file => file.type === 'Requirement Document');
				const hasCodeOrUML = files.some(file => file.type === 'Source Code' || file.type === 'UML');
				if (!hasRequirementDoc || !hasCodeOrUML) {
					window.alert('Bu süreç için hem Requirement Document hem de Source Code veya UML dosyası yüklemelisiniz.');
					setPipelineStatus(prev => ({ ...prev, [processId]: 'idle' }));
					return;
				}
			}
			if (processId === 'code-review' && files.length > 0) {
				const allRequirementDocs = files.every(file => file.type === 'Requirement Document');
				if (allRequirementDocs) {
					window.alert('Code review sadece Requirement Document ile çalıştırılamaz. Lütfen kod dosyası da ekleyin.');
					setPipelineStatus(prev => ({ ...prev, [processId]: 'idle' }));
					return;
				}
			}
			// --- KONTROL SONU ---
			
			console.log(`[App] Processing with ${files.length} files`);
			
			// Windows pop-up ile kullanılan dosyaları göster (Test Case Optimization hariç)
			if (processId !== 'test-case-optimization') {
				if (files.length > 0) {
					const fileNames = files.map(file => file.name || file.file?.name || 'Unnamed File').join('\n');
					window.alert(`Processing ${processId} with the following files:\n\n${fileNames}`);
				} else {
					window.alert(`Processing ${processId} with no files selected.`);
				}
			}
	
			let result;
			if (processId === 'code-review') {
				console.log('[App] Running code review with ai model', aiModels);
				const selectedModel = aiModels[processId] || 'default';
				console.log(`[App] Using AI model for code review: ${selectedModel}`);
				// Custom prompt'u al
				const customPrompt = processPrompts[processId]?.prompt_text || processPrompts[processId]?.content || null;
				// API key'i al - Gemini modelleri için google key'ini kullan
				const apiKey = apiKeys?.google || null;
				console.log(`[App] Using API key for code review: ${apiKey ? 'Yes' : 'No'}`);
				await dispatch(runCodeReview({files, model: selectedModel, customPrompt, sessionId, apiKey})).unwrap();
				if (error) {
					throw new Error(error);
				}
				setOutputs(prev => ({
					...prev,
					[processId]: {
						content: reviews.join('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'),
						status: status === 'succeeded' ? 'completed' : 'error',
						processType: 'Code Review',
						processId,
						timestamp: new Date().toISOString(),
						model: selectedModel
					}
				}));
			} else if (processId === 'test-planning') {
				console.log('[App] Running test planning');
				const selectedModel = aiModels[processId] || 'default';
				const customPrompt = processPrompts[processId]?.prompt_text || processPrompts[processId]?.content || null;
				
				// API key'i al ve geçir
				const googleApiKey = apiKeys?.google || null;
				console.log('[App] Google API key for test planning:', googleApiKey ? 'Available' : 'Not found');
				await dispatch(runTestPlanning({files, model: selectedModel, customPrompt, sessionId, apiKey: googleApiKey})).unwrap();
				// OutputPanel zaten plans dizisini redux'tan okuyacak!
			} else if (processId === 'requirement-analysis') {
				console.log('[App] Running requirement analysis');
				try {
					const selectedModel = aiModels[processId] || 'llama3.2:3b';
					const fileNames = files.map(file => file.name || file.file?.name || 'Unnamed File').join('\n');
					window.alert(`Requirement Analysis şu model ile çalıştırılıyor: ${selectedModel}\n\nKullanılan dosyalar:\n${fileNames}`);
					const customPrompt = processPrompts[processId]?.prompt_text || processPrompts[processId]?.content || null;
					
					// API key'i al ve geçir (code review ile aynı field kullan)
					const googleApiKey = apiKeys?.google || null;
					console.log('[App] Google API key for requirement analysis:', googleApiKey ? 'Available' : 'Not found');
					await dispatch(runRequirementAnalysis({files, model: selectedModel, customPrompt, sessionId, apiKey: googleApiKey})).unwrap();
					console.log('[App] Requirement analysis completed, redux state güncellendi');
				} catch (error) {
					console.error('[App] Error in requirement analysis:', error);
					setOutputs(prev => ({
						...prev,
						[processId]: {
							content: `Hata: ${error.message}`,
							status: 'error',
							processType: 'Requirement Analysis',
							processId: processId,
							timestamp: new Date().toISOString(),
							model: aiModels[processId] || 'llama3.2:3b'
						}
					}));
				}
			} else if (processId === 'environment-setup') {
				console.log('[App] Running environment setup');
				const selectedModel = aiModels[processId] || 'default';
				const customPrompt = processPrompts[processId]?.prompt_text || processPrompts[processId]?.content || null;
				const environmentName = environmentNames[processId] || 'Unnamed Environment';
				
				// API key'i al ve geçir
				const googleApiKey = apiKeys?.google || null;
				console.log('[App] Google API key for environment setup:', googleApiKey ? 'Available' : 'Not found');
				console.log('[App] Environment name for environment setup:', environmentName);
				await dispatch(runEnvironmentSetup({files, model: selectedModel, customPrompt, sessionId, environmentName, apiKey: googleApiKey})).unwrap();
				// OutputPanel zaten setups dizisini redux'tan okuyacak!
			} else if (processId === 'test-code-generation') {
				console.log('[App] Running test code generation');
				
				// Call the component's execute function if available
				if (window.testCodeGenerationExecute && typeof window.testCodeGenerationExecute === 'function') {
					console.log('[App] Calling TestCodeGeneration component execute function');
					await window.testCodeGenerationExecute();
				} else {
					console.warn('[App] TestCodeGeneration execute function not available');
					throw new Error('Test Code Generation component not ready. Please ensure all required fields are filled.');
				}
			} else if (processId === 'test-scenario-generation') {
			console.log('[App] Running test scenario generation');
			
			// Debug the current state
			console.log('[App] Current processPrompts:', processPrompts);
			console.log('[App] ProcessPrompts for test-scenario-generation:', processPrompts[processId]);
			
			// Final prompt'u al
			const finalPrompt = processPrompts[processId]?.finalPrompt || processPrompts[processId]?.generatedCustomPrompt || '';
			
			console.log('[App] Final prompt check:', {
				hasProcessPrompts: !!processPrompts[processId],
				hasFinalPrompt: !!processPrompts[processId]?.finalPrompt,
				hasGeneratedCustomPrompt: !!processPrompts[processId]?.generatedCustomPrompt,
				finalPromptLength: finalPrompt.length
			});
			
			if (!finalPrompt) {
				const errorMsg = 'Please generate a prompt first before running test scenario generation';
				console.error('[App] Error:', errorMsg);
				window.alert(errorMsg);
				throw new Error(errorMsg);
			}
			
			const config = {
				files: files.map(f => f.file || f), // File objects
				model: processPrompts[processId]?.model || 'llama3.2:3b',
				finalPrompt: finalPrompt,
				testType: processPrompts[processId]?.testType || 'Functional Testing',
				testCategory: processPrompts[processId]?.testCategory || 'Functional',
				sessionId: sessionId, // Use global sessionId instead of generating new one
				apiKey: apiKey  // API key eklendi
			};
			
			console.log('[App] Test scenario generation config:', {
				...config,
				files: `[${config.files.length} files]`,
				finalPrompt: `[${config.finalPrompt.length} characters]`
			});
	
			const result = await processService.runTestScenarioGeneration(config);
			
			console.log('[App] Test scenario generation result:', result);
			
			// Format the output for display
			let formattedOutput = '';
			if (result.status === 'success' && result.test_scenarios) {
				const scenarios = result.test_scenarios;
				
				// Create summary
				formattedOutput += `# Test Scenario Generation Results\n\n`;
				formattedOutput += `**Status:** ✅ Success\n`;
				formattedOutput += `**Model Used:** ${result.metadata?.model_used || config.model}\n`;
				formattedOutput += `**Files Processed:** ${result.metadata?.files_processed || config.files.length}\n`;
				formattedOutput += `**Total Scenarios:** ${scenarios.Summary?.TotalScenarios || scenarios.TestScenarios?.length || 0}\n\n`;
				
				// Add categories summary
				if (scenarios.Summary?.Categories) {
					formattedOutput += `## Categories\n`;
					Object.entries(scenarios.Summary.Categories).forEach(([category, count]) => {
						formattedOutput += `- **${category}:** ${count} scenarios\n`;
					});
					formattedOutput += '\n';
				}
				
				// Add coverage info
				if (scenarios.Summary?.Coverage) {
					formattedOutput += `## Coverage\n${scenarios.Summary.Coverage}\n\n`;
				}
				
				// Add scenarios
				if (scenarios.TestScenarios && scenarios.TestScenarios.length > 0) {
					formattedOutput += `## Test Scenarios\n\n`;
					scenarios.TestScenarios.forEach((scenario, index) => {
						formattedOutput += `### ${index + 1}. ${scenario.Title} (${scenario.ScenarioID})\n\n`;
						formattedOutput += `**Description:** ${scenario.Description}\n\n`;
						if (scenario.Objective) formattedOutput += `**Objective:** ${scenario.Objective}\n\n`;
						if (scenario.Category) formattedOutput += `**Category:** ${scenario.Category}\n\n`;
						if (scenario.Priority) formattedOutput += `**Priority:** ${scenario.Priority}\n\n`;
						
						if (scenario.Prerequisites && scenario.Prerequisites.length > 0) {
							formattedOutput += `**Prerequisites:**\n`;
							scenario.Prerequisites.forEach(prereq => {
								formattedOutput += `- ${prereq}\n`;
							});
							formattedOutput += '\n';
						}
						
						if (scenario.TestSteps && scenario.TestSteps.length > 0) {
							formattedOutput += `**Test Steps:**\n`;
							scenario.TestSteps.forEach((step, i) => {
								formattedOutput += `${i + 1}. ${step}\n`;
							});
							formattedOutput += '\n';
						}
						
						if (scenario.ExpectedResults) formattedOutput += `**Expected Results:** ${scenario.ExpectedResults}\n\n`;
						if (scenario.TestData) formattedOutput += `**Test Data:** ${scenario.TestData}\n\n`;
						if (scenario.Comments) formattedOutput += `**Comments:** ${scenario.Comments}\n\n`;
						
						formattedOutput += '---\n\n';
					});
				}
				
				// Add JSON download info
				formattedOutput += `## JSON Output\n\n`;
				formattedOutput += `\`\`\`json\n${JSON.stringify(scenarios, null, 2)}\n\`\`\`\n`;
				
			} else {
				formattedOutput = `# Test Scenario Generation Failed\n\n`;
				formattedOutput += `**Status:** ❌ Error\n`;
				formattedOutput += `**Message:** ${result.message || 'Unknown error'}\n\n`;
				formattedOutput += `Please check your configuration and try again.`;
			}
			
			setOutputs(prev => ({
				...prev,
				[processId]: {
					content: formattedOutput,
					status: result.status === 'success' ? 'completed' : 'error',
					processType: 'Test Scenario Generation',
					processId: processId,
					timestamp: new Date().toISOString(),
					rawData: result // Store raw data for potential future use
				}
			}));
	
			console.log('[App] Test scenario generation completed');
			} else {
				setOutputs(prev => ({
					...prev,
					[processId]: {
						content: `# ${processId} Process Output\n\nSuccessfully completed the ${processId} process.\n\n## Details\n- Process ID: ${processId}\n- Timestamp: ${new Date().toISOString()}\n- Files processed: ${files.length}\n\n## Summary\nAll operations completed successfully with no errors.`,
						status: 'completed',
						// Fix the processType generation with type checking
						processType: typeof processId === 'string' 
							? processId.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
							: 'Unknown Process',
						processId: processId,
						timestamp: new Date().toISOString()
					}
				}));
				console.log(`[App] Process ${processId} completed, output set`);
			}
	
			setPipelineStatus(prev => ({
				...prev,
				[processId]: 'completed'
			}));
			console.log(`[App] Pipeline status set to 'completed' for ${processId}`);
		} catch (error) {
			console.error(`[App] Process ${processId} failed: ${error.message}`);
			setPipelineStatus(prev => ({
				...prev,
				[processId]: 'error'
			}));
			setOutputs(prev => ({
				...prev,
				[processId]: {
					content: `Error: ${error.message}`,
					status: 'error',
					processType: processes.find(p => p.id === processId)?.name || 'Unknown Process',
					processId: processId,
					timestamp: new Date().toISOString()
				}
			}));
		}
	};

	// Test senaryoları formatlamak için yardımcı fonksiyon
	const formatTestScenarios = (scenarios) => {
		return `# Generated Test Scenarios\n\n${scenarios.map(scenario => `
	## ${scenario.title}
	${scenario.description}
	
	### Prerequisites
	${scenario.prerequisites.map(prereq => `- ${prereq}`).join('\n')}
	
	### Steps
	${scenario.steps.map((step, index) => `${index + 1}. ${step}`).join('\n')}
	`).join('\n')}`;
	};

	// Pipeline başlatma fonksiyonu
	const handleStartPipeline = async () => {
		console.log('[App] Starting pipeline');
		
		// Seçilen süreçleri sırayla çalıştır
		const selectedProcessIds = Array.from(selectedProcesses);
		
		// Önce tüm süreç durumlarını "pending" olarak ayarla
		setPipelineStatus(prev => {
			const newStatus = { ...prev };
			selectedProcessIds.forEach(id => {
				newStatus[id] = 'pending';
			});
			return newStatus;
		});
		
		// Süreçleri sırayla çalıştır
		for (const processId of selectedProcessIds) {
			console.log(`[App] Running pipeline step: ${processId}`);
			
			try {
				// Mevcut sürecin durumunu "running" olarak güncelle
				setPipelineStatus(prev => ({
					...prev,
					[processId]: 'running'
				}));
				
				// Süreç için dosyaları belirle
				const relevantFiles = managedFiles.filter(file => 
					fileProcessMappings[file.id]?.includes(processId)
				);
				
				// Süreç çalıştırma fonksiyonunu çağır ve sonuçları bekle
				await handleProcessRun(processId, relevantFiles);
				
				// Kısa bir bekleme süresi ekle
				await new Promise(resolve => setTimeout(resolve, 500));
				
			} catch (error) {
				console.error(`[App] Pipeline step failed at ${processId}: ${error.message}`);
				
				// Hata durumunda süreci durdur
				setPipelineStatus(prev => ({
					...prev,
					[processId]: 'error'
				}));
				
				// Hata mesajını çıktı olarak göster
				setOutputs(prev => ({
					...prev,
					pipeline: {
						content: `Pipeline Error at ${processId}: ${error.message}`,
						status: 'error',
						processType: 'Pipeline',
						processId: 'pipeline',
						timestamp: new Date().toISOString()
					}
				}));
				
				break;
			}
		}
		
		console.log('[App] Pipeline execution completed');
	};
	
	// Ana çalıştırma fonksiyonu - pipeline veya tek süreç
	const handleRun = (processId, config) => {
		if (!processId) {
			// processId yoksa pipeline çalıştır
			handleStartPipeline();
		} else if (config) {
			// Config verilmişse (form'dan gelen çağrılar için)
			handleRunProcessWithConfig(processId, config);
		} else {
			// processId varsa tek süreç çalıştır
			handleProcessRun(processId);
		}
	};

	// Handle run process with config (for forms that provide their own config)
	const handleRunProcessWithConfig = async (processId, config) => {
		try {
			console.log('[App] handleRunProcessWithConfig called with:', { processId, config });
			
			setPipelineStatus(prev => ({
				...prev,
				[processId]: 'running'
			}));

		if (processId === 'test-scenario-generation') {
			console.log('[App] Running test scenario generation with provided config');
			
			// Get Google API key from Redux
			const googleApiKey = apiKeys.google;
			console.log('[App] Google API Key:', googleApiKey ? 'SET' : 'NOT SET');
			
			// Add API key to config
			const configWithApiKey = {
				...config,
				apiKey: googleApiKey
			};				const result = await processService.runTestScenarioGeneration(configWithApiKey);
				console.log('[App] Test scenario generation result:', result);
				
				// Format the output for display - use the same detailed formatting as handleProcessRun
				let formattedOutput = '';
				if (result.status === 'success' && result.test_scenarios) {
					const scenarios = result.test_scenarios;
					
					// Create summary
					formattedOutput += `# Test Scenario Generation Results\n\n`;
					formattedOutput += `**Status:** ✅ Success\n`;
					formattedOutput += `**Model Used:** ${result.metadata?.model_used || config.model}\n`;
					formattedOutput += `**Files Processed:** ${result.metadata?.files_processed || config.files.length}\n`;
					formattedOutput += `**Total Scenarios:** ${scenarios.Summary?.TotalScenarios || scenarios.TestScenarios?.length || 0}\n\n`;
					
					// Add categories summary
					if (scenarios.Summary?.Categories) {
						formattedOutput += `## Categories\n`;
						Object.entries(scenarios.Summary.Categories).forEach(([category, count]) => {
							formattedOutput += `- **${category}:** ${count} scenarios\n`;
						});
						formattedOutput += '\n';
					}
					
					// Add coverage info
					if (scenarios.Summary?.Coverage) {
						formattedOutput += `## Coverage\n${scenarios.Summary.Coverage}\n\n`;
					}
					
					// Add scenarios
					if (scenarios.TestScenarios && scenarios.TestScenarios.length > 0) {
						formattedOutput += `## Test Scenarios\n\n`;
						scenarios.TestScenarios.forEach((scenario, index) => {
							formattedOutput += `### ${index + 1}. ${scenario.Title} (${scenario.ScenarioID})\n\n`;
							formattedOutput += `**Description:** ${scenario.Description}\n\n`;
							if (scenario.Objective) formattedOutput += `**Objective:** ${scenario.Objective}\n\n`;
							if (scenario.Category) formattedOutput += `**Category:** ${scenario.Category}\n\n`;
							if (scenario.Priority) formattedOutput += `**Priority:** ${scenario.Priority}\n\n`;
							
							if (scenario.Prerequisites && scenario.Prerequisites.length > 0) {
								formattedOutput += `**Prerequisites:**\n`;
								scenario.Prerequisites.forEach(prereq => {
									formattedOutput += `- ${prereq}\n`;
								});
								formattedOutput += '\n';
							}
							
							if (scenario.TestSteps && scenario.TestSteps.length > 0) {
								formattedOutput += `**Test Steps:**\n`;
								scenario.TestSteps.forEach((step, i) => {
									formattedOutput += `${i + 1}. ${step}\n`;
								});
								formattedOutput += '\n';
							}
							
							if (scenario.ExpectedResults) formattedOutput += `**Expected Results:** ${scenario.ExpectedResults}\n\n`;
							if (scenario.TestData) formattedOutput += `**Test Data:** ${scenario.TestData}\n\n`;
							if (scenario.Comments) formattedOutput += `**Comments:** ${scenario.Comments}\n\n`;
							
							formattedOutput += '---\n\n';
						});
					}
					
					// Add JSON download info
					formattedOutput += `## JSON Output\n\n`;
					formattedOutput += `\`\`\`json\n${JSON.stringify(scenarios, null, 2)}\n\`\`\`\n`;
					
				} else {
					formattedOutput = `# Test Scenario Generation Failed\n\n`;
					formattedOutput += `**Status:** ❌ Error\n`;
					formattedOutput += `**Message:** ${result.message || 'Unknown error'}\n\n`;
					formattedOutput += `Please check your configuration and try again.`;
				}
				
				setOutputs(prev => ({
					...prev,
					[processId]: {
						content: formattedOutput,
						status: result.status === 'success' ? 'completed' : 'error',
						processType: 'Test Scenario Generation',
						processId: processId,
						timestamp: new Date().toISOString(),
						rawData: result // Store raw data for potential future use
					}
				}));

				setPipelineStatus(prev => ({
					...prev,
					[processId]: result.status === 'success' ? 'completed' : 'error'
				}));

				console.log('[App] Test scenario generation completed');
			} else if (processId === 'test-case-generation') {
				console.log('[App] Running test case generation with provided config');
				
				// Test Case Generation için özel işlem
				// Config içindeki data'yı direkt olarak output'a set edelim
				const result = config.data;
				console.log('[App] Test case generation result:', result);
				
				// Output'u setOutputs ile set et (renderTestCaseContent kullanacak OutputPanel)
				setOutput({
					type: 'test-case-generation',
					data: result,
					sessionId: config.sessionId,
					processId: processId,
					timestamp: new Date().toISOString()
				});
				
				// Outputs state'ini de güncelle (backwards compatibility için)
				setOutputs(prev => ({
					...prev,
					[processId]: {
						type: 'test-case-generation',
						data: result,
						content: `Test Case Generation completed with ${result.summary?.successful_scenarios || 0} successful scenarios`,
						status: result.status === 'success' ? 'completed' : 'error',
						processType: 'Test Case Generation',
						processId: processId,
						timestamp: new Date().toISOString(),
						rawData: result
					}
				}));

				setPipelineStatus(prev => ({
					...prev,
					[processId]: result.status === 'success' ? 'completed' : 'error'
				}));

				console.log('[App] Test case generation completed and output set');
			} else if (processId === 'test-code-generation') {
				console.log('[App] Running test code generation with provided config');
				
				// Test Code Generation için özel işlem
				const result = config.data;
				console.log('[App] Test code generation result:', result);
				
				// Markdown formatında output oluştur
				let formattedOutput = '';
				if (result.status === 'success') {
					formattedOutput = `# Test Code Generation Results\n\n`;
					formattedOutput += `**Status:** ✅ Success\n`;
					formattedOutput += `**Environment Setup:** ${result.environment_setup_id}\n`;
					formattedOutput += `**Process Title:** ${result.process_title}\n`;
					formattedOutput += `**Generated Test Codes:** ${result.test_codes?.length || 0}\n\n`;
					
					if (result.test_codes && result.test_codes.length > 0) {
						formattedOutput += `## Generated Test Codes\n\n`;
						result.test_codes.forEach((testCode, index) => {
							formattedOutput += `### Test Code ${index + 1}\n`;
							formattedOutput += `**Test Case ID:** ${testCode.test_case_id}\n`;
							formattedOutput += `**Framework:** ${testCode.framework}\n`;
							formattedOutput += `**Language:** ${testCode.language}\n\n`;
							formattedOutput += `\`\`\`${testCode.language}\n${testCode.code}\n\`\`\`\n\n`;
						});
					}
				} else {
					formattedOutput = `# Test Code Generation Failed\n\n`;
					formattedOutput += `**Status:** ❌ Error\n`;
					formattedOutput += `**Message:** ${result.message || 'Unknown error'}\n\n`;
					formattedOutput += `Please check your configuration and try again.`;
				}
				
				// Output'u set et
				setOutput({
					type: 'test-code-generation',
					data: result,
					sessionId: config.sessionId,
					processId: processId,
					timestamp: new Date().toISOString()
				});
				
				// Outputs state'ini de güncelle
				setOutputs(prev => ({
					...prev,
					[processId]: {
						type: 'test-code-generation',
						data: result,
						content: formattedOutput,
						status: result.status === 'success' ? 'completed' : 'error',
						processType: 'Test Code Generation',
						processId: processId,
						timestamp: new Date().toISOString(),
						rawData: result
					}
				}));

				setPipelineStatus(prev => ({
					...prev,
					[processId]: result.status === 'success' ? 'completed' : 'error'
				}));

				console.log('[App] Test code generation completed and output set');
			} else {
				console.warn('[App] handleRunProcessWithConfig called for unsupported process:', processId);
			}

		} catch (error) {
			console.error('[App] Error in handleRunProcessWithConfig:', error);
			setPipelineStatus(prev => ({
				...prev,
				[processId]: 'error'
			}));

			setOutputs(prev => ({
				...prev,
				[processId]: {
					content: `# Error\n\nFailed to run ${processId}: ${error.message}`,
					status: 'error',
					processType: processId,
					processId: processId,
					timestamp: new Date().toISOString()
				}
			}));
			
			// Re-throw the error to prevent fallback retry
			throw error;
		}
	};

	const handleGeneratePrompt = async (processId, formData) => {
		try {
			console.log('[App] Generate prompt called with:', { processId, formData });
			
			if (processId === 'test-scenario-generation') {
				// Test scenario generation için özel işlem - sadece state güncellemesi yap
				console.log('[App] Test scenario generation prompt received from form');
				
				// finalPrompt'u öncelikle al, yoksa generatedCustomPrompt'u kullan
				const promptToUse = formData.finalPrompt || formData.generatedCustomPrompt;
				
				console.log('[App] handleGeneratePrompt debug:', {
					processId,
					hasFinalPrompt: !!formData.finalPrompt,
					hasGeneratedCustomPrompt: !!formData.generatedCustomPrompt,
					promptToUseLength: promptToUse?.length || 0,
					currentProcessPrompts: Object.keys(processPrompts)
				});
				
				if (promptToUse) {
					const promptData = {
						content: promptToUse,
						prompt_text: promptToUse,
						finalPrompt: promptToUse,  // Add this property for handleProcessRun to find
						generatedCustomPrompt: promptToUse,  // Also add this as fallback
						model: formData.model,  // Store the model
						testType: formData.testType,  // Store the test type
						testCategory: formData.testCategory  // Store the test category
					};
					
					setProcessPrompts(prev => {
						const updated = {
							...prev,
							[processId]: promptData
						};
						console.log('[App] processPrompts updated:', Object.keys(updated));
						return updated;
					});
					
					console.log('[App] Process prompt updated successfully with:', promptToUse.substring(0, 100) + '...');
					return { prompt: promptToUse };
				} else {
					console.warn('[App] No prompt received from form');
					// Boş prompt yerine varsayılan bir mesaj göster
					const defaultMessage = 'Please complete the form configuration to generate a prompt.';
					setProcessPrompts(prev => ({
						...prev,
						[processId]: {
							content: defaultMessage,
							prompt_text: defaultMessage
						}
					}));
					return { prompt: defaultMessage };
				}
			} else {
				// Diğer processler için standart API çağrısı
				const response = await fetch(`/api/test-scenario-generation/generate-prompt`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					body: JSON.stringify(formData),
				});
				
				if (!response.ok) {
					throw new Error('Failed to generate prompt');
				}
				
				const data = await response.json();
				
				if (data.status === 'success') {
					setProcessPrompts(prev => ({
						...prev,
						[processId]: data.prompt
					}));
					return data;
				}
			}
		} catch (error) {
			console.error('Error generating prompt:', error);
			throw error;
		}
	};

	const handleRunProcess = async () => {
		try {
			const response = await axios.post('/api/test-scenario-generation/run', {
				prompt: generatedPrompt,

			});
			// Process Result alanını güncelle
			setProcessResult(response.data.result);
		} catch (error) {
			console.error('Error running process:', error);
		}
	};
	
	// Handler for setting output directly (for modules that handle their own processing)
	const handleSetOutput = (processId, outputData) => {
		console.log('[App] Setting output for:', processId, outputData);
		setOutputs(prev => ({
			...prev,
			[processId]: outputData
		}));
		setPipelineStatus(prev => ({
			...prev,
			[processId]: (outputData && outputData.status) || 'completed'
		}));
	};

	return (
		<div className="min-h-screen flex flex-col">
			<Header />
			<div className="flex-1 flex flex-col overflow-hidden">
				{validationError && (
					<div className="bg-red-100 text-red-700 p-3 text-center">
						{validationError}
					</div>
				)}
				<TabPanel
					processes={processes}
					activeTab={activeTab}
					setActiveTab={setActiveTab}
					selectedProcesses={selectedProcesses}
					processOrigins={processOrigins}
					onProcessSelect={handleProcessSelect}
					processFiles={processFiles}
					onFileUpload={handleFileUpload}
					onAIModelUpdate={handleAIModelUpdate}
					onOutputFormatUpdate={handleOutputFormatUpdate}
					onEnvironmentNameUpdate={handleEnvironmentNameUpdate}
					aiModels={aiModels}
					environmentNames={environmentNames}
					outputFormats={outputFormats}
					processPrompts={processPrompts}
					onPromptUpdate={handlePromptUpdate}
					pipelineStatus={pipelineStatus}
					onRun={handleRun}
					onSetOutput={handleSetOutput}
					validationError={validationError}
					output={output}
					outputs={outputs}
					isPipelineEnabled={isPipelineEnabled}
					onTogglePipeline={setIsPipelineEnabled}
					managedFiles={managedFiles}
					fileProcessMappings={fileProcessMappings}
					sessionId={sessionId} // Pass global sessionId
					onFileProcessMapping={handleFileProcessMapping}
					onFileDelete={handleFileDelete}
					selectedFileIds={selectedFileIds}
					setSelectedFileIds={setSelectedFileIds}
					onGeneratePrompt={handleGeneratePrompt}
				/>
			</div>
		</div>
	);
}

// Main App component that provides Redux store
export default function App() {
	return (
		<Provider store={store}>
			<AppContents />
		</Provider>
	);
}