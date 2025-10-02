# main.py

# Firebase 서비스와 통신하기 위한 기본 도구들을 가져옵니다.
from firebase_functions import options, scheduler_fn, logger
from firebase_admin import initialize_app, firestore, db

# Firebase 앱을 초기화합니다.
initialize_app()
options.set_global_options(region="asia-northeast3") # 서울 리전 설정

@scheduler_fn.on_schedule(schedule="every 10 minutes")
def analyze_energy_data(event: scheduler_fn.ScheduledEvent) -> None:
    """
    10분마다 실행되어 에너지 사용량 데이터를 분석하고 랭킹을 산정하는 함수
    (JS의 async/await와 완전히 동일하게 비동기 처리가 가능하지만,
     이 코드에서는 동기적으로 처리해도 충분하여 async를 붙이지 않았습니다.)
    """
    logger.info("에너지 데이터 분석 함수 실행 시작!")

    # JS의 try...catch는 Python에서 try...except 입니다.
    try:
        # Firestore와 Realtime Database 클라이언트를 가져옵니다.
        firestore_db = firestore.client()
        rtdb = db.reference()

        # Firestore에서 최근 5분간의 원본 데이터 읽어오기
        # (로직은 JS와 거의 동일)
        from datetime import datetime, timedelta
        
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        
        logs_query = firestore_db.collection("ac_logs").where("timestamp", ">=", ten_minutes_ago).stream()

        recent_logs = [doc.to_dict() for doc in logs_query]

        if not recent_logs:
            logger.info("최근 10분간 새로운 데이터가 없습니다.")
            return

        logger.info(f"총 {len(recent_logs)}개의 로그를 읽었습니다.")
        
        # ToDo 2: 읽어온 데이터를 분석/계산하기
        # (이곳에 Python으로 데이터 분석 로직을 구현)

        # ToDo 3: 분석된 최종 결과를 Realtime Database에 저장하기
        analysis_result = {"status": "completed", "log_count": len(recent_logs)}
        rtdb.child("analysis/latest").set(analysis_result)
        
        logger.info("에너지 데이터 분석 및 저장 성공!")

    except Exception as e:
        logger.error(f"에너지 데이터 분석 중 에러 발생: {e}")