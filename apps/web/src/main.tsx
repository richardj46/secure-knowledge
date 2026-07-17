import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import { router } from "./router";
import { SelectedOrganizationProvider } from "./shared/organizations/context";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <SelectedOrganizationProvider>
      <RouterProvider router={router} />
    </SelectedOrganizationProvider>
  </React.StrictMode>,
);
