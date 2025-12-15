// Create axios instance with base configuration
import axios from 'axios';

// API Configuration - Vite uses import.meta.env instead of process.env
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 1260000, // 21 minutes (1260 seconds) - slightly longer than backend to avoid race conditions
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data || config.params);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response from ${response.config.url}:`, response.data);
    return response;
  },
  (error) => {
    console.error('[API] Response error:', error.response?.data || error.message);
    
    // Timeout hatalarında retry YAPMA - kullanıcıya hata göster
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      console.error('[API] Request timed out - NOT retrying automatically');
      const timeoutError = new Error('Request timed out after 21 minutes. The operation is taking too long. Please try with fewer files, a simpler prompt, or a faster model.');
      timeoutError.isTimeout = true;
      return Promise.reject(timeoutError);
    }
    
    return Promise.reject(error);
  }
);

export default api;