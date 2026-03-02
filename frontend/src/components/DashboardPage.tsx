import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, RefreshCw, Sparkles } from 'lucide-react';
import {
  statsApi,
  type InteractionStatsItem,
  type StatsRange,
} from '@/api/stats';

type RangeOption = {
  key: StatsRange;
  label: string;
};

const RANGE_OPTIONS: RangeOption[] = [
  { key: 'today', label: '今天' },
  { key: '7d', label: '近7天' },
  { key: '30d', label: '近30天' },
  { key: '90d', label: '近90天' },
  { key: '1y', label: '近1年' },
  { key: 'all', label: '全部数据' },
];

const RANGE_SET = new Set<StatsRange>(['today', '7d', '30d', '90d', '1y', 'all']);

function isStatsRange(value: string | null): value is StatsRange {
  return value !== null && RANGE_SET.has(value as StatsRange);
}

function getRangeLabel(range: StatsRange): string {
  const found = RANGE_OPTIONS.find((item) => item.key === range);
  return found ? found.label : '近30天';
}

type ChartRow = {
  date: string;
  count: number;
};

function DashboardSkeleton() {
  return (
    <div className="h-full overflow-y-auto bg-soul-cream/20">
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <div className="h-8 w-64 animate-pulse rounded-xl bg-soul-sand/50" />
        <div className="h-20 animate-pulse rounded-2xl bg-white/70" />
        <div className="h-[360px] animate-pulse rounded-3xl bg-white/70" />
        <div className="h-48 animate-pulse rounded-3xl bg-white/70" />
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const initialRange = searchParams.get('range');
  const [selectedRange, setSelectedRange] = useState<StatsRange>(
    isStatsRange(initialRange) ? initialRange : '30d'
  );

  const [rawChartData, setRawChartData] = useState<InteractionStatsItem[]>([]);
  const [analysis, setAnalysis] = useState<string>('');

  const [pageLoading, setPageLoading] = useState<boolean>(true);
  const [chartLoading, setChartLoading] = useState<boolean>(false);
  const [summaryLoading, setSummaryLoading] = useState<boolean>(false);

  const [chartError, setChartError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const requestIdRef = useRef(0);
  const loadedOnceRef = useRef(false);

  const chartData = useMemo<ChartRow[]>(() => {
    const grouped = new Map<string, number>();
    for (const item of rawChartData) {
      if (!item.date) continue;
      const count = Number(item.count) || 0;
      grouped.set(item.date, (grouped.get(item.date) || 0) + count);
    }
    return Array.from(grouped.entries())
      .map(([date, count]) => ({ date, count }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [rawChartData]);

  const totalCount = useMemo(
    () => chartData.reduce((sum, row) => sum + row.count, 0),
    [chartData]
  );

  const rangeLabel = useMemo(() => getRangeLabel(selectedRange), [selectedRange]);
  const isRefreshing = chartLoading || summaryLoading;

  const loadDashboardData = useCallback(async () => {
    const requestId = ++requestIdRef.current;

    if (!loadedOnceRef.current) {
      setPageLoading(true);
    }

    setChartLoading(true);
    setSummaryLoading(true);
    setChartError(null);
    setSummaryError(null);

    console.log('[Dashboard] range=', selectedRange);

    const [interactionResult, summaryResult] = await Promise.allSettled([
      statsApi.getInteractionStats({ range: selectedRange }),
      statsApi.getEmotionTopicSummary({ range: selectedRange }),
    ]);

    if (requestId !== requestIdRef.current) return;

    if (interactionResult.status === 'fulfilled') {
      console.log('[Dashboard] interaction response=', interactionResult.value);
      setRawChartData(Array.isArray(interactionResult.value.chart_data) ? interactionResult.value.chart_data : []);
    } else {
      console.error('[Dashboard] interaction error=', interactionResult.reason);
      setRawChartData([]);
      setChartError(interactionResult.reason instanceof Error ? interactionResult.reason.message : '互动数据加载失败');
    }

    if (summaryResult.status === 'fulfilled') {
      console.log('[Dashboard] summary response=', summaryResult.value);
      const text = (summaryResult.value.analysis ?? '').trim();
      setAnalysis(text || '该时间范围内暂无足够聊天记录用于分析。');
    } else {
      console.error('[Dashboard] summary error=', summaryResult.reason);
      setAnalysis('');
      setSummaryError(summaryResult.reason instanceof Error ? summaryResult.reason.message : '情绪与话题总结加载失败');
    }

    setChartLoading(false);
    setSummaryLoading(false);
    setPageLoading(false);
    loadedOnceRef.current = true;
  }, [selectedRange]);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set('range', selectedRange);
    setSearchParams(params, { replace: true });
  }, [selectedRange, setSearchParams]);

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  const handleRefresh = useCallback(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  if (pageLoading && chartData.length === 0 && !analysis) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="h-full overflow-y-auto bg-soul-cream/20">
      <div className="mx-auto max-w-5xl space-y-8 px-4 py-8 sm:px-6 lg:px-8">
        <header>
          <h1 className="flex items-center gap-3 text-3xl font-display font-bold text-soul-ink">
            <Activity className="h-8 w-8 text-soul-rose" />
            灵魂共鸣数据洞察
          </h1>
          <p className="mt-2 text-sm text-soul-deep/70">
            选择时间范围后会自动刷新图表与情绪话题总结。
          </p>
        </header>

        <section className="rounded-3xl border border-soul-sand/60 bg-white p-5 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex flex-wrap items-center gap-2">
            {RANGE_OPTIONS.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setSelectedRange(item.key)}
                className={`rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                  selectedRange === item.key
                    ? 'bg-soul-rose text-white'
                    : 'bg-soul-cream/80 text-soul-deep hover:bg-soul-sand/70'
                }`}
              >
                {item.label}
              </button>
            ))}

            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="ml-auto inline-flex items-center gap-1.5 rounded-xl border border-soul-sand px-3 py-2 text-sm text-soul-deep hover:bg-soul-sand/40 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              刷新
            </button>
          </div>
          <p className="mt-2 text-xs text-soul-deep/60">当前范围：{rangeLabel}</p>
        </section>

        <section className="rounded-3xl border border-soul-sand/60 bg-white p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="mb-4 flex items-end justify-between">
            <h2 className="text-lg font-semibold text-soul-ink">{rangeLabel}角色互动频次</h2>
            <p className="text-xs text-soul-deep/60">总消息量：{totalCount}</p>
          </div>

          <div className={`h-[350px] w-full transition-opacity duration-300 ${isRefreshing ? 'opacity-90' : 'opacity-100'}`}>
            {chartLoading && chartData.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <div className="h-7 w-7 animate-spin rounded-full border-2 border-soul-rose border-t-transparent" />
              </div>
            ) : chartError ? (
              <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                <p className="text-sm text-red-500">{chartError}</p>
                <button
                  type="button"
                  onClick={handleRefresh}
                  className="rounded-lg border border-soul-sand px-3 py-1.5 text-sm text-soul-deep hover:bg-soul-sand/40"
                >
                  重新加载
                </button>
              </div>
            ) : chartData.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                <p className="text-sm text-soul-deep/60">这个时间段还没有互动，去和角色聊聊吧。</p>
                <button
                  type="button"
                  onClick={handleRefresh}
                  className="rounded-lg border border-soul-sand px-3 py-1.5 text-sm text-soul-deep hover:bg-soul-sand/40"
                >
                  刷新数据
                </button>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12, fill: '#8a8583' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value: string) => (value.length >= 10 ? value.slice(5) : value)}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 12, fill: '#8a8583' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    cursor={{ fill: '#f7f5f4' }}
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  />
                  <Bar dataKey="count" name="消息数量" fill="#E27B88" radius={[6, 6, 0, 0]} maxBarSize={36} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="rounded-3xl border border-soul-sand/60 bg-white p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-soul-ink">
            <Sparkles className="h-5 w-5 text-soul-sage" />
            {rangeLabel}情绪与话题总结
          </h2>
          <div className="relative min-h-[130px] rounded-2xl border border-soul-sand/50 bg-soul-cream/40 p-5">
            {summaryLoading ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-soul-rose border-t-transparent" />
              </div>
            ) : summaryError ? (
              <div className="flex min-h-[90px] flex-col items-center justify-center gap-3 text-center">
                <p className="text-sm text-red-500">{summaryError}</p>
                <button
                  type="button"
                  onClick={handleRefresh}
                  className="rounded-lg border border-soul-sand px-3 py-1.5 text-sm text-soul-deep hover:bg-soul-sand/40"
                >
                  重新分析
                </button>
              </div>
            ) : (
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-soul-ink/90">
                {analysis || '该时间范围内暂无足够聊天记录用于分析。'}
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
