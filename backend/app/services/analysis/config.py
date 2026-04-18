from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisTuning:
    min_landmark_visibility: float = 0.55
    min_presence_confidence: float = 0.50
    moving_average_window: int = 7
    early_window_ratio: float = 0.22
    minimum_frames_required: int = 5
    preferred_minimum_frames: int = 18

    low_confidence_visibility_ratio: float = 0.58
    warning_visibility_ratio: float = 0.70
    low_detected_frame_ratio: float = 0.60
    edge_margin_ratio: float = 0.06
    cut_off_frame_ratio_warning: float = 0.25

    movement_energy_threshold: float = 0.35
    movement_confirmation_frames: int = 2
    initiation_velocity_threshold: float = 0.35

    contact_ground_tolerance_ratio: float = 0.20
    contact_speed_threshold: float = 3.5
    contact_candidate_score_threshold: float = 0.38
    contact_min_spacing_frames: int = 3
    contact_max_spacing_frames: int = 22
    contact_pre_start_frames: int = 8
    contact_scan_window_frames: int = 8
    max_contact_duration_frames: float = 12.0

    low_drive_vertical_rise_ratio: float = 0.45
    strong_forward_progress_ratio: float = 1.05
    push_direction_window_frames: int = 12
    push_direction_vertical_weight: float = 1.35

    first_step_overreach_ratio: float = 0.32
    first_step_under_pelvis_bonus_ratio: float = 0.08
    first_step_switch_min_ratio: float = 0.15
    first_step_switch_good_ratio: float = 0.55

    ideal_contact_progress_ratio: float = 0.48
    ideal_contact_duration_frames: float = 6.0
    minimum_contact_duration_frames: float = 3.0
    excessive_impact_speed: float = 4.4

    max_vertical_oscillation_ratio: float = 0.55
    min_forward_monotonic_ratio: float = 0.72
    rhythm_late_surge_soft_ceiling: float = 1.35

    minimum_arm_swing_ratio: float = 0.35
    ideal_set_lean_ratio: float = 0.75
    start_posture_lean_tolerance: float = 0.40
    ideal_set_hip_height_ratio: float = 0.95
    start_posture_hip_tolerance: float = 0.90
    benchmark_event_tolerance_frames: int = 2
    benchmark_target_weight: float = 0.75
    debug_contact_window_padding: int = 8
    final_score_bias: float = 0.8


DEFAULT_ANALYSIS_TUNING = AnalysisTuning()
