import { AppShell } from "@/components/app-shell";
import { AnalysisPolling } from "@/components/analysis-polling";
import { FeedbackSection } from "@/components/feedback-section";
import { ResultCard } from "@/components/result-card";
import { ScoreDisplay } from "@/components/score-display";
import { getAnalysis } from "@/lib/api";
import { toHundredPointScore } from "@/lib/score";

export const dynamic = "force-dynamic";

function formatAnalysisStatus(status: string) {
  const labels: Record<string, string> = {
    uploaded: "アップロード済み",
    queued: "待機中",
    processing: "解析中",
    completed: "完了",
    failed: "失敗"
  };

  return labels[status] ?? status;
}

function extractWarnings(debugMetrics: Record<string, unknown> | undefined) {
  const warnings = debugMetrics?.warnings;
  if (!Array.isArray(warnings)) {
    return [];
  }
  return warnings.filter((item): item is string => typeof item === "string");
}

function localizeWarning(warning: string) {
  const warningMap: Record<string, string> = {
    "Low-confidence pose detection across the clip.":
      "姿勢推定の信頼度が低く、今回は参考値になりやすい映像です。",
    "Pose confidence is moderate; event timing may need review.":
      "姿勢推定の安定度が十分ではなく、接地タイミングにズレが出る可能性があります。",
    "Landmarks were missing in too many frames for reliable sprint analysis.":
      "フレーム内で姿勢点が欠ける場面が多く、解析精度が下がっています。",
    "Athlete appears partially cut off near the frame edges.":
      "選手の身体や足元が画面端で切れており、参考値として見るのが安全です。",
    "Clip is short for stable step-phase validation.":
      "動画が短く、set から3歩目までの判定が安定しにくいです。"
  };

  return warningMap[warning] ?? warning;
}

function normalizeStoredFeedbackText(text: string) {
  return text
    // 旧メカニクス概要「〜を見ています」パターン
    .replace(/接地で地面を押した力が、そのまま前に進む力へ変わっているかを見ています。/g,
      "踏んだ力がそのままスピードに変わっているかを確認しています。")
    .replace(/スタート直後の力の向きが、低く前へ向いているかを見ています。/g,
      "スタート直後に低く前に出られているかを確認しています。")
    .replace(/一歩目スイッチで足が前に流れず、体の真下へ戻るかを見ています。/g,
      "最初の一歩がブレーキにならず体の下に落とせているかを確認しています。")
    .replace(/最初の3歩をつなぐ加速リズムは、現時点で比較的まとまっています。/g,
      "最初の3歩のスピードのつながりは比較的まとまっています。")
    .replace(/最初の3歩で推進を切らさず、加速を連結できているかを見ています。/g,
      "最初の3歩でスピードをつなげられているかを確認しています。")
    .replace(/スタートで低く前に出る準備ができているかを見ています。/g,
      "スタートの構えが低く前に出やすい形になっているかを確認しています。")
    // 旧フィードバック文の改善
    .replace(/接地で受けた力が前に進む力へ変わり切っていません。/g,
      "踏んだ力がスピードに変わりきっていません。改善すると加速が直接上がります。")
    .replace(/押し出しが少し上へ逃げ、前へ出る動きが弱くなっています。/g,
      "力が少し上に逃げており、前に進む力が弱くなっています。")
    .replace(/一歩目で足が前に流れ、接地がブレーキ寄りです。/g,
      "最初の一歩で足が少し前に出すぎて、ブレーキになっています。")
    .replace(/接地ごとの前進が細切れで、初期加速がつながり切っていません。/g,
      "一歩ごとのスピードのつながりが途切れており、加速が乗りにくくなっています。")
    // 旧ラベルをシンプルなラベルに統一（古い順→新しい順で重ねて変換）
    .replace(/接地の質/g, "地面の押し方")
    .replace(/接地推進力/g, "地面の押し方")
    .replace(/一歩目スイッチ/g, "最初の一歩")
    .replace(/一歩目接地/g, "最初の一歩")
    .replace(/加速の連結/g, "加速のつながり")
    .replace(/重心前進連続性/g, "加速のつながり")
    .replace(/加速の流れ/g, "加速のつながり")
    .replace(/腕振りと脚の連動/g, "腕と脚の合わせ")
    .replace(/腕脚協調/g, "腕と脚の合わせ")
    .replace(/腕脚の連動/g, "腕と脚の合わせ")
    .replace(/セット姿勢/g, "スタートの構え")
    .replace(/セットポジション/g, "スタートの構え")
    .replace(/押し出し方向/g, "前への出方")
    .replace(/ドライブ方向/g, "前への出方")
    // 誤字・文法修正
    .replace(/足が足が前に流れることせず/g, "足が前に流れず")
    .replace(/足が前に流れることせず/g, "足が前に流れず")
    .replace(/切り替えとタイミングさせてください/g, "切り替えのタイミングを合わせてください");
}

