import axios from 'axios';

const API_BASE_URL = '/api/processes';

export const processService = {
  async runProcess(processType, files) {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      console.log(`İstek gönderiliyor: ${processType} süreci için`);
      const response = await axios.post(
        `${API_BASE_URL}/processes/${processType}/run`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      console.log(`İstek başarıyla gönderildi: ${processType} süreci`);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || `Failed to run ${processType}`);
    }
  },

  async runCodeReview(files, model = null, customPrompt = null, sessionId = null) {
    console.log('[ProcessService] Running code review with model:', model);
    
    const formData = new FormData();
    files.forEach(fileInfo => {
      const file = fileInfo.file || fileInfo;
      formData.append('files', file);
    });
    
    if (model) {
      formData.append('model', model);
    }
    if (customPrompt) {
      console.log('processService.js - custom_prompt gönderiliyor:', customPrompt);
      formData.append('custom_prompt', customPrompt);
    }
    if (sessionId) {
      formData.append('session_id', sessionId);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/code-review/run`, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      const data = await response.json();
      // Redux action payload formatına uygun dönüş
      return {
        reviews: data.reviews.map(review => `## Files Analyzed\n${review.files}\n\n## Review\n${review.review}`),
        metadata: {
          timestamp: new Date().toISOString(),
          fileCount: files.length
        }
      };
    } catch (error) {
      throw error;
    }
  },

  async runRequirementAnalysis(files, model = null, customPrompt = null, sessionId = null) {
    const formData = new FormData();
    files.forEach(file => {
      const actualFile = file.file || file;
      formData.append('files', actualFile);
    });
    // Dosya tiplerini ayrı bir array olarak ekle
    const types = files.map(fileInfo => fileInfo.type || '');
    types.forEach(type => formData.append('types', type));
    if (model) {
      formData.append('model', model);
    }
    if (customPrompt) {
      formData.append('custom_prompt', customPrompt);
    }
    if (sessionId) {
      formData.append('session_id', sessionId);
    }
  
    try {
      console.log("İstek gönderiliyor: Gereksinim analizi süreci için");
      const response = await axios.post(
        `${API_BASE_URL}/requirement_analysis/run`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      console.log("İstek başarıyla gönderildi: Gereksinim analizi süreci");
      return response.data;
    } catch (error) {
      console.error("Hata detayları:", error.response?.data);
      const errorMsg = error.response?.data?.detail || 'Requirement analysis failed';
      throw new Error(errorMsg);
    }
  },

  async generateCustomPrompt(promptGenerationData) {
    try {
      console.log('[ProcessService] Generating custom prompt with data:', promptGenerationData);
      
      const response = await fetch(`${API_BASE_URL}/test-scenario-generation/generate-prompt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(promptGenerationData)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[ProcessService] Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log('[ProcessService] Custom prompt generated successfully:', data);
      return data;
    } catch (error) {
      console.error('[ProcessService] Error generating custom prompt:', error);
      throw error;
    }
  },

  async getTestTypeDetails(testType) {
    try {
      console.log('Fetching test type details for:', testType);
      const response = await axios.get(
        `${API_BASE_URL}/test-scenario-generation/test-type/${encodeURIComponent(testType)}`,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      console.log('Received test type details:', response.data);
      
      // Backend'den gelen veriyi frontend formatına dönüştür
      const testScoringElements = response.data.test_scoring_elements_and_prompts || {};
      const testInstructionElements = response.data.test_instruction_elements_and_prompts || {};
      
      return {
        test_prompt: response.data.test_prompt || '',
        test_scoring_elements_and_prompts: testScoringElements,
        test_instruction_elements_and_prompts: testInstructionElements,
        // Eski format için uyumluluk
        scoring_elements: testScoringElements,
        instruction_elements: testInstructionElements
      };
    } catch (error) {
      console.error('Error fetching test type details:', error);
      if (error.response?.status === 404) {
        console.log('Test type not found in database, returning empty data');
        return {
          test_prompt: '',
          test_scoring_elements_and_prompts: {},
          test_instruction_elements_and_prompts: {},
          scoring_elements: {},
          instruction_elements: {}
        };
      }
      throw new Error(error.response?.data?.detail || 'Failed to fetch test type details');
    }
  },

  async runTestPlanning(files, model = null, customPrompt = null, sessionId = null) {
    const formData = new FormData();
    files.forEach(fileInfo => {
      const file = fileInfo.file || fileInfo;
      formData.append('files', file);
    });
    if (model) formData.append('model', model);
    if (customPrompt) formData.append('custom_prompt', customPrompt);
    if (sessionId) formData.append('session_id', sessionId);

    try {
      const response = await fetch('/api/processes/test-planning/run', {
        method: 'POST',
        body: formData,
        headers: { 'Accept': 'application/json' }
      });
      if (!response.ok) throw new Error(`Backend error: ${response.status}`);
      const data = await response.json();
      return {
        plans: data.plans.map(plan => `## Files Analyzed\n${plan.files}\n\n## Test Plan\n${plan.plan}`),
        metadata: {
          timestamp: new Date().toISOString(),
          fileCount: files.length
        }
      };
    } catch (error) {
      throw error;
    }
  },

  async runEnvironmentSetup(files, model = null, customPrompt = null, sessionId = null) {
    console.log("runEnvironmentSetup çağrıldı. Dosyalar ve tipleri:");
    files.forEach((fileInfo, idx) => {
      const file = fileInfo.file || fileInfo;
      const type = fileInfo.type || '';
      console.log(`  [${idx}] Dosya adı: ${file.name || file.file?.name}, Tip: \"${type}\"`);
    });

    const formData = new FormData();
    files.forEach(fileInfo => {
      const file = fileInfo.file || fileInfo;
      formData.append('files', file);
    });
    // Dosya tiplerini ayrı bir array olarak ekle
    const types = files.map(fileInfo => fileInfo.type || '');
    console.log("Gönderilecek types array'i:", types);
    types.forEach(type => formData.append('types', type));
    if (model) formData.append('model', model);
    if (customPrompt) formData.append('custom_prompt', customPrompt);
    if (sessionId) formData.append('session_id', sessionId);

    try {
      const response = await fetch('/api/processes/environment-setup/run', {
        method: 'POST',
        body: formData,
        headers: { 'Accept': 'application/json' }
      });
      if (!response.ok) throw new Error(`Backend error: ${response.status}`);
      const data = await response.json();
      return {
        setups: data.setups.map(setup => `## Files Analyzed\n${setup.files}\n\n## Environment Setup\n${setup.setup}`),
        metadata: {
          timestamp: new Date().toISOString(),
          fileCount: files.length
        }
      };
    } catch (error) {
      throw error;
    }
  },

  // Test Scenario Generation için çalıştırma fonksiyonu
  async runTestScenarioGeneration(data) {
    console.log('[ProcessService] Running test scenario generation with data:', data);
    
    const formData = new FormData();
    
    // Add files if provided
    if (data.files && Array.isArray(data.files)) {
      data.files.forEach((file, index) => {
        console.log(`[ProcessService] Adding file ${index}:`, file.name || 'unnamed');
        formData.append('files', file);
      });
    }
      // Add other parameters
    if (data.model) formData.append('model', data.model);
    if (data.finalPrompt) formData.append('final_prompt', data.finalPrompt);
    if (data.testCategory) formData.append('test_category', data.testCategory);
    if (data.testType) formData.append('test_type', data.testType);
    if (data.sessionId) formData.append('session_id', data.sessionId);
    if (data.process_title) formData.append('process_title', data.process_title);

    try {
      console.log('[ProcessService] Running test scenario generation with final prompt');
      console.log('[ProcessService] Data keys:', Object.keys(data));
      console.log('[ProcessService] Final prompt length:', data.finalPrompt?.length || 0);
      console.log('[ProcessService] Model:', data.model);
      
      const response = await fetch('/api/processes/test-scenario-generation/run', {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[ProcessService] Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      console.log('[ProcessService] Test scenario generation completed successfully:', result);
      return result;
    } catch (error) {
      console.error('[ProcessService] Error running test scenario generation:', error);
      throw error;
    }
  }
};

export default processService;
