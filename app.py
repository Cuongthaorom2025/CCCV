import streamlit as st
from datetime import datetime
import re

# Cấu hình hiển thị chuẩn di động & máy tính
st.set_page_config(page_title="Điều Phối Công Việc V7", page_icon="📆", layout="wide")

# Danh sách các ngày trong tuần cố định
DAYS_OF_WEEK = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

# ==========================================================
# KHỞI TẠO BỘ NHỚ HỆ THỐNG (SESSION STATE)
# ==========================================================
if "members" not in st.session_state:
    st.session_state.members = {
        "Ánh": {"excluded": [], "max": 10, "workload": 0, "history": []},
        "Anh Hải": {"excluded": [], "max": 15, "workload": 0, "history": []},
        "Chị Hoa": {"excluded": [], "max": 5, "workload": 0, "history": []},
        "Đức Tuấn": {"excluded": [], "max": 20, "workload": 0, "history": []}
    }

if "tasks_with_shifts" not in st.session_state:
    st.session_state.tasks_with_shifts = {
        "Trực UAV": ["Ca 1 (7h30-11h)", "Ca 2 (13h30-17h)"],
        "Trực ban": ["Ca Sáng (08:00-12:00)", "Ca Đêm (22:00-06:00)"]
    }

if "day_offs" not in st.session_state:
    st.session_state.day_offs = {day: [] for day in DAYS_OF_WEEK}

if "pins" not in st.session_state:
    st.session_state.pins = {}

if "history" not in st.session_state:
    st.session_state.history = []


# ==========================================================
# HÀM BỔ TRỢ THỜI GIAN ĐỂ TÍNH TOÁN QUY TẮC NÂNG CAO
# ==========================================================
def parse_shift_bounds(shift_str, day_idx):
    """Bóc tách text giờ (7h30-11h) thành mốc thời gian tuyến tính để tính toán"""
    parts = re.split(r'[-–—to]', shift_str)
    start_t, end_t = 0.0, 0.0
    
    if len(parts) >= 2:
        def extract_time(text):
            match = re.search(r'(\d{1,2})[h:](\d{2})', text)
            if match: return int(match.group(1)) + int(match.group(2)) / 60.0
            match = re.search(r'(\d{1,2})\s*h', text)
            if match: return float(match.group(1))
            numbers = re.findall(r'\d+', text)
            if numbers: return float(numbers[-1])
            return 0.0
        
        start_t = extract_time(parts[0])
        end_t = extract_time(parts[1])
        
    abs_start = day_idx * 24.0 + start_t
    # Xử lý ca xuyên đêm (Ví dụ: 22h - 6h sáng hôm sau)
    abs_end = day_idx * 24.0 + end_t + (24.0 if end_t < start_t else 0.0)
    return start_t, end_t, abs_start, abs_end


def check_24h_violation(existing_tracks, new_slot):
    """Quy tắc 2: Kiểm tra xem trong vòng 24h bất kỳ có bị gác quá 2 ca không"""
    all_slots = existing_tracks + [new_slot]
    all_slots.sort(key=lambda x: x["abs_start"])
    
    for slot_x in all_slots:
        window_start = slot_x["abs_start"]
        window_end = window_start + 24.0
        
        # Đếm số ca bắt đầu nằm gọn trong cửa sổ 24 giờ này
        count = sum(1 for slot_y in all_slots if window_start <= slot_y["abs_start"] < window_end)
        if count > 2:
            return True
    return False


# ==========================================================
# GIAO DIỆN CHÍNH
# ==========================================================
st.title("📆 Hệ Thống Cắt Cử Công Việc Tự Động V7")
st.markdown(" *Cập nhật tối ưu: Chống trực ca liên tục & Chặn gác quá 2 ca trong vòng 24H rolling-time* ")

tab1, tab2, tab3 = st.tabs(["⚙️ Cơ Sở Dữ Liệu Gốc", "📅 Cấu Hình Ca & Ghim Việc", "🚀 Cắt Cử & Lịch Sử"])

