import streamlit as st
from datetime import datetime

# Cấu hình hiển thị chuẩn di động & máy tính
st.set_page_config(page_title="Điều Phối Công Việc Nâng Cao V3", page_icon="📆", layout="centered")

# Danh sách các ngày trong tuần cố định để lập lịch
DAYS_OF_WEEK = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

# ==========================================================
# KHỞI TẠO BỘ NHỚ HỆ THỐNG (SESSION STATE)
# ==========================================================
if "members" not in st.session_state:
    st.session_state.members = {
        "Anh Hải": {"excluded": ["Trực đêm"], "max": 999, "workload": 0, "history": []},
        "Chị Hoa": {"excluded": [], "max": 2, "workload": 0, "history": []},
        "Đức Tuấn": {"excluded": [], "max": 999, "workload": 0, "history": []},
        "Khánh Linh": {"excluded": [], "max": 999, "workload": 0, "history": []}
    }
if "tasks" not in st.session_state:
    st.session_state.tasks = ["Trực ban sáng", "Kiểm tra kho", "Trực đêm"]

# Cấu hình động cho phiên cắt cử hiện tại
if "day_offs" not in st.session_state:
    st.session_state.day_offs = {day: [] for day in DAYS_OF_WEEK}

if "day_pre_assignments" not in st.session_state:
    st.session_state.day_pre_assignments = {day: {} for day in DAYS_OF_WEEK}

if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================================
# GIAO DIỆN CHÍNH
# ==========================================================
st.title("📆 Cắt Cử Công Việc Tự Động V3")
st.markdown(" *Hỗ trợ Thêm/Xóa nhân sự, đầu việc và cấu hình linh hoạt* ")

tab1, tab2, tab3 = st.tabs(["👥 Quản Lý Thành Viên & Việc", "⚙️ Cấu Hình Phiên Lập Lịch", "🚀 Kết Quả & Lịch Sử"])

# ------------------------------------------------------
# TAB 1: QUẢN LÝ THÀNH VIÊN & DANH SÁCH VIỆC (THÊM / XÓA)
# ------------------------------------------------------
with tab1:
    col_left, col_right = st.columns(2)
    
    # --- KHU VỰC THÀNH VIÊN ---
    with col_left:
        st.subheader("👥 Nhân Sự")
        with st.expander("➕ Thêm thành viên mới", expanded=False):
            m_name = st.text_input("Tên thành viên:")
            m_exclude = st.text_input("Việc không thể làm (cách nhau dấu phẩy):")
            m_max = st.number_input("Giới hạn việc nhận tối đa/đợt:", min_value=1, value=10, key="add_max_m")
            if st.button("Lưu thành viên"):
                if m_name.strip():
                    excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
                    st.session_state.members[m_name.strip()] = {"excluded": excluded_list, "max": m_max, "workload": 0, "history": []}
                    st.success(f"Đã thêm {m_name}")
                    st.rerun()
                else:
                    st.error("Tên không được để trống!")
                    
        st.write("---")
        st.markdown("**Danh sách nhân sự hiện tại:**")
        for name, info in list(st.session_state.members.items()):
            col_m_info, col_m_del = st.columns([3, 1])
            col_m_info.write(f"👤 **{name}**\n<small>Cấm: {', '.join(info['excluded']) if info['excluded'] else 'Không'} | Max: {info['max']}</small>", unsafe_allowed_html=True)
            
            # Nút xóa thành viên
            if col_m_del.button("❌ Xóa", key=f"del_m_{name}"):
                del st.session_state.members[name]
                for d in DAYS_OF_WEEK:
                    if name in st.session_state.day_offs[d]:
                        st.session_state.day_offs[d].remove(name)
                    
                    # Xóa bộ nhớ cache widget tránh crash giao diện
                    if f"off_{d}" in st.session_state:
                        del st.session_state[f"off_{d}"]
                        
                    st.session_state.day_pre_assignments[d] = {t: m for t, m in st.session_state.day_pre_assignments[d].items() if m != name}
                st.toast(f"Đã xóa thành viên: {name}")
                st.rerun()
                
    # --- KHU VỰC CÔNG VIỆC ---
    with col_right:
        st.subheader("📌 Công Việc Gốc")
        with st.expander("➕ Thêm công việc mới", expanded=False):
            t_name = st.text_input("Tên công việc hàng ngày:")
            if st.button("Lưu công việc"):
                if t_name.strip():
                    if t_name.strip() not in st.session_state.tasks:
                        st.session_state.tasks.append(t_name.strip())
                        st.success(f"Đã thêm việc: {t_name}")
                        st.rerun()
                    else:
                        st.warning("Công việc này đã tồn tại!")
                else:
                    st.error("Tên việc không được để trống!")
                    
        st.write("---")
        st.markdown("**Danh sách công việc cần chia:**")
        for t in list(st.session_state.tasks):
            col_t_info, col_t_del = st.columns([3, 1])
            col_t_info.write(f"🔹 {t}")
            
            # Nút xóa công việc
            if col_t_del.button("❌ Xóa", key=f"del_t_{t}"):
                st.session_state.tasks.remove(t)
                for d in DAYS_OF_WEEK:
                    if t in st.session_state.day_pre_assignments[d]:
                        del st.session_state.day_pre_assignments[d][t]
                st.toast(f"Đã xóa công việc: {t}")
                st.rerun()

