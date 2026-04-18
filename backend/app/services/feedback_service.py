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


def _variant(variants: list[str], seed: float) -> str:
    idx = int(hashlib.md5(str(round(seed, 3)).encode()).hexdigest(), 16) % len(variants)
    return variants[idx]


def build_feedback_payload(
    scores: dict[str, float],
    score_details: dict[str, dict[str, Any]],
    primary_diagnosis: str,
) -> dict[str, Any]:
    localized_diagnosis = PRIMARY_DIAGNOSIS_LABELS.get(primary_diagnosis, primary_diagnosis)
    strengths = _strengths(scores)
    priorities = _priorities(scores)
    coaching_focus = _build_coaching_focus(scores, score_details)
    mechanics_overview = _build_mechanics_overview(scores)
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
        "next_session_focus": next_session_focus,
    }


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
    return f"今回は特に{priorities[0]}と{priorities[1]}を重点的に練習することで、最初の3歩が改善します。"


def _strengths(scores: dict[str, float]) -> list[str]:
    messages: list[str] = []
    for score_key, score_value in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:2]:
        if score_value >= 7.0:
            messages.append(_strength_message(score_key, score_value))
    return messages


def _priorities(scores: dict[str, float]) -> list[str]:
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

    for score_key, _ in _focus_priority_items(scores):
        items.append(
            {
                "title": SCORE_LABELS[score_key],
                "ideal": _ideal_text(score_key),
                "current": _current_text(score_key, score_details.get(score_key, {}), scores.get(score_key, 0.0)),
                "action": _action_text(score_key, score_details.get(score_key, {}), scores.get(score_key, 0.0)),
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
        ],
        "push_direction": [
            "スタート直後の力の向きが前向きにまとまっており、無駄なく加速できています。",
            "低く前に出る方向がしっかり出ており、力がスピードに変わっています。",
            "ドライブの方向は良好で、力が上に逃げずに前への加速につながっています。",
        ],
        "first_step_landing": [
            "一歩目の足の位置が体の近くに収まっており、ブレーキになっていません。",
            "一歩目で足が前に出すぎることなく、うまく体の下に落とせています。",
            "一歩目の接地がきれいで、スピードを落とさずに加速を続けられています。",
        ],
        "forward_com": [
            "3歩のスピードがつながっており、流れを途切れさせずに加速できています。",
            "1歩ずつスピードが乗っており、3歩を通じた加速のリズムができています。",
            "各ストライドでしっかり前に進んでおり、加速の連続性は良い状態です。",
        ],
        "arm_leg_coordination": [
            "腕と脚のタイミングが合っており、お互いを引っ張り合えています。",
            "腕振りと脚の切り替えが同じタイミングで動いており、連動ができています。",
            "腕脚の動きがそろっており、上半身と下半身がうまく協力できています。",
        ],
    }
    default_variants = [
        "セットポジションの姿勢は適正で、スタートの準備ができています。",
        "スタート前の姿勢に大きな崩れはなく、素直に出やすい形ができています。",
        "セットポジションは問題なく、ドライブに入りやすい状態です。",
    ]
    return _variant(variants.get(score_key, default_variants), score)


def _axis_status(score_key: str, score: float) -> str:
    if score >= 8.5:
        return "優秀"
    if score >= 7.0:
        return "良好"
    if score >= 5.8:
        return "要改善"
    return "重点改善"


