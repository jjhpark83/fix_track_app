import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests
import io

# ===========================================================================
# 1. 환경 설정, 구글 시트 주소 및 텔레그램 설정
# ===========================================================================
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/15QOe-xrOxKNwckaKiexr9PGnqid6NVPFgJU5wTjhvDA/edit?usp=sharing"
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxgXUROJBacDjLaWBzZaxGpvcuazsqfn9Tgnoeyeh02S8F_M1LpafNp1twIOwtyTNRUGA/exec"

# 📱 [★텔레그램 연동 정보 입력★]
TELEGRAM_BOT_TOKEN = "8845407511:AAHjJ-uVnHxvmtqaNo9KF5Rz3yNIUXC7Czo"
TELEGRAM_CHAT_IDS = ["641951727"]

st.set_page_config(page_title="FixTrack - 고장관리", page_icon="🛠️", layout="wide")
st.title("🛠️ FixTrack - 고장관리 시스템")

# 구글 시트 고유 ID 추출 함수
def get_sheet_id(url):
    try:
        return url.split("/d/")[1].split("/")[0]
    except Exception:
        return None

SHEET_ID = get_sheet_id(GOOGLE_SHEET_URL)
COLUMNS = ['공장', 'BAY(장소)', '고장내용', '발생일', '접수자', '접수자연락처', '수리내용', '수리일', '수리담당자']

