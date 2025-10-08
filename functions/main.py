'''
네, 알겠습니다. 제공해주신 JSON 구조를 요청하신 형식의 스키마로 작성했습니다.

```
/*
================================================================================
|                        Firebase Realtime Database Schema               |
================================================================================

/ (root)
|
|--- mainPage/
|    |
|    |--- monthlyRanking: (Array) 월간 랭킹 목록.
|    |    |--- [0]: { classId: (String), className: (String), monthlyUsageIndex: (Number) }
|    |    |--- [1]: ...
|    |
|    |--- systemIndexChangeVsLastWeek: (Number) 전체 시스템의 지난주 대비 증감률 (%).
|    |
|    `--- lastUpdated: (String) 마지막 업데이트 시간 (ISO 8601).
|
|--- detailPage/
|    |
|    |--- {classId}/ (e.g., "1-1", "1-2", ...)
|    |    |
|    |    |--- className: (String) 학급 이름.
|    |    |
|    |    |--- summary/
|    |    |    |--- dailyUsageIndex: (Number) 일간 사용 지수.
|    |    |    |--- weeklyUsageIndex: (Number) 주간 사용 지수.
|    |    |    `--- monthlyUsageIndex: (Number) 월간 사용 지수.
|    |    |
|    |    |--- comparison/
|    |    |    |--- vsLastDay: (Number) 어제 대비 증감률 (%).
|    |    |    |--- vsLastWeek: (Number) 지난주 대비 증감률 (%).
|    |    |    `--- vsLastMonth: (Number) 지난달 대비 증감률 (%).
|    |    |
|    |    `--- trends/
|    |         |--- last7Days: (Array) 지난 7일간의 일별 데이터.
|    |         |    `--- [0]: { date: (String), value: (Number) }
|    |         |
|    |         |--- last4Weeks: (Array) 지난 4주간의 주별 데이터.
|    |         |    `--- [0]: { week: (String), value: (Number) }
|    |         |
|    |         `--- todayRealtime: (Array) 오늘의 실시간 데이터.
|    |              `--- [0]: { time: (String), value: (Number) }
|
`--- comparisonPage/
     |
     |--- summary/
     |    |--- dailyTotalIndex: (Number) 전체 일간 총합 지수.
     |    |--- weeklyTotalIndex: (Number) 전체 주간 총합 지수.
     |    `--- monthlyTotalIndex: (Number) 전체 월간 총합 지수.
     |
     |--- comparison/
     |    |--- vsYesterday: (Number) 전체 어제 대비 증감률 (%).
     |    |--- vsLastWeek: (Number) 전체 지난주 대비 증감률 (%).
     |    `--- vsLastMonth: (Number) 전체 지난달 대비 증감률 (%).
     |
     |--- classTrends: (Array) 각 반의 상세 추이 데이터 목록.
     |    `--- [0]: { classId: (String), last7Days: (Array), last4Weeks: (Array), todayRealtime: (Array) }
     |
     `--- lastUpdated: (String) 마지막 업데이트 시간 (ISO 8601).

*/


================================================================================
|                        Firestore Database Schema                             |
================================================================================
🗄️ ac_logs (컬렉션)
  └── 📄 {자동 생성 ID_1} (문서)      <- 로그 1개
      ├── classId: "1-1"
      ├── timestamp: ...
      ├── isOn: true
      ├── mode: "냉방"
      ├── temperature: 24.5
      └── fanSpeed: "강풍"

  └── 📄 {자동 생성 ID_2} (문서)      <- 로그 1개
      └── ...


🗄️ class_stats (컬렉션)
  └── 📁 1-1 (문서)                   <- 반별 데이터를 담는 컨테이너
      └── 🗄️ daily_history (서브컬렉션) <- 일별 기록을 담는 책장
          └── 📄 2025-10-08 (문서)     <- 하루치 기록 파일
              │
              ├── cumulative_by_time (맵)  <- 시간대별 누적 지수
              │   │
              │   ├── "09:00": 50        <- 9시 00분까지의 누적값
              │   ├── "09:05": 58        <- 9시 05분까지의 누적값
              │   └── ...
              │
              └── finalTotal: 1390 (숫자) <- 해당 날짜의 최종 마감 지수

          └── 📄 2025-10-07 (문서)
              └── ...

        
```
'''
# main.py