# ------------------------------------------------------
# TAB 1: QUẢN LÝ THÀNH VIÊN & BIÊN SOẠN CÔNG VIỆC
# ------------------------------------------------------
with tab1:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("👥 Danh Sách Nhân Sự")
        with st.expander("➕ Thêm nhân sự mới", expanded=False):
            m_name = st.text_input("Tên thành viên:")
            m_exclude = st.text_input("Việc không thể làm (cách nhau dấu phẩy):")
            m_max = st.number_input("Giới hạn việc/tuần:", min_value=1, value=10, key="m_max_v7")
            if st.button("Lưu nhân sự"):
                if m_name.strip():
                    excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
                    st.session_state.members[m_name.strip()] = {"excluded": excluded_list, "max": m_max, "workload": 0, "history": []}
                    st.rerun()
        
        st.write("---")
        for name, info in list(st.session_state.members.items()):
            c_info, c_del = st.columns([4, 1])
            c_info.markdown(f"👤 **{name}** \n<small>Cấm làm: {', '.join(info['excluded']) if info['excluded'] else 'Không'} | Tối đa: {info['max']} việc/tuần</small>", unsafe_allow_html=True)
            if c_del.button("❌", key=f"del_m_{name}"):
                del st.session_state.members[name]
                for d in DAYS_OF_WEEK:
                    if name in st.session_state.day_offs[d]: st.session_state.day_offs[d].remove(name)
                for k in list(st.session_state.pins.keys()):
                    st.session_state.pins[k] = [m for m in st.session_state.pins[k] if m != name]
                st.rerun()

    with col_right:
        st.subheader("📌 Quản Lý Công Việc & Ca Trực")
        with st.expander("➕ Tạo công việc mới", expanded=False):
            new_t_name = st.text_input("Tên công việc mới (Ví dụ: Trực UAV):")
            if st.button("Tạo công việc"):
                if new_t_name.strip() and new_t_name.strip() not in st.session_state.tasks_with_shifts:
                    st.session_state.tasks_with_shifts[new_t_name.strip()] = []
                    st.rerun()
                    
        if st.session_state.tasks_with_shifts:
            with st.expander("➕ Thêm ca trực cho Công việc", expanded=False):
                target_task = st.selectbox("Chọn công việc:", list(st.session_state.tasks_with_shifts.keys()))
                new_s_name = st.text_input("Tên ca & Giờ cụ thể (Ví dụ: Ca 1 (7h30-11h)):")
                if st.button("Thêm ca vào việc"):
                    if new_s_name.strip() and new_s_name.strip() not in st.session_state.tasks_with_shifts[target_task]:
                        st.session_state.tasks_with_shifts[target_task].append(new_s_name.strip())
                        st.rerun()

        st.write("---")
        for task, shifts in list(st.session_state.tasks_with_shifts.items()):
            with st.container(border=True):
                c_t_title, c_t_del = st.columns([4, 1])
                c_t_title.markdown(f"📂 **Nhiệm vụ: {task}**")
                if c_t_del.button("Xóa việc", key=f"del_t_{task}"):
                    del st.session_state.tasks_with_shifts[task]
                    st.session_state.pins = {k: v for k, v in st.session_state.pins.items() if f"_{task}_" not in k}
                    st.rerun()
                
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
            
            valid_defaults = [m for m in st.session_state.day_offs[day] if m in st.session_state.members]
            st.session_state.day_offs[day] = st.multiselect(
                f"❌ Chọn người nghỉ (BẬN cả ngày) vào {day}:",
                options=list(st.session_state.members.keys()),
                default=valid_defaults,
                key=f"off_{day}"
            )
            
            st.write("---")
            st.markdown("### ⚡ Trợ lý Ghim Tốc Hành (Nhập nhanh văn bản)")
            st.caption("Cú pháp chuẩn di động: `Tên người - Tên việc - Tên ca`")
            
            quick_input = st.text_input(
                "Nhập câu lệnh ghim nhanh:", 
                placeholder="Ví dụ: Ánh - Trực UAV - Ca 1 (7h30-11h)", 
                key=f"text_input_{day}"
            )
            
            if st.button("🚀 Kích hoạt ghim nhanh", key=f"btn_quick_{day}"):
                if quick_input:
                    parts = [p.strip() for p in re.split(r'[,;|]|\s+-\s+|\s+–\s+|\s+—\s+', quick_input) if p.strip()]
                    if len(parts) == 3:
                        p_name, p_task, p_shift = parts[0], parts[1], parts[2]
                        
                        if p_name not in st.session_state.members:
                            st.session_state.members[p_name] = {"excluded": [], "max": 10, "workload": 0, "history": []}
                        if p_task not in st.session_state.tasks_with_shifts:
                            st.session_state.tasks_with_shifts[p_task] = []
                        if p_shift not in st.session_state.tasks_with_shifts[p_task]:
                            st.session_state.tasks_with_shifts[p_task].append(p_shift)
                            
                        pin_key = f"{day}_{p_task}_{p_shift}"
                        if pin_key not in st.session_state.pins: st.session_state.pins[pin_key] = []
                        if p_name not in st.session_state.pins[pin_key]: st.session_state.pins[pin_key].append(p_name)
                        st.success(f"🎉 Đã ghi nhận lệnh ghim trước!")
                        st.rerun()
                    else:
                        st.error("⚠️ Sai cú pháp! Vui lòng dùng dấu cách hai bên dấu gạch ngang: Người - Việc - Ca")

            st.write("---")
            st.markdown("#### 📌 Cấu hình ghim hiển thị hiện tại:")
            for task, shifts in st.session_state.tasks_with_shifts.items():
                if shifts:
                    st.markdown(f"📂 **Nhiệm vụ: {task}**")
                    for shift in shifts:
                        pin_key = f"{day}_{task}_{shift}"
                        is_pinned = pin_key in st.session_state.pins and st.session_state.pins[pin_key]
                        c_s_view, c_s_act = st.columns([4, 1])
                        if is_pinned:
                            p_people = ", ".join(st.session_state.pins[pin_key])
                            c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 📌 Ghim: **{p_people}**")
                            if c_s_act.button("Hủy ghim", key=f"unpin_{pin_key}"):
                                del st.session_state.pins[pin_key]
                                st.rerun()
                        else:
                            c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 🤖 *Hệ thống tự động chia*")

