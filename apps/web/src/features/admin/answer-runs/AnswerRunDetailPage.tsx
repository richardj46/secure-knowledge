import { useMemo, useState, type FormEvent } from "react";

import { AdminPage } from "../shared/AdminPage";
import { useRequiredRouteParam } from "../shared/useRequiredRouteParam";
import {
  useAnswerRunDetail,
  type AnswerCitationInspection,
  type AnswerReviewInput,
} from "./useAnswerRunDetail";

const numberFormatter = new Intl.NumberFormat("en-US");

function formatDuration(milliseconds: number | null): string {
  if (milliseconds === null) {
    return "—";
  }
  return milliseconds >= 1_000
    ? `${(milliseconds / 1_000).toFixed(2)}s`
    : `${milliseconds}ms`;
}

function formatCost(microusd: number | null): string {
  if (microusd === null) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(microusd / 1_000_000);
}

function formatConfidence(confidence: number | null): string {
  return confidence === null ? "—" : `${Math.round(confidence * 100)}%`;
}

function formatTokenBreakdown(
  inputTokens: number | null,
  outputTokens: number | null,
): string {
  if (inputTokens === null) {
    return "—";
  }
  return `${numberFormatter.format(inputTokens)} / ${numberFormatter.format(
    outputTokens ?? 0,
  )}`;
}

function humanize(value: string | null): string {
  if (!value) {
    return "—";
  }
  return value.replaceAll("_", " ");
}

interface ClaimGroup {
  claim: string;
  citations: AnswerCitationInspection[];
}

function groupCitationsByClaim(
  citations: AnswerCitationInspection[],
): ClaimGroup[] {
  const groups = new Map<string, AnswerCitationInspection[]>();
  for (const citation of citations) {
    const claim = citation.claim?.trim() || "Claim text was not recorded.";
    groups.set(claim, [...(groups.get(claim) ?? []), citation]);
  }
  return [...groups].map(([claim, groupedCitations]) => ({
    claim,
    citations: groupedCitations,
  }));
}

function CitationCard({ citation }: { citation: AnswerCitationInspection }) {
  return (
    <article className="citation-card">
      <header>
        <div>
          <strong>{citation.document_title}</strong>
          <span>
            Page {citation.page_number ?? "—"} · Version{" "}
            {citation.document_version}
          </span>
        </div>
        <span>Citation {citation.citation_index}</span>
      </header>
      {citation.section_title ? <h5>{citation.section_title}</h5> : null}
      <p>{citation.chunk_content}</p>
      <code>{citation.chunk_id}</code>
    </article>
  );
}

function optionalScore(value: string): number | null {
  return value === "" ? null : Number(value);
}

