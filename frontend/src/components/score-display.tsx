"use client";

import { useEffect, useState } from "react";

function getScoreTone(score: number) {
  if (score >= 90) return "最高";
  if (score >= 75) return "良好";
  if (score >= 60) return "平均";
  return "改善余地あり";
}

export function ScoreDisplay({
  score,
  label = "スタートスコア",
  helperText = "最初の3歩における地面への力の伝え方と、前方への推進効率をまとめた指標です。"
}: {
  score: number;
  label?: string;
  helperText?: string;
}) {
  const [displayScore, setDisplayScore] = useState(0);

  useEffect(() => {
    let frame = 0;
    const totalFrames = 28;
    const timer = window.setInterval(() => {
      frame += 1;
      const progress = frame / totalFrames;
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(score * eased));
      if (frame >= totalFrames) {
        window.clearInterval(timer);
      }
    }, 28);

    return () => window.clearInterval(timer);
  }, [score]);

  const tone = getScoreTone(score);
  const circumference = 2 * Math.PI * 58;
  const progress = Math.max(0, Math.min(1, score / 100));
  const dashOffset = circumference * (1 - progress);

  return (
    <div className="accent-glow relative overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-8 shadow-panel">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-ember to-transparent" />
      <p className="text-xs uppercase tracking-[0.35em] text-fog">{label}</p>

      <div className="mt-8 grid items-center gap-8 lg:grid-cols-[220px_1fr]">
        <div className="relative flex h-[220px] w-[220px] items-center justify-center">
          <svg className="absolute inset-0 -rotate-90" viewBox="0 0 140 140">
            <circle cx="70" cy="70" r="58" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
            <circle
              cx="70"
              cy="70"
              r="58"
              fill="none"
              stroke="url(#scoreGradient)"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              className="transition-[stroke-dashoffset] duration-700 ease-out"
            />
            <defs>
              <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ff7a1f" />
                <stop offset="100%" stopColor="#ff3d00" />
              </linearGradient>
            </defs>
          </svg>

          <div className="text-center">
            <div className="text-6xl font-semibold leading-none lg:text-7xl">{displayScore}</div>
            <div className="mt-2 text-xs uppercase tracking-[0.35em] text-fog">100点満点</div>
          </div>
        </div>

        <div>
          <div className="inline-flex rounded-full border border-white/10 bg-black/30 px-4 py-2 text-xs uppercase tracking-[0.28em] text-ember">
            {tone}
          </div>
          <p className="mt-5 max-w-md text-base leading-7 text-bone/90">{helperText}</p>
          <div className="mt-6 h-2 rounded-full bg-white/10">
            <div
              className="animate-pulse-track h-2 rounded-full bg-gradient-to-r from-ember via-orange-400 to-red-500"
              style={{ width: `${score}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
