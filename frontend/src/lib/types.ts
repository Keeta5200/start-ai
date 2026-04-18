export type AnalysisStatus = "uploaded" | "queued" | "processing" | "completed" | "failed";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name?: string | null;
  };
}

export interface AnalysisSummary {
  id: string;
  status: AnalysisStatus;
  score: number;
  video_filename: string;
  created_at: string;
}

export interface AnalysisScores {
  start_posture: number;
  push_direction: number;
  first_step_landing: number;
  ground_contact: number;
  forward_com: number;
  arm_leg_coordination: number;
}

export interface AnalysisFeedback {
  primary_diagnosis: string;
  headline?: string;
  summary: string;
  strengths: string[];
  priorities: string[];
  coaching_cues: string[];
  mechanics_overview?: {
    key: string;
    title: string;
    status: string;
    summary: string;
  }[];
  coaching_focus?: {
    title: string;
    ideal: string;
    current: string;
    action: string;
  }[];
  next_session_focus?: string[];
}

export interface AnalysisDetail extends AnalysisSummary {
  step_count: number;
  result_payload: {
    final_score: number;
    scores: AnalysisScores;
    score_details: Record<string, unknown>;
    primary_diagnosis?: string | null;
    feedback?: AnalysisFeedback;
    debug_metrics: Record<string, unknown>;
    deduction_reasons: Record<string, string[]>;
    key_frame_images?: Record<string, string>;
  } | null;
}
