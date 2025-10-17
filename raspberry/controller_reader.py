# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
import sys
import json # 💡 json 모듈 추가
from google import genai
from google.genai import types

# ✅ 환경 변수에 API 키 설정 (안전하게는 코드에 직접 넣지 말고 환경변수로 설정)
os.environ['GEMINI_API_KEY'] = "AIzaSyC0o" 

def generate(image_path: str) -> dict: # 💡 반환 타입을 dict로 명시
    # ✅ 이미지 파일 확인
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # ✅ 이미지 base64로 읽기
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # ✅ Gemini 클라이언트 초기화
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    # ✅ 모델과 프롬프트 설정
    model = "gemini-flash-lite-latest"
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(
                    mime_type="image/jpeg",  # PNG면 "image/png"로 변경
                    data=image_bytes
                ),
                types.Part.from_text(text="Analyze the air conditioner controller image and provide the operating status in JSON format."),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        thinking_config=types.ThinkingConfig(
            thinking_budget=0,
        ),
        system_instruction=[
            types.Part.from_text(text="""
Provide the operating status of the air conditioner controller in the following JSON format. 
Return only the JSON without a code block.

{
"status": "heating|cooling|OFF",
"temperature": "number|Po",
"wind": "verylow|low|medium|strong|auto|power"
}
"""),
        ],
    )

    # ✅ 응답 스트리밍 수집
    full_response_text = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        full_response_text += chunk.text
    
    # 💡 JSON 파싱 및 딕셔너리 반환
    try:
        # 응답 문자열을 Python 딕셔너리로 변환
        parsed_json = json.loads(full_response_text.strip())
        print("--- JSON 파싱 결과 (Python Dictionary) ---")
        # 보기 좋게 출력
        print(json.dumps(parsed_json, indent=4, ensure_ascii=False)) 
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"--- JSON 파싱 오류 발생 ---")
        print(f"오류: {e}")
        print(f"수신된 원본 텍스트: '{full_response_text.strip()}'")
        return {} # 파싱 실패 시 빈 딕셔너리 반환

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    
    # 💡 generate 함수 실행 및 결과 딕셔너리 받기
    result_dict = generate(image_path)
    
    # 딕셔너리 사용 예시
    if result_dict:
        print("\n--- 딕셔너리에서 값 접근 예시 ---")
        print(f"운전 상태 (status): {result_dict.get('status', 'N/A')}")
        print(f"설정 온도 (temperature): {result_dict.get('temperature', 'N/A')}")