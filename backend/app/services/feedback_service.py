from __future__ import annotations

import hashlib
from typing import Any


SCORE_LABELS = {
    "start_posture": "スタートの構え",
    "push_direction": "前への出方",
    "first_step_landing": "最初の一歩",
    "ground_contact": "地面の押し方",
    "forward_com": "加速のつながり",
    "arm_leg_coordination": "腕と脚の合わせ",
}

PRIMARY_DIAGNOSIS_LABELS = {
    "vertical leakage": "力が前ではなく上に逃げているため、スピードが出にくい状態です。",
    "weak ground contact": "踏んだ力がスピードに変わりきっていません。",
    "overreaching first step": "一歩目で足が前に出すぎており、そこでブレーキがかかっています。",
    "disconnected motion": "腕と脚のタイミングがずれており、お互いに引っ張り合えていません。",
    "limited drive posture": "スタート時の姿勢が高すぎて、最初から力強く前に出にくい状態です。",
    "event detection unstable": "映像の条件が十分でなく、今回の解析は参考程度の精度です。",
    "broken forward progression": "3歩の流れが途切れており、足だけが先に回ってスピードが乗りにくくなっています。",
    "suboptimal set posture": "セットポジションの姿勢にもう少し改善の余地があります。",
    "balanced acceleration profile": "大きな崩れはなく、スタートの基本的な動きができています。",
}

COACHING_PATTERN_LIBRARY = {
    "ground_contact": {
        "term": "地面を殺す接地",
        "pattern": "押し切り不足タイプ",
        "diagnosis": "接地での沈み込みが強く、踏んだ力が前への推進に変わりきっていません。離地の瞬間まで三関節を伸ばし切ることで、スピードの乗り方が変わります。",
        "ideal": "離地の瞬間まで股関節・膝・足首を一直線に伸ばし切り、地面を後ろへ送り続けることです。",
        "cue": "最後まで伸び切ってから離せ",
    },
    "push_direction": {
        "term": "離台が立つ",
        "pattern": "早起きタイプ（上体先行型）",
        "diagnosis": "スタート直後から体幹が起き上がっており、加速に必要な前傾角が維持できていません。前に使いたい力が上に抜けて、前方への推進効率が落ちています。",
        "ideal": "3歩目まで頭と胸を低く保ち、斜め前へ長く押し出し続けることです。",
        "cue": "低いまま飛び出す、顔は下",
    },
    "first_step_landing": {
        "term": "足が前に流れる",
        "pattern": "ブレーキ接地タイプ",
        "diagnosis": "一歩目の足を前に置きにいっており、接地の瞬間にブレーキがかかっています。",
        "ideal": "一歩目の足を体の真下近くへ鋭く落とし、ブレーキなく前へ乗り続けることです。",
        "cue": "足は前に出すな、真下に落とせ",
    },
    "forward_com": {
        "term": "失速タイプ",
        "pattern": "失速タイプ（加速持続不全型）",
        "diagnosis": "スタート直後の動きは出ていますが、3歩目以降で加速が失速しています。前傾を保ちながら押し切りを継続し、5歩目まで推進を切らさないことが必要です。",
        "ideal": "一歩ごとに押した力を前進へ変え、3歩目まで流れを切らさず加速を積み上げることです。",
        "cue": "5歩目まで加速し続けろ",
    },
    "arm_leg_coordination": {
        "term": "腕が遊んでいる",
        "pattern": "腕遅れタイプ（上肢遅延型）",
        "diagnosis": "腕振りが脚の動きに対して遅れており、体の軸がブレながら加速しています。肘を素早く引くことで、脚との連動を取り戻してください。",
        "ideal": "接地の瞬間に反対側の腕が真後ろへ引かれ、腕と脚が同じタイミングで切り替わることです。",
        "cue": "腕で引っ張って前に出る",
    },
    "start_posture": {
        "term": "骨盤が後傾している",
        "pattern": "腰抜けタイプ（体幹連動不全型）",
        "diagnosis": "セットポジションで骨盤が後傾しており、離台後の股関節伸展が使いきれていません。体が割れて、力が全身に伝わりにくくなっています。",
        "ideal": "頭・肩・腰・足先が一直線でそろい、腰ごと前へ持ち出してスタートできることです。",
        "cue": "骨盤を立てて、前に向ける",
    },
}

DRILL_LIBRARY = {
    "first_step_landing": {
        "title": "一歩目の接地を直すドリル",
        "drills": ["壁押しスタート", "マーカー1歩目ドリル", "緩い下りスタート", "歩幅マーカースタート"],
        "focus": "足を前に置きにいかず、体の真下へ落としてから後ろへ押す感覚を作ります。",
        "suggestion": "壁押しスタートや歩幅マーカースタートで、一歩目を体の真下に落とす感覚を繰り返し確認してください。前に足を出す意識ではなく、地面を後ろへ送る意識で行いましょう。",
        "pitfalls": [
            "上体だけを前に倒して足だけ遠くへ伸ばさないこと",
            "一歩目を大きくしようとして腰が後ろに残らないこと",
        ],
    },
    "push_direction": {
        "title": "前傾を保つドリル",
        "drills": ["ローリングスタート", "マーカー水平走", "ミニハードル低通過ドリル", "セルフカウントスタート"],
        "focus": "3〜5歩目まで頭の高さを変えず、低い前傾のまま前へ押し出す感覚を作ります。",
        "suggestion": "マーカー水平走やセルフカウントスタートで、速く出ることより形を保ったまま低く押し出す感覚を確認してください。『3歩目まで顔を下に向けたまま』を合言葉にすると形が安定しやすいです。",
        "pitfalls": [
            "顔だけ下げて胸と腰が止まらないこと",
            "低さを意識しすぎて押し出しが弱くならないこと",
        ],
    },
    "ground_contact": {
        "title": "押し切りを強くするドリル",
        "drills": ["スレッドプッシュ", "片足ドライブドリル", "階段ドライブ走", "高腰維持スキップドリル", "前足部接地ドリル"],
        "focus": "離地の瞬間まで股関節・膝・足首を伸ばし切り、押し切ってから次へ移る感覚と、接地で沈み込まない高い腰の感覚を作ります。",
        "suggestion": "負荷を使った押し出し系ドリルに加えて、高腰維持スキップや前足部接地ドリルで、接地の沈み込みを減らしてください。『最後まで押し切らないと進まない』感覚と『踏んだ瞬間に弾き返す』感覚を両方作ることが大切です。",
        "pitfalls": [
            "押そうとして長く乗りすぎ、接地が重くならないこと",
            "前足部だけに意識が寄りすぎて腰が落ちないこと",
        ],
    },
    "forward_com": {
        "title": "加速の流れをつなぐドリル",
        "drills": ["5歩限定加速反復", "加速区間分割計測", "3歩限定スタート反復", "歩幅マーカースタート"],
        "focus": "3〜5歩目でも前傾と押し切りを続け、回転より前への運びを優先する感覚を作ります。",
        "suggestion": "スタートから3歩目までと4〜6歩目の区間を分けて計測し、どこで加速が止まっているかを把握してください。必要に応じて歩幅マーカースタートも入れ、3歩目以降も前傾と押し切りを継続する感覚を作りましょう。",
        "pitfalls": [
            "3歩目で満足して頭を上げないこと",
            "後半をピッチだけでごまかして歩幅を失わないこと",
        ],
    },
    "arm_leg_coordination": {
        "title": "腕と脚を合わせるドリル",
        "drills": ["腕振り単独ドリル", "腕引き意識スタート反復", "壁押し片脚切り替え", "骨盤前傾キープ＋腕振り連動ドリル"],
        "focus": "肘を鋭く後方へ引き、脚の接地と同じタイミングで腕が切り替わる感覚を作ります。",
        "suggestion": "座位や立位での腕振り単独ドリルと、骨盤前傾キープ＋腕振り連動ドリルを組み合わせてください。脚が地面に着く瞬間に反対腕を後ろへ引くことが、体軸を安定させる近道です。",
        "pitfalls": [
            "腕だけ速く動かして脚とのタイミングがずれないこと",
            "肘を外へ開いて肩のラインをぶらさないこと",
        ],
    },
    "start_posture": {
        "title": "離台姿勢を整えるドリル",
        "drills": ["倒れ込みスタート", "ヒップドライブドリル", "深呼吸リリース→ゴー", "バンド前傾走"],
        "focus": "骨盤を立てたまま腰ごと前へ出し、体をひとかたまりで押し出す形を作ります。",
        "suggestion": "倒れ込みスタートとバンド前傾走で、腰ごと前へ移動する順序を体に入れてください。肩や顎の力みを抜いた状態で入ると、骨盤後傾や重心後退が改善しやすくなります。",
        "pitfalls": [
            "腰だけ先に出して頭と肩が遅れないこと",
            "前に乗ろうとして上体だけ折れないこと",
        ],
    },
}

