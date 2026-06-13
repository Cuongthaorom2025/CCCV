import streamlit as st
from datetime import datetime
import calendar
import re

# Cấu hình hiển thị chuẩn Dashboard điều hành thông minh
st.set_page_config(page_title="Lịch Điều Phối Cao Cấp V12.4", page_icon="📅", layout="wide")

# Danh sách các ngày trong tuần cố định
DAYS_OF_WEEK = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

# ==========================================================
# KHỞI TẠO BỘ NHỚ HỆ THỐNG TRÊN ĐỒNG HỒ THỜI GIAN (2026)
# ==========================================================
if "members" not in st.session_state:
    st.session_state.members = {
        "Ánh": {"excluded": [], "max": 40, "workload": 0, "history": []},
        "Anh Hải": {"excluded": [], "max": 45, "workload": 0, "history": []},
        "Chị Hoa": {"excluded": [], "max": 20, "workload": 0, "history": []},
        "Đức Tuấn": {"excluded": [], "max": 50, "workload": 0, "history": []}
    }

if "global_tasks" not in st.session_state:
    st.session_state.global_tasks = ["Trực UAV", "Trực ban", "Tuần tra cơ động", "Kiểm tra kho"]

if "monthly_structure" not in st.session_state:
    st.session_state.monthly_structure = {}

# Cập nhật cấu hình quy tắc mặc định có thêm luật nghỉ ca đêm
if "rules" not in st.session_state:
    st.session_state.rules = {
        "block_consecutive": True,        
        "max_shifts_in_window": 2,        
        "window_hours": 24.0,             
        "min_rest_hours": 2.0,
        "night_shift_morning_off": True,  # Bật/Tắt luật trực đêm nghỉ sáng hôm sau
        "anti_pairs": []                  
    }

if "day_offs" not in st.session_state:
    st.session_state.day_offs = {}  

if "pins" not in st.session_state:
    st.session_state.pins = {}      

if "history" not in st.session_state:
    st.session_state.history = []


# ==========================================================
# BỘ MÁY XỬ LÝ THỜI GIAN TUYẾN TÍNH (ABSOLUTE TIMELINE)
# ==========================================================
def parse_shift_to_absolute_hours(date_str, shift_str):
    base_date = datetime.strptime(date_str, "%Y-%m-%d")
    epoch = datetime(2026, 1, 1)
    delta_days = (base_date - epoch).days
    base_hours = delta_days * 24.0
    
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
        
    abs_start = base_hours + start_t
    abs_end = base_hours + end_t + (24.0 if end_t < start_t else 0.0)
    return start_t, end_t, abs_start, abs_end


def validate_custom_rules(name, slot, member_tracks, current_shift_people, rules):
    new_start = slot["abs_start"]
    new_end = slot["abs_end"]
    tracks = member_tracks[name]
    
    slot_date = datetime.strptime(slot["date_str"], "%Y-%m-%d")
    epoch = datetime(2026, 1, 1)
    
    for t in tracks:
        # 1. QUY TẮC: Chống gác 2 ca liên tục liền kề
        if rules["block_consecutive"]:
            if abs(t["abs_end"] - new_start) < 0.01 or abs(new_end - t["abs_start"]) < 0.01:
                return False
                
        # 2. QUY TẮC: Khoảng thời gian nghỉ tối thiểu giữa các ca
        if rules["min_rest_hours"] > 0:
            if new_start >= t["abs_end"]:
                if (new_start - t["abs_end"]) < rules["min_rest_hours"]: return False
            elif t["abs_start"] >= new_end:
                if (t["abs_start"] - new_end) < rules["min_rest_hours"]: return False
                
        # 3. QUY TẮC MỚI: Trực đêm/xuyên đêm hôm trước được nghỉ buổi sáng hôm sau (trước 12h00)
        if rules.get("night_shift_morning_off", True):
            slot_day_start_hours = (slot_date - epoch).days * 24.0
            end_hour_on_slot_day = t["abs_end"] - slot_day_start_hours
            
            # Nếu ca cũ kết thúc vào khoảng từ 0h00 đến 8h00 sáng ngày hôm nay (gác xuyên đêm)
            if 0.0 < end_hour_on_slot_day <= 8.0:
                # Thì mọi ca trực tự động vào ngày hôm nay bắt đầu trước 12h00 trưa đều bị chặn
                if slot["start_t"] < 12.0:
                    return False

    # 4. QUY TẮC: Giới hạn số ca trong vòng X giờ rolling-time
    all_slots = tracks + [{"abs_start": new_start, "abs_end": new_end}]
    for s_x in all_slots:
        w_start = s_x["abs_start"]
        w_end = w_start + rules["window_hours"]
        count = sum(1 for s_y in all_slots if w_start <= s_y["abs_start"] < w_end)
        if count > rules["max_shifts_in_window"]:
            return False

    # 5. QUY TẮC: Chặn cặp bài trùng chung ca
    for p1, p2 in rules["anti_pairs"]:
        if name == p1 and p2 in current_shift_people: return False
        if name == p2 and p1 in current_shift_people: return False
    return True


