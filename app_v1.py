import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import datetime
import io
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. 환경변수 로드
load_dotenv()
AUTH_KEY = os.getenv("AUTH_KEY") or st.secrets["AUTH_KEY"]
if not AUTH_KEY:
    st.error("❗ API 키가 설정되어 있지 않습니다. Streamlit Cloud의 Secrets 설정을 확인해주세요.")
    st.stop()

# 2. 전역 CSS
css = """
<style>
  @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
  html, body, [class*="css"] { 
    font-family: 'Pretendard', sans-serif; 
    font-size: 15px;
    color: #334155;
    background-color: #f8fafc;
  }

  /* 메인 타이틀 */
  .title {
    font-size: 28px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 2rem;
    padding-bottom: 0.75rem;
    border-bottom: 2px solid #e2e8f0;
    letter-spacing: -0.5px;
  }

  /* 카드 스타일 */
  .card {
    background: #ffffff;
    border: none;
    border-radius: 20px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.04);
    padding: 2rem;
    margin-bottom: 2rem;
    transition: all 0.3s ease;
  }
  .card:hover {
    box-shadow: 0 8px 32px rgba(0,0,0,0.06);
    transform: translateY(-2px);
  }

  /* 섹션 타이틀 */
  .section-title {
    font-size: 20px;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 1.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e2e8f0;
    letter-spacing: -0.3px;
  }

  /* 버튼 스타일 */
  .stButton > button {
    background-color: #3b82f6;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
    font-weight: 500;
    transition: all 0.3s ease;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(59,130,246,0.1);
  }
  .stButton > button:hover {
    background-color: #2563eb;
    box-shadow: 0 6px 16px rgba(59,130,246,0.2);
    transform: translateY(-1px);
  }

  /* 라디오 버튼 스타일 */
  .stRadio > div {
    margin-top: 1rem;
    margin-bottom: 1.5rem;
  }
  .stRadio > div[role="radiogroup"] > label {
    padding: 0.75rem 1.25rem;
    border-radius: 10px;
    transition: all 0.2s ease;
    color: #475569;
  }
  .stRadio > div[role="radiogroup"] > label:hover {
    background-color: #f1f5f9;
    color: #0f172a;
  }

  /* 테이블 스타일 */
  .card table {
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    margin: 1rem 0;
  }
  .card table th {
    background-color: #f8fafc !important;
    color: #0f172a !important;
    font-weight: 600 !important;
    padding: 1rem 1.5rem !important;
    text-align: center !important;
    border-bottom: 2px solid #e2e8f0 !important;
    font-size: 0.95rem;
  }
  .card table td {
    padding: 1rem 1.5rem !important;
    border-bottom: 1px solid #e2e8f0 !important;
    color: #475569;
    font-size: 0.95rem;
  }
  .card table tr:hover td {
    background-color: #f8fafc !important;
    color: #0f172a;
  }

  /* 셀 정렬 */
  .card table td:nth-child(1),  /* No */
  .card table td:nth-child(3) {  /* 회차 */
    text-align: center !important;
  }
  .card table td:nth-child(2) {  /* 훈련기관 */
    text-align: left !important;
  }
  .card table td:nth-child(4),  /* 신청인원 */
  .card table td:nth-child(5) {  /* 교육비합계 */
    text-align: right !important;
    font-weight: 500;
  }

  /* 에러 메시지 */
  .error-message {
    color: #dc2626;
    font-weight: 500;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    background-color: #fef2f2;
    margin: 1rem 0;
    border: 1px solid #fee2e2;
    font-size: 0.95rem;
  }

  /* Streamlit DataFrame 스타일 */
  div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.04);
  }
  div[data-testid="stDataFrame"] th {
    background-color: #f8fafc !important;
    color: #0f172a !important;
    font-weight: 600 !important;
    text-align: center !important;
    padding: 1rem 1.5rem !important;
    font-size: 0.95rem;
  }
  div[data-testid="stDataFrame"] td {
    padding: 1rem 1.5rem !important;
    color: #475569;
    font-size: 0.95rem;
  }

  /* 다운로드 버튼 */
  .stDownloadButton > button {
    background-color: #10b981;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
    font-weight: 500;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(16,185,129,0.1);
  }
  .stDownloadButton > button:hover {
    background-color: #059669;
    box-shadow: 0 6px 16px rgba(16,185,129,0.2);
    transform: translateY(-1px);
  }

  /* 로딩 스피너 */
  .stSpinner > div {
    border-color: #3b82f6;
  }

  /* 선택 상자 스타일 */
  .stSelectbox > div > div {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    padding: 0.5rem;
  }
  .stSelectbox > div > div:hover {
    border-color: #3b82f6;
  }

  /* 날짜 선택 스타일 */
  .stDateInput > div > div {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    padding: 0.5rem;
  }
  .stDateInput > div > div:hover {
    border-color: #3b82f6;
  }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

def validate_date_range(start_date: datetime.date, end_date: datetime.date) -> bool:
    """날짜 범위의 유효성을 검사합니다."""
    if start_date > end_date:
        st.error("시작일은 종료일보다 이후일 수 없습니다.")
        return False
    if (end_date - start_date).days > 365:
        st.error("조회 기간은 최대 1년을 초과할 수 없습니다.")
        return False
    return True

def parse_xml_response(content: bytes) -> Optional[ET.Element]:
    """XML 응답을 파싱하고 유효성을 검사합니다."""
    try:
        root = ET.fromstring(content)
        if root.find("srchList") is None:
            st.error("API 응답 형식이 올바르지 않습니다.")
            return None
        return root
    except ET.ParseError:
        st.error("API 응답을 파싱하는 중 오류가 발생했습니다.")
        return None

def fetch_training_data(params: Dict[str, str]) -> List[Dict]:
    """훈련 데이터를 가져옵니다."""
    results = []
    BASE_URL = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo311L01.do"
    
    try:
        for page in range(1, 1000):
            params["pageNum"] = str(page)
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            root = parse_xml_response(response.content)
            if root is None:
                break
                
            srch_list = root.find("srchList")
            rows = srch_list.findall("scn_list") if srch_list is not None else []
            
            if not rows:
                break
                
            for row in rows:
                try:
                    result = {
                        "훈련기관": row.findtext("subTitle", "").strip(),
                        "훈련과정명": row.findtext("title", "").strip(),
                        "회차": row.findtext("trprDegr", "").strip(),
                        "개강일": row.findtext("traStartDate", "").strip(),
                        "신청인원": int(row.findtext("regCourseMan", "0")),
                        "교육비": int(row.findtext("realMan", "0")),
                    }
                    if all(result.values()):  # 모든 필드가 비어있지 않은 경우만 추가
                        results.append(result)
                except (ValueError, TypeError) as e:
                    logger.warning(f"데이터 변환 중 오류 발생: {e}")
                    continue
                    
    except requests.RequestException as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
        return []
        
    return results

# 3. 페이지 제목
st.markdown("<div class='title'>사업주훈련(고용24) 분석 대시보드</div>", unsafe_allow_html=True)

# 4. 파라미터 설정 카드
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>파라미터 설정</div>", unsafe_allow_html=True)

# 훈련유형 선택
crse_type = st.selectbox(
    "훈련유형 선택",
    [
        ("전체", ""),
        ("일반직무훈련", "C0041T"),
        ("기업직업훈련카드", "C0041B"),
        ("고숙련신기술훈련", "C0041N"),
        ("패키지구독형 원격", "C0041H"),
    ],
    format_func=lambda x: x[0],
)[1]

# 개강일자 범위 입력
today = datetime.date.today()
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("개강일 범위 (시작)", value=today)
with col2:
    end_date = st.date_input("개강일 범위 (종료)", value=today + datetime.timedelta(days=30))

# 데이터 수집 버튼
if st.button("데이터 수집 시작"):
    if not validate_date_range(start_date, end_date):
        st.stop()
        
    params = {
        "authKey": AUTH_KEY,
        "returnType": "XML",
        "outType": "1",
        "pageSize": "100",
        "srchTraStDt": start_date.strftime("%Y%m%d"),
        "srchTraEndDt": end_date.strftime("%Y%m%d"),
        "crseTracseSe": crse_type,
        "sort": "ASC",
        "sortCol": "TRNG_BGDE",
    }
    
    with st.spinner("🔄 데이터를 수집 중입니다..."):
        results = fetch_training_data(params)
        
        if results:
            df = pd.DataFrame(results)
            df["교육비합계"] = df["신청인원"] * df["교육비"]
            
            # 메모리 최적화를 위해 데이터 타입 조정
            df = df.astype({
                "신청인원": "int32",
                "교육비": "int32",
                "교육비합계": "int32"
            })
            
            grouped = (
                df.groupby("훈련기관")
                .agg(
                    회차=("회차", "count"),
                    신청인원=("신청인원", "sum"),
                    교육비합계=("교육비합계", "sum"),
                )
                .reset_index()
            )
            
            st.session_state.df_raw = df
            st.session_state.df_grouped = grouped
        else:
            st.error("❌ 조건에 맞는 데이터가 없습니다.")

# 파라미터 카드 닫기
st.markdown("</div>", unsafe_allow_html=True)

# 5. 데이터 분석 결과 카드
if "df_grouped" in st.session_state:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>데이터 분석 결과</div>", unsafe_allow_html=True)

    sort_option = st.radio(
        "정렬 기준",
        ["교육비 합계", "신청인원", "훈련기관명"],
        index=0,
        horizontal=True,
        key="sort_main",
    )
    
    df_grp = st.session_state.df_grouped.copy()
    if sort_option == "교육비 합계":
        df_grp = df_grp.sort_values("교육비합계", ascending=False)
    elif sort_option == "신청인원":
        df_grp = df_grp.sort_values("신청인원", ascending=False)
    else:
        df_grp = df_grp.sort_values("훈련기관")

    df_grp = df_grp.reset_index(drop=True)
    df_grp.insert(0, "No", range(1, len(df_grp) + 1))

    st.dataframe(
        df_grp.style.format({
            "신청인원": "{:,}",
            "교육비합계": "{:,}"
        }).set_properties(**{
            "No": "text-align: center; vertical-align: middle;",
            "훈련기관": "text-align: left; vertical-align: middle;",
            "회차": "text-align: center; vertical-align: middle;",
            "신청인원": "text-align: right; vertical-align: middle;",
            "교육비합계": "text-align: right; vertical-align: middle;"
        }).set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center'), ('vertical-align', 'middle')]},
            {'selector': 'th div', 'props': [('text-align', 'center'), ('vertical-align', 'middle')]},
            {'selector': 'th div div', 'props': [('text-align', 'center'), ('vertical-align', 'middle')]}
        ]),
        use_container_width=True,
        hide_index=True
    )

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        st.session_state.df_raw.to_excel(writer, index=False, sheet_name='상세데이터')
        df_grp.to_excel(writer, index=False, sheet_name='기관별집계')
    buf.seek(0)
    
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "엑셀 파일 다운로드",
        data=buf,
        file_name=f"훈련과정_회차_목록_{ts}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("</div>", unsafe_allow_html=True)