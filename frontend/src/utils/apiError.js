function describe(value) {
  if (Array.isArray(value)) return value.map(describe).join(" ");
  if (value && typeof value === "object") return Object.entries(value).map(([field, detail]) => field + ": " + describe(detail)).join(" · ");
  return String(value);
}

export function errorMessage(error) {
  const body = error.response?.data;
  if (body?.errors) return describe(body.errors);
  return body?.detail || "Something went wrong. Please try again.";
}
