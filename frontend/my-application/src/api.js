import axios from "axios";

// Resume parsing and first-time database connections can take longer than a short
// request timeout. Keep requests alive long enough for the server to finish them.
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api", timeout: 60000 });
let refreshPromise = null;
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("skilltrack-access-token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use((response) => response.data, (error) => {
  const originalRequest = error.config;
  const refreshToken = localStorage.getItem("skilltrack-refresh-token");
  const isAuthMutation = /\/auth\/(login|register|refresh|logout)/.test(originalRequest?.url || "");
  if (error.response?.status === 401 && refreshToken && !originalRequest?._retried && !isAuthMutation) {
    originalRequest._retried = true;
    if (!refreshPromise) refreshPromise = axios.post(`${api.defaults.baseURL}/auth/refresh`, { refresh_token: refreshToken }).then(({ data }) => {
      localStorage.setItem("skilltrack-access-token", data.access_token);
      localStorage.setItem("skilltrack-refresh-token", data.refresh_token);
      return data.access_token;
    }).catch((refreshError) => {
      localStorage.removeItem("skilltrack-access-token");
      localStorage.removeItem("skilltrack-refresh-token");
      window.dispatchEvent(new Event("skilltrack:session-expired"));
      throw refreshError;
    }).finally(() => { refreshPromise = null; });
    return refreshPromise.then((accessToken) => {
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return api(originalRequest);
    }).catch(() => {
      return Promise.reject(new Error("Your session expired. Please sign in again."));
    });
  }
  const message = error.response?.data?.detail || (error.code === "ECONNABORTED" ? "The request took too long. Please try again." : error.message) || "The server could not be reached. Make sure the API is running.";
  return Promise.reject(new Error(Array.isArray(message) ? message.map((item) => item.msg).join(", ") : message));
});

export default api;
