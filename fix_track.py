import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. 페이지 설정 및 한글 폰트 설정
# ==========================================
st.set_page_config(
    page_title="FixTrack - 고장관리 시스템",
    page_icon="🛠️",
    layout="wide"
)

# Matplotlib 한글 폰트 설정 (Windows / Mac)
plt.rcParams['font.family'] = 'Malgun Gothic' if os.name == 'nt' else 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

EXCEL_FILE = 'fixtrack.xlsx'

# 컬럼 정의 (fixtrack.xlsx 참고)
COLUMNS = ['공장', 'BAY(장소)', '고장내용', '발생일', '접수자', '접수자연락처', '수리내용', '수리일', '수리담당자']

# ==========================================
# 2. 데이터 로드 / 저장 함수
# ==========================================
def load_data():
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE)
            # 날짜 형식을 datetime으로 변환
            df['발생일'] = pd.to_datetime(df['발생일']).dt.date
            df['수리일'] = pd.to_datetime(df['수리일']).dt.date
            return df
        except Exception as e:
            st.error(f"엑셀 파일 읽기 오류: {e}")
            return pd.DataFrame(columns=COLUMNS)
    else:
        # 파일이 없을 경우 기본 컬럼으로 빈 데이터프레임 생성
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

# ==========================================
# 3. 텔레그램 메세지 전송 함수
# ==========================================
def send_telegram_message(token, chat_id, text):
    if not token or not chat_id:
        return False, "텔레그램 봇 토큰과 Chat ID를 입력해주세요."
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            return True, "메시지 전송 성공!"
        else:
            return False, f"전송 실패 (코드: {res.status_code}): {res.text}"
    except Exception as e:
        return False, f"오류 발생: {e}"

# ==========================================
# 4. 앱 헤더 및 사이드바 (텔레그램 설정)
# ==========================================
st.title("🛠️ FixTrack - 설비 고장 관리 앱")

# 데이터 불러오기
df = load_data()

# 사이드바 설정 (텔레그램 연동)
st.sidebar.header("⚙️ 텔레그램 알림 설정")
telegram_token = st.sidebar.text_input("Bot Token", type="password", help="BotFather에게 받은 토큰")
telegram_chat_id = st.sidebar.text_input("Chat ID", help="알림을 받을 채팅방 ID")

st.sidebar.markdown("---")
st.sidebar.info("💡 **FixTrack 사용 안내**\n- 엑셀 파일 데이터 실시간 반영\n- 고장 접수/수리등록/통계 시각화 제공")

# ==========================================
# 5. 탭 구성
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📋 고장 현황 및 관리", "➕ 신규 고장 접수", "🔧 수리 완료 등록", "📊 통계 및 그래프"])