# 📲 텔레그램 메시지 발송 함수 (상세 에러 확인용 수정본)
def send_telegram_message(message_text):
    if "여기에_" in TELEGRAM_BOT_TOKEN or not TELEGRAM_BOT_TOKEN:
        st.sidebar.warning("⚠️ 텔레그램 토큰 설정이 되어있지 않아 알림이 전송되지 않았습니다.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN.strip()}/sendMessage"
    success_count = 0

    for raw_id in TELEGRAM_CHAT_IDS:
        # ID 앞뒤 공백 제거 및 문자열 정제
        chat_id = str(raw_id).strip().replace('"', '').replace("'", "")
        
        payload = {
            "chat_id": chat_id,
            "text": message_text
        }
        try:
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                success_count += 1
                st.sidebar.success(f"📱 텔레그램 발송 성공! ({chat_id})")
            else:
                # 🛑 전송 실패 시 텔레그램에서 돌려준 정확한 에러 원인 표시
                st.sidebar.error(f"📱 텔레그램 전송 실패 [{res.status_code}]: {res.text}")
        except Exception as e:
            st.sidebar.error(f"📱 텔레그램 통신 오류: {e}")

    return success_count > 0

# ===========================================================================
# 2. 데이터 로드 및 저장 함수
# ===========================================================================
def load_data_from_sheets():
    fallback_df = pd.DataFrame(columns=COLUMNS)
    if not SHEET_ID or "여기에_본인" in GOOGLE_SHEET_URL:
        st.error("❌ 올바른 구글 시트 URL 주소를 상단에 설정해주세요.")
        return fallback_df
        
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
        live_url = f"{csv_url}&t={int(datetime.now().timestamp())}"
        df = pd.read_csv(live_url)
        
        if df.empty:
            return fallback_df
            
        for col in ['공장', 'BAY(장소)', '고장내용', '접수자', '접수자연락처', '수리내용', '수리담당자']:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
            else:
                df[col] = ""
        
        df['발생일'] = pd.to_datetime(df['발생일'], errors='coerce').dt.date
        df['수리일'] = pd.to_datetime(df['수리일'], errors='coerce').dt.date
        return df[COLUMNS]
    except Exception as e:
        st.error(f"❌ 구글 드라이브 실시간 자료 로드 실패: {e}")
        return fallback_df

def save_data_to_sheets(payload_data):
    try:
        if "여기에_본인" in GOOGLE_WEBAPP_URL or not GOOGLE_WEBAPP_URL:
            return False
        response = requests.post(GOOGLE_WEBAPP_URL, json=payload_data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"🌐 구글 전송 오류: {e}")
        return False

if 'live_data' not in st.session_state:
    st.session_state.live_data = load_data_from_sheets()

df = st.session_state.live_data

# ===========================================================================
# 3. 사이드바: 🆕 신규 고장 접수 및 수리 처리 섹션
# ===========================================================================
st.sidebar.header("🆕 고장 접수 / 수리 등록")

if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None

if st.session_state.edit_index is not None:
    idx = st.session_state.edit_index
    st.sidebar.warning(f"⚠️ 현재 [{idx + 1}번 행] 수리 완료/수정 모드입니다.")
    
    default_factory = str(df.loc[idx, '공장']) if idx < len(df) else ""
    default_bay = str(df.loc[idx, 'BAY(장소)']) if idx < len(df) else ""
    default_desc = str(df.loc[idx, '고장내용']) if idx < len(df) else ""
    default_occ_date = df.loc[idx, '발생일'] if idx < len(df) and pd.notna(df.loc[idx, '발생일']) else datetime.now().date()
    default_reporter = str(df.loc[idx, '접수자']) if idx < len(df) else ""
    default_contact = str(df.loc[idx, '접수자연락처']) if idx < len(df) else ""
    default_repair_desc = str(df.loc[idx, '수리내용']) if idx < len(df) else ""
    default_is_repaired = pd.notna(df.loc[idx, '수리일']) and str(df.loc[idx, '수리일']).strip() != "" if idx < len(df) else False
    default_repair_date = df.loc[idx, '수리일'] if default_is_repaired else datetime.now().date()
    default_repair_person = str(df.loc[idx, '수리담당자']) if idx < len(df) else ""
    
    submit_label = "💾 수리 완료 / 수정 저장"
else:
    default_factory = "1공장"
    default_bay = "1베이"
    default_desc = ""
    default_occ_date = datetime.now().date()
    default_reporter = ""
    default_contact = "010-"
    default_repair_desc = ""
    default_is_repaired = False
    default_repair_date = datetime.now().date()
    default_repair_person = ""
    submit_label = "📝 신규 고장 접수하기"

with st.sidebar.form(key='register_form', clear_on_submit=True):
    input_factory = st.text_input("공장 (예: 2공장)", value=default_factory)
    input_bay = st.text_input("BAY(장소) (예: 4베이)", value=default_bay)
    input_desc = st.text_area("고장내용", value=default_desc)
    input_occ_date = st.date_input("발생일", value=default_occ_date)
    input_reporter = st.text_input("접수자", value=default_reporter)
    input_contact = st.text_input("접수자연락처", value=default_contact)
    
    st.markdown("---")
    is_repaired = st.checkbox("체크 시 수리 완료 처리", value=default_is_repaired)
    input_repair_desc = st.text_area("수리내용", value=default_repair_desc)
    input_repair_date = st.date_input("수리일", value=default_repair_date) if is_repaired else None
    input_repair_person = st.text_input("수리담당자", value=default_repair_person)
    
    submit_btn = st.form_submit_button(label=submit_label)

if st.session_state.edit_index is not None:
    if st.sidebar.button("❌ 선택/수정 취소"):
        st.session_state.edit_index = None
        st.rerun()

if submit_btn:
    if input_factory and input_desc and input_reporter:
        payload = {
            "factory": input_factory.strip(),
            "bay": input_bay.strip(),
            "breakdown_desc": input_desc.strip(),
            "occurrence_date": str(input_occ_date),
            "reporter": input_reporter.strip(),
            "reporter_contact": input_contact.strip(),
            "repair_desc": input_repair_desc.strip() if is_repaired else "",
            "repair_date": str(input_repair_date) if is_repaired else "",
            "repair_person": input_repair_person.strip() if is_repaired else ""
        }
        
        success = save_data_to_sheets(payload)
        
        if success:
            if st.session_state.edit_index is not None:
                df.loc[st.session_state.edit_index] = [
                    input_factory.strip(), input_bay.strip(), input_desc.strip(), input_occ_date,
                    input_reporter.strip(), input_contact.strip(),
                    input_repair_desc.strip() if is_repaired else "", input_repair_date if is_repaired else "", input_repair_person.strip() if is_repaired else ""
                ]
                st.sidebar.success("💾 구글 스프레드시트 수리내용 수정 완료!")
                st.session_state.edit_index = None
            else:
                new_row = pd.DataFrame([[
                    input_factory.strip(), input_bay.strip(), input_desc.strip(), input_occ_date,
                    input_reporter.strip(), input_contact.strip(),
                    input_repair_desc.strip() if is_repaired else "", input_repair_date if is_repaired else "", input_repair_person.strip() if is_repaired else ""
                ]], columns=df.columns)
                df = pd.concat([df, new_row], ignore_index=True)
                st.sidebar.success("🎉 구글 스프레드시트 신규 고장 접수 완료!")
                
                # 📢 [신규 고장 접수 시 텔레그램 알림 발송]
                msg = f"🚨 {input_factory.strip()} 신규접수\n- 장소: {input_bay.strip()}\n- 내용: {input_desc.strip()}\n- 접수자: {input_reporter.strip()}"
                send_telegram_message(msg)
            
            st.session_state.live_data = df
            st.rerun()
        else:
            st.sidebar.error("❌ 구글 웹앱 연결 실패! URL 주소나 배포 버전을 확인하세요.")
    else:
        st.sidebar.error("⚠️ 공장, 고장내용, 접수자는 필수 입력 사항입니다.")

# ===========================================================================
# 4. 메인 화면: 📊 통계 그래프 존
# ===========================================================================
st.subheader("📊 실시간 고장 및 수리 현황 통계")
if not df.empty:
    col1, col2 = st.columns(2)
    unrepaired_df = df[df['수리내용'].isna() | (df['수리내용'] == "")]
    
    with col1:
        if not unrepaired_df.empty:
            factory_counts = unrepaired_df['공장'].value_counts().reset_index()
            factory_counts.columns = ['공장', '미완료 건수']
            fig1 = px.bar(factory_counts, x='공장', y='미완료 건수', title="🔥 공장별 수리 미완료 건수", color='공장')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("현재 수리 대기 중인 고장 건이 없습니다! 🎉")
            
    with col2:
        if not df.empty:
            rep_status = pd.DataFrame({
                '상태': ['수리 완료', '수리 대기'],
                '건수': [len(df) - len(unrepaired_df), len(unrepaired_df)]
            })
            fig2 = px.pie(rep_status, values='건수', names='상태', title="⏳ 수리 처리 진행 비율", hole=0.3, color='상태',
                          color_discrete_map={'수리 완료': '#2ECC71', '수리 대기': '#E74C3C'})
            st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("통계를 표시할 데이터가 없습니다.")

st.markdown("---")

# ===========================================================================
# 5. 메인 화면: 🔍 검색 및 데이터프레임 클릭 연동 존
# ===========================================================================
st.subheader("🔍 고장 이력 검색 및 클릭 수정")

if 'selected_factory' not in st.session_state:
    st.session_state.selected_factory = "전체"

available_factory = sorted(list(df['공장'].dropna().unique())) if not df.empty else []
all_factory_options = ["전체"] + available_factory

search_factory = st.selectbox(
    "🏢 공장 선택 필터", 
    all_factory_options, 
    index=all_factory_options.index(st.session_state.selected_factory) if st.session_state.selected_factory in all_factory_options else 0
)

show_completed = st.checkbox("✅ 수리 완료된 항목도 조회 목록에 포함하기", value=True)

if search_factory != st.session_state.selected_factory:
    st.session_state.selected_factory = search_factory
    st.rerun()

view_df = df.copy()
view_df['원래번호'] = view_df.index

if not view_df.empty:
    if search_factory != "전체":
        view_df = view_df[view_df['공장'] == search_factory]
        
    if not show_completed:
        view_df = view_df[(view_df['수리내용'].isna()) | (view_df['수리내용'] == "")]

st.markdown("👇 **수리 완료 처리 또는 수정할 행을 아래 목록에서 클릭하면 좌측 사이드바로 불러옵니다.**")
event = st.dataframe(
    view_df.drop(columns=['원래번호']) if not view_df.empty else view_df, 
    use_container_width=True, 
    hide_index=True,
    selection_mode="single-row",
    on_select="rerun"
)

if event and 'rows' in event.get('selection', {}) and event['selection']['rows']:
    selected_row_idx = event['selection']['rows'][0]
    actual_df_idx = view_df.iloc[selected_row_idx]['원래번호']
    st.session_state.edit_index = actual_df_idx
    st.rerun()

# ===========================================================================
# 6. 메인 화면: 📥 엑셀 다운로드 존
# ===========================================================================
if not view_df.empty:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        view_df.drop(columns=['원래번호']).to_excel(writer, index=False, sheet_name='Sheet1')
    
    st.download_button(
        label="📥 현재 조회된 고장 이력 엑셀 다운로드",
        data=buffer.getvalue(),
        file_name=f"fixtrack_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
