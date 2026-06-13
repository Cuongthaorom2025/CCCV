import streamlit as st
from datetime import datetime, timedelta
import calendar
import re

# Cấu hình hiển thị giao diện rộng rãi chuẩn Dashboard điều hành
st.set_page_config(page_title="Lịch Điều Phối Tháng V11.1", page_icon="📅", layout="wide")

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

# Lịch cấu hình động theo ngày thực tế "YYYY-MM-DD" thay vì Thứ
if "monthly_structure" not in st.session_state:
    st.session_state.monthly_structure = {}

if "rules" not in st.session_state:
    st.session_state.rules = {
        "block_consecutive": True,        
        "max_shifts_in_window": 2,        
        "window_hours": 24.0,             
        "min_rest_hours": 2.0,            
        "anti_pairs": []                  
    }

if "day_offs" not in st.session_state:
    st.session_state.day_offs = {}  # Lưu theo "YYYY-MM-DD"

if "pins" not in st.session_state:
    st.session_state.pins = {}      # Lưu theo "YYYY-MM-DD_Task_Shift"

if "history" not in st.session_state:
    st.session_state.history = []

# Mặc định chọn ngày hôm nay trong năm 2026 để làm việc
if "selected_date" not in st.session_state:
    st.session_state.selected_date = "2026-06-13"


# ==========================================================
# BỘ MÁY XỬ LÝ THỜI GIAN TUYẾN TÍNH QUY ĐỔI RA GIỜ (ABSOLUTE TIMELINE)
# ==========================================================
def parse_shift_to_absolute_hours(date_str, shift_str):
    """Quy đổi ngày và khung giờ bất kỳ ra số giờ tuyến tính so với mốc năm 2026"""
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
    return abs_start, abs_end


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


