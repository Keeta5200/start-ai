"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  buildAuthCookie,
  buildTokenCookie,
  getLocalStorageItem,
  getSessionStorageItem,
  getStoredAuthToken,
  savePendingAnalysis,
} from "@/lib/auth";

function getApiBaseUrl() {
  if (typeof window !== "undefined") {
    return "/api/proxy";
  }

  return "http://127.0.0.1:8000/api/v1";
}

function getUploadApiBaseUrl() {
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000/api/v1";
  }

  if (window.location.hostname.endsWith(".up.railway.app")) {
    return "https://backend-production-29b9.up.railway.app/api/v1";
  }

  return "/api/proxy";
}

function getUploadApiBaseUrls() {
  const primary = getUploadApiBaseUrl();
  const urls = [primary];

  if (primary !== "/api/proxy") {
    urls.push("/api/proxy");
  }

  return urls;
}

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("スタート局面の動画をアップロードすると、解析を開始します。");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isSubmitting) {
      return;
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isSubmitting]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setMessage("先に動画ファイルを選択してください。");
      return;
    }

    setIsSubmitting(true);
    setProgress(0);
    setMessage("アップロードの準備をしています...");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("step_count", "3");
    let uploadCompleted = false;

    try {
      setMessage("解析サーバーを準備しています...");
      await warmupAnalysisBackend();
      const data = await uploadWithRetry(formData, {
        onProgress: (value) => {
          setProgress(value);
          if (value < 100) {
            setMessage(`動画をアップロード中... ${value}%`);
          } else {
            uploadCompleted = true;
            setMessage("アップロード完了。解析を開始しています...");
          }
        },
        onRetry: () => {
          if (uploadCompleted) {
            setProgress(100);
            setMessage("アップロードは完了しています。解析ジョブを確認しています...");
            return;
          }

          setMessage("通信が不安定なため、アップロードを再試行しています...");
        },
      });
      try {
        const persistentToken = getLocalStorageItem("start-ai-token");
        const token = getStoredAuthToken();
        if (token) {
          const persistent = Boolean(persistentToken);
          document.cookie = buildAuthCookie(persistent);
          document.cookie = buildTokenCookie(token, persistent);
        }
        savePendingAnalysis({
          id: data.analysis_id,
          createdAt: new Date().toISOString(),
          videoFilename: file.name,
        });
      } catch {
        // Storage sync can fail on some mobile browsers; still continue to the result page.
      }
      window.location.assign(`/result/${data.analysis_id}`);
    } catch (err) {
      const recoveredAnalysis = uploadCompleted ? await recoverRecentAnalysis(file.name) : null;
      if (recoveredAnalysis) {
        try {
          savePendingAnalysis({
            id: recoveredAnalysis.id,
            createdAt: recoveredAnalysis.created_at,
            videoFilename: recoveredAnalysis.video_filename,
          });
        } catch {
          // Ignore storage issues on restrictive mobile browsers and continue.
        }
        window.location.assign(`/result/${recoveredAnalysis.id}`);
        return;
      }

      if (err instanceof UploadError && err.status === 401) {
        window.location.assign("/login");
        return;
      }
      if (err instanceof UploadError && err.status === 413) {
        setMessage("動画サイズが大きすぎてアップロードできませんでした。短めに切り出して再度お試しください。");
      } else {
        setMessage("アップロードまたは解析開始に失敗しました。通信状況を確認して、もう一度お試しください。");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="accent-glow rounded-[2rem] border border-white/10 bg-[linear-gradient(145deg,rgba(255,255,255,0.08),rgba(255,255,255,0.04))] p-8 shadow-panel"
    >
      <p className="text-xs uppercase tracking-[0.35em] text-fog">動画受付</p>
      <div className="mt-3 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-3xl font-semibold">最初の3歩を解析する</h2>
          <p className="mt-3 max-w-2xl text-sm text-fog">{message}</p>
        </div>
        <div className="rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs uppercase tracking-[0.28em] text-fog">
          1人・1本・1つの明確な評価
        </div>
      </div>

      <div className="mt-6 rounded-[1.5rem] border border-ember/20 bg-ember/5 p-5">
        <p className="text-xs uppercase tracking-[0.28em] text-ember">推奨撮影条件</p>
        <div className="mt-3 grid gap-2 text-sm leading-7 text-bone/90">
          <p>真横に近い角度から、スマホ横向きの横動画で撮影してください。</p>
          <p>スタート前から3歩目まで、足元を含めて全身が切れない構図が理想です。</p>
          <p>縦動画、斜め角度、足元が切れる映像は、参考値になりやすく精度が下がります。</p>
        </div>
      </div>

      <label className="mt-8 flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-[2rem] border border-dashed border-white/15 bg-black/30 px-6 text-center transition hover:border-ember hover:bg-black/40">
        <span className="text-lg font-medium">{file ? file.name : "動画をドラッグするか選択してください"}</span>
        <span className="mt-2 text-sm text-fog">
          MP4 または MOV。スタート局面のみ、1本につき1人。
        </span>
        <input
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>

      <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-black/20 p-4">
        <div className="flex items-center justify-between text-xs uppercase tracking-[0.28em] text-fog">
          <span>アップロード進行</span>
          <span>{progress}%</span>
        </div>
        <div className="mt-3 h-2 rounded-full bg-white/10">
          <div
            className="h-2 rounded-full bg-gradient-to-r from-ember via-orange-400 to-red-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-8 rounded-full bg-ember px-8 py-4 text-base font-semibold text-ink transition hover:scale-[1.01] hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "解析中..." : "解析する"}
      </button>
    </form>
  );
}

