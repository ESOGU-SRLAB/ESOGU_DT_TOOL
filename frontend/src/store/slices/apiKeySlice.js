import { createSlice, createAsyncThunk, createSelector } from '@reduxjs/toolkit';
import axios from 'axios';

// API base URL
const API_BASE_URL = '';

// Async thunk for validating Google API key
export const validateGoogleApiKey = createAsyncThunk(
  'apiKey/validateGoogle',
  async (apiKey, { rejectWithValue }) => {
    try {
      // Test the API key by making a simple request to Google's API
      const response = await axios.post(`${API_BASE_URL}/api/test-google-api-key`, {
        api_key: apiKey
      });
      
      console.log('Google API validation response:', response.data);
      
      if (response.data.success) {
        return { 
          provider: 'google',
          isValid: true,
          key: apiKey,
          validatedAt: new Date().toISOString()
        };
      } else {
        return rejectWithValue(response.data.message || 'Invalid Google API key');
      }
    } catch (error) {
      return rejectWithValue(error.response?.data?.error || 'Failed to validate API key');
    }
  }
);

// Load API keys from localStorage
const loadApiKeysFromStorage = () => {
  try {
    const stored = localStorage.getItem('stlc_api_keys');
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        google: parsed.google || null,
        openai: parsed.openai || null,
        anthropic: parsed.anthropic || null,
        // Add other providers as needed
      };
    }
  } catch (error) {
    console.error('Error loading API keys from storage:', error);
  }
  return {
    google: null,
    openai: null,
    anthropic: null,
  };
};

// Save API keys to localStorage
const saveApiKeysToStorage = (apiKeys) => {
  try {
    localStorage.setItem('stlc_api_keys', JSON.stringify(apiKeys));
  } catch (error) {
    console.error('Error saving API keys to storage:', error);
  }
};

const initialState = {
  // API Keys for different providers
  apiKeys: loadApiKeysFromStorage(),
  
  // Validation status for each provider
  validation: {
    google: { isValidating: false, isValid: null, error: null, lastValidated: null },
    openai: { isValidating: false, isValid: null, error: null, lastValidated: null },
    anthropic: { isValidating: false, isValid: null, error: null, lastValidated: null },
  },
  
  // Global settings
  settings: {
    autoValidate: true,
    showApiKeyStatus: true,
    defaultProvider: 'google',
  },
  
  // UI state
  isLoading: false,
  error: null,
};

const apiKeySlice = createSlice({
  name: 'apiKey',
  initialState,
  reducers: {
    // Set API key for a specific provider
    setApiKey: (state, action) => {
      const { provider, key } = action.payload;
      state.apiKeys[provider] = key;
      
      // Reset validation status when key changes
      if (state.validation[provider]) {
        state.validation[provider] = {
          isValidating: false,
          isValid: null,
          error: null,
          lastValidated: null
        };
      }
      
      // Save to localStorage
      saveApiKeysToStorage(state.apiKeys);
    },
    
    // Remove API key for a specific provider
    removeApiKey: (state, action) => {
      const { provider } = action.payload;
      state.apiKeys[provider] = null;
      
      // Reset validation status
      if (state.validation[provider]) {
        state.validation[provider] = {
          isValidating: false,
          isValid: null,
          error: null,
          lastValidated: null
        };
      }
      
      // Save to localStorage
      saveApiKeysToStorage(state.apiKeys);
    },
    
    // Update settings
    updateSettings: (state, action) => {
      state.settings = { ...state.settings, ...action.payload };
    },
    
    // Clear all validation errors
    clearValidationErrors: (state) => {
      Object.keys(state.validation).forEach(provider => {
        state.validation[provider].error = null;
      });
    },
    
    // Set validation status manually (for testing)
    setValidationStatus: (state, action) => {
      const { provider, status } = action.payload;
      if (state.validation[provider]) {
        state.validation[provider] = { ...state.validation[provider], ...status };
      }
    },
  },
  
  extraReducers: (builder) => {
    // Google API key validation
    builder
      .addCase(validateGoogleApiKey.pending, (state) => {
        state.validation.google.isValidating = true;
        state.validation.google.error = null;
      })
      .addCase(validateGoogleApiKey.fulfilled, (state, action) => {
        state.validation.google.isValidating = false;
        state.validation.google.isValid = true;
        state.validation.google.error = null;
        state.validation.google.lastValidated = action.payload.validatedAt;
      })
      .addCase(validateGoogleApiKey.rejected, (state, action) => {
        state.validation.google.isValidating = false;
        state.validation.google.isValid = false;
        state.validation.google.error = action.payload;
      });
  },
});

// Action creators
export const {
  setApiKey,
  removeApiKey,
  updateSettings,
  clearValidationErrors,
  setValidationStatus,
} = apiKeySlice.actions;

// Selectors
export const selectApiKeys = (state) => state.apiKey.apiKeys;
export const selectApiKey = (provider) => (state) => state.apiKey.apiKeys[provider];
export const selectValidationStatus = (provider) => (state) => state.apiKey.validation[provider];
export const selectAllValidationStatus = (state) => state.apiKey.validation;
export const selectApiKeySettings = (state) => state.apiKey.settings;
export const selectIsAnyKeyValidating = (state) => 
  Object.values(state.apiKey.validation).some(v => v.isValidating);

// Helper selectors
export const selectHasValidApiKey = (provider) => (state) => {
  const key = state.apiKey.apiKeys[provider];
  const validation = state.apiKey.validation[provider];
  return key && validation?.isValid === true;
};

export const selectAvailableProviders = createSelector(
  [selectApiKeys, selectAllValidationStatus],
  (apiKeys, validationStatus) => {
    return Object.keys(apiKeys).filter(provider => 
      apiKeys[provider] && 
      validationStatus[provider]?.isValid === true
    );
  }
);

export default apiKeySlice.reducer;