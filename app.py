import streamlit as st
from datetime import datetime

# Cấu hình hiển thị chuẩn di động & máy tính
st.set_page_config(page_title="Điều Phối Công Việc V4", page_icon="📆", layout="wide")

# Danh sách các ngày trong tuần cố định
DAYS_OF_WEEK = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

# ==========================================================
# KHỞI TẠO BỘ NHỚ HỆ THỐNG (SESSION STATE)
# ==========================================================
if "members" not in st.session_state:
    st.session_state.members = {
        "Anh Hải": {"excluded": ["Trực đêm"], "max": 15, "workload": 0, "history": []},
        "Chị Hoa": {"excluded": [], "max": 5, "workload": 0, "history": []},
        "Đức Tuấn": {"excluded": [], "max": 20, "workload": 0, "history": []},
        "Khánh Linh": {"excluded": [], "max": 20, "workload": 0, "history": []}
    }
if "shifts" not in st.session_state:
    st.session_state.shifts = ["Ca Sáng (08:00-12:00)", "Ca Chiều (13:00-17:00)", "Ca Đêm (22:00-06:00)"]

if "tasks" not in st.session_state:
    st.session_state.tasks = ["Trực ban", "Kiểm tra kho", "Hỗ trợ khách hàng"]

if "day_offs" not in st.session_state:
    st.session_state.day_offs = {day: [] for day in DAYS_OF_WEEK}

# Cấu hình ghim lưu dưới dạng: { "Ngày_Ca_Việc": [Danh sách người được ghim] }
if "pins" not in st.session_state:
    st.session_state.pins = {}

if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================================
# GIAO DIỆN CHÍNH
# ==========================================================
st.title("📆 Hệ Thống Cắt Cử Công Việc Tự Động V4")
st.markdown(" *Phiên bản tối ưu: Quản lý theo Ca/Giờ, Ghim nhiều người - nhiều việc, Chống trùng lịch* ")

tab1, tab2, tab3 = st.tabs(["⚙️ Cơ Sở Dữ Liệu Gốc", "📅 Cấu Hình Ca & Ghim Việc", "🚀 Cắt Cử & Lịch Sử"])

