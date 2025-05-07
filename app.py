
import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# .env 파일에서 인증키 불러오기
load_dotenv()
DEFAULT_AUTH_KEY = os.getenv("AUTH_KEY", "")

st.set_page_config(layout="wide")

# Pretendard 글꼴 적용
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/npm/pretendard@1.3.8/dist/web/static/pretendard.css');

    html, body, [class*="css"]  {
        font-family: 'Pretendard', sans-serif !important;
        font-size: 15px;
    }

    .title-text {
        font-size: 22px !important;
        font-weight: 600;
        font-family: 'Pretendard SemiBold', Pretendard, sans-serif;
    }

    .sub-header {
        color: #2A4365;
        font-weight: 600;
    }

    .dataframe thead tr th {
        color: #2A4365;
    }

    td {
        text-align: right;
    }

    </style>
""", unsafe_allow_html=True)

# ⭕ 타이틀
st.markdown('<p class="title-text">고용24 사업주훈련 분석 대시보드</p>', unsafe_allow_html=True)

# 🔶 1단: 인증키, 훈련유형
col1, col2 = st.columns([2, 1])
with col1:
    auth_key = st.text_input("인증키", type="password", value=DEFAULT_AUTH_KEY)
with col2:
    course_type = st.selectbox("훈련유형 선택", ["전체", "일반직무훈련", "기업직업훈련카드", "고숙련신기술훈련", "패키지구독형 원격"])

# 🔶 2단: 날짜 범위 선택
today = datetime.today()
default_start = today.strftime("%Y-%m-%d")
default_end = (today + timedelta(days=30)).strftime("%Y-%m-%d")

col3, col4 = st.columns(2)
with col3:
    start_date = st.date_input("개강일 범위 (시작)", value=pd.to_datetime(default_start))
with col4:
    end_date = st.date_input("개강일 범위 (종료)", value=pd.to_datetime(default_end))

# 🔘 버튼
if st.button("데이터 수집"):
    if not auth_key:
        st.warning("인증키를 입력해주세요.")
    else:
        crse_map = {
            "전체": "",
            "일반직무훈련": "C0041T",
            "기업직업훈련카드": "C0041B",
            "고숙련신기술훈련": "C0041N",
            "패키지구독형 원격": "C0041H"
        }
        crse_type_code = crse_map[course_type]
        s_date = start_date.strftime("%Y%m%d")
        e_date = end_date.strftime("%Y%m%d")

        BASE_URL = 'https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo311L01.do'
        results = []

        for page in range(1, 1000):
            params = {
                'authKey': auth_key,
                'returnType': 'XML',
                'outType': '1',
                'pageNum': str(page),
                'pageSize': '100',
                'srchTraStDt': s_date,
                'srchTraEndDt': e_date,
                'crseTracseSe': crse_type_code,
                'sort': 'ASC',
                'sortCol': 'TRNG_BGDE'
            }

            try:
                res = requests.get(BASE_URL, params=params, timeout=30)
                root = ET.fromstring(res.content)
                rows = root.find('srchList')
                if rows is None:
                    break
                for item in rows.findall('scn_list'):
                    기관 = item.findtext('subTitle', '')
                    과정 = item.findtext('title', '')
                    회차 = item.findtext('trprDegr', '')
                    개강일 = item.findtext('traStartDate', '')
                    신청인원 = item.findtext('regCourseMan', '0')
                    교육비 = item.findtext('realMan', '0')
                    교육비합계 = int(신청인원) * int(교육비)
                    results.append([기관, 과정, 회차, 개강일, int(신청인원), int(교육비), 교육비합계])
                if not rows.findall('scn_list'):
                    break
            except:
                break

        if results:
            df = pd.DataFrame(results, columns=["훈련기관명", "훈련과정명", "회차", "개강일", "신청인원", "교육비", "교육비합계"])
            df["신청인원"] = df["신청인원"].astype(int)
            df["교육비"] = df["교육비"].astype(int)
            df["교육비합계"] = df["교육비합계"].astype(int)

            st.markdown("### 📊 데이터 분석 결과")
            total_rows = len(df)
            st.write(f"🔹 총 {total_rows}건의 훈련 회차 정보가 수집되었습니다.")
            st.write(df.style.format({"신청인원": "{:,}", "교육비": "{:,}", "교육비합계": "{:,}"}).hide_index())

            now = datetime.now().strftime("%Y%m%d_%H%M")
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False, engine="openpyxl")
            st.download_button(
                label="📥 Excel 다운로드",
                data=excel_buffer.getvalue(),
                file_name=f"훈련과정_목록_{now}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("조건에 맞는 데이터가 없습니다.")
