import { useEffect, useState } from "react";
import api from "../../api/axios";
import { errorMessage } from "../../utils/apiError";

const root = "/moderator/";

export const workspaceApi = {
  get: (path, config) => api.get(root + path, config),
  post: (path, data, config) => api.post(root + path, data, config),
  patch: (path, data) => api.patch(root + path, data),
  remove: (path) => api.delete(root + path),
};

export function useWorkspaceData(path) {
  const [version, setVersion] = useState(0);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    workspaceApi.get(path, { signal: controller.signal }).then(({ data }) => {
      if (!controller.signal.aborted) setResult({ path, version, data });
    }).catch((error) => {
      if (!controller.signal.aborted) setResult({ path, version, error: errorMessage(error) });
    });
    return () => controller.abort();
  }, [path, version]);

  const current = result?.path === path && result.version === version ? result : {};
  return { ...current, reload: () => setVersion((value) => value + 1) };
}

export async function download(path, filename) {
  try {
    const { data } = await workspaceApi.get(path, { responseType: "blob" });
    const url = URL.createObjectURL(data);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
  } catch (error) {
    if (error.response?.data instanceof Blob) {
      try {
        error.response.data = JSON.parse(await error.response.data.text());
      } catch {
        // The response may be an HTML error page from the hosting platform.
      }
    }
    throw error;
  }
}