# ------------------------------------------------------
# TAB 2: CẤU HÌNH PHIÊN LẬP LỊCH CHI TIẾT THEO NGÀY
# ------------------------------------------------------
with tab2:
    st.subheader("📅 Thiết lập đặc thù cho từng ngày")
    st.info("💡 Bấm chọn từng ngày dưới đây để cài đặt ai BẬN hoặc GIAO VIỆC TRƯỚC cho riêng ngày đó.")
    
    if not st.session_state.members or not st.session_state.tasks:
        st.warning("⚠️ Vui lòng thêm ít nhất 1 Thành viên và 1 Công việc ở Tab 1 trước khi cấu hình!")
    else:
        day_tabs = st.tabs(DAYS_OF_WEEK)
        
        for idx, day in enumerate(DAYS_OF_WEEK):
            with day_tabs[idx]:
                st.markdown(f"#### Cài đặt cho **{day}**")
                
                # Chọn người bận/không cắt cử ngày này
                st.session_state.day_offs[day] = st.multiselect(
                    f"❌ Chọn người KHÔNG cắt cử (BẬN) vào {day}:",
                    options=list(st.session_state.members.keys()),
                    default=st.session_state.day_offs[day],
                    key=f"off_{day}"
                )
                
                st.markdown("🎯 **Giao việc đích danh trước (Nhiệm vụ cụ thể):**")
                current_pre = st.session_state.day_pre_assignments[day]
                if current_pre:
                    for task, member in list(current_pre.items()):
                        col_view_a, col_view_b = st.columns([3, 1])
                        col_view_a.write(f"👉 Chỉ định: **{member}** làm việc *'{task}'*")
                        if col_view_b.button("Hủy ghim", key=f"del_ghim_{day}_{task}"):
                            del st.session_state.day_pre_assignments[day][task]
                            st.rerun()
                
                with st.form(key=f"form_pre_{day}"):
                    c_m = st.selectbox("Chọn người nhận việc:", ["-- Chọn người --"] + list(st.session_state.members.keys()))
                    c_t = st.selectbox("Chọn việc giao riêng:", ["-- Chọn việc --"] + st.session_state.tasks)
                    submit_pre = st.form_submit_button("📌 Ghim nhiệm vụ này")
                    
                    if submit_pre and c_m != "-- Chọn người --" and c_t != "-- Chọn việc --":
                        if c_m in st.session_state.day_offs[day]:
                            st.error(f"Lỗi: {c_m} đang được chọn là BẬN vào {day}, không thể ghim việc!")
                        else:
                            st.session_state.day_pre_assignments[day][c_t] = c_m
                            st.success(f"Đã ghim: {c_m} làm {c_t} vào {day}")
                            st.rerun()

