import { AdminPage } from "../shared/AdminPage";
import { useRequiredRouteParam } from "../shared/useRequiredRouteParam";

export function EvaluationRunDetailPage() {
  const runId = useRequiredRouteParam("runId");
  return (
    <AdminPage
      eyebrow="Evaluation review"
      title="Evaluation run detail"
      description="Inspect case evidence, regressions, graders, and reviews."
      resourceId={runId}
    />
  );
}
