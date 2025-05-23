import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import plotly.express as px
import plotly.graph_objects as go
from cachetools import TTLCache
import logging
from typing import Dict, List, Optional, Tuple
import json
import io
from pytz import timezone  # 추가

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 캐시 설정 (1시간 TTL)
cache = TTLCache(maxsize=100, ttl=3600)

# 환경변수 로드
load_dotenv()
AUTH_KEY = os.getenv("AUTH_KEY") or st.secrets.get("AUTH_KEY", "")

# 페이지 설정
st.set_page_config(
    page_title="HRD아카이브 대시보드",
    page_icon="📊",
    layout="wide",  # 화면 가로 사이즈를 넓게 설정
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    @font-face {
        font-family: 'NanumBarunGothic';
        src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2104@1.1/NanumBarunGothic.woff') format('woff');
        font-weight: normal;
        font-style: normal;
    }
    .stApp {
        background-color: #f8f9fa;
        font-family: 'NanumBarunGothic', sans-serif;
        font-size: 11px;
        max-width: 70%; /* 이전 버전으로 복원 */
        margin: 0 auto; /* 중앙 정렬 */
        padding-top: 2rem; /* 상단 여백 유지 */
    }
    .main-title {
        font-size: 1.0rem;
        font-weight: 600;
        color: #222;
        margin-bottom: 0.5rem;
        padding-bottom: 0.1rem;
        border-bottom: 1px solid #bbb;
        font-family: 'NanumBarunGothic', sans-serif;
    }
    .section-title {
        font-size: 0.85rem;
        font-weight: 500;
        color: #444;
        margin-bottom: 0.3rem;
        font-family: 'NanumBarunGothic', sans-serif;
    }
    .stButton > button {
        background-color: #888;
        color: white;
        border: none;
        padding: 0.3rem 0.5rem;
        border-radius: 4px;
        font-weight: 500;
        font-size: 1.1rem;
        min-height: 2.2rem;
        width: 100% !important;
        font-family: 'NanumBarunGothic', sans-serif;
    }
    .stButton > button:hover {
        background-color: #555;
    }
    .dataframe th {
        background-color: #bbb !important;
        color: #222 !important;
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        font-family: 'NanumBarunGothic', sans-serif !important;
    }
    .dataframe td {
        padding: 0.35rem !important; /* 내부 여백 5픽셀 추가 */
        font-size: 0.78rem !important;
        font-family: 'NanumBarunGothic', sans-serif !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.0rem !important;
        font-family: 'NanumBarunGothic', sans-serif !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        font-family: 'NanumBarunGothic', sans-serif !important;
    }
    .footer {
        text-align: center;
        padding: 0.5rem 0 0.2rem 0;
        margin-top: 0.7rem;
        border-top: 1px solid #bbb;
        color: #888;
        font-size: 0.7rem;
        font-family: 'NanumBarunGothic', sans-serif;
    }
    .graybox-text {
        font-size: 11pt !important;
        font-family: 'NanumBarunGothic', sans-serif !important;
        font-weight: 600;
        color: #222;
        text-align: center;
        padding: 0.3rem 0 0.3rem 0.2rem;
        background: #f2f2f2;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

def validate_date_range(start_date: datetime.date, end_date: datetime.date) -> Tuple[bool, str]:
    """날짜 범위의 유효성을 검사합니다."""
    if start_date > end_date:
        return False, "시작일은 종료일보다 이후일 수 없습니다."
    if (end_date - start_date).days > 365:
        return False, "조회 기간은 최대 1년을 초과할 수 없습니다."
    return True, ""

def fetch_training_data(params: Dict[str, str]) -> List[Dict]:
    """훈련 데이터를 가져옵니다."""
    cache_key = json.dumps(params, sort_keys=True)
    if cache_key in cache:
        return cache[cache_key]
    
    results = []
    BASE_URL = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo311L01.do"
    
    try:
        for page in range(1, 1000):
            params["pageNum"] = str(page)
            # HRD 아카이브 코드 강제 설정
            params["crseTracseSe"] = "C0041H"
            
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            srch_list = root.find("srchList")
            if srch_list is None:
                break
                
            rows = srch_list.findall("scn_list")
            if not rows:
                break
                
            for row in rows:
                try:
                    # 훈련유형 코드 확인
                    course_type = row.findtext("crseTracseSe", "").strip()
                    if course_type != "C0041H":
                        continue
                        
                    result = {
                        "훈련기관": row.findtext("subTitle", "").strip(),
                        "훈련과정명": row.findtext("title", "").strip(),
                        "회차": row.findtext("trprDegr", "").strip(),
                        "개강일": row.findtext("traStartDate", "").strip(),
                        "신청인원": int(row.findtext("regCourseMan", "0")),
                        "교육비": int(row.findtext("realMan", "0")),
                    }
                    result["교육비합계"] = result["신청인원"] * result["교육비"]
                    results.append(result)
                except (ValueError, TypeError) as e:
                    logger.warning(f"데이터 변환 중 오류 발생: {e}")
                    continue
                    
    except requests.RequestException as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
        return []
    
    cache[cache_key] = results
    return results

def format_krw_uk(value):
    """숫자를 억원 단위(소수점 1자리)로 변환해주는 함수"""
    return f"{value/1e8:.1f}억"

def format_comma(value):
    """천단위 쉼표로 변환"""
    return f"{value:,}"

def create_summary_metrics(df: pd.DataFrame) -> None:
    """요약 지표를 생성합니다."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 훈련과정 수", f"{df['훈련과정명'].nunique():,}개")
    with col2:
        st.metric("총 회차 개수", f"{len(df):,}회차")
    with col3:
        st.metric("총 신청인원", f"{df['신청인원'].sum():,}명")
    with col4:
        st.metric("총 교육비 합계", format_krw_uk(df['교육비합계'].sum()))

def create_visualizations(df: pd.DataFrame) -> None:
    """데이터 시각화를 생성합니다."""
    st.markdown("### 📊 HRD아카이브 데이터 시각화")
    # 밝은 회색~진한 회색 그라데이션
    gray_palette = [
        '#eeeeee', '#dddddd', '#cccccc', '#bbbbbb', '#aaaaaa',
        '#999999', '#888888', '#777777', '#666666', '#555555',
        '#eeeeee', '#dddddd', '#cccccc', '#bbbbbb', '#aaaaaa',
        '#999999', '#888888', '#777777', '#666666', '#555555'
    ]
    highlight_color = '#FF6F61'  # 알파코 강조 색상

    # 1. 훈련기관별 신청인원 분포 (최대 20개)
    top_institutes = df.groupby("훈련기관")["신청인원"].sum().sort_values(ascending=False).head(20)
    institutes = top_institutes.index.tolist()
    values = top_institutes.values.tolist()
    colors = [highlight_color if '알파코' in name else gray_palette[i % len(gray_palette)] for i, name in enumerate(institutes)]
    fig1 = go.Figure(data=[
        go.Bar(
            x=institutes,
            y=values,
            marker_color=colors,
            text=[format_comma(v) for v in values],
            textposition='outside',
        )
    ])
    fig1.update_layout(
        title="상위 20개 훈련기관 신청인원",
        font=dict(size=16),  # 폰트 크기 증가
        title_font=dict(size=18),
        plot_bgcolor='#fafafa',
        paper_bgcolor='#fafafa',
        yaxis_title="신청인원",
        xaxis_title="훈련기관",
        margin=dict(t=80, b=60),  # 마진 조정
        height=500,  # 그래프 높이 증가
        yaxis_tickformat=",d",
        uniformtext_minsize=10,
        uniformtext_mode='hide'
    )
    st.plotly_chart(fig1, use_container_width=True)

    # 2. 훈련기관별 교육비 합계 분포 (최대 20개)
    top_institutes_fee = df.groupby("훈련기관")["교육비합계"].sum().sort_values(ascending=False).head(20)
    institutes_fee = top_institutes_fee.index.tolist()
    values_fee = top_institutes_fee.values.tolist()
    colors_fee = [highlight_color if '알파코' in name else gray_palette[i % len(gray_palette)] for i, name in enumerate(institutes_fee)]
    fig2 = go.Figure(data=[
        go.Bar(
            x=institutes_fee,
            y=[v/1e8 for v in values_fee],
            marker_color=colors_fee,
            text=[format_krw_uk(v) for v in values_fee],
            textposition='outside',
        )
    ])
    fig2.update_layout(
        title="상위 20개 훈련기관 교육비 합계",
        font=dict(size=16),  # 폰트 크기 증가
        title_font=dict(size=18),
        plot_bgcolor='#fafafa',
        paper_bgcolor='#fafafa',
        yaxis_title="교육비 합계(억원)",
        xaxis_title="훈련기관",
        margin=dict(t=600, b=240, l=180, r=180),  # 내부 여백을 3배로 증가
        height=500,  # 그래프 높이 증가
        yaxis_tickformat=".1f",
        uniformtext_minsize=10,
        uniformtext_mode='hide'
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 3. 월별 신청인원 추이만 남김
    df["개강월"] = pd.to_datetime(df["개강일"]).dt.strftime("%Y-%m")
    monthly_data = df.groupby("개강월")["신청인원"].sum().reset_index()
    fig3 = px.line(
        monthly_data,
        x="개강월",
        y="신청인원",
        title="월별 신청인원 추이",
        labels={"신청인원": "신청인원", "개강월": "개강월"},
        markers=True
    )
    fig3.update_traces(line_color='#888888')
    fig3.update_layout(
        font=dict(size=16),  # 폰트 크기 증가
        title_font=dict(size=18),
        plot_bgcolor='#fafafa',
        paper_bgcolor='#fafafa',
        yaxis_tickformat=",d",
        height=500  # 그래프 높이 증가
    )
    st.plotly_chart(fig3, use_container_width=True)

def main():
    st.markdown('<h1 class="main-title">📊 HRD아카이브 대시보드</h1>', unsafe_allow_html=True)

    # 상단에 조건 설정 영역 배치 (상하 구조)
    st.markdown('<div class="section-title">⚙️ 조건 설정</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        st.markdown('**훈련유형**')
        st.markdown('<div class="graybox-text">HRD아카이브</div>', unsafe_allow_html=True)
        course_type = "C0041H"  # HRD 아카이브 코드
    with col2:
        st.markdown('**개강일 범위 (시작)**')
        start_date = st.date_input(
            label="개강일 범위 (시작)",
            value=datetime(2025, 3, 1).date(),
            key='start_date_input',
            label_visibility='collapsed'
        )
    with col3:
        st.markdown('**개강일 범위 (종료)**')
        # 한국 시간(KST) 기준으로 현재 날짜를 가져오기
        kst = timezone('Asia/Seoul')
        today_kst = datetime.now(kst).date()

        # 개강일 범위 (종료) 설정
        end_date = st.date_input(
            label="개강일 범위 (종료)",
            value=today_kst,  # 한국 시간 기준으로 현재 날짜 설정
            key='end_date_input',
            label_visibility='collapsed'
        )

    # 데이터 자동 수집 및 표시
    params = {
        "authKey": AUTH_KEY,
        "returnType": "XML",
        "outType": "1",
        "pageSize": "100",
        "srchTraStDt": start_date.strftime("%Y%m%d"),
        "srchTraEndDt": end_date.strftime("%Y%m%d"),
        "crseTracseSe": course_type,  # HRD 아카이브 코드 사용
        "sort": "ASC",
        "sortCol": "TRNG_BGDE",
    }
    is_valid, error_message = validate_date_range(start_date, end_date)
    if not is_valid:
        st.error(error_message)
        return

    with st.spinner("데이터를 수집하는 중..."):
        results = fetch_training_data(params)
        if results:
            df = pd.DataFrame(results)
            st.markdown("### 📈 요약 지표")
            create_summary_metrics(df)
            create_visualizations(df)
            st.markdown("### 📋 상세 데이터")
            st.dataframe(
                df.style.format({
                    "신청인원": "{:,}",
                    "교육비": "{:,}",
                    "교육비합계": "{:,}"
                }),
                use_container_width=True
            )
            st.markdown("### 💾 데이터 내보내기")
            col1, col2 = st.columns(2)
            with col1:
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "CSV 다운로드",
                    csv,
                    "training_data.csv",
                    "text/csv",
                    key='download-csv'
                )
            with col2:
                with io.BytesIO() as buffer:
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    st.download_button(
                        "Excel 다운로드",
                        buffer.getvalue(),
                        "training_data.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key='download-excel'
                    )
        else:
            st.warning("조건에 맞는 데이터가 없습니다.")

    # 푸터
    st.markdown("""
    <div class="footer">
        <div class="footer-desc">
            본 대시보드는 고용24 API를 활용하여 사업주훈련 과정의 데이터를 분석하고 시각화합니다.<br>
            데이터 출처: 고용24 (www.work24.go.kr)
        </div>
        <p>© 2025 알파코. All rights reserved.<br>
        Last updated: 2025.05</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()