import pytest
from app.app_utils.burnout_model import calculate_burnout_risk_score

def test_high_burnout_risk():
    # High volume (+30%), poor sleep (<7), negative mood days (>0)
    score = calculate_burnout_risk_score(
        recent_volume=13000, 
        baseline_volume=10000, 
        avg_sleep=6.5, 
        negative_mood_days=2
    )
    assert score > 80

def test_low_burnout_risk():
    # Normal volume, good sleep, no negative mood
    score = calculate_burnout_risk_score(
        recent_volume=10000, 
        baseline_volume=10000, 
        avg_sleep=8.0, 
        negative_mood_days=0
    )
    assert score < 40

def test_moderate_burnout_risk_volume_only():
    # High volume, but good sleep and mood
    score = calculate_burnout_risk_score(
        recent_volume=14000, 
        baseline_volume=10000, 
        avg_sleep=7.5, 
        negative_mood_days=0
    )
    assert 40 <= score <= 80

def test_moderate_burnout_risk_sleep_only():
    # Normal volume, poor sleep
    score = calculate_burnout_risk_score(
        recent_volume=10000, 
        baseline_volume=10000, 
        avg_sleep=5.5, 
        negative_mood_days=0
    )
    assert 40 <= score <= 80

def test_score_capped_at_100():
    # Extreme conditions
    score = calculate_burnout_risk_score(
        recent_volume=20000, 
        baseline_volume=10000, 
        avg_sleep=3.0, 
        negative_mood_days=7
    )
    assert score == 100

def test_score_floored_at_0():
    # Perfect conditions, very low volume
    score = calculate_burnout_risk_score(
        recent_volume=1000, 
        baseline_volume=10000, 
        avg_sleep=9.0, 
        negative_mood_days=0
    )
    assert score == 0
