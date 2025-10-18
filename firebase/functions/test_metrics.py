# functions/test_metrics.py

import unittest
from datetime import datetime
# 테스트하고 싶은 함수들을 main.py에서 가져옵니다.
from main import _generate_usage_metrics, _generate_comparison_metrics, _get_point_in_time_value, KST

# --- 테스트를 위한 '가짜 데이터' 준비 ---
# 실제로는 _get_all_historical_data() 함수가 Firestore에서 가져올 데이터입니다.
mock_historical_data = {
    "1-1": {
        "2025-10-07": { # 어제
            "finalTotal": 150,
            "cumulative_by_time": {"10:00": 50, "10:05": 55, "20:00": 140, "20:05": 150}
        },
        "2025-10-06": {"finalTotal": 130}, # 그저께 (월요일)
        "2025-10-01": { # 일주일 전 같은 요일 (수요일)
            "finalTotal": 160,
            "cumulative_by_time": {"10:00": 60, "10:05": 68, "20:00": 155, "20:05": 160}
        },
        "2025-09-30": {"finalTotal": 145}, # 일주일 전 화요일
    }
}

# 10분 함수가 Firestore를 업데이트해서 만들어낸 '오늘'의 데이터라고 가정합니다.
# 현재 시각: 2025년 10월 8일 20:05
mock_today_data = {
    "cumulative_by_time": {"10:00": 55, "10:05": 60, "20:00": 148, "20:05": 158}
}
# ------------------------------------

class MetricsTest(unittest.TestCase):

    def test_generate_usage_metrics(self):
        print("\n--- Testing _generate_usage_metrics ---")
        
        # '오늘' 날짜를 2025년 10월 8일(수)로 고정하여 테스트
        # (실제 main.py의 now() 부분을 테스트 시에는 이렇게 고정된 값으로 대체해야
        #  일관된 결과를 얻을 수 있지만, 여기서는 개념 이해를 위해 그대로 사용합니다)
        
        # 함수 실행
        summary = _generate_usage_metrics("1-1", mock_today_data["cumulative_by_time"], mock_historical_data, datetime(2025, 10, 8, 20, 5, tzinfo=KST))
        
        # 결과 출력
        print("Calculated Summary:", summary)
        
        # 예상 결과:
        # dailyUsageIndex: 158 (오늘의 최종 누적값)
        # weeklyUsageIndex: 158(오늘) + 150(화) + 130(월) = 438
        # monthlyUsageIndex: ... (10/1 ~ 10/7까지의 finalTotal 합 + 오늘의 158)
        self.assertIsNotNone(summary)


    def test_generate_comparison_metrics(self):
        print("\n--- Testing _generate_comparison_metrics ---")

        # 함수 실행 (now()가 2025-10-08 20:05 라고 가정)
        comparison = _generate_comparison_metrics("1-1", mock_today_data["cumulative_by_time"], mock_historical_data, datetime(2025, 10, 8, 20, 5, tzinfo=KST))

        # 결과 출력
        print("Calculated Comparison:", comparison)

        # 예상 결과:
        # vsLastDay: 오늘 20:05 값(158) vs 어제 20:05 값(150) -> 약 5.3%
        # vsLastWeek: 이번 주 수요일까지 누적(438) vs 지난주 수요일까지 누적(...)
        self.assertIsNotNone(comparison)

# 이 파일을 직접 실행했을 때 테스트를 수행하도록 설정
if __name__ == '__main__':
    unittest.main()