# Style CSS đồ màu bảng và các block ca kíp gác
st.markdown("""
<style>
    .day-box { border-radius: 8px; padding: 10px; margin-bottom: 5px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); min-height: 85px; }
    .day-normal { border: 1px solid #E5E7EB; background-color: #FFFFFF; }
    .day-configured { border: 1px solid #3B82F6; background-color: #F0F6FF; box-shadow: 0 2px 5px rgba(59,130,246,0.1); }
    .day-empty { background-color: #F9FAFB; border: 1px dashed #E5E7EB; }
    .txt-date { font-weight: bold; font-size: 16px; color: #1F2937; margin-bottom: 2px; }
    .txt-count { font-size: 11px; font-weight: 500; color: #2563EB; }
    .txt-count-zero { font-size: 11px; color: #9CA3AF; }
    .calendar-header { text-align: center; font-weight: bold; padding: 10px; background-color: #1E3A8A; color: white; border-radius: 6px; margin-bottom: 10px; }
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); border-radius: 8px; overflow: hidden; }
    .calendar-table th { background-color: #1F2937; color: white; text-align: center; padding: 12px; font-weight: 600; border: 1px solid #374151; }
    .calendar-table td { border: 1px solid #D1D5DB; height: 145px; vertical-align: top; padding: 8px; background-color: white; }
    .result-day-num { font-weight: bold; font-size: 15px; color: #111827; margin-bottom: 5px; display: block; }
    .result-shift-strip { font-size: 11px; padding: 4px 6px; margin-bottom: 3px; border-radius: 4px; line-height: 1.3; font-weight: 500; border-left: 3px solid transparent; }
    .strip-pin { background-color: #E0F2FE; color: #0369A1; border-left-color: #0284C7; }
    .strip-auto { background-color: #DCFCE7; color: #15803D; border-left-color: #22C55E; }
    .strip-danger { background-color: #FEE2E2; color: #B91C1C; border-left-color: #EF4444; font-weight: bold; }
    .strip-fade { opacity: 0.15; background-color: #F3F4F6; color: #9CA3AF; border-left-color: #D1D5DB; }
    .strip-highlight { background-color: #FEF3C7 !important; color: #92400E !important; border-left-color: #D97706 !important; font-weight: bold !important; box-shadow: inset 0 0 4px rgba(217,119,6,0.2); }
</style>
""", unsafe_allow_html=True)


