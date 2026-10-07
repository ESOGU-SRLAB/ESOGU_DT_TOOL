/**
 * useModels.js
 * ------------
 * Merkezi AI model yönetimi için React hook'u.
 * Tüm form componentlerde kullanılabilir.
 * API Key aware - Global API key sistemini destekler.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { useSelector } from 'react-redux';
import { selectApiKeys, selectAllValidationStatus, selectApiKeySettings } from '../store/slices/apiKeySlice';

// API base URL
const API_BASE_URL = '/api/models';

/**
 * Merkezi model yönetimi hook'u
 * @param {Object} options - Hook konfigürasyon seçenekleri
 * @param {string} options.filterType - Model tipi filtresi (local/api)
 * @param {string} options.filterCategory - Model kategorisi filtresi
 * @param {string} options.filterPerformance - Performans filtresi
 * @param {boolean} options.optimizationReady - Optimization-ready modeller
 * @param {boolean} options.fastOnly - Sadece hızlı modeller
 * @param {boolean} options.autoFetch - Otomatik fetch (default: true)
 * @param {boolean} options.includeDescriptions - Model açıklamalarını dahil et
 * @param {boolean} options.includeUnavailableApi - API key olmayan API modellerini dahil et
 * @param {boolean} options.showApiKeyStatus - API key durumunu model bilgisinde göster
 * @returns {Object} Hook state ve fonksiyonları
 */
