
import cv2
import numpy as np
import pytesseract
import json
import time
import os

# --- 1단계: 초기 설정 및 준비 ---

# Mac에서 Tesseract가 기본 경로에 설치되지 않은 경우, 아래 줄의 주석을 해제하고 경로를 지정하세요.
# 예: pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'

# (중요) 정보가 위치한 영역의 좌표 (x, y, 너비, 높이)
# 이 값들은 카메라 뷰에 맞춰 반드시 수동으로 조정해야 합니다.
ROI_COORDS = {
    "temperature": (300, 200, 150, 80),  # 온도 표시 영역
    "mode": (100, 200, 100, 100),         # 운전 모드 아이콘 영역
    "fan_speed": (100, 350, 100, 100)     # 바람 세기 아이콘 영역
}

# (중요) 아이콘 인식을 위한 템플릿 이미지 경로
# 생성된 임시 파일을 실제 아이콘 이미지로 교체해야 합니다.
ICON_TEMPLATES = {
    "mode": {
        "cooling": "cooling_icon.png",
        "heating": "heating_icon.png"
    },
    "fan_speed": {
        "low": "fan_low_icon.png",
        "high": "fan_high_icon.png"
    }
}

# --- 2단계: 이미지 캡처 및 전처리 함수 ---

def capture_image_from_webcam():
    """Mac의 웹캠에서 이미지를 캡처하여 저장합니다."""
    # 웹캠 열기 (0은 기본 웹캠)
    cap = cv2.VideoCapture(1)
    
    if not cap.isOpened():
        print("오류: 웹캠을 열 수 없습니다.")
        return None

    # 잠시 시간을 주어 카메라가 안정되도록 함
    time.sleep(2)

    # 프레임 읽기
    ret, frame = cap.read()

    # 웹캠 해제
    cap.release()

    if not ret:
        print("오류: 프레임을 캡처할 수 없습니다.")
        return None
    
    # 캡처된 이미지를 파일로 저장
    captured_path = "capture.jpg"
    cv2.imwrite(captured_path, frame)
    print(f"이미지가 {captured_path}에 저장되었습니다.")
    return captured_path

# --- 3단계: 정보 추출 함수 ---

def extract_temperature(image, roi_coords):
    """ROI에서 이미지를 잘라내고 OCR로 온도를 추출합니다."""
    x, y, w, h = roi_coords
    roi = image[y:y+h, x:x+w]

    # OCR 정확도 향상을 위한 전처리
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    # 적절한 임계값(threshold)을 찾아 조정할 수 있습니다.
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Tesseract로 숫자 인식
    # config: --psm 7 (한 줄의 텍스트로 간주), -c tessedit_char_whitelist (인식할 문자 지정)
    custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789.'
    try:
        text = pytesseract.image_to_string(thresh, config=custom_config)
        # 추출된 텍스트에서 숫자만 정리
        temp = "".join(filter(str.isdigit, text))
        return int(temp) if temp else "N/A"
    except Exception as e:
        print(f"온도 인식 중 오류 발생: {e}")
        return "Error"

def recognize_icon(image, roi_coords, templates):
    """ROI에서 템플릿 매칭을 통해 가장 일치하는 아이콘을 찾습니다."""
    x, y, w, h = roi_coords
    roi = image[y:y+h, x:x+w]
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    best_match = {"name": "N/A", "score": -1}

    for name, path in templates.items():
        if not os.path.exists(path):
            print(f"경고: 템플릿 파일을 찾을 수 없습니다 - {path}")
            continue
            
        template = cv2.imread(path, 0)
        if template is None:
            print(f"경고: 템플릿 파일을 읽을 수 없습니다 - {path}")
            continue

        res = cv2.matchTemplate(roi_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)

        if max_val > best_match["score"]:
            best_match["score"] = max_val
            best_match["name"] = name
    
    # 특정 신뢰도 이상일 때만 인정 (예: 0.7)
    if best_match["score"] > 0.7:
        return best_match["name"]
    else:
        return "Unknown"

# --- 4단계: 메인 로직 ---

def main_process():
    """전체 정보 추출 과정을 실행하고 결과를 JSON으로 저장합니다."""
    # 4.1. 웹캠에서 사진 촬영
    captured_path = capture_image_from_webcam()
    if captured_path is None:
        return

    # 분석할 이미지 불러오기
    image = cv2.imread(captured_path)
    if image is None:
        print("오류: 캡처된 이미지를 읽을 수 없습니다.")
        return

    # 4.2. 정보 추출
    temperature = extract_temperature(image, ROI_COORDS["temperature"])
    mode = recognize_icon(image, ROI_COORDS["mode"], ICON_TEMPLATES["mode"])
    fan_speed = recognize_icon(image, ROI_COORDS["fan_speed"], ICON_TEMPLATES["fan_speed"])

    # 4.3. JSON 데이터 생성
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "temperature": temperature,
        "mode": mode,
        "fan_speed": fan_speed
    }

    # 4.4. JSON 파일로 저장
    output_filename = 'controller_info.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"정보가 {output_filename}에 저장되었습니다.")
    print(json.dumps(data, indent=4, ensure_ascii=False))

# --- 스크립트 실행 ---
if __name__ == "__main__":
    main_process()