# ==========================================================
# BẢNG POPUP DIALOG TƯƠNG TÁC
# ==========================================================
@st.dialog("⚙️ Bảng Điều Khiển Ô Lịch Ngày")
def configure_day_modal(target_day):
    st.markdown(f"### 📅 Cấu hình lịch gác ngày: **{target_day}**")
    if target_day not in st.session_state.monthly_structure: st.session_state.monthly_structure[target_day] = {}
    if target_day not in st.session_state.day_offs: st.session_state.day_offs[target_day] = []
        
    c_pop1, c_pop2 = st.columns(2)
    with c_pop1:
        st.markdown("**➕ Thêm việc & Ca trực:**")
        with st.form(key=f"pop_form_add_{target_day}"):
            if not st.session_state.global_tasks:
                st.warning("Hãy thêm công việc gốc ở Tab 'Quản lý Nhân Sự & Việc' trước!")
                chosen_task = None
            else:
                chosen_task = st.selectbox("Chọn công việc gác:", options=st.session_state.global_tasks)
            s_input = st.text_input("Ca & Khung giờ (Ví dụ: ca1 7h30-11h hoặc ca từ 20h-6h):")
            
            if st.form_submit_button("➕ Thêm vào ngày này") and chosen_task and s_input.strip():
                s_clean = s_input.strip()
                if chosen_task not in st.session_state.monthly_structure[target_day]: st.session_state.monthly_structure[target_day][chosen_task] = []
                if s_clean not in st.session_state.monthly_structure[target_day][chosen_task]: st.session_state.monthly_structure[target_day][chosen_task].append(s_clean)
        
        valid_defaults = [m for m in st.session_state.day_offs[target_day] if m in st.session_state.members]
        st.session_state.day_offs[target_day] = st.multiselect(f"❌ Nhân sự nghỉ (BẬN cả ngày):", options=list(st.session_state.members.keys()), default=valid_defaults, key=f"pop_off_{target_day}")
        
    with c_pop2:
        st.markdown("**⚡ Trợ lý Ghim Tốc Hành bằng văn bản:**")
        quick_input = st.text_input("Nhập câu lệnh ghim nhanh:", placeholder="Ví dụ: Ánh - Trực UAV - ca từ 20h-6h", key=f"pop_txt_quick_{target_day}")
        if st.button("🚀 Kích hoạt ghim nhanh", key=f"pop_btn_quick_{target_day}"):
            if quick_input:
                parts = [p.strip() for p in re.split(r'[,;|]|\s+-\s+|\s+–\s+|\s+—\s+', quick_input) if p.strip()]
                if len(parts) == 3:
                    p_name, p_task, p_shift = parts[0], parts[1], parts[2]
                    if p_name not in st.session_state.members: st.session_state.members[p_name] = {"excluded": [], "max": 40, "workload": 0, "history": []}
                    if p_task not in st.session_state.global_tasks: st.error(f"Đầu việc '{p_task}' không tồn tại gốc!")
                    else:
                        if p_task not in st.session_state.monthly_structure[target_day]: st.session_state.monthly_structure[target_day][p_task] = []
                        if p_shift not in st.session_state.monthly_structure[target_day][p_task]: st.session_state.monthly_structure[target_day][p_task].append(p_shift)
                        pin_key = f"{target_day}_{p_task}_{p_shift}"
                        if pin_key not in st.session_state.pins: st.session_state.pins[pin_key] = []
                        if p_name not in st.session_state.pins[pin_key]: st.session_state.pins[pin_key].append(p_name)

    st.write("---")
    for task, shifts in list(st.session_state.monthly_structure[target_day].items()):
        with st.container(border=True):
            col_t_title, col_t_del = st.columns([5, 1])
            col_t_title.markdown(f"📂 **Nhiệm vụ: {task}**")
            if col_t_del.button("Xóa việc", key=f"pop_del_t_{target_day}_{task}"): del st.session_state.monthly_structure[target_day][task]
            for shift in shifts:
                pin_key = f"{target_day}_{task}_{shift}"
                is_pinned = pin_key in st.session_state.pins and st.session_state.pins[pin_key]
                col_s_view, col_s_act = st.columns([4, 1])
                if is_pinned:
                    col_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 📌 Ghim: **{', '.join(st.session_state.pins[pin_key])}**")
                    if col_s_act.button("Hủy ghim", key=f"pop_unpin_{pin_key}"): del st.session_state.pins[pin_key]
                else:
                    col_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 🤖 *Tự động chia*")
                    if col_s_act.button("Xóa ca", key=f"pop_del_s_{target_day}_{task}_{shift}"): st.session_state.monthly_structure[target_day][task].remove(shift)
                        
    st.write("---")
    if st.button("💾 XONG & ĐÓNG CỬA SỔ (Cập nhật lên Lịch Tháng)", type="primary", use_container_width=True): st.rerun()


# ==========================================================
# CƠ CẤU HỆ THỐNG TABS GIAO DIỆN CHÍNH
# ==========================================================
tab_calendar, tab_members, tab_rules = st.tabs(["🗓️ Bản Đồ Lịch Tháng & Điều Phối", "👥 Quản Lý Nhân Sự & Việc Gốc", "🛡️ Quản Lý Điều Kiện Cắt Cử"])

