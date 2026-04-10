from __future__ import annotations


def build_team_match_takeaways(team_name: str, metrics: dict[str, float]) -> list[str]:
    takeaways: list[str] = []

    left_share = metrics.get("left_lane_build_up_share", 0.0)
    right_share = metrics.get("right_lane_build_up_share", 0.0)
    high_regains = metrics.get("high_regains", 0.0)

    if left_share > 0.4:
        takeaways.append(f"{team_name} leaned heavily on the left lane in the early build-up.")
    elif right_share > 0.4:
        takeaways.append(f"{team_name} favored the right lane as the first progression route.")

    if high_regains >= 8:
        takeaways.append(f"{team_name} recovered possession high often enough to suggest an aggressive pressing plan.")

    if not takeaways:
        takeaways.append(f"{team_name} showed a balanced profile in the current metric set.")

    return takeaways

