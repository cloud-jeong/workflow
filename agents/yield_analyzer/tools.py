"""Yield Analyzer Agent - MCP tool implementations."""
from __future__ import annotations

import random


def mcp_calc_yield(lot_id: str, wafer_count: int = 25) -> dict:
    """웨이퍼별 수율 계산."""
    random.seed(hash(lot_id) % 1000)

    dies_per_wafer = 1200
    wafers = []
    for i in range(wafer_count):
        good = int(dies_per_wafer * random.gauss(0.923, 0.02))
        good = max(0, min(dies_per_wafer, good))
        wafers.append({
            "wafer_id": f"{lot_id}-W{i+1:02d}",
            "total_dies": dies_per_wafer,
            "good_dies":  good,
            "yield_pct":  round(good / dies_per_wafer * 100, 2),
        })

    total_good  = sum(w["good_dies"]  for w in wafers)
    total_dies  = sum(w["total_dies"] for w in wafers)
    lot_yield   = round(total_good / total_dies * 100, 2)
    below_spec  = [w for w in wafers if w["yield_pct"] < 90.0]

    return {
        "lot_id":         lot_id,
        "wafer_count":    wafer_count,
        "lot_yield_pct":  lot_yield,
        "target_yield_pct": 92.0,
        "pass":           lot_yield >= 92.0,
        "below_spec_wafers": [w["wafer_id"] for w in below_spec],
        "wafer_summary":  wafers,
    }


def mcp_bin_analysis(lot_id: str) -> dict:
    """Bin별 불량 분류 분석."""
    random.seed(hash(lot_id) % 1000 + 1)
    total = 30000

    bin1 = int(total * random.gauss(0.923, 0.015))
    remaining = total - bin1
    bin2 = int(remaining * 0.40)   # leakage
    bin3 = int(remaining * 0.25)   # open
    bin4 = int(remaining * 0.20)   # short
    bin5 = remaining - bin2 - bin3 - bin4  # parametric

    bins = [
        {"bin": 1, "name": "Pass",        "count": bin1, "pct": round(bin1/total*100, 2)},
        {"bin": 2, "name": "Leakage",     "count": bin2, "pct": round(bin2/total*100, 2)},
        {"bin": 3, "name": "Open",        "count": bin3, "pct": round(bin3/total*100, 2)},
        {"bin": 4, "name": "Short",       "count": bin4, "pct": round(bin4/total*100, 2)},
        {"bin": 5, "name": "Parametric",  "count": bin5, "pct": round(bin5/total*100, 2)},
    ]

    dominant_fail = max(bins[1:], key=lambda b: b["count"])

    return {
        "lot_id":          lot_id,
        "total_dies":      total,
        "bins":            bins,
        "dominant_failure": dominant_fail["name"],
        "action":          f"{dominant_fail['name']} 불량 원인 분석 필요"
                           if dominant_fail["pct"] > 2.0 else "정상 범위",
    }


def mcp_wafer_map(lot_id: str, wafer_id: str = "W01") -> dict:
    """웨이퍼 맵 생성 - 다이 위치별 Pass/Fail."""
    random.seed(hash(lot_id + wafer_id) % 1000)

    rows, cols = 10, 10
    grid = []
    fail_positions = []

    for r in range(rows):
        row = []
        for c in range(cols):
            # 엣지 다이는 불량률 높음
            edge = r in (0, rows-1) or c in (0, cols-1)
            fail_prob = 0.15 if edge else 0.05
            status = "F" if random.random() < fail_prob else "P"
            if status == "F":
                fail_positions.append({"row": r, "col": c})
            row.append(status)
        grid.append(row)

    total  = rows * cols
    passes = sum(row.count("P") for row in grid)

    return {
        "lot_id":         lot_id,
        "wafer_id":       f"{lot_id}-{wafer_id}",
        "grid_size":      f"{rows}x{cols}",
        "total_dies":     total,
        "pass_dies":      passes,
        "fail_dies":      total - passes,
        "yield_pct":      round(passes / total * 100, 1),
        "fail_positions": fail_positions,
        "map":            grid,
        "edge_effect":    True,
    }
