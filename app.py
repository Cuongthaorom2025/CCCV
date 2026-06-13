import streamlit as st
from datetime import datetime
import re  # Thêm thư viện cấu trúc chuỗi thông minh

# Cấu hình hiển thị chuẩn di động & máy tính
st.set_page_config(page_title="Điều Phối Công Việc V5.1", page_icon="📆", layout="wide")

# Danh sách các ngày trong tuần cố định
DAYS_OF_WEEK = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

# ==========================================================
# KHỞI TẠO BỘ NHỚ HỆ THỐNG (SESSION STATE)
# ==========================================================
if "members" not in st.session_state:
    st.session_state.members = {
        "Anh Hải": {"excluded": ["Trực đêm"], "max": 15, "workload": 0, "history": []},
        "Chị Hoa": {"excluded": [], "max": 5, "workload": 0, "history": []},
        "Đức Tuấn": {"excluded": [], "max": 20, "workload": 0, "history": []}
    }
if "shifts" not in st.session_state:
    st.session_state.shifts = ["Ca Sáng (08:00-12:00)", "Ca Chiều (13:00-17:00)"]

if "tasks" not in st.session_state:
    st.session_state.tasks = ["Trực ban", "Kiểm tra kho"]

if "day_offs" not in st.session_state:
    st.session_state.day_offs = {day: [] for day in DAYS_OF_WEEK}

if "pins" not in st.session_state:
    st.session_state.pins = {}

if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================================
# GIAO DIỆN CHÍNH
# ==========================================================
st.title("📆 Hệ Thống Cắt Cử Công Việc Tự Động V5.1")
st.markdown(" *Đã sửa lỗi nhận diện khung giờ — Hỗ trợ ghim tốc hành đa dụng* ")

tab1, tab2, tab3 = st.tabs(["⚙️ Cơ Sở Dữ Liệu Gốc", "📅 Cấu Hình Ca & Ghim Việc", "🚀 Cắt Cử & Lịch Sử"])

# ------------------------------------------------------
# TAB 1: QUẢN LÝ THÀNH VIÊN, CA TRỰC & CÔNG VIỆC GỐC
# ------------------------------------------------------
with tab1:
    st.info("💡 Mẹo di động: Bạn không nhất thiết phải thêm dữ liệu ở đây. Khi ghim nhanh bằng văn bản ở Tab 2, hệ thống sẽ tự động cập nhật vào đây cho bạn!")
    col_m, col_s, col_t = st.columns(3)
    
    with col_m:
        st.subheader("👥 Nhân Sự Tổng")
        with st.expander("➕ Thêm nhân sự", expanded=False):
            m_name = st.text_input("Tên thành viên:")
            m_exclude = st.text_input("Việc không thể làm (cách nhau dấu phẩy):")
            m_max = st.number_input("Giới hạn việc/tuần:", min_value=1, value=10, key="m_max_v5")
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
                for d in DAYS_OF_WEEK:
                    if name in st.session_state.day_offs[d]: st.session_state.day_offs[d].remove(name)
                for k in list(st.session_state.pins.keys()):
                    st.session_state.pins[k] = [m for m in st.session_state.pins[k] if m != name]
                st.rerun()

    with col_s:
        st.subheader("🕒 Ca / Khung Giờ")
        with st.expander("➕ Thêm ca trực mới", expanded=False):
            s_name = st.text_input("Tên ca (Ví dụ: Ca 1 (7h30-11h)):")
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
                st.session_state.pins = {k: v for k, v in st.session_state.pins.items() if f"_{shift}_" not in k}
                st.rerun()

    with col_t:
        st.subheader("📌 Công Việc")
        with st.expander("➕ Thêm công việc mới", expanded=False):
            t_name = st.text_input("Tên công việc (Ví dụ: Trực UAV):")
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
                st.session_state.pins = {k: v for k, v in st.session_state.pins.items() if not k.endswith(f"_{task}")}
                st.rerun()

