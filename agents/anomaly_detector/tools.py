"""Anomaly Detector Agent - MCP tool implementations."""
from __future__ import annotations

import random
import statistics


def mcp_ml_predict(lot_id: str, features: dict | None = None) -> dict:
    """ML 모델 기반 이상 공정 예측 (Isolation Forest 시뮬레이션)."""
    random.seed(hash(lot_id) % 1000)

    # 입력 feature 값 (context에서 넘어온 SPC/Yield 결과 반영)
    anomaly_score = round(random.gauss(0.72, 0.12), 4)
    anomaly_score = max(0.0, min(1.0, anomaly_score))

    is_anomaly  = anomaly_score > 0.65
    confidence  = round(abs(anomaly_score - 0.5) * 2 * 100, 1)

    contributing = []
    if anomaly_score > 0.65:
        contributing = [
            {"feature": "gate_oxide_thickness", "importance": 0.42, "direction": "high"},
            {"feature": "chamber_temp_c",        "importance": 0.31, "direction": "high"},
            {"feature": "ooc_violation_count",   "importance": 0.27, "direction": "high"},
        ]

    return {
        "lot_id":          lot_id,
        "model":           "IsolationForest_v2.3",
        "anomaly_score":   anomaly_score,
        "threshold":       0.65,
        "is_anomaly":      is_anomaly,
        "confidence_pct":  confidence,
        "prediction":      "ANOMALY" if is_anomaly else "NORMAL",
        "contributing_features": contributing,
        "risk_level":      "HIGH" if anomaly_score > 0.80
                           else "MEDIUM" if anomaly_score > 0.65
                           else "LOW",
    }


def mcp_detect_drift(lot_id: str, parameter: str = "gate_oxide_thickness") -> dict:
    """공정 파라미터 드리프트 탐지 (CUSUM 알고리즘 시뮬레이션)."""
    random.seed(hash(lot_id) % 1000 + 2)

    target = 100.0
    # 최근 25개 측정값 (드리프트 패턴 삽입)
    values = [round(random.gauss(target + i * 0.15, 1.5), 2) for i in range(25)]
    mean   = statistics.mean(values)
    drift  = round(mean - target, 3)

    cusum_pos = 0.0
    cusum_neg = 0.0
    k = 0.5  # allowance
    cusum_scores = []
    for v in values:
        z = (v - target) / 2.0
        cusum_pos = max(0, cusum_pos + z - k)
        cusum_neg = max(0, cusum_neg - z - k)
        cusum_scores.append(round(cusum_pos - cusum_neg, 3))

    drift_detected = abs(cusum_scores[-1]) > 4.0
    direction      = "UP" if cusum_scores[-1] > 0 else "DOWN"

    return {
        "lot_id":          lot_id,
        "parameter":       parameter,
        "target":          target,
        "recent_mean":     round(mean, 3),
        "drift_magnitude": drift,
        "drift_detected":  drift_detected,
        "direction":       direction if drift_detected else "NONE",
        "cusum_final":     cusum_scores[-1],
        "alert_threshold": 4.0,
        "action":          f"{parameter} {direction} 드리프트 - 장비 점검 권고"
                           if drift_detected else "정상",
    }


def mcp_correlation_check(lot_id: str) -> dict:
    """주요 공정 파라미터 간 상관관계 분석."""
    random.seed(hash(lot_id) % 1000 + 3)

    def corr(base: float) -> float:
        return round(max(-1.0, min(1.0, base + random.gauss(0, 0.05))), 3)

    matrix = {
        "gate_oxide_thickness": {
            "chamber_temp_c":    corr(0.78),
            "o2_flow_sccm":      corr(0.65),
            "process_time_sec":  corr(0.91),
            "yield_pct":         corr(-0.61),
        },
        "chamber_temp_c": {
            "o2_flow_sccm":      corr(0.42),
            "process_time_sec":  corr(0.55),
            "yield_pct":         corr(-0.58),
        },
    }

    # 강한 상관관계 (|r| > 0.7) 추출
    strong = []
    for param, correlations in matrix.items():
        for other, r in correlations.items():
            if abs(r) > 0.7:
                strong.append({
                    "param_a": param, "param_b": other,
                    "r": r,
                    "type": "positive" if r > 0 else "negative",
                })

    return {
        "lot_id":              lot_id,
        "correlation_matrix":  matrix,
        "strong_correlations": strong,
        "insight": (
            f"{strong[0]['param_a']} ↔ {strong[0]['param_b']} "
            f"강한 {'양' if strong[0]['r'] > 0 else '음'}의 상관관계 (r={strong[0]['r']})"
            if strong else "유의미한 상관관계 없음"
        ),
    }
