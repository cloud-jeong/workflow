"""Alert Agent - MCP tool implementations."""
from __future__ import annotations

import random
from datetime import datetime


def mcp_notify_slack(
    lot_id:   str,
    message:  str = "",
    channel:  str = "#yms-alerts",
    severity: str = "HIGH",
) -> dict:
    """Slack 알림 발송."""
    now = datetime.now()
    color_map = {"HIGH": "#FF0000", "MEDIUM": "#FFA500", "LOW": "#FFFF00"}
    emoji_map = {"HIGH": "🚨", "MEDIUM": "⚠️",  "LOW": "ℹ️"}

    default_msg = (
        f"{emoji_map.get(severity, '🔔')} *[YMS Alert]* LOT `{lot_id}` 공정 이상 감지\n"
        f"> 심각도: *{severity}*\n"
        f"> 감지 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"> 조치 필요: 담당 엔지니어 확인 요망"
    )

    return {
        "lot_id":     lot_id,
        "channel":    channel,
        "message":    message or default_msg,
        "severity":   severity,
        "color":      color_map.get(severity, "#808080"),
        "sent_at":    now.isoformat(),
        "message_ts": f"{now.timestamp():.6f}",
        "status":     "ok",
        "notified_users": ["@process_oncall", "@yield_engineer"],
    }


def mcp_create_ticket(
    lot_id:      str,
    title:       str = "",
    priority:    str = "P1",
    assignee:    str = "process_team",
) -> dict:
    """Jira 이슈 티켓 생성."""
    random.seed(hash(lot_id) % 1000)
    ticket_num = random.randint(10000, 99999)
    ticket_id  = f"YMS-{ticket_num}"
    now        = datetime.now()

    priority_sla = {"P1": "4h", "P2": "8h", "P3": "24h", "P4": "72h"}

    return {
        "lot_id":      lot_id,
        "ticket_id":   ticket_id,
        "title":       title or f"[공정 이상] LOT {lot_id} SPC OOC 감지",
        "priority":    priority,
        "sla":         priority_sla.get(priority, "24h"),
        "assignee":    assignee,
        "status":      "OPEN",
        "created_at":  now.isoformat(),
        "url":         f"https://jira.fab.com/browse/{ticket_id}",
        "due_by":      f"{now.strftime('%Y-%m-%d')} +{priority_sla.get(priority, '24h')}",
    }


def mcp_escalate(
    lot_id:    str,
    ticket_id: str = "",
    level:     int = 1,
) -> dict:
    """이슈 에스컬레이션 - 상위 관리자에게 보고."""
    escalation_chain = {
        1: {"role": "Senior Process Engineer", "contact": "senior_eng@fab.com"},
        2: {"role": "Process Module Manager",  "contact": "module_mgr@fab.com"},
        3: {"role": "Fab Director",            "contact": "fab_dir@fab.com"},
    }
    target = escalation_chain.get(level, escalation_chain[1])
    now    = datetime.now()

    return {
        "lot_id":          lot_id,
        "ticket_id":       ticket_id,
        "escalation_id":   f"ESC-{lot_id}-L{level}",
        "level":           level,
        "assigned_to":     target["role"],
        "contact":         target["contact"],
        "escalated_at":    now.isoformat(),
        "reason":          f"LOT {lot_id} 공정 이상 - Level {level} 에스컬레이션",
        "status":          "ESCALATED",
        "next_review_min": 30 * level,
    }
