import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import datetime
import io
import os
from dotenv import load_dotenv

# 1. 환경변수 로드
load_dotenv()
AUTH_KEY = os.getenv("AUTH_KEY", "")
if not AUTH_KEY:
    st.error("❗ 환경변수 `AUTH_KEY`가 설정되어 있지 않습니다. `.env` 파일을 확인해주세요.")
    st.stop()

# 2. 전역 CSS 설정
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; font-size: 15px; }

        /* 페이지 제목 */
        .title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 1rem;
        }

        /* 카드 스타일 */
        .card {
            background: #fff;
            border: 1px solid #ececec;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }

        /* 카드 내부 섹션 타이틀 */
        .section-title {
            font-size: 17px;
            font-weight: 600;
            color: #1a4c8b;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid #dfe3e8;
            padding-bottom: 0.25rem;
        }

        /* 버튼/라디오 마진 */
        .stButton > button { margin-top: 0.5rem; margin-bottom: 1rem; }
        .stRadio > div    { margin-top: 1rem; margin-bottom: 1rem; }

        /* 테이블 헤더 음영 + 가운데 정렬 */
        .card table th {
            background-color: #f5f6fa !important;
            text-align: center !important;
            font-weight: 600 !important;
        }
        /* 홀수 행 음영 */
        .card table tr:nth-child(odd) td {
            background-color: #fbfbfb !important;
        }
        /* No, 회차 컬럼 가운데 정렬 */
        .card table td:nth-child(1),
        .card table td:nth-child(3) {
            text-align: center !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. 페이지 제목
st.markdown("<div class='title'>사업주훈련(고용24) 분석 대시보드</div>", unsafe_allow_html=True)

# 4. 파라미터 입력 카드
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>파라미터 설정</div>", unsafe_allow_html=True)

crse_type = st.selectbox(
    "훈련유형 선택",
    options=[
        ("전체", ""),
        ("일반직무훈련", "C0041T"),
        ("기업직업훈련카드", "C0041B"),
        ("고숙련신기술훈련", "C0041N"),
        ("패키지구독형 원격", "C0041H")
    ],
    format_func=lambda x: x[0]
)[1]

today = datetime.date.today()
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("개강일 범위 (시작)", value=today)
with col2:
    end_date = st.date_input("개강일 범위 (종료)", value=today + datetime.timedelta(days=30))

if st.button("데이터 수집 시작"):
    BASE_URL = 'https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo311L01.do'
    results = []
    with st.spinner("🔄 데이터를 수집 중입니다..."):
        for page in range(1, 1000):
            params = {
                'authKey': AUTH_KEY,
                'returnType': 'XML',
                'outType': '1',
                'pageNum': str(page),
                'pageSize': '100',
                'srchTraStDt': start_date.strftime('%Y%m%d'),
                'srchTraEndDt': end_date.strftime('%Y%m%d'),
                'crseTracseSe': crse_type,
                'sort': 'ASC',
                'sortCol': 'TRNG_BGDE'
            }
            resp = requests.get(BASE_URL, params=params, timeout=30)
            root = ET.fromstring(resp.content)
            items = root.find('srchList')
            rows = items.findall('scn_list') if items is not None else []
            if not rows:
                break
            for r in rows:
                try:
                    results.append({
                        "훈련기관":   r.findtext('subTitle',''),
                        "훈련과정명": r.findtext('title',''),
                        "회차":      r.findtext('trprDegr',''),
                        "개강일":    r.findtext('traStartDate',''),
                        "신청인원":   int(r.findtext('regCourseMan','0')),
                        "교육비":    int(r.findtext('realMan','0')),
                    })
                except:
                    continue

    if results:
        df = pd.DataFrame(results)
        df["교육비합계"] = df["신청인원"] * df["교육비"]
        grouped = (
            df.groupby("훈련기관")
              .agg(
                  회차       = ("회차",       "count"),
                  신청인원    = ("신청인원",   "sum"),
                  교육비합계   = ("교육비합계","sum")
              )
              .reset_index()
        )
        st.session_state.df_raw     = df
        st.session_state.df_grouped = grouped
    else:
        st.error("❌ 조건에 맞는 데이터가 없습니다.")

st.markdown("</div>", unsafe_allow_html=True)  # 파라미터 카드 닫기

# 5. 결과 영역 카드
if "df_grouped" in st.session_state:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>데이터 분석 결과</div>", unsafe_allow_html=True)

    sort_option = st.radio(
        "정렬 기준",
        options=["훈련기관명", "교육비 합계"],
        index=1,
        horizontal=True,
        key="sort_main"
    )
    grp = st.session_state.df_grouped.copy()
    if sort_option == "교육비 합계":
        grp = grp.sort_values("교육비합계", ascending=False)
    else:
        grp = grp.sort_values("훈련기관")

    grp = grp.reset_index(drop=True)
    grp.insert(0, "No", range(1, len(grp) + 1))

    st.dataframe(
        grp.style.format({"신청인원":"{:,}", "교육비합계":"{:,}"}),
        use_container_width=True
    )

    buf = io.BytesIO()
    st.session_state.df_raw.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "엑셀 파일 다운로드",
        data=buf,
        file_name=f"훈련과정_회차_목록_{ts}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("</div>", unsafe_allow_html=True)  # 결과 카드 닫기