def _axis_summary(score_key: str, score: float) -> str:
    if score_key == "ground_contact":
        if score >= 8.5:
            return "踏んだ力がそのままスピードになっています。接地の質はとても高い水準です。"
        if score >= 7.0:
            return "接地反力をスピードに変換できており、推進への連結は安定しています。"
        if score >= 5.8:
            return "踏んだ力の一部がスピードに変わりきっていません。改善すると加速がはっきり上がります。"
        return "踏んでもスピードに変わっていない状態で、1歩ごとにロスが出ています。"
    if score_key == "push_direction":
        if score >= 8.5:
            return "力の向きが前にそろっており、ほぼ全部がスピードに変わっています。"
        if score >= 7.0:
            return "ドライブ方向は前向きにまとまっており、スピードへの変換効率は良好です。"
        if score >= 5.8:
            return "力が上に逃げており、前へのスピードに変わる量が減っています。"
        return "力が上に大きく逃げており、スピードが出にくい状態の主な原因になっています。"
    if score_key == "first_step_landing":
        if score >= 8.5:
            return "一歩目でブレーキがほぼかかっておらず、スピードをロスなく加速に乗せられています。"
        if score >= 7.0:
            return "一歩目接地のブレーキング成分は少なく、スピードの継続性は良好です。"
        if score >= 5.8:
            return "一歩目で少しブレーキがかかっており、そこでスピードが落ちています。"
        return "一歩目のブレーキが大きく、せっかくのスタートのスピードが落ちてしまっています。"
    if score_key == "forward_com":
        if score >= 8.5:
            return "3歩を通じてスピードがきれいに積み上がっており、加速の流れが非常に良い状態です。"
        if score >= 7.0:
            return "初期加速のリズムは整っており、スピードを連続して積み上げられています。"
        if score >= 5.8:
            return "ストライドの間でスピードの流れが途切れやすく、加速の効率に改善余地があります。"
        return "3歩でスピードがうまく積み上がらず、足だけが速く回る状態になっています。"
    if score >= 7.0:
        return "セットポジションは問題なく、スタートの準備ができています。"
    return "セットポジションに改善余地があり、スタートのスピードに影響しています。"


def _ideal_text(score_key: str) -> str:
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
                "接地で地面を押す動きはできていますが、最後まで押し切る前に次の動作に移ってしまっています。もう少し粘れると、さらにスピードが出ます。",
                "踏む力はあります。ただ、もう半歩分だけ地面を押し続けられると、スピードへの変換がさらに高まります。",
            ], score)
        if score >= 6.5:
            return _variant([
                "接地はできていますが、地面に当てるだけで終わっている感じがあります。足が離れるまで後ろへ押す意識がもう少し必要です。",
                "踏み込みはできていますが、押し切る前に足が上がってしまっています。最後まで地面を蹴り続けることが課題です。",
            ], score)
        return _variant([
            "踏んでいますが、力がスピードに変わりきっていません。「当たっているだけ」の接地になっており、前に進む力が十分に出ていません。",
            "足が地面に触れているだけで、後ろへ押す動作が弱い状態です。踏んだ力がそのまま逃げてしまっています。",
            "接地のたびに力のロスが起きています。地面に当てるだけでなく、しっかり後ろへ押し切ることが必要です。",
        ], score)

    if score_key == "push_direction":
        if score >= 7.5:
            return _variant([
                "方向はほぼ前向きです。もう少し体を低く保てると、さらにスピードが乗ります。",
                "前への力は出ていますが、少しだけ上に力が逃げています。体の起き上がりをもう少し我慢できると改善します。",
            ], score)
        if score >= 6.5:
            return _variant([
                "スタート直後に体が少し早く起き上がっています。その分、力が上に逃げてスピードに変わりにくくなっています。",
                "出だしは良いですが、2〜3歩目で体が起き上がるのが早く、そこから力が前ではなく上に向かっています。",
            ], score)
        return _variant([
            "力が前ではなく上に向かっています。体の起き上がりが早いため、スピードに変わる前に力が逃げてしまっています。",
            "スタート直後から体が立ってしまっており、地面を蹴っても上に浮くような動きになっています。",
            "ドライブで力が上に逃げており、前に進む力が出にくい状態です。体を低く保つことが最優先です。",
        ], score)

    if score_key == "first_step_landing":
        if score >= 7.5:
            return _variant([
                "一歩目の足の位置はほぼ良いです。もう少し体の真下に近づけると、さらにブレーキが減ります。",
                "一歩目はうまく体の下に落とせています。足がほんの少し前に出ている場面があるので、そこだけ意識すると完璧です。",
            ], score)
        if score >= 6.5:
            return _variant([
                "一歩目で足が少し前に出すぎています。そこでわずかにブレーキがかかり、スピードが落ちています。",
                "一歩目の足の位置がやや前寄りです。体の下に引きつける動作をもう少し速くできるとブレーキが減ります。",
            ], score)
        return _variant([
            "一歩目で足が前に出すぎており、そこでブレーキになっています。足を前に置きに行く動作が出ているため、スピードが落ちています。",
            "一歩目の接地が体より前になっており、踏んだ瞬間にブレーキがかかっています。足を体の下に落とす意識が必要です。",
            "一歩目で足が流れており、ブレーキになっています。せっかくスタートで出した力がそこでロスになっています。",
        ], score)

    if score_key == "forward_com":
        if score >= 7.5:
            return _variant([
                "3歩の流れはつながっています。ただ、足だけが先に回る場面があり、体全体の前への流れをもう少し出せます。",
                "加速の流れはできていますが、3歩目あたりで足の回転が先走り、体が前に乗りきれていない瞬間があります。",
            ], score)
        if score >= 6.5:
            return _variant([
                "3歩の流れはありますが、途中で途切れる場面があります。足だけを速く動かそうとして、体が前についてきていない状態です。",
                "スピードが乗りかけているところで、足の回転だけが先に速くなり、体の前進が追いついていません。",
            ], score)
        return _variant([
            "3歩のスピードが途切れています。足だけが速く回ってしまい、体が前に進みきれていない状態です。",
            "足の回転は速くなっていますが、体全体が前に乗っていません。スピードが出ているように見えて、実際にはロスが続いています。",
            "加速の流れが1歩ごとに途切れており、スピードが積み上がっていきません。足だけが先走るパターンが出ています。",
        ], score)

    if score_key == "arm_leg_coordination":
        return _variant([
            "腕と脚のタイミングがずれています。脚が着いているときに腕の引きが間に合っておらず、お互いを引っ張り合えていません。",
            "腕振りと脚の切り替えがバラバラになっています。腕が引けないぶん、脚も前に出にくくなっています。",
            "腕の振りが弱いか、脚の動きとタイミングが合っていません。腕と脚をそろえることで前への力が増します。",
        ], score)

    return _variant([
        "セットポジションで体が少し高すぎます。もう少し低く構えると、最初から前に力強く出やすくなります。",
        "スタートの姿勢が高めで、出た瞬間に力が上に逃げやすい形になっています。",
    ], score)


