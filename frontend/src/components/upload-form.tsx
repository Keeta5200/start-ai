"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

function getApiBaseUrl() {
  if (typeof window !== "undefined") {
    return "/api/proxy";
  }

  return "http://127.0.0.1:8000/api/v1";
}

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("スタート局面の動画をアップロードすると、解析を開始します。");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);

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

    try {
      const data = await uploadWithProgress(formData, (value) => {
        setProgress(value);
        if (value < 100) {
          setMessage(`動画をアップロード中... ${value}%`);
        } else {
          setMessage("アップロード完了。解析を開始しています...");
        }
      });
      router.push(`/result/${data.analysis_id}`);
    } catch (err) {
      if (err instanceof UploadError && err.status === 401) {
        router.push("/login");
        return;
      }
      setMessage("アップロードに失敗しました。時間をおいて再度お試しください。");
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

function uploadWithProgress(
  formData: FormData,
  onProgress: (value: number) => void
): Promise<{ analysis_id: string }> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${getApiBaseUrl()}/uploads/video`);
    const token = localStorage.getItem("start-ai-token");
    if (token) {
      request.setRequestHeader("Authorization", `Bearer ${token}`);
    }

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
      resolve(JSON.parse(request.responseText) as { analysis_id: string });
    };

    request.onerror = () => reject(new UploadError(0));
    request.send(formData);
  });
}