# ------------------------------------------------------
# TAB CENTRAL: BẢN ĐỒ LỊCH THÁNG & BẢNG KẾT QUẢ VUÔNG ĐỘC ĐÁO
# ------------------------------------------------------
with tab_calendar:
    col_ctrl1, col_ctrl2 = st.columns([3, 7])
    with col_ctrl1:
        select_month = st.selectbox("📅 Chọn Tháng gác:", list(range(1, 13)), index=5) 
        select_year = st.number_input("📆 Chọn Năm trực:", min_value=2026, max_value=2030, value=2026)
    with col_ctrl2:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("🚀 KÍCH HOẠ TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN THÁNG", type="primary", use_container_width=True):
            for name in st.session_state.members: st.session_state.members[name]['workload'] = 0
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            flat_slots = []
            num_days = calendar.monthrange(select_year, select_month)[1]
            for day_num in range(1, num_days + 1):
                d_str = f"{select_year}-{select_month:02d}-{day_num:02d}"
                if d_str not in st.session_state.monthly_structure: continue
                
                for task, shifts in st.session_state.monthly_structure[d_str].items():
                    for shift in shifts:
                        start_t, end_t, abs_start, abs_end = parse_shift_to_absolute_hours(d_str, shift)
                        flat_slots.append({
                            "date_str": d_str, "day_num": day_num, "task": task, "shift": shift,
                            "start_t": start_t, "end_t": end_t,
                            "abs_start": abs_start, "abs_end": abs_end, "assigned_people": []
                        })
                        
            member_tracks = {name: [] for name in st.session_state.members}
            
            # ĐIỀN GHIM TRƯỚC
            for slot in flat_slots:
                pin_key = f"{slot['date_str']}_{slot['task']}_{slot['shift']}"
                if pin_key in st.session_state.pins:
                    for member in st.session_state.pins[pin_key]:
                        if member in st.session_state.members:
                            slot["assigned_people"].append(member)
                            st.session_state.members[member]['workload'] += 1
                            member_tracks[member].append({
                                "abs_start": slot["abs_start"], "abs_end": slot["abs_end"], "date_str": slot["date_str"]
                            })
                            
            flat_slots.sort(key=lambda x: x["abs_start"])
            
            # TỰ ĐỘNG PHÂN PHỐI THÀNH VIÊN
            for slot in flat_slots:
                if not slot["assigned_people"]:
                    busy_people = st.session_state.day_offs.get(slot["date_str"], [])
                    eligible_members = []
                    current_shift_people = []
                    for s_check in flat_slots:
                        if s_check["date_str"] == slot["date_str"] and abs(s_check["abs_start"] - slot["abs_start"]) < 0.01:
                            current_shift_people.extend(s_check["assigned_people"])
                            
                    for name, info in st.session_state.members.items():
                        if name in busy_people or slot["task"] in info["excluded"] or info["workload"] >= info["max"]: continue
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
                    member_tracks[chosen].append({
                        "abs_start": slot["abs_start"], "abs_end": slot["abs_end"], "date_str": slot["date_str"]
                    })

            month_schedule = {}
            for slot in flat_slots:
                if slot["date_str"] not in month_schedule: month_schedule[slot["date_str"]] = {}
                if slot["task"] not in month_schedule[slot["date_str"]]: month_schedule[slot["date_str"]][slot["task"]] = {}
                month_schedule[slot["date_str"]][slot["task"]][slot["shift"]] = slot["assigned_people"]
                
            deep_copied_structure = {d: {t: list(s) for t, s in tasks.items()} for d, tasks in st.session_state.monthly_structure.items()}
            st.session_state.history.append({
                "time": timestamp, "schedule": month_schedule, "structure": deep_copied_structure,
                "month": select_month, "year": select_year
            })
            st.rerun()

    st.write("---")
    st.markdown(f"#### 🗓️ Cuốn Lịch Thiết Lập Tháng {select_month} / {select_year}")
    st.caption("👉 **HƯỚNG DẪN:** Bấm nút **'Sửa ngày'** bất kỳ để mở Popup ghim lịch.")

    cols_header = st.columns(7)
    for i, text in enumerate(DAYS_OF_WEEK):
        cols_header[i].markdown(f'<div class="calendar-header">{text}</div>', unsafe_allow_html=True)

    month_matrix = calendar.monthcalendar(select_year, select_month)
    for week in month_matrix:
        cols_week = st.columns(7)
        for d_idx, day_num in enumerate(week):
            with cols_week[d_idx]:
                if day_num == 0:
                    st.markdown('<div class="day-box day-empty"></div>', unsafe_allow_html=True)
                else:
                    curr_date_str = f"{select_year}-{select_month:02d}-{day_num:02d}"
                    day_struct = st.session_state.monthly_structure.get(curr_date_str, {})
                    shift_count = sum(len(shifts) for shifts in day_struct.values())
                    
                    box_style = "day-configured" if shift_count > 0 else "day-normal"
                    count_style = "txt-count" if shift_count > 0 else "txt-count-zero"
                    
                    st.markdown(f"""
                    <div class="day-box {box_style}">
                        <div class="txt-date">{day_num}</div>
                        <div class="{count_style}">⚙️ {shift_count} ca trực</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Sửa ngày {day_num}", key=f"btn_pop_{curr_date_str}", use_container_width=True):
                        configure_day_modal(curr_date_str)

    # --- BẢNG KẾT QUẢ DẠNG LỊCH THÁNG Ô VUÔNG ---
    st.write("---")
    if not st.session_state.history:
        st.info("💡 Hãy thiết lập lịch trình và ấn nút kích hoạt CHẠY hệ thống ở trên để xuất ma trận lịch gác vuông.")
    else:
        latest = st.session_state.history[-1]
        view_month = latest.get("month", select_month)
        view_year = latest.get("year", select_year)
        
        st.subheader(f"📋 Bảng Kết Quả Điều Phối Lịch Tháng Vuông {view_month}/{view_year} ({latest['time']})")
        selected_view_member = st.selectbox("🔍 Khảo sát lịch cá nhân nhanh (Làm nổi bật tên):", options=["-- Xem toàn bộ hệ thống (Master Board) --"] + list(st.session_state.members.keys()))
        
        historical_structure = latest.get("structure", st.session_state.monthly_structure)
        result_month_matrix = calendar.monthcalendar(view_year, view_month)
        
        html_table = '<table class="calendar-table"><tr>'
        for day_name in DAYS_OF_WEEK: html_table += f'<th>{day_name}</th>'
        html_table += '</tr>'
        
        for week in result_month_matrix:
            html_table += '<tr>'
            for d_idx, day_num in enumerate(week):
                if day_num == 0:
                    html_table += '<td style="background-color: #F9FAFB;"></td>'
                else:
                    d_str = f"{view_year}-{view_month:02d}-{day_num:02d}"
                    html_table += '<td>'
                    html_table += f'<div class="result-day-num">{day_num}</div>'
                    
                    busy_people = st.session_state.day_offs.get(d_str, [])
                    if busy_people:
                        html_table += f'<div style="font-size:10px; color:#EF4444; margin-bottom:4px; font-weight:500;">❌ Nghỉ: {", ".join(busy_people)}</div>'
                        
                    day_tasks = historical_structure.get(d_str, {})
                    for task, shifts in day_tasks.items():
                        for shift in shifts:
                            people_list = latest['schedule'].get(d_str, {}).get(task, {}).get(shift, [])
                            pin_key = f"{d_str}_{task}_{shift}"
                            
                            if not people_list or "⚠️ Trống" in people_list:
                                html_table += f'<div class="result-shift-strip strip-danger">⚠️ {task} ({shift})</div>'
                            else:
                                for person in people_list:
                                    is_pinned_cell = pin_key in st.session_state.pins and person in st.session_state.pins[pin_key]
                                    strip_class = "strip-pin" if is_pinned_cell else "strip-auto"
                                    
                                    if selected_view_member != "-- Xem toàn bộ hệ thống (Master Board) --":
                                        if person == selected_view_member: strip_class = "strip-highlight"
                                        else: strip_class = "strip-fade"
                                            
                                    html_table += f'<div class="result-shift-strip {strip_class}"><b>{person}</b>: {task} ({shift})</div>'
                    html_table += '</td>'
            html_table += '</tr>'
            
        html_table += '</table>'
        st.markdown(html_table, unsafe_allow_html=True)

# ------------------------------------------------------
# TAB 2: QUẢN LÝ NHÂN SỰ & DANH MỤC CÔNG VIỆC GỐC
# ------------------------------------------------------
with tab_members:
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.subheader("👥 Quản Lý Hồ Sơ Nhân Sự")
        with st.expander("➕ Thêm nhân sự mới", expanded=False):
            m_name = st.text_input("Tên nhân sự:")
            m_exclude = st.text_input("Việc không thể gác (Cách nhau bằng dấu phẩy):")
            m_max = st.number_input("Số ca trực tối đa/tháng:", min_value=1, value=40)
            if st.button("Lưu hồ sơ nhân sự"):
                if m_name.strip():
                    excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
                    st.session_state.members[m_name.strip()] = {"excluded": excluded_list, "max": m_max, "workload": 0, "history": []}
                    st.rerun()
        st.write("---")
        for name, info in list(st.session_state.members.items()):
            c_info, c_del = st.columns([5, 1])
            c_info.markdown(f"👤 **{name}** \n<small>Cấm gác: {', '.join(info['excluded']) if info['excluded'] else 'Không'} | Max: {info['max']} ca</small>", unsafe_allow_html=True)
            if c_del.button("Xóa", key=f"tab_del_m_{name}"):
                del st.session_state.members[name]
                st.rerun()
                
    with c_m2:
        st.subheader("📂 Danh Mục Công Việc Gốc")
        with st.expander("➕ Định nghĩa đầu việc mới", expanded=False):
            t_g_input = st.text_input("Nhập tên đầu việc cốt lõi:")
            if st.button("Lưu công việc gốc"):
                if t_g_input.strip() and t_g_input.strip() not in st.session_state.global_tasks:
                    st.session_state.global_tasks.append(t_g_input.strip())
                    st.rerun()
        st.write("---")
        st.markdown("**Danh sách công việc đang khả dụng trên hệ thống:**")
        for idx, task_g in enumerate(st.session_state.global_tasks):
            c_t_name, c_t_del = st.columns([5, 1])
            c_t_name.write(f"🔹 **{task_g}**")
            if c_t_del.button("Xóa việc", key=f"tab_del_tg_{idx}_{task_g}"):
                st.session_state.global_tasks.remove(task_g)
                st.rerun()

# ------------------------------------------------------
# TAB 3: LUẬT ĐIỀU PHỐI NÂNG CAO
# ------------------------------------------------------
with tab_rules:
    st.subheader("🛠️ Bộ Cấu Hình Điều Kiện Cắt Cử")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.session_state.rules["block_consecutive"] = st.checkbox("🔒 Nghiêm cấm gác 2 ca liên tục liền kề nhau", value=st.session_state.rules["block_consecutive"])
        st.session_state.rules["min_rest_hours"] = st.number_input("⏱️ Thời gian nghỉ tối thiểu bắt buộc giữa các ca trực (Giờ):", min_value=0.0, max_value=12.0, value=st.session_state.rules["min_rest_hours"], step=0.5)
        
        # Công tắc Bật/Tắt quy tắc trực đêm được nghỉ sáng hôm sau
        st.session_state.rules["night_shift_morning_off"] = st.checkbox(
            "🌙 Trực ca đêm/xuyên đêm được nghỉ buổi sáng hôm sau (Không xếp ca gác trước 12h00 trưa)", 
            value=st.session_state.rules.get("night_shift_morning_off", True)
        )
        
    with col_r2:
        st.session_state.rules["max_shifts_in_window"] = st.number_input("🛡️ Số lượng ca trực tối đa gác trong chu kỳ:", min_value=1, max_value=5, value=st.session_state.rules["max_shifts_in_window"])
        st.session_state.rules["window_hours"] = st.number_input("⏳ Độ dài chu kỳ rolling-time (Giờ):", min_value=1.0, max_value=48.0, value=st.session_state.rules["window_hours"], step=1.0)
        
    st.write("---")
    st.markdown("### 🚫 Chặn cặp bài trùng chung ca")
    if len(st.session_state.members) >= 2:
        with st.form("tab_form_anti_pair"):
            p1 = st.selectbox("Nhân sự A:", list(st.session_state.members.keys()), key="tab_ap_p1")
            p2 = st.selectbox("Nhân sự B:", list(st.session_state.members.keys()), key="tab_ap_p2")
            if st.form_submit_button("Xác nhận chặn cặp này") and p1 != p2:
                pair = (p1, p2) if p1 < p2 else (p2, p1)
                if pair not in st.session_state.rules["anti_pairs"]:
                    st.session_state.rules["anti_pairs"].append(pair)
                    st.rerun()
        for pair in list(st.session_state.rules["anti_pairs"]):
            c_p_txt, c_p_del = st.columns([5, 1])
            c_p_txt.write(f"❌ Không đứng chung ca: **{pair[0]}** và **{pair[1]}**")
            if c_p_del.button("Hủy bỏ lệnh chặn", key=f"tab_del_ap_{pair[0]}_{pair[1]}"):
                st.session_state.rules["anti_pairs"].remove(pair)
                st.rerun()