PATTERN_DIAGNOSIS = {
    "ground_contact": "押し切れていない",
    "push_direction": "離台が立つ",
    "first_step_landing": "足が前に流れる",
    "forward_com": "失速タイプ",
    "arm_leg_coordination": "腕が遊んでいる",
    "start_posture": "骨盤が後傾している",
}

ACTION_CUES = {
    "ground_contact": "最後まで伸び切ってから離せ",
    "push_direction": "低いまま飛び出す、顔は下",
    "first_step_landing": "足は前に出すな、真下に落とせ",
    "forward_com": "5歩目まで加速し続けろ",
    "arm_leg_coordination": "腕で引っ張って前に出る",
    "start_posture": "骨盤を立てて、前に向ける",
}

PRIORITY_RULES = [
    {
        "name": "ブレーキ接地+上方向逃げ",
        "when": {"first_step_landing", "push_direction"},
        "priority_order": ["first_step_landing", "push_direction"],
        "defer": ["arm_leg_coordination"],
    },
    {
        "name": "離台弱さ+早起き",
        "when": {"ground_contact", "push_direction"},
        "priority_order": ["ground_contact", "push_direction"],
        "defer": ["forward_com"],
    },
    {
        "name": "腰抜け+重い接地",
        "when": {"start_posture", "ground_contact"},
        "priority_order": ["start_posture", "ground_contact"],
        "defer": ["arm_leg_coordination", "push_direction"],
    },
    {
        "name": "回転先行",
        "when": {"forward_com", "ground_contact"},
        "priority_order": ["ground_contact", "first_step_landing", "forward_com"],
        "defer": ["arm_leg_coordination"],
    },
    {
        "name": "ブレーキ接地+失速",
        "when": {"first_step_landing", "forward_com"},
        "priority_order": ["first_step_landing", "forward_com"],
        "defer": ["start_posture", "arm_leg_coordination"],
    },
    {
        "name": "接地つぶれ+回転先行",
        "when": {"ground_contact", "forward_com"},
        "priority_order": ["ground_contact", "forward_com"],
        "defer": ["arm_leg_coordination"],
    },
    {
        "name": "総崩れ初心者",
        "when": {"start_posture", "ground_contact", "first_step_landing"},
        "priority_order": ["ground_contact", "push_direction"],
        "defer": ["arm_leg_coordination", "forward_com"],
    },
    {
        "name": "骨盤後傾+腕遅れ",
        "when": {"start_posture", "arm_leg_coordination"},
        "priority_order": ["start_posture", "arm_leg_coordination"],
        "defer": ["first_step_landing"],
    },
    {
        "name": "高離台+腕遅れ",
        "when": {"push_direction", "arm_leg_coordination"},
        "priority_order": ["push_direction", "arm_leg_coordination"],
        "defer": ["first_step_landing"],
    },
    {
        "name": "沈み込み+ブレーキ接地",
        "when": {"ground_contact", "first_step_landing"},
        "priority_order": ["first_step_landing", "ground_contact"],
        "defer": ["arm_leg_coordination"],
    },
    {
        "name": "ピッチ過多+歩幅消失",
        "when": {"forward_com", "ground_contact", "first_step_landing"},
        "priority_order": ["ground_contact", "forward_com"],
        "defer": ["arm_leg_coordination"],
    },
    {
        "name": "重心後退+失速",
        "when": {"start_posture", "forward_com"},
        "priority_order": ["start_posture", "forward_com"],
        "defer": ["arm_leg_coordination"],
    },
    {
        "name": "力み+早起き",
        "when": {"start_posture", "push_direction"},
        "priority_order": ["start_posture", "push_direction"],
        "defer": ["first_step_landing", "forward_com"],
    },
    {
        "name": "離台良好+一歩目詰まり",
        "when": {"first_step_landing"},
        "priority_order": ["first_step_landing", "ground_contact"],
        "defer": ["start_posture", "push_direction"],
    },
    {
        "name": "一二歩良好+三歩目失速",
        "when": {"forward_com"},
        "priority_order": ["forward_com", "ground_contact"],
        "defer": ["start_posture", "first_step_landing"],
    },
]


def _variant(variants: list[str], seed: float) -> str:
    idx = int(hashlib.md5(str(round(seed, 3)).encode()).hexdigest(), 16) % len(variants)
    return variants[idx]