# ------------------------------------------
# TAB 1: 고장 현황 및 조회 / 엑셀 다운로드
# ------------------------------------------
with tab1:
    st.subheader("📋 전체 고장/수리 이력 현황")
    
    # 필터링 옵션
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        factory_filter = st.multiselect("공장 필터", options=df['공장'].unique() if not df.empty else [], default=[])
    with col_f2:
        status_filter = st.radio("수리 상태 필터", ["전체", "수리 대기 중", "수리 완료"], horizontal=True)
    
    filtered_df = df.copy()
    
    if factory_filter:
        filtered_df = filtered_df[filtered_df['공장'].isin(factory_filter)]
    
    if status_filter == "수리 대기 중":
        filtered_df = filtered_df[filtered_df['수리내용'].isna() | (filtered_df['수리내용'] == '')]
    elif status_filter == "수리 완료":
        filtered_df = filtered_df[filtered_df['수리내용'].notna() & (filtered_df['수리내용'] != '')]

    # 데이터 표 출력
    st.dataframe(filtered_df, use_container_width=True)
    
    # 엑셀 다운로드 기능
    st.markdown("### 📥 데이터 다운로드")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    
    st.download_button(
        label="📄 현재 조회 목록 엑셀 다운로드",
        data=processed_data,
        file_name=f"fixtrack_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ------------------------------------------
# TAB 2: 신규 고장 접수
# ------------------------------------------
with tab2:
    st.subheader("➕ 신규 고장 접수 등록")
    
    with st.form("new_fix_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            factory = st.text_input("공장", value="1공장", help="예: 2공장, 3공장")
            bay = st.text_input("BAY(장소)", value="1베이", help="예: 4베이, 1베이")
            occurrence_date = st.date_input("발생일", value=datetime.today())
        with c2:
            reporter = st.text_input("접수자", value="")
            reporter_contact = st.text_input("접수자 연락처", value="010-")
        
        breakdown_desc = st.text_area("고장내용", placeholder="예: 크레인 흘러내림, 에틸렌 누기 등")
        
        send_alarm = st.checkbox("접수 완료 시 텔레그램으로 즉시 알림 전송", value=True)
        submit_btn = st.form_submit_button("🚨 고장 접수 등록")
        
        if submit_btn:
            if not factory or not breakdown_desc or not reporter:
                st.warning("공장, 고장내용, 접수자는 필수 입력 사항입니다.")
            else:
                new_row = {
                    '공장': factory,
                    'BAY(장소)': bay,
                    '고장내용': breakdown_desc,
                    '발생일': occurrence_date,
                    '접수자': reporter,
                    '접수자연락처': reporter_contact,
                    '수리내용': None,
                    '수리일': None,
                    '수리담당자': None
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                st.success("새로운 고장 건이 정상적으로 접수되었습니다!")
                
                # 텔레그램 전송
                if send_alarm:
                    msg = (
                        f"🚨 <b>[신규 고장 접수]</b>\n\n"
                        f"• <b>위치:</b> {factory} {bay}\n"
                        f"• <b>발생일:</b> {occurrence_date}\n"
                        f"• <b>고장내용:</b> {breakdown_desc}\n"
                        f"• <b>접수자:</b> {reporter} ({reporter_contact})"
                    )
                    ok, res_msg = send_telegram_message(telegram_token, telegram_chat_id, msg)
                    if ok:
                        st.info("📱 텔레그램 알림이 전송되었습니다.")
                    else:
                        st.error(f"📱 텔레그램 전송 실패: {res_msg}")
                
                st.rerun()

# ------------------------------------------
# TAB 3: 수리 완료 등록
# ------------------------------------------
with tab3:
    st.subheader("🔧 미완료 건 수리 처리")
    
    # 수리 미완료 건만 필터링
    unrepaired_df = df[df['수리내용'].isna() | (df['수리내용'] == '')]
    
    if unrepaired_df.empty:
        st.success("현재 수리 대기 중인 고장 건이 없습니다! 🎉")
    else:
        st.write(f"현재 **{len(unrepaired_df)}**건의 수리 대기 건이 있습니다.")
        
        # 선택 목록 만들기
        options = [f"[{idx}] {row['공장']} {row['BAY(장소)']} - {row['고장내용']} ({row['발생일']})" for idx, row in unrepaired_df.iterrows()]
        selected_option = st.selectbox("수리 처리할 고장 항목 선택", options)
        
        if selected_option:
            selected_idx = int(selected_option.split(']')[0].replace('[', ''))
            target_row = df.loc[selected_idx]
            
            st.info(f"선택 항목: **{target_row['공장']} {target_row['BAY(장소)']}** / 접수자: {target_row['접수자']}")
            
            with st.form("repair_form"):
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    repair_date = st.date_input("수리일", value=datetime.today())
                with col_r2:
                    repair_person = st.text_input("수리담당자", value="")
                
                repair_desc = st.text_area("수리내용", placeholder="예: 니뿔 교체, 부품 세척 완료 등")
                
                send_repair_alarm = st.checkbox("수리 완료 시 텔레그램으로 알림 전송", value=True)
                repair_btn = st.form_submit_button("✅ 수리 완료 등록")
                
                if repair_btn:
                    if not repair_desc or not repair_person:
                        st.warning("수리내용과 수리담당자를 입력해주세요.")
                    else:
                        df.at[selected_idx, '수리내용'] = repair_desc
                        df.at[selected_idx, '수리일'] = repair_date
                        df.at[selected_idx, '수리담당자'] = repair_person
                        save_data(df)
                        st.success("수리 처리가 완료되었습니다!")
                        
                        if send_repair_alarm:
                            msg = (
                                f"✅ <b>[수리 완료 알림]</b>\n\n"
                                f"• <b>위치:</b> {target_row['공장']} {target_row['BAY(장소)']}\n"
                                f"• <b>고장내용:</b> {target_row['고장내용']}\n"
                                f"• <b>수리내용:</b> {repair_desc}\n"
                                f"• <b>수리일:</b> {repair_date}\n"
                                f"• <b>담당자:</b> {repair_person}"
                            )
                            ok, res_msg = send_telegram_message(telegram_token, telegram_chat_id, msg)
                            if ok:
                                st.info("📱 텔레그램 알림이 전송되었습니다.")
                            else:
                                st.error(f"📱 텔레그램 전송 실패: {res_msg}")
                        
                        st.rerun()

# ------------------------------------------
# TAB 4: 통계 및 그래프 시각화
# ------------------------------------------
with tab4:
    st.subheader("📊 고장 통계 분석")
    
    if df.empty:
        st.info("분석할 데이터가 없습니다.")
    else:
        col_m1, col_m2, col_m3 = st.columns(3)
        total_cnt = len(df)
        completed_cnt = len(df[df['수리내용'].notna() & (df['수리내용'] != '')])
        pending_cnt = total_cnt - completed_cnt
        
        col_m1.metric("총 접수 건수", f"{total_cnt} 건")
        col_m2.metric("수리 완료", f"{completed_cnt} 건")
        col_m3.metric("수리 대기", f"{pending_cnt} 건", delta_color="inverse")
        
        st.markdown("---")
        
        col_g1, col_g2 = st.columns(2)
        
        # 1. 공장별 고장 건수 차트
        with col_g1:
            st.markdown("##### 🏢 공장별 고장 발생 건수")
            fig1, ax1 = plt.subplots(figsize=(6, 4))
            factory_counts = df['공장'].value_counts()
            sns.barplot(x=factory_counts.index, y=factory_counts.values, ax=ax1, palette="Blues_d")
            ax1.set_ylabel("건수")
            ax1.set_xlabel("공장")
            for i, v in enumerate(factory_counts.values):
                ax1.text(i, v + 0.05, str(v), ha='center', fontweight='bold')
            st.pyplot(fig1)
            
        # 2. 수리 진행 상태 비율 차트
        with col_g2:
            st.markdown("##### ⏳ 수리 처리 상태 비율")
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            labels = ['수리 완료', '수리 대기']
            sizes = [completed_cnt, pending_cnt]
            colors = ['#4CAF50', '#FF9800']
            
            if total_cnt > 0:
                ax2.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90, explode=(0.05, 0))
                ax2.axis('equal')
                st.pyplot(fig2)
            else:
                st.write("표시할 데이터가 없습니다.")