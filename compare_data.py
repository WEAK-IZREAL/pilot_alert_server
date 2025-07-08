def check_for_updates(old_data, new_data):
    status_added = []
    status_removed = []
    time_changes = []
    removed_ships = []

    old_dict = {item['id']: item for item in old_data}
    new_dict = {item['id']: item for item in new_data}

    # 변경 감지
    for id_, new_item in new_dict.items():
        old_item = old_dict.get(id_)
        if not old_item:
            continue

        # 시간 변경
        if old_item.get('time') != new_item.get('time'):
            time_changes.append({
                'id': id_,
                'ship_name': new_item.get('ship_name'),
                'before': old_item.get('time'),
                'after': new_item.get('time')
            })

        # 상태 변경 (Heavy Weather, Dense Fog)
        old_status = old_item.get('status', '')
        new_status = new_item.get('status', '')
        for keyword in ['Heavy Weather', 'Dense Fog']:
            if keyword in new_status and keyword not in old_status:
                status_added.append({
                    'id': id_,
                    'ship_name': new_item.get('ship_name'),
                    'status': keyword
                })
            elif keyword in old_status and keyword not in new_status:
                status_removed.append({
                    'id': id_,
                    'ship_name': new_item.get('ship_name'),
                    'status': keyword
                })

    # 목록에서 사라진 선박 체크
    for id_, old_item in old_dict.items():
        if id_ not in new_dict:
            removed_ships.append({
                'id': id_,
                'ship_name': old_item.get('ship_name'),
                'time': old_item.get('time'),
                'status': old_item.get('status'),
            })

    return {
        'status_added': status_added,
        'status_removed': status_removed,
        'time_changes': time_changes,
        'removed_ships': removed_ships,
    }
