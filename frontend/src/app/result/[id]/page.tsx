import { redirect } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { AnalysisPolling } from "@/components/analysis-polling";
import { FeedbackSection } from "@/components/feedback-section";
import { ResultCard } from "@/components/result-card";
import { ScoreDisplay } from "@/components/score-display";
import { getAnalysis, ApiError } from "@/lib/api";
import { PENDING_ANALYSIS_STALE_MS } from "@/lib/auth";
import { toHundredPointScore } from "@/lib/score";

export const dynamic = "force-dynamic";

function isAnalysisStale(createdAt: string) {
  const createdAtMs = new Date(createdAt).getTime();
  if (Number.isNaN(createdAtMs)) {
    return true;
  }

  return Date.now() - createdAtMs > PENDING_ANALYSIS_STALE_MS;
}

type PracticeRecommendation = {
  title: string;
  drills: string[];
  focus: string;
  suggestion: string;
};

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

function buildPracticeRecommendationFallback(
  coachingFocus: { title: string }[],
  mechanicsOverview: { title: string }[] = [],
  diagnosis = ""
): PracticeRecommendation[] {
  const titleAliases: Record<string, string> = {
    "地面の押し方": "地面の押し方",
    "接地の質": "地面の押し方",
    "接地推進力": "地面の押し方",
    "前への出方": "前への出方",
    "押し出し方向": "前への出方",
    "ドライブ方向": "前への出方",
    "最初の一歩": "最初の一歩",
    "一歩目スイッチ": "最初の一歩",
    "一歩目接地": "最初の一歩",
    "加速のつながり": "加速のつながり",
    "加速の連結": "加速のつながり",
    "加速の流れ": "加速のつながり",
    "重心前進連続性": "加速のつながり",
    "腕と脚の合わせ": "腕と脚の合わせ",
    "腕振りと脚の連動": "腕と脚の合わせ",
    "腕脚協調": "腕と脚の合わせ",
    "腕脚の連動": "腕と脚の合わせ",
    "スタートの構え": "スタートの構え",
    "セット姿勢": "スタートの構え",
    "セットポジション": "スタートの構え"
  };

  const library: Record<string, { title: string; drills: string[]; focus: string; suggestion: string }> = {
    "最初の一歩": {
      title: "一歩目の接地を直す練習",
      drills: ["壁押しスタート", "マーカー1歩目ドリル"],
      focus: "足を前に置きにいかず、体の真下へ落としてから後ろへ押す感覚を作ります。",
      suggestion:
        "壁押しスタートで、一歩目を体の真下に落とす感覚を繰り返し確認してください。前へ足を出すより、地面を後ろへ送る意識を優先すると改善しやすいです。"
    },
    "前への出方": {
      title: "前傾を保つ練習",
      drills: ["低姿勢ローリングスタート", "低いミニハードル通過"],
      focus: "3歩目まで頭と胸を低く保ったまま前へ押し出す感覚を作ります。",
      suggestion:
        "低い姿勢のまま3歩だけ進む反復を入れてください。『3歩目まで立たない』を合言葉にすると、前へ出る形が整いやすいです。"
    },
    "地面の押し方": {
      title: "押し切りを強くする練習",
      drills: ["スレッドプッシュ", "片足ドライブドリル"],
      focus: "離地の瞬間まで押し切ってから次へ移る感覚を作ります。",
      suggestion:
        "負荷を使った押し出し系ドリルで、『最後まで押し切らないと進まない』感覚を体に入れてください。まずは強度より、押し切る形を優先すると効果が出やすいです。"
    },
    "加速のつながり": {
      title: "加速の流れをつなぐ練習",
      drills: ["3歩限定スタート反復", "押し出し意識のショートダッシュ"],
      focus: "足の回転を急がず、1歩ごとに押した力を前へのスピードへ変える感覚を作ります。",
      suggestion:
        "3歩だけに絞ったスタート反復で、『押した分だけ前に出る』感覚を確認してください。回転を速くするより、3歩の流れを切らさないことを優先しましょう。"
    },
    "腕と脚の合わせ": {
      title: "腕と脚を合わせる練習",
      drills: ["壁押し片脚切り替え", "その場スプリント腕脚連動"],
      focus: "接地の瞬間に反対側の腕が後ろへ引かれ、腕と脚が同じタイミングで切り替わる感覚を作ります。",
      suggestion:
        "壁押し姿勢で片脚切り替えを行い、脚が地面に着く瞬間に反対腕を後ろへ引く練習を入れてください。腕と脚が同時に切り替わるだけで前への進みやすさが変わります。"
    },
    "スタートの構え": {
      title: "離台姿勢を整える練習",
      drills: ["ヒップドライブドリル", "ランジウォーク"],
      focus: "腰を後ろに残さず、頭・肩・腰をそろえたまま前へ持ち出す形を作ります。",
      suggestion:
        "ヒップドライブやランジ系の動きで、腰ごと前へ出る感覚を先につくってからスタート練習へ入ってください。腰の位置が整うと、その後の接地も軽くなりやすいです。"
    }
  };

  const diagnosisHints: string[] = [];
  if (diagnosis.includes("ブレーキ")) diagnosisHints.push("最初の一歩");
  if (diagnosis.includes("上に逃げ") || diagnosis.includes("前ではなく上")) diagnosisHints.push("前への出方");
  if (diagnosis.includes("踏んだ力") || diagnosis.includes("押し切")) diagnosisHints.push("地面の押し方");
  if (diagnosis.includes("足だけが先") || diagnosis.includes("3歩の流れ")) diagnosisHints.push("加速のつながり");
  if (diagnosis.includes("腕と脚") || diagnosis.includes("タイミング")) diagnosisHints.push("腕と脚の合わせ");
  if (diagnosis.includes("姿勢") || diagnosis.includes("セット")) diagnosisHints.push("スタートの構え");

  const titles = [
    ...coachingFocus.map((item) => item.title),
    ...mechanicsOverview.map((item) => item.title),
    ...diagnosisHints,
  ];

  const recommendations = titles
    .map((title) => library[titleAliases[title] ?? title])
    .filter((item): item is { title: string; drills: string[]; focus: string; suggestion: string } => Boolean(item));

  const uniqueRecommendations = recommendations.filter(
    (item, index, array) => array.findIndex((candidate) => candidate.title === item.title) === index
  );

  if (uniqueRecommendations.length > 0) {
    return uniqueRecommendations.slice(0, 2);
  }

  return [
    {
      title: "スタート基礎を整える練習",
      drills: ["壁押しスタート", "3歩限定スタート反復"],
      focus: "最初の3歩で低く前に出る形と、一歩ごとに押して進む感覚をまとめて作ります。",
      suggestion:
        "まずは壁押しスタートと3歩限定の反復を行い、低い姿勢のまま一歩ごとに地面を押して前に進む感覚を整えてください。細かいことより、最初の3歩の流れをそろえることを優先しましょう。"
    }
  ];
}

