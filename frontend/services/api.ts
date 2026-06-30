import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import Constants from 'expo-constants';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://192.168.7.2:8000/api/v1';

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
}

/**
 * Bridge so the auth layer (AuthContext) can react to token lifecycle events
 * happening inside the axios interceptor — persisting rotated tokens and
 * forcing a logout when the session can no longer be refreshed.
 */
export interface AuthEventHandlers {
  onTokensRefreshed?: (access: string, refresh: string) => void;
  onAuthExpired?: () => void;
}

let authEvents: AuthEventHandlers = {};

export function setAuthEvents(events: AuthEventHandlers) {
  authEvents = events;
}

const api: AxiosInstance = axios.create({ baseURL: BASE_URL, timeout: 15000 });

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (res: AxiosResponse) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && refreshToken && !original._retry) {
      original._retry = true;
      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refreshToken });
        setTokens(data.access_token, data.refresh_token);
        authEvents.onTokensRefreshed?.(data.access_token, data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        // Refresh token is invalid/expired — the session is over. Force logout.
        clearTokens();
        authEvents.onAuthExpired?.();
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// --- Domain API methods ---

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export function isAuthenticated(): boolean {
  return accessToken !== null;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { username, password });
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export interface EnvironmentScan {
  people_count: number;
  environment_type: string;
  crowd_density: string;
  ambient_conditions: { lighting: string; estimated_time: string };
  notable_observations: string[];
}

export interface AnalysisResult {
  id: number;
  frame_id: string;
  provider: string;
  detections: Array<{ object_name: string; confidence: number; bbox: object | null }>;
  metrics: Array<{ metric_name: string; value: number }>;
  environment_scan: EnvironmentScan | null;
  frame_thumbnail: string | null;
  created_at: string;
}

export interface ResultFilters {
  dateFrom?: string;
  dateTo?: string;
  objectName?: string;
  minConfidence?: number;
  environmentType?: string;
}

export async function fetchResults(page = 1, pageSize = 20, filters: ResultFilters = {}) {
  const { data } = await api.get<{ items: AnalysisResult[]; total: number }>('/results', {
    params: {
      page,
      page_size: pageSize,
      ...(filters.dateFrom && { date_from: filters.dateFrom }),
      ...(filters.dateTo && { date_to: filters.dateTo }),
      ...(filters.objectName && { object_name: filters.objectName }),
      ...(filters.minConfidence != null && { min_confidence: filters.minConfidence / 100 }),
      ...(filters.environmentType && { environment_type: filters.environmentType }),
    },
  });
  return data;
}

export async function fetchHealth() {
  const { data } = await api.get('/health');
  return data;
}

export interface Schedule {
  id: number;
  name: string;
  interval_seconds: number;
  enabled: boolean;
  last_run: string | null;
  next_run: string | null;
  success_count: number;
  fail_count: number;
}

export async function fetchSchedules(): Promise<Schedule[]> {
  const { data } = await api.get<Schedule[]>('/schedules');
  return data;
}

export async function createSchedule(name: string, interval_seconds: number, enabled = true) {
  const { data } = await api.post<Schedule>('/schedules', { name, interval_seconds, enabled });
  return data;
}

export async function toggleSchedule(id: number, enabled: boolean) {
  const { data } = await api.patch<Schedule>(`/schedules/${id}`, { enabled });
  return data;
}

export async function deleteSchedule(id: number) {
  await api.delete(`/schedules/${id}`);
}

export async function triggerAnalysis(): Promise<void> {
  await api.post('/analyze', {});
}

export async function connectCamera(): Promise<{ connected: boolean }> {
  const { data } = await api.post<{ connected: boolean }>('/camera/connect');
  return data;
}

export async function disconnectCamera(): Promise<{ connected: boolean }> {
  const { data } = await api.post<{ connected: boolean }>('/camera/disconnect');
  return data;
}

// --- Detection / counts / status (Stage 1 + Stage 2) ---

export interface Detection {
  label: string;
  confidence: number;
  bbox: [number, number, number, number]; // normalized x1,y1,x2,y2
  track_id: number | null;
}

export interface Counts {
  live: number;
  cumulative: number;
}

export interface DetectorStatus {
  backend: string;
  available: boolean;
  enabled: boolean;
}

export interface OllamaStatus {
  enabled: boolean;
  reachable: boolean;
  model: string;
  model_present: boolean;
  host: string;
}

export interface HealthData {
  status: string;
  camera_connected: boolean;
  camera_source: string | null;
  active_adapter: string | null;
  cpu_percent: number | null;
  memory_percent: number | null;
  uptime_seconds: number | null;
  detector?: DetectorStatus;
  ollama?: OllamaStatus;
}

// --- Runtime config ---

export interface ScannerConfig {
  camera_source: string;
  camera_rotation: number; // clockwise mount correction: 0 | 90 | 180 | 270
  detection_enabled: boolean;
  detection_conf_threshold: number;
  detection_iou_threshold: number;
  detection_interval_seconds: number;
  counting_min_hits: number;
  counting_person_alert_threshold: number;
  ollama_enabled: boolean;
  ollama_model: string;
  analysis_default_interval_seconds: number;
  allow_cloud: boolean;
  store_frames: boolean;
}

export async function fetchConfig(): Promise<ScannerConfig> {
  const { data } = await api.get<ScannerConfig>('/config');
  return data;
}

export async function updateConfig(patch: Partial<ScannerConfig>): Promise<ScannerConfig> {
  const { data } = await api.patch<ScannerConfig>('/config', patch);
  return data;
}

// --- Events / logs ---

export interface EventItem {
  id: number;
  kind: string;
  severity: string;
  message: string;
  data_json: Record<string, unknown> | null;
  created_at: string;
}

export async function fetchEvents(page = 1, pageSize = 30, kind?: string) {
  const { data } = await api.get<{ items: EventItem[]; total: number }>('/events', {
    params: { page, page_size: pageSize, ...(kind && { kind }) },
  });
  return data;
}
