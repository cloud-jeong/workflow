from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DIFY_BASE_URL     = os.getenv("DIFY_BASE_URL", "http://localhost:5001/v1")
DIFY_API_KEY      = os.getenv("DIFY_API_KEY", "")

AGENT_REGISTRY: dict[str, dict] = {
    "data_collector": {
        "name": "DataCollector Agent",
        "type": "tool",
        "description": "DB 조회, 센서 데이터 수집, 장비 로그 읽기",
        "tools": ["mcp_query_db", "mcp_fetch_sensor", "mcp_read_file", "mcp_fetch_equipment_log"],
        "endpoint": "http://agent-svc:8001",
    },
    "spc_analyzer": {
        "name": "SPC Analyzer Agent",
        "type": "tool",
        "description": "SPC 분석, Cpk 계산, OOC 탐지",
        "tools": ["mcp_run_spc", "mcp_calculate_cpk", "mcp_detect_ooc"],
        "endpoint": "http://agent-svc:8002",
    },
    "yield_analyzer": {
        "name": "Yield Analyzer Agent",
        "type": "tool",
        "description": "수율 계산, Bin 분석, Wafer Map 생성",
        "tools": ["mcp_calc_yield", "mcp_bin_analysis", "mcp_wafer_map"],
        "endpoint": "http://agent-svc:8003",
    },
    "anomaly_detector": {
        "name": "Anomaly Detector Agent",
        "type": "tool",
        "description": "ML 기반 이상 탐지, 드리프트 감지",
        "tools": ["mcp_ml_predict", "mcp_detect_drift", "mcp_correlation_check"],
        "endpoint": "http://agent-svc:8004",
    },
    "report_agent": {
        "name": "Report Agent",
        "type": "tool",
        "description": "리포트 생성, PDF 내보내기, 메일 발송",
        "tools": ["mcp_gen_report", "mcp_export_pdf", "mcp_send_email"],
        "endpoint": "http://agent-svc:8005",
    },
    "alert_agent": {
        "name": "Alert Agent",
        "type": "tool",
        "description": "Slack 알림, 티켓 생성, 에스컬레이션",
        "tools": ["mcp_notify_slack", "mcp_create_ticket", "mcp_escalate"],
        "endpoint": "http://agent-svc:8006",
    },
}
