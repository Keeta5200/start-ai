type CoachingFocusItem = {
  title: string;
  ideal: string;
  current: string;
  action: string;
};

function normalizeFeedbackText(text: string) {
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

export function FeedbackSection({
  diagnosis,
  headline,
  summary,
  strengths,
  coachingFocus
}: {
  diagnosis: string;
  headline: string;
  summary: string;
  strengths: string[];
  coachingFocus: CoachingFocusItem[];
}) {
  return (
    <section className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-8">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-fog">フィードバック</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight">コーチングの重点</h2>
          <p className="mt-4 max-w-2xl text-base leading-7 text-bone/90">{normalizeFeedbackText(headline)}</p>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-fog">{normalizeFeedbackText(summary)}</p>
        </div>
        <div className="rounded-full border border-ember/30 bg-ember/10 px-4 py-2 text-sm font-medium text-ember">
          主な所見: {normalizeFeedbackText(diagnosis)}
        </div>
      </div>

      {strengths.length > 0 ? (
        <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-black/20 px-5 py-4">
          <p className="text-xs uppercase tracking-[0.28em] text-fog">維持したい点</p>
          <div className="mt-3 space-y-2">
            {strengths.map((item) => (
              <p key={item} className="text-sm leading-7 text-bone/85">
                {normalizeFeedbackText(item)}
              </p>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-6 grid gap-4">
        {coachingFocus.map((item, index) => (
          <div
            key={`${item.title}-${index}`}
            className="rounded-[1.5rem] border border-white/10 bg-black/20 px-5 py-5"
          >
            <p className="text-xs uppercase tracking-[0.28em] text-fog">重点 {index + 1}</p>
            <h3 className="mt-2 text-xl font-semibold tracking-tight">{item.title}</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <div className="rounded-[1.25rem] border border-white/8 bg-white/[0.03] p-4">
                <p className="text-[11px] uppercase tracking-[0.24em] text-fog">理想</p>
                <p className="mt-2 text-sm leading-7 text-bone/90">{normalizeFeedbackText(item.ideal)}</p>
              </div>
              <div className="rounded-[1.25rem] border border-white/8 bg-white/[0.03] p-4">
                <p className="text-[11px] uppercase tracking-[0.24em] text-fog">現状</p>
                <p className="mt-2 text-sm leading-7 text-bone/90">{normalizeFeedbackText(item.current)}</p>
              </div>
              <div className="rounded-[1.25rem] border border-ember/20 bg-ember/5 p-4">
                <p className="text-[11px] uppercase tracking-[0.24em] text-ember">次に意識すること</p>
                <p className="mt-2 text-sm leading-7 text-bone/90">{normalizeFeedbackText(item.action)}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