export function AnswerRunDetailPage() {
  const answerRunId = useRequiredRouteParam("answerRunId");
  const {
    run,
    review,
    loading,
    submittingReview,
    error,
    reviewError,
    submitReview,
  } = useAnswerRunDetail(answerRunId);
  const [groundednessScore, setGroundednessScore] = useState("");
  const [relevanceScore, setRelevanceScore] = useState("");
  const [citationScore, setCitationScore] = useState("");
  const [notes, setNotes] = useState("");
  const claimGroups = useMemo(
    () => groupCitationsByClaim(run?.citations ?? []),
    [run?.citations],
  );
  const totalTokens =
    run?.input_tokens === null || run?.input_tokens === undefined
      ? null
      : run.input_tokens + (run.output_tokens ?? 0);

  function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nativeEvent = event.nativeEvent as SubmitEvent;
    const submitter = nativeEvent.submitter as HTMLButtonElement | null;
    const status = submitter?.value as AnswerReviewInput["status"] | undefined;
    if (!status) {
      return;
    }

    void submitReview({
      status,
      groundedness_score: optionalScore(groundednessScore),
      relevance_score: optionalScore(relevanceScore),
      citation_score: optionalScore(citationScore),
      notes: notes.trim() || null,
    });
  }

  return (
    <AdminPage
      eyebrow="Answer trace"
      title="Answer review"
      description="Compare generated claims with their approved evidence and record a human review."
      resourceId={answerRunId}
    >
      {error ? (
        <div className="dashboard-error" role="alert">
          <strong>Answer unavailable</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <section className="answer-review-layout" aria-busy={loading}>
        <div className="answer-review-main">
          <section className="trace-section">
            <p className="eyebrow">Question</p>
            <h3 className="answer-question">{run?.question ?? "Loading…"}</h3>

            <div className="answer-output">
              <p className="eyebrow">Generated answer</p>
              <p>
                {run?.answer ??
                  (loading ? "Loading…" : "No answer was generated.")}
              </p>
            </div>

            <dl className="answer-metadata-grid">
              <div>
                <dt>Answerability</dt>
                <dd>{humanize(run?.answerability ?? null)}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{formatConfidence(run?.confidence ?? null)}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>{run?.model ?? "—"}</dd>
              </div>
              <div>
                <dt>Prompt version</dt>
                <dd>{run?.prompt_version ?? "—"}</dd>
              </div>
              <div>
                <dt>Total latency</dt>
                <dd>{formatDuration(run?.total_latency_ms ?? null)}</dd>
              </div>
              <div>
                <dt>Token usage</dt>
                <dd>
                  {totalTokens === null
                    ? "—"
                    : `${numberFormatter.format(totalTokens)} total`}
                </dd>
              </div>
              <div>
                <dt>Input / output tokens</dt>
                <dd>
                  {formatTokenBreakdown(
                    run?.input_tokens ?? null,
                    run?.output_tokens ?? null,
                  )}
                </dd>
              </div>
              <div>
                <dt>Estimated cost</dt>
                <dd>{formatCost(run?.estimated_cost_microusd ?? null)}</dd>
              </div>
            </dl>
          </section>

          <section className="trace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Evidence</p>
                <h3>Claims and citations</h3>
              </div>
              <span>{claimGroups.length} claims</span>
            </div>

            {claimGroups.length ? (
              <div className="claim-list">
                {claimGroups.map((group, index) => (
                  <article className="claim-card" key={group.claim}>
                    <header>
                      <span>Claim {index + 1}</span>
                      <h4>{group.claim}</h4>
                    </header>
                    <div className="claim-citations">
                      {group.citations.map((citation) => (
                        <CitationCard
                          citation={citation}
                          key={`${citation.citation_index}-${citation.claim_index}`}
                        />
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="muted-copy">
                This answer has no recorded claim-level citations.
              </p>
            )}
          </section>
        </div>

        <aside className="review-panel">
          <div>
            <p className="eyebrow">Human review</p>
            <h3>Review controls</h3>
            <p>Scores use a range from 0 to 1.</p>
          </div>

          <form onSubmit={handleReview}>
            <label>
              Groundedness score
              <input
                max="1"
                min="0"
                onChange={(event) => setGroundednessScore(event.target.value)}
                placeholder="0.00–1.00"
                step="0.01"
                type="number"
                value={groundednessScore}
              />
            </label>
            <label>
              Relevance score
              <input
                max="1"
                min="0"
                onChange={(event) => setRelevanceScore(event.target.value)}
                placeholder="0.00–1.00"
                step="0.01"
                type="number"
                value={relevanceScore}
              />
            </label>
            <label>
              Citation score
              <input
                max="1"
                min="0"
                onChange={(event) => setCitationScore(event.target.value)}
                placeholder="0.00–1.00"
                step="0.01"
                type="number"
                value={citationScore}
              />
            </label>
            <label>
              Notes
              <textarea
                maxLength={5000}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Record evidence gaps or required changes."
                rows={6}
                value={notes}
              />
            </label>

            {reviewError ? (
              <p className="form-message form-error" role="alert">
                {reviewError}
              </p>
            ) : null}
            {review ? (
              <p className="form-message form-success" role="status">
                Review saved as {humanize(review.status)}.
              </p>
            ) : null}

            <div className="review-actions">
              <button
                className="review-approve"
                disabled={submittingReview || loading || !run}
                type="submit"
                value="approved"
              >
                Approve
              </button>
              <button
                className="review-reject"
                disabled={submittingReview || loading || !run}
                type="submit"
                value="rejected"
              >
                Reject
              </button>
              <button
                className="review-revision"
                disabled={submittingReview || loading || !run}
                type="submit"
                value="needs_revision"
              >
                Needs revision
              </button>
            </div>
          </form>
        </aside>
      </section>
    </AdminPage>
  );
}
