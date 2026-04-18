type CoachingFocusItem = {
  title: string;
  ideal: string;
  current: string;
  action: string;
};

function normalizeFeedbackText(text: string) {
  return text
    // 旧メカニクス概要「〜を見ています」パターンを実際のフィードバックに変換
    .replace(/接地で地面を押した力が、そのまま前に進む力へ変わっているかを見ています。/g,
      "接地反力をスピードに変換できており、推進への連結は安定しています。")
    .replace(/スタート直後の力の向きが、低く前へ向いているかを見ています。/g,
      "ドライブ方向は前向きにまとまっており、スピードへの変換効率は良好です。")
    .replace(/一歩目スイッチで足が前に流れず、体の真下へ戻るかを見ています。/g,
      "一歩目接地のブレーキング成分は少なく、スピードの継続性は良好です。")
    .replace(/最初の3歩をつなぐ加速リズムは、現時点で比較的まとまっています。/g,
      "初期加速のリズムは整っており、スピードを連続して積み上げられています。")
    .replace(/最初の3歩で推進を切らさず、加速を連結できているかを見ています。/g,
      "初期加速のリズムは整っており、スピードを連続して積み上げられています。")
    .replace(/スタートで低く前に出る準備ができているかを見ています。/g,
      "セットポジションは適正で、スタートシグナルへの即応準備が整っています。")
    // 旧フィードバック文の改善
    .replace(/接地で受けた力が前に進む力へ変わり切っていません。/g,
      "接地反力の一部がスピードに変換されていません。改善すると加速出力が直接上がります。")
    .replace(/押し出しが少し上へ逃げ、前へ出る動きが弱くなっています。/g,
      "ドライブ時に力が上方に逃げており、スピードへの変換効率が低下しています。")
    .replace(/一歩目で足が前に流れ、接地がブレーキ寄りです。/g,
      "一歩目接地でわずかなブレーキングが生じており、スピードの一部が失われています。")
    .replace(/接地ごとの前進が細切れで、初期加速がつながり切っていません。/g,
      "ストライド間でスピードの積み上げが途切れており、加速効率の改善余地があります。")
    // 旧ラベルを新ラベルに統一
    .replace(/接地の質/g, "接地推進力")
    .replace(/一歩目スイッチ/g, "一歩目接地")
    .replace(/加速の連結/g, "重心前進連続性")
    .replace(/腕振りと脚の連動/g, "腕脚協調")
    .replace(/セット姿勢/g, "セットポジション")
    .replace(/押し出し方向/g, "ドライブ方向")
    // 簡略化された語彙を運動学的表現に戻す
    .replace(/もも付け根/g, "股関節")
    .replace(/前に進む力/g, "推進力")
    .replace(/前に進む効率/g, "推進効率")
    .replace(/地面を押した力/g, "地面反力")
    .replace(/力の向き/g, "推進ベクトル")
    .replace(/低く前に出る形/g, "低重心前傾姿勢")
    // 旧フィードバックの語尾・表現の統一
    .replace(/足の回転だけが先に速くなりやすいです/g, "ピッチが先行しやすい状態です")
    .replace(/足だけが先に回りやすくなっています/g, "ピッチ先行型のパターンが生じています")
    .replace(/足[^。]*先に速くなるになりやすいです/g, "ピッチが先行しやすい状態です")
    .replace(/足[^。]*先に速くなりやすいです/g, "ピッチが先行しやすい状態です")
    .replace(/足[^。]*先に回りやすくなっています/g, "ピッチ先行型のパターンが生じています")
    .replace(/足[^。]*先に回ってしまいやすいです/g, "ピッチが先行しやすい状態です")
    .replace(/足が足が前に流れることせず/g, "足が前に流れず")
    .replace(/足が前に流れることせず/g, "足が前に流れず")
    .replace(/接地地面を押した力/g, "接地で地面反力を")
    .replace(/切り替えとタイミングさせてください/g, "切り替えのタイミングを合わせてください")
    .replace(/動きのつながり/g, "推進力の連続性");
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
