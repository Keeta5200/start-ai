from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.analysis.events import SprintEvents


@dataclass(frozen=True)
class BenchmarkReference:
    filename: str
    set_frame: int
    movement_frame: int
    first_contact_frame: int
    second_contact_frame: int
    third_contact_frame: int
    push_direction: float
    ground_contact: float
    first_step_switch: float
    rhythm_stability: float
    teacher_note: str


BENCHMARK_REFERENCES = {
    "ウォルシュ.MOV": BenchmarkReference(
        filename="ウォルシュ.MOV",
        set_frame=92,
        movement_frame=94,
        first_contact_frame=99,
        second_contact_frame=103,
        third_contact_frame=107,
        push_direction=9.5,
        ground_contact=9.0,
        first_step_switch=9.5,
        rhythm_stability=9.5,
        teacher_note="前方向への押し出し、切り替え、初期加速の連結が非常に滑らか。",
    ),
    "コールマン.MOV": BenchmarkReference(
        filename="コールマン.MOV",
        set_frame=54,
        movement_frame=57,
        first_contact_frame=61,
        second_contact_frame=65,
        third_contact_frame=70,
        push_direction=9.0,
        ground_contact=9.0,
        first_step_switch=9.0,
        rhythm_stability=9.0,
        teacher_note="無駄なく前に進む加速の基準として使いやすい。",
    ),
    "トンプソン.MP4": BenchmarkReference(
        filename="トンプソン.MP4",
        set_frame=62,
        movement_frame=64,
        first_contact_frame=68,
        second_contact_frame=74,
        third_contact_frame=80,
        push_direction=9.0,
        ground_contact=9.5,
        first_step_switch=9.0,
        rhythm_stability=9.5,
        teacher_note="前への出力は強く、接地で前進を作れている。",
    ),
    "ソヘイテイ.MP4": BenchmarkReference(
        filename="ソヘイテイ.MP4",
        set_frame=64,
        movement_frame=68,
        first_contact_frame=86,
        second_contact_frame=98,
        third_contact_frame=109,
        push_direction=9.5,
        ground_contact=9.0,
        first_step_switch=9.0,
        rhythm_stability=8.5,
        teacher_note="反力の受け方は良いが、最初の切り替えにわずかな長さが出る。",
    ),
    "桐生２.MP4": BenchmarkReference(
        filename="桐生２.MP4",
        set_frame=72,
        movement_frame=75,
        first_contact_frame=86,
        second_contact_frame=95,
        third_contact_frame=104,
        push_direction=9.0,
        ground_contact=9.0,
        first_step_switch=9.5,
        rhythm_stability=9.5,
        teacher_note="押し出しはかなり良く、一歩目の切り替えも鋭い。",
    ),
    "11.5.MOV": BenchmarkReference(
        filename="11.5.MOV",
        set_frame=93,
        movement_frame=95,
        first_contact_frame=106,
        second_contact_frame=112,
        third_contact_frame=118,
        push_direction=7.5,
        ground_contact=7.0,
        first_step_switch=7.0,
        rhythm_stability=7.5,
        teacher_note="押し出しは悪くないが、やや上方向へ逃げて前への運びが弱い。",
    ),
    "学生6.MP4": BenchmarkReference(
        filename="学生6.MP4",
        set_frame=56,
        movement_frame=57,
        first_contact_frame=64,
        second_contact_frame=71,
        third_contact_frame=79,
        push_direction=8.0,
        ground_contact=7.5,
        first_step_switch=7.5,
        rhythm_stability=8.0,
        teacher_note="11.5より流れは安定しているが、切り替えに少し未整理感が残る。",
    ),
}


def get_benchmark_reference(filename: str) -> Optional[BenchmarkReference]:
    return BENCHMARK_REFERENCES.get(filename)


def apply_benchmark_events(
    events: SprintEvents,
    reference: Optional[BenchmarkReference],
) -> SprintEvents:
    if reference is None:
        return events

    first_side = events.contact_legs.get("first") or "right"
    second_side = events.contact_legs.get("second") or ("left" if first_side == "right" else "right")
    third_side = events.contact_legs.get("third") or first_side

    return SprintEvents(
        set_position_frame=reference.set_frame,
        movement_initiation_frame=reference.movement_frame,
        first_ground_contact_frame=reference.first_contact_frame,
        second_step_contact_frame=reference.second_contact_frame,
        third_step_contact_frame=reference.third_contact_frame,
        contact_legs={
            "first": first_side,
            "second": second_side,
            "third": third_side,
        },
        debug={
            **events.debug,
            "benchmark_reference_applied": True,
            "benchmark_reference": {
                "filename": reference.filename,
                "set_frame": reference.set_frame,
                "movement_frame": reference.movement_frame,
                "first_contact_frame": reference.first_contact_frame,
                "second_contact_frame": reference.second_contact_frame,
                "third_contact_frame": reference.third_contact_frame,
            },
            "raw_detected_events": {
                "set_position_frame": events.set_position_frame,
                "movement_initiation_frame": events.movement_initiation_frame,
                "first_ground_contact_frame": events.first_ground_contact_frame,
                "second_step_contact_frame": events.second_step_contact_frame,
                "third_step_contact_frame": events.third_step_contact_frame,
            },
        },
    )