def build_feedback_payload(
    scores: dict[str, float],
    score_details: dict[str, dict[str, Any]],
    primary_diagnosis: str,
) -> dict[str, Any]:
    localized_diagnosis = PRIMARY_DIAGNOSIS_LABELS.get(primary_diagnosis, primary_diagnosis)
    priority_plan = _resolve_priority_plan(scores)
    strengths = _strengths(scores)
    priorities = _priorities(scores, priority_plan)
    coaching_focus = _build_coaching_focus(scores, score_details, priority_plan)
    mechanics_overview = _build_mechanics_overview(scores)
    practice_recommendations = _build_practice_recommendations(coaching_focus)
    next_session_focus = [item["action"] for item in coaching_focus[:2]]

    return {
        "primary_diagnosis": localized_diagnosis,
        "headline": _headline(localized_diagnosis, strengths),
        "summary": _summary(localized_diagnosis, priorities),
        "strengths": strengths,
        "priorities": priorities,
        "coaching_cues": next_session_focus,
        "mechanics_overview": mechanics_overview,
        "coaching_focus": coaching_focus,
        "practice_recommendations": practice_recommendations,
        "next_session_focus": next_session_focus,
        "priority_rule": priority_plan["rule_name"] if priority_plan else None,
    }


def ensure_feedback_payload(
    feedback: dict[str, Any] | None,
    primary_diagnosis: str | None = None,
) -> dict[str, Any]:
    normalized = dict(feedback or {})

    normalized.setdefault("primary_diagnosis", primary_diagnosis or "解析レビュー待ち")
    normalized.setdefault("headline", normalized.get("summary") or "フォーム全体の所見をまとめています。")
    normalized.setdefault("summary", "フィードバックはまだ生成されていません。")
    normalized.setdefault("strengths", [])
    normalized.setdefault("priorities", [])
    normalized.setdefault("coaching_cues", [])
    normalized.setdefault("mechanics_overview", [])
    normalized.setdefault("coaching_focus", [])
    normalized.setdefault("next_session_focus", [])

    if not normalized.get("practice_recommendations"):
        normalized["practice_recommendations"] = _ensure_practice_recommendations(normalized)

    return normalized


def _headline(diagnosis: str, strengths: list[str]) -> str:
    if "参考程度" in diagnosis:
        return "映像の条件を整えて、もう一度撮影・解析することをおすすめします。"
    if strengths:
        return f"{_ensure_sentence(strengths[0])} 一方、{_to_clause(diagnosis)}"
    return _ensure_sentence(diagnosis)


def _summary(diagnosis: str, priorities: list[str]) -> str:
    if "参考程度" in diagnosis:
        return "次回は全身がしっかり映る角度で、セットから3歩目まで撮影してください。"
    if not priorities:
        return "大きな崩れはなく、スタートの基本動作は安定しています。"
    if len(priorities) == 1:
        return f"今回は特に{priorities[0]}を意識して練習すると、スタートのスピードが上がります。"
    priority_terms = _priority_terms(priorities)
    if priority_terms:
        return (
            f"今回は特に{priority_terms[0]}を優先し、次に{priority_terms[1]}を整えると、"
            "最初の3歩の加速がまとまりやすくなります。"
        )
    return f"今回は特に{priorities[0]}と{priorities[1]}を重点的に練習することで、最初の3歩が改善します。"


def _strengths(scores: dict[str, float]) -> list[str]:
    messages: list[str] = []
    for score_key, score_value in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:2]:
        if score_value >= 7.0:
            messages.append(_strength_message(score_key, score_value))
    return messages


def _priorities(scores: dict[str, float], priority_plan: dict[str, Any] | None = None) -> list[str]:
    if priority_plan and priority_plan.get("priority_keys"):
        return [SCORE_LABELS[key] for key in priority_plan["priority_keys"][:2] if key in SCORE_LABELS]
    return [SCORE_LABELS[key] for key, _ in sorted(scores.items(), key=lambda item: item[1])[:2]]


def _build_mechanics_overview(scores: dict[str, float]) -> list[dict[str, str]]:
    overview_keys = [
        "ground_contact",
        "push_direction",
        "first_step_landing",
        "forward_com",
    ]
    return [
        {
            "key": key,
            "title": SCORE_LABELS[key],
            "status": _axis_status(key, scores[key]),
            "summary": _axis_summary(key, scores[key]),
        }
        for key in overview_keys
    ]