from datetime import datetime, timedelta, timezone
from firebase_functions import options, scheduler_fn
import logging as logger
from firebase_admin import initialize_app, firestore, db

# --- 초기 설정 ---
initialize_app()
options.set_global_options(region="asia-northeast3", memory=options.MemoryOption.MB_256)
# -----------------

# =================================================================================
# |                         10분마다 실행되는 메인 함수                              |
# =================================================================================

#@https_fn.on_call
@scheduler_fn.on_schedule(schedule="every 10 minutes")
def analyze_and_update_data(event: scheduler_fn.ScheduledEvent) -> None:
    """
    10분마다 실행되어 실시간 데이터 집계 및 Realtime DB 업데이트를 수행합니다.
    """
    logger.info("✅ (10분 주기) 데이터 분석 작업을 시작합니다.")
    try:
        # 1. Firestore 'ac_logs'에서 최근 10분간의 로그를 가져옵니다.
        recent_logs = _get_recent_logs()
        if not recent_logs:
            logger.info("- 새로운 데이터가 없어 작업을 종료합니다.")
            return

        # 2. 로그에 미리 계산된 usageIndex를 반별로 합산합니다.
        new_points_by_class = _aggregate_indexes_from_logs(recent_logs)

        # 3. Firestore 'daily_history'에 시간대별 누적 값을 업데이트합니다.
        updated_daily_docs = _update_firestore_history(new_points_by_class)

        # 4. 업데이트된 최신 데이터를 바탕으로 Realtime DB용 최종 JSON을 생성하고 저장합니다.
        #_create_and_save_rtdb_data(updated_daily_docs)

        logger.info("🎉 (10분 주기) 데이터 분석 및 저장을 성공적으로 완료했습니다.")
    except Exception as e:
        logger.error(f"🔥 (10분 주기) 작업 중 에러 발생: {e}")

# =================================================================================
# |                          자정마다 실행되는 마감 함수                             |
# =================================================================================
@scheduler_fn.on_schedule(schedule="59 23 * * *", timezone=scheduler_fn.Timezone("Asia/Seoul"))
def finalize_daily_stats(event: scheduler_fn.ScheduledEvent) -> None:
    """
    매일 23시 59분에 실행되어 그날의 데이터를 최종 마감 처리합니다.
    """
    logger.info("✅ (자정 주기) 일일 데이터 마감 작업을 시작합니다.")
    try:
        yesterday_str = (datetime.now(timezone(timedelta(hours=9))) - timedelta(days=1)).strftime('%Y-%m-%d')
        firestore_db = firestore.client()
        
        # 모든 반의 어제 자 daily_history 문서를 가져옵니다.
        class_stats_ref = firestore_db.collection("class_stats")
        for class_doc in class_stats_ref.stream():
            class_id = class_doc.id
            yesterday_doc_ref = class_stats_ref.document(class_id).collection("daily_history").document(yesterday_str)
            yesterday_doc = yesterday_doc_ref.get()

            if yesterday_doc.exists:
                cumulative_map = yesterday_doc.to_dict().get("cumulative_by_time", {})
                if cumulative_map:
                    # 그날의 가장 마지막 누적 값을 찾아 finalTotal로 저장합니다.
                    final_total = max(cumulative_map.values())
                    yesterday_doc_ref.update({"finalTotal": round(final_total)})
                    logger.info(f"- {class_id}반 {yesterday_str}의 최종값 {round(final_total)}을 저장했습니다.")

        logger.info("🎉 (자정 주기) 일일 데이터 마감 작업을 성공적으로 완료했습니다.")
    except Exception as e:
        logger.error(f"🔥 (자정 주기) 작업 중 에러 발생: {e}")

