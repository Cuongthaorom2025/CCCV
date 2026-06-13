import streamlit as st
from datetime import datetime
import re

# Cấu hình hiển thị chuẩn di động & máy tính
st.set_page_config(page_title="Điều Phối Công Việc V6", page_icon="📆", layout="wide")

# Danh sách các ngày trong tuần cố định
DAYS_OF_WEEK = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

# ==========================================================
# KHỞI TẠO BỘ NHỚ HỆ THỐNG (SESSION STATE)
# ==========================================================
if "members" not in st.session_state:
    st.session_state.members = {
        "Anh Hải": {"excluded": [], "max": 15, "workload": 0, "history": []},
        "Chị Hoa": {"excluded": [], "max": 5, "workload": 0, "history": []},
        "Đức Tuấn": {"excluded": [], "max": 20, "workload": 0, "history": []}
    }

# Thay đổi cấu trúc: { "Tên công việc": ["Tên ca 1 (Giờ)", "Tên ca 2 (Giờ)"] }
if "tasks_with_shifts" not in st.session_state:
    st.session_state.tasks_with_shifts = {
        "Trực UAV": ["Ca 1 (7h30-11h)", "Ca 2 (13h30-17h)"],
        "Trực ban": ["Ca Sáng (08:00-12:00)", "Ca Đêm (22:00-06:00)"]
    }

if "day_offs" not in st.session_state:
    st.session_state.day_offs = {day: [] for day in DAYS_OF_WEEK}

# Lưu cấu hình ghim: { "Ngày_CôngViệc_Ca": [Danh sách người ghim] }
if "pins" not in st.session_state:
    st.session_state.pins = {}

if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================================
# GIAO DIỆN CHÍNH
# ==========================================================
st.title("📆 Hệ Thống Cắt Cử Công Việc Tự Động V6")
st.markdown(" *Phiên bản Đặc biệt: Tách biệt Ca/Giờ riêng cho từng Công việc — Tích hợp Trợ lý Ghim Văn Bản* ")

tab1, tab2, tab3 = st.tabs(["⚙️ Cơ Sở Dữ Liệu Gốc", "📅 Cấu Hình Ca & Ghim Việc", "🚀 Cắt Cử & Lịch Sử"])

