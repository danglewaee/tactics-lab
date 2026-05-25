from __future__ import annotations


def build_team_match_takeaways(team_name: str, metrics: dict[str, float]) -> list[str]:
    takeaways: list[str] = []

    left_share = metrics.get("left_lane_build_up_share", 0.0)
    center_share = metrics.get("center_lane_build_up_share", 0.0)
    right_share = metrics.get("right_lane_build_up_share", 0.0)
    field_tilt = metrics.get("field_tilt", 0.0)
    high_regains = metrics.get("high_regains", 0.0)

    if center_share >= 0.5:
        takeaways.append(f"{team_name} routed most first-phase progression through the center.")
    elif left_share >= 0.45:
        takeaways.append(f"{team_name} leaned heavily on the left lane in the early build-up.")
    elif right_share >= 0.45:
        takeaways.append(f"{team_name} favored the right lane as the first progression route.")

    if field_tilt >= 0.6:
        takeaways.append(f"{team_name} controlled a larger share of final-third actions than the opponent.")

    if high_regains >= 6:
        takeaways.append(f"{team_name} recovered possession high often enough to suggest sustained pressure after turnovers.")

    if not takeaways:
        takeaways.append(f"{team_name} showed a balanced profile in the current metric set.")

    return takeaways
