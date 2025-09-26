import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from folium import Tooltip
import random

# =========================
# 데이터 로드
# =========================
df = pd.read_csv("data/2024_price.csv")

# 물건금액 범위
min_price_val = float(df["물건금액"].min())
max_price_val = float(df["물건금액"].max())

# =========================
# 고정 옵션 (요청 반영: 순서 정리)
# =========================
building_year_categories = ['2020년대', '2010년대', '2000년대', '1990년대', '1980년대', '1979년 이하']
building_types = ["아파트", "오피스텔", "단독다가구", "연립다세대"]  # ← 순서 변경
area_options = ['10평 미만', '10평대', '20평대', '30평대', '40평대', '50평대', '60평대 이상']  # ← 순서 정리

# 서울 구 중심 좌표
seoul_gu_coords = {
    "종로구": [37.572950, 126.979357], "중구": [37.563757, 126.997730], "용산구": [37.532600, 126.990860],
    "성동구": [37.563680, 127.036580], "광진구": [37.538420, 127.082550], "동대문구": [37.574400, 127.039390],
    "중랑구": [37.606570, 127.092720], "성북구": [37.589910, 127.016900], "강북구": [37.639970, 127.025980],
    "도봉구": [37.668530, 127.047980], "노원구": [37.654290, 127.056950], "은평구": [37.602570, 126.929620],
    "서대문구": [37.579680, 126.936880], "마포구": [37.566680, 126.901450], "양천구": [37.516340, 126.866940],
    "강서구": [37.550940, 126.849530], "구로구": [37.495650, 126.887770], "금천구": [37.456430, 126.895160],
    "영등포구": [37.526640, 126.896210], "동작구": [37.512650, 126.939930], "관악구": [37.478090, 126.951590],
    "서초구": [37.483570, 127.032660], "강남구": [37.517200, 127.047320], "송파구": [37.514560, 127.105570],
    "강동구": [37.530130, 127.123820],
}
gu_options = ["전체"] + list(seoul_gu_coords.keys())

# =========================
# 페이지 설정 & 타이틀
# =========================
st.set_page_config(page_title="서울에서 내 집 마련하기", layout="wide")
st.title("🏠 서울에서 내 집 마련하기")
st.caption("**사이드바를 열고 원하는 조건을 입력하세요.** 예산·연식·면적·최소 층수·구를 선택하면 표와 지도에 바로 반영됩니다.")

# =========================
# 사이드바 필터
# =========================
st.sidebar.header("🔎 필터 조건 선택")
selected_gu = st.sidebar.selectbox("서울의 구 선택", gu_options, index=0)
selected_year_category = st.sidebar.selectbox("건축년도 구분", building_year_categories, index=2)
selected_building_type = st.sidebar.selectbox("건물 종류", building_types)
selected_area = st.sidebar.selectbox("면적 (평)", area_options)

# 층수: '이하' → '최소 N층 이상'으로 변경
min_floor = st.sidebar.number_input("최소 층수 (이상)", value=0, step=1, format="%d")  # 지하 원하면 음수도 입력 가능

# 예산: 슬라이더 → 최소/최대 입력
min_budget = st.sidebar.number_input("최소 예산 (억)", value=0.0, min_value=0.0, step=0.1, format="%.1f")
max_budget = st.sidebar.number_input("최대 예산 (억)", value=max_price_val, min_value=0.0, step=0.1, format="%.1f")
if max_budget < min_budget:
    st.sidebar.warning("최대 예산이 최소 예산보다 작습니다. 값을 다시 확인하세요.")
    min_budget, max_budget = max_budget, min_budget  # swap

# =========================
# 데이터 필터링
# =========================
filtered_df = df[
    (df["건축년도구분"] == selected_year_category) &
    (df["건물용도"] == selected_building_type) &
    (df["건물면적구분"] == selected_area) &
    (df["층"].fillna(0) >= min_floor) &
    (df["물건금액"].between(min_budget, max_budget))
]
if selected_gu != "전체":
    filtered_df = filtered_df[filtered_df["자치구명"] == selected_gu]