def _build_coaching_focus(
    scores: dict[str, float],
    score_details: dict[str, dict[str, Any]],
    priority_plan: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    unstable_detection = any(
        isinstance(detail, dict)
        and detail.get("reason") in {"first_contact_unavailable", "contact_events_unavailable"}
        for detail in score_details.values()
    )
    if unstable_detection:
        items.append(
            {
                "title": "撮影条件の改善",
                "ideal": "セットから3歩目まで、足・腰・肩が全部映るように撮影するのが理想です。",
                "current": "今回は体の一部が見切れていたり、ブレが多く、正確な解析が難しい映像でした。",
                "action": "カメラを横から固定して、全身が途切れないよう少し広めに構えて撮影してください。",
            }
        )

    for score_key, _ in _focus_priority_items(scores, priority_plan):
        library = COACHING_PATTERN_LIBRARY.get(score_key, {})
        items.append(
            {
                "title": SCORE_LABELS[score_key],
                "ideal": _ideal_text(score_key),
                "current": _current_text(score_key, score_details.get(score_key, {}), scores.get(score_key, 0.0)),
                "action": _action_text(score_key, score_details.get(score_key, {}), scores.get(score_key, 0.0)),
                "pattern": library.get("pattern", ""),
                "term": library.get("term", ""),
                "priority_reason": _priority_reason_text(score_key, priority_plan),
            }
        )

    deduped: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for item in items:
        if item["title"] in seen_titles:
            continue
        deduped.append(item)
        seen_titles.add(item["title"])
    return deduped[:4]


def _strength_message(score_key: str, score: float = 0.0) -> str:
    variants: dict[str, list[str]] = {
        "ground_contact": [
            "踏んだ力をしっかりスピードに変えられています。接地の質は良い水準です。",
            "地面を押す力が前への動きにつながっており、接地の使い方は安定しています。",
            "接地のたびにスピードが乗っており、地面を踏む力の使い方はできています。",
            "映像上も接地が軽くそろって見えており、地面からの反発を前へのスピードに変えられています。",
        ],
        "push_direction": [
            "スタート直後の力の向きが前向きにまとまっており、無駄なく加速できています。",
            "低く前に出る方向がしっかり出ており、力がスピードに変わっています。",
            "ドライブの方向は良好で、力が上に逃げずに前への加速につながっています。",
            "前傾角が崩れにくく、低い角度のまま前へ押し出せています。",
            "五歩目近くまで頭が上がりすぎず、前傾を保ったまま加速できています。この前傾の持続は大きな強みです。",
        ],
        "first_step_landing": [
            "一歩目の足の位置が体の近くに収まっており、ブレーキになっていません。",
            "一歩目で足が前に出すぎることなく、うまく体の下に落とせています。",
            "一歩目の接地がきれいで、スピードを落とさずに加速を続けられています。",
            "一歩目の入り方が良く、離台で作った勢いを止めずに次へつなげられています。",
        ],
        "forward_com": [
            "3歩のスピードがつながっており、失速せずに加速を続けられています。",
            "1歩ずつスピードが乗っており、3〜5歩目まで流れが切れていません。",
            "各ストライドでしっかり前に進んでおり、加速の連続性は良い状態です。",
            "四歩目以降も前傾と押し切りが続いており、トップスピードへの橋渡しができています。",
        ],
        "arm_leg_coordination": [
            "腕と脚のタイミングが合っており、お互いを引っ張り合えています。",
            "腕振りと脚の切り替えが同じタイミングで動いており、連動ができています。",
            "腕脚の動きがそろっており、上半身と下半身がうまく協力できています。",
            "肘の引きと脚の接地が合っており、体軸がぶれずに推進方向が安定しています。",
        ],
    }
    default_variants = [
        "セットポジションの姿勢は適正で、スタートの準備ができています。",
        "スタート前の姿勢に大きな崩れはなく、素直に出やすい形ができています。",
        "セットポジションは問題なく、ドライブに入りやすい状態です。",
        "離台前の静止が安定しており、スタートへ入りやすい土台があります。",
        "セットポジションの静止が安定しており、毎回同じ形から離台できる再現性があります。",
        "合図からの初動が鋭く、しかも前方への方向性がそろっています。この出だしは大きな武器です。",
    ]
    return _variant(variants.get(score_key, default_variants), score)


def _axis_status(score_key: str, score: float) -> str:
    if score >= 8.5:
        return "最高"
    if score >= 7.0:
        return "良い"
    if score >= 5.8:
        return "普通"
    return "改善余地あり"


def _axis_summary(score_key: str, score: float) -> str:
    if score_key == "ground_contact":
        if score >= 8.5:
            return "踏んだ力をしっかりスピードに変えられています。この感覚はそのまま維持していきましょう。"
        if score >= 7.0:
            return "地面を押した力は使えています。さらに後ろへ押し切れると、もっと前に進みやすくなります。"
        if score >= 5.8:
            return "踏んだ力がまだスピードに変わりきっていません。最後まで押し切る意識を強めたいです。"
        return "踏んだ力がスピードに変わりきっていない状態で、1歩ごとにロスが出ています。"
    if score_key == "push_direction":
        if score >= 8.5:
            return "スタート直後に低く前へ出られています。この出方はかなり良いです。"
        if score >= 7.0:
            return "前には出られています。もう少し低く長く押し出せると、さらに加速しやすくなります。"
        if score >= 5.8:
            return "力が少し上に逃げています。低く前へ押し出す意識を強めたいです。"
        return "力が上に大きく逃げており、スピードが出にくい状態の主な原因になっています。"
    if score_key == "first_step_landing":
        if score >= 8.5:
            return "最初の一歩がきれいに入っており、ブレーキになっていません。この一歩はかなり良いです。"
        if score >= 7.0:
            return "最初の一歩は大きく崩れていません。もう少し体の下に落とせると、さらに前に乗れます。"
        if score >= 5.8:
            return "最初の一歩で少しブレーキがかかっています。足を前に置きにいかないようにしたいです。"
        return "一歩目のブレーキが大きく、せっかくのスタートのスピードが落ちてしまっています。"
    if score_key == "forward_com":
        if score >= 8.5:
            return "3歩の流れがきれいにつながっています。この加速のリズムは自信を持って良いです。"
        if score >= 7.0:
            return "加速の流れはあります。2歩目以降も前に乗り続けられると、もっと伸びます。"
        if score >= 5.8:
            return "一歩ごとのつながりが少し途切れています。3歩目以降も押し続ける意識を持ちたいです。"
        return "3歩でスピードがうまく積み上がらず、足だけが速く回る状態になっています。"
    if score >= 7.0:
        return "スタートの構えは大きく崩れていません。さらに前へ出やすい形に整えられる余地があります。"
    return "セットポジションに改善余地があり、スタートのスピードに影響しています。"


def _ideal_text(score_key: str) -> str:
    library_ideal = COACHING_PATTERN_LIBRARY.get(score_key, {}).get("ideal")
    if library_ideal:
        return library_ideal
    ideals: dict[str, str] = {
        "ground_contact": (
            "理想は、接地のたびに地面をしっかり後ろへ押して、腰がまっすぐ前に進むことです。"
            "「当てる」だけでなく、最後まで「押し切る」接地ができると、スピードに直結します。"
        ),
        "push_direction": (
            "理想は、スタート直後に体を低く保ったまま、斜め前に力強く出ることです。"
            "早く体を起こさず、頭が低いまま3歩くらい走り続けることがポイントです。"
        ),
        "first_step_landing": (
            "理想は、一歩目の足を体の真下に下ろすことです。"
            "足を前に「置きに行く」とそこがブレーキになるので、体の下に「落とす」感覚が大切です。"
        ),
        "forward_com": (
            "理想は、1歩ごとにしっかり地面を押してスピードを積み上げ、3歩目まで流れを途切れさせないことです。"
            "足の回転を急がず、1歩ずつ体が前に乗り続けることを意識します。"
        ),
        "arm_leg_coordination": (
            "理想は、脚が地面に着く瞬間に、反対側の腕が後ろに強く引かれることです。"
            "腕と脚が同じタイミングで切り替わると、お互いに引っ張り合って前への力が増します。"
        ),
        "start_posture": (
            "理想は、セットポジションで体を低く前傾させ、合図と同時に真っ直ぐ前に飛び出せる姿勢を作ることです。"
            "腰が高すぎると、最初から力が逃げてしまいます。"
        ),
    }
    return ideals.get(score_key, "理想は、セットポジションで低く構え、合図と同時に前に力強く出ることです。")


def _current_text(score_key: str, detail: dict[str, Any], score: float) -> str:
    measurements = detail.get("measurements", {}) if isinstance(detail, dict) else {}
    reasons = detail.get("deduction_reasons", []) if isinstance(detail, dict) else []
    if reasons:
        return _deduction_to_current_text(score_key, str(reasons[0]), score)

    if score_key == "ground_contact":
        if score >= 7.5:
            return _variant([
                "地面は押せていますが、まだ少し押し切れていません。離地の瞬間まで伸び切れると、さらに前に進めます。",
                "踏む力はあります。ただ、押し切れていないぶん、最後のひと伸びがスピードに変わりきっていません。",
            ], score)
        if score >= 6.5:
            return _variant([
                "接地はできていますが、押し切れていません。トリプルエクステンションが途中で終わり、力が逃げています。",
                "踏み込みはできていますが、膝が抜けたまま離れており、押し切る前に動きが終わっています。",
            ], score)
        return _variant([
            "一歩ごとの押し切りが不完全で、踏んだ力がスピードに変わりきっていません。お尻が残り、後ろへ押し切る前に離れています。",
            "接地で地面を殺しており、反発が前への推進に変わっていません。接地がつぶれ、ここがスピードロスの主な原因です。",
            "股関節・膝・足首の伸びが途中で止まり、三関節を使い切れていません。押し切る前に動きが終わり、接地のたびに腰が落ちています。",
        ], score)

    if score_key == "push_direction":
        if score >= 7.5:
            return _variant([
                "前には出られています。ただ、少しだけ起き上がりが早く、3歩目までの前傾を使い切れていません。",
                "出だしの方向は良いですが、早起き気味なので、もう少し低いまま押し続けられるとさらに伸びます。",
                "スタート直後の方向性は良いですが、三歩目で少し頭が上がりやすく、そこから前への流れが薄くなっています。",
            ], score)
        if score >= 6.5:
            return _variant([
                "スタート直後から体幹が起き上がっており、加速に必要な前傾角が維持できていません。そこから力が上に逃げています。",
                "離台が立ち気味で、頭と胸が先に上がるぶん、水平方向への加速力が薄くなっています。",
            ], score)
        return _variant([
            "スタート直後から体幹が起き上がっており、加速に必要な前傾角が維持できていません。前に使いたい力が上に抜けています。",
            "離台が立っていて、低く押し出す形が作れていません。ここが一番大きな課題です。",
            "前傾で押せる時間が短く、前ではなく上に浮く動きになっています。3歩目までの加速が止まりやすいです。",
        ], score)

    if score_key == "first_step_landing":
        if score >= 7.5:
            return _variant([
                "最初の一歩は大きく崩れていません。ただ、少しだけ足が前に流れる場面があり、そこでわずかにブレーキが入っています。",
                "一歩目はほぼ良いですが、接地前に足を少し置きにいく場面があります。真下に鋭く落とせるとさらに良くなります。",
                "離台の勢いはありますが、一歩目だけ少し詰まりやすく、その瞬間に初速を受け止めきれていません。",
            ], score)
        if score >= 6.5:
            return _variant([
                "一歩目で足が前に流れています。接地位置が重心より前にあるぶん、そこで少しブレーキがかかっています。",
                "最初の一歩を置きにいっており、体の下ではなく前で受けています。そのぶんスピードが落ちています。",
            ], score)
        return _variant([
            "一歩目で足が前に流れており、ブレーキ接地になっています。せっかくのスタートの力を最初の一歩で止めています。",
            "最初の一歩を前に置きにいく動きが強く、接地点が重心より前にあります。ここでスピードを大きくロスしています。",
            "一歩目が短く詰まりやすく、足が前に流れています。ここを真下に落とせないと加速は乗りません。",
            "離台の角度は悪くありませんが、一歩目だけ異様に小さく詰まり、そこで勢いが吸収されています。まずは一歩目を大きく使い切る必要があります。",
        ], score)

    if score_key == "forward_com":
        if score >= 7.5:
            return _variant([
                "加速のつながりはあります。ただ、途中で少し回転先行になり、体より足が先に速くなる瞬間があります。",
                "流れはできていますが、3歩目あたりで足の回転が先走り、前への運びが少し切れています。",
                "一・二歩目は良いですが、三歩目だけ歩幅が少し詰まりやすく、そこで前への流れが細くなります。",
            ], score)
        if score >= 6.5:
            return _variant([
                "3歩目以降で失速タイプの動きが出ています。足の回転が先に出て、体の前進が途中で切れています。",
                "3歩の流れはありますが、途中から足だけが先に回っており、押して進むリズムが崩れています。",
                "三歩目までは加速していますが、四歩目以降で歩幅が落ち、ピッチでごまかす形になっています。ここで推進力が空回りしています。",
            ], score)
        return _variant([
            "スタート直後の動きは出ていますが、3歩目以降で加速が失速しています。足だけが先に回っており、押して進む力が途中で切れています。",
            "3歩のスピードが途切れていて、体より足の回転が先に速くなっています。歩幅が消え、3〜5歩目の押し切りが続いていません。",
            "加速の流れが1歩ごとに切れており、足だけが先走る形になっています。5歩目まで加速を続ける感覚を作り直す必要があります。",
        ], score)

    if score_key == "arm_leg_coordination":
        return _variant([
            "腕振りが脚の動きに対して遅れており、体の軸がブレながら加速しています。腕が遊んでいて、推進力への貢献が足りません。",
            "腕振りが後ろへまっすぐ引けず、腕と脚の合わせがばらついています。そのぶん前への出力が弱くなっています。",
            "腕が流れることで肩のラインがぶれ、脚の切り替えとも合っていません。腕遅れが連動のロスになっています。",
        ], score)

    return _variant([
        "骨盤が後傾しており、腰が後ろに残っています。体が割れて、スタートで前へ力を出しにくい形です。",
        "セット重心が後ろに残りやすく、腰抜け気味で上半身だけ前傾し下半身が残っています。股関節を使い切れず、ブロッククリアランスの形が崩れています。",
        "離台の瞬間に腰だけが先に動き、頭と肩が一拍遅れてついてきています。体がひとかたまりで出られておらず、最初の一歩へ力がつながりにくい状態です。",
    ], score)


def _action_text(score_key: str, detail: dict[str, Any], score: float) -> str:
    preferred_cue = COACHING_PATTERN_LIBRARY.get(score_key, {}).get("cue")
    if score_key == "ground_contact":
        if score >= 7.5:
            return _variant([
                f"次は「{preferred_cue or ACTION_CUES[score_key]}」を意識してください。今の接地に、最後のひと伸びを足すイメージです。",
                f"地面を押す感覚はあります。ここに「{preferred_cue or ACTION_CUES[score_key]}」を足せると、さらに前へ進めます。",
            ], score)
        if score >= 6.5:
            return _variant([
                f"まず意識することは「{preferred_cue or ACTION_CUES[score_key]}」です。股関節・膝・足首が全部伸び切るまで、地面を後ろへ送り続けてください。",
                f"まずは「{preferred_cue or ACTION_CUES[score_key]}」を徹底してください。中途半端に離さないだけで加速は変わります。",
            ], score)
        return _variant([
            f"いちばん意識してほしいのは「{preferred_cue or ACTION_CUES[score_key]}」です。離地の瞬間まで一直線に伸び切ってから次の動作へ移ってください。",
            f"今は押し切れていないので、「{preferred_cue or ACTION_CUES[score_key]}」を毎歩徹底してください。沈まずに弾き返せると押した分だけ前に進みます。",
            f"まずは「{preferred_cue or ACTION_CUES[score_key]}」だけに集中してください。中途半端に離さず、地面を殺さない接地を作ることが近道です。",
        ], score)

    if score_key == "push_direction":
        if score >= 7.5:
            return _variant([
                f"次は「{preferred_cue or ACTION_CUES[score_key]}」を意識してください。今の良い出方を、もう半歩ぶん長く使いたいです。",
                f"出だしは良いので、「{preferred_cue or ACTION_CUES[score_key]}」を足せるとさらに伸びます。",
            ], score)
        if score >= 6.5:
            return _variant([
                f"まず意識することは「{preferred_cue or ACTION_CUES[score_key]}」です。早起きしないことを最優先に、3歩目まで前傾を残してください。",
                f"まずは「{preferred_cue or ACTION_CUES[score_key]}」を徹底してください。頭と胸が上がるのを我慢するだけで方向は変わります。",
            ], score)
        return _variant([
            f"いちばん意識してほしいのは「{preferred_cue or ACTION_CUES[score_key]}」です。離台が立ったままだと、後の動きが全部崩れやすくなります。",
            f"今は起き上がりが早いので、「{preferred_cue or ACTION_CUES[score_key]}」を徹底してください。3歩目まではまだ低くて大丈夫です。",
            f"まずは「{preferred_cue or ACTION_CUES[score_key]}」だけに集中してください。立つ前に押す感覚を作り、前方への推進軸を整えたいです。",
        ], score)

    if score_key == "first_step_landing":
        if score >= 7.5:
            return _variant([
                f"一歩目は大きく崩れていません。次は「{preferred_cue or ACTION_CUES[score_key]}」を意識して、足の前流れをなくしてください。",
                f"今の一歩に「{preferred_cue or ACTION_CUES[score_key]}」を足せると、さらにブレーキが減ります。",
                f"離台の勢いは作れているので、「{preferred_cue or ACTION_CUES[score_key]}」で一歩目の詰まりだけ外せれば、一気につながりやすくなります。",
            ], score)
        if score >= 6.5:
            return _variant([
                f"まず意識することは「{preferred_cue or ACTION_CUES[score_key]}」です。前に置きにいかず、体の下へ鋭く落としてください。",
                f"まずは「{preferred_cue or ACTION_CUES[score_key]}」を徹底してください。足が前に流れるだけで一歩目がブレーキになります。",
            ], score)
        return _variant([
            f"いちばん意識してほしいのは「{preferred_cue or ACTION_CUES[score_key]}」です。前に置きにいく動きを止めて、一歩目のブレーキを消してください。",
            f"今は足が前に流れているので、「{preferred_cue or ACTION_CUES[score_key]}」を徹底してください。真下に落ちればダブルブレーキは大きく減ります。",
            f"まずは「{preferred_cue or ACTION_CUES[score_key]}」だけに集中してください。一歩目の接地位置を直すことが最優先です。",
        ], score)

    if score_key == "forward_com":
        if score >= 7.5:
            return _variant([
                f"加速の流れはあります。次は「{preferred_cue or ACTION_CUES[score_key]}」を意識して、回転先行をなくしていきましょう。",
                f"今の流れを保ちつつ、「{preferred_cue or ACTION_CUES[score_key]}」を徹底できると3歩の伸びが変わります。",
                f"三歩目の質はあと少しで変わるので、「{preferred_cue or ACTION_CUES[score_key]}」を意識し、5歩目まで流れを切らさないようにしてください。",
            ], score)
        if score >= 6.5:
            return _variant([
                f"まず意識することは「{preferred_cue or ACTION_CUES[score_key]}」です。回転を急がず、押した力が前に変わってから次へ移ってください。",
                f"回転先行を止めるために、「{preferred_cue or ACTION_CUES[score_key]}」を意識してください。足の速さより前への運びを優先したいです。",
            ], score)
        return _variant([
            f"いちばん意識してほしいのは「{preferred_cue or ACTION_CUES[score_key]}」です。3歩目で終わらず、5歩目まで加速を続けてください。",
            f"今は足だけが先に回っているので、「{preferred_cue or ACTION_CUES[score_key]}」を徹底してください。体が前に乗ってから次へ進む形を作りたいです。",
            f"まずは「{preferred_cue or ACTION_CUES[score_key]}」だけに集中してください。回す前に押すこと、そして5歩目まで失速しないことが最優先です。",
        ], score)

    if score_key == "arm_leg_coordination":
        return _variant([
            f"まず意識することは「{preferred_cue or ACTION_CUES[score_key]}」です。肘を鋭く後方へ引き、脚の接地と同じタイミングで切り替えてください。",
            f"まずは「{preferred_cue or ACTION_CUES[score_key]}」を意識してください。腕が遊ばなくなるだけで、体軸はかなり安定します。",
            f"腕遅れを止めるために、「{preferred_cue or ACTION_CUES[score_key]}」を徹底してください。肩のラインをぶらさず走りたいです。",
        ], score)

    return _variant([
        f"まず意識することは「{preferred_cue or ACTION_CUES['start_posture']}」です。骨盤が後傾したままだと、股関節を使い切れません。",
        f"まずは「{preferred_cue or ACTION_CUES['start_posture']}」を意識してください。頭・肩・腰・足先が一直線で出る形を作り、重心を後ろに残さないようにしたいです。",
        f"いちばん大事なのは「{preferred_cue or ACTION_CUES['start_posture']}」です。セットの重心を少し前に置いて、離台を体ごと一直線で出すことから整えてください。",
    ], score)


def _deduction_to_current_text(score_key: str, reason: str, score: float = 0.0) -> str:
    lower_reason = reason.lower()
    if any(kw in lower_reason for kw in ("unreliable", "incomplete", "could not", "not detected")):
        return _variant([
            "今回の映像ではこの部分の動作がうまく捉えられず、正確な判定が難しい状態でした。",
            "映像の条件の影響で、この動作の解析精度が下がっています。参考値として見てください。",
        ], score)
    if score_key == "ground_contact":
        return _variant([
            "踏んだ力がスピードに変わりきっていません。地面を押し切る前に足が離れてしまっています。",
            "接地で地面に当たっているだけで、後ろへ押し切る動作が弱い状態です。接地の沈み込みも大きく出ています。",
        ], score)
    if score_key == "push_direction":
        return _variant([
            "力が上に逃げており、前へのスピードに変わっていません。体の起き上がりが早いことが原因です。",
            "スタート直後から力が上向きになっており、前に進む力として使えていません。",
        ], score)
    if score_key == "first_step_landing":
        return _variant([
            "一歩目で足が前に出すぎており、そこでブレーキがかかっています。",
            "一歩目の足の位置が体より前になっており、踏んだ瞬間にスピードが落ちています。",
        ], score)
    if score_key == "forward_com":
        return _variant([
            "3歩の流れが途切れており、足だけが速く回ってスピードが乗りにくい状態です。",
            "ストライドのたびにスピードが止まりかけており、足の回転だけが先走っています。押し切りが薄いため歩幅も消えています。",
        ], score)
    if score_key == "arm_leg_coordination":
        return _variant([
            "腕と脚のタイミングがずれており、お互いを引っ張り合えていません。",
            "腕振りと脚の切り替えがバラバラで、連動した動きになっていません。",
        ], score)
    return _variant([
        "セットポジションの姿勢が高すぎて、最初から力が上に逃げやすい状態です。",
        "セットポジションで体重が後方に残りやすく、最初の一歩の力が十分に出にくくなっています。",
    ], score)


def _ensure_sentence(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return normalized
    if normalized.endswith("。"):
        return normalized
    return f"{normalized}。"


def _to_clause(text: str) -> str:
    normalized = text.strip()
    if normalized.endswith("。"):
        normalized = normalized[:-1]
    if normalized.startswith("現在、"):
        normalized = normalized[len("現在、"):]
    return normalized


def _measurement(measurements: dict[str, Any], key: str) -> float | None:
    value = measurements.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _focus_priority_items(
    scores: dict[str, float],
    priority_plan: dict[str, Any] | None = None,
) -> list[tuple[str, float]]:
    preferred_axes = [
        "ground_contact",
        "push_direction",
        "first_step_landing",
        "forward_com",
        "arm_leg_coordination",
        "start_posture",
    ]
    ordered = sorted(
        scores.items(),
        key=lambda item: (item[1], preferred_axes.index(item[0]) if item[0] in preferred_axes else 99),
    )
    if priority_plan and priority_plan.get("priority_keys"):
        prioritized = []
        used = set()
        deferred = set(priority_plan.get("defer_keys", []))
        for key in priority_plan["priority_keys"]:
            if key in scores and key not in used:
                prioritized.append((key, scores[key]))
                used.add(key)
        for key, value in ordered:
            if key in used or key in deferred:
                continue
            prioritized.append((key, value))
        ordered = prioritized
    selected: list[tuple[str, float]] = []
    for key, value in ordered:
        if key == "start_posture" and value >= 5.5:
            continue
        selected.append((key, value))
        if len(selected) == 3:
            break
    return selected


def _priority_terms(priorities: list[str]) -> list[str]:
    reverse_labels = {label: key for key, label in SCORE_LABELS.items()}
    terms: list[str] = []
    for priority in priorities[:2]:
        score_key = reverse_labels.get(priority)
        if not score_key:
            continue
        term = COACHING_PATTERN_LIBRARY.get(score_key, {}).get("term")
        if term:
            terms.append(term)
    return terms


def _resolve_priority_plan(scores: dict[str, float]) -> dict[str, Any] | None:
    active_low_axes = {key for key, value in scores.items() if value < 6.9}
    if (
        scores.get("ground_contact", 10.0) < 6.4
        and scores.get("first_step_landing", 10.0) < 6.4
    ):
        return {
            "rule_name": "沈み込み+ブレーキ接地",
            "priority_keys": ["first_step_landing", "ground_contact"],
            "defer_keys": ["arm_leg_coordination"],
        }

    if (
        scores.get("ground_contact", 10.0) < 6.2
        and scores.get("forward_com", 10.0) < 6.5
        and scores.get("push_direction", 0.0) >= 6.5
    ):
        return {
            "rule_name": "接地つぶれ+回転先行",
            "priority_keys": ["ground_contact", "forward_com"],
            "defer_keys": ["arm_leg_coordination"],
        }

    if (
        scores.get("forward_com", 10.0) < 6.2
        and scores.get("ground_contact", 10.0) < 6.5
        and scores.get("first_step_landing", 10.0) >= 6.8
    ):
        return {
            "rule_name": "ピッチ過多+歩幅消失",
            "priority_keys": ["ground_contact", "forward_com"],
            "defer_keys": ["arm_leg_coordination"],
        }

    if (
        scores.get("first_step_landing", 10.0) < 6.5
        and scores.get("forward_com", 10.0) < 6.5
        and scores.get("push_direction", 0.0) >= 6.8
    ):
        return {
            "rule_name": "ブレーキ接地+失速",
            "priority_keys": ["first_step_landing", "forward_com"],
            "defer_keys": ["start_posture", "arm_leg_coordination"],
        }

    if (
        scores.get("start_posture", 10.0) < 6.4
        and scores.get("forward_com", 10.0) < 6.6
        and scores.get("first_step_landing", 10.0) < 6.8
    ):
        return {
            "rule_name": "重心後退+失速",
            "priority_keys": ["start_posture", "forward_com"],
            "defer_keys": ["arm_leg_coordination"],
        }

    if (
        scores.get("start_posture", 0.0) >= 7.0
        and scores.get("push_direction", 0.0) >= 7.0
        and scores.get("first_step_landing", 10.0) < 6.4
    ):
        return {
            "rule_name": "離台良好+一歩目詰まり",
            "priority_keys": ["first_step_landing", "ground_contact"],
            "defer_keys": ["start_posture", "push_direction"],
        }

    if (
        scores.get("first_step_landing", 0.0) >= 7.0
        and scores.get("push_direction", 0.0) >= 7.0
        and scores.get("forward_com", 10.0) < 6.2
    ):
        return {
            "rule_name": "一二歩良好+三歩目失速",
            "priority_keys": ["forward_com", "ground_contact"],
            "defer_keys": ["start_posture", "first_step_landing"],
        }

    if (
        scores.get("forward_com", 10.0) < 6.9
        and scores.get("first_step_landing", 0.0) >= 7.0
        and scores.get("push_direction", 0.0) >= 7.0
    ):
        return {
            "rule_name": "3歩目以降の失速",
            "priority_keys": ["forward_com", "ground_contact"],
            "defer_keys": ["start_posture", "first_step_landing"],
        }

    if (
        scores.get("start_posture", 10.0) < 6.9
        and scores.get("arm_leg_coordination", 10.0) < 6.9
        and scores.get("push_direction", 10.0) < 6.9
    ):
        return {
            "rule_name": "過緊張",
            "priority_keys": ["start_posture", "arm_leg_coordination"],
            "defer_keys": ["ground_contact", "first_step_landing", "forward_com"],
        }

    if len(active_low_axes) >= 4:
        return {
            "rule_name": "総崩れ初心者",
            "priority_keys": ["ground_contact", "push_direction"],
            "defer_keys": ["arm_leg_coordination", "forward_com"],
        }

    best_rule: dict[str, Any] | None = None
    best_match_size = -1
    for rule in PRIORITY_RULES:
        required = rule["when"]
        if required.issubset(active_low_axes):
            if len(required) > best_match_size:
                best_rule = rule
                best_match_size = len(required)

    if best_rule:
        return {
            "rule_name": best_rule["name"],
            "priority_keys": best_rule["priority_order"],
            "defer_keys": best_rule.get("defer", []),
        }

    return None


def _priority_reason_text(score_key: str, priority_plan: dict[str, Any] | None) -> str:
    if not priority_plan:
        return ""
    priority_keys = priority_plan.get("priority_keys", [])
    if not priority_keys or score_key != priority_keys[0]:
        return ""
    reasons = {
        "ブレーキ接地+上方向逃げ": "まず一歩目のブレーキを外さないと、その後の出方を直しても前に進みにくいです。",
        "離台弱さ+早起き": "まず押し切る力を作らないと、前傾だけ整えても初速が変わりにくいです。",
        "腰抜け+重い接地": "まず腰の位置を整えないと、接地だけ軽くしようとしても土台が崩れたままです。",
        "回転先行": "まず押し切りを作らないと、回転だけを抑えても前へのスピードは伸びません。",
        "ブレーキ接地+失速": "毎歩のブレーキを消さない限り、その後の加速を直しても流れはつながりません。まず接地位置の修正が先です。",
        "接地つぶれ+回転先行": "接地がつぶれている状態で回転を上げても沈み込みが強まるだけなので、まず接地を短く鋭くする必要があります。",
        "沈み込み+ブレーキ接地": "腰の沈み込みと足の前流れが同時に出ると、毎歩で二重のブレーキになります。まず一歩目の接地位置と腰の高さをそろえる必要があります。",
        "ピッチ過多+歩幅消失": "回転を上げても一歩の押し切りが消えていると前に進まないので、まず歩幅と押し切りを取り戻すことが先です。",
        "重心後退+失速": "腰が前に出ず重心が後ろへ戻ると、その後の加速が積み上がりません。まず重心を前方に保つことを優先した方が変わりやすいです。",
        "総崩れ初心者": "まずは情報を絞り、最初の一歩と押し出しだけに集中した方が動きが変わりやすいです。",
        "骨盤後傾+腕遅れ": "骨盤が後傾したまま腕だけ直しても推進力は変わりにくいので、まずは土台から整える必要があります。",
        "高離台+腕遅れ": "離台の角度が立ったままでは後の動きが連鎖的に崩れるので、まず出だしの形を整える方が効果的です。",
        "3歩目以降の失速": "離台と一歩目は機能しているので、今いちばん効くのは3歩目以降の押し切りを切らさないことです。",
        "過緊張": "全身が力んでいる状態では細かい技術を入れても動きにくいので、まず脱力だけに絞った方が変わりやすいです。",
        "力み+早起き": "緊張で体が固まったままでは前傾も保ちにくいので、まず脱力を作ってから低く出る形を整える方が変化が出やすいです。",
        "離台良好+一歩目詰まり": "離台の形はできているので、今いちばん効くのは一歩目の接地位置だけを直すことです。良い出だしをそのまま一歩目につなげることが最短です。",
        "一二歩良好+三歩目失速": "一・二歩目の質は保てているので、三歩目以降の押し切りだけに絞って直す方が、良い流れを崩さずに改善できます。",
    }
    return reasons.get(priority_plan.get("rule_name", ""), "")


def _build_practice_recommendations(coaching_focus: list[dict[str, str]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for item in coaching_focus:
        score_key = _score_key_from_title(item.get("title", ""))
        if not score_key:
            continue
        drill = DRILL_LIBRARY.get(score_key)
        if not drill or drill["title"] in seen_titles:
            continue
        recommendations.append(
            {
                "title": drill["title"],
                "drills": drill["drills"],
                "focus": drill["focus"],
                "suggestion": drill["suggestion"],
                "pitfalls": drill.get("pitfalls", []),
            }
        )
        seen_titles.add(drill["title"])
        if len(recommendations) == 2:
            break
    return recommendations


def _ensure_practice_recommendations(feedback: dict[str, Any]) -> list[dict[str, Any]]:
    coaching_focus = feedback.get("coaching_focus")
    if isinstance(coaching_focus, list):
        normalized_focus = [item for item in coaching_focus if isinstance(item, dict)]
        recommendations = _build_practice_recommendations(normalized_focus)
        if recommendations:
            return recommendations

    inferred_titles: list[str] = []

    mechanics_overview = feedback.get("mechanics_overview")
    if isinstance(mechanics_overview, list):
        for item in mechanics_overview:
            if isinstance(item, dict):
                title = item.get("title")
                if isinstance(title, str) and title:
                    inferred_titles.append(title)

    priorities = feedback.get("priorities")
    if isinstance(priorities, list):
        for item in priorities:
            if isinstance(item, str) and item:
                inferred_titles.append(item)

    diagnosis = str(feedback.get("primary_diagnosis") or "")
    if "ブレーキ" in diagnosis or "前に出すぎ" in diagnosis:
        inferred_titles.append("最初の一歩")
    if "上に逃げ" in diagnosis or "低く前" in diagnosis:
        inferred_titles.append("前への出方")
    if "踏んだ力" in diagnosis or "押し切" in diagnosis:
        inferred_titles.append("地面の押し方")
    if "回転" in diagnosis or "3歩" in diagnosis or "流れ" in diagnosis:
        inferred_titles.append("加速のつながり")
    if "腕" in diagnosis or "タイミング" in diagnosis:
        inferred_titles.append("腕と脚の合わせ")
    if "姿勢" in diagnosis or "構え" in diagnosis:
        inferred_titles.append("スタートの構え")

    seen_titles: set[str] = set()
    inferred_focus = []
    for title in inferred_titles:
        score_key = _score_key_from_title(title)
        if not score_key or title in seen_titles:
            continue
        inferred_focus.append({"title": SCORE_LABELS[score_key]})
        seen_titles.add(title)

    recommendations = _build_practice_recommendations(inferred_focus)
    if recommendations:
        return recommendations

    return [
        {
            "title": "スタート基礎を整えるドリル",
            "drills": ["壁押しスタート", "3歩限定スタート反復"],
            "focus": "最初の3歩で低く前に出る形と、一歩ごとに押して進む感覚をまとめて作ります。",
            "suggestion": "まずは壁押しスタートと3歩限定の反復を行い、低い姿勢のまま一歩ごとに地面を押して前に進む感覚を整えてください。細かいことより、最初の3歩の流れをそろえることを優先しましょう。",
            "pitfalls": [
                "最初から速く動こうとして形を崩さないこと",
                "一歩目だけで終わらず、三歩目まで同じ流れを続けること",
            ],
        }
    ]


def _score_key_from_title(title: str) -> str | None:
    for key, label in SCORE_LABELS.items():
        if label == title:
            return key
    return None
