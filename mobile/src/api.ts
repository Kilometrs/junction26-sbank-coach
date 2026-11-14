// Client for the FastAPI backend in ../app.py.
import { Platform } from 'react-native';

// Web and iOS simulator reach the laptop on localhost, the Android emulator on 10.0.2.2.
// On a real phone set EXPO_PUBLIC_API_URL=http://<your laptop's LAN IP>:8000 and run uvicorn with --host 0.0.0.0.
export const API_URL =
  process.env.EXPO_PUBLIC_API_URL ?? (Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000');

export type Customer = { id: string; label: string };
export type LifeStages = Record<string, { label: string; target_months: number }>;

export type Signal = { stage: string; why: string };

export type Profile = {
  customer_id: string;
  age: number;
  as_of: string;
  balance: number;
  income_monthly: number;
  income_lowest_month: number;
  saving_monthly: number;
  buckets_monthly: { fixed: number; irregular: number; flexible: number };
  by_category_monthly: Record<string, number>;
  mandatory_monthly: number;
  life_stage: string;
  life_stage_confirmed: boolean;
  life_stage_signals: Signal[];
  safety_net: { months_now: number | null; target_months: number; target_eur: number; missing_eur: number };
  safe_to_spend: SafeToSpend;
  persona_text: string;
};

export type SafeToSpend = {
  month: string;
  flexible_budget: number;
  safety_net_contribution: number;
  spent_so_far: number;
  left: number;
  usual_flexible_spend: number;
};

/** One engine call behind a reply: the raw numbers the coach worked from. */
export type Card = { tool: string; args: Record<string, unknown>; result: unknown };

// Charts the coach drew with its chart tools (../charts.py). Every number in them came from the engine.
export type Unit = 'eur' | 'months' | 'percent' | 'count';
type ChartBase = { title: string; note?: string };
export type BarChartSpec = ChartBase & {
  type: 'bar_chart';
  unit: Unit;
  categories: string[];
  series: { name: string; values: number[] }[];
  highlight?: string;
  stacked: boolean;
};
export type LineChartSpec = ChartBase & {
  type: 'line_chart';
  unit: Unit;
  x_unit: 'months' | 'labels';
  x_labels?: string[];
  series: { name: string; dashed: boolean; points?: { x: number; y: number }[]; values?: number[] }[];
  reference?: { label: string; value: number };
};
export type ProgressSpec = ChartBase & {
  type: 'progress';
  unit: Unit;
  bars: { label: string; value: number }[];
  target?: { label: string; value: number };
  badge?: string;
};
/** What a one-off cost takes out of an amount: one bar with the part that stays and the part that goes. */
export type BeforeAfterSpec = ChartBase & {
  type: 'before_after';
  unit: Unit;
  before: { label: string; value: number };
  change: { label: string; value: number };
  after: { label: string; value: number };
  target?: { label: string; value: number };
  badge?: string;
};
export type KeyFiguresSpec = ChartBase & {
  type: 'key_figures';
  headline?: { label: string; value: number; unit: Unit };
  rows: { label: string; value: number; unit: Unit; sign?: 'plus' | 'minus' }[];
  badge?: string;
};
export type ChartSpec = BarChartSpec | LineChartSpec | ProgressSpec | BeforeAfterSpec | KeyFiguresSpec;

export type ChatMessage = { role: 'user' | 'assistant'; content: string };
/**
 * The reply has a [[chart:id]] line where each of `charts` goes. `options` are answers to the question the reply
 * ends with, shown as buttons (empty when there is none).
 */
export type ChatReply = {
  reply: string;
  cards: Card[];
  charts: Record<string, ChartSpec>;
  options: string[];
  life_stage: string | null;
  error?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_URL + path, init);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  customers: () => request<Customer[]>('/customers'),
  lifeStages: () => request<LifeStages>('/life-stages'),
  profile: (id: string, lifeStage?: string | null) =>
    request<Profile>(`/profile/${id}` + (lifeStage ? `?life_stage=${encodeURIComponent(lifeStage)}` : '')),
  chat: (customerId: string, messages: ChatMessage[], lifeStage?: string | null) =>
    request<ChatReply>('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId, messages, life_stage: lifeStage ?? null }),
    }),
};
