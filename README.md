# 고용24 대시보드

사업주훈련(고용24) 데이터를 분석하고 시각화하는 Streamlit 대시보드입니다.

## 설치 방법

1. 저장소 클론:
```bash
git clone [repository-url]
cd [repository-name]
```

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정:
- `.env` 파일을 생성하고 다음 내용을 추가:
```
AUTH_KEY=your_api_key_here
```
- `your_api_key_here`를 실제 API 키로 교체

4. 앱 실행:
```bash
streamlit run app_v1.py
```

## 주요 기능

- 훈련유형별 데이터 조회
- 개강일자 범위 설정
- 데이터 시각화 및 분석
- 엑셀 파일 다운로드

## 주의사항

- API 키는 절대 공개 저장소에 커밋하지 마세요.
- `.env` 파일은 반드시 `.gitignore`에 포함되어 있어야 합니다. 