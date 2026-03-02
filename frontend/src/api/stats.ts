import { api } from './client';

export type StatsRange = 'today' | '7d' | '30d' | '90d' | '1y' | 'all';

export interface StatsQueryParams {
  range: StatsRange;
}

export interface InteractionStatsItem {
  date: string;
  count: number;
}

export interface InteractionStatsResponse {
  chart_data: InteractionStatsItem[];
  meta?: {
    range?: string;
    label?: string;
    bucket?: 'day' | 'month';
    startDate?: string | null;
    endDate?: string | null;
  };
}

export interface EmotionTopicSummaryResponse {
  analysis: string;
}

function buildStatsQuery(params: StatsQueryParams): string {
  const query = new URLSearchParams();
  query.set('range', params.range);
  return `?${query.toString()}`;
}

const getInteractionStats = (params: StatsQueryParams) =>
  api.get<InteractionStatsResponse>(`/stats/chat/${buildStatsQuery(params)}`);

const getEmotionTopicSummary = (params: StatsQueryParams) =>
  api.get<EmotionTopicSummaryResponse>(`/stats/analysis/${buildStatsQuery(params)}`);

export const statsApi = {
  getInteractionStats,
  getEmotionTopicSummary,

  // 兼容旧调用（仅供历史代码过渡使用）
  getChatStats: (range: 'day' | 'month' | 'year') => {
    const mapped: StatsRange = range === 'day' ? 'today' : range === 'year' ? '1y' : '30d';
    return getInteractionStats({ range: mapped });
  },
  getTopicAnalysis: () => getEmotionTopicSummary({ range: '30d' }),
};