# =========================
# 포맷터: 평수 표시(소수1자리 반올림)
# =========================
def fmt_area(v):
    try:
        x = round(float(v), 1)   # 소수 첫째자리 반올림
        return f"{x:g}"          # 12.0 -> "12"
    except Exception:
        return "-"

# =========================
# 지도 만들기
# =========================
default_center = [37.5665, 126.9780]
map_center = seoul_gu_coords.get(selected_gu, default_center)
m = folium.Map(location=map_center, zoom_start=13 if selected_gu != "전체" else 11)

# ‘전체’면 각 구에 파란 핀, 특정 구면 그 구에 파란 핀
if selected_gu == "전체":
    for gu, coords in seoul_gu_coords.items():
        folium.Marker(location=coords, popup=gu, tooltip=gu,
                      icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)
else:
    folium.Marker(location=map_center, popup=selected_gu, tooltip=selected_gu,
                  icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)

# 스파이럴(달팽이) 방지: 건수가 적으면 클러스터 미사용, 많으면 클러스터 + spiderfy 끔
def add_marker(mapobj, lat, lon, popup_html, tooltip_text):
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=320),
        tooltip=Tooltip(tooltip_text, sticky=True),
        icon=folium.Icon(color='red', icon='home')
    ).add_to(mapobj)

def jittered_coord(gu_name: str, seed: int):
    base = seoul_gu_coords.get(gu_name, default_center)
    random.seed(seed * 7919)
    return [base[0] + (random.random()-0.5)*0.004,
            base[1] + (random.random()-0.5)*0.004]

if not filtered_df.empty:
    rows = filtered_df.reset_index(drop=True)
    if len(rows) <= 200:
        for i, row in rows.iterrows():
            lat, lon = jittered_coord(str(row.get("자치구명","")), i)
            name = str(row.get("건물명","매물"))
            popup_html = f"""
            <b>{name}</b><br>
            🗺 {row.get('자치구명','')}, {row.get('법정동명','')}<br>
            🏢 {row.get('건물용도','')} / {row.get('건물면적구분','')} ({fmt_area(row.get('건물면적',''))}평)<br>
            📅 {row.get('건축년도','-')} ({row.get('건축년도구분','')})<br>
            ⬆ 층: {row.get('층','-')}<br>
            💰 가격: {row.get('물건금액','-')} 억
            """
            add_marker(m, lat, lon, popup_html, name)
    else:
        cluster = MarkerCluster(options={
            "disableClusteringAtZoom": 15,
            "spiderfyOnMaxZoom": False,
            "showCoverageOnHover": False
        }).add_to(m)
        for i, row in rows.iterrows():
            lat, lon = jittered_coord(str(row.get("자치구명","")), i)
            name = str(row.get("건물명","매물"))
            popup_html = f"""
            <b>{name}</b><br>
            🗺 {row.get('자치구명','')}, {row.get('법정동명','')}<br>
            🏢 {row.get('건물용도','')} / {row.get('건물면적구분','')} ({fmt_area(row.get('건물면적',''))}평)<br>
            📅 {row.get('건축년도','-')} ({row.get('건축년도구분','')})<br>
            ⬆ 층: {row.get('층','-')}<br>
            💰 가격: {row.get('물건금액','-')} 억
            """
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=Tooltip(name, sticky=True),
                icon=folium.Icon(color='red', icon='home')
            ).add_to(cluster)

# =========================
# 레이아웃
# =========================
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("📌 선택한 조건의 매물 지도")
    st_folium(m, width=700, height=600)

with col2:
    st.subheader("🎯 현재 선택된 필터")
    st.markdown(f"""
    - **건축년도 구분**: {selected_year_category}  
    - **건물 종류**: {selected_building_type}  
    - **면적**: {selected_area}  
    - **최소 층수(이상)**: {int(min_floor)}층  
    - **예산 범위**: {min_budget:.1f}억 ~ {max_budget:.1f}억  
    - **선택한 구**: {selected_gu}
    """)
    st.write(f"🔎 매물 수: {len(filtered_df)}건")

with st.expander("🏠 조건에 맞는 집 목록 보기 (모든 컬럼)"):
    st.dataframe(filtered_df.reset_index(drop=True))
