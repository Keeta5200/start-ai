import { AnalysisList } from "@/components/analysis-list";
import { AppShell } from "@/components/app-shell";
import { ScoreDisplay } from "@/components/score-display";
import { getAnalyses } from "@/lib/api";
import { AnalysisSummary } from "@/lib/types";
import { toHundredPointScore } from "@/lib/score";

const DEFAULT_VISIBLE_ANALYSES = 5;

function getDashboardSummary(analysisCount: number, latestScore: number | null) {
  if (analysisCount === 0) {
    return {
      score: 0,
      helperText:
        "まだ解析結果がありません。最初の動画をアップロードすると、ここに最新のスタート評価が表示されます。"
    };
  }

  if (latestScore === null) {
    return {
      score: 0,
      helperText:
        "最新の動画はまだ解析中です。完了すると、接地の質や最初の3歩の流れをここで確認できます。"
    };
  }

  return {
    score: toHundredPointScore(latestScore),
    helperText:
      "最新のスタート解析サマリーです。接地の質、押し出し方向、一歩目スイッチ、加速の連結をまとめて確認できます。"
  };
}

export default async function DashboardPage({
  searchParams
}: {
  searchParams?: { view?: string };
}) {
  let analyses: AnalysisSummary[] = [];

  try {
    analyses = await getAnalyses();
  } catch {
    analyses = [];
  }

  const sortedAnalyses = [...analyses].sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
  );

  const latestCompletedAnalysis = sortedAnalyses.find((analysis) => analysis.status === "completed") ?? null;
  const showAll = searchParams?.view === "all";
  const visibleAnalyses = showAll
    ? sortedAnalyses
    : sortedAnalyses.slice(0, DEFAULT_VISIBLE_ANALYSES);
  const dashboardSummary = getDashboardSummary(
    sortedAnalyses.length,
    latestCompletedAnalysis?.score ?? null
  );

  return (
    <AppShell
      title="ダッシュボード"
      subtitle="アップロードしたスタート動画を一覧で確認し、解析結果から改善ポイントを見つけるページです。"
    >
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <ScoreDisplay
          score={dashboardSummary.score}
          helperText={dashboardSummary.helperText}
        />
        <AnalysisList
          analyses={visibleAnalyses}
          totalCount={sortedAnalyses.length}
          showAll={showAll}
        />
      </div>
    </AppShell>
  );
}
