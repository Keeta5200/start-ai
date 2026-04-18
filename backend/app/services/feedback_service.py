from __future__ import annotations

import hashlib
from typing import Any


SCORE_LABELS = {
    "start_posture": "セットポジション",
    "push_direction": "ドライブ方向",
    "first_step_landing": "一歩目接地",
    "ground_contact": "接地推進力",
    "forward_com": "重心前進連続性",
    "arm_leg_coordination": "腕脚協調",
}

PRIMARY_DIAGNOSIS_LABELS = {
    "vertical leakage": "ドライブ局面で推進ベクトルが上方に偏位しており、水平推進力が減衰しています。",
    "weak ground contact": "接地反力の水平分力への変換効率が低く、各接地で推進力損失が生じています。",
    "overreaching first step": "一歩目の接地位置が重心前方に超過しており、ブレーキング接地が発生しています。",
    "disconnected motion": "腕振りと脚の切り返しの位相がずれており、推進力の伝達効率が低下しています。",
    "limited drive posture": "セットポジションでの体幹前傾角・骨盤高が不十分で、爆発的なドライブ局面への移行準備が不足しています。",
    "event detection unstable": "映像条件の制約により、今回の動作解析の信頼度が限定的です。",
    "broken forward progression": "初期加速局面でストライドごとの重心前進が不連続となり、ピッチ先行型のパターンが顕在化しています。",
    "suboptimal set posture": "セットポジションの体幹前傾角・骨盤高に改善余地があり、低重心での水平加速準備が不十分です。",
    "balanced acceleration profile": "主要動作指標に大きな逸脱はなく、基礎的な加速パターンが形成されています。",
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
    if "信頼度が限定的" in diagnosis:
        return "まず映像条件を整え、セットから3歩目まで全身が安定して捉えられる状態で再解析することを推奨します。"
    if strengths:
        return f"{_ensure_sentence(strengths[0])} 一方、{_to_clause(diagnosis)}"
    return _ensure_sentence(diagnosis)


def _summary(diagnosis: str, priorities: list[str]) -> str:
    if "信頼度が限定的" in diagnosis:
        return "今回の解析は参考値として扱い、次回は足部・骨盤ラインが途切れない映像でセットから3歩目までを再評価してください。"
    if not priorities:
        return "主要動作指標に大きな逸脱はなく、初期加速の基礎パターンは安定しています。"
    if len(priorities) == 1:
        return f"今回は特に{priorities[0]}の改善が、初期加速局面の推進効率向上に直結します。"
    return f"今回は特に{priorities[0]}と{priorities[1]}の改善により、最初の3ストライドの推進力連続性が高まります。"


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
                "title": "映像条件の最適化",
                "ideal": "セットポジションから3歩目の接地まで、足部・骨盤・肩ラインが全フレームで安定して検出できる映像が理想です。",
                "current": "今回は接地イベントまたは開始局面の検出精度が低く、動作指標の信頼性が制限されました。",
                "action": "次回は側面固定カメラで、セット前から3歩目通過まで全身が途切れないよう、やや広角で撮影してください。",
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
            "接地反力の水平分力への変換効率が高く、推進力の基礎は良好な水準にあります。",
            "各接地で骨盤前進が確保されており、地面反力を推進ベクトルへ転換する能力は安定しています。",
            "接地局面での反力獲得と骨盤前進への変換ロスが少なく、接地推進の土台ができています。",
        ],
        "push_direction": [
            "ドライブ局面の推進ベクトルが水平寄りにまとまっており、低重心での加速出力が確保されています。",
            "スタート直後の骨盤前進量が十分確保され、ドライブ方向の精度は高い水準です。",
            "初期ドライブで水平分力優位のパターンが形成されており、前方推進への力の集約ができています。",
        ],
        "first_step_landing": [
            "一歩目の接地位置が重心直下付近に収まっており、ブレーキング成分が抑制されています。",
            "一歩目スイッチの接地精度が高く、前方超過による減速インパクトが最小限に抑えられています。",
            "一歩目で足部が重心前方に出過ぎることなく、接地位置の適正性は良好です。",
        ],
        "forward_com": [
            "初期加速局面での重心前進連続性が保たれており、3ストライドにわたる推進の連結が機能しています。",
            "骨盤の前進速度が各接地間で途絶せず、加速リズムが安定して形成されています。",
            "ストライドごとの推進量が均一に近く、ピッチと重心前進のバランスが保たれています。",
        ],
        "arm_leg_coordination": [
            "腕振りと脚の切り返しの位相が同期しており、推進力の伝達効率が高い状態です。",
            "各接地局面での腕脚協調パターンが安定しており、上下肢の連動による推進補強が機能しています。",
            "腕振り振幅と脚の切り返しタイミングが乱れておらず、エネルギー損失が最小化されています。",
        ],
    }
    default_variants = [
        "セットポジションの体幹前傾角・骨盤高は適正範囲内にあり、ドライブ局面への移行準備姿勢が整っています。",
        "セットポジションでの加速準備姿勢に大きな逸脱はなく、ドライブ移行の土台が形成されています。",
        "スタート準備姿勢の主要指標が適正範囲に収まっており、初期ドライブへの移行に支障はありません。",
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
            return "各接地で地面反力がスピードに直結しています。推進変換の効率は非常に高い水準です。"
        if score >= 7.0:
            return "接地反力をスピードに変換できており、推進への連結は安定しています。"
        if score >= 5.8:
            return "接地反力の一部がスピードに変換されていません。改善すると加速出力が直接上がります。"
        return "接地がスピードに変換されておらず、毎歩ごとに大きなロスが発生しています。"
    if score_key == "push_direction":
        if score >= 8.5:
            return "ドライブ方向が理想に近く、力がほぼそのままスピードに変換されています。"
        if score >= 7.0:
            return "ドライブ方向は前向きにまとまっており、スピードへの変換効率は良好です。"
        if score >= 5.8:
            return "ドライブ時に力が上方に逃げており、スピードへの変換効率が低下しています。"
        return "推進力が大きく上方向に漏れており、スピード獲得の主な阻害要因になっています。"
    if score_key == "first_step_landing":
        if score >= 8.5:
            return "一歩目接地のブレーキング成分がほぼゼロで、スピードのロスなく加速に移行できています。"
        if score >= 7.0:
            return "一歩目接地のブレーキング成分は少なく、スピードの継続性は良好です。"
        if score >= 5.8:
            return "一歩目接地でわずかなブレーキングが生じており、スピードの一部が失われています。"
        return "一歩目のブレーキング接地が顕著で、スピードへの大きなロスが発生しています。"
    if score_key == "forward_com":
        if score >= 8.5:
            return "3ストライドを通じた加速連続性が高く、スピードが効率よく積み上がっています。"
        if score >= 7.0:
            return "初期加速のリズムは整っており、スピードを連続して積み上げられています。"
        if score >= 5.8:
            return "ストライド間でスピードの積み上げが途切れやすく、加速効率の改善余地があります。"
        return "初期加速でスピードが連続して積み上がらず、3歩での加速効率が低い状態です。"
    if score >= 7.0:
        return "セットポジションは適正で、スタートシグナルへの即応準備が整っています。"
    return "セットポジションに改善余地があり、初期ドライブのスピード出力に影響しています。"


def _ideal_text(score_key: str) -> str:
    ideals: dict[str, str] = {
        "ground_contact": (
            "理想は、各接地で股関節伸展を最大化し、地面反力の水平分力が骨盤前進に直結することです。"
            "接地時間は適切な範囲に収まり、過短・過長ともに推進効率を低下させます。"
        ),
        "push_direction": (
            "理想は、ブロックアウト直後から体幹前傾を維持し、骨盤の水平前進量が垂直上昇量を大きく上回ることです。"
            "水平・垂直比が高いほど推進ベクトルが進行方向に収束し、加速効率が高まります。"
        ),
        "first_step_landing": (
            "理想は、一歩目の接地位置が骨盤直下付近に収まり、ブレーキング接地成分が最小化されることです。"
            "股関節屈曲からの素早い切り返しによって足部を重心直下へ引き戻すことが鍵になります。"
        ),
        "forward_com": (
            "理想は、1歩目から3歩目にかけて骨盤の前進速度が単調に増加し、各ストライドで推進が連結されることです。"
            "ピッチの急増より重心前進の連続性を優先することが初期加速の効率を高めます。"
        ),
        "arm_leg_coordination": (
            "理想は、各接地局面で対側腕が後方に強く引かれ、脚の切り返しと腕の引き動作が同位相で連動することです。"
            "腕振り振幅が十分に確保されることで推進補強の効果が最大化されます。"
        ),
        "start_posture": (
            "理想は、セットポジションで体幹前傾角を確保し、骨盤が低位に保たれた状態でスタートシグナルに反応できることです。"
            "低い前傾姿勢からドライブ局面へ移行することで、初期の水平推進力を最大化できます。"
        ),
    }
    return ideals.get(score_key, "理想は、セットポジションで加速準備姿勢が整い、ドライブ局面への移行が即座に行えることです。")


def _current_text(score_key: str, detail: dict[str, Any], score: float) -> str:
    measurements = detail.get("measurements", {}) if isinstance(detail, dict) else {}
    reasons = detail.get("deduction_reasons", []) if isinstance(detail, dict) else []
    if reasons:
        return _deduction_to_current_text(score_key, str(reasons[0]), score)

    if score_key == "ground_contact":
        progress = _measurement(measurements, "mean_pelvis_progress_ratio")
        if progress is not None and progress >= 0.35:
            return _variant([
                f"現在、接地後の骨盤前進は確認されますが（前進比率: {progress:.2f}）、接地反力の後方押し切りをより完全に行う余地があります。",
                f"接地推進は機能していますが（骨盤前進比率: {progress:.2f}）、股関節伸展の最終局面まで押し切ることで推進力をさらに引き出せます。",
                f"骨盤前進比率 {progress:.2f} は参考水準を確保していますが、トップレベル基準への到達にはもう一段の押し切りが必要です。",
            ], score)
        if score >= 6.5:
            return _variant([
                "現在、接地での支持は確保されていますが、股関節伸展による後方への押し切りが不十分で、反力の水平分力が十分に得られていません。",
                "接地支持はできていますが、骨盤前進量が目標値に達しておらず、地面への押し込みが推進に十分変換されていません。",
            ], score)
        return _variant([
            "現在、接地時間に対して骨盤前進量が不足しており、接地反力の推進ベクトルへの変換効率が低い状態です。",
            "接地で地面反力を十分に獲得できていないか、反力が垂直方向に逃げており、水平推進力への変換が非効率です。",
            "各接地で骨盤が前方へ運ばれる前に支持が終了しており、推進力の損失が繰り返し発生しています。",
        ], score)

    if score_key == "push_direction":
        vertical = _measurement(measurements, "pelvis_vertical_rise_ratio")
        progress = _measurement(measurements, "pelvis_forward_progress_ratio")
        if vertical is not None and vertical <= 0.45:
            v_str = f"{vertical:.2f}"
            return _variant([
                f"現在、ドライブ方向は大きく逸脱していませんが（垂直上昇比率: {v_str}）、水平推進への収束をさらに高める余地があります。",
                f"推進ベクトルの上方偏位は軽度ですが（垂直比率: {v_str}）、低重心維持の延長によって前方収束の効率をさらに改善できます。",
            ], score)
        if score >= 6.5:
            return _variant([
                "現在、ドライブ方向は概ね適正ですが、ブロックアウト直後に体幹が起き始め、推進ベクトルが上方にわずかに偏位しています。",
                "ドライブ角は許容範囲内ですが、体幹前傾の早期喪失により水平分力の損失が発生しています。",
            ], score)
        return _variant([
            "現在、ドライブ局面で推進ベクトルが上方に偏位しており、垂直方向への力の漏れが水平推進力を減衰させています。",
            "ドライブ局面での骨盤垂直上昇が過剰で、水平推進力の獲得が制限されています。体幹の早期直立が主因です。",
            "スタート直後の推進方向が垂直寄りになっており、水平方向への力積の蓄積が不十分な状態です。",
        ], score)

    if score_key == "first_step_landing":
        landing = _measurement(measurements, "foot_to_pelvis_ratio")
        if landing is not None:
            l_str = f"{landing:.2f}"
            if landing <= 0.20:
                return _variant([
                    f"現在、一歩目の接地位置は骨盤近傍に収まっており（前方超過比率: {l_str}）、ブレーキング接地の抑制は良好です。",
                    f"一歩目接地は重心直下付近に収束しており（骨盤前方比率: {l_str}）、前方超過による減速インパクトは最小限です。",
                ], score)
            if score >= 6.5:
                return _variant([
                    f"現在、一歩目の接地位置がわずかに重心前方に超過しており（前方比率: {l_str}）、軽度のブレーキング成分が生じています。",
                    f"一歩目接地に軽度の前方超過が認められ（比率: {l_str}）、接地反力のブレーキング成分が推進効率を低下させています。",
                ], score)
        return _variant([
            "現在、一歩目の接地位置が重心の前方に超過しており、ブレーキング接地による推進力損失が顕著です。",
            "一歩目接地で足部が過度に重心前方に出ており、接地反力が推進方向と逆行するブレーキングフォースを生成しています。",
            "一歩目のスイッチ動作で足部の引き戻しが間に合わず、前方接地によるブレーキング接地が繰り返されています。",
        ], score)

    if score_key == "forward_com":
        rhythm = _measurement(measurements, "step_progression_variation")
        if rhythm is not None and rhythm <= 0.45:
            r_str = f"{rhythm:.2f}"
            return _variant([
                f"現在、3ストライドの重心前進連続性は概ね維持されていますが（リズム変動係数: {r_str}）、トップ水準への精度向上の余地があります。",
                f"加速連続性はほぼ確保されていますが（変動係数: {r_str}）、ストライドごとの推進量の均一性をさらに高めることが課題です。",
            ], score)
        if score >= 6.5:
            return _variant([
                "現在、加速の流れは形成されていますが、後半ストライドでピッチが先行して増加し、重心前進が追いつかない場面があります。",
                "骨盤の前進傾向は確認できますが、2歩目以降でピッチ先行型のパターンが現れ、推進連続性が低下しています。",
            ], score)
        return _variant([
            "現在、ストライドごとの骨盤前進が不連続で、初期加速局面での推進連続性が低い状態です。ピッチ先行型のパターンが顕在化しています。",
            "各接地間で重心前進が途絶しやすく、速度増加がピッチ依存になっています。垂直振動も加速効率を阻害しています。",
            "3ストライドを通じた骨盤の単調前進が維持されておらず、加速リズムが乱れやすい状態です。",
        ], score)

    if score_key == "arm_leg_coordination":
        return _variant([
            "現在、ドライブ局面で腕振りと脚の切り返しの位相がずれており、腕脚協調による推進補強が十分に機能していません。",
            "各接地で対側腕の引き動作と脚の切り返しタイミングが同期せず、上下肢の連動による推進効率が損なわれています。",
            "腕振り振幅が不足しているか、脚の接地タイミングとの位相差が大きく、腕脚協調による推進補強が発揮されていません。",
        ], score)

    return _variant([
        "現在、セットポジションで体幹の前傾角が不足しており、ドライブ局面への移行時に早期の起き上がりが生じやすい状態です。",
        "セットポジションの骨盤高または体幹前傾角が適正範囲を外れており、初期ドライブの推進方向に影響しています。",
    ], score)


def _action_text(score_key: str, detail: dict[str, Any], score: float) -> str:
    if score_key == "ground_contact":
        if score >= 7.5:
            return _variant([
                "現状の接地推進力を維持しつつ、股関節伸展の最終局面をより完全に使って後方への押し切りをもう一段深めてください。",
                "接地の強度を保ちながら、支持脚の股関節が完全に伸展するまで押し切り、接地時間を適切な範囲で確保してください。",
                "推進の質を維持しながら、接地ごとに骨盤が前方へ運ばれるまで押し切りを完了させる意識を強めてください。",
            ], score)
        if score >= 6.5:
            return _variant([
                "接地での支持を素早く推進に変換するため、股関節伸展を意識しながら地面を後方に押し切り、骨盤を前方に運んでください。",
                "接地時に足部を止めず、股関節伸展と足首底屈を連動させて後方に押し切り、接地反力を骨盤前進に転換してください。",
            ], score)
        return _variant([
            "各接地で「当てる」接地から「押し切る」接地へ切り替えてください。股関節伸展を最大化し、骨盤が前方へ運ばれるまで支持脚を伸展させ続けてください。",
            "接地反力を推進に変換するため、足部接地後に股関節を積極的に伸展し、体重を前方に乗せながら後方へ押し切る動作を強化してください。",
            "接地ごとに地面を後方へ押し切る動作を徹底し、骨盤前進が確認できるまで支持を継続する意識で1歩目から取り組んでください。",
        ], score)

    if score_key == "push_direction":
        if score >= 7.5:
            return _variant([
                "現状のドライブ方向を維持しながら、体幹前傾の維持時間をさらに延ばし、骨盤の垂直上昇が始まるタイミングを遅らせてください。",
                "現在の前傾維持を保ちつつ、視線を前方3〜5m先の床面に向けることで体幹の早期起き上がりを抑制してください。",
            ], score)
        if score >= 6.5:
            return _variant([
                "ブロックアウト直後に頭部から起き上がらず、頭頂から骨盤までを一直線に保ちながら、斜め前方へ全身を投射するイメージで出てください。",
                "ドライブ局面では胸を早期に起こさず、骨盤と肩を同時に低く前方へ送り出すことで推進ベクトルの水平成分を確保してください。",
            ], score)
        return _variant([
            "スタート直後から体幹前傾を維持し、骨盤の垂直上昇を最小化してください。頭部・胸部の早期起き上がりは水平推進力の損失に直結します。",
            "ドライブ局面で全身を低く前方に投射することを意識し、骨盤が垂直上昇するより先に水平前進を獲得するパターンを作ってください。",
            "体幹の早期直立を防ぐため、スタートシグナル後は視線を前方低めに固定し、低重心のまま3歩目まで前傾を保ち続けてください。",
        ], score)

    if score_key == "first_step_landing":
        if score >= 7.5:
            return _variant([
                "一歩目の接地精度を維持しつつ、股関節屈曲から切り返しへの遷移を速め、接地位置をさらに重心直下に近づけてください。",
                "現在の接地位置の適正性を保ちながら、スイッチ動作での足部引き戻しスピードをさらに上げ、切り返しの鋭さを高めてください。",
            ], score)
        if score >= 6.5:
            return _variant([
                "一歩目で足部を前方に「置きに行く」動作を排除し、股関節の積極的な切り返しで足部を重心直下へ素早く引き戻すことを意識してください。",
                "一歩目スイッチで足部が前方に流れないよう、ハムストリングスの引き戻しを早めに起動させ、骨盤直下への接地を意識してください。",
            ], score)
        return _variant([
            "一歩目接地で足部が重心前方に出ないよう、股関節屈曲後の切り返しを素早く行い、足部を体の下に引きつけながら接地してください。前方への「置き」接地を完全に排除することが最優先です。",
            "一歩目のブレーキング接地を解消するため、スイッチ動作の始動を早め、接地位置を骨盤の前方超過ゾーンから直下へ修正してください。ハムストリングスの積極的な引き込み動作が鍵です。",
            "一歩目スイッチで足部を前方ではなく下方へ引き戻すイメージを持ち、接地時の骨盤直下への収束を意識して繰り返し練習してください。",
        ], score)

    if score_key == "forward_com":
        if score >= 7.5:
            return _variant([
                "現状の加速連続性を保ちながら、3歩目以降でピッチを急増させず、骨盤前進の連続から速度増加を獲得するパターンを維持してください。",
                "重心前進の連続性を維持しつつ、後半ストライドでの垂直振動をさらに抑え、水平方向への推進効率を高めてください。",
            ], score)
        if score >= 6.5:
            return _variant([
                "2歩目から3歩目でピッチを急に上げず、各接地で骨盤が前方へ運ばれるまで推進を完了させてから次のストライドへ移ってください。",
                "ピッチ先行型のパターンを修正するため、各ストライドで接地から骨盤前進への変換を完了させることを優先し、ピッチより推進の連続性を意識してください。",
            ], score)
        return _variant([
            "1歩目から3歩目までピッチを急増させず、各接地で地面を押し切って骨盤を前方へ運ぶことを優先してください。速度はピッチを急いでも得られず、推進の連続から生まれます。",
            "初期加速での推進連続性を回復するため、各接地間で骨盤が前方に運ばれるまで次のストライドへの移行を待ち、ストライドごとの推進サイクルを完結させてください。",
            "ピッチ先行を防ぐため、1歩ごとに「押し切ってから次へ」のリズムを作り、3ストライドを通じた重心前進の連続性を最優先にしてください。",
        ], score)

    if score_key == "arm_leg_coordination":
        return _variant([
            "各接地タイミングに合わせて対側腕を後方に強く引き、脚の切り返しと腕の引き動作を同期させてください。腕振りが脚の推進を補強する構造を作ることが重要です。",
            "腕振り振幅を十分に確保し、脚の接地と対称腕の後方引き動作のタイミングを一致させてください。腕脚の協調タイミングが推進力の伝達効率を決定します。",
            "腕振りと脚の切り返しの位相を合わせるため、接地の瞬間に反対腕の肘を後方に強く引く動作を意識し、上下肢の同期を作ってください。",
        ], score)

    return _variant([
        "セットポジションで体幹前傾角を確保し、骨盤を低位に保ったままスタートシグナルに反応してください。早期の起き上がりはドライブ局面の推進力損失に直結します。",
        "スタートの準備姿勢で低い前傾を維持し、体重を前方へ移動させながらドライブ局面に入ることで、初期の水平推進力を最大化してください。",
    ], score)


def _deduction_to_current_text(score_key: str, reason: str, score: float = 0.0) -> str:
    lower_reason = reason.lower()
    if any(kw in lower_reason for kw in ("unreliable", "incomplete", "could not", "not detected")):
        return _variant([
            "今回の映像では該当局面の動作検出精度が低く、信頼性の高い所見の提示が困難です。",
            "映像条件の制約により、この局面の動作指標が十分な精度で算出できず、所見は参考値として扱ってください。",
        ], score)
    if score_key == "ground_contact":
        if "contact" in lower_reason or "push" in lower_reason:
            return _variant([
                "接地反力が水平推進力へ変換される前に接地が終了しており、推進力損失が各接地で発生しています。",
                "接地での押し切りが不十分で、反力を推進ベクトルに変換できずに接地が終わるパターンが確認されます。",
            ], score)
        if "vertical" in lower_reason:
            return _variant([
                "接地後に骨盤が垂直方向に上昇しやすく、地面反力が推進ではなく垂直変位に消費されています。",
                "接地局面での骨盤垂直上昇が過剰で、水平推進力の生成効率が低下しています。",
            ], score)
    if score_key == "push_direction":
        return _variant([
            "ドライブ局面で推進ベクトルが上方向に偏位し、水平推進力が有効に獲得できていません。",
            "スタート直後の推進方向が垂直寄りになっており、水平方向への力積の蓄積が不十分です。",
        ], score)
    if score_key == "first_step_landing":
        return _variant([
            "一歩目の接地位置が重心前方に超過しており、ブレーキング接地による推進力損失が確認されます。",
            "一歩目で足部が重心の前方に出るブレーキング接地パターンが検出されました。",
        ], score)
    if score_key == "forward_com":
        return _variant([
            "初期加速局面でストライドごとの重心前進が不連続となり、ピッチ先行型の加速パターンが生じています。",
            "3ストライド間で骨盤前進の連続性が維持されず、速度増加がピッチ依存になっています。",
        ], score)
    if score_key == "arm_leg_coordination":
        return _variant([
            "腕振りと脚の切り返しの位相が同期しておらず、推進力の伝達において腕脚協調が機能していません。",
            "各接地で腕脚のタイミングがずれており、上下肢の協調による推進補強が発揮されていません。",
        ], score)
    return _variant([
        "セットポジションでの体幹前傾角または骨盤高が適正範囲を外れており、ドライブ局面への移行に支障が生じています。",
        "スタート準備姿勢に問題があり、初期ドライブの推進方向に影響が出ています。",
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
