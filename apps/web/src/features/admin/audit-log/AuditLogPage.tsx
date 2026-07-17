import { AdminPage } from "../shared/AdminPage";

export function AuditLogPage() {
  return (
    <AdminPage
      eyebrow="Security audit"
      title="Audit log"
      description="Review immutable organization-scoped administrative events."
    />
  );
}
