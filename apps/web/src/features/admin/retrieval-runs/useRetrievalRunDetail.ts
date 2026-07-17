import { useCallback, useEffect, useState } from "react";

import { useSelectedOrganization } from "../../../shared/organizations/context";
import { fetchAdminResource } from "../shared/adminApi";

export interface RetrievalRunDetail {
  id: string;
  organization_id: string;
  user_id: string;
  query: string;
  workspace_ids: string[];
  embedding_model: string;
  retrieval_configuration_version: string;
  authorization_policy_version: string;
  vector_candidate_count: number;
  keyword_candidate_count: number;
  fused_result_count: number;
  selected_result_count: number;
  embedding_duration_ms: number | null;
  vector_duration_ms: number | null;
  keyword_duration_ms: number | null;
  fusion_duration_ms: number | null;
  total_duration_ms: number;
  created_at: string;
}

export interface NeighboringChunk {
  chunk_id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  section_title: string | null;
}

export interface RetrievalTraceResult {
  final_rank: number;
  chunk_id: string;
  chunk_index: number;
  content: string;
  document_id: string;
  document_title: string;
  document_filename: string;
  document_mime_type: string;
  workspace_id: string;
  document_version_id: string;
  document_version_number: number;
  page_number: number | null;
  section_title: string | null;
  vector_rank: number | null;
  keyword_rank: number | null;
  fused_score: number;
  retrieval_sources: string[];
  selected_for_context: boolean;
  permission_path: string | null;
  permission_source_id: string | null;
  authorization_policy_version: string;
  neighboring_chunks: NeighboringChunk[];
}

interface RetrievalDetailState {
  run: RetrievalRunDetail | null;
  results: RetrievalTraceResult[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  error: string | null;
  loadMore: () => Promise<void>;
}

interface RetrievalResultPage {
  items: RetrievalTraceResult[];
  next_cursor: string | null;
}

export function useRetrievalRunDetail(runId: string): RetrievalDetailState {
  const { organization } = useSelectedOrganization();
  const [run, setRun] = useState<RetrievalRunDetail | null>(null);
  const [results, setResults] = useState<RetrievalTraceResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!organization) {
      return;
    }

    const controller = new AbortController();
    setRun(null);
    setResults([]);
    setNextCursor(null);
    setLoading(true);
    setError(null);

    Promise.all([
      fetchAdminResource<RetrievalRunDetail>(
        organization.id,
        `/retrieval-runs/${runId}`,
        controller.signal,
      ),
      fetchAdminResource<RetrievalResultPage>(
        organization.id,
        `/retrieval-runs/${runId}/results?limit=50`,
        controller.signal,
      ),
    ])
      .then(([retrievalRun, retrievalPage]) => {
        setRun(retrievalRun);
        setResults(retrievalPage.items);
        setNextCursor(retrievalPage.next_cursor);
      })
      .catch((requestError: unknown) => {
        if (
          requestError instanceof DOMException &&
          requestError.name === "AbortError"
        ) {
          return;
        }
        setError("The retrieval trace could not be loaded.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [organization, runId]);

  const loadMore = useCallback(async () => {
    if (!organization || !nextCursor || loadingMore) {
      return;
    }
    setLoadingMore(true);
    try {
      const page = await fetchAdminResource<RetrievalResultPage>(
        organization.id,
        `/retrieval-runs/${runId}/results?limit=50&cursor=${encodeURIComponent(
          nextCursor,
        )}`,
      );
      setResults((current) => [...current, ...page.items]);
      setNextCursor(page.next_cursor);
    } catch {
      setError("More retrieval results could not be loaded.");
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, nextCursor, organization, runId]);

  return {
    run,
    results,
    loading,
    loadingMore,
    hasMore: nextCursor !== null,
    error,
    loadMore,
  };
}