export default async function ResultPage({ params }: { params: { id: string } }) {
  let analysis;
  try {
    analysis = await getAnalysis(params.id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      redirect(`/login?next=/result/${params.id}`);
    }
    return (
      <AppShell
        title="結果の読み込みに失敗"
        subtitle="しばらく待ってから再度お試しください。"
      >
        <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-8">
          <p className="text-base text-bone">結果データの取得に失敗しました。</p>
          <p className="mt-3 text-sm leading-7 text-fog">
            数秒待ってからページを再読み込みしてください。
          </p>
        </div>
      </AppShell>
    );
  }
  const result = analysis.result_payload;

  if (!result) {
    const isStalePendingAnalysis =
      (analysis.status === "queued" || analysis.status === "processing" || analysis.status === "uploaded") &&
      isAnalysisStale(analysis.created_at);

    return (
      <AppShell
        title={`結果 ${params.id}`}
        subtitle={
          isStalePendingAnalysis
            ? "この解析は長時間更新がなく、自動追跡の対象から外れています。"
            : "解析ジョブは開始されていますが、まだ結果の生成が終わっていません。"
        }
      >
        <AnalysisPolling active={!isStalePendingAnalysis} />
        <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-8">
          {isStalePendingAnalysis ? (
            <>
              <p className="text-base text-bone">この解析は読み込みに時間がかかりすぎているため、追跡表示を停止しました。</p>
              <p className="mt-3 text-sm leading-7 text-fog">
                その後に解析結果が作られた場合はダッシュボードから開けます。結果が出ないままの場合は、再アップロードしていただく方が確実です。
              </p>
            </>
          ) : (
            <>
              <p className="text-base text-bone">解析を実行中です。</p>
              <p className="mt-3 text-sm leading-7 text-fog">
                数秒ごとに自動で更新しています。しばらくそのままでお待ちください。
              </p>
            </>
          )}
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
          status: "良い",
          summary: "地面を押した力は使えています。さらに後ろへ押し切れると、もっと前に進みやすくなります。"
        },
        {
          key: "push_direction",
          title: "前への出方",
          status: "普通",
          summary: "力が少し上に逃げており、前に進む力が弱くなっています。"
        },
        {
          key: "first_step_landing",
          title: "最初の一歩",
          status: "普通",
          summary: "最初の一歩で足が少し前に出すぎて、ブレーキになっています。"
        },
        {
          key: "forward_com",
          title: "加速のつながり",
          status: "良い",
          summary: "加速の流れはあります。2歩目以降も前に乗り続けられると、もっと伸びます。"
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
  const practiceRecommendations = feedback.practice_recommendations?.length
    ? feedback.practice_recommendations
    : buildPracticeRecommendationFallback(coachingFocus, mechanicsOverview, feedback.primary_diagnosis);
  const visiblePracticeRecommendations =
    practiceRecommendations.length > 0
      ? practiceRecommendations
      : [
          {
            title: "スタート基礎を整える練習",
            drills: ["壁押しスタート", "3歩限定スタート反復"],
            focus: "最初の3歩で低く前に出る形と、一歩ごとに押して進む感覚をまとめて作ります。",
            suggestion:
              "まずは壁押しスタートと3歩限定の反復を行い、低い姿勢のまま一歩ごとに地面を押して前に進む感覚を整えてください。細かいことより、最初の3歩の流れをそろえることを優先しましょう。"
          }
        ];

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
            practiceRecommendations={practiceRecommendations}
          />

          <section className="rounded-[2rem] border border-ember/20 bg-ember/5 p-8">
            <div className="border-b border-ember/10 pb-5">
              <p className="text-xs uppercase tracking-[0.35em] text-ember">おすすめ練習</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight">まず取り組む練習</h2>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-bone/85">
                今回の課題に合わせて、最初に取り組みやすい練習を独立してまとめています。
              </p>
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              {visiblePracticeRecommendations.map((item) => (
                <div
                  key={item.title}
                  className="rounded-[1.5rem] border border-white/10 bg-black/25 p-5"
                >
                  <h3 className="text-xl font-semibold tracking-tight">
                    {normalizeStoredFeedbackText(item.title)}
                  </h3>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {item.drills.map((drill) => (
                      <span
                        key={drill}
                        className="rounded-full border border-ember/20 bg-ember/5 px-3 py-2 text-xs text-ember"
                      >
                        {normalizeStoredFeedbackText(drill)}
                      </span>
                    ))}
                  </div>
                  <p className="mt-4 text-sm leading-7 text-bone/90">
                    {normalizeStoredFeedbackText(item.focus)}
                  </p>
                  <p className="mt-3 text-sm leading-7 text-fog">
                    {normalizeStoredFeedbackText(item.suggestion)}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