# ------------------------------------------------------
# TAB 1: QUẢN LÝ THÀNH VIÊN & BIÊN SOẠN CÔNG VIỆC - CA
# ------------------------------------------------------
with tab1:
    col_left, col_right = st.columns(2)
    
    # --- 1. QUẢN LÝ NHÂN SỰ ---
    with col_left:
        st.subheader("👥 Danh Sách Nhân Sự")
        with st.expander("➕ Thêm nhân sự mới", expanded=False):
            m_name = st.text_input("Tên thành viên:")
            m_exclude = st.text_input("Việc không thể làm (cách nhau dấu phẩy):")
            m_max = st.number_input("Giới hạn việc/tuần:", min_value=1, value=10, key="m_max_v6")
            if st.button("Lưu nhân sự"):
                if m_name.strip():
                    excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
                    st.session_state.members[m_name.strip()] = {"excluded": excluded_list, "max": m_max, "workload": 0, "history": []}
                    st.rerun()
        
        st.write("---")
        for name, info in list(st.session_state.members.items()):
            c_info, c_del = st.columns([4, 1])
            c_info.markdown(f"👤 **{name}** \n<small>Cấm làm: {', '.join(info['excluded']) if info['excluded'] else 'Không'} | Tải tối đa: {info['max']} việc/tuần</small>", unsafe_allow_html=True)
            if c_del.button("❌", key=f"del_m_{name}"):
                del st.session_state.members[name]
                for d in DAYS_OF_WEEK:
                    if name in st.session_state.day_offs[d]: st.session_state.day_offs[d].remove(name)
                for k in list(st.session_state.pins.keys()):
                    st.session_state.pins[k] = [m for m in st.session_state.pins[k] if m != name]
                st.rerun()

    # --- 2. QUẢN LÝ MA TRẬN CÔNG VIỆC & CA RIÊNG ---
    with col_right:
        st.subheader("📌 Quản Lý Công Việc & Ca Trực")
        
        # Form 2a: Thêm Công việc mới
        with st.expander("➕ Tạo công việc mới", expanded=False):
            new_t_name = st.text_input("Tên công việc mới (Ví dụ: Trực UAV):")
            if st.button("Tạo công việc"):
                if new_t_name.strip() and new_t_name.strip() not in st.session_state.tasks_with_shifts:
                    st.session_state.tasks_with_shifts[new_t_name.strip()] = []
                    st.rerun()
                    
        # Form 2b: Thêm Ca/Giờ cho Công việc cụ thể
        if st.session_state.tasks_with_shifts:
            with st.expander("➕ Thêm ca trực cho Công việc", expanded=False):
                target_task = st.selectbox("Chọn công việc:", list(st.session_state.tasks_with_shifts.keys()))
                new_s_name = st.text_input("Tên ca & Giờ cụ thể (Ví dụ: Ca 1 (7h30-11h)):")
                if st.button("Thêm ca vào việc"):
                    if new_s_name.strip() and new_s_name.strip() not in st.session_state.tasks_with_shifts[target_task]:
                        st.session_state.tasks_with_shifts[target_task].append(new_s_name.strip())
                        st.rerun()

        st.write("---")
        st.markdown("**Cấu trúc Công việc - Ca trực hiện tại:**")
        for task, shifts in list(st.session_state.tasks_with_shifts.items()):
            with st.container(border=True):
                c_t_title, c_t_del = st.columns([4, 1])
                c_t_title.markdown(f"📂 **Nhiệm vụ: {task}**")
                
                if c_t_del.button("Xóa việc", key=f"del_t_{task}"):
                    del st.session_state.tasks_with_shifts[task]
                    st.session_state.pins = {k: v for k, v in st.session_state.pins.items() if f"_{task}_" not in k}
                    st.rerun()
                
                if not shifts:
                    st.caption("Chưa có ca trực nào cho việc này. Hãy thêm ca ở form trên.")
                else:
                    for shift in shifts:
                        c_s_title, c_s_del = st.columns([5, 1])
                        c_s_title.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift}")
                        if c_s_del.button("Xóa ca", key=f"del_s_{task}_{shift}"):
                            st.session_state.tasks_with_shifts[task].remove(shift)
                            st.session_state.pins = {k: v for k, v in st.session_state.pins.items() if f"_{task}_{shift}" not in k}
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
            
            # Chọn người bận nghỉ cả ngày
            valid_defaults = [m for m in st.session_state.day_offs[day] if m in st.session_state.members]
            st.session_state.day_offs[day] = st.multiselect(
                f"❌ Chọn người nghỉ (BẬN cả ngày) vào {day}:",
                options=list(st.session_state.members.keys()),
                default=valid_defaults,
                key=f"off_{day}"
            )
            
            st.write("---")
            
            # TRỢ LÝ GHIM TỐC HÀNH TỰ ĐỘNG KHỚP CẤU TRÚC MỚI
            st.markdown("### ⚡ Trợ lý Ghim Tốc Hành (Nhập nhanh văn bản)")
            st.caption("Cú pháp chuẩn: `Tên người - Tên việc - Tên ca` (Khoảng trống trước và sau dấu gạch ngang)")
            
            quick_input = st.text_input(
                "Nhập câu lệnh ghim nhanh:", 
                placeholder="Ví dụ đúng: Ánh - Trực UAV - Ca 1 (7h30-11h)", 
                key=f"text_input_{day}"
            )
            
            if st.button("🚀 Kích hoạt ghim nhanh", key=f"btn_quick_{day}"):
                if quick_input:
                    # Tách chuỗi né dấu gạch ngang viết liền của khung giờ (ví dụ: 7h30-11h)
                    parts = [p.strip() for p in re.split(r'[,;|]|\s+-\s+|\s+–\s+|\s+—\s+', quick_input) if p.strip()]
                    
                    if len(parts) == 3:
                        p_name, p_task, p_shift = parts[0], parts[1], parts[2]
                        
                        # Tự động tạo mới nếu chưa tồn tại trong hệ thống
                        if p_name not in st.session_state.members:
                            st.session_state.members[p_name] = {"excluded": [], "max": 10, "workload": 0, "history": []}
                            st.toast(f"Tự tạo nhân sự: {p_name}")
                        if p_task not in st.session_state.tasks_with_shifts:
                            st.session_state.tasks_with_shifts[p_task] = []
                            st.toast(f"Tự tạo công việc: {p_task}")
                        if p_shift not in st.session_state.tasks_with_shifts[p_task]:
                            st.session_state.tasks_with_shifts[p_task].append(p_shift)
                            st.toast(f"Tự bổ sung ca trực: {p_shift}")
                            
                        # Lưu dữ liệu ghim vào bộ nhớ máy
                        pin_key = f"{day}_{p_task}_{p_shift}"
                        if pin_key not in st.session_state.pins:
                            st.session_state.pins[pin_key] = []
                        if p_name not in st.session_state.pins[pin_key]:
                            st.session_state.pins[pin_key].append(p_name)
                            
                        st.success(f"🎉 Đã ghim thành công **{p_name}** vào việc **{p_task}**, ca **{p_shift}**")
                        st.rerun()
                    else:
                        st.error(f"⚠️ Nhập sai cú pháp! Hệ thống đếm được {len(parts)} phần. Cú pháp chuẩn phải có dấu cách: Người - Việc - Ca")

            st.write("---")
            st.markdown("#### 📌 Danh sách các vị trí cần phân bổ trong ngày:")
            
            if not st.session_state.tasks_with_shifts:
                st.caption("Chưa cấu hình Công việc & Ca trực nào ở Tab 1.")
            else:
                for task, shifts in st.session_state.tasks_with_shifts.items():
                    if shifts:
                        st.markdown(f"📂 **Nhiệm vụ: {task}**")
                        for shift in shifts:
                            pin_key = f"{day}_{task}_{shift}"
                            is_pinned = pin_key in st.session_state.pins and st.session_state.pins[pin_key]
                            
                            c_s_view, c_s_act = st.columns([4, 1])
                            if is_pinned:
                                p_people = ", ".join(st.session_state.pins[pin_key])
                                c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 📌 Ghim đích danh: **{p_people}**")
                                if  c_s_act.button("Hủy ghim", key=f"unpin_{pin_key}"):
                                    del st.session_state.pins[pin_key]
                                    st.rerun()
                            else:
                                c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 🤖 *Hệ thống tự động chia*")
                        st.write("")