# Style CSS đổ màu các trạng thái ô lịch tháng
st.markdown("""
<style>
    .day-box {
        border-radius: 6px; padding: 8px; margin-bottom: 10px; text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); min-height: 90px;
    }
    .day-active { border: 2px solid #1E3A8A; background-color: #EFF6FF; }
    .day-normal { border: 1px solid #E5E7EB; background-color: #FFFFFF; }
    .day-empty { background-color: #F9FAFB; border: 1px dashed #E5E7EB; }
    .txt-date { font-weight: bold; font-size: 16px; margin-bottom: 4px; }
    .txt-count { font-size: 12px; color: #6B7280; }
    .calendar-header {
        text-align: center; font-weight: bold; padding: 10px; 
        background-color: #1E3A8A; color: white; border-radius: 4px; margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# GIAO DIỆN ĐIỀU HÀNH CHÍNH
# ==========================================================
st.title("📅 Hệ Thống Cắt Cử Điều Phối Lịch Tháng V11.1")
st.markdown(" *Tương tác tối cao: Chọn ngày trực tiếp trên giao diện Lịch tháng 2026* ")

# Thao tác chọn Tháng/Năm trực tiếp ở góc trên
c_m1, c_m2 = st.columns([2, 8])
with c_m1:
    select_month = st.selectbox("📅 Chọn Tháng làm việc:", list(range(1, 13)), index=5) # Mặc định Tháng 6
    select_year = st.number_input("📆 Chọn Năm:", min_value=2026, max_value=2030, value=2026)

st.write("---")

# ==========================================================
# HOẠT HỌA GIAO DIỆN LƯỚI LỊCH THÁNG (MONTHLY CALENDAR GRID)
# ==========================================================
st.subheader(f"🗓️ Bản Đồ Lịch Tháng {select_month}/{select_year}")
st.caption("💡 Hướng dẫn: Bấm vào nút ngày bất kỳ để kích hoạt bảng điều khiển chi tiết của ngày đó ở ngay phía dưới.")

# Tạo tiêu đề cột từ Thứ 2 đến Chủ Nhật
cols_header = st.columns(7)
week_days_text = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
for i, text in enumerate(week_days_text):
    cols_header[i].markdown(f'<div class="calendar-header">{text}</div>', unsafe_allow_html=True)

# Lấy ma trận các tuần của tháng từ thư viện calendar
month_matrix = calendar.monthcalendar(select_year, select_month)

for week in month_matrix:
    cols_week = st.columns(7)
    for d_idx, day_num in enumerate(week):
        with cols_week[d_idx]:
            if day_num == 0:
                st.markdown('<div class="day-box day-empty"></div>', unsafe_allow_html=True)
            else:
                curr_date_str = f"{select_year}-{select_month:02d}-{day_num:02d}"
                is_selected = (st.session_state.selected_date == curr_date_str)
                
                day_struct = st.session_state.monthly_structure.get(curr_date_str, {})
                shift_count = sum(len(shifts) for shifts in day_struct.values())
                
                box_class = "day-active" if is_selected else "day-normal"
                st.markdown(f"""
                <div class="day-box {box_class}">
                    <div class="txt-date">{day_num}</div>
                    <div class="txt-count">⚙️ {shift_count} ca chờ</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Chọn ngày", key=f"btn_select_day_{curr_date_str}", use_container_width=True):
                    st.session_state.selected_date = curr_date_str
                    st.rerun()

st.write("---")

# ==========================================================
# KHU VỰC TƯƠNG TÁC LỊCH TRỰC TIẾP TRÊN NGÀY ĐANG CHỌN
# ==========================================================
target_day = st.session_state.selected_date
if target_day not in st.session_state.monthly_structure:
    st.session_state.monthly_structure[target_day] = {
        "Trực UAV": ["Ca 1 (7h30-11h)", "Ca 2 (13h30-17h)"],
        "Trực ban": ["Ca Sáng (08:00-12:00)"]
    }
if target_day not in st.session_state.day_offs:
    st.session_state.day_offs[target_day] = []

st.markdown(f"### 🛠️ BẢNG ĐIỀU KHIỂN TƯƠNG TÁC CA: **NGÀY {target_day}**")

tab_day_edit, tab_rules, tab_execute = st.tabs(["⚙️ Thêm Việc / Ghim Nhanh", "🛡️ Luật Hệ Thống", "🚀 Chạy Phân Phối Lịch Tháng"])

with tab_day_edit:
    c_edit_left, c_edit_right = st.columns(2)
    
    with c_edit_left:
        st.markdown("**➕ Thêm Công Việc & Ca trực tiếp vào ngày này:**")
        with st.form(key=f"form_add_t_{target_day}"):
            t_input = st.text_input("Tên công việc gán cho ngày này:")
            s_input = st.text_input("Tên ca & Giờ gán cho việc này (Ví dụ: Ca 1 (7h30-11h)):")
            if st.form_submit_button("🚀 Lưu vào ô lịch") and t_input.strip() and s_input.strip():
                t_clean, s_clean = t_input.strip(), s_input.strip()
                if t_clean not in st.session_state.monthly_structure[target_day]:
                    st.session_state.monthly_structure[target_day][t_clean] = []
                if s_clean not in st.session_state.monthly_structure[target_day][t_clean]:
                    st.session_state.monthly_structure[target_day][t_clean].append(s_clean)
                st.rerun()
                
        valid_defaults = [m for m in st.session_state.day_offs[target_day] if m in st.session_state.members]
        st.session_state.day_offs[target_day] = st.multiselect(
            f"❌ Chọn người xin nghỉ (BẬN cả ngày {target_day}):",
            options=list(st.session_state.members.keys()), default=valid_defaults, key=f"off_{target_day}"
        )
        
    with c_edit_right:
        st.markdown("**⚡ Trợ lý Ghim Tốc Hành bằng văn bản:**")
        quick_input = st.text_input("Cú pháp: Người - Việc - Ca", placeholder="Ví dụ: Ánh - Trực UAV - Ca 1 (7h30-11h)", key=f"txt_quick_{target_day}")
        if st.button("🚀 Kích hoạt ghim và tự tạo", key=f"btn_quick_{target_day}"):
            if quick_input:
                parts = [p.strip() for p in re.split(r'[,;|]|\s+-\s+|\s+–\s+|\s+—\s+', quick_input) if p.strip()]
                if len(parts) == 3:
                    p_name, p_task, p_shift = parts[0], parts[1], parts[2]
                    if p_name not in st.session_state.members: st.session_state.members[p_name] = {"excluded": [], "max": 40, "workload": 0, "history": []}
                    if p_task not in st.session_state.monthly_structure[target_day]: st.session_state.monthly_structure[target_day][p_task] = []
                    if p_shift not in st.session_state.monthly_structure[target_day][p_task]: st.session_state.monthly_structure[target_day][p_task].append(p_shift)
                    
                    pin_key = f"{target_day}_{p_task}_{p_shift}"
                    if pin_key not in st.session_state.pins: st.session_state.pins[pin_key] = []
                    if p_name not in st.session_state.pins[pin_key]: st.session_state.pins[pin_key].append(p_name)
                    st.success("Đã ghi nhận lệnh ghim chốt vào ô lịch!")
                    st.rerun()

    st.write("---")
    st.markdown(f"#### 📊 Chi tiết danh sách việc cấu hình riêng của ngày {target_day}:")
    for task, shifts in list(st.session_state.monthly_structure[target_day].items()):
        with st.container(border=True):
            c_t_title, c_t_del = st.columns([5, 1])
            c_t_title.markdown(f"📂 **Nhiệm vụ: {task}**")
            if c_t_del.button("Xóa việc", key=f"del_t_{target_day}_{task}"):
                del st.session_state.monthly_structure[target_day][task]
                st.rerun()
                
            for shift in shifts:
                pin_key = f"{target_day}_{task}_{shift}"
                is_pinned = pin_key in st.session_state.pins and st.session_state.pins[pin_key]
                c_s_view, c_s_act = st.columns([4, 1])
                if is_pinned:
                    c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 📌 Ghim: **{', '.join(st.session_state.pins[pin_key])}**")
                    if c_s_act.button("Hủy ghim", key=f"unpin_{pin_key}"):
                        del st.session_state.pins[pin_key]
                        st.rerun()
                else:
                    c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 🤖 *Tự động chia*")
                    if c_s_act.button("Xóa ca", key=f"del_s_{target_day}_{task}_{shift}"):
                        st.session_state.monthly_structure[target_day][task].remove(shift)
                        st.rerun()

with tab_rules:
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.session_state.rules["block_consecutive"] = st.checkbox("🔒 Nghiêm cấm gác 2 ca liên tục kề sát nhau", value=st.session_state.rules["block_consecutive"])
        st.session_state.rules["min_rest_hours"] = st.number_input("⏱️ Thời gian nghỉ tối thiểu bắt buộc giữa các ca trực (Giờ):", min_value=0.0, max_value=12.0, value=st.session_state.rules["min_rest_hours"], step=0.5)
    with col_r2:
        st.session_state.rules["max_shifts_in_window"] = st.number_input("🛡️ Số lượng ca trực tối đa được nhận:", min_value=1, max_value=5, value=st.session_state.rules["max_shifts_in_window"])
        st.session_state.rules["window_hours"] = st.number_input("⏳ Trong chu kỳ rolling-time (Giờ):", min_value=1.0, max_value=48.0, value=st.session_state.rules["window_hours"], step=1.0)

with tab_execute:
    st.subheader("🚀 Phân Phối Cắt Cử Công Bằng Toàn Tháng")
    if st.button("⚙️ BẮT ĐẦU TỰ ĐỘNG CẮT CỬ TOÀN BỘ CÁC NGÀY TRONG THÁNG", type="primary", use_container_width=True):
        for name in st.session_state.members: st.session_state.members[name]['workload'] = 0
        timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
        
        flat_slots = []
        num_days = calendar.monthrange(select_year, select_month)[1]
        for day_num in range(1, num_days + 1):
            d_str = f"{select_year}-{select_month:02d}-{day_num:02d}"
            if d_str not in st.session_state.monthly_structure: continue
            
            for task, shifts in st.session_state.monthly_structure[d_str].items():
                for shift in shifts:
                    abs_start, abs_end = parse_shift_to_absolute_hours(d_str, shift)
                    flat_slots.append({
                        "date_str": d_str, "day_num": day_num, "task": task, "shift": shift,
                        "abs_start": abs_start, "abs_end": abs_end, "assigned_people": []
                    })
                    
        member_tracks = {name: [] for name in st.session_state.members}
        
        for slot in flat_slots:
            pin_key = f"{slot['date_str']}_{slot['task']}_{slot['shift']}"
            if pin_key in st.session_state.pins:
                for member in st.session_state.pins[pin_key]:
                    if member in st.session_state.members:
                        slot["assigned_people"].append(member)
                        st.session_state.members[member]['workload'] += 1
                        member_tracks[member].append({"abs_start": slot["abs_start"], "abs_end": slot["abs_end"]})
                        
        flat_slots.sort(key=lambda x: x["abs_start"])
        
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
                member_tracks[chosen].append({"abs_start": slot["abs_start"], "abs_end": slot["abs_end"]})

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

    # --- ĐỒ HỌA BẢNG MASTER BOARD LỊCH THÁNG ---
    st.write("---")
    if not st.session_state.history:
        st.info("💡 Hãy thiết lập các ngày và ấn nút kích hoạt CHẠY hệ thống ở trên để nhận bảng lịch tháng.")
    else:
        latest = st.session_state.history[-1]
        
        # 🔥 ĐÃ SỬA: Dùng hàm .get() an toàn kèm bộ gán Fallback để né triệt để lỗi KeyError từ cache cũ
        view_month = latest.get("month", select_month)
        view_year = latest.get("year", select_year)
        
        st.subheader(f"📋 Bảng Kết Quả Điều Phối Lịch Tháng {view_month}/{view_year} ({latest['time']})")
        
        selected_view_member = st.selectbox("🔍 Tiện ích: Chọn nhân sự để làm nổi bật lịch biểu cá nhân:", options=["-- Xem toàn bộ hệ thống (Master Board) --"] + list(st.session_state.members.keys()))
        
        historical_structure = latest.get("structure", st.session_state.monthly_structure)
        num_days = calendar.monthrange(view_year, view_month)[1]
        
        all_matrix_rows = []
        for d_num in range(1, num_days + 1):
            d_str = f"{view_year}-{view_month:02d}-{d_num:02d}"
            for task, shifts in historical_structure.get(d_str, {}).items():
                for shift in shifts:
                    if (task, shift) not in all_matrix_rows: all_matrix_rows.append((task, shift))
        all_matrix_rows.sort(key=lambda x: x[0])
        
        html_table = '<div style="overflow-x: auto;"><table class="calendar-table"><tr><th>Nhiệm vụ & Khung ca</th>'
        for d_num in range(1, num_days + 1):
            html_table += f'<th>Ngày {d_num}</th>'
        html_table += '</tr>'
        
        current_printed_task = ""
        for task, shift in all_matrix_rows:
            if task != current_printed_task:
                current_printed_task = task
                html_table += f'<tr><td class="row-task-title" colspan="{num_days+1}">📂 {task}</td></tr>'
                
            html_table += f'<tr><td style="font-weight:500; background-color:#fcfcfc; min-width:160px;">⏱️ {shift}</td>'
            
            for d_num in range(1, num_days + 1):
                d_str = f"{view_year}-{view_month:02d}-{d_num:02d}"
                day_tasks = historical_structure.get(d_str, {})
                
                if task in day_tasks and shift in day_tasks[task]:
                    html_table += '<td>'
                    people_list = latest['schedule'].get(d_str, {}).get(task, {}).get(shift, [])
                    
                    if not people_list or "⚠️ Trống" in people_list:
                        html_table += '<span class="badge badge-danger">⚠️ Trống</span>'
                    else:
                        for person in people_list:
                            pin_key = f"{d_str}_{task}_{shift}"
                            is_pinned_cell = pin_key in st.session_state.pins and person in st.session_state.pins[pin_key]
                            class_badge = "badge-pin" if is_pinned_cell else "badge-auto"
                            
                            if selected_view_member != "-- Xem toàn bộ hệ thống (Master Board) --":
                                if person == selected_view_member: class_badge += " badge-highlight"
                                else: class_badge += " badge-fade"
                            html_table += f'<span class="badge {class_badge}">{person}</span>'
                    html_table += '</td>'
                else:
                    html_table += '<td class="no-shift-cell">—</td>'
            html_table += '</tr>'
            
        html_table += '</table></div>'
        st.markdown(html_table, unsafe_allow_html=True)
        
        with st.expander("📊 Thống kê khối lượng phân bổ toàn tháng"):
            for name, info in st.session_state.members.items():
                st.write(f"- 👤 **{name}** gác tổng cộng: `{info['workload']}` ca trực trong tháng này.")