# ------------------------------------------------------
# TAB 2: CẤU HÌNH ĐẶC THÙ THEO NGÀY VÀ GHIM TỐC HÀNH
# ------------------------------------------------------
with tab2:
    st.subheader("📅 Thiết lập đặc thù & Ghim việc theo ngày")
    
    day_tabs = st.tabs(DAYS_OF_WEEK)
    for idx, day in enumerate(DAYS_OF_WEEK):
        with day_tabs[idx]:
            st.markdown(f"### 🛠️ Cài đặt cho **{day}**")
            
            # Chọn người bận cả ngày
            valid_defaults = [m for m in st.session_state.day_offs[day] if m in st.session_state.members]
            st.session_state.day_offs[day] = st.multiselect(
                f"❌ Chọn người nghỉ (BẬN cả ngày) vào {day}:",
                options=list(st.session_state.members.keys()),
                default=valid_defaults,
                key=f"off_{day}"
            )
            
            st.write("---")
            
            # 🔥 TRỢ LÝ GHIM TỐC HÀNH ĐÃ ĐƯỢC FIX LỖI CHÍNH XÁC
            st.markdown("### ⚡ Trợ lý Ghim Tốc Hành (Nhập nhanh văn bản)")
            st.caption("Cú pháp linh hoạt: `Tên người - Tên ca - Tên việc` hoặc dùng dấu phẩy `Tên người, Tên ca, Tên việc`")
            
            quick_input = st.text_input(
                "Nhập câu lệnh ghim:", 
                placeholder="Ánh - Ca 1 (7h30-11h) - Trực UAV", 
                key=f"text_input_{day}"
            )
            
            if st.button("🚀 Kích hoạt ghim nhanh", key=f"btn_quick_{day}"):
                if quick_input:
                    # SỬA ĐỔI: Tách bằng dấu phẩy, chấm phẩy, hoặc dấu gạch ngang PHẢI CÓ khoảng trống hai bên (\s+-\s+)
                    # Điều này giữ nguyên dấu gạch nối viết liền ở khung giờ như '7h30-11h'
                    parts = [p.strip() for p in re.split(r'[,;|]|\s+-\s+|\s+–\s+|\s+—\s+', quick_input) if p.strip()]
                    
                    if len(parts) == 3:
                        p_name, p_shift, p_task = parts[0], parts[1], parts[2]
                        
                        # Tự động tạo mới nếu thiếu dữ liệu
                        if p_name not in st.session_state.members:
                            st.session_state.members[p_name] = {"excluded": [], "max": 10, "workload": 0, "history": []}
                            st.toast(f"Hệ thống tự tạo thành viên mới: {p_name}")
                        if p_shift not in st.session_state.shifts:
                            st.session_state.shifts.append(p_shift)
                            st.toast(f"Hệ thống tự tạo ca mới: {p_shift}")
                        if p_task not in st.session_state.tasks:
                            st.session_state.tasks.append(p_task)
                            st.toast(f"Hệ thống tự tạo việc mới: {p_task}")
                            
                        # Lưu cấu hình ghim
                        pin_key = f"{day}_{p_shift}_{p_task}"
                        if pin_key not in st.session_state.pins:
                            st.session_state.pins[pin_key] = []
                        if p_name not in st.session_state.pins[pin_key]:
                            st.session_state.pins[pin_key].append(p_name)
                            
                        st.success(f"🎉 Ghim thành công **{p_name}** làm **{p_task}** tại **{p_shift}**")
                        st.rerun()
                    else:
                        st.error(f"⚠️ Sai cú pháp! Hệ thống đếm được {len(parts)} phần. Hãy đảm bảo có khoảng cách trước và sau dấu gạch ngang. Ví dụ: Ánh - Ca 1 (7h30-11h) - Trực UAV")

            st.write("---")
            st.markdown("#### 📌 Trạng thái các ca và ghim hiện tại của ngày:")
            
            if not st.session_state.shifts:
                st.caption("Chưa có ca làm việc nào.")
            else:
                for shift in st.session_state.shifts:
                    has_pin = False
                    pin_details = []
                    for task in st.session_state.tasks:
                        pin_key = f"{day}_{shift}_{task}"
                        if pin_key in st.session_state.pins and st.session_state.pins[pin_key]:
                            has_pin = True
                            people_str = ", ".join(st.session_state.pins[pin_key])
                            pin_details.append((task, people_str, pin_key))
                    
                    shift_title = f"⏰ {shift} — *(Có {len(pin_details)} việc được ghim trước)*" if has_pin else f"⏰ {shift}"
                    with st.expander(shift_title, expanded=has_pin):
                        if not has_pin:
                            st.caption("Không có ghim nào trong ca này (Hệ thống sẽ tự động điều phối khi chạy)")
                        else:
                            for task, people, p_key in pin_details:
                                c_txt, c_del = st.columns([4, 1])
                                c_txt.write(f"• **{task}** ➔ Ghim cho: `{people}`")
                                if c_del.button("Hủy ghim", key=f"unpin_{p_key}"):
                                    del st.session_state.pins[p_key]
                                    st.rerun()

