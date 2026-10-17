import api from "./axios";

export const authApi = {
  login: (username, password) => api.post("/auth/login/", { username, password }),
  showroomLogin: (username, password) => api.post("/auth/login/showroom/", { username, password }),
  me: () => api.get("/accounts/me/"),
};

export const showroomApi = {
  list: () => api.get("/showrooms/"),
  create: (data) => api.post("/showrooms/", data),
  update: (id, data) => api.patch(`/showrooms/${id}/`, data),
};

export const showroomUserApi = {
  list: () => api.get("/accounts/showroom-users/"),
  create: (data) => api.post("/accounts/showroom-users/", data),
  update: (id, data) => api.patch(`/accounts/showroom-users/${id}/`, data),
};

export const categoryApi = {
  list: () => api.get("/products/categories/"),
  create: (data) => api.post("/products/categories/", data),
};

export const productApi = {
  list: (params) => api.get("/products/", { params }),
  create: (data) => api.post("/products/", data),
  update: (id, data) => api.patch(`/products/${id}/`, data),
};

export const stockApi = {
  list: (params) => api.get("/inventory/stocks/", { params }),
  create: (data) => api.post("/inventory/stocks/", data),
  update: (id, data) => api.patch(`/inventory/stocks/${id}/`, data),
};

export const balanceApi = {
  list: (params) => api.get("/inventory/balances/", { params }),
  create: (data) => api.post("/inventory/balances/", data),
  update: (id, data) => api.patch(`/inventory/balances/${id}/`, data),
};

export const reportApi = {
  dashboard: (params) => api.get("/reports/dashboard/", { params }),
  daily: (params) => api.get("/reports/daily/", { params }),
  monthly: (params) => api.get("/reports/monthly/", { params }),
  exportDaily: (params, filename) => downloadFile("/reports/export/daily/", params, filename),
  exportMonthly: (params, filename) => downloadFile("/reports/export/monthly/", params, filename),
};

// Excel export endpoints require the JWT header, so a plain <a href> link
// won't work — we fetch as a blob (auth header attached automatically by
// the axios interceptor) and then trigger the browser download manually.
async function downloadFile(path, params, filename) {
  const response = await api.get(path, { params, responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename || "report.xlsx");
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
