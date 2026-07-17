import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { getAccessToken } from "./tokens";

export function RequireAuthentication({ children }: { children: ReactNode }) {
  const location = useLocation();

  if (!getAccessToken()) {
    const from = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to="/login" replace state={{ from }} />;
  }

  return children;
}
