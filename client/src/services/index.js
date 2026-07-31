import api from './api';

export const authService = {
  login: (username, password) =>
    api.post('/auth/login', { username, password }),

  register: (email, username, password) =>
    api.post('/auth/register', { email, username, password }),

  refresh: (refreshToken) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),

  getProfile: () => api.get('/users/me'),

  updateProfile: (data) => api.put('/users/me', data),
};

export const forecastService = {
  generate: (params) => api.post('/forecast/generate', params),
  history: () => api.get('/forecast/history'),
  getById: (id) => api.get(`/forecast/${id}`),
};

export const inventoryService = {
  generateRecommendations: (params) => api.post('/inventory/recommendations', params),
  demandMultiplier: () => api.get('/inventory/demand-multiplier'),
  seasonalAdvice: () => api.get('/inventory/seasonal-advice'),
};

export const analyticsService = {
  overview: () => api.get('/analytics/overview'),
  salesTrend: (days = 90) => api.get(`/analytics/sales-trend?days=${days}`),
  topProducts: (limit = 10) => api.get(`/analytics/top-products?limit=${limit}`),
  storePerformance: () => api.get('/analytics/store-performance'),
  seasonal: () => api.get('/analytics/seasonal'),
  dayOfWeek: () => api.get('/analytics/day-of-week'),
};

export const uploadService = {
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  history: () => api.get('/upload/history'),
  clean: (datasetId) => api.post(`/upload/${datasetId}/clean`),
};

export const modelService = {
  train: (params) => api.post('/model/train', params),
  history: () => api.get('/model/history'),
  best: () => api.get('/model/best'),
  features: () => api.get('/model/features'),
};

export const insightsService = {
  generate: () => api.post('/insights/generate'),
  list: () => api.get('/insights/list'),
  seasonContext: () => api.get('/insights/season-context'),
};

export const weatherService = {
  current: (city = 'Lahore') => api.get(`/weather/current?city=${city}`),
  forecast: (city = 'Lahore', days = 7) => api.get(`/weather/forecast?city=${city}&days=${days}`),
  holidaysUpcoming: (limit = 10) => api.get(`/weather/holidays/upcoming?limit=${limit}`),
  holidaysCurrent: () => api.get('/weather/holidays/current'),
};
