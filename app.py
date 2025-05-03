import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# 🔐 기본 인증키 (여기에 본인의 인증키 입력)
DEFAULT_AUTH_KEY = "여기에_본인_API_인증키를_입력하세요"

# 🗓 오늘 날짜 기준
today = datetime.today()
default_start_date = today
default_end_date = today + timedelta(days=30)

# ▶ Pretendard 스타일 적용
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }
    .title {
        font-family: 'Pretendard', sans-serif;
        font-size: 20px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📊 고용24 사업주훈련 데이터 수집 대시보드</div>', unsafe_allow_html=True)

# ▶ 세션 초기화
if 'auth_key' not in st.session_state:
    st.session_state.auth_key = DEFAULT_AUTH_KEY
if 'raw_df' not in st.session_state:
    st.session_state.raw_df = pd.DataFrame()
if 'group_df' not in st.session_state:
    st.session_state.group_df = pd.DataFrame()

# ▶ 인증키 입력
with st.expander("🔑 인증키 입력", expanded=True):
    auth_key_input = st.text_input("API 인증키 입력", value=st.session_state.auth_key)
    if st.button("✅ 인증키 저장"):
        st.session_state.auth_key = auth_key_input
        st.success("인증키가 저장되었습니다.")

# ▶ 개강일 범위 (분리 입력 + ~ 표시)
col1, col2, col3 = st.columns([1.2, 0.2, 1.2])
with col1:
    start_date = st.date_input("📅 시작일", default_start_date)
with col2:
    st.markdown("<div style='margin-top:35px; text-align:center;'>~</div>", unsafe_allow_html=True)
with col3:
    end_date = st.date_input("📅 종료일", default_end_date)

# ▶ 훈련유형 선택
course_type = st.selectbox(
    "📦 훈련유형 선택",
    ("전체", "일반직무훈련(C0041T)", "기업직업훈련카드(C0041B)", "고숙련신기술훈련(C0041N)", "패키지구독형 원격(C0041H)")
)

course_type_code = {
    "전체": "",
    "일반직무훈련(C0041T)": "C0041T",
    "기업직업훈련카드(C0041B)": "C0041B",
    "고숙련신기술훈련(C0041N)": "C0041N",
    "패키지구독형 원격(C0041H)": "C0041H"
}[course_type]

# ▶ 실행 버튼
col_run, col_stop = st.columns([1, 1])
run_clicked = col_run.button("📡 데이터 수집 시작")
stop_clicked = col_stop.button("🛑 실행 중지")

# ▶ 데이터 수집
if run_clicked:
    if not st.session_state.auth_key:
        st.error("❗ 인증키를 입력해 주세요.")
    elif start_date > end_date:
        st.error("❗ 시작일이 종료일보다 늦을 수 없습니다.")
    else:
        with st.spinner("데이터 수집 중..."):
            url = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo311L01.do"
            results = []
            try:
                for page in range(1, 1001):
                    params = {
                        "authKey": st.session_state.auth_key,
                        "returnType": "XML",
                        "outType": "1",
                        "pageNum": str(page),
                        "pageSize": "100",
                        "srchTraStDt": start_date.strftime('%Y%m%d'),
                        "srchTraEndDt": end_date.strftime('%Y%m%d'),
                        "crseTracseSe": course_type_code,
                        "sort": "ASC",
                        "sortCol": "TRNG_BGDE"
                    }
                    res = requests.get(url, params=params, timeout=30)
                    root = ET.fromstring(res.content)
                    scn_list = root.find('srchList')
                    rows = scn_list.findall('scn_list') if scn_list is not None else []
                    if not rows:
                        break
                    for row in rows:
                        results.append({
                            '훈련기관명': row.findtext('subTitle', ''),
                            '훈련과정명': row.findtext('title', ''),
                            '회차': row.findtext('trprDegr', ''),
                            '훈련개강일': row.findtext('traStartDate', ''),
                            '수강신청인원': int(row.findtext('regCourseMan', '0')),
                            '교육비(실제)': int(row.findtext('realMan', '0'))
                        })
            except Exception as e:
                st.error(f"❗ 요청 실패: {e}")

            if results:
                raw_df = pd.DataFrame(results)
                raw_df['교육비 합계'] = raw_df['수강신청인원'] * raw_df['교육비(실제)']
                st.session_state.raw_df = raw_df

                group_df = raw_df.groupby('훈련기관명').agg(
                    회차수=('회차', 'count'),
                    수강신청인원합계=('수강신청인원', 'sum'),
                    교육비합계=('교육비 합계', 'sum')
                ).reset_index()
                st.session_state.group_df = group_df
            else:
                st.warning("❗ 수집된 데이터가 없습니다.")

# ▶ 집계 데이터 표시
if not st.session_state.group_df.empty:
    group_df = st.session_state.group_df.copy()

    # 훈련기관 필터
    org_options = ['전체'] + sorted(group_df['훈련기관명'].dropna().unique().tolist())
    selected_org = st.selectbox("🏫 훈련기관 선택", org_options)
    if selected_org != '전체':
        group_df = group_df[group_df['훈련기관명'] == selected_org]

    # 정렬 옵션
    sort_col = st.selectbox("정렬 기준", ['훈련기관명', '교육비합계'])
    ascending = st.radio("정렬 순서", ['오름차순', '내림차순']) == '오름차순'
    group_df = group_df.sort_values(by=sort_col, ascending=ascending).reset_index(drop=True)

    # 넘버링
    group_df.insert(0, '순번', range(1, len(group_df) + 1))

    # 숫자 포맷
    display_df = group_df.copy()
    display_df['수강신청인원합계'] = display_df['수강신청인원합계'].map('{:,}'.format)
    display_df['교육비합계'] = display_df['교육비합계'].map('{:,}'.format)

    st.markdown("### 📊 데이터 분석 결과")

    # 페이지네이션
    page_size = 20
    total_pages = (len(display_df) - 1) // page_size + 1
    page = st.radio("", list(range(1, total_pages + 1)), horizontal=True)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    st.table(display_df.iloc[start_idx:end_idx])

    # Excel 다운로드 (.xlsx)
    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        st.session_state.raw_df.to_excel(writer, index=False, sheet_name="회차별 데이터")

    st.download_button(
        label="⬇️ Excel 다운로드 (회차별)",
        data=excel_buffer.getvalue(),
        file_name=f"훈련과정_회차별_데이터_{now_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("❗ 수집된 데이터가 없습니다. 먼저 데이터를 수집해 주세요.")
