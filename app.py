import streamlit as st
from datetime import datetime

# Cấu hình hiển thị chuẩn di động & máy tính
st.set_page_config(page_title="Điều Phối Công Việc Nâng Cao", page_icon="📆", layout="centered")

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
    # Lưu danh sách người bận theo từng ngày { "Thứ 2": ["Chị Hoa"], ... }
    st.session_state.day_offs = {day: [] for day in DAYS_OF_WEEK}

if "day_pre_assignments" not in st.session_state:
    # Lưu chỉ định trước theo từng ngày { "Thứ 2": {"Trực đêm": "Đức Tuấn"}, ... }
    st.session_state.day_pre_assignments = {day: {} for day in DAYS_OF_WEEK}

if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================================
# GIAO DIỆN CHÍNH
# ==========================================================
st.title("📆 Cắt Cử Công Việc Tự Động V2")
st.markdown(" *Hỗ trợ cấu hình bận/rảnh và chỉ định việc riêng từng ngày* ")

tab1, tab2, tab3 = st.tabs(["👥 Thành Viên & Việc Gốc", "⚙️ Cấu Hình Phiên Lập Lịch", "🚀 Kết Quả & Lịch Sử"])

# ------------------------------------------------------
# TAB 1: QUẢN LÝ THÀNH VIÊN & DANH SÁCH VIỆC GỐC
# ------------------------------------------------------
with tab1:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Nhân sự toàn cục")
        m_name = st.text_input("Tên thành viên mới:")
        m_exclude = st.text_input("Việc không thể làm (cách nhau dấu phẩy):")
        m_max = st.number_input("Giới hạn việc nhận tối đa/đợt:", min_value=1, value=10)
        if st.button("➕ Thêm Thành Viên"):
            if m_name:
                excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
                st.session_state.members[m_name] = {"excluded": excluded_list, "max": m_max, "workload": 0, "history": []}
                st.success(f"Đã thêm {m_name}")
                st.rerun()
                
    with col_right:
        st.subheader("Danh mục việc cốt lõi")
        t_name = st.text_input("Tên công việc hàng ngày:")
        if st.button("➕ Thêm Việc"):
            if t_name and t_name not in st.session_state.tasks:
                st.session_state.tasks.append(t_name)
                st.success(f"Đã thêm việc: {t_name}")
                st.rerun()

    st.write("---")
    st.markdown("### 📊 Dữ liệu cấu hình hiện tại")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Thành viên & Giới hạn cấm:**")
        for name, info in st.session_state.members.items():
            st.write(f"- **{name}**: Cấm [{', '.join(info['excluded']) if info['excluded'] else 'Không'}], Tối đa: {info['max']}")
    with c2:
        st.write("**Các công việc cần phân bổ mỗi ngày:**")
        for t in st.session_state.tasks:
            st.write(f"- 📌 {t}")

# ------------------------------------------------------
# TAB 2: CẤU HÌNH PHIÊN LẬP LỊCH CHI TIẾT THEO NGÀY
# ------------------------------------------------------
with tab2:
    st.subheader("📅 Thiết lập đặc thù cho từng ngày")
    st.info("💡 Bạn hãy bấm chọn từng ngày dưới đây để cài đặt ai BẬN hoặc GIAO VIỆC TRƯỚC cho riêng ngày đó.")
    
    # Tạo các sub-tab cho từng ngày từ Thứ 2 đến Chủ Nhật
    day_tabs = st.tabs(DAYS_OF_WEEK)
    
    for idx, day in enumerate(DAYS_OF_WEEK):
        with day_tabs[idx]:
            st.markdown(f"#### Cài đặt cho **{day}**")
            
            # 1. Chọn người bận/không cắt cử ngày này
            st.session_state.day_offs[day] = st.multiselect(
                f"❌ Chọn người KHÔNG cắt cử (BẬN) vào {day}:",
                options=list(st.session_state.members.keys()),
                default=st.session_state.day_offs[day],
                key=f"off_{day}"
            )
            
            # 2. Giao việc cụ thể trước cho riêng ai đó ngày này
            st.markdown("🎯 **Giao việc đích danh trước (Nhiệm vụ cụ thể):**")
            
            # Hiển thị các lệnh ghim hiện tại của ngày
            current_pre = st.session_state.day_pre_assignments[day]
            if current_pre:
                for task, member in list(current_pre.items()):
                    col_view_a, col_view_b = st.columns([3, 1])
                    col_view_a.write(f"👉 Chỉ định: **{member}** làm việc *'{task}'*")
                    if col_view_b.button("Hủy ghim", key=f"del_{day}_{task}"):
                        del st.session_state.day_pre_assignments[day][task]
                        st.rerun()
            
            # Form ngắn để thêm chỉ định việc trước
            with st.form(key=f"form_pre_{day}"):
                c_m = st.selectbox("Chọn người nhận việc:", ["-- Chọn người --"] + list(st.session_state.members.keys()))
                c_t = st.selectbox("Chọn việc giao riêng:", ["-- Chọn việc --"] + st.session_state.tasks)
                submit_pre = st.form_submit_button("📌 Ghim nhiệm vụ này")
                
                if submit_pre and c_m != "-- Chọn người --" and c_t != "-- Chọn việc --":
                    st.session_state.day_pre_assignments[day][c_t] = c_m
                    st.success(f"Đã ghim: {c_m} làm {c_t} vào {day}")
                    st.rerun()

