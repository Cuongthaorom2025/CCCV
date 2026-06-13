import streamlit as st
from datetime import datetime
import re

# Cấu hình hiển thị chuẩn giao diện Dashboard
st.set_page_config(page_title="Lịch Điều Phối Trực Quan V9", page_icon="📅", layout="wide")

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

if "rules" not in st.session_state:
    st.session_state.rules = {
        "block_consecutive": True,        
        "max_shifts_in_window": 2,        
        "window_hours": 24.0,             
        "min_rest_hours": 2.0,            
        "anti_pairs": []                  
    }

if "day_offs" not in st.session_state:
    st.session_state.day_offs = {day: [] for day in DAYS_OF_WEEK}

if "pins" not in st.session_state:
    st.session_state.pins = {}

if "history" not in st.session_state:
    st.session_state.history = []


# ==========================================================
# THƯ VIỆN LOGIC XỬ LÝ THỜI GIAN TUYẾN TÍNH
# ==========================================================
def parse_shift_bounds(shift_str, day_idx):
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
    abs_end = day_idx * 24.0 + end_t + (24.0 if end_t < start_t else 0.0)
    return start_t, end_t, abs_start, abs_end

def validate_custom_rules(name, slot, member_tracks, current_shift_people, rules):
    new_start = slot["abs_start"]
    new_end = slot["abs_end"]
    tracks = member_tracks[name]
    
    for t in tracks:
        if rules["block_consecutive"]:
            if abs(t["abs_end"] - new_start) < 0.01 or abs(new_end - t["abs_start"]) < 0.01:
                return False
        if rules["min_rest_hours"] > 0:
            if new_start >= t["abs_end"]:
                if (new_start - t["abs_end"]) < rules["min_rest_hours"]: return False
            elif t["abs_start"] >= new_end:
                if (t["abs_start"] - new_end) < rules["min_rest_hours"]: return False

    all_slots = tracks + [{"abs_start": new_start, "abs_end": new_end}]
    for s_x in all_slots:
        w_start = s_x["abs_start"]
        w_end = w_start + rules["window_hours"]
        count = sum(1 for s_y in all_slots if w_start <= s_y["abs_start"] < w_end)
        if count > rules["max_shifts_in_window"]:
            return False

    for p1, p2 in rules["anti_pairs"]:
        if name == p1 and p2 in current_shift_people: return False
        if name == p2 and p1 in current_shift_people: return False
    return True


# ==========================================================
# STYLE CSS CHO BẢNG LỊCH TRỰC QUAN (INJECTED HTML)
# ==========================================================
CALENDAR_CSS = """
<style>
    .calendar-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-radius: 8px;
        overflow: hidden;
    }
    .calendar-table th {
        background-color: #2F4F4F;
        color: white;
        text-align: center;
        padding: 12px;
        font-weight: 600;
        border: 1px solid #444;
    }
    .calendar-table td {
        border: 1px solid #e0e0e0;
        padding: 10px;
        vertical-align: top;
        background-color: #ffffff;
        min-width: 120px;
    }
    .row-task-title {
        background-color: #f5f5f5 !important;
        font-weight: bold;
        color: #333;
    }
    .badge {
        display: inline-block;
        padding: 4px 8px;
        margin: 3px 2px;
        border-radius: 4px;
        font-size: 13px;
        font-weight: 500;
        text-align: center;
    }
    .badge-pin { background-color: #D1E8FF; color: #004085; border: 1px solid #b8daff; }
    .badge-auto { background-color: #D4EDDA; color: #155724; border: 1px solid #c3e6cb; }
    .badge-danger { background-color: #F8D7DA; color: #721C24; border: 1px solid #f5c6cb; font-weight: bold; }
    .badge-fade { opacity: 0.25; background-color: #f0f0f0; color: #999; border: 1px solid #ddd; }
    .badge-highlight { 
        background-color: #FFDF00 !important; 
        color: #000 !important; 
        font-weight: bold !important;
        box-shadow: 0 0 8px rgba(255,223,0,0.8);
        transform: scale(1.05);
    }
</style>
"""
st.markdown(CALENDAR_CSS, unsafe_allow_html=True)