# =================================================================================
# |                                  헬퍼 함수들                                   |
# =================================================================================

def _get_recent_logs() -> list:
    """Firestore 'ac_logs' 컬렉션에서 최근 10분 이내의 문서를 조회하여 반환합니다."""
    firestore_db = firestore.client()
    utc_now = datetime.now(timezone.utc)
    ten_minutes_ago = utc_now - timedelta(minutes=10)
    
    logs_query = firestore_db.collection("ac_logs").where("timestamp", ">=", ten_minutes_ago).stream()
    
    logs = [doc.to_dict() for doc in logs_query]
    logger.info(f"- Firestore에서 {len(logs)}개의 새 로그를 가져왔습니다.")
    return logs

def _aggregate_indexes_from_logs(logs: list) -> dict:
    """로그 목록을 받아, 미리 계산된 usageIndex를 반별로 합산합니다."""
    points_by_class = {}
    for log in logs:
        class_id = log.get("classId")
        usage_index = log.get("usageIndex", 0.0)
        if not class_id:
            continue
        points_by_class[class_id] = points_by_class.get(class_id, 0.0) + usage_index
    return points_by_class

def _update_firestore_history(points_by_class: dict) -> dict:
    """계산된 새 지수를 Firestore 'daily_history'의 각 문서에 업데이트합니다."""
    firestore_db = firestore.client()
    today_str = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    now_time_str = datetime.now(timezone(timedelta(hours=9))).strftime('%H:%M')
    
    updated_docs = {}

    for class_id, new_points in points_by_class.items():
        doc_ref = firestore_db.collection("class_stats").document(class_id).collection("daily_history").document(today_str)
        doc = doc_ref.get()
        
        cumulative_map = {}
        if doc.exists:
            cumulative_map = doc.to_dict().get("cumulative_by_time", {})
        
        last_cumulative_value = max(cumulative_map.values()) if cumulative_map else 0.0
        new_cumulative_value = last_cumulative_value + new_points
        
        cumulative_map[now_time_str] = new_cumulative_value
        
        # Firestore에 업데이트
        doc_ref.set({"cumulative_by_time": cumulative_map}, merge=True)
        updated_docs[class_id] = cumulative_map
        
    logger.info(f"- {today_str} Firestore 일일 원장을 업데이트했습니다.")
    return updated_docs

# 헬퍼 함수들 내에서 사용할 시간대 설정 (한국 시간)
KST = timezone(timedelta(hours=9))

def _get_all_historical_data() -> dict:
    """
    계산에 필요한 모든 반의 과거 데이터를 Firestore에서 한 번에 가져옵니다.
    약 40일 전까지의 데이터를 조회하여 월간 비교까지 충분히 커버합니다.
    """
    firestore_db = firestore.client()
    # 비교 계산을 위해 약 40일 전 데이터까지 조회
    start_date_str = (datetime.now(KST) - timedelta(days=40)).strftime('%Y-%m-%d')
    
    historical_data = {}
    class_stats_ref = firestore_db.collection("class_stats")
    
    for class_doc in class_stats_ref.stream():
        class_id = class_doc.id
        historical_data[class_id] = {}
        
        # 각 반의 daily_history 서브컬렉션에서 40일치 문서를 가져옴
        daily_docs_query = class_doc.reference.collection("daily_history").where(firestore.FieldPath.document_id(), ">=", start_date_str)
        
        for daily_doc in daily_docs_query.stream():
            historical_data[class_id][daily_doc.id] = daily_doc.to_dict()
            
    logger.info(f"- {len(historical_data)}개 반의 과거 데이터를 Firestore에서 가져왔습니다.")
    return historical_data

