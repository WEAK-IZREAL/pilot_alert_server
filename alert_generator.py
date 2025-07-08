def generate_alert_messages(changes):
    alerts = []

    # 상태 추가 알림 (Heavy Weather / Dense Fog 발생 → 도선 제한)
    for added in changes.get('status_added', []):
        alerts.append(
            f"⚠️ [도선 제한] '{added['ship_name']}' 선박이 '{added['status']}' 상태로 도선이 제한됩니다.")

    # 상태 제거 알림 (제한 해제 → 도선 재개)
    for removed in changes.get('status_removed', []):
        alerts.append(
            f"✅ [도선 재개] '{removed['ship_name']}' 선박이 '{removed['status']}'가 해제되어 도선이 재개됩니다.")

    # 도선 시간 변경 알림
    for change in changes.get('time_changes', []):
        alerts.append(
            f"⏰ [시간 변경] '{change['ship_name']}' 선박의 도선 시간이 {change['before']} ➝ {change['after']}로 변경되었습니다.")

    # 선박 목록에서 사라짐
    for removed in changes.get('removed_ships', []):
        alerts.append(
            f"🚢 [목록 제외] '{removed['ship_name']}' 선박이 도선 목록에서 제외되었습니다.")

    return alerts
