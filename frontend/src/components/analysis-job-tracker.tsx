"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ApiError, getAnalysis } from "@/lib/api";
import {
  clearPendingAnalysis,
  isPendingAnalysisStale,
  PendingAnalysisRecord,
  readPendingAnalysis,
  savePendingAnalysis,
} from "@/lib/auth";

type PendingAnalysisState = {
  id: string;
  status: string;
  createdAt: string;
  videoFilename?: string;
};

function statusMessage(status: string) {
  if (status === "queued") {
    return "解析ジョブを準備しています。ページを移動しても、このまま追跡できます。";
  }
  if (status === "processing") {
    return "動画を解析中です。別ページへ移動しても、完了後に結果ページへ戻れます。";
  }
  if (status === "failed") {
    return "解析に失敗しました。動画の長さや写り方を確認して、もう一度アップロードしてください。";
  }
  return "解析の状態を更新しています。";
}

function canOpenResultPage(status: string) {
  return status === "completed" || status === "failed";
}

export function AnalysisJobTracker() {
  const router = useRouter();
  const pathname = usePathname();
  const [pending, setPending] = useState<PendingAnalysisState | null>(null);

  useEffect(() => {
    const pendingRecord = readPendingAnalysis();
    if (!pendingRecord) {
      return;
    }

    if (isPendingAnalysisStale(pendingRecord.createdAt)) {
      clearPendingAnalysis();
      return;
    }
    setPending({ ...pendingRecord, status: "queued" });
  }, []);

  useEffect(() => {
    if (!pending?.id) {
      return;
    }

    let cancelled = false;

    const syncPendingAnalysis = async () => {
      try {
        const analysis = await getAnalysis(pending.id);
        if (cancelled) {
          return;
        }

        const nextState: PendingAnalysisState = {
          id: analysis.id,
          status: analysis.status,
          createdAt: analysis.created_at,
          videoFilename: analysis.video_filename,
        };

        if (analysis.status !== "completed" && analysis.status !== "failed") {
          if (isPendingAnalysisStale(analysis.created_at)) {
            clearPendingAnalysis();
            setPending(null);
            return;
          }

          savePendingAnalysis({
            id: analysis.id,
            createdAt: analysis.created_at,
            videoFilename: analysis.video_filename,
          });
        }

        setPending(nextState);

        if (analysis.status === "completed" || analysis.status === "failed") {
          clearPendingAnalysis();
          if (analysis.status === "completed" && pathname !== `/result/${analysis.id}`) {
            router.refresh();
          }
          return;
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiError && error.status === 404) {
          clearPendingAnalysis();
          setPending(null);
        }
      }
    };

    void syncPendingAnalysis();
    const timer = window.setInterval(() => {
      void syncPendingAnalysis();
    }, 4000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [pathname, pending?.id, router]);

  const isVisible = useMemo(() => {
    if (!pending || pending.status === "completed") {
      return false;
    }

    if (pathname === `/result/${pending.id}`) {
      return false;
    }

    return true;
  }, [pathname, pending]);

  if (!isVisible || !pending) {
    return null;
  }

  return (
    <div className="mb-6 rounded-[1.5rem] border border-ember/20 bg-ember/5 p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-ember">解析の追跡</p>
          <p className="mt-2 text-base font-semibold text-bone">
            {pending.videoFilename ? `${pending.videoFilename} を解析しています` : "解析中の動画があります"}
          </p>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-bone/85">
            {statusMessage(pending.status)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs uppercase tracking-[0.28em] text-fog">
            {pending.status === "queued" ? "待機中" : pending.status === "processing" ? "解析中" : "失敗"}
          </span>
          {canOpenResultPage(pending.status) ? (
            <a
              href={`/result/${pending.id}`}
              className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-bone transition hover:border-ember hover:text-ember"
            >
              結果ページへ
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}
