import { Navigate, createBrowserRouter } from "react-router-dom";

import { AnswerRunDetailPage } from "./features/admin/answer-runs/AnswerRunDetailPage";
import { AnswerRunsPage } from "./features/admin/answer-runs/AnswerRunsPage";
import { AuditLogPage } from "./features/admin/audit-log/AuditLogPage";
import { AdminDashboardPage } from "./features/admin/dashboard/AdminDashboardPage";
import { DocumentDetailPage } from "./features/admin/documents/DocumentDetailPage";
import { DocumentsPage } from "./features/admin/documents/DocumentsPage";
import { EvaluationRunDetailPage } from "./features/admin/evaluations/EvaluationRunDetailPage";
import { EvaluationRunsPage } from "./features/admin/evaluations/EvaluationRunsPage";
import { RetrievalRunDetailPage } from "./features/admin/retrieval-runs/RetrievalRunDetailPage";
import { RetrievalRunsPage } from "./features/admin/retrieval-runs/RetrievalRunsPage";
import { AdminLayout } from "./features/admin/shared/AdminLayout";
import { RequireSelectedOrganization } from "./shared/organizations/RequireSelectedOrganization";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/admin" replace />,
  },
  {
    path: "/admin",
    element: (
      <RequireSelectedOrganization>
        <AdminLayout />
      </RequireSelectedOrganization>
    ),
    children: [
      { index: true, element: <AdminDashboardPage /> },
      { path: "retrieval", element: <RetrievalRunsPage /> },
      { path: "retrieval/:runId", element: <RetrievalRunDetailPage /> },
      { path: "answers", element: <AnswerRunsPage /> },
      { path: "answers/:answerRunId", element: <AnswerRunDetailPage /> },
      { path: "documents", element: <DocumentsPage /> },
      { path: "documents/:documentId", element: <DocumentDetailPage /> },
      { path: "evaluations", element: <EvaluationRunsPage /> },
      { path: "evaluations/:runId", element: <EvaluationRunDetailPage /> },
      { path: "audit", element: <AuditLogPage /> },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/admin" replace />,
  },
]);