# ------------------------------------------------------
# TAB 3: TIẾN HÀNH ĐIỀU PHỐI TỰ ĐỘNG & XEM KẾT QUẢ
# ------------------------------------------------------
with tab3:
    st.subheader("⚡ Thực thi thuật toán cắt cử thông minh V7")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        run_v7 = st.button("🚀 TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN", type="primary", use_container_width=True)
    with c_btn2:
        clear_log = st.button("🗑️ Xóa sạch lịch sử", use_container_width=True)
        
    if clear_log:
        st.session_state.history = []
        st.success("Đã xóa nhật ký lịch sử thành công!")
        st.rerun()

    if run_v7:
        if not st.session_state.members or not st.session_state.tasks_with_shifts:
            st.error("Thiếu dữ liệu cấu hình gốc để chạy!")
        else:
            for name in st.session_state.members:
                st.session_state.members[name]['workload'] = 0
            
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            # Khởi tạo danh sách phẳng chứa tất cả các slot cần xếp trong tuần
            flat_slots = []
            for d_idx, day in enumerate(DAYS_OF_WEEK):
                for task, shifts in st.session_state.tasks_with_shifts.items():
                    for shift in shifts:
                        start_t, end_t, abs_start, abs_end = parse_shift_bounds(shift, d_idx)
                        flat_slots.append({
                            "day_idx": d_idx, "day_name": day, "task": task, "shift": shift,
                            "start": start_t, "end": end_t, "abs_start": abs_start, "abs_end": abs_end,
                            "assigned_people": []
                        })
            
            # Bộ theo dõi dòng thời gian làm việc thực tế của từng người trong phiên này
            member_tracks = {name: [] for name in st.session_state.members}
            
            # --- BƯỚC 1: ĐIỀN TOÀN BỘ CÁC LỆNH GHIM TRƯỚC VÀO TIMELINE ---
            for slot in flat_slots:
                pin_key = f"{slot['day_name']}_{slot['task']}_{slot['shift']}"
                if pin_key in st.session_state.pins:
                    for member in st.session_state.pins[pin_key]:
                        if member in st.session_state.members:
                            slot["assigned_people"].append(member)
                            st.session_state.members[member]['workload'] += 1
                            st.session_state.members[member]['history'].append(f"{slot['day_name']} - {slot['task']}: {slot['shift']} (Ghim)")
                            member_tracks[member].append({
                                "abs_start": slot["abs_start"], "abs_end": slot["abs_end"], "day_idx": slot["day_idx"]
                            })
                            
            # --- BƯỚC 2: SẮP XẾP TOÀN BỘ SLOT TRỐNG THEO THỨ TỰ THỜI GIAN ĐỂ CHIA TỰ ĐỘNG ---
            flat_slots.sort(key=lambda x: (x["day_idx"], x["abs_start"]))
            
            for slot in flat_slots:
                if not slot["assigned_people"]:
                    busy_day_people = st.session_state.day_offs[slot["day_name"]]
                    eligible_members = []
                    
                    for name, info in st.session_state.members.items():
                        if name in busy_day_people: continue
                        if slot["task"] in info["excluded"]: continue
                        if info["workload"] >= info["max"]: continue
                        
                        # QUY TẮC 1: Không gác 2 ca liên tục (Liền kề/Sát sườn nhau)
                        is_consecutive = False
                        for track in member_tracks[name]:
                            if abs(track["abs_end"] - slot["abs_start"]) < 0.01 or abs(slot["abs_end"] - track["abs_start"]) < 0.01:
                                is_consecutive = True
                                break
                        if is_consecutive: continue
                        
                        # QUY TẮC 2: Không gác quá 2 ca trong vòng một cửa sổ 24H bất kỳ
                        if check_24h_violation(member_tracks[name], slot): continue
                        
                        eligible_members.append(name)
                        
                    if not eligible_members:
                        slot["assigned_people"].append("⚠️ Không ai đủ điều kiện")
                        continue
                    
                    # Đảm bảo công bằng: Ưu tiên người ít việc nhất tuần hiện tại
                    eligible_members.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                    chosen = eligible_members[0]
                    
                    # Cập nhật kết quả vào dòng thời gian của người đó
                    slot["assigned_people"].append(chosen)
                    st.session_state.members[chosen]['workload'] += 1
                    st.session_state.members[chosen]['history'].append(f"{slot['day_name']} - {slot['task']}: {slot['shift']}")
                    member_tracks[chosen].append({
                        "abs_start": slot["abs_start"], "abs_end": slot["abs_end"], "day_idx": slot["day_idx"]
                    })
            
            # Đóng gói danh sách phẳng thành cấu trúc Ma trận tuần để hiển thị lên UI
            week_schedule = {}
            for day in DAYS_OF_WEEK:
                week_schedule[day] = {}
                for task, shifts in st.session_state.tasks_with_shifts.items():
                    week_schedule[day][task] = {shift: [] for shift in shifts}
            for slot in flat_slots:
                if slot["day_name"] in week_schedule and slot["task"] in week_schedule[slot["day_name"]]:
                    week_schedule[slot["day_name"]][slot["task"]][slot["shift"]] = slot["assigned_people"]
                    
            st.session_state.history.append({"time": timestamp, "schedule": week_schedule})
            st.rerun()

    # --- HIỂN THỊ KẾT QUẢ MỚI NHẤT ---
    st.write("---")
    if not st.session_state.history:
        st.info("💡 Hệ thống đang sẵn sàng. Hãy bấm nút 'TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN' để nhận lịch.")
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
