'''

================================================================================
|                               개선이 필요한 것                                   |
================================================================================

달 계산할 떄 30일 빼는게 아니라 dateutil 같은 라이브러리 써서 정확하게 계산하기 --> 그냥 당장은 귀찮아서 넘어갔는데 나중에 고치기

ALL_CLASS_IDS 하드코딩 말고 어디서든지 가져올 수 있게 하기 (파이어스토어에 반 목록 따로 저장해두기?)

이상적인 상황을 가정한 코드이므로, 실제 운영 환경에서는 추가적인 예외 처리 및 최적화가 필요할 수 있음
-> 지금 당장 생각나는 거는 OCR이 안돼서 ac_logs에 문서가 없는 경우(결측치 어떻게 처리할건지... -- 그리고 뭔가 딜레이가 생겨서 정확히 5분만에 들어오지 않은 경우 어떻게 할건지)
-> finalize_daily_stats가 실행이 안되면 걍 꼬임

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
#from firebase_functions import options, scheduler_fn
from firebase_functions import options, scheduler_fn, https_fn #시뮬레이션용
import logging
from firebase_admin import initialize_app, firestore, db
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore import FieldFilter




# --- 초기 설정 ---
initialize_app()
options.set_global_options(region="asia-northeast3", memory=options.MemoryOption.MB_256)
logging.basicConfig(level=logging.DEBUG)
# -----------------

# =================================================================================
# |                         10분마다 실행되는 메인 함수                              |
# =================================================================================


#@scheduler_fn.on_schedule(schedule="every 10 minutes")
#def analyze_and_update_data(event: scheduler_fn.ScheduledEvent) -> None:
@https_fn.on_call()   # 시뮬레이션용
def analyze_and_update_data(req: https_fn.CallableRequest) -> any: # 시뮬레이션용
    """
    10분마다 실행되어 실시간 데이터 집계 및 Realtime DB 업데이트를 수행합니다.
    """
    logging.debug("✅ (10분 주기) 데이터 분석 작업을 시작합니다.")
    try:
        # 1. Firestore 'ac_logs'에서 최근 10분간의 로그를 가져옵니다.
        recent_logs = _get_recent_logs()
        if not recent_logs:
            logging.debug("- 새로운 데이터가 없어 작업을 종료합니다.")
            return

        # 2. 로그에 미리 계산된 usageIndex를 반별로 합산합니다.
        new_points_by_class = _aggregate_indexes_from_logs(recent_logs)
        logging.debug("🎉 (10분 주기) 데이터 분석 및 저장을 성공적으로 완료했습니다.")

        # 3. Firestore 'daily_history'에 시간대별 누적 값을 업데이트합니다.
        updated_daily_docs = _update_firestore_history(new_points_by_class)
        logging.debug("Firestore 'daily_history'에 시간대별 누적 값을 업데이트했습니다.")

        # 4. 업데이트된 최신 데이터를 바탕으로 Realtime DB용 최종 JSON을 생성하고 저장합니다.
        _create_and_save_rtdb_data(updated_daily_docs)
        logging.debug("RealtimeDB를 생성하고 저장했습니다.")

        logging.debug("(10분 주기) 데이터 분석 및 저장을 성공적으로 완료했습니다.")
    except Exception as e:
        logging.error(f"(10분 주기) 작업 중 에러 발생: {e}")

# =================================================================================
# |                          자정마다 실행되는 마감 함수                             |
# =================================================================================
@scheduler_fn.on_schedule(schedule="59 23 * * *", timezone=scheduler_fn.Timezone("Asia/Seoul"))
def finalize_daily_stats(event: scheduler_fn.ScheduledEvent) -> None:
    """
    매일 23시 59분에 실행되어 그날의 데이터를 최종 마감 처리합니다.
    """
    logging.debug("✅ (자정 주기) 일일 데이터 마감 작업을 시작합니다.")
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
                    logging.debug(f"- {class_id}반 {yesterday_str}의 최종값 {round(final_total)}을 저장했습니다.")

        logging.debug("🎉 (자정 주기) 일일 데이터 마감 작업을 성공적으로 완료했습니다.")
    except Exception as e:
        logging.error(f"🔥 (자정 주기) 작업 중 에러 발생: {e}")

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
    logging.debug(f"- Firestore에서 {len(logs)}개의 새 로그를 가져왔습니다.")
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
        
    logging.debug(f"- {today_str} Firestore 일일 원장을 업데이트했습니다.")
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
        #daily_docs_query = class_doc.reference.collection("daily_history").where(filter=FieldFilter(FieldPath.document_id(), ">=", start_date_str)) --> 이거 KEY가 문자열이 아니라 다른 특수 번호라 오류남. 
        daily_docs_query = class_doc.reference.collection("daily_history").order_by(FieldPath.document_id()).start_at([start_date_str])
        
        for daily_doc in daily_docs_query.stream():
            historical_data[class_id][daily_doc.id] = daily_doc.to_dict()
            
    logging.debug(f"- {len(historical_data)}개 반의 과거 데이터를 Firestore에서 가져왔습니다.")
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
    for i in range(1, now.weekday()+1): # 월요일(0) ~ 일요일(6)
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
def _create_system_wide_history(historical_data: dict) -> dict:
    """
    모든 반의 과거 데이터를 합산하여 시스템 전체의 과거 데이터를 생성합니다.
    데이터가 누락된 경우를 고려하여 각 시점의 마지막 값을 기준으로 합산합니다.
    """
    system_history = {}
    
    # 분석할 모든 날짜와 모든 시간대를 수집
    all_dates = set()
    all_times_by_date = {}
    for class_history in historical_data.values():
        for date_str, day_data in class_history.items():
            all_dates.add(date_str)
            if date_str not in all_times_by_date:
                all_times_by_date[date_str] = set()
            all_times_by_date[date_str].update(day_data.get("cumulative_by_time", {}).keys())

    # 각 날짜별로 순회
    for date_str in sorted(list(all_dates)):
        system_cumulative_map = {}
        # 해당 날짜에 기록된 모든 시간대를 정렬하여 순회
        sorted_times = sorted(list(all_times_by_date.get(date_str, set())))

        for time_str in sorted_times:
            total_at_time = 0
            # 모든 반에 대해 해당 시점의 값을 더함
            for class_id, class_history in historical_data.items():
                day_data = class_history.get(date_str, {})
                cumulative_map = day_data.get("cumulative_by_time", {})
                # _get_point_in_time_value 함수를 재사용하여 누락된 데이터를 처리
                total_at_time += _get_point_in_time_value(cumulative_map, time_str)
            
            system_cumulative_map[time_str] = total_at_time
        
        # 그날의 최종값(finalTotal)도 합산
        final_total = sum(ch.get(date_str, {}).get("finalTotal", 0) for ch in historical_data.values())

        system_history[date_str] = {
            "finalTotal": final_total,
            "cumulative_by_time": system_cumulative_map
        }
        
    return system_history

def _create_and_save_rtdb_data(updated_daily_docs: dict) -> None:
    """Realtime DB에 저장할 최종 JSON을 생성하고 저장합니다."""
    logging.debug("- Realtime DB용 데이터 생성을 시작합니다.")
    now = datetime.now(KST)
    all_class_ids = ["1-1", "1-2", "1-3", "1-4", "1-5", "1-6"]
    # 1. 계산에 필요한 모든 과거 데이터를 Firestore에서 딱 한 번만 불러옵니다.
    historical_data = _get_all_historical_data()
    logging.debug("- Realtime DB용 데이터를 불러옵니다.")

    final_rtdb_data = {
        "mainPage": {},
        "detailPage": {},
        "comparisonPage": {"classTrends": []}
    }

    all_detail_pages = {}
    
    # 2. 각 반의 detailPage 데이터를 계산합니다.
    for class_id in all_class_ids:
        today_cumulative_map = updated_daily_docs.get(class_id, {})
        class_history = historical_data.get(class_id, {})
        
        # summary 계산
        summary = _generate_usage_metrics(class_id, today_cumulative_map, class_history)
        
        # comparison 계산
        comparison = _generate_comparison_metrics(class_id, today_cumulative_map, class_history)
        
        # trends 데이터 가공
        trends = _format_trends_data(today_cumulative_map, class_history)
        
        all_detail_pages[class_id] = {
            "className": f"1학년 {class_id.split('-')[1]}반", # 예시
            "summary": summary,
            "comparison": comparison,
            "trends": trends
        }
    final_rtdb_data["detailPage"] = all_detail_pages

    # 3. mainPage 및 comparisonPage 데이터를 계산합니다.
    final_rtdb_data["mainPage"] = _generate_main_page_data(all_detail_pages)
    final_rtdb_data["comparisonPage"] = _generate_comparison_page_data(all_detail_pages)
    
    # 4. 최종 데이터를 Realtime Database에 저장합니다.
    rtdb_ref = db.reference('/')
    rtdb_ref.set(final_rtdb_data)
    logging.debug("- Realtime DB에 최종 데이터를 저장했습니다.")
def _format_trends_data(today_map: dict, history: dict) -> dict:
    """그래프용 trends 데이터를 최종 배열 형식으로 가공합니다."""
    now = datetime.now(KST)
    
    # last7Days 가공
    last7days_arr = []
    for i in range(7):
        date = now - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        value = history.get(date_str, {}).get("finalTotal", 0)
        last7days_arr.append({"date": date_str, "value": round(value)})
    
    # last4Weeks, todayRealtime 가공 로직 추가
    
    return {
        "last7Days": sorted(last7days_arr, key=lambda x: x['date']),
        "last4Weeks": [], # TODO
        "todayRealtime": [{"time": t, "value": round(v)} for t, v in sorted(today_map.items())]
    }

def _generate_main_page_data(all_details: dict, historical_data: dict) -> dict:
    """mainPage 데이터를 생성합니다."""
    # 1. 랭킹 생성
    ranking = sorted(
        [
            {"classId": cid, "className": d["className"], "monthlyUsageIndex": d["summary"]["monthlyUsageIndex"]}
            for cid, d in all_details.items()
        ],
        key=lambda x: x["monthlyUsageIndex"]
    )

    # 2. 시스템 전체의 과거 데이터를 생성
    system_history = _create_system_wide_history(historical_data)
    
    # 3. 시스템 전체의 '오늘' 데이터 합산
    system_today_map = {}
    for details in all_details.values():
        for time_str, value in details["trends"]["todayRealtime"]:
            system_today_map[time_str] = system_today_map.get(time_str, 0) + value

    # 4. _generate_comparison_metrics 함수 재사용!
    system_comparison = _generate_comparison_metrics("system", system_today_map, {"system": system_history})
    
    return {
        "monthlyRanking": ranking,
        "systemIndexChangeVsLastWeek": system_comparison["vsLastWeek"],
        "lastUpdated": datetime.now(KST).isoformat()
    }

def _generate_comparison_page_data(all_details: dict, historical_data: dict) -> dict:
    """comparisonPage 데이터를 생성합니다."""
    # 1. 시스템 전체의 과거 및 오늘 데이터 생성 (mainPage와 동일)
    system_history = _create_system_wide_history(historical_data)
    system_today_map = {}
    for details in all_details.values():
        for time_obj in details["trends"]["todayRealtime"]:
            time_str, value = time_obj["time"], time_obj["value"]
            system_today_map[time_str] = system_today_map.get(time_str, 0) + value

    # 2. 기존 함수들을 재사용하여 시스템 전체의 summary와 comparison 계산
    system_summary = _generate_usage_metrics("system", system_today_map, {"system": system_history})
    system_comparison = _generate_comparison_metrics("system", system_today_map, {"system": system_history})
    
    # 3. classTrends 데이터 구성
    class_trends = [
        {"classId": cid, **d["trends"]} for cid, d in all_details.items()
    ]

    return {
        "summary": system_summary,
        "comparison": system_comparison,
        "classTrends": class_trends,
        "lastUpdated": datetime.now(KST).isoformat()
    }

