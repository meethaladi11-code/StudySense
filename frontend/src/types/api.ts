/**
 * API type definitions mirroring the StudySense backend Pydantic schemas.
 * Keep in sync with backend/database/schemas.py.
 */

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface UserCreate {
  email: string;
  username: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  username: string;
  created_at: string;
  is_active: boolean;
}

// ── Documents ─────────────────────────────────────────────────────────────────

export interface DocumentResponse {
  id: number;
  filename: string;
  stored_filename: string;
  file_type: string;
  collection_name: string | null;
  chunk_count: number;
  is_processed: boolean;
  created_at: string;
  user_id: number | null;
}

// ── Sources ───────────────────────────────────────────────────────────────────

export interface SourceMetadata {
  document_id: number | null;
  filename: string;
  page: number | null;
  start_index: number | null;
  content_preview: string;
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatSessionCreate {
  title: string;
  document_ids: number[];
}

export interface ChatSessionSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessagePublic {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources: SourceMetadata[] | null;
  created_at: string;
}

export interface ChatSessionDetail {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  documents: DocumentResponse[];
  messages: ChatMessagePublic[];
}

export interface SessionMessageRequest {
  question: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceMetadata[];
}

// ── Quizzes ───────────────────────────────────────────────────────────────────

export interface QuizGenerateRequest {
  title: string;
  document_ids: number[];
  num_questions: number;
  difficulty: 'easy' | 'medium' | 'hard' | 'mixed';
}

export interface QuizSummary {
  id: number;
  title: string;
  quiz_type: string;
  target_topic: string | null;
  created_at: string;
  question_count: number;
}

export interface QuizQuestionForStudent {
  question_id: number;
  question_text: string;
  options: { A: string; B: string; C: string; D: string };
  topic: string;
  difficulty: string;
}

export interface QuizTakeResponse {
  quiz_id: number;
  title: string;
  questions: QuizQuestionForStudent[];
}

export interface AnswerSubmission {
  question_id: number;
  selected_answer: 'A' | 'B' | 'C' | 'D';
}

export interface QuizSubmitRequest {
  answers: AnswerSubmission[];
}

export interface ReviewItem {
  question_id: number;
  question_text: string;
  selected_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation: string;
  topic: string;
  sources: SourceMetadata[] | null;
}

export interface QuizSubmitResponse {
  attempt_id: number;
  correct_count: number;
  total_questions: number;
  score_percentage: number;
  review: ReviewItem[];
}

export interface AttemptSummary {
  id: number;
  quiz_id: number;
  started_at: string;
  submitted_at: string | null;
  correct_count: number;
  total_questions: number;
  score_percentage: number;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  total_quizzes: number;
  total_attempts: number;
  average_score: number;
  questions_answered: number;
  correct_answers: number;
}

export type TopicStatus = 'strong' | 'improving' | 'weak' | 'insufficient_data';

export interface TopicStat {
  topic: string;
  questions_answered: number;
  correct: number;
  accuracy: number;
  status: TopicStatus;
}

export interface WeakTopicSummary {
  topic: string;
  accuracy: number;
  questions_answered: number;
  incorrect: number;
}

// ── Improvement Plans ─────────────────────────────────────────────────────────

export interface ImprovementPlanRequest {
  topic: string;
}

export interface ImprovementPlanResponse {
  id: number;
  topic: string;
  baseline_accuracy: number;
  latest_accuracy: number | null;
  accuracy_change: number | null;
  focus_areas: string[];
  study_plan: string;
  recommended_minutes: number;
  source_refs: SourceMetadata[] | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PracticeQuizResponse {
  quiz_id: number;
  title: string;
  quiz_type: string;
  target_topic: string;
  questions: QuizQuestionForStudent[];
}

// ── API Error ─────────────────────────────────────────────────────────────────

export interface APIError {
  detail: string | { msg: string; type: string }[];
}
