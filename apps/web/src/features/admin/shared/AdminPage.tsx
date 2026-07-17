import type { ReactNode } from "react";

import { useSelectedOrganization } from "../../../shared/organizations/context";

interface AdminPageProps {
  eyebrow: string;
  title: string;
  description: string;
  resourceId?: string;
  children?: ReactNode;
}

export function AdminPage({
  eyebrow,
  title,
  description,
  resourceId,
  children,
}: AdminPageProps) {
  const { organization } = useSelectedOrganization();

  return (
    <section>
      <header className="page-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <div className="scope-card" aria-label="Current organization scope">
          <span>Organization</span>
          <strong>{organization?.name}</strong>
        </div>
      </header>
      {resourceId ? (
        <div className="resource-id">
          <span>Resource ID</span>
          <code>{resourceId}</code>
        </div>
      ) : null}
      {children ?? (
        <div className="empty-panel">
          <h3>Admin view ready</h3>
          <p>
            This route is scoped through the selected organization context and
            is ready for its read-only data view.
          </p>
        </div>
      )}
    </section>
  );
}
