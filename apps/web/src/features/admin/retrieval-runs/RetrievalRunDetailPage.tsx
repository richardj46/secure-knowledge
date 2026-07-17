import { useState } from "react";

import { AdminPage } from "../shared/AdminPage";
import { useRequiredRouteParam } from "../shared/useRequiredRouteParam";
import {
  useRetrievalRunDetail,
  type NeighboringChunk,
  type RetrievalTraceResult,
} from "./useRetrievalRunDetail";

const permissionLabels: Record<string, string> = {
  organization_admin: "Organization administrator",
  document_owner: "Document owner",
  organization_visibility: "Organization visibility",
  workspace_membership: "Workspace membership",
  direct_user_grant: "Direct user grant",
  group_grant: "Group grant",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function formatDuration(milliseconds: number): string {
  return milliseconds >= 1_000
    ? `${(milliseconds / 1_000).toFixed(2)}s`
    : `${milliseconds}ms`;
}

function displayRank(rank: number | null): string {
  return rank === null ? "—" : String(rank);
}

function permissionExplanation(result: RetrievalTraceResult): string {
  if (!result.permission_path) {
    return "No permission path was recorded for this result.";
  }

  const label =
    permissionLabels[result.permission_path] ?? result.permission_path;
  const source = result.permission_source_id
    ? ` Source: ${result.permission_source_id}.`
    : "";
  return `${label} allowed access under policy ${result.authorization_policy_version}.${source}`;
}

function NeighborCard({ chunk }: { chunk: NeighboringChunk }) {
  return (
    <article className="neighbor-card">
      <div>
        <strong>Chunk {chunk.chunk_index}</strong>
        <span>Page {chunk.page_number ?? "—"}</span>
      </div>
      <p>{chunk.content}</p>
    </article>
  );
}

function PassageDrawer({
  result,
  onClose,
}: {
  result: RetrievalTraceResult;
  onClose: () => void;
}) {
  return (
    <aside
      aria-labelledby="passage-drawer-title"
      className="passage-drawer"
      role="dialog"
    >
      <header className="drawer-header">
        <div>
          <p className="eyebrow">Retrieved passage</p>
          <h3 id="passage-drawer-title">{result.document_title}</h3>
        </div>
        <button aria-label="Close passage drawer" onClick={onClose} type="button">
          Close
        </button>
      </header>

      <dl className="drawer-metadata">
        <div>
          <dt>Document ID</dt>
          <dd>{result.document_id}</dd>
        </div>
        <div>
          <dt>Workspace ID</dt>
          <dd>{result.workspace_id}</dd>
        </div>
        <div>
          <dt>File</dt>
          <dd>{result.document_filename}</dd>
        </div>
        <div>
          <dt>Version</dt>
          <dd>
            {result.document_version_number} ({result.document_version_id})
          </dd>
        </div>
        <div>
          <dt>Page</dt>
          <dd>{result.page_number ?? "—"}</dd>
        </div>
        <div>
          <dt>Section</dt>
          <dd>{result.section_title ?? "—"}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{result.retrieval_sources.join(" + ") || "—"}</dd>
        </div>
        <div>
          <dt>MIME type</dt>
          <dd>{result.document_mime_type}</dd>
        </div>
        <div>
          <dt>Chunk ID</dt>
          <dd>{result.chunk_id}</dd>
        </div>
      </dl>

      <section className="drawer-section">
        <h4>Chunk text</h4>
        <p className="passage-content">{result.content}</p>
      </section>

      <section className="drawer-section permission-explanation">
        <h4>Permission explanation</h4>
        <p>{permissionExplanation(result)}</p>
      </section>

      <section className="drawer-section">
        <h4>Authorized neighboring chunks</h4>
        {result.neighboring_chunks.length ? (
          <div className="neighbor-list">
            {result.neighboring_chunks.map((chunk) => (
              <NeighborCard chunk={chunk} key={chunk.chunk_id} />
            ))}
          </div>
        ) : (
          <p className="muted-copy">No authorized neighboring chunks.</p>
        )}
      </section>
    </aside>
  );
}

export function RetrievalRunDetailPage() {
  const runId = useRequiredRouteParam("runId");
  const {
    run,
    results,
    loading,
    loadingMore,
    hasMore,
    error,
    loadMore,
  } = useRetrievalRunDetail(runId);
  const [selectedResult, setSelectedResult] =
    useState<RetrievalTraceResult | null>(null);

  return (
    <AdminPage
      eyebrow="Retrieval trace"
      title="Retrieval run detail"
      description="Compare vector, keyword, fusion, and authorization results."
      resourceId={runId}
    >
      {error ? (
        <div className="dashboard-error" role="alert">
          <strong>Trace unavailable</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <section className="trace-section" aria-busy={loading}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Request</p>
            <h3>Request summary</h3>
          </div>
        </div>
        <dl className="summary-grid">
          <div>
            <dt>User</dt>
            <dd>{run?.user_id ?? "Loading…"}</dd>
          </div>
          <div>
            <dt>Organization</dt>
            <dd>{run?.organization_id ?? "Loading…"}</dd>
          </div>
          <div>
            <dt>Workspace filters</dt>
            <dd className="workspace-filter-list">
              {run?.workspace_ids.length
                ? run.workspace_ids.map((workspaceId) => (
                    <code key={workspaceId}>{workspaceId}</code>
                  ))
                : "All authorized workspaces"}
            </dd>
          </div>
          <div>
            <dt>Time</dt>
            <dd>{run ? formatDate(run.created_at) : "Loading…"}</dd>
          </div>
          <div className="summary-question">
            <dt>Question</dt>
            <dd>{run?.query ?? "Loading…"}</dd>
          </div>
          <div>
            <dt>Total duration</dt>
            <dd>{run ? formatDuration(run.total_duration_ms) : "Loading…"}</dd>
          </div>
        </dl>
      </section>

      <section className="trace-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Ranking</p>
            <h3>Candidate pipeline</h3>
          </div>
        </div>
        <div className="pipeline-grid">
          <article>
            <span>Vector candidates</span>
            <strong>{run?.vector_candidate_count ?? "—"}</strong>
          </article>
          <article>
            <span>Keyword candidates</span>
            <strong>{run?.keyword_candidate_count ?? "—"}</strong>
          </article>
          <article>
            <span>Fused results</span>
            <strong>{run?.fused_result_count ?? "—"}</strong>
          </article>
          <article>
            <span>Selected context</span>
            <strong>{run?.selected_result_count ?? "—"}</strong>
          </article>
        </div>
      </section>

      <section className="trace-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Evidence</p>
            <h3>Results</h3>
          </div>
          <span>{results.length} results</span>
        </div>
        <div className="result-table-wrap">
          <table className="result-table">
            <thead>
              <tr>
                <th>Final rank</th>
                <th>Document</th>
                <th>Page</th>
                <th>Vector rank</th>
                <th>Keyword rank</th>
                <th>Score</th>
                <th>Permission path</th>
                <th>Selected</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr
                  className="result-row"
                  key={result.chunk_id}
                  onClick={() => setSelectedResult(result)}
                >
                  <td>{result.final_rank}</td>
                  <td>
                    <button
                      className="document-cell-button"
                      onClick={() => setSelectedResult(result)}
                      type="button"
                    >
                      <strong>{result.document_title}</strong>
                      <span>{result.section_title ?? "View passage"}</span>
                    </button>
                  </td>
                  <td>{result.page_number ?? "—"}</td>
                  <td>{displayRank(result.vector_rank)}</td>
                  <td>{displayRank(result.keyword_rank)}</td>
                  <td>{result.fused_score.toFixed(4)}</td>
                  <td>
                    {result.permission_path
                      ? permissionLabels[result.permission_path] ??
                        result.permission_path
                      : "Not recorded"}
                  </td>
                  <td>
                    <span
                      className={`selection-badge selection-${
                        result.selected_for_context ? "yes" : "no"
                      }`}
                    >
                      {result.selected_for_context ? "Yes" : "No"}
                    </span>
                  </td>
                </tr>
              ))}
              {!loading && results.length === 0 ? (
                <tr>
                  <td className="table-empty" colSpan={8}>
                    This retrieval run returned no results.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        {hasMore ? (
          <button
            className="load-more-button"
            disabled={loadingMore}
            onClick={() => void loadMore()}
            type="button"
          >
            {loadingMore ? "Loading…" : "Load more results"}
          </button>
        ) : null}
      </section>

      {selectedResult ? (
        <PassageDrawer
          onClose={() => setSelectedResult(null)}
          result={selectedResult}
        />
      ) : null}
    </AdminPage>
  );
}
