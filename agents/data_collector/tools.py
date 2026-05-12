"""DataCollector Agent - MCP tool implementations."""
from __future__ import annotations

import random
from datetime import datetime, timedelta


def mcp_query_db(lot_id: str, query: str = "spc_measurements") -> dict:
    """DB에서 LOT 공정 측정 데이터 조회."""
    random.seed(hash(lot_id) % 1000)
    base_time = datetime(2024, 8, 12, 8, 0, 0)

    records = []
    for i in range(25):
        records.append({
            "seq":        i + 1,
            "timestamp":  (base_time + timedelta(minutes=i * 30)).isoformat(),
            "gate_ox":    round(random.gauss(100.0, 2.0), 2),
            "poly_cd":    round(random.gauss(65.0,  1.5), 2),
            "implant_dose": round(random.gauss(1.2e15, 2e13), -12),
            "step":       f"STEP_{(i % 5) + 1}",
            "equipment":  f"EQ-{(i % 3) + 1:03d}",
        })

    return {
        "lot_id":     lot_id,
        "query_type": query,
        "record_count": len(records),
        "date_range": {
            "start": records[0]["timestamp"],
            "end":   records[-1]["timestamp"],
        },
        "records": records,
    }


def mcp_fetch_sensor(lot_id: str, equipment_id: str = "EQ-001") -> dict:
    """장비 센서 실시간 데이터 수집 (온도/압력/가스 유량)."""
    random.seed(hash(lot_id + equipment_id) % 1000)

    return {
        "lot_id":       lot_id,
        "equipment_id": equipment_id,
        "sampled_at":   datetime.now().isoformat(),
        "sensors": {
            "chamber_temp_c":  round(random.gauss(850.0, 3.0), 1),
            "chamber_pressure_torr": round(random.gauss(7.5, 0.1), 3),
            "o2_flow_sccm":    round(random.gauss(200.0, 5.0), 1),
            "n2_flow_sccm":    round(random.gauss(500.0, 8.0), 1),
            "rf_power_w":      round(random.gauss(1200.0, 20.0), 1),
        },
        "status": "RUNNING",
    }


def mcp_read_file(lot_id: str, file_type: str = "recipe") -> dict:
    """레시피/설정 파일 읽기."""
    recipes = {
        "recipe": {
            "recipe_id":   "OXIDE_V3.2",
            "process":     "Gate Oxide Growth",
            "target_thickness_A": 100,
            "temperature_c":      850,
            "pressure_torr":      7.5,
            "time_sec":           1200,
            "gas": {"O2": 200, "N2": 500},
        }
    }
    return {
        "lot_id":    lot_id,
        "file_type": file_type,
        "content":   recipes.get(file_type, {}),
        "path":      f"/recipes/{lot_id}_{file_type}.json",
    }


def mcp_fetch_equipment_log(lot_id: str, equipment_id: str = "EQ-001") -> dict:
    """장비 이벤트 로그 수집."""
    random.seed(hash(lot_id) % 500)
    base_time = datetime(2024, 8, 12, 6, 0, 0)
    levels = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
    messages = [
        "Process started",
        "Chamber pumped down",
        "Temperature stabilized",
        "Minor pressure fluctuation detected",
        "Gas flow deviation: O2 +8% from setpoint",
        "Process completed",
        "Wafer unloaded",
    ]

    logs = []
    for i in range(12):
        level = random.choice(levels)
        logs.append({
            "timestamp": (base_time + timedelta(minutes=i * 15)).isoformat(),
            "level":     level,
            "message":   random.choice(messages),
            "equipment": equipment_id,
        })

    warn_count  = sum(1 for l in logs if l["level"] == "WARN")
    error_count = sum(1 for l in logs if l["level"] == "ERROR")

    return {
        "lot_id":       lot_id,
        "equipment_id": equipment_id,
        "log_count":    len(logs),
        "warn_count":   warn_count,
        "error_count":  error_count,
        "logs":         logs,
        "has_anomaly":  error_count > 0,
    }
