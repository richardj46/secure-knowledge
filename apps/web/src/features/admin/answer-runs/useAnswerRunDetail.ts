import { useCallback, useEffect, useState } from "react";

import { useSelectedOrganization } from "../../../shared/organizations/context";
import {
  createAdminResource,
  fetchAdminResource,
} from "../shared/adminApi";

export interface AnswerCitationInspection {
  citation_index: number;
  claim_index: number;
  claim: string | null;
  chunk_id: string;
  chunk_content: string;
  document_id: string;
  document_title: string;
  page_number: number | null;
  section_title: string | null;
  document_version: number;
}

export interface AnswerRunDetail {
  id: string;
  organization_id: string;
  user_id: string;
  question: string;
  answer: string | null;
  answerability: string | null;
  confidence: number | null;
  conversation_id: string;
  retrieval_run_id: string;
  model: string;
  prompt_version: string;
  provider_request_id: string | null;
  selected_chunk_ids: string[];
  citations: AnswerCitationInspection[];
  limitations: string[];
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_microusd: number | null;
  retrieval_latency_ms: number;
  generation_latency_ms: number | null;
  total_latency_ms: number;
  status: string;
  failure_code: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AnswerReviewInput {
  status: "approved" | "rejected" | "needs_revision";
  groundedness_score: number | null;
  relevance_score: number | null;
  citation_score: number | null;
  notes: string | null;
}

export interface AnswerReview {
  id: string;
  answer_run_id: string;
  reviewer_user_id: string;
  status: string;
  groundedness_score: number | null;
  relevance_score: number | null;
  citation_score: number | null;
  notes: string | null;
  created_at: string;
}

interface AnswerRunDetailState {
  run: AnswerRunDetail | null;
  review: AnswerReview | null;
  loading: boolean;
  submittingReview: boolean;
  error: string | null;
  reviewError: string | null;
  submitReview: (input: AnswerReviewInput) => Promise<void>;
}

export function useAnswerRunDetail(answerRunId: string): AnswerRunDetailState {
  const { organization } = useSelectedOrganization();
  const [run, setRun] = useState<AnswerRunDetail | null>(null);
  const [review, setReview] = useState<AnswerReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [submittingReview, setSubmittingReview] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!organization) {
      return;
    }

    const controller = new AbortController();
    setRun(null);
    setReview(null);
    setLoading(true);
    setError(null);

    fetchAdminResource<AnswerRunDetail>(
      organization.id,
      `/answer-runs/${answerRunId}`,
      controller.signal,
    )
      .then(setRun)
      .catch((requestError: unknown) => {
        if (
          requestError instanceof DOMException &&
          requestError.name === "AbortError"
        ) {
          return;
        }
        setError("The answer trace could not be loaded.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [answerRunId, organization]);

  const submitReview = useCallback(
    async (input: AnswerReviewInput) => {
      if (!organization) {
        return;
      }

      setSubmittingReview(true);
      setReviewError(null);
      try {
        const createdReview = await createAdminResource<
          AnswerReview,
          AnswerReviewInput
        >(
          organization.id,
          `/answer-runs/${answerRunId}/reviews`,
          input,
        );
        setReview(createdReview);
      } catch {
        setReviewError("The review could not be saved.");
      } finally {
        setSubmittingReview(false);
      }
    },
    [answerRunId, organization],
  );

  return {
    run,
    review,
    loading,
    submittingReview,
    error,
    reviewError,
    submitReview,
  };
}
