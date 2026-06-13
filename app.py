import streamlit as st
from datetime import datetime

# Cấu hình trang hiển thị di động mượt mà
st.set_page_config(page_title="Cắt cử Công Việc", page_icon="⚡", layout="centered")

# ==========================================================
# KHỞI TẠO BỘ NHỚ LƯU TRỮ (SESSION STATE)
# ==========================================================
if "members" not in st.session_state:
    st.session_state.members = {
        "Anh Hải": {"excluded": ["Trực đêm"], "max": 999, "workload": 0, "history": []},
        "Chị Hoa": {"excluded": [], "max": 1, "workload": 0, "history": []},
        "Đức Tuấn": {"excluded": [], "max": 999, "workload": 0, "history": []},
        "Khánh Linh": {"excluded": [], "max": 999, "workload": 0, "history": []}
    }
if "tasks" not in st.session_state:
    st.session_state.tasks = [
        {"name": "Trực ban sáng", "type": "Cố định"},
        {"name": "Kiểm tra kho", "type": "Cố định"},
        {"name": "Trực đêm", "type": "Cố định"},
        {"name": "Sửa mạng đột xuất", "type": "Phát sinh"}
    ]
if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================================
# GIAO DIỆN CHÍNH
# ==========================================================
st.title("⚡ Hệ Thống Điều Phối Công Việc")

tab1, tab2, tab3 = st.tabs(["👥 Thành Viên", "📋 Công Việc", "🚀 Điều Phối & Lịch Sử"])

# ------------------------------------------------------
# TAB 1: QUẢN LÝ THÀNH VIÊN
# ------------------------------------------------------
with tab1:
    st.subheader("Thêm Thành Viên Mới")
    m_name = st.text_input("Tên thành viên:")
    m_exclude = st.text_input("Công việc KHÔNG THỂ làm (cách nhau bằng dấu phẩy):")
    m_max = st.number_input("Số việc tối đa có thể nhận:", min_value=1, value=5)
    
    if st.button("Thêm Thành Viên"):
        if m_name:
            excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
            st.session_state.members[m_name] = {
                "excluded": excluded_list,
                "max": m_max,
                "workload": 0,
                "history": []
            }
            st.success(f"Đã thêm {m_name}!")
            st.rerun()
            
    st.write("---")
    st.subheader("Danh sách hiện tại:")
    for name, info in st.session_state.members.items():
        st.markdown(f"**{name}** (Tải hiện tại: {info['workload']})")
        st.caption(f"Bỏ qua: {', '.join(info['excluded']) if info['excluded'] else 'Không'} | Tối đa: {info['max']} việc")

# ------------------------------------------------------
# TAB 2: QUẢN LÝ CÔNG VIỆC
# ------------------------------------------------------
with tab2:
    st.subheader("Thêm Công Việc Mới")
    t_name = st.text_input("Tên công việc:")
    t_type = st.selectbox("Loại công việc:", ["Cố định", "Phát sinh"])
    
    if st.button("Thêm Công Việc"):
        if t_name:
            st.session_state.tasks.append({"name": t_name, "type": t_type})
            st.success(f"Đã thêm việc: {t_name}")
            st.rerun()
            
    st.write("---")
    st.subheader("Danh sách công việc chờ xếp:")
    for t in st.session_state.tasks:
        badge = "📌" if t['type'] == "Cố định" else "⚡"
        st.write(f"{badge} {t['name']} ({t['type']})")

# ------------------------------------------------------
# TAB 3: ĐIỀU PHỐI & LỊCH SỬ
# ------------------------------------------------------
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        run_assign = st.button("🚀 TỰ ĐỘNG CẮT CỬ", type="primary", use_container_width=True)
    with col2:
        reset_load = st.button("🔄 Reset Tải Công Việc", use_container_width=True)
        
    if reset_load:
        for name in st.session_state.members:
            st.session_state.members[name]['workload'] = 0
        st.success("Đã làm mới tải công việc về 0!")
        st.rerun()

    if run_assign:
        if not st.session_state.tasks or not st.session_state.members:
            st.error("Thiếu dữ liệu Công việc hoặc Thành viên!")
        else:
            # Sắp xếp việc cố định trước
            sorted_tasks = sorted(st.session_state.tasks, key=lambda x: 0 if x['type'] == 'Cố định' else 1)
            current_session = {}
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            st.subheader("Kết quả đợt này:")
            
            for task in sorted_tasks:
                eligible = []
                for name, info in st.session_state.members.items():
                    if task['name'] not in info['excluded'] and info['workload'] < info['max']:
                        eligible.append(name)
                
                if not eligible:
                    st.warning(f"⚠️ Không ai đủ điều kiện: {task['name']}")
                    continue
                
                # Chọn người ít việc nhất
                eligible.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                chosen = eligible[0]
                
                # Cập nhật dữ liệu
                st.session_state.members[chosen]['workload'] += 1
                st.session_state.members[chosen]['history'].append(task['name'])
                current_session[task['name']] = chosen
                
                st.write(f"✅ **{chosen}** ➔ {task['name']}")
            
            # Lưu lịch sử
            st.session_state.history.append({"time": timestamp, "jobs": current_session})
            # Xóa việc phát sinh, giữ việc cố định
            st.session_state.tasks = [t for t in st.session_state.tasks if t['type'] == 'Cố định']

    st.write("---")
    st.subheader("📜 Nhật Ký Lịch Sử Cắt Cử")
    if not st.session_state.history:
        st.info("Chưa có lịch sử điều phối.")
    else:
        for idx, session in enumerate(reversed(st.session_state.history), 1):
            with st.expander(f"📍 Lần {idx} ({session['time']})"):
                for job, person in session['jobs'].items():
                    st.write(f"• {job} ➔ **{person}**")