# ==========================================================
# GIAO DIỆN ĐIỀU HÀNH CHÍNH
# ==========================================================
st.title("📆 Hệ Thống Cắt Cử Điều Phối Trực Quan V9")
st.markdown(" *Bản thiết kế tối cao: Ma trận lịch tuần trực quan, tích hợp bộ lọc tìm kiếm cá nhân* ")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Nhân Sự & Việc Gốc", "🛠️ Thiết Lập Luật Cắt", "📅 Cấu Hình Ngày & Ghim Tốc Hành", "🚀 Bảng Lịch Trực Quan"])

# ------------------------------------------------------
# TAB 1: QUẢN LÝ DỮ LIỆU NHÂN SỰ VÀ ĐẦU VIỆC GỐC
# ------------------------------------------------------
with tab1:
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("👥 Danh Sách Nhân Sự")
        with st.expander("➕ Thêm nhân sự mới", expanded=False):
            m_name = st.text_input("Tên thành viên:")
            m_exclude = st.text_input("Việc không thể làm (cách nhau dấu phẩy):")
            m_max = st.number_input("Giới hạn việc/tuần:", min_value=1, value=10)
            if st.button("Lưu nhân sự"):
                if m_name.strip():
                    excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
                    st.session_state.members[m_name.strip()] = {"excluded": excluded_list, "max": m_max, "workload": 0, "history": []}
                    st.rerun()
        st.write("---")
        for name, info in list(st.session_state.members.items()):
            c_info, c_del = st.columns([4, 1])
            c_info.markdown(f"👤 **{name}** \n<small>Cấm làm: {', '.join(info['excluded']) if info['excluded'] else 'Không'} | Tối đa: {info['max']} ca/tuần</small>", unsafe_allow_html=True)
            if c_del.button("❌", key=f"del_m_{name}"):
                del st.session_state.members[name]
                st.rerun()

    with col_right:
        st.subheader("📌 Quản Lý Công Việc & Ca Trực")
        with st.expander("➕ Tạo công việc mới", expanded=False):
            new_t_name = st.text_input("Tên công việc mới:")
            if st.button("Tạo công việc"):
                if new_t_name.strip() and new_t_name.strip() not in st.session_state.tasks_with_shifts:
                    st.session_state.tasks_with_shifts[new_t_name.strip()] = []
                    st.rerun()
        if st.session_state.tasks_with_shifts:
            with st.expander("➕ Thêm ca trực cho Công việc", expanded=False):
                target_task = st.selectbox("Chọn công việc hành mục:", list(st.session_state.tasks_with_shifts.keys()))
                new_s_name = st.text_input("Tên ca & Khung giờ (Ví dụ: Ca 1 (7h30-11h)):")
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
                    st.rerun()
                for shift in shifts:
                    c_s_title, c_s_del = st.columns([5, 1])
                    c_s_title.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift}")
                    if c_s_del.button("Xóa ca", key=f"del_s_{task}_{shift}"):
                        st.session_state.tasks_with_shifts[task].remove(shift)
                        st.rerun()