# ------------------------------------------------------
# TAB 3: TIẾN HÀNH ĐIỀU PHỐI TỰ ĐỘNG & XEM LỊCH SỬ
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
        # Bước 1: Khởi tạo lại tải công việc của mọi người về 0 để chia đều từ đầu cho tuần/phiên này
        for name in st.session_state.members:
            st.session_state.members[name]['workload'] = 0
            
        final_week_schedule = {}
        timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
        
        # Vòng lặp quét qua từng ngày trong tuần
        for day in DAYS_OF_WEEK:
            day_schedule = {}
            # Danh sách việc cần phân phối trong ngày (mặc định lấy danh sách gốc)
            remaining_tasks = st.session_state.tasks.copy()
            
            # --- PHẦN 1: Áp dụng các việc ĐÃ CHỈ ĐỊNH TRƯỚC cho ngày này ---
            pre_assigned = st.session_state.day_pre_assignments[day]
            for task, member in pre_assigned.items():
                day_schedule[task] = member
                st.session_state.members[member]['workload'] += 1
                st.session_state.members[member]['history'].append(f"{day}: {task} (Chỉ định)")
                if task in remaining_tasks:
                    remaining_tasks.remove(task) # Việc này đã giao xong, không tự động chia nữa
            
            # --- PHẦN 2: Tự động điều phối các công việc CÒN LẠI ---
            busy_people = st.session_state.day_offs[day] # Người bận ngày này
            
            for task in remaining_tasks:
                eligible_members = []
                for name, info in st.session_state.members.items():
                    # ĐIỀU KIỆN CHIA VIỆC TỰ ĐỘNG: 
                    # Không bận ngày này + Việc không nằm trong danh sách cấm + Chưa vượt quá số việc tối đa
                    if (name not in busy_people and 
                        task not in info['excluded'] and 
                        info['workload'] < info['max']):
                        eligible_members.append(name)
                        
                if not eligible_members:
                    day_schedule[task] = "⚠️ Không ai đủ điều kiện"
                    continue
                
                # ĐẢM BẢO CÔNG BẰNG TUYỆT ĐỐI: 
                # Sắp xếp chọn người có workload tích lũy trong tuần thấp nhất tại thời điểm đó
                eligible_members.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                chosen_one = eligible_members[0]
                
                # Giao việc tự động
                day_schedule[task] = chosen_one
                st.session_state.members[chosen_one]['workload'] += 1
                st.session_state.members[chosen_one]['history'].append(f"{day}: {task}")
                
            final_week_schedule[day] = day_schedule

        # Lưu kết quả toàn bộ tuần vào lịch sử hệ thống
        st.session_state.history.append({"time": timestamp, "schedule": final_week_schedule})

    # --- HIỂN THỊ KẾT QUẢ VÀ LỊCH SỬ ---
    st.write("---")
    if not st.session_state.history:
        st.info("Chưa thực hiện phiên cắt cử nào. Hãy bấm nút phía trên để chạy hệ thống.")
    else:
        st.subheader("📋 Bảng Kết Quả Điều Phối Mới Nhất")
        latest_session = st.session_state.history[-1]
        st.caption(f"Thời gian tính toán: {latest_session['time']}")
        
        # Hiển thị kết quả tuần trực quan dưới dạng các hộp mở rộng (Expander)
        for day, schedule in latest_session['schedule'].items():
            with st.expander(f"📅 Lịch làm việc: {day}", expanded=True):
                for task, person in schedule.items():
                    if "⚠️" in person:
                        st.markdown(f"• {task} ➔ <span style='color:red'>{person}</span>", unsafe_allowed_html=True)
                    elif task in st.session_state.day_pre_assignments[day]:
                        st.markdown(f"• {task} ➔ **{person}** *(📌 Chỉ định trước)*")
                    else:
                        st.markdown(f"• {task} ➔ **{person}**")
                        
        # Xem lại tải công việc sau khi chia để Admin kiểm tra tính công bằng
        with st.expander("📊 Thống kê khối lượng công việc đợt này (Kiểm tra công bằng)"):
            for name, info in st.session_state.members.items():
                st.write(f"- **{name}** nhận tổng cộng: `{info['workload']}` nhiệm vụ trong tuần.")