def _generate_usage_metrics(class_id: str, today_cumulative_map: dict, historical_data: dict, now: datetime) -> dict:
    """
    한 개 반의 '오늘/이번 주/이번 달' 누적 사용 지수를 계산합니다.
    
    :param class_id: 계산할 반의 ID (예: "1-1")
    :param today_cumulative_map: 오늘 현재까지의 시간대별 누적값 맵
    :param historical_data: 모든 과거 데이터가 담긴 딕셔너리
    :param now: 기준 시각
    :return: summary 객체 딕셔너리
    """
    
    # 1. 오늘 누적 지수 계산
    daily_index = max(today_cumulative_map.values()) if today_cumulative_map else 0

    # 2. 이번 주 누적 지수 계산
    weekly_index = daily_index
    # 오늘이 월요일이 아니라면, 이번 주 월요일부터 어제까지의 finalTotal을 더해줌
    for i in range(1, now.weekday()): # 월요일(0) ~ 일요일(6)
        day_to_add = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        weekly_index += historical_data.get(class_id, {}).get(day_to_add, {}).get("finalTotal", 0)

    # 3. 이번 달 누적 지수 계산
    monthly_index = daily_index
    # 오늘이 1일이 아니라면, 이번 달 1일부터 어제까지의 finalTotal을 더해줌
    for i in range(1, now.day):
        day_to_add = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        monthly_index += historical_data.get(class_id, {}).get(day_to_add, {}).get("finalTotal", 0)

    return {
        "dailyUsageIndex": round(daily_index),
        "weeklyUsageIndex": round(weekly_index),
        "monthlyUsageIndex": round(monthly_index)
    }

def _get_point_in_time_value(history_map: dict, target_time: str) -> float:
    """'HH:MM' 형식의 시간대별 누적 맵에서 특정 시간의 값을 찾아 반환하는 유틸리티 함수"""
    if target_time in history_map:
        return history_map[target_time]
    
    # 정확한 시간이 없으면, 그 시간 바로 이전의 마지막 값을 찾음
    available_times = sorted([t for t in history_map.keys() if t <= target_time], reverse=True)
    return history_map[available_times[0]] if available_times else 0.0
# main.py 파일의 헬퍼 함수 섹션에 아래 코드를 추가하거나 대체하세요.

# 이 함수는 _generate_comparison_metrics 안에서 사용됩니다.
def _get_point_in_time_value(history_map: dict, target_time: str) -> float:
    """'HH:MM' 형식의 시간대별 누적 맵에서 특정 시간 또는 그 이전의 마지막 값을 찾아 반환합니다."""
    if not history_map:
        return 0.0
    if target_time in history_map:
        return history_map[target_time]
    
    # 정확한 시간이 없으면, 그 시간 바로 이전의 마지막 값을 찾습니다.
    available_times = sorted([t for t in history_map.keys() if t <= target_time], reverse=True)
    return history_map[available_times[0]] if available_times else 0.0

