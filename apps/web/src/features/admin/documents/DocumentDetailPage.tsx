import { AdminPage } from "../shared/AdminPage";
import { useRequiredRouteParam } from "../shared/useRequiredRouteParam";

export function DocumentDetailPage() {
  const documentId = useRequiredRouteParam("documentId");
  return (
    <AdminPage
      eyebrow="Document inspection"
      title="Document detail"
      description="Review versions, processing attempts, and safe failure details."
      resourceId={documentId}
    />
  );
}
