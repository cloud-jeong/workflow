"""Report Agent - MCP tool implementations."""
from __future__ import annotations

from datetime import datetime


def mcp_gen_report(lot_id: str, context: dict | None = None) -> dict:
    """분석 결과 종합 리포트 생성."""
    now = datetime.now()
    ctx = context or {}

    sections = {
        "summary": {
            "lot_id":       lot_id,
            "report_date":  now.strftime("%Y-%m-%d %H:%M"),
            "overall_status": "FAIL" if ctx.get("is_anomaly") else "PASS",
            "risk_level":   ctx.get("risk_level", "LOW"),
        },
        "spc_result": {
            "ooc_detected":     ctx.get("ooc_detected", False),
            "violation_count":  ctx.get("violation_count", 0),
            "cpk":              ctx.get("cpk", "N/A"),
            "cpk_grade":        ctx.get("cpk_grade", "N/A"),
        },
        "yield_result": {
            "lot_yield_pct":        ctx.get("lot_yield_pct", "N/A"),
            "target_yield_pct":     92.0,
            "dominant_failure":     ctx.get("dominant_failure", "N/A"),
            "below_spec_wafers":    ctx.get("below_spec_wafers", []),
        },
        "anomaly_result": {
            "prediction":           ctx.get("prediction", "NORMAL"),
            "anomaly_score":        ctx.get("anomaly_score", 0.0),
            "drift_detected":       ctx.get("drift_detected", False),
            "drift_direction":      ctx.get("direction", "NONE"),
        },
        "recommendations": [
            "SPC OOC 발생 구간 장비 점검 실시",
            "Gate Oxide 공정 파라미터 재조정 검토",
            "Leakage 불량 원인 분석 (공정 엔지니어 배정)",
        ] if ctx.get("is_anomaly") else ["정상 공정 유지"],
    }

    return {
        "lot_id":      lot_id,
        "report_id":   f"RPT-{lot_id}-{now.strftime('%Y%m%d%H%M')}",
        "generated_at": now.isoformat(),
        "sections":    sections,
        "page_count":  4,
    }


def mcp_export_pdf(report_id: str, lot_id: str) -> dict:
    """리포트를 PDF로 내보내기."""
    now = datetime.now()
    filename = f"{report_id}.pdf"
    path     = f"/reports/{now.strftime('%Y/%m')}/{filename}"

    return {
        "report_id":   report_id,
        "lot_id":      lot_id,
        "filename":    filename,
        "path":        path,
        "size_kb":     284,
        "exported_at": now.isoformat(),
        "download_url": f"http://report-svc/download/{report_id}",
        "status":      "SUCCESS",
    }


def mcp_send_email(
    lot_id:     str,
    report_id:  str,
    recipients: list[str] | None = None,
) -> dict:
    """리포트 이메일 발송."""
    recipients = recipients or [
        "process_eng@fab.com",
        "yield_team@fab.com",
        "manager@fab.com",
    ]
    now = datetime.now()

    return {
        "lot_id":      lot_id,
        "report_id":   report_id,
        "recipients":  recipients,
        "subject":     f"[YMS] LOT {lot_id} 공정 분석 리포트",
        "sent_at":     now.isoformat(),
        "status":      "SENT",
        "message_id":  f"<{now.strftime('%Y%m%d%H%M%S')}.{lot_id}@fab.com>",
    }