def _action_text(score_key: str, detail: dict[str, Any], score: float) -> str:
    if score_key == "ground_contact":
        if score >= 7.5:
            return _variant([
                "接地の強さを保ちながら、足が地面を離れるまで後ろへ押し続けてください。「当てたら終わり」ではなく、「押し切ってから次へ」の感覚で。",
                "今の接地を維持しつつ、最後まで地面を蹴り続けることを意識してください。もう少し粘るだけでスピードが変わります。",
            ], score)
        if score >= 6.5:
            return _variant([
                "足が地面についたら、後ろへ押しながら腰を前に運ぶ感覚を大切に。「踏む」より「押す」イメージで接地してください。",
                "接地したあと、足の裏で地面を後ろに押し続けながら、体重を前に乗せていく意識を持ってください。",
            ], score)
        return _variant([
            "接地のたびに「地面を後ろへ押して、腰を前へ運ぶ」を意識してください。当てるだけで終わらず、最後まで押し切ることが大切です。",
            "踏んだ瞬間から後ろへ押す意識を持ち、体が前に乗るまで押し続けてください。「押し切ってから次の足」のリズムで走ってみてください。",
            "1歩ずつ地面をしっかり後ろへ押し切ることを最優先にしてください。スピードは押した分だけ返ってきます。",
        ], score)

    if score_key == "push_direction":
        if score >= 7.5:
            return _variant([
                "今の前傾姿勢を保ちながら、体を起こすのをもう少し我慢してください。3歩目まで頭を低く保つ意識で走ってみてください。",
                "体を起こしたくなる気持ちを我慢して、低いまま3歩進んでみてください。それだけでスピードが変わります。",
            ], score)
        if score >= 6.5:
            return _variant([
                "スタートから3歩は背中を水平に保ち、頭が低いまま前に出てください。早く体を起こさないことが大切です。",
                "出だしで胸を起こさず、体全体を低いまま斜め前に進んでください。頭の位置が低いほど前への力が出ます。",
            ], score)
        return _variant([
            "スタートから3歩は体を低く保ってください。頭が先に起き上がると力が上に逃げます。視線は前の地面に向けたまま、低く前に出る意識で。",
            "体を早く起こさないことが最優先です。頭から腰までを低く保ったまま、斜め前に全身を投げ出すイメージで出てください。",
            "低い姿勢を3歩間キープする練習をしてください。「まだ起きない、まだ起きない」と思いながら前に出るくらいがちょうど良いです。",
        ], score)

    if score_key == "first_step_landing":
        if score >= 7.5:
            return _variant([
                "今の接地位置を保ちながら、足を体の下に引きつける動作をさらに速くしてください。太ももの裏で引き寄せる感覚です。",
                "一歩目の接地を維持しつつ、足を落とすタイミングをもう少し早めてみてください。体の下に先に落とすイメージです。",
            ], score)
        if score >= 6.5:
            return _variant([
                "一歩目は足を前に「出す」のではなく、体の下に「落とす」感覚で。太ももの裏を使って足を引きつけながら接地してください。",
                "一歩目で足が前に流れないよう、太ももの裏側で引き戻しながら接地してください。体の下に落ちてくるイメージです。",
            ], score)
        return _variant([
            "一歩目は足を前に置きに行かないでください。体の下に落とすイメージで、太ももの裏を使って足を引きつけながら接地してください。前に出すのではなく「下ろす」感覚です。",
            "一歩目で足が前に出すぎています。足を前に「置く」のをやめて、体の真下に「引き落とす」動きに変えてください。ハムストリング（太もも裏）で引きつける意識です。",
            "一歩目スイッチで足を前ではなく下に向けて引き戻してください。体の下に先に足が来るようになると、ブレーキがなくなってスピードが続きます。",
        ], score)

    if score_key == "forward_com":
        if score >= 7.5:
            return _variant([
                "足の回転を急がず、1歩ごとに体が前に乗ってから次の足へ移ってください。「押してから進む」を3歩続ける意識で。",
                "ピッチを上げることより、体が前に乗り続けることを優先してください。流れが途切れないことがスピードにつながります。",
            ], score)
        if score >= 6.5:
            return _variant([
                "2〜3歩目で足だけを速く動かそうとしないでください。1歩ずつ地面を押して体が前に進んでから、次の足へ移るリズムを作ってください。",
                "ピッチより流れを大切に。1歩ごとに体重が前に移ってから次の足が出るリズムを意識すると、スピードが乗り続けます。",
            ], score)
        return _variant([
            "1歩目から3歩目まで、足の回転を急がず「押してから次へ」のリズムを守ってください。スピードは足を速く動かすことではなく、体が前に乗り続けることから生まれます。",
            "足だけが速く回るのをやめて、1歩ごとに体を前に乗せてから次の足へ移ってください。「乗ってから次へ」を3歩繰り返すだけでスピードが変わります。",
            "ピッチを急がず、1歩ずつしっかり押してから次へ進んでください。3歩の流れをつなげることが、スタートのスピードを上げる一番の近道です。",
        ], score)

    if score_key == "arm_leg_coordination":
        return _variant([
            "脚が地面に着く瞬間に、反対の腕を後ろに強く引いてください。腕が引けると、脚も自然に前に出やすくなります。腕と脚を同じタイミングで切り替える意識を持ってください。",
            "腕振りをもっと大きくして、脚の切り替えと同じタイミングで後ろに引いてください。腕と脚がそろうと、前への力が増します。",
            "次は、押し出しと同時に反対腕を強く後ろに引いて、腕と脚の切り替えタイミングを合わせてください。腕が引けると体全体が前に出やすくなります。",
        ], score)

    return _variant([
        "セットポジションでもう少し低く構えてください。腰を下げて体を前傾させた姿勢から出ると、最初から前への力が出やすくなります。",
        "スタートの姿勢を低くして、合図と同時に真っ直ぐ前に飛び出せる形を作ってください。低く構えるほど、最初の一歩が力強くなります。",
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
            "接地で地面に当たっているだけで、後ろへ押し切る動作が弱い状態です。",
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
            "ストライドのたびにスピードが止まりかけており、足の回転だけが先走っています。",
        ], score)
    if score_key == "arm_leg_coordination":
        return _variant([
            "腕と脚のタイミングがずれており、お互いを引っ張り合えていません。",
            "腕振りと脚の切り替えがバラバラで、連動した動きになっていません。",
        ], score)
    return _variant([
        "セットポジションの姿勢が高すぎて、最初から力が上に逃げやすい状態です。",
        "スタートの姿勢に問題があり、最初の一歩の力が十分に出にくくなっています。",
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


def _focus_priority_items(scores: dict[str, float]) -> list[tuple[str, float]]:
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
    selected: list[tuple[str, float]] = []
    for key, value in ordered:
        if key == "start_posture" and value >= 5.5:
            continue
        selected.append((key, value))
        if len(selected) == 3:
            break
    return selected