export const useModels = (options = {}) => {
  const {
    filterType = null,
    filterCategory = null,
    filterPerformance = null,
    optimizationReady = null,
    fastOnly = false,
    autoFetch = true,
    includeDescriptions = false,
    includeUnavailableApi = false,
    showApiKeyStatus = null // null = global setting'i kullan
  } = options;

  // Redux state - API key management
  const apiKeys = useSelector(selectApiKeys);
  const validationStatus = useSelector(selectAllValidationStatus);
  const apiKeySettings = useSelector(selectApiKeySettings);

  // Local state
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  // Cache için model açıklamaları
  const [modelDescriptions, setModelDescriptions] = useState({});

  // API key status gösterimi için setting
  const shouldShowApiKeyStatus = showApiKeyStatus !== null 
    ? showApiKeyStatus 
    : apiKeySettings.showApiKeyStatus;

  /**
   * API key durumuna göre modelleri filtrele
   */
  const filterModelsByApiKeyAvailability = useCallback((modelList) => {
    if (includeUnavailableApi) {
      return modelList; // Tüm modelleri dahil et
    }

    return modelList.filter(model => {
      // Local modeller her zaman kullanılabilir
      if (model.type === 'local') {
        return true;
      }

      // API modeller için API key kontrolü
      if (model.type === 'api') {
        const provider = model.provider?.toLowerCase();
        
        // Provider bilgisi yoksa dahil et (güvenli taraf)
        if (!provider) {
          return true;
        }

        // API key var mı ve geçerli mi kontrol et
        const hasKey = apiKeys[provider];
        const isValid = validationStatus[provider]?.isValid;
        
        // API key varsa ve geçerliliği bilinmiyorsa dahil et
        if (hasKey && isValid !== false) {
          return true;
        }

        // API key yoksa veya geçersizse dahil etme
        return false;
      }

      return true; // Diğer tip modeller için
    });
  }, [includeUnavailableApi, apiKeys, validationStatus]);

  /**
   * Modellere API key durumu bilgisini ekle
   */
  const enhanceModelsWithApiKeyStatus = useCallback((modelList) => {
    console.log('🔧 Enhancing models with API key status...');
    console.log('🔧 Input models (first 3):', modelList.slice(0, 3).map(m => ({
      key: m.key,
      name: m.name,
      provider: m.provider,
      type: m.type
    })));
    
    return modelList.map(model => {
      const enhancedModel = { ...model };

      if (model.type === 'api' && shouldShowApiKeyStatus) {
        // Provider mapping - backend'den gelen provider'ları Redux key'leri ile eşleştir
        const providerMapping = {
          'Google': 'google',
          'OpenAI': 'openai',
          // Diğer provider'lar eklenebilir
        };
        
        const backendProvider = model.provider;
        const reduxProvider = providerMapping[backendProvider] || backendProvider?.toLowerCase();
        
        console.log(`🔧 Provider mapping for ${model.key}:`, {
          backendProvider: backendProvider,
          reduxProvider: reduxProvider,
          hasApiKey: !!apiKeys[reduxProvider],
          apiKeys: apiKeys
        });
        
        if (reduxProvider && apiKeys[reduxProvider]) {
          const validation = validationStatus[reduxProvider];
          
          console.log(`🔧 API key found for ${reduxProvider}:`, {
            hasKey: !!apiKeys[reduxProvider],
            validation: validation,
            isValid: validation?.isValid
          });
          
          enhancedModel.apiKeyStatus = {
            hasKey: true,
            isValid: validation?.isValid,
            isValidating: validation?.isValidating,
            error: validation?.error,
            lastValidated: validation?.lastValidated,
            provider: reduxProvider
          };

          // Standart model adı formatı: "Model Adı - Açıklama"
          const baseDisplayName = `${model.name} - ${model.description}`;
          
          // Model adına durum ekle (eğer ayar aktifse)
          if (validation?.isValid === true) {
            enhancedModel.displayName = `${baseDisplayName} ✓`;
          } else if (validation?.isValid === false) {
            enhancedModel.displayName = `${baseDisplayName} ⚠️`;
          } else if (validation?.isValidating) {
            enhancedModel.displayName = `${baseDisplayName} 🔄`;
          } else {
            enhancedModel.displayName = `${baseDisplayName} ❓`;
          }
        } else {
          enhancedModel.apiKeyStatus = {
            hasKey: false,
            isValid: false,
            isValidating: false,
            error: 'No API key configured',
            lastValidated: null,
            provider: reduxProvider || backendProvider?.toLowerCase()
          };
          
          enhancedModel.displayName = `${model.name} - ${model.description} 🔐`;
        }
      } else {
        // Local modeller için standart format
        enhancedModel.displayName = `${model.name} - ${model.description}`;
        enhancedModel.apiKeyStatus = {
          hasKey: true, // Local modeller için API key gerekmez
          isValid: true,
          isValidating: false,
          error: null,
          provider: 'local'
        };
      }

      return enhancedModel;
    });
  }, [shouldShowApiKeyStatus, apiKeys, validationStatus]);

  /**
   * API'den modelleri getir
   */
  const fetchModels = useCallback(async (customFilters = {}) => {
    setLoading(true);
    setError(null);

    try {
      // Filter parametrelerini hazırla
      const filters = {
        model_type: filterType,
        category: filterCategory,
        performance: filterPerformance,
        optimization_ready: optimizationReady,
        legacy_format: true, // Mevcut frontend uyumluluğu için
        ...customFilters
      };

      // Fast only filtresi varsa performans filtresi ekle
      if (fastOnly && !filters.performance) {
        // İki ayrı request ile fast ve very-fast modelleri al
        const fastResponse = await axios.get(`${API_BASE_URL}/fast`);
        if (fastResponse.data.success) {
          const fastModels = fastResponse.data.data.map(model => ({
            key: model.key,
            name: model.name,
            description: model.description,
            type: model.type,
            provider: model.provider,
            performance: model.performance,
            category: model.category
          }));
          
          // API key durumunu ekle
          const modelsWithApiKeyStatus = enhanceModelsWithApiKeyStatus(fastModels);
          setModels(modelsWithApiKeyStatus);
          setLastFetch(new Date());
          setLoading(false);
          return modelsWithApiKeyStatus;
        }
      }

      // Normal API çağrısı
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          params.append(key, value);
        }
      });

      // Test with direct fetch
      console.log('🔍 Making request to:', `${API_BASE_URL}?${params}`);
      const testResponse = await fetch(`${API_BASE_URL}?${params}`);
      const testData = await testResponse.json();
      console.log('🔍 Direct fetch response:', testData);
      console.log('🔍 Direct fetch models (first 3):', testData.data?.slice(0, 3).map(m => ({
        key: m.key,
        name: m.name,
        provider: m.provider,
        type: m.type
      })));

      const response = await axios.get(`${API_BASE_URL}?${params}`);
      
      console.log('🔍 Raw API Response:', response.data);
      console.log('🔍 First 3 models from API:', response.data.data?.slice(0, 3).map(m => ({
        key: m.key,
        name: m.name,
        provider: m.provider,
        type: m.type
      })));
      
      if (response.data.success) {
        let fetchedModels = response.data.data;
        
        // API key aware filtering
        fetchedModels = filterModelsByApiKeyAvailability(fetchedModels);
        
        // API key durumunu ekle
        fetchedModels = enhanceModelsWithApiKeyStatus(fetchedModels);
        
        setModels(fetchedModels);
        setLastFetch(new Date());

        // Model açıklamalarını getir (eğer istenmişse)
        if (includeDescriptions) {
          await fetchModelDescriptions(fetchedModels);
        }

        console.log(`[useModels] Fetched ${fetchedModels.length} models successfully`);
        return fetchedModels;
      } else {
        throw new Error(response.data.message || 'Failed to fetch models');
      }
    } catch (err) {
      console.error('[useModels] Error fetching models:', err);
      setError(err.message || 'Failed to fetch models');
      
      // Fallback: Static model listesi (geriye uyumluluk)
      const fallbackModels = getFallbackModels(filterType, filterCategory);
      const fallbackWithApiKeyStatus = enhanceModelsWithApiKeyStatus(fallbackModels);
      setModels(fallbackWithApiKeyStatus);
      return fallbackWithApiKeyStatus;
    } finally {
      setLoading(false);
    }
  }, [filterType, filterCategory, filterPerformance, optimizationReady, fastOnly, includeDescriptions, includeUnavailableApi, apiKeys, validationStatus]);

  /**
   * Model açıklamalarını getir
   */
  const fetchModelDescriptions = useCallback(async (modelList) => {
    const descriptions = {};
    
    try {
      for (const model of modelList) {
        try {
          const response = await axios.get(`${API_BASE_URL}/${model.key}/descriptions`);
          if (response.data.success) {
            descriptions[model.key] = response.data.data.descriptions;
          }
        } catch (err) {
          // Sessizce geç, açıklama zorunlu değil
          console.warn(`[useModels] Could not fetch descriptions for ${model.key}`);
        }
      }
      
      setModelDescriptions(prev => ({ ...prev, ...descriptions }));
    } catch (err) {
      console.warn('[useModels] Error fetching model descriptions:', err);
    }
  }, []);

  /**
   * Belirli bir model hakkında detay getir
   */
  const getModelDetails = useCallback(async (modelKey) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/${modelKey}`);
      if (response.data.success) {
        return response.data.data;
      }
      throw new Error(response.data.message || 'Model not found');
    } catch (err) {
      console.error(`[useModels] Error fetching model details for ${modelKey}:`, err);
      return null;
    }
  }, []);

  /**
   * Modelleri yeniden getir
   */
  const refetch = useCallback((customFilters = {}) => {
    return fetchModels(customFilters);
  }, [fetchModels]);

  /**
   * Kategori listesini getir
   */
  const fetchCategories = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/categories`);
      if (response.data.success) {
        return response.data.data.categories;
      }
      throw new Error('Failed to fetch categories');
    } catch (err) {
      console.error('[useModels] Error fetching categories:', err);
      return ['code', 'general', 'reasoning', 'multilingual', 'development'];
    }
  }, []);

  /**
   * Performans seviyelerini getir
   */
  const fetchPerformanceLevels = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/performance-levels`);
      if (response.data.success) {
        return response.data.data.levels;
      }
      throw new Error('Failed to fetch performance levels');
    } catch (err) {
      console.error('[useModels] Error fetching performance levels:', err);
      return ['very-fast', 'fast', 'medium', 'slow', 'very-slow'];
    }
  }, []);

  // Otomatik fetch (component mount'ta)
  useEffect(() => {
    if (autoFetch) {
      fetchModels();
    }
  }, [autoFetch, fetchModels]);

  // Computed values
  const modelsByType = useMemo(() => {
    return models.reduce((acc, model) => {
      if (!acc[model.type]) acc[model.type] = [];
      acc[model.type].push(model);
      return acc;
    }, {});
  }, [models]);

  const modelsByCategory = useMemo(() => {
    return models.reduce((acc, model) => {
      const category = model.category || 'general';
      if (!acc[category]) acc[category] = [];
      acc[category].push(model);
      return acc;
    }, {});
  }, [models]);

  const fastModels = useMemo(() => {
    return models.filter(model => 
      ['fast', 'very-fast'].includes(model.performance)
    );
  }, [models]);

  const apiModels = useMemo(() => {
    return models.filter(model => model.type === 'api');
  }, [models]);

  const localModels = useMemo(() => {
    return models.filter(model => model.type === 'local');
  }, [models]);

  // API key aware computed values
  const availableApiModels = useMemo(() => {
    return apiModels.filter(model => 
      model.apiKeyStatus?.hasKey && model.apiKeyStatus?.isValid !== false
    );
  }, [apiModels]);

  const unavailableApiModels = useMemo(() => {
    return apiModels.filter(model => 
      !model.apiKeyStatus?.hasKey || model.apiKeyStatus?.isValid === false
    );
  }, [apiModels]);

  const validatedApiModels = useMemo(() => {
    return apiModels.filter(model => 
      model.apiKeyStatus?.isValid === true
    );
  }, [apiModels]);

  const modelsByApiKeyStatus = useMemo(() => {
    return {
      available: models.filter(model => 
        model.type === 'local' || (model.apiKeyStatus?.hasKey && model.apiKeyStatus?.isValid !== false)
      ),
      unavailable: models.filter(model => 
        model.type === 'api' && (!model.apiKeyStatus?.hasKey || model.apiKeyStatus?.isValid === false)
      ),
      validated: models.filter(model => 
        model.type === 'local' || model.apiKeyStatus?.isValid === true
      ),
      pending: models.filter(model => 
        model.type === 'api' && model.apiKeyStatus?.hasKey && model.apiKeyStatus?.isValid === null
      )
    };
  }, [models]);

  // Yardımcı fonksiyonlar
  const getModelByKey = useCallback((key) => {
    return models.find(model => model.key === key);
  }, [models]);

  const getModelDescriptions = useCallback((key) => {
    return modelDescriptions[key] || [];
  }, [modelDescriptions]);

  return {
    // Ana data
    models,
    loading,
    error,
    lastFetch,

    // Computed data
    modelsByType,
    modelsByCategory,
    fastModels,
    apiModels,
    localModels,

    // API key aware data
    availableApiModels,
    unavailableApiModels,
    validatedApiModels,
    modelsByApiKeyStatus,

    // Model açıklamaları
    modelDescriptions,
    getModelDescriptions,

    // Fonksiyonlar
    fetchModels,
    refetch,
    getModelDetails,
    getModelByKey,
    fetchCategories,
    fetchPerformanceLevels,

    // API key aware fonksiyonlar
    filterModelsByApiKeyAvailability,
    enhanceModelsWithApiKeyStatus,

    // Yardımcı fonksiyonlar
    hasModels: models.length > 0,
    isEmpty: models.length === 0,
    totalCount: models.length,
    localCount: localModels.length,
    apiCount: apiModels.length,
    fastCount: fastModels.length,
    availableApiCount: availableApiModels.length,
    unavailableApiCount: unavailableApiModels.length,
    validatedApiCount: validatedApiModels.length,

    // API key status
    apiKeySettings,
    shouldShowApiKeyStatus,
    hasValidApiKeys: Object.values(apiKeys).some(key => key),
    validApiProviders: Object.entries(validationStatus).filter(([_, status]) => status.isValid === true).map(([provider]) => provider)
  };
};

/**
 * Fallback model listesi (API erişilmediğinde)
 */
function getFallbackModels(filterType = null, filterCategory = null) {
  const fallbackModels = [
    // Temel modeller
    { key: "codegeex4:9b", name: "CodeGeeX4 (9B)", description: "Code generation optimized model", type: "local", category: "code" },
    { key: "codellama:7b", name: "Code Llama (7B)", description: "Meta's code-focused model", type: "local", category: "code" },
    { key: "deepseek-coder:6.7b", name: "DeepSeek Coder (6.7B)", description: "DeepSeek's coding model", type: "local", category: "code" },
    { key: "gemma2:2b", name: "Gemma 2 (2B)", description: "Google's lightweight model", type: "local", category: "general" },
    { key: "gemma3:4b", name: "Gemma 3 (4B)", description: "Google's enhanced model", type: "local", category: "general" },
    { key: "llama3.2:3b", name: "Llama 3.2 (3B)", description: "Meta's latest efficient model", type: "local", category: "general" },
    { key: "qwen2.5:7b", name: "Qwen 2.5 (7B)", description: "Alibaba's advanced model", type: "local", category: "multilingual" },
    { key: "qwen2.5-coder:3b", name: "Qwen 2.5 Coder (3B)", description: "Coding-focused Qwen model", type: "local", category: "code" },
    { key: "stable-code:3b", name: "Stable Code (3B)", description: "Stability AI's code model", type: "local", category: "code" },
    { key: "starcoder2:7b", name: "StarCoder 2 (7B)", description: "BigCode's enhanced model", type: "local", category: "code" },

    // API modelleri
    { key: "gemini-2.5-flash", name: "Gemini 2.5 Flash", description: "Google's latest fast model", type: "api", category: "general" },
    { key: "gemini-2.5-pro", name: "Gemini 2.5 Pro", description: "Google's latest pro model", type: "api", category: "general" }
  ];

  // Filtreleme uygula
  let filtered = fallbackModels;
  
  if (filterType) {
    filtered = filtered.filter(model => model.type === filterType);
  }
  
  if (filterCategory) {
    filtered = filtered.filter(model => model.category === filterCategory);
  }

  return filtered;
}

/**
 * Sadece hızlı modeller için özel hook
 */
export const useFastModels = () => {
  return useModels({ fastOnly: true });
};

/**
 * Test Case Optimization modelleri için özel hook
 */
export const useOptimizationModels = () => {
  return useModels({ optimizationReady: true });
};

/**
 * API modelleri için özel hook (sadece kullanılabilir olanlar)
 */
export const useApiModels = () => {
  return useModels({ filterType: 'api', includeUnavailableApi: false });
};

/**
 * Tüm API modelleri için özel hook (kullanılabilir olmayan dahil)
 */
export const useAllApiModels = () => {
  return useModels({ filterType: 'api', includeUnavailableApi: true });
};

/**
 * Local modeller için özel hook
 */
export const useLocalModels = () => {
  return useModels({ filterType: 'local' });
};

/**
 * Belirli bir kategori için modeller
 */
export const useModelsByCategory = (category) => {
  return useModels({ filterCategory: category });
};

/**
 * Sadece geçerli API key'i olan modeller
 */
export const useValidatedModels = () => {
  return useModels({ includeUnavailableApi: false, showApiKeyStatus: true });
};

/**
 * API key durumu gösteren modeller
 */
export const useModelsWithApiKeyStatus = () => {
  return useModels({ includeUnavailableApi: true, showApiKeyStatus: true });
};

export default useModels;