# ------------------------------------------------------
# TAB 2: QUẢN LÝ CÁC ĐIỀU KIỆN & QUY TẮC CẮT CỬ ĐỘNG
# ------------------------------------------------------
with tab2:
    st.subheader("🛠️ Cấu Hình Các Quy Tắc Điều Phối Hệ Thống")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.session_state.rules["block_consecutive"] = st.checkbox("🔒 Chống gác 2 ca liên tiếp sát nhau", value=st.session_state.rules["block_consecutive"])
        st.session_state.rules["min_rest_hours"] = st.number_input("⏱️ Khoảng thời gian nghỉ tối thiểu giữa 2 ca trực (Giờ):", min_value=0.0, max_value=12.0, value=st.session_state.rules["min_rest_hours"], step=0.5)
    with col_r2:
        st.session_state.rules["max_shifts_in_window"] = st.number_input("🛡️ Số ca trực tối đa được phép gác trong chu kỳ:", min_value=1, max_value=5, value=st.session_state.rules["max_shifts_in_window"])
        st.session_state.rules["window_hours"] = st.number_input("⏳ Độ dài chu kỳ rolling-time (Giờ):", min_value=1.0, max_value=48.0, value=st.session_state.rules["window_hours"], step=1.0)
        
    st.write("---")
    st.markdown("### 👥 Quy tắc Cặp nhân sự chống đứng chung ca")
    if len(st.session_state.members) >= 2:
        with st.form("form_anti_pair"):
            p1 = st.selectbox("Nhân sự thứ nhất:", list(st.session_state.members.keys()), key="ap_p1")
            p2 = st.selectbox("Nhân sự thứ hai:", list(st.session_state.members.keys()), key="ap_p2")
            if st.form_submit_button("➕ Thêm quy tắc chặn cặp này") and p1 != p2:
                pair = (p1, p2) if p1 < p2 else (p2, p1)
                if pair not in st.session_state.rules["anti_pairs"]:
                    st.session_state.rules["anti_pairs"].append(pair)
                    st.rerun()
        for pair in list(st.session_state.rules["anti_pairs"]):
            c_p_txt, c_p_del = st.columns([4, 1])
            c_p_txt.write(f"🚫 Tuyệt đối không xếp chung ca: **{pair[0]}** và **{pair[1]}**")
            if c_p_del.button("Hủy bỏ chặn", key=f"del_ap_{pair[0]}_{pair[1]}"):
                st.session_state.rules["anti_pairs"].remove(pair)
                st.rerun()

# ------------------------------------------------------
# TAB 3: THIẾT LẬP THEO NGÀY & TRỢ LÝ GHIM TỐC HÀNH
# ------------------------------------------------------
with tab3:
    st.subheader("📅 Thiết lập đặc thù & Ghim việc theo ngày")
    day_tabs = st.tabs(DAYS_OF_WEEK)
    for idx, day in enumerate(DAYS_OF_WEEK):
        with day_tabs[idx]:
            st.markdown(f"### 🛠️ Cài đặt cho **{day}**")
            valid_defaults = [m for m in st.session_state.day_offs[day] if m in st.session_state.members]
            st.session_state.day_offs[day] = st.multiselect(f"❌ Chọn người nghỉ (BẬN cả ngày) vào {day}:", options=list(st.session_state.members.keys()), default=valid_defaults, key=f"off_{day}")
            
            st.write("---")
            st.markdown("### ⚡ Trợ lý Ghim Tốc Hành (Nhập nhanh văn bản)")
            st.caption("Cú pháp: `Tên người - Tên việc - Tên ca` (Né được dấu gạch nối thời gian dạng 7h30-11h)")
            quick_input = st.text_input("Nhập lệnh ghim nhanh:", placeholder="Ví dụ: Ánh - Trực UAV - Ca 1 (7h30-11h)", key=f"text_input_{day}")
            
            if st.button("🚀 Kích hoạt ghim", key=f"btn_quick_{day}"):
                if quick_input:
                    parts = [p.strip() for p in re.split(r'[,;|]|\s+-\s+|\s+–\s+|\s+—\s+', quick_input) if p.strip()]
                    if len(parts) == 3:
                        p_name, p_task, p_shift = parts[0], parts[1], parts[2]
                        if p_name not in st.session_state.members: st.session_state.members[p_name] = {"excluded": [], "max": 10, "workload": 0, "history": []}
                        if p_task not in st.session_state.tasks_with_shifts: st.session_state.tasks_with_shifts[p_task] = []
                        if p_shift not in st.session_state.tasks_with_shifts[p_task]: st.session_state.tasks_with_shifts[p_task].append(p_shift)
                        
                        pin_key = f"{day}_{p_task}_{p_shift}"
                        if pin_key not in st.session_state.pins: st.session_state.pins[pin_key] = []
                        if p_name not in st.session_state.pins[pin_key]: st.session_state.pins[pin_key].append(p_name)
                        st.rerun()

            st.write("---")
            for task, shifts in st.session_state.tasks_with_shifts.items():
                if shifts:
                    st.markdown(f"📂 **Nhiệm vụ: {task}**")
                    for shift in shifts:
                        pin_key = f"{day}_{task}_{shift}"
                        is_pinned = pin_key in st.session_state.pins and st.session_state.pins[pin_key]
                        c_s_view, c_s_act = st.columns([4, 1])
                        if is_pinned:
                            c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 📌 Ghim: **{', '.join(st.session_state.pins[pin_key])}**")
                            if c_s_act.button("Hủy ghim", key=f"unpin_{pin_key}"):
                                del st.session_state.pins[pin_key]
                                st.rerun()
                        else:
                            c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 🤖 *Tự động chia*")

