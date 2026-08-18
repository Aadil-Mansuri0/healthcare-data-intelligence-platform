import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT Bearer token if present
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// ─── 1. Drugs & KPIs ────────────────────────────────────────────────────────
export interface DrugSummaryItem {
  GNRC_NAME: string;
  BRND_NAME: string;
  YEAR: number;
  IS_GENERIC: number | boolean;
  TOTAL_CLAIMS: number;
  TOTAL_COST_USD: number;
  TOTAL_BENEFICIARIES: number;
  AVG_COST_PER_CLAIM: number;
  UNIQUE_PRESCRIBERS: number;
  COST_RANK: number;
}

export const getDrugSummary = (year?: number, limit = 50): Promise<{ data: DrugSummaryItem[] }> =>
  api.get("/api/drugs/summary", { params: { year, limit } }).then((r) => r.data);

export const getGenericVsBrand = (year?: number) =>
  api.get("/api/drugs/generic-vs-brand", { params: { year } }).then((r) => r.data);

export const getDrugDetail = (drugName: string) =>
  api.get(`/api/drugs/${encodeURIComponent(drugName)}`).then((r) => r.data);

// ─── 2. Prescribers & State KPIs ────────────────────────────────────────────
export interface StateKPIItem {
  STATE_ABRVTN: string;
  YEAR: number;
  TOTAL_CLAIMS: number;
  TOTAL_COST_USD: number;
  TOTAL_BENEFICIARIES: number;
  TOTAL_PRESCRIBERS: number;
  UNIQUE_DRUGS: number;
  AVG_COST_PER_CLAIM: number;
  COST_PER_BENEFICIARY: number;
  NATIONAL_RANK: number;
  PAIN_SPECIALTY_CLAIMS: number;
}

export interface PrescriberItem {
  PRSCRBR_NPI: number;
  YEAR: number;
  PRSCRBR_LAST_ORG_NAME: string;
  PRSCRBR_FIRST_NAME: string;
  PRSCRBR_STATE_ABRVTN: string;
  PRSCRBR_TYPE: string;
  PRSCRBR_CITY: string;
  TOTAL_CLAIMS: number;
  TOTAL_COST_USD: number;
  TOTAL_BENEFICIARIES: number;
  UNIQUE_DRUGS_PRESCRIBED: number;
  GENERIC_RATE: number;
  STATE_RANK: number;
}

export const getTopPrescribers = (state?: string, year?: number, limit = 100): Promise<{ data: PrescriberItem[] }> =>
  api.get("/api/prescribers/top", { params: { state, year, limit } }).then((r) => r.data);

export const getStateKPI = (year?: number): Promise<{ data: StateKPIItem[] }> =>
  api.get("/api/prescribers/state-kpi", { params: { year } }).then((r) => r.data);

// ─── 3. AI Services (Insights, Reports, Quality, Recommendations) ───────────
export interface AIInsightsResponse {
  year?: number;
  insights: string[];
  snapshot: any;
  source?: string;
}

export const getAIInsights = (year?: number): Promise<AIInsightsResponse> =>
  api.get("/api/ai/insights", { params: { year } }).then((r) => r.data);

export interface AIReportResponse {
  period: string;
  start_date: string;
  end_date: string;
  markdown: string;
  data: any;
}

export const generatePeriodicReport = (period: "weekly" | "monthly", year?: number): Promise<AIReportResponse> =>
  api.get(`/api/ai/reports/${period}`, { params: { year } }).then((r) => r.data);

export interface AIQualityCheckResponse {
  year: number;
  status: "healthy" | "issues_found";
  anomalies: any[];
  duplicates: any[];
  ai_explanation: string;
}

export const getAIQualityCheck = (year = 2024): Promise<AIQualityCheckResponse> =>
  api.get("/api/ai/data-quality-check", { params: { year } }).then((r) => r.data);

export interface RecommendationItem {
  recommendation: string;
  estimated_impact: string;
  priority: "high" | "medium" | "low";
}

export interface AIRecommendationsResponse {
  year: number;
  recommendations: RecommendationItem[];
  total_potential_savings_usd: number;
  supporting_data: any;
}

export const getAIRecommendations = (year = 2024): Promise<AIRecommendationsResponse> =>
  api.get("/api/ai/recommendations", { params: { year } }).then((r) => r.data);

// ─── 4. RAG Assistant & NL2SQL ──────────────────────────────────────────────
export interface RAGChatResponse {
  question: string;
  resolved_question: string;
  generated_sql?: string;
  row_count?: number;
  results?: any[];
  summary: string;
  from_cache: boolean;
  cache_similarity?: number;
  rag_retrieval_stats?: {
    knowledge_chunks: number;
    schema_chunks: number;
    query_examples: number;
  };
}

