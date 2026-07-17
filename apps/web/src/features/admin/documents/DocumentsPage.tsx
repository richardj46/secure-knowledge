import { AdminPage } from "../shared/AdminPage";

export function DocumentsPage() {
  return (
    <AdminPage
      eyebrow="Ingestion operations"
      title="Documents"
      description="Inspect processing status, failures, and retry history."
    />
  );
}
