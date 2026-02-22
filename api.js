import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  timeout: 30_000,
});

export const fetchHealth      = ()          => api.get('/health').then(r => r.data);
export const predictSingle    = (body)      => api.post('/predict-single', body).then(r => r.data);
export const fetchHistory     = (p = 1, l = 20) => api.get('/history', { params: { page: p, limit: l } }).then(r => r.data);
export const fetchHistoryEntry = (id)       => api.get(`/history/${id}`).then(r => r.data);
