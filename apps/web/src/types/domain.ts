export type ModuleStatus = "planned" | "active" | "ready";

export interface ProjectModule {
  id: string;
  name: string;
  status: ModuleStatus;
  description: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface CaseSummary {
  id: string;
  anonymous_code: string;
  age_group?: string | null;
  gender?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CaseCreatePayload {
  age_group?: string;
  gender?: string;
  notes?: string;
}

export interface CollectionContext {
  lighting_condition?: string | null;
  container_type?: string | null;
  background_type?: string | null;
  resting_minutes?: number | null;
  is_morning_sample?: boolean | null;
  interference_note?: string | null;
}

export interface SymptomContext {
  chief_complaint?: string | null;
  duration?: string | null;
  sleep?: string | null;
  diet?: string | null;
  water_intake?: string | null;
  urination?: string | null;
  stool?: string | null;
  medication?: string | null;
}

export interface QualityIssue {
  type: string;
  severity: "low" | "medium" | "high" | string;
  message: string;
  source?: string;
}

export interface GemmaQualityReview {
  status: "completed" | "skipped" | "failed" | string;
  provider: string;
  reason?: string;
  sample_visible?: boolean;
  urine_region_complete?: boolean;
  sample_region_size?: string;
  background?: string;
  reflection_risk?: string;
  blur_risk?: string;
  collection_quality?: "good" | "acceptable" | "poor" | "unknown" | string;
  confidence?: "low" | "medium" | "high" | string;
  issues?: QualityIssue[];
  recommendations?: string[];
  raw_excerpt?: string;
}

export interface QualityScoreSources {
  rule_cv_score: number;
  gemma_penalty: number;
  fusion_method: string;
}

export interface ImageQualityResult {
  quality_score: number;
  usable: boolean;
  issues: QualityIssue[];
  recommendations: string[];
  metrics?: Record<string, unknown>;
  gemma_review?: GemmaQualityReview;
  score_sources?: QualityScoreSources;
  rule_cv_result?: {
    quality_score: number;
    usable: boolean;
    issues: QualityIssue[];
  };
}

export interface VisualFeatureItem {
  label: string;
  confidence: number;
  evidence: string;
  source?: string;
  metrics?: Record<string, unknown>;
  rule_label?: string;
  gemma_label?: string;
}

export interface GemmaFeatureReview {
  status: "completed" | "skipped" | "failed" | string;
  provider: string;
  reason?: string;
  features?: Record<string, VisualFeatureItem>;
  summary?: string;
  recommendations?: string[];
  raw_excerpt?: string;
}

export interface VisualFeaturesResult {
  status: "completed" | "failed" | string;
  features: Record<string, VisualFeatureItem>;
  summary?: string;
  recommendations?: string[];
  metrics?: Record<string, unknown>;
  rule_cv_result?: Record<string, unknown>;
  gemma_review?: GemmaFeatureReview;
}

export interface SymptomMention {
  label: string;
  category: string;
  evidence: string;
}

export interface SymptomInterferenceFactor {
  label: string;
  evidence: string;
}

export interface StructuredSymptomProfile {
  raw_text: string;
  chief_complaint: string;
  duration?: string | null;
  sleep?: string | null;
  diet?: string | null;
  water_intake?: string | null;
  medication?: string | null;
  urination?: string | null;
  stool?: string | null;
  appetite_digestive?: string | null;
  temperature?: string | null;
  pain?: string | null;
  general?: string | null;
  symptom_tags: string[];
  mentions: SymptomMention[];
  interference_factors: SymptomInterferenceFactor[];
  structured_input?: SymptomContext;
}

export interface SymptomProfileResult {
  status: "completed" | "skipped" | string;
  raw_text: string;
  summary: string;
  symptom_profile: StructuredSymptomProfile;
  missing_fields: string[];
  follow_up_questions: string[];
  confidence: "low" | "medium" | "high" | string;
  safety_note?: string;
}

export interface ObservationCreatePayload {
  case_id: string;
  image_path?: string | null;
  collection_context: CollectionContext;
  symptom_context?: SymptomContext;
  symptom_text?: string | null;
}

export interface ObservationUpdatePayload {
  case_id?: string;
  image_path?: string | null;
  collection_context?: CollectionContext;
  symptom_context?: SymptomContext;
  symptom_text?: string | null;
}

export interface ObservationRecord {
  id: string;
  case_id: string;
  image_path?: string | null;
  collection_context: CollectionContext;
  symptom_context: SymptomContext;
  symptom_text?: string | null;
  created_at: string;
  updated_at: string;
  quality_result?: ImageQualityResult | null;
  visual_features?: VisualFeaturesResult | null;
  symptom_profile?: SymptomProfileResult | null;
  assisted_interpretation?: Record<string, unknown> | null;
  report?: Record<string, unknown> | null;
}

export interface ImageUploadResponse {
  image_id: string;
  filename: string;
  content_type: string;
  image_path: string;
}