# ------------------------------------------------------
# TAB 3: TIẾN HÀNH ĐIỀU PHỐI TỰ ĐỘNG & XEM KẾT QUẢ
# ------------------------------------------------------
with tab3:
    st.subheader("⚡ Thực thi thuật toán cắt cử thông minh")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        run_v5 = st.button("🚀 TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN", type="primary", use_container_width=True)
    with c_btn2:
        clear_log = st.button("🗑️ Xóa sạch lịch sử", use_container_width=True)
        
    if clear_log:
        st.session_state.history = []
        st.success("Đã xóa nhật ký lịch sử thành công!")
        st.rerun()

    if run_v5:
        if not st.session_state.members or not st.session_state.shifts or not st.session_state.tasks:
            st.error("Thiếu dữ liệu để chạy thuật toán!")
        else:
            for name in st.session_state.members:
                st.session_state.members[name]['workload'] = 0
            
            week_schedule = {}
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            for day in DAYS_OF_WEEK:
                week_schedule[day] = {}
                busy_day_people = st.session_state.day_offs[day]
                
                for shift in st.session_state.shifts:
                    week_schedule[day][shift] = {task: [] for task in st.session_state.tasks}
                    assigned_in_this_shift = set()
                    
                    # BƯỚC 1: ĐIỀN CÁC LỆNH GHIM TRƯỚC
                    for task in st.session_state.tasks:
                        pin_key = f"{day}_{shift}_{task}"
                        if pin_key in st.session_state.pins:
                            for member in st.session_state.pins[pin_key]:
                                if member in st.session_state.members:
                                    week_schedule[day][shift][task].append(member)
                                    st.session_state.members[member]['workload'] += 1
                                    st.session_state.members[member]['history'].append(f"{day}-{shift}: {task} (Ghim)")
                                    assigned_in_this_shift.add(member)
                                    
                    # BƯỚC 2: TỰ ĐỘNG ĐIỀU PHỐI CÁC PHẦN VIỆC TRỐNG
                    for task in st.session_state.tasks:
                        if not week_schedule[day][shift][task]:
                            eligible_members = []
                            for name, info in st.session_state.members.items():
                                if (name not in busy_day_people and          
                                    name not in assigned_in_this_shift and   
                                    task not in info['excluded'] and         
                                    info['workload'] < info['max']):         
                                    eligible_members.append(name)
                            
                            if not eligible_members:
                                week_schedule[day][shift][task].append("⚠️ Không ai đủ điều kiện")
                                continue
                            
                            eligible_members.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                            chosen = eligible_members[0]
                            
                            week_schedule[day][shift][task].append(chosen)
                            st.session_state.members[chosen]['workload'] += 1
                            st.session_state.members[chosen]['history'].append(f"{day}-{shift}: {task}")
                            assigned_in_this_shift.add(chosen)
                            
            st.session_state.history.append({"time": timestamp, "schedule": week_schedule})
            st.rerun()

    # --- HIỂN THỊ KẾT QUẢ MỚI NHẤT ---
    st.write("---")
    if not st.session_state.history:
        st.info("💡 Hệ thống đang sẵn sàng. Hãy bấm nút 'TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN' để tính toán lịch công bằng.")
    else:
        latest = st.session_state.history[-1]
        st.subheader(f"📋 Bảng Kết Quả Cắt Cử Toàn Tuần Mới Nhất ({latest['time']})")
        
        for day in DAYS_OF_WEEK:
            if day in latest['schedule']:
                with st.expander(f"📅 LỊCH CÔNG TÁC: {day}", expanded=True):
                    for shift in latest['schedule'][day].keys():
                        st.markdown(f"**🕒 {shift}**")
                        for task, people in latest['schedule'][day][shift].items():
                            people_text = ", ".join(people)
                            
                            pin_key = f"{day}_{shift}_{task}"
                            if "⚠️" in people_text:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 {task} ➔ <span style='color:red'>{people_text}</span>", unsafe_allow_html=True)
                            elif pin_key in st.session_state.pins and st.session_state.pins[pin_key]:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 {task} ➔ **{people_text}** *(📌 Ghim trước)*")
                            else:
                                East_tag = f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 {task} ➔ **{people_text}**"
                                st.markdown(East_tag)
                        st.write("")
                    
        with st.expander("📊 Biểu đồ thống kê khối lượng công việc tuần này (Tính công bằng)"):
            for name, info in st.session_state.members.items():
                st.write(f"- 👤 **{name}** đã được phân bổ: `{info['workload']}` ca trực/nhiệm vụ trong tuần.")