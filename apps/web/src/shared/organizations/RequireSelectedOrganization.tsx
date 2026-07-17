import type { ReactNode } from "react";

import { useSelectedOrganization } from "./context";

export function RequireSelectedOrganization({
  children,
}: {
  children: ReactNode;
}) {
  const { organization } = useSelectedOrganization();

  if (!organization) {
    return (
      <main className="organization-required">
        <p className="eyebrow">Organization required</p>
        <h1>Select an organization to open administration.</h1>
        <p>
          The admin area reads organization scope from the application&apos;s
          organization switcher. It never accepts a tenant ID from an editable
          admin form.
        </p>
      </main>
    );
  }

  return children;
}