# ------------------------------------------------------
# TAB 3: TIẾN HÀNH ĐIỀU PHỐI TỰ ĐỘNG & XEM KẾT QUẢ
# ------------------------------------------------------
with tab3:
    st.subheader("⚡ Thực thi thuật toán cắt cử thông minh")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        run_v6 = st.button("🚀 TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN", type="primary", use_container_width=True)
    with c_btn2:
        clear_log = st.button("🗑️ Xóa sạch lịch sử", use_container_width=True)
        
    if clear_log:
        st.session_state.history = []
        st.success("Đã xóa nhật ký lịch sử thành công!")
        st.rerun()

    if run_v6:
        if not st.session_state.members or not st.session_state.tasks_with_shifts:
            st.error("Thiếu dữ liệu cấu hình gốc để chạy!")
        else:
            # Reset tải công việc tuần này về 0 để tính toán độ công bằng từ đầu đợt
            for name in st.session_state.members:
                st.session_state.members[name]['workload'] = 0
            
            week_schedule = {}
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            for day in DAYS_OF_WEEK:
                week_schedule[day] = {}
                busy_day_people = st.session_state.day_offs[day]
                
                # Bộ nhớ theo dõi chống trùng lịch theo ngày: { "Tên người": set(["Tên ca trực"]) }
                # Một người không thể làm 2 việc khác nhau có cùng tên ca/khung giờ trong một ngày
                assigned_time_slots_today = {name: set() for name in st.session_state.members}
                
                # Khởi tạo khung lịch trống cho ngày
                for task, shifts in st.session_state.tasks_with_shifts.items():
                    week_schedule[day][task] = {shift: [] for shift in shifts}
                    
                # BƯỚC 1: ƯU TIÊN ĐIỀN CÁC LỆNH GHIM TRƯỚC
                for task, shifts in st.session_state.tasks_with_shifts.items():
                    for shift in shifts:
                        pin_key = f"{day}_{task}_{shift}"
                        if pin_key in st.session_state.pins:
                            for member in st.session_state.pins[pin_key]:
                                if member in st.session_state.members:
                                    week_schedule[day][task][shift].append(member)
                                    st.session_state.members[member]['workload'] += 1
                                    st.session_state.members[member]['history'].append(f"{day} - {task}: {shift} (Ghim)")
                                    assigned_time_slots_today[member].add(shift) # Khóa khung giờ ca này của người đó lại
                                    
                # BƯỚC 2: TỰ ĐỘNG ĐIỀU PHỐI CÁC CA CÒN TRỐNG NGƯỜI
                for task, shifts in st.session_state.tasks_with_shifts.items():
                    for shift in shifts:
                        # Nếu ca trực này của nhiệm vụ này chưa có ai làm (không bị ghim trước)
                        if not week_schedule[day][task][shift]:
                            eligible_members = []
                            for name, info in st.session_state.members.items():
                                # ĐIỀU KIỆN NHẬN VIỆC TỰ ĐỘNG:
                                if (name not in busy_day_people and                       # 1. Không nghỉ ngày này
                                    shift not in assigned_time_slots_today[name] and      # 2. CHỐNG TRÙNG: Ca trực này giờ này chưa bận việc khác
                                    task not in info['excluded'] and                      # 3. Không thuộc danh sách cấm của người đó
                                    info['workload'] < info['max']):                      # 4. Chưa vượt tải giới hạn tuần
                                    eligible_members.append(name)
                                    
                            if not eligible_members:
                                week_schedule[day][task][shift].append("⚠️ Không ai đủ điều kiện")
                                continue
                            
                            # ĐẢM BẢO CÔNG BẰNG: Chọn người có lượng workload tích lũy trong tuần thấp nhất tại thời điểm đó
                            eligible_members.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                            chosen = eligible_members[0]
                            
                            # Giao việc tự động
                            week_schedule[day][task][shift].append(chosen)
                            st.session_state.members[chosen]['workload'] += 1
                            st.session_state.members[chosen]['history'].append(f"{day} - {task}: {shift}")
                            assigned_time_slots_today[chosen].add(shift) # Khóa khung giờ ca này lại
                            
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
            if day in latest['schedule']:
                with st.expander(f"📅 LỊCH CÔNG TÁC: {day}", expanded=True):
                    for task, shifts_dict in latest['schedule'][day].items():
                        st.markdown(f"📂 **Nhiệm vụ: {task}**")
                        for shift, people in shifts_dict.items():
                            people_text = ", ".join(people)
                            
                            pin_key = f"{day}_{task}_{shift}"
                            if "⚠️" in people_text:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ <span style='color:red'>{people_text}</span>", unsafe_allow_html=True)
                            elif pin_key in st.session_state.pins and st.session_state.pins[pin_key]:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ **{people_text}** *(📌 Ghim trước)*")
                            else:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ **{people_text}**")
                        st.write("")
                    
        with st.expander("📊 Thống kê khối lượng công việc tuần này (Tính công bằng)"):
            for name, info in st.session_state.members.items():
                st.write(f"- 👤 **{name}** đã được phân bổ: `{info['workload']}` ca trực/nhiệm vụ trong tuần.")
