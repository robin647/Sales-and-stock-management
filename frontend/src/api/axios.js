import axios from "axios";
import { portalLogin } from "../routes/paths";

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
const defaultApiUrl = import.meta.env.PROD
  ? "https://sales-and-stock-management.onrender.com/api"
  : "http://localhost:8000/api";
const configuredBaseUrl = (configuredApiUrl || defaultApiUrl).replace(/\/+$/, "");

const API_URL = /\/api$/i.test(configuredBaseUrl)
  ? configuredBaseUrl
  : `${configuredBaseUrl}/api`;

const api = axios.create({ baseURL: API_URL });
const isLoginRequest = (url = "") => /^\/auth\/(?:login\/(?:showroom\/)?|customer\/login\/|refresh\/)$/.test(url);

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token && !isLoginRequest(config.url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let queue = [];

function processQueue(error, token = null) {
  queue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  queue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (import.meta.env.DEV) {
      console.error("[API request failed]", {
        method: originalRequest?.method?.toUpperCase(),
        url: originalRequest?.baseURL ? `${originalRequest.baseURL}${originalRequest.url}` : originalRequest?.url,
        status: error.response?.status,
      });
    }

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      // A rejected login must stay rejected; never replay submitted credentials
      // using a previous account's refresh token or redirect away from its error.
      if (isLoginRequest(originalRequest.url)) {
        return Promise.reject(error);
      }
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        if (localStorage.getItem("access_token")) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = portalLogin(window.location.pathname);
        }
        return Promise.reject(error);
      }

      originalRequest._retry = true;
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      isRefreshing = true;

      try {
        const { data } = await axios.post(`${API_URL}/auth/refresh/`, {
          refresh: refreshToken,
        });
        if (localStorage.getItem("refresh_token") !== refreshToken) {
          processQueue(error);
          return Promise.reject(error);
        }
        localStorage.setItem("access_token", data.access);
        if (data.refresh) localStorage.setItem("refresh_token", data.refresh);
        processQueue(null, data.access);
        originalRequest.headers.Authorization = `Bearer ${data.access}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
        if (localStorage.getItem("refresh_token") === refreshToken) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = portalLogin(window.location.pathname);
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
