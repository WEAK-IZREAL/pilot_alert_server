from flask import Flask, Response, request
import json
from alert_generator import generate_alert_messages
from fetch_pilot_data import fetch_pilot_data
from compare_data import check_for_updates
import os
import threading
import time

# Firebase Admin SDK import 및 초기화
import firebase_admin
from firebase_admin import credentials, messaging

FIREBASE_CREDENTIALS_PATH = 'pilotalertapp-firebase-adminsdk-fbsvc-ea28e551f9.json'  # JSON 키 파일 경로

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

app = Flask(__name__)

DATA_FILE = 'previous_data.json'

def load_previous_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_current_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/api/pilotships', methods=['GET'])
def get_pilot_ships():
    try:
        data = fetch_pilot_data()
        return Response(
            json.dumps({"status": "success", "data": data}, ensure_ascii=False),
            mimetype='application/json'
        )
    except Exception as e:
        return Response(
            json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            mimetype='application/json'
        )

@app.route('/api/checkupdates', methods=['GET'])
def check_updates():
    try:
        old_data = load_previous_data()
        new_data = fetch_pilot_data()
        changes = check_for_updates(old_data, new_data)
        alerts = generate_alert_messages(changes)
        save_current_data(new_data)

        return Response(
            json.dumps({
                "status": "success",
                "changes": changes,
                "alerts": alerts
            }, ensure_ascii=False),
            mimetype='application/json'
        )
    except Exception as e:
        return Response(
            json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            mimetype='application/json'
        )

@app.route('/test-alert', methods=['GET'])
def test_alert():
    changes_example = {
        "status_added": [
            {"id": "101", "ship_name": "TEST SHIP 1", "status": "Heavy Weather"},
        ],
        "status_removed": [
            {"id": "102", "ship_name": "TEST SHIP 2", "status": "Dense Fog"},
        ],
        "time_changes": [
            {"id": "103", "ship_name": "TEST SHIP 3", "before": "10:00", "after": "11:00"},
        ],
        "removed_ships": [
            {"id": "104", "ship_name": "TEST SHIP 4"}
        ]
    }
    messages = generate_alert_messages(changes_example)

    return Response(
        json.dumps({"status": "success", "alerts": messages}, ensure_ascii=False),
        mimetype='application/json'
    )


# -------------- 새로 추가: FCM 토큰 등록 API ----------------
registered_tokens = set()  # 메모리 저장 (실제 환경에서는 DB 사용 권장)

@app.route('/api/register_token', methods=['POST'])
def register_token():
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({"status": "error", "message": "Token missing"}), 400
    
    registered_tokens.add(token)
    print(f"Registered token: {token}")
    return jsonify({"status": "success", "message": "Token registered"}), 200
# ---------------------------------------------------------


def send_fcm_notification(token, alert_messages):
    """FCM 토큰 하나에 알림 메시지 리스트를 전송"""
    notification_body = "\n".join(alert_messages)[:200]  # 최대 길이 제한 처리

    message = messaging.Message(
        notification=messaging.Notification(
            title="울산항 도선 정보 알림",
            body=notification_body
        ),
        token=token
    )
    try:
        response = messaging.send(message)
        print(f"FCM 전송 성공: {response}")
    except Exception as e:
        print(f"FCM 전송 실패: {e}")

def load_favorites():
    """
    예시: 사용자 FCM 토큰별 즐겨찾기 선박 목록 반환
    실제 구현 시에는 DB 또는 외부 저장소에서 불러와야 함
    """
    return {
        "user_fcm_token_1": ["YEOSU VOYAGER", "FC GLORIA"],
        "user_fcm_token_2": ["GOLDEN PROCYON"],
    }

def send_notifications_to_users(changes, alerts):
    favorites_map = load_favorites()

    for token, favorite_ships in favorites_map.items():
        filtered_alerts = []
        for alert in alerts:
            # alert 메시지 안에 즐겨찾기 선박 이름이 포함되어 있으면 필터링
            if any(ship in alert for ship in favorite_ships):
                filtered_alerts.append(alert)

        if filtered_alerts:
            send_fcm_notification(token, filtered_alerts)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
