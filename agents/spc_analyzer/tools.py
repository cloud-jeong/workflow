"""SPC Analyzer Agent - MCP tool implementations with sample data."""
from __future__ import annotations

import random
import statistics


def mcp_run_spc(lot_id: str, parameter: str = "gate_oxide_thickness") -> dict:
    """SPC 관리도 분석 - 측정 데이터와 관리한계선 계산."""
    random.seed(hash(lot_id) % 1000)

    # 공정 파라미터 설정 (단위: Å)
    target = 100.0
    sigma = 2.0
    ucl = target + 3 * sigma   # 106.0
    lcl = target - 3 * sigma   # 94.0
    uwl = target + 2 * sigma   # 104.0  (Warning Limit)
    lwl = target - 2 * sigma   # 96.0

    # 25개 측정점 생성 (일부 이상 패턴 삽입)
    measurements = []
    for i in range(25):
        if i in (7, 8, 9, 10, 11, 12, 13, 14, 15):  # Rule 2: 연속 9점 편향
            val = round(target + 1.5 + random.gauss(0, 0.5), 2)
        elif i == 19:                                  # Rule 1: 3σ 이탈점
            val = round(target + 3.4 * sigma, 2)
        else:
            val = round(random.gauss(target, sigma), 2)
        measurements.append(val)

    mean = round(statistics.mean(measurements), 3)
    std  = round(statistics.stdev(measurements), 3)

    return {
        "lot_id": lot_id,
        "parameter": parameter,
        "unit": "Å",
        "target": target,
        "control_limits": {"ucl": ucl, "cl": target, "lcl": lcl,
                           "uwl": uwl, "lwl": lwl},
        "measurements": [{"seq": i + 1, "value": v} for i, v in enumerate(measurements)],
        "stats": {"mean": mean, "std": std, "n": len(measurements)},
    }


def mcp_calculate_cpk(lot_id: str, usl: float = 108.0, lsl: float = 92.0) -> dict:
    """공정 능력 지수 Cpk / Cp / Cpu / Cpl 계산."""
    random.seed(hash(lot_id) % 1000 + 1)

    measurements = [round(random.gauss(100.5, 2.1), 2) for _ in range(25)]
    mean = statistics.mean(measurements)
    std  = statistics.stdev(measurements)

    cp  = round((usl - lsl) / (6 * std), 3)
    cpu = round((usl - mean) / (3 * std), 3)
    cpl = round((mean - lsl) / (3 * std), 3)
    cpk = round(min(cpu, cpl), 3)

    if cpk >= 1.67:
        grade, status = "A", "Excellent"
    elif cpk >= 1.33:
        grade, status = "B", "Capable"
    elif cpk >= 1.00:
        grade, status = "C", "Marginal"
    else:
        grade, status = "D", "Not Capable"

    return {
        "lot_id": lot_id,
        "spec_limits": {"usl": usl, "lsl": lsl},
        "process_stats": {"mean": round(mean, 3), "std": round(std, 3)},
        "indices": {"cp": cp, "cpk": cpk, "cpu": cpu, "cpl": cpl},
        "grade": grade,
        "status": status,
        "action_required": cpk < 1.33,
    }


def mcp_detect_ooc(lot_id: str, spc_data: dict | None = None) -> dict:
    """OOC(Out of Control) 탐지 - Western Electric Rules 적용."""
    if spc_data is None:
        spc_data = mcp_run_spc(lot_id)

    measurements = [p["value"] for p in spc_data["measurements"]]
    cl  = spc_data["control_limits"]["cl"]
    ucl = spc_data["control_limits"]["ucl"]
    lcl = spc_data["control_limits"]["lcl"]
    uwl = spc_data["control_limits"]["uwl"]
    lwl = spc_data["control_limits"]["lwl"]
    sigma = (ucl - cl) / 3

    violations: list[dict] = []

    for i, v in enumerate(measurements):
        seq = i + 1

        # Rule 1: 3σ 이탈
        if v > ucl or v < lcl:
            violations.append({
                "seq": seq, "value": v,
                "rule": "Rule 1",
                "description": f"관리한계선 이탈 ({'UCL' if v > ucl else 'LCL'}={ucl if v > ucl else lcl:.1f})",
                "severity": "HIGH",
            })

        # Rule 2: 연속 9점이 CL 같은 쪽
        if i >= 8:
            window = measurements[i - 8: i + 1]
            if all(w > cl for w in window) or all(w < cl for w in window):
                violations.append({
                    "seq": seq, "value": v,
                    "rule": "Rule 2",
                    "description": f"연속 9점 CL {'상방' if v > cl else '하방'} 편향 (seq {seq-8}~{seq})",
                    "severity": "MEDIUM",
                })

        # Rule 3: 연속 6점 단조 증가/감소
        if i >= 5:
            window = measurements[i - 5: i + 1]
            if all(window[j] < window[j + 1] for j in range(5)):
                violations.append({
                    "seq": seq, "value": v,
                    "rule": "Rule 3",
                    "description": f"연속 6점 단조 증가 (seq {seq-5}~{seq})",
                    "severity": "MEDIUM",
                })
            elif all(window[j] > window[j + 1] for j in range(5)):
                violations.append({
                    "seq": seq, "value": v,
                    "rule": "Rule 3",
                    "description": f"연속 6점 단조 감소 (seq {seq-5}~{seq})",
                    "severity": "MEDIUM",
                })

        # Rule 4: 3점 중 2점이 2σ 초과
        if i >= 2:
            window = measurements[i - 2: i + 1]
            beyond_2s = sum(1 for w in window if w > uwl or w < lwl)
            if beyond_2s >= 2:
                violations.append({
                    "seq": seq, "value": v,
                    "rule": "Rule 4",
                    "description": f"3점 중 2점 2σ 초과 (seq {seq-2}~{seq})",
                    "severity": "LOW",
                })

    # 중복 seq 제거 (같은 측정점에 여러 rule 적용 시 첫 번째만)
    seen: set[int] = set()
    unique_violations = []
    for v in violations:
        if v["seq"] not in seen:
            seen.add(v["seq"])
            unique_violations.append(v)

    ooc_detected = len(unique_violations) > 0

    return {
        "lot_id": lot_id,
        "ooc_detected": ooc_detected,
        "total_points": len(measurements),
        "violation_count": len(unique_violations),
        "violations": unique_violations,
        "summary": (
            f"OOC {len(unique_violations)}건 감지 - "
            f"즉시 조치 필요" if ooc_detected
            else "정상 공정 상태"
        ),
    }
