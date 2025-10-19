import math
from collections import deque
from typing import Optional

class UsageIndexCalculator:
    def __init__(self, window_size: int = 5, initial_value: float = 5.0):
        # 최근 사용지수만 저장, 초기값 5개는 5.0으로 채움
        self.recent_values = deque([initial_value]*window_size, maxlen=window_size)

    def calculate_usage_index(
        self,
        mode: Optional[str], #모드는 str로 받아오기,만약 측정 안되면 None으로 반환
        indoor_temp_setting: Optional[float], #실내온도는 float로 받아오기,만약 안되면 float('nan')으로 반환
        fan_speed: Optional[str], #풍속은 str로 받아오기,만약 측정 안되면 None으로 반환
        outdoor_temp: Optional[float], #외부온도는 float으로 받아오기,만약 측정 안되면 float('nan')으로 반환
        is_on: Optional[bool] #외부온도는 bool로 받아오기,만약 측정 안되면 None으로 반환
    ) -> float:
        # 결측치 확인
        def is_missing(value):
            return value is None or (isinstance(value, float) and math.isnan(value))

        # --- 1. 꺼져 있는 경우 ---
        if is_on is False:
            return 0.0

        # --- 2. 결측치 존재 또는 상태 확인 불가 → 이동평균 반환 ---
        if (is_missing(indoor_temp_setting) or
            is_missing(outdoor_temp) or
            mode is None or
            fan_speed is None or
            is_on is None):
            return round(sum(self.recent_values) / len(self.recent_values), 2)

        # --- 3. 사용지수 계산 ---
        base_points = 5.0
        fan_multipliers = {"약풍": 1.0, "중풍": 1.1, "강풍": 1.2, "자동": 1.05, "파워": 1.3}
        fan_multiplier = fan_multipliers.get(fan_speed, 1.0)

        if mode == "냉방":
            temp_multiplier = 1.0 + max(0, 26 - indoor_temp_setting) * 0.15
            load_multiplier = 1.0 + max(0, outdoor_temp - indoor_temp_setting) * 0.05
            efficiency_multiplier = 1.0 + max(0, outdoor_temp - 30.0) * 0.03
        elif mode == "난방":
            temp_multiplier = 1.0 + max(0, indoor_temp_setting - 20) * 0.15
            load_multiplier = 1.0 + max(0, indoor_temp_setting - outdoor_temp) * 0.05
            efficiency_multiplier = 1.0 + max(0, 5.0 - outdoor_temp) * 0.03
        else:
            # 알 수 없는 모드 → 이동평균 반환
            return round(sum(self.recent_values) / len(self.recent_values), 2)

        usage_index = round(base_points * temp_multiplier * fan_multiplier * load_multiplier * efficiency_multiplier, 2)

        # --- 4. 최근 사용지수 갱신 ---
        self.recent_values.append(usage_index)

        # --- 5. 계산된 사용지수 반환 ---
        return usage_index