# ------------------------------------------------------
# TAB 1: QUẢN LÝ THÀNH VIÊN, CA TRỰC & CÔNG VIỆC
# ------------------------------------------------------
with tab1:
    col_m, col_s, col_t = st.columns(3)
    
    # --- 1. QUẢN LÝ NHÂN SỰ ---
    with col_m:
        st.subheader("👥 Nhân Sự")
        with st.expander("➕ Thêm nhân sự", expanded=False):
            m_name = st.text_input("Tên thành viên:")
            m_exclude = st.text_input("Việc không thể làm (cách nhau dấu phẩy):")
            m_max = st.number_input("Giới hạn việc/tuần:", min_value=1, value=10, key="m_max_v4")
            if st.button("Lưu nhân sự"):
                if m_name.strip():
                    excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
                    st.session_state.members[m_name.strip()] = {"excluded": excluded_list, "max": m_max, "workload": 0, "history": []}
                    st.rerun()
        
        st.write("---")
        for name, info in list(st.session_state.members.items()):
            c_info, c_del = st.columns([3, 1])
            c_info.markdown(f"👤 **{name}** \n<small>Cấm: {', '.join(info['excluded']) if info['excluded'] else 'Không'} | Max: {info['max']}</small>", unsafe_allow_html=True)
            if c_del.button("❌", key=f"del_m_{name}"):
                del st.session_state.members[name]
                # Dọn dẹp tên khỏi danh sách bận và ghim
                for d in DAYS_OF_WEEK:
                    if name in st.session_state.day_offs[d]: st.session_state.day_offs[d].remove(name)
                for k in list(st.session_state.pins.keys()):
                    st.session_state.pins[k] = [m for m in st.session_state.pins[k] if m != name]
                st.rerun()

    # --- 2. QUẢN LÝ CA / KHUNG GIỜ ---
    with col_s:
        st.subheader("🕒 Ca / Khung Giờ")
        with st.expander("➕ Thêm ca trực mới", expanded=False):
            s_name = st.text_input("Tên ca (Ví dụ: Ca Chiều (13h-17h)):")
            if st.button("Lưu ca trực"):
                if s_name.strip() and s_name.strip() not in st.session_state.shifts:
                    st.session_state.shifts.append(s_name.strip())
                    st.rerun()
        
        st.write("---")
        for shift in list(st.session_state.shifts):
            c_info, c_del = st.columns([3, 1])
            c_info.write(f"⏰ {shift}")
            if c_del.button("❌", key=f"del_s_{shift}"):
                st.session_state.shifts.remove(shift)
                # Dọn dẹp ghim liên quan đến ca này
                st.session_state.pins = {k: v for k, v in st.session_state.pins.items() if f"_{shift}_" not in k}
                st.rerun()

    # --- 3. QUẢN LÝ CÔNG VIỆC ---
    with col_t:
        st.subheader("📌 Công Việc")
        with st.expander("➕ Thêm công việc mới", expanded=False):
            t_name = st.text_input("Tên công việc:")
            if st.button("Lưu công việc"):
                if t_name.strip() and t_name.strip() not in st.session_state.tasks:
                    st.session_state.tasks.append(t_name.strip())
                    st.rerun()
        
        st.write("---")
        for task in list(st.session_state.tasks):
            c_info, c_del = st.columns([3, 1])
            c_info.write(f"🔹 {task}")
            if c_del.button("❌", key=f"del_t_{task}"):
                st.session_state.tasks.remove(task)
                # Dọn dẹp ghim liên quan đến việc này
                st.session_state.pins = {k: v for k, v in st.session_state.pins.items() if not k.endswith(f"_{task}")}
                st.rerun()

# ------------------------------------------------------
# TAB 2: CẤU HÌNH ĐẶC THÙ THEO NGÀY VÀ THEO CA CHI TIẾT
# ------------------------------------------------------
with tab2:
    st.subheader("📅 Thiết lập đặc thù theo từng Ca trong ngày")
    
    if not st.session_state.members or not st.session_state.shifts or not st.session_state.tasks:
        st.warning("⚠️ Vui lòng điền đầy đủ Nhân sự, Ca trực và Công việc ở Tab 1 trước!")
    else:
        day_tabs = st.tabs(DAYS_OF_WEEK)
        for idx, day in enumerate(DAYS_OF_WEEK):
            with day_tabs[idx]:
                st.markdown(f"### 🛠️ Cấu hình cho **{day}**")
                
                # Chọn người bận cả ngày
                valid_defaults = [m for m in st.session_state.day_offs[day] if m in st.session_state.members]
                st.session_state.day_offs[day] = st.multiselect(
                    f"❌ Chọn người nghỉ (BẬN cả ngày) vào {day}:",
                    options=list(st.session_state.members.keys()),
                    default=valid_defaults,
                    key=f"off_{day}"
                )
                
                st.write("---")
                st.markdown("#### 🕒 Danh sách các ca trực trong ngày:")
                
                # Duyệt qua từng ca trực để cấu hình ghim đa nhiệm
                for shift in st.session_state.shifts:
                    with st.expander(f"⚙️ Thiết lập cho: {shift}", expanded=False):
                        
                        # Hiển thị các lệnh ghim hiện tại của Ca này
                        st.markdown("**📌 Các nhiệm vụ đã ghim trước trong ca này:**")
                        has_pin = False
                        for task in st.session_state.tasks:
                            pin_key = f"{day}_{shift}_{task}"
                            if pin_key in st.session_state.pins and st.session_state.pins[pin_key]:
                                has_pin = True
                                c_pin_text, c_pin_del = st.columns([4, 1])
                                people_str = ", ".join(st.session_state.pins[pin_key])
                                c_pin_text.write(f"• Việc *'{task}'* ➔ Đã ghim cho: **{people_str}**")
                                if c_pin_del.button("Hủy ghim", key=f"unpin_{pin_key}"):
                                    del st.session_state.pins[pin_key]
                                    st.rerun()
                        if not has_pin:
                            st.caption("Chưa có nhiệm vụ nào được ghim trước.")
                        
                        st.write("---")
                        # Form để ghim nhiều người vào việc (Ghim đa nhiệm)
                        st.markdown("**➕ Thêm ghim mới (Nhiều người - Nhiều việc):**")
                        with st.form(key=f"form_pin_{day}_{shift}"):
                            chosen_task = st.selectbox("Chọn công việc cần ghim:", st.session_state.tasks, key=f"sel_t_{day}_{shift}")
                            chosen_people = st.multiselect("Chọn những ai sẽ làm việc này (Có thể chọn nhiều người):", options=list(st.session_state.members.keys()), key=f"sel_m_{day}_{shift}")
                            submit_pin = st.form_submit_button("🎯 Xác nhận ghim vào ca này")
                            
                            if submit_pin and chosen_people:
                                # Kiểm tra xem có ai lỡ bị chọn bận cả ngày không
                                conf_conflict = [p for p in chosen_people if p in st.session_state.day_offs[day]]
                                if conf_conflict:
                                    st.error(f"Lỗi: {', '.join(conf_conflict)} đã xin nghỉ cả ngày này ở trên!")
                                else:
                                    pin_key = f"{day}_{shift}_{chosen_task}"
                                    st.session_state.pins[pin_key] = chosen_people
                                    st.success("Đã ghim thành công!")
                                    st.rerun()