class UploadError extends Error {
  status: number;
  constructor(status: number) {
    super(`Upload failed: ${status}`);
    this.status = status;
  }
}

async function warmupAnalysisBackend(): Promise<void> {
  let lastError: UploadError | null = null;

  for (const baseUrl of getUploadApiBaseUrls()) {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try {
        const response = await fetch(`${baseUrl}/health`, {
          method: "GET",
          cache: "no-store",
        });

        if (response.ok) {
          return;
        }

        lastError = new UploadError(response.status);
        if (!shouldRetryWarmup(response.status) || attempt === 4) {
          break;
        }
      } catch (error) {
        if (error instanceof UploadError) {
          lastError = error;
        } else {
          lastError = new UploadError(0);
        }

        if (attempt === 4) {
          break;
        }
      }

      await wait(1500 * attempt);
    }
  }

  throw lastError ?? new UploadError(0);
}

function uploadWithProgress(
  formData: FormData,
  onProgress: (value: number) => void,
  baseUrl: string
): Promise<{ analysis_id: string }> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${baseUrl}/uploads/video`);
    request.withCredentials = true;
    const token = getStoredAuthToken();
    if (token) {
      request.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    request.timeout = 1000 * 60 * 5;

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const value = Math.round((event.loaded / event.total) * 100);
      onProgress(value);
    };

    request.onload = () => {
      if (request.status < 200 || request.status >= 300) {
        reject(new UploadError(request.status));
        return;
      }
      onProgress(100);
      try {
        resolve(JSON.parse(request.responseText) as { analysis_id: string });
      } catch {
        reject(new UploadError(500));
      }
    };

    request.onerror = () => reject(new UploadError(0));
    request.ontimeout = () => reject(new UploadError(408));
    request.onabort = () => reject(new UploadError(499));
    request.send(formData);
  });
}

type UploadWithRetryOptions = {
  onProgress: (value: number) => void;
  onRetry: (attempt: number, totalAttempts: number) => void;
};

async function uploadWithRetry(
  formData: FormData,
  { onProgress, onRetry }: UploadWithRetryOptions
): Promise<{ analysis_id: string }> {
  let lastError: UploadError | null = null;
  let retryCount = 0;
  const baseUrls = getUploadApiBaseUrls();
  const totalAttempts = Math.max(1, baseUrls.length * 3 - 1);

  for (const baseUrl of baseUrls) {
    let uploadBodyCompleted = false;

    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        return await uploadWithProgress(
          formData,
          (value) => {
            if (value >= 100) {
              uploadBodyCompleted = true;
            }

            onProgress(value);
          },
          baseUrl
        );
      } catch (error) {
        if (!(error instanceof UploadError)) {
          throw error;
        }

        lastError = error;

        if (uploadBodyCompleted) {
          throw error;
        }

        if (!shouldRetryUpload(error.status)) {
          break;
        }

        retryCount += 1;
        onRetry(retryCount, totalAttempts);
        await wait(1200 * attempt);
      }
    }
  }

  throw lastError ?? new UploadError(0);
}

function shouldRetryUpload(status: number) {
  return status === 0 || status === 408 || status === 429 || status === 499 || status === 500 || status === 502 || status === 503 || status === 504;
}

function shouldRetryWarmup(status: number) {
  return status === 0 || status === 408 || status === 425 || status === 429 || status === 499 || status === 500 || status === 502 || status === 503 || status === 504;
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

type RecentAnalysis = {
  id: string;
  status: "uploaded" | "queued" | "processing" | "completed" | "failed";
  score: number;
  video_filename: string;
  created_at: string;
};

async function recoverRecentAnalysis(fileName: string): Promise<RecentAnalysis | null> {
  const recoveryDeadline = Date.now() + 1000 * 20;

  while (Date.now() < recoveryDeadline) {
    try {
      const response = await fetch(`${getApiBaseUrl()}/analyses`, {
        cache: "no-store",
        credentials: "include",
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        const analyses = ((await response.json()) as RecentAnalysis[]).slice().sort((a, b) => {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
        const recoveredAnalysis = selectRecentAnalysisCandidate(analyses, fileName);

        if (recoveredAnalysis) {
          return recoveredAnalysis;
        }
      }
    } catch {
      // Keep polling briefly; mobile networks often fail after the upload body
      // finishes even though the backend has already created the analysis job.
    }

    await wait(2500);
  }

  return null;
}

function selectRecentAnalysisCandidate(
  analyses: RecentAnalysis[],
  fileName: string
): RecentAnalysis | null {
  const now = Date.now();
  const exactCutoff = now - 1000 * 60 * 20;
  const fuzzyCutoff = now - 1000 * 60 * 5;
  const normalizedFileName = normalizeAnalysisFilename(fileName);
  const normalizedStem = stripFilenameExtension(normalizedFileName);

  const exactMatch = analyses.find((analysis) => {
    if (analysis.status === "failed") {
      return false;
    }

    if (new Date(analysis.created_at).getTime() < exactCutoff) {
      return false;
    }

    return normalizeAnalysisFilename(analysis.video_filename) === normalizedFileName;
  });

  if (exactMatch) {
    return exactMatch;
  }

  const stemMatch = analyses.find((analysis) => {
    if (analysis.status === "failed") {
      return false;
    }

    if (new Date(analysis.created_at).getTime() < exactCutoff) {
      return false;
    }

    return stripFilenameExtension(normalizeAnalysisFilename(analysis.video_filename)) === normalizedStem;
  });

  if (stemMatch) {
    return stemMatch;
  }

  return (
    analyses.find((analysis) => {
      if (analysis.status === "failed") {
        return false;
      }

      return new Date(analysis.created_at).getTime() >= fuzzyCutoff;
    }) ?? null
  );
}

function normalizeAnalysisFilename(fileName: string) {
  return fileName.normalize("NFKC").trim().toLowerCase();
}

function stripFilenameExtension(fileName: string) {
  return fileName.replace(/\.[^.]+$/, "");
}

function buildAuthHeaders(): Record<string, string> {
  const token = getStoredAuthToken();

  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}
