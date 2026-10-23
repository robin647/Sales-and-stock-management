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

export const factoryStockApi = {
  list: (params) => api.get("/inventory/factory-stocks/", { params }),
};

export const stockAdjustmentApi = {
  list: (params) => api.get("/wholesale/stock-adjustments/", { params }),
  create: (data) => api.post("/wholesale/stock-adjustments/", data),
};

export const wholesalePartyApi = {
  list: (params) => api.get("/wholesale/parties/", { params }),
  get: (id) => api.get(`/wholesale/parties/${id}/`),
  create: (data) => api.post("/wholesale/parties/", data),
  update: (id, data) => api.patch(`/wholesale/parties/${id}/`, data),
  history: (id, params) => api.get(`/wholesale/parties/${id}/history/`, { params }),
  exportStatement: (id, params) => downloadFile(`/wholesale/parties/${id}/statement/export/`, params, `party-${id}-account-statement.xlsx`),
};

export const wholesaleInvoiceApi = {
  list: (params) => api.get("/wholesale/invoices/", { params }),
  get: (id) => api.get(`/wholesale/invoices/${id}/`),
  create: (data) => api.post("/wholesale/invoices/", data),
  update: (id, data) => api.patch(`/wholesale/invoices/${id}/`, data),
  delete: (id) => api.delete(`/wholesale/invoices/${id}/`),
};

export const easyWholesaleApi = {
  sales: {
    list: (params) => api.get("/wholesale/easy/sales/", { params }),
    get: (id) => api.get(`/wholesale/easy/sales/${id}/`),
    create: (data, idempotencyKey) => api.post("/wholesale/easy/sales/", data, { headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {} }),
    update: (id, data) => api.patch(`/wholesale/easy/sales/${id}/`, data),
    delete: (id) => api.delete(`/wholesale/easy/sales/${id}/`),
  },
  payments: {
    list: (params) => api.get("/wholesale/easy/payments/", { params }),
    get: (id) => api.get(`/wholesale/easy/payments/${id}/`),
    create: (data, idempotencyKey) => api.post("/wholesale/easy/payments/", data, { headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {} }),
    update: (id, data) => api.patch(`/wholesale/easy/payments/${id}/`, data),
    delete: (id) => api.delete(`/wholesale/easy/payments/${id}/`),
  },
  returns: {
    list: (params) => api.get("/wholesale/easy/returns/", { params }),
    get: (id) => api.get(`/wholesale/easy/returns/${id}/`),
    create: (data, idempotencyKey) => api.post("/wholesale/easy/returns/", data, { headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {} }),
    update: (id, data) => api.patch(`/wholesale/easy/returns/${id}/`, data),
    delete: (id) => api.delete(`/wholesale/easy/returns/${id}/`),
  },
};

export const wholesalePaymentApi = {
  list: (params) => api.get("/wholesale/payments/", { params }),
  get: (id) => api.get(`/wholesale/payments/${id}/`),
  create: (data, idempotencyKey) => api.post("/wholesale/payments/", data, { headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {} }),
  update: (id, data) => api.patch(`/wholesale/payments/${id}/`, data),
  delete: (id) => api.delete(`/wholesale/payments/${id}/`),
};

export const wholesaleReturnApi = {
  list: (params) => api.get("/wholesale/returns/", { params }),
  get: (id) => api.get(`/wholesale/returns/${id}/`),
  create: (data, idempotencyKey) => api.post("/wholesale/returns/", data, { headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {} }),
  update: (id, data) => api.patch(`/wholesale/returns/${id}/`, data),
  delete: (id) => api.delete(`/wholesale/returns/${id}/`),
};

export const wholesaleReportApi = {
  summary: (params) => api.get("/wholesale/summary/", { params }),
  exportSummary: (params) => downloadFile("/wholesale/summary/export/", params, "wholesale-all-parties-summary.xlsx"),
  reports: (params) => api.get("/wholesale/reports/", { params }),
  export: (params) => downloadFile("/wholesale/reports/export/", params, "wholesale-report.xlsx"),
};

export const showroomStockApi = {
  list: (params) => api.get("/inventory/showroom-stocks/", { params }),
};

export const stockTransferApi = {
  list: (params) => api.get("/inventory/transfers/", { params }),
  create: (data) => api.post("/inventory/transfers/", data),
  update: (id, data) => api.patch(`/inventory/transfers/${id}/`, data),
  delete: (id) => api.delete(`/inventory/transfers/${id}/`),
  summary: (params) => api.get("/inventory/transfers/summary/", { params }),

  receive: (data) => api.post("/inventory/transfers/", { ...data, transfer_type: "receive" }),
  sell: (data) => api.post("/inventory/transfers/", { ...data, transfer_type: "sale" }),
  return: (data) => api.post("/inventory/transfers/", { ...data, transfer_type: "return" }),
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