# ------------------------------------------------------
# TAB 3: TIẾN HÀNH ĐIỀU PHỐI TỰ ĐỘNG & XEM KẾT QUẢ
# ------------------------------------------------------
with tab3:
    st.subheader("⚡ Thực thi thuật toán cắt cử thông minh")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        run_v4 = st.button("🚀 TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN", type="primary", use_container_width=True)
    with c_btn2:
        clear_log = st.button("🗑️ Xóa sạch lịch sử", use_container_width=True)
        
    if clear_log:
        st.session_state.history = []
        st.success("Đã xóa nhật ký lịch sử thành công!")
        st.rerun()

    if run_v4:
        if not st.session_state.members or not st.session_state.shifts or not st.session_state.tasks:
            st.error("Thiếu dữ liệu để tính toán lịch!")
        else:
            # Reset tải công việc về 0 trước khi tính toán phiên mới
            for name in st.session_state.members:
                st.session_state.members[name]['workload'] = 0
            
            week_schedule = {}
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            # --- VÒNG LẶP ĐIỀU PHỐI CHÍNH ---
            for day in DAYS_OF_WEEK:
                week_schedule[day] = {}
                busy_day_people = st.session_state.day_offs[day]
                
                for shift in st.session_state.shifts:
                    # Tạo cấu trúc lưu trữ kết quả cho ca: { "Tên việc": [Danh sách người làm] }
                    week_schedule[day][shift] = {task: [] for task in st.session_state.tasks}
                    
                    # Tập hợp chống trùng lịch: Ai đã có việc trong ca này rồi thì KHÔNG giao thêm việc khác nữa
                    assigned_in_this_shift = set()
                    
                    # BƯỚC 1: ƯU TIÊN ĐIỀN CÁC LỆNH GHIM TRƯỚC
                    for task in st.session_state.tasks:
                        pin_key = f"{day}_{shift}_{task}"
                        if pin_key in st.session_state.pins:
                            for member in st.session_state.pins[pin_key]:
                                # Kiểm tra xem thành viên ghim còn tồn tại trong DB không
                                if member in st.session_state.members:
                                    week_schedule[day][shift][task].append(member)
                                    st.session_state.members[member]['workload'] += 1
                                    st.session_state.members[member]['history'].append(f"{day}-{shift}: {task} (Ghim)")
                                    assigned_in_this_shift.add(member) # Đánh dấu đã có việc ca này
                                    
                    # BƯỚC 2: TỰ ĐỘNG ĐIỀU PHỐI CÁC CHỖ TRỐNG CÒN LẠI
                    for task in st.session_state.tasks:
                        # Nếu việc này chưa có ai được ghim, hệ thống sẽ tự động tìm 1 người phù hợp nhất
                        if not week_schedule[day][shift][task]:
                            eligible_members = []
                            for name, info in st.session_state.members.items():
                                # ĐIỀU KIỆN NHẬN VIỆC TỰ ĐỘNG TRONG CA:
                                if (name not in busy_day_people and          # 1. Không nghỉ ngày này
                                    name not in assigned_in_this_shift and   # 2. CHỐNG TRÙNG: Chưa có việc nào ca này
                                    task not in info['excluded'] and         # 3. Việc không nằm trong danh mục cấm
                                    info['workload'] < info['max']):         # 4. Chưa vượt tải tuần
                                    eligible_members.append(name)
                            
                            if not eligible_members:
                                week_schedule[day][shift][task].append("⚠️ Không ai đủ điều kiện")
                                continue
                            
                            # ĐẢM BẢO CÔNG BẰNG: Chọn người có workload tích lũy thấp nhất tuần tại thời điểm đó
                            eligible_members.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                            chosen = eligible_members[0]
                            
                            # Giao việc tự động
                            week_schedule[day][shift][task].append(chosen)
                            st.session_state.members[chosen]['workload'] += 1
                            st.session_state.members[chosen]['history'].append(f"{day}-{shift}: {task}")
                            assigned_in_this_shift.add(chosen) # Khóa người này lại trong ca hiện tại
                            
            # Lưu lịch tuần vào lịch sử hệ thống
            st.session_state.history.append({"time": timestamp, "schedule": week_schedule})
            st.rerun()

    # --- HIỂN THỊ KẾT QUẢ MỚI NHẤT ---
    st.write("---")
    if not st.session_state.history:
        st.info("💡 Hệ thống đang sẵn sàng. Hãy cài đặt cấu hình ở Tab 2 rồi bấm nút 'TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN' để nhận lịch.")
    else:
        latest = st.session_state.history[-1]
        st.subheader(f"📋 Bảng Kết Quả Cắt Cử Toàn Tuần Mới Nhất ({latest['time']})")
        
        for day in DAYS_OF_WEEK:
            with st.expander(f"📅 LỊCH CÔNG TÁC: {day}", expanded=True):
                # Tạo bảng hiển thị trực quan các ca trực
                for shift in st.session_state.shifts:
                    st.markdown(f"**🕒 {shift}**")
                    for task, people in latest['schedule'][day][shift].items():
                        people_text = ", ".join(people)
                        
                        # Kiểm tra xem đây là diện ghim hay diện tự động chia để hiển thị tag trực quan
                        pin_key = f"{day}_{shift}_{task}"
                        if "⚠️" in people_text:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 {task} ➔ <span style='color:red'>{people_text}</span>", unsafe_allow_html=True)
                        elif pin_key in st.session_state.pins and st.session_state.pins[pin_key]:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 {task} ➔ **{people_text}** *(📌 Ghim trước)*")
                        else:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 {task} ➔ **{people_text}**")
                    st.write("")
                    
        # Xem bảng thống kê tải công việc để Admin đối chiếu tính công bằng
        with st.expander("📊 Biểu đồ thống kê khối lượng công việc tuần này (Tính công bằng)"):
            for name, info in st.session_state.members.items():
                st.write(f"- 👤 **{name}** đã được phân bổ: `{info['workload']}` ca trực/nhiệm vụ trong tuần.")