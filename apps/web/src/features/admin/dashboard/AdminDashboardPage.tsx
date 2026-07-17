import { Link } from "react-router-dom";

import { AdminPage } from "../shared/AdminPage";
import {
  formatCost,
  formatDuration,
  useAdminDashboard,
  type AttentionItem,
} from "./useAdminDashboard";

const integerFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

function formatPercentage(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

interface Metric {
  label: string;
  value: string;
  tone?: "danger" | "default";
}

function MetricCard({ label, value, tone = "default" }: Metric) {
  return (
    <article className={`metric-card metric-card-${tone}`}>
      <span>{label}</span>
      <strong className="metric-value">{value}</strong>
    </article>
  );
}

function AttentionRow({ item }: { item: AttentionItem }) {
  const content = (
    <>
      <div className="attention-item-heading">
        <strong>{item.title}</strong>
        <span className={`severity-badge severity-${item.severity}`}>
          {item.severity}
        </span>
      </div>
      <p>{item.detail}</p>
    </>
  );

  return (
    <li className={`attention-item attention-${item.severity}`}>
      {item.href ? (
        <Link aria-label={`${item.title}: ${item.detail}`} to={item.href}>
          {content}
        </Link>
      ) : (
        <div>{content}</div>
      )}
    </li>
  );
}

export function AdminDashboardPage() {
  const { overview, attention, loading, error } = useAdminDashboard();
  const placeholder = loading ? "Loading…" : "—";
  const totalTokens = overview
    ? overview.total_input_tokens + overview.total_output_tokens
    : null;

  const metricRows: Metric[][] = [
    [
      {
        label: "Queries",
        value: overview
          ? integerFormatter.format(overview.total_queries)
          : placeholder,
      },
      {
        label: "Answer rate",
        value: overview ? formatPercentage(overview.answer_rate) : placeholder,
      },
      {
        label: "Abstention rate",
        value: overview
          ? formatPercentage(overview.abstention_rate)
          : placeholder,
      },
      {
        label: "Failure rate",
        value: overview ? formatPercentage(overview.failure_rate) : placeholder,
        tone: overview && overview.failure_rate > 0 ? "danger" : "default",
      },
    ],
    [
      {
        label: "p95 retrieval latency",
        value: overview
          ? formatDuration(overview.p95_retrieval_latency_ms)
          : placeholder,
      },
      {
        label: "p95 answer latency",
        value: overview
          ? formatDuration(overview.p95_generation_latency_ms)
          : placeholder,
      },
      {
        label: "Total token usage",
        value:
          totalTokens === null
            ? placeholder
            : integerFormatter.format(totalTokens),
      },
      {
        label: "Estimated cost",
        value: overview
          ? formatCost(overview.total_estimated_cost_microusd)
          : placeholder,
      },
    ],
    [
      {
        label: "Ready documents",
        value: overview
          ? integerFormatter.format(overview.documents_ready)
          : placeholder,
      },
      {
        label: "Processing documents",
        value: overview
          ? integerFormatter.format(overview.documents_processing)
          : placeholder,
      },
      {
        label: "Failed documents",
        value: overview
          ? integerFormatter.format(overview.documents_failed)
          : placeholder,
        tone: overview && overview.documents_failed > 0 ? "danger" : "default",
      },
      {
        label: "Evaluation pass rate",
        value: overview
          ? formatPercentage(overview.evaluation_pass_rate)
          : placeholder,
      },
    ],
  ];

  return (
    <AdminPage
      eyebrow="Operations"
      title="System overview"
      description="Inspect production health within the selected organization."
    >
      {error ? (
        <div className="dashboard-error" role="alert">
          <strong>Dashboard unavailable</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <div className="dashboard-metrics" aria-busy={loading}>
        {metricRows.map((row, rowIndex) => (
          <div className="metric-row" key={`metric-row-${rowIndex + 1}`}>
            {row.map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </div>
        ))}
      </div>

      <section className="attention-section" aria-labelledby="attention-title">
        <div className="attention-header">
          <div>
            <p className="eyebrow">Needs review</p>
            <h3 id="attention-title">Attention</h3>
          </div>
          <span>{attention.length} active</span>
        </div>

        {loading ? (
          <p className="attention-empty">Loading operational issues…</p>
        ) : attention.length === 0 ? (
          <p className="attention-empty">
            No ingestion failures, answer failures, regressions, or threshold
            alerts need attention.
          </p>
        ) : (
          <ul className="attention-list">
            {attention.map((item) => (
              <AttentionRow item={item} key={item.id} />
            ))}
          </ul>
        )}
      </section>
    </AdminPage>
  );
}
