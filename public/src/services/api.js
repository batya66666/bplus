import axios from 'axios';

const API_URL = 'http://localhost:8000';
const TOKEN_KEY = 'lms_token';

// 1. Создаем экземпляр axios
const api = axios.create({
  baseURL: API_URL,
});

// 2. Настраиваем перехватчики (interceptors)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 3. Экспортируем объект со ВСЕМИ методами
export default {
  // ========== AUTH ==========
  login: (email, password) => api.post('/auth/login', { email, password }),
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token) => localStorage.setItem(TOKEN_KEY, token),
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = '/login';
  },

  // ========== ADMIN ==========
  getDepartments: () => api.get('/departments'),
  createDepartment: (data) => api.post('/departments', data),
  assignCourse: (data) => api.post('/courses/assign', data),
  createUser: (data) => api.post('/users', data),
  getUsers: () => api.get('/users'),

  // ========== COURSES ==========
  getMyCourses: () => api.get('/my-courses'), // Список курсов с уроками

  // ========== VIDEO PLAYER (НОВЫЕ МЕТОДЫ) ==========
  getVideoProgress: (lessonId) => api.get(`/my-courses/lessons/${lessonId}/progress`),
  saveVideoProgress: (lessonId, data) => api.post(`/my-courses/lessons/${lessonId}/progress`, data),
  completeLesson: (data) => api.post('/my-courses/complete_lesson', data),
  // В файле api.js исправьте эту строку:
  getLessonDetail: (lessonId) =>
  api.get(`/my-courses/lessons/${lessonId}`),


  // ========== REPORTS ==========
  getMyReports: () => api.get('/standups/my'),
  sendReport: (data) => api.post('/standups', data),

  // ========== DOCUMENTS ==========
  getDocuments: (query) => api.get(`/documents?q=${query}`),
};