def _generate_comparison_metrics(class_id: str, today_cumulative_map: dict, historical_data: dict, now: datetime) -> dict:
    """
    한 개 반의 '어제/지난주/지난달' 대비 시점별 변화율(%)을 계산합니다.

    :param class_id: 계산할 반의 ID
    :param today_cumulative_map: 오늘 현재까지의 시간대별 누적값 맵
    :param historical_data: 모든 과거 데이터가 담긴 딕셔너리
    :param now: 기준 시각
    :return: comparison 객체 딕셔너리
    """
    now_time_str = now.strftime('%H:%M')
    
    class_history = historical_data.get(class_id, {})

    # --- 어제 대비 (vsLastDay) ---
    today_val = _get_point_in_time_value(today_cumulative_map, now_time_str)
    
    yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_history = class_history.get(yesterday_str, {}).get("cumulative_by_time", {})
    yesterday_val = _get_point_in_time_value(yesterday_history, now_time_str)
    
    vs_last_day = ((today_val / yesterday_val) - 1) * 100 if yesterday_val > 0 else 0.0

    # --- 지난주 대비 (vsLastWeek) ---
    # 이번 주 현재 시점까지의 누적값 계산
    current_weekly_total = today_val
    for i in range(1, now.weekday() + 1): # 월요일(0)부터 어제까지
        day_str = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        current_weekly_total += class_history.get(day_str, {}).get("finalTotal", 0)

    # 지난주 같은 시점까지의 누적값 계산
    last_week_point_date = now - timedelta(weeks=1)
    last_week_point_date_str = last_week_point_date.strftime('%Y-%m-%d')
    last_week_point_history = class_history.get(last_week_point_date_str, {}).get("cumulative_by_time", {})
    last_week_point_val = _get_point_in_time_value(last_week_point_history, last_week_point_date.strftime('%H:%M'))
    
    last_week_total_at_point = last_week_point_val
    for i in range(1, last_week_point_date.weekday() + 1):
        day_str = (last_week_point_date - timedelta(days=i)).strftime('%Y-%m-%d')
        last_week_total_at_point += class_history.get(day_str, {}).get("finalTotal", 0)

    vs_last_week = ((current_weekly_total / last_week_total_at_point) - 1) * 100 if last_week_total_at_point > 0 else 0.0
    
    # --- 지난달 대비 (vsLastMonth) ---
    # 이번 달 현재 시점까지의 누적값 계산
    current_monthly_total = today_val
    for i in range(1, now.day):
        day_str = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        current_monthly_total += class_history.get(day_str, {}).get("finalTotal", 0)

    # 지난달 같은 시점 날짜 계산 (예: 3월 31일의 한달 전은 2월 28/29일)
    last_month_point_date = now - timedelta(days=30) # 간단한 근사치, 더 정확하게 하려면 dateutil 라이브러리 사용
    last_month_point_date_str = last_month_point_date.strftime('%Y-%m-%d')
    last_month_point_history = class_history.get(last_month_point_date_str, {}).get("cumulative_by_time", {})
    last_month_point_val = _get_point_in_time_value(last_month_point_history, last_month_point_date.strftime('%H:%M'))
    
    last_month_total_at_point = last_month_point_val
    for i in range(1, last_month_point_date.day):
        day_str = (last_month_point_date - timedelta(days=i)).strftime('%Y-%m-%d')
        last_month_total_at_point += class_history.get(day_str, {}).get("finalTotal", 0)
        
    vs_last_month = ((current_monthly_total / last_month_total_at_point) - 1) * 100 if last_month_total_at_point > 0 else 0.0

    return {
        "vsLastDay": round(vs_last_day, 1),
        "vsLastWeek": round(vs_last_week, 1),
        "vsLastMonth": round(vs_last_month, 1)
    }


"""
def _create_and_save_rtdb_data(updated_daily_docs):

    # 1. 계산에 필요한 모든 과거 데이터를 Firestore에서 딱 한 번만 불러온다.
    historical_data = _get_all_historical_data() 
    
    final_rtdb_data = { ... } # 최종 JSON 템플릿
    all_class_ids = ["1-1", "1-2", "1-3", "1-4", "1-5", "1-6"]

    # 2. 메모리에 있는 데이터를 가지고 각 반의 지표를 계산한다.
    for class_id in all_class_ids:
        
        # '오늘'의 최신 데이터는 updated_daily_docs에서 가져옴
        today_data = updated_daily_docs.get(class_id)

        # (계산 전문가 1) 메모리의 과거 데이터로 summary 계산
        summary = generate_usage_metrics(class_id, today_data, historical_data)
        
        # (계산 전문가 2) 메모리의 과거 데이터로 comparison 계산
        comparison = generate_comparison_metrics(class_id, today_data, historical_data)

        # 계산 결과를 최종 JSON에 채워넣기
        final_rtdb_data["detailPage"][class_id]["summary"] = summary
        final_rtdb_data["detailPage"][class_id]["comparison"] = comparison
        # ... trends 등 나머지 데이터도 채워넣기 ...
    
    # 3. 모든 반의 계산이 끝난 후, 랭킹 등 2차 계산 수행
    # ...

    # 4. 최종 JSON을 Realtime DB에 저장
    # ...
"""