export const ragChat = (question: string, sessionId = "default"): Promise<RAGChatResponse> =>
  api.post("/api/rag/chat", { question, session_id: sessionId }).then((r) => r.data);

export const getSuggestedQuestions = (): Promise<{ suggestions: string[] }> =>
  api.get("/api/ai/suggested-questions").then((r) => r.data);

export const getChatHistory = (sessionId = "default") =>
  api.get(`/api/rag/chat/history/${sessionId}`).then((r) => r.data);

export const clearChatHistory = (sessionId = "default") =>
  api.delete(`/api/rag/chat/history/${sessionId}`).then((r) => r.data);

// ─── 5. Platform Intelligence (Lineage, Data Quality, Streaming, Compliance) ─
export interface LineageGraphResponse {
  pipeline: string;
  orchestrator: string;
  openlineage_version: string;
  nodes: Array<{
    id: string;
    name: string;
    layer: string;
    category: string;
    status: string;
    engine: string;
    lastSync: string;
    [key: string]: any;
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: string;
  }>;
  summary: {
    total_nodes: number;
    total_edges: number;
    healthy_count: number;
    pipeline_state: string;
    last_dag_run: string;
  };
}

export const getLineageGraph = (): Promise<LineageGraphResponse> =>
  api.get("/api/platform/lineage").then((r) => r.data);

export interface DataQualityReportResponse {
  overall_health_score: number;
  status: string;
  last_validated: string;
  suites: Array<{
    suite_name: string;
    layer: string;
    total_tests: number;
    passed: number;
    failed: number;
    status: string;
    assertions: Array<{
      name: string;
      status: string;
      observed: string;
    }>;
  }>;
  statistics: {
    total_assertions: number;
    passed_assertions: number;
    failed_assertions: number;
    records_evaluated: string;
    anomalies_detected: number;
  };
}

export const getDataQualityReport = (): Promise<DataQualityReportResponse> =>
  api.get("/api/platform/data-quality").then((r) => r.data);

export interface StreamingEvent {
  claim_id: string;
  prscrbr_npi: number;
  prscrbr_state_abrvtn: string;
  drug_name: string;
  is_opioid: boolean;
  cost_usd: number;
  days_supply: number;
  timestamp: string;
  topic: string;
}

export const getStreamingClaims = (count = 15): Promise<{
  stream_status: string;
  partition_count: number;
  throughput_rate: string;
  events: StreamingEvent[];
}> => api.get("/api/platform/streaming/events", { params: { count } }).then((r) => r.data);

export interface OpioidAlert {
  alert_id: string;
  alert_type: string;
  prscrbr_npi: number;
  prscrbr_name: string;
  prscrbr_state_abrvtn: string;
  specialty: string;
  claim_count_in_window: number;
  threshold: number;
  window_minutes: number;
  severity: "HIGH" | "MEDIUM" | "LOW";
  detected_at: string;
  status: string;
}

export const getOpioidAlerts = (): Promise<{
  active_window_minutes: number;
  alert_threshold: number;
  total_active_alerts: number;
  alerts: OpioidAlert[];
}> => api.get("/api/platform/streaming/alerts").then((r) => r.data);

export const testPHIRedaction = (text: string): Promise<{
  original_text: string;
  redacted_text: string;
  findings_by_category: Record<string, number>;
  total_phi_patterns_detected: number;
  is_safe_for_llm: boolean;
  safe_harbor_standards_covered: number;
}> => api.post("/api/platform/compliance/test-redaction", { text }).then((r) => r.data);

export const getComplianceAuditLogs = (limit = 50): Promise<{
  retention_policy: string;
  audit_table: string;
  total_logged: number;
  records: Array<{
    id: number;
    username: string;
    path: string;
    method: string;
    status_code: number;
    duration_ms: number;
    client_ip: string;
    accessed_at: string;
  }>;
}> => api.get("/api/platform/compliance/audit-logs", { params: { limit } }).then((r) => r.data);

export const getPlatformUsers = (): Promise<{
  total_users: number;
  roles_available: string[];
  users: Array<{
    username: string;
    email: string;
    full_name: string;
    role: string;
    status: string;
    created_at: string;
    last_login: string;
  }>;
}> => api.get("/api/platform/users").then((r) => r.data);

export const getSystemHealth = () =>
  api.get("/api/platform/system-health").then((r) => r.data);
