import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, ".", "");
  const apiTarget =
    environment.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/auth": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/organizations": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/workspaces": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/documents": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/document-versions": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/groups": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
