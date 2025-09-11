# controller_reader.py

def read_ac_status():
    """
    하드웨어 컨트롤러의 상태를 1회 읽어와 dictionary 형태로 반환합니다.
    성공 시: {'isOn': True, 'mode': '냉방', ...}
    실패 시: None
    """
    try:
        # --- 여기에 하드웨어와 통신하는 실제 코드가 들어갑니다 ---
        #
        #
        #
        # (지금은 하드웨어가 없으므로 성공했다고 가정하고 가짜 데이터를 반환)
        
        mock_data = {
            'isOn': True,
            'mode': "냉방",
            'temperature': 24.5,
            'fanSpeed': "자동",
            'errorState': None
        }
        return mock_data
    
    except Exception as e:
        # 하드웨어 통신 중 에러가 발생했을 때
        print(f"하드웨어 통신 에러: {e}")
        return None