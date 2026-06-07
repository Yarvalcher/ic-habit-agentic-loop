def calculate_burnout_risk_score(
    recent_volume: float, 
    baseline_volume: float, 
    avg_sleep: float, 
    negative_mood_days: int
) -> int:
    """
    Calculates a predictive burnout risk score from 0 to 100.
    
    Factors considered:
    1. Training Volume Spike: How much recent volume exceeds baseline.
    2. Sleep Quality: Penalty for sleeping less than 7.5 hours.
    3. Qualitative Mood: Penalty for consecutive negative mood days.
    """
    score = 0.0

    # 1. Volume Factor (up to 40 points)
    # 30% increase gives max 40 points
    if baseline_volume > 0 and recent_volume > baseline_volume:
        increase_pct = (recent_volume - baseline_volume) / baseline_volume
        volume_penalty = min(40, (increase_pct / 0.3) * 40)
        score += volume_penalty

    # 2. Sleep Factor (up to 40 points)
    # Optimal sleep is 7.5h. 2-hour deficit gives max 40 points.
    optimal_sleep = 7.5
    if avg_sleep < optimal_sleep:
        sleep_deficit = optimal_sleep - avg_sleep
        sleep_penalty = min(40, (sleep_deficit / 2.0) * 40)
        score += sleep_penalty

    # 3. Mood Factor (up to 40 points)
    # Each consecutive negative mood day gives 15 points
    mood_penalty = min(40, negative_mood_days * 15)
    score += mood_penalty

    # Ensure bounds
    final_score = int(max(0, min(100, round(score))))
    return final_score