# ------------------------------------------------------
# TAB 3: TIỂN HÀNH ĐIỀU PHỐI TỰ ĐỘNG & XEM LỊCH SỬ
# ------------------------------------------------------
with tab3:
    st.subheader("⚡ Thực thi thuật toán cắt cử")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        run_algorithm = st.button("🚀 TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN", type="primary", use_container_width=True)
    with col_btn2:
        clear_history = st.button("🗑️ Xóa nhật ký lịch sử", use_container_width=True)
        
    if clear_history:
        st.session_state.history = []
        st.success("Đã xóa sạch lịch sử log!")
        st.rerun()

    if run_algorithm:
        if not st.session_state.tasks or not st.session_state.members:
            st.error("❌ Không thể chạy! Danh sách Thành viên hoặc Công việc đang trống.")
        else:
            for name in st.session_state.members:
                st.session_state.members[name]['workload'] = 0
                
            final_week_schedule = {}
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            for day in DAYS_OF_WEEK:
                day_schedule = {}
                remaining_tasks = st.session_state.tasks.copy()
                
                # --- PHẦN 1: Việc chỉ định trước ---
                pre_assigned = st.session_state.day_pre_assignments[day]
                for task, member in pre_assigned.items():
                    if member in st.session_state.members and task in remaining_tasks:
                        day_schedule[task] = member
                        st.session_state.members[member]['workload'] += 1
                        st.session_state.members[member]['history'].append(f"{day}: {task} (Chỉ định)")
                        remaining_tasks.remove(task)
                
                # --- PHẦN 2: Tự động điều phối ---
                busy_people = st.session_state.day_offs[day]
                for task in remaining_tasks:
                    eligible_members = []
                    for name, info in st.session_state.members.items():
                        if (name not in busy_people and 
                            task not in info['excluded'] and 
                            info['workload'] < info['max']):
                            eligible_members.append(name)
                            
                    if not eligible_members:
                        day_schedule[task] = "⚠️ Không ai đủ điều kiện"
                        continue
                    
                    eligible_members.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                    chosen_one = eligible_members[0]
                    
                    day_schedule[task] = chosen_one
                    st.session_state.members[chosen_one]['workload'] += 1
                    st.session_state.members[chosen_one]['history'].append(f"{day}: {task}")
                    
                final_week_schedule[day] = day_schedule

            st.session_state.history.append({"time": timestamp, "schedule": final_week_schedule})

    # --- HIỂN THỊ KẾT QUẢ VÀ LỊCH SỬ ---
    st.write("---")
    if not st.session_state.history:
        st.info("Chưa thực hiện phiên cắt cử nào. Hãy bấm nút phía trên để chạy hệ thống.")
    else:
        st.subheader("📋 Bảng Kết Quả Điều Phối Mới Nhất")
        latest_session = st.session_state.history[-1]
        st.caption(f"Thời gian tính toán: {latest_session['time']}")
        
        for day, schedule in latest_session['schedule'].items():
            with st.expander(f"📅 Lịch làm việc: {day}", expanded=True):
                for task, person in schedule.items():
                    if "⚠️" in person:
                        st.markdown(f"• {task} ➔ <span style='color:red'>{person}</span>", unsafe_allowed_html=True)
                    elif task in st.session_state.day_pre_assignments[day]:
                        st.markdown(f"• {task} ➔ **{person}** *(📌 Chỉ định trước)*")
                    else:
                        st.markdown(f"• {task} ➔ **{person}**")
                        
        with st.expander("📊 Thống kê khối lượng công việc đợt này (Kiểm tra công bằng)"):
            for name, info in st.session_state.members.items():
                st.write(f"- **{name}** nhận tổng cộng: `{info['workload']}` nhiệm vụ trong tuần.")
