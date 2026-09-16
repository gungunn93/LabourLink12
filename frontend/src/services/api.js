import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_BACKEND_URL || "/api",
  timeout: 20000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ll_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      const path = window.location.pathname;
      if (!path.startsWith("/login") && !path.startsWith("/register")) {
        localStorage.removeItem("ll_token");
        localStorage.removeItem("ll_user");
      }
    }
    return Promise.reject(error);
  }
);

export const unwrap = (res) => res.data?.data;
export const messageOf = (error, fallback = "Something went wrong") =>
  error.response?.data?.message || error.message || fallback;

export default api;
