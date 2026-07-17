import { useEffect, useMemo, useState } from "react";

import { useSelectedOrganization } from "../../../shared/organizations/context";
import { fetchAdminResource } from "../shared/adminApi";

const LATENCY_ALERT_THRESHOLD_MS = 10_000;
const COST_ALERT_THRESHOLD_MICROUSD_PER_QUERY = 25_000;

export interface AdminOverviewMetrics {
  total_queries: number;
  answered_queries: number;
  abstained_queries: number;
  failed_queries: number;
  answer_rate: number;
  abstention_rate: number;
  failure_rate: number;
  empty_retrieval_rate: number;
  average_retrieval_latency_ms: number;
  p95_retrieval_latency_ms: number;
  average_generation_latency_ms: number;
  p95_generation_latency_ms: number;
  average_total_latency_ms: number;
  p95_total_latency_ms: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_estimated_cost_microusd: number;
  documents_ready: number;
  documents_processing: number;
  documents_failed: number;
  evaluation_runs: number;
  evaluation_pass_rate: number;
  authorization_leakage_count: number;
}

interface FailedDocument {
  document_id: string;
  document_title: string;
  version_id: string;
  failure_code: string | null;
  safe_failure_message: string | null;
}

interface FailedDocumentsResponse {
  items: FailedDocument[];
}

interface AnswerRun {
  id: string;
  status: string;
  failure_code: string | null;
}

interface AnswerRunsResponse {
  items: AnswerRun[];
}

interface EvaluationRun {
  id: string;
  dataset: string;
  regression_classification: string;
  security_regression: boolean;
}

interface EvaluationRunsResponse {
  items: EvaluationRun[];
}

export interface AttentionItem {
  id: string;
  severity: "critical" | "warning";
  title: string;
  detail: string;
  href?: string;
}

interface DashboardState {
  overview: AdminOverviewMetrics | null;
  attention: AttentionItem[];
  loading: boolean;
  error: string | null;
}

export function useAdminDashboard(): DashboardState {
  const { organization } = useSelectedOrganization();
  const [overview, setOverview] = useState<AdminOverviewMetrics | null>(null);
  const [failedDocuments, setFailedDocuments] = useState<FailedDocument[]>([]);
  const [answerRuns, setAnswerRuns] = useState<AnswerRun[]>([]);
  const [evaluationRuns, setEvaluationRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!organization) {
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      fetchAdminResource<AdminOverviewMetrics>(
        organization.id,
        "/metrics/overview",
        controller.signal,
      ),
      fetchAdminResource<FailedDocumentsResponse>(
        organization.id,
        "/document-versions/failed?limit=5",
        controller.signal,
      ),
      fetchAdminResource<AnswerRunsResponse>(
        organization.id,
        "/answer-runs?limit=50",
        controller.signal,
      ),
      fetchAdminResource<EvaluationRunsResponse>(
        organization.id,
        "/evaluation-runs?limit=50",
        controller.signal,
      ),
    ])
      .then(([metrics, documents, answers, evaluations]) => {
        setOverview(metrics);
        setFailedDocuments(documents.items);
        setAnswerRuns(answers.items);
        setEvaluationRuns(evaluations.items);
      })
      .catch((requestError: unknown) => {
        if (
          requestError instanceof DOMException &&
          requestError.name === "AbortError"
        ) {
          return;
        }
        setError("The organization dashboard could not be loaded.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [organization]);

  const attention = useMemo(
    () =>
      buildAttentionItems(
        overview,
        failedDocuments,
        answerRuns,
        evaluationRuns,
      ),
    [overview, failedDocuments, answerRuns, evaluationRuns],
  );

  return { overview, attention, loading, error };
}

function buildAttentionItems(
  overview: AdminOverviewMetrics | null,
  failedDocuments: FailedDocument[],
  answerRuns: AnswerRun[],
  evaluationRuns: EvaluationRun[],
): AttentionItem[] {
  const items: AttentionItem[] = failedDocuments.map((document) => ({
    id: `document-${document.version_id}`,
    severity: "warning",
    title: `Ingestion failed: ${document.document_title}`,
    detail:
      document.safe_failure_message ??
      document.failure_code ??
      "Document ingestion failed.",
    href: `/admin/documents/${document.document_id}`,
  }));

  items.push(
    ...answerRuns
      .filter((run) => run.status === "failed")
      .slice(0, 5)
      .map((run) => ({
        id: `answer-${run.id}`,
        severity: "warning" as const,
        title: "Answer generation failed",
        detail: run.failure_code ?? "The answer run did not complete.",
        href: `/admin/answers/${run.id}`,
      })),
  );

  items.push(
    ...evaluationRuns
      .filter((run) => run.regression_classification !== "none")
      .slice(0, 5)
      .map((run) => ({
        id: `evaluation-${run.id}`,
        severity: run.security_regression
          ? ("critical" as const)
          : ("warning" as const),
        title: run.security_regression
          ? `Security regression: ${run.dataset}`
          : `Quality regression: ${run.dataset}`,
        detail: `Classification: ${run.regression_classification.replaceAll(
          "_",
          " ",
        )}.`,
        href: `/admin/evaluations/${run.id}`,
      })),
  );

  if (!overview) {
    return sortAttentionItems(items);
  }

  if (overview.authorization_leakage_count > 0) {
    items.unshift({
      id: "authorization-leakage",
      severity: "critical",
      title: "Authorization leakage detected",
      detail: `${overview.authorization_leakage_count} evaluation cases reported leakage.`,
      href: "/admin/evaluations",
    });
  }

  const averageCost =
    overview.total_queries > 0
      ? overview.total_estimated_cost_microusd / overview.total_queries
      : 0;
  if (averageCost > COST_ALERT_THRESHOLD_MICROUSD_PER_QUERY) {
    items.push({
      id: "cost-spike",
      severity: "warning",
      title: "Unusual cost detected",
      detail: `Average cost exceeded the configured ${formatCost(
        COST_ALERT_THRESHOLD_MICROUSD_PER_QUERY,
      )} per-query threshold.`,
    });
  }

  if (overview.p95_total_latency_ms > LATENCY_ALERT_THRESHOLD_MS) {
    items.push({
      id: "latency-spike",
      severity: "warning",
      title: "Unusual latency detected",
      detail: `p95 answer latency exceeded ${formatDuration(LATENCY_ALERT_THRESHOLD_MS)}.`,
    });
  }

  return sortAttentionItems(items);
}

function sortAttentionItems(items: AttentionItem[]): AttentionItem[] {
  return [...items].sort((left, right) => {
    const priority = { critical: 0, warning: 1 };
    return priority[left.severity] - priority[right.severity];
  });
}

export function formatCost(microusd: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(microusd / 1_000_000);
}

export function formatDuration(milliseconds: number): string {
  return milliseconds >= 1_000
    ? `${(milliseconds / 1_000).toFixed(1)}s`
    : `${Math.round(milliseconds)}ms`;
}
