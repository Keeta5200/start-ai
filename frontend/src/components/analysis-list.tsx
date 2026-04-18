import Link from "next/link";
import { AnalysisSummary } from "@/lib/types";
import { toHundredPointScore } from "@/lib/score";

export function AnalysisList({
  analyses,
  totalCount,
  showAll
}: {
  analyses: AnalysisSummary[];
  totalCount: number;
  showAll: boolean;
}) {
  const statusLabel: Record<string, string> = {
    uploaded: "アップロード済み",
    queued: "待機中",
    processing: "解析中",
    completed: "完了",
    failed: "失敗"
  };

  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-fog">最近のアップロード</p>
          <h2 className="mt-3 text-2xl font-semibold">解析一覧</h2>
          {totalCount > 0 ? (
            <p className="mt-2 text-sm text-fog">
              {showAll ? `全${totalCount}件を表示中` : `直近${Math.min(totalCount, analyses.length)}件を表示中`}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          {totalCount > 5 ? (
            <Link
              href={showAll ? "/dashboard" : "/dashboard?view=all"}
              className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-3 text-sm font-semibold text-bone transition hover:border-ember hover:text-ember"
            >
              {showAll ? "直近5件に戻す" : "すべてを見る"}
            </Link>
          ) : null}
          <Link
            href="/upload"
            className="rounded-full bg-ember px-5 py-3 text-sm font-semibold text-ink transition hover:opacity-90"
          >
            解析する
          </Link>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {analyses.length === 0 ? (
          <div className="rounded-[1.5rem] border border-dashed border-white/10 bg-black/20 px-4 py-6 text-sm leading-7 text-fog">
            まだ解析履歴がありません。右上の「解析する」から動画をアップロードすると、ここに最新の結果が並びます。
          </div>
        ) : (
          analyses.map((analysis) => (
            <Link
              key={analysis.id}
              href={`/result/${analysis.id}`}
              className="flex items-center justify-between rounded-[1.5rem] border border-white/10 bg-black/20 px-4 py-4 transition hover:border-ember hover:bg-black/30"
            >
              <div>
                <p className="font-medium">{analysis.video_filename}</p>
                <p className="text-sm text-fog">{statusLabel[analysis.status] ?? analysis.status}</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-semibold">{toHundredPointScore(analysis.score)}</p>
                <p className="text-xs uppercase tracking-[0.25em] text-fog">100点満点</p>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
