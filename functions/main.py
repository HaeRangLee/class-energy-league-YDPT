
import firebase_admin
from firebase_admin import credentials, firestore, db
import datetime
import functions_framework

# Firebase Admin SDK 초기화
# Cloud Functions 환경에서는 자동으로 인증 정보를 가져오므로, credentials가 필요 없습니다.
try:
    firebase_admin.initialize_app()
except ValueError:
    # 앱이 이미 초기화된 경우의 예외 처리
    pass

# Firestore 클라이언트
firestore_db = firestore.client()

# --- 1. Firestore에서 최근 로그 가져오기 ---
def get_recent_logs():
    """지난 10분 동안의 AC 로그를 Firestore에서 가져옵니다."""
    print("Firestore에서 최근 로그를 가져오는 중...")
    
    now = datetime.datetime.now(datetime.timezone.utc)
    ten_minutes_ago = now - datetime.timedelta(minutes=10)

    logs_ref = firestore_db.collection('ac_logs')
    query = logs_ref.where("timestamp", ">=", ten_minutes_ago).where("timestamp", "<=", now)
    
    docs = query.stream()
    
    # 문서를 리스트로 변환하여 반환
    log_list = [doc.to_dict() for doc in docs]
    print(f"{len(log_list)}개의 로그를 찾았습니다.")
    return log_list

# --- 2. 사용 시간 계산하기 (현재는 더미 데이터 반환) ---
def calculate_usage_from_logs(logs):
    """
    가져온 로그를 바탕으로 학급별 사용 시간을 계산합니다.
    TODO: 실제 계산 로직 구현 필요.
    """
    print("사용 시간 계산 중 (현재는 더미 데이터 사용)...")
    
    # 예시 더미 데이터: {'학급ID': 사용시간(분)}
    dummy_usage_data = {
        '1반': 10,
        '2반': 5,
        '3반': 10,
    }
    return dummy_usage_data

# --- 3. 분석 데이터 업데이트 및 저장 ---
def update_realtime_database(usage_data):
    """계산된 데이터를 Realtime Database에 업데이트합니다."""
    print("Realtime Database 업데이트 중...")
    
    # TODO: 기존 데이터를 읽고 합산하는 로직 추가 필요
    # 현재는 전달받은 데이터로 덮어쓰기만 합니다.
    
    # 순위 계산 (간단한 예시)
    sorted_ranking = sorted(usage_data.items(), key=lambda item: item[1])
    ranking_list = [{"className": item[0], "usage": item[1]} for item in sorted_ranking]

    # Realtime Database에 저장할 최종 데이터 구조
    analysis_data = {
        'totalUsage': usage_data,
        'ranking': ranking_list,
        'lastUpdated': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    ref = db.reference('/analysis')
    ref.set(analysis_data)
    print("Realtime Database 업데이트 완료.")


# --- Cloud Function 진입점 ---
@functions_framework.scheduler_ 제조업체
def main(event):
    """스케줄러에 의해 10분마다 실행되는 메인 함수"""
    print("배치 작업 시작...")
    
    # 1. Firestore에서 데이터 가져오기
    recent_logs = get_recent_logs()
    
    # 2. 사용 시간 계산 (현재는 더미 데이터)
    usage_by_class = calculate_usage_from_logs(recent_logs)
    
    # 3. Realtime Database에 결과 저장
    update_realtime_database(usage_by_class)
    
    print("배치 작업 완료.")
    return "OK"