function normalizeFeedbackPayload<T>(value: T): T {
  if (typeof value === "string") {
    return normalizeStoredFeedbackText(value) as T;
  }
  if (Array.isArray(value)) {
    return value.map((item) => normalizeFeedbackPayload(item)) as T;
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, normalizeFeedbackPayload(item)])
    ) as T;
  }
  return value;
}

export default async function ResultPage({ params }: { params: { id: string } }) {
  let analysis;
  try {
    analysis = await getAnalysis(params.id);
  } catch {
    return (
      <AppShell
        title={`結果 ${params.id}`}
        subtitle="結果データの取得に失敗しました。バックエンドの起動状況を確認して、もう一度開いてください。"
      >
        <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-8">
          <p className="text-base text-bone">結果ページの読み込みに失敗しました。</p>
          <p className="mt-3 text-sm leading-7 text-fog">
            API 応答エラーの可能性があります。数秒待って再読み込みしてください。
          </p>
        </div>
      </AppShell>
    );
  }
  const result = analysis.result_payload;

  if (!result) {
    return (
      <AppShell
        title={`結果 ${params.id}`}
        subtitle="解析ジョブは開始されていますが、まだ結果の生成が終わっていません。"
      >
        <AnalysisPolling active />
        <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-8">
          <p className="text-base text-bone">解析を実行中です。</p>
          <p className="mt-3 text-sm leading-7 text-fog">
            数秒ごとに自動で更新しています。しばらくそのままでお待ちください。
          </p>
        </div>
      </AppShell>
    );
  }

  const feedback = normalizeFeedbackPayload(result.feedback ?? {
    primary_diagnosis: result.primary_diagnosis ?? "解析レビュー待ち",
    headline: "フォーム全体の所見をまとめています。",
    summary: "フィードバックはまだ生成されていません。",
    strengths: [],
    priorities: [],
    coaching_cues: [],
    mechanics_overview: [],
    coaching_focus: []
  });
  const analysisWarnings = extractWarnings(result.debug_metrics);
  const shouldShowReferenceNotice = analysisWarnings.length > 0;
  const mechanicsOverview = feedback.mechanics_overview?.length
    ? feedback.mechanics_overview
    : [
        {
          key: "ground_contact",
          title: "地面の押し方",
          status: "良好",
          summary: "踏んだ力がしっかりスピードに変わっており、地面の使い方は安定しています。"
        },
        {
          key: "push_direction",
          title: "前への出方",
          status: "要改善",
          summary: "力が少し上に逃げており、前に進む力が弱くなっています。"
        },
        {
          key: "first_step_landing",
          title: "最初の一歩",
          status: "要改善",
          summary: "最初の一歩で足が少し前に出すぎて、ブレーキになっています。"
        },
        {
          key: "forward_com",
          title: "加速のつながり",
          status: "良好",
          summary: "最初の3歩のスピードのつながりはできており、加速のリズムは整っています。"
        }
      ];
  const keyFrameImages = (result.key_frame_images ?? {}) as Record<string, string>;
  const keyFrameOrder = ["set", "first_contact", "second_contact", "third_contact"] as const;
  const keyFrameLabels: Record<string, string> = {
    set: "セット",
    first_contact: "1歩目接地",
    second_contact: "2歩目接地",
    third_contact: "3歩目接地",
  };
  const availableKeyFrames = keyFrameOrder.filter((k) => keyFrameImages[k]);

  const coachingFocus = feedback.coaching_focus?.length
    ? feedback.coaching_focus
    : feedback.coaching_cues.map((item, index) => ({
        title: `ポイント ${index + 1}`,
        ideal: "理想の動きに近づけるための視点です。",
        current: item,
        action: item
      }));

  return (
    <AppShell
      title={`結果 ${params.id}`}
      subtitle="アップロードされたスタート動画に対する解析結果です。推進力、押し出し方向、最初の3歩の質に着目しています。"
    >
      <AnalysisPolling active={analysis.status === "queued" || analysis.status === "processing"} />
      {shouldShowReferenceNotice ? (
        <div className="mb-6 rounded-[1.5rem] border border-amber-400/20 bg-amber-500/10 px-6 py-5">
          <p className="text-xs uppercase tracking-[0.28em] text-amber-300">解析精度について</p>
          <p className="mt-3 text-base leading-7 text-bone/90">
            今回の結果は参考値です。撮影条件の影響で、通常より解析精度が下がっています。
          </p>
          <div className="mt-3 space-y-2 text-sm leading-7 text-bone/80">
            {analysisWarnings.map((warning) => (
              <p key={warning}>{localizeWarning(warning)}</p>
            ))}
          </div>
        </div>
      ) : null}
      {availableKeyFrames.length > 0 && (
        <section className="mb-6 rounded-[2rem] border border-white/10 bg-white/[0.04] p-8">
          <p className="text-xs uppercase tracking-[0.35em] text-fog">キーフレーム骨格</p>
          <p className="mt-2 text-sm text-fog">セットから3歩目までの接地瞬間の姿勢を骨格で可視化しています。</p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {availableKeyFrames.map((key) => (
              <div key={key} className="space-y-2">
                <p className="text-xs uppercase tracking-[0.28em] text-ember">{keyFrameLabels[key]}</p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`data:image/jpeg;base64,${keyFrameImages[key]}`}
                  alt={keyFrameLabels[key]}
                  className="w-full rounded-xl border border-white/10 object-cover"
                />
              </div>
            ))}
          </div>
        </section>
      )}
      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-6">
          <ScoreDisplay
            score={toHundredPointScore(result.final_score)}
            label="総合スコア"
            helperText="総合スコアはモチベーション用の目安です。実際の改善では、右側のコーチング所見と4項目のメカニクス評価を優先して見てください。"
          />

          <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.35em] text-fog">解析状態</p>
              <p className="rounded-full border border-ember/30 bg-ember/10 px-4 py-2 text-xs uppercase tracking-[0.28em] text-ember">
                {formatAnalysisStatus(analysis.status)}
              </p>
            </div>
            <p className="mt-5 text-sm leading-7 text-fog">
              解析ID: {params.id}
            </p>
          </div>
        </div>

        <div className="space-y-6">
          <section className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-8">
            <p className="text-xs uppercase tracking-[0.35em] text-fog">メカニクス概要</p>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {mechanicsOverview.map((item, index) => (
                <ResultCard
                  key={item.key}
                  title={item.title}
                  value={item.status}
                  subtitle={item.summary}
                  accent={index === 0}
                />
              ))}
            </div>
          </section>

          <FeedbackSection
            diagnosis={feedback.primary_diagnosis}
            headline={feedback.headline ?? feedback.summary}
            summary={feedback.summary}
            strengths={feedback.strengths}
            coachingFocus={coachingFocus}
          />
        </div>
      </div>
    </AppShell>
  );
}
