export const legacyAdminPaths = {
  "/products": "/admin/products", "/showrooms": "/admin/showrooms",
  "/stock-adjustments": "/admin/stock-adjustments", "/employees": "/admin/employees",
  "/swing": "/admin/swing", "/producer-cost-management": "/admin/producer-cost-management",
  "/online-products": "/admin/online-products", "/online-stock": "/admin/online-stock", "/online-orders": "/admin/online-orders",
  "/wholesale/parties": "/admin/wholesale/parties", "/wholesale/sales": "/admin/wholesale/sales",
  "/wholesale/easy": "/admin/wholesale/easy", "/wholesale/returns": "/admin/wholesale/returns",
  "/wholesale/summary": "/admin/wholesale/summary", "/wholesale/reports": "/admin/wholesale/reports",
};
export function portalLogin(path) {
  return path.startsWith("/admin") ? "/admin/login" : path.startsWith("/showroom") ? "/showroom/login" : "/login";
}