# ------------------------------------------------------
# 🔥 TAB 4: THỰC THI THUẬT TOÁN & BẢNG LỊCH TRỰC QUAN (MỚI)
# ------------------------------------------------------
with tab4:
    st.subheader("⚡ Bản Đồ Lịch Trực Phân Phối Toàn Diện")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        run_v9 = st.button("🚀 BẮT ĐẦU TỰ ĐỘNG CẮT CỬ ĐỀU", type="primary", use_container_width=True)
    with c_btn2:
        if st.button("🗑️ Xóa sạch lịch sử log", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    if run_v9:
        if not st.session_state.members or not st.session_state.tasks_with_shifts:
            st.error("Thiếu cơ sở dữ liệu để chạy điều phối lịch!")
        else:
            for name in st.session_state.members: st.session_state.members[name]['workload'] = 0
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            flat_slots = []
            for d_idx, day in enumerate(DAYS_OF_WEEK):
                for task, shifts in st.session_state.tasks_with_shifts.items():
                    for shift in shifts:
                        _, _, abs_start, abs_end = parse_shift_bounds(shift, d_idx)
                        flat_slots.append({
                            "day_idx": d_idx, "day_name": day, "task": task, "shift": shift,
                            "abs_start": abs_start, "abs_end": abs_end, "assigned_people": []
                        })
            
            member_tracks = {name: [] for name in st.session_state.members}
            
            # ĐIỀN LỆNH GHIM TRƯỚC
            for slot in flat_slots:
                pin_key = f"{slot['day_name']}_{slot['task']}_{slot['shift']}"
                if pin_key in st.session_state.pins:
                    for member in st.session_state.pins[pin_key]:
                        if member in st.session_state.members:
                            slot["assigned_people"].append(member)
                            st.session_state.members[member]['workload'] += 1
                            member_tracks[member].append({"abs_start": slot["abs_start"], "abs_end": slot["abs_end"]})
            
            flat_slots.sort(key=lambda x: (x["day_idx"], x["abs_start"]))
            
            # TỰ ĐỘNG CHIA ĐỀU BẰNG BỘ LỌC ĐỘNG
            for slot in flat_slots:
                if not slot["assigned_people"]:
                    busy_day_people = st.session_state.day_offs[slot["day_name"]]
                    eligible_members = []
                    
                    current_shift_people = []
                    for s_check in flat_slots:
                        if s_check["day_idx"] == slot["day_idx"] and abs(s_check["abs_start"] - slot["abs_start"]) < 0.01:
                            current_shift_people.extend(s_check["assigned_people"])
                    
                    for name, info in st.session_state.members.items():
                        if name in busy_day_people or slot["task"] in info["excluded"] or info["workload"] >= info["max"]: continue
                        
                        is_overlapping = False
                        for track in member_tracks[name]:
                            if not (slot["abs_end"] <= track["abs_start"] or slot["abs_start"] >= track["abs_end"]):
                                is_overlapping = True; break
                        if is_overlapping: continue
                        
                        if not validate_custom_rules(name, slot, member_tracks, current_shift_people, st.session_state.rules): continue
                        eligible_members.append(name)
                        
                    if not eligible_members:
                        slot["assigned_people"].append("⚠️ Trống")
                        continue
                    
                    eligible_members.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                    chosen = eligible_members[0]
                    slot["assigned_people"].append(chosen)
                    st.session_state.members[chosen]['workload'] += 1
                    member_tracks[chosen].append({"abs_start": slot["abs_start"], "abs_end": slot["abs_end"]})
            
            # Đóng gói dữ liệu lịch tuần
            week_schedule = {}
            for day in DAYS_OF_WEEK:
                week_schedule[day] = {}
                for task, shifts in st.session_state.tasks_with_shifts.items():
                    week_schedule[day][task] = {shift: [] for shift in shifts}
            for slot in flat_slots:
                week_schedule[slot["day_name"]][slot["task"]][slot["shift"]] = slot["assigned_people"]
                
            st.session_state.history.append({"time": timestamp, "schedule": week_schedule})
            st.rerun()

    # --- ĐOẠN MÃ XUẤT ĐỒ HỌA LỊCH MA TRẬN TRỰC QUAN ---
    st.write("---")
    if not st.session_state.history:
        st.info("💡 Chưa có dữ liệu lịch làm việc. Hãy cấu hình và kích hoạt nút chạy phía trên!")
    else:
        latest = st.session_state.history[-1]
        
        # BỘ LỌC TÌM KIẾM CÁ NHÂN TRÊN ĐIỆN THOẠI CỰC TIỆN
        st.markdown("### 🔍 Bộ lọc tìm kiếm & Khảo sát lịch")
        selected_view_member = st.selectbox(
            "Chọn một thành viên để xem lịch biểu riêng (Các vị trí khác sẽ tự động mờ đi):", 
            options=["-- Xem toàn bộ hệ thống (Master Board) --"] + list(st.session_state.members.keys())
        )
        
        # Tạo khung bảng HTML
        html_table = '<table class="calendar-table"><tr><th>Nhiệm vụ & Khung ca</th>'
        for day in DAYS_OF_WEEK:
            html_table += f'<th>{day}</th>'
        html_table += '</tr>'
        
        # Điền dữ liệu ma trận Ngày - Giờ - Việc
        for task, shifts in st.session_state.tasks_with_shifts.items():
            if shifts:
                # Tiêu đề dòng Công việc lớn
                html_table += f'<tr><td class="row-task-title" colspan="8">📂 {task}</td></tr>'
                for shift in shifts:
                    html_table += f'<tr><td style="font-weight:500; background-color:#fafafa;">⏱️ {shift}</td>'
                    
                    for day in DAYS_OF_WEEK:
                        html_table += '<td>'
                        people_list = latest['schedule'].get(day, {}).get(task, {}).get(shift, [])
                        
                        if not people_list or "⚠️ Trống" in people_list:
                            html_table += '<span class="badge badge-danger">⚠️ Trống</span>'
                        else:
                            for person in people_list:
                                pin_key = f"{day}_{task}_{shift}"
                                is_pinned_cell = pin_key in st.session_state.pins and person in st.session_state.pins[pin_key]
                                class_badge = "badge-pin" if is_pinned_cell else "badge-auto"
                                
                                # Áp dụng hiệu ứng làm nổi bật khi lọc tên cá nhân
                                if selected_view_member != "-- Xem toàn bộ hệ thống (Master Board) --":
                                    if person == selected_view_member:
                                        class_badge += " badge-highlight"
                                    else:
                                        class_badge += " badge-fade"
                                        
                                html_table += f'<span class="badge {class_badge}">{person}</span>'
                        html_table += '</td>'
                    html_table += '</tr>'
                    
        html_table += '</table>'
        
        # Đẩy trực tiếp bảng đồ họa vào giao diện Streamlit Cloud
        st.markdown(html_table, unsafe_allow_html=True)
        
        # Thống kê tải cuối tuần công bằng
        with st.expander("📊 Thống kê khối lượng phân bổ đợt này"):
            for name, info in st.session_state.members.items():
                st.write(f"- 👤 **{name}** gác tổng cộng: `{info['workload']}` ca trực trong tuần này.")
