import streamlit as st
from datetime import datetime
import re

# Cấu hình hiển thị chuẩn giao diện Dashboard rộng rãi
st.set_page_config(page_title="Lịch Điều Phối V10", page_icon="📅", layout="wide")

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

# 🔥 THAY ĐỔI CỐT LÕI V10: Cấu trúc Công việc & Ca trực được lưu biệt lập theo từng ngày
if "daily_structure" not in st.session_state:
    st.session_state.daily_structure = {
        day: {
            "Trực UAV": ["Ca 1 (7h30-11h)", "Ca 2 (13h30-17h)"],
            "Trực ban": ["Ca Sáng (08:00-12:00)", "Ca Đêm (22:00-06:00)"]
        } for day in DAYS_OF_WEEK
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
# BỘ MÁY PHÂN TÍCH THỜI GIAN LÀM VIỆC TUYẾN TÍNH
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


# Style CSS cho bảng đồ họa Master Board
st.markdown("""
<style>
    .calendar-table { width: 100%; border-collapse: collapse; font-family: sans-serif; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; overflow: hidden; }
    .calendar-table th { background-color: #1E3A8A; color: white; text-align: center; padding: 12px; font-weight: 600; border: 1px solid #3B82F6; }
    .calendar-table td { border: 1px solid #E5E7EB; padding: 10px; vertical-align: top; background-color: #ffffff; min-width: 125px; }
    .row-task-title { background-color: #EFF6FF !important; font-weight: bold; color: #1E40AF; padding: 8px !important; }
    .badge { display: inline-block; padding: 4px 8px; margin: 3px 2px; border-radius: 4px; font-size: 13px; font-weight: 500; }
    .badge-pin { background-color: #DBEAFE; color: #1E40AF; border: 1px solid #BFDBFE; }
    .badge-auto { background-color: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; }
    .badge-danger { background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; font-weight: bold; }
    .badge-fade { opacity: 0.2; background-color: #F3F4F6; color: #9CA3AF; }
    .badge-highlight { background-color: #FBBF24 !important; color: #78350F !important; font-weight: bold !important; box-shadow: 0 0 8px rgba(251,191,36,0.7); }
    .no-shift-cell { text-align: center; color: #D1D5DB; background-color: #F9FAFB; font-style: italic; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# GIAO DIỆN ĐIỀU HÀNH CHÍNH
# ==========================================================
st.title("📆 Hệ Thống Cắt Cử Công Việc Trực Quan V10")
st.markdown(" *Đỉnh cao điều phối: Thêm Việc, tạo Ca trực tiếp trên Lịch Ngày độc lập* ")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Quản Lý Nhân Sự Gốc", "🛡️ Thiết Lập Luật Điều Phối", "📅 Lập Lịch Trực Tiếp Trên Ngày", "🚀 Thực Thi & Bảng Kết Quả"])

# ------------------------------------------------------
# TAB 1: DANH SÁCH NHÂN SỰ TOÀN CỤC
# ------------------------------------------------------
with tab1:
    st.subheader("👥 Quản Lý Hồ Sơ Nhân Sự")
    with st.expander("➕ Thêm thành viên mới vào hệ thống", expanded=False):
        m_name = st.text_input("Tên nhân sự:")
        m_exclude = st.text_input("Việc không thể gác (Cách nhau bằng dấu phẩy):")
        m_max = st.number_input("Số ca trực tối đa được nhận trong tuần:", min_value=1, value=15)
        if st.button("Lưu hồ sơ nhân sự"):
            if m_name.strip():
                excluded_list = [t.strip() for t in m_exclude.split(",") if t.strip()]
                st.session_state.members[m_name.strip()] = {"excluded": excluded_list, "max": m_max, "workload": 0, "history": []}
                st.rerun()

    st.write("---")
    for name, info in list(st.session_state.members.items()):
        c_info, c_del = st.columns([5, 1])
        c_info.markdown(f"👤 **{name}** &nbsp;&nbsp;|&nbsp;&nbsp; <small>Danh mục cấm: {', '.join(info['excluded']) if info['excluded'] else 'Không'} &nbsp;&nbsp;•&nbsp;&nbsp; Giới hạn tuần: {info['max']} ca</small>", unsafe_allow_html=True)
        if c_del.button("Xóa hồ sơ", key=f"del_m_{name}"):
            del st.session_state.members[name]
            st.rerun()

# ------------------------------------------------------
# TAB 2: QUẢN LÝ LUẬT VÀ ĐIỀU KIỆN CẮT CỬ ĐỘNG
# ------------------------------------------------------
with tab2:
    st.subheader("🛠️ Bộ Cấu Hình Điều Kiện Cắt Cử")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.session_state.rules["block_consecutive"] = st.checkbox("🔒 Nghiêm cấm gác 2 ca liên tục liền kề nhau", value=st.session_state.rules["block_consecutive"])
        st.session_state.rules["min_rest_hours"] = st.number_input("⏱️ Thời gian rảnh bắt buộc phải nghỉ giữa 2 ca trực (Giờ):", min_value=0.0, max_value=12.0, value=st.session_state.rules["min_rest_hours"], step=0.5)
    with col_r2:
        st.session_state.rules["max_shifts_in_window"] = st.number_input("🛡️ Số lượng ca trực tối đa được gác:", min_value=1, max_value=5, value=st.session_state.rules["max_shifts_in_window"])
        st.session_state.rules["window_hours"] = st.number_input("⏳ Trong khoảng chu kỳ rolling-time (Giờ):", min_value=1.0, max_value=48.0, value=st.session_state.rules["window_hours"], step=1.0)
        
    st.write("---")
    st.markdown("### 🚫 Chặn cặp bài trùng chung ca")
    if len(st.session_state.members) >= 2:
        with st.form("form_anti_pair"):
            p1 = st.selectbox("Nhân sự A:", list(st.session_state.members.keys()), key="ap_p1")
            p2 = st.selectbox("Nhân sự B:", list(st.session_state.members.keys()), key="ap_p2")
            if st.form_submit_button("Xác nhận chặn cặp này") and p1 != p2:
                pair = (p1, p2) if p1 < p2 else (p2, p1)
                if pair not in st.session_state.rules["anti_pairs"]:
                    st.session_state.rules["anti_pairs"].append(pair)
                    st.rerun()
        for pair in list(st.session_state.rules["anti_pairs"]):
            c_p_txt, c_p_del = st.columns([5, 1])
            c_p_txt.write(f"❌ Không đứng chung ca: **{pair[0]}** và **{pair[1]}**")
            if c_p_del.button("Hủy bỏ lệnh chặn", key=f"del_ap_{pair[0]}_{pair[1]}"):
                st.session_state.rules["anti_pairs"].remove(pair)
                st.rerun()

# ------------------------------------------------------
# 🔥 TAB 3: THIẾT LẬP TRỰC TIẾP TRÊN LỊCH NGÀY (MỚI NÂNG CẤP)
# ------------------------------------------------------
with tab3:
    st.subheader("📅 Ma Trận Lập Lịch Chi Tiết Theo Từng Ngày")
    st.info("💡 Điểm đặc biệt V10: Mỗi ngày có một lịch trình ca trực hoàn toàn riêng biệt. Bạn có thể thêm Việc hoặc tạo Ca trực tiếp cho ngày đó tại đây.")
    
    day_tabs = st.tabs(DAYS_OF_WEEK)
    for idx, day in enumerate(DAYS_OF_WEEK):
        with day_tabs[idx]:
            st.markdown(f"## 🛠️ Điều phối lịch trình cho **{day}**")
            
            # Khung chọn người bận cả ngày
            valid_defaults = [m for m in st.session_state.day_offs[day] if m in st.session_state.members]
            st.session_state.day_offs[day] = st.multiselect(f"❌ Chọn nhân sự xin nghỉ (BẬN toàn bộ ngày {day}):", options=list(st.session_state.members.keys()), default=valid_defaults, key=f"off_{day}")
            
            st.write("---")
            
            # KHU VỰC THÊM CÔNG VIỆC VÀ CA TRỰC TIẾP VÀO NGÀY
            st.markdown("### ➕ Thêm Việc & Ca trực tiếp vào ngày này")
            c_add_t, c_add_s = st.columns(2)
            
            with c_add_t:
                with st.form(key=f"form_add_t_{day}"):
                    t_input = st.text_input("Tên công việc mới gán riêng cho ngày này:")
                    if st.form_submit_button("🚀 Thêm Công Việc") and t_input.strip():
                        t_clean = t_input.strip()
                        if t_clean not in st.session_state.daily_structure[day]:
                            st.session_state.daily_structure[day][t_clean] = []
                            st.rerun()
            
            with c_add_s:
                if st.session_state.daily_structure[day]:
                    with st.form(key=f"form_add_s_{day}"):
                        sel_t = st.selectbox("Chọn công việc để tạo ca:", list(st.session_state.daily_structure[day].keys()))
                        s_input = st.text_input("Tên ca & Khung giờ cụ thể (Ví dụ: Ca 1 (7h30-11h)):")
                        if st.form_submit_button("🚀 Thêm Ca & Giờ") and s_input.strip():
                            s_clean = s_input.strip()
                            if s_clean not in st.session_state.daily_structure[day][sel_t]:
                                st.session_state.daily_structure[day][sel_t].append(s_clean)
                                st.rerun()

            st.write("---")
            
            # TRỢ LÝ VĂN BẢN GHIM NHANH VÀ TỰ TẠO DỮ LIỆU CHO NGÀY
            st.markdown("### ⚡ Trợ lý Ghim Tốc Hành bằng văn bản")
            st.caption("Cú pháp: `Tên người - Tên việc - Tên ca`. Nếu Việc hoặc Ca của ngày này chưa có, hệ thống sẽ tự động tạo luôn!")
            quick_input = st.text_input("Nhập câu lệnh ghim nhanh cho ngày này:", placeholder="Ví dụ: Ánh - Trực UAV - Ca 1 (7h30-11h)", key=f"text_input_{day}")
            
            if st.button("🎯 Kích hoạt ghim và tạo nhanh", key=f"btn_quick_{day}"):
                if quick_input:
                    parts = [p.strip() for p in re.split(r'[,;|]|\s+-\s+|\s+–\s+|\s+—\s+', quick_input) if p.strip()]
                    if len(parts) == 3:
                        p_name, p_task, p_shift = parts[0], parts[1], parts[2]
                        
                        # Tự tạo thành viên nếu chưa có
                        if p_name not in st.session_state.members:
                            st.session_state.members[p_name] = {"excluded": [], "max": 10, "workload": 0, "history": []}
                        # 🔥 Tự động tạo việc và ca cho RIÊNG ngày này trên lịch
                        if p_task not in st.session_state.daily_structure[day]:
                            st.session_state.daily_structure[day][p_task] = []
                        if p_shift not in st.session_state.daily_structure[day][p_task]:
                            st.session_state.daily_structure[day][p_task].append(p_shift)
                            
                        pin_key = f"{day}_{p_task}_{p_shift}"
                        if pin_key not in st.session_state.pins: st.session_state.pins[pin_key] = []
                        if p_name not in st.session_state.pins[pin_key]: st.session_state.pins[pin_key].append(p_name)
                        st.success("🎉 Đã ghim và cập nhật trực tiếp vào lịch ngày hôm nay thành công!")
                        st.rerun()
                    else:
                        st.error("Cú pháp chuẩn phải cách dấu gạch ngang: Người - Việc - Ca")

            st.write("---")
            
            # HIỂN THỊ CẤU TRÚC LỊCH HIỆN TẠI CỦA NGÀY (CÓ NÚT XÓA TRỰC TIẾP)
            st.markdown("#### 📊 Trực quan sơ đồ ca trực cấu hình hôm nay:")
            if not st.session_state.daily_structure[day]:
                st.caption("Ngày hôm nay đang trống lịch trình.")
            else:
                for task, shifts in list(st.session_state.daily_structure[day].items()):
                    with st.container(border=True):
                        c_t_title, c_t_del = st.columns([5, 1])
                        c_t_title.markdown(f"📂 **Nhiệm vụ: {task}**")
                        if c_t_del.button("Xóa việc khỏi ngày này", key=f"del_t_{day}_{task}"):
                            del st.session_state.daily_structure[day][task]
                            st.rerun()
                            
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
                                c_s_view.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift} ➔ 🤖 *Tự động chia*")
                                if c_s_act.button("Xóa ca này", key=f"del_s_{day}_{task}_{shift}"):
                                    st.session_state.daily_structure[day][task].remove(shift)
                                    if pin_key in st.session_state.pins: del st.session_state.pins[pin_key]
                                    st.rerun()

# ------------------------------------------------------
# TAB 4: THỰC THI THUẬT TOÁN ĐIỀU PHỐI & MASTER BOARD
# ------------------------------------------------------
with tab4:
    st.subheader("🚀 Kích Hoạt Hệ Thống Điều Phối Lịch Tuần")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        run_v10 = st.button("⚙️ CHẠY TỰ ĐỘNG CẮT CỬ ĐỀU", type="primary", use_container_width=True)
    with c_btn2:
        if st.button("🗑️ Xóa lịch sử", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    if run_v10:
        for name in st.session_state.members: st.session_state.members[name]['workload'] = 0
        timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
        
        # Tạo danh sách phẳng từ cấu trúc lịch ngày động
        flat_slots = []
        for d_idx, day in enumerate(DAYS_OF_WEEK):
            for task, shifts in st.session_state.daily_structure[day].items():
                for shift in shifts:
                    _, _, abs_start, abs_end = parse_shift_bounds(shift, d_idx)
                    flat_slots.append({
                        "day_idx": d_idx, "day_name": day, "task": task, "shift": shift,
                        "abs_start": abs_start, "abs_end": abs_end, "assigned_people": []
                    })
                    
        member_tracks = {name: [] for name in st.session_state.members}
        
        # BƯỚC 1: ĐIỀN GHIM TRƯỚC
        for slot in flat_slots:
            pin_key = f"{slot['day_name']}_{slot['task']}_{slot['shift']}"
            if pin_key in st.session_state.pins:
                for member in st.session_state.pins[pin_key]:
                    if member in st.session_state.members:
                        slot["assigned_people"].append(member)
                        st.session_state.members[member]['workload'] += 1
                        member_tracks[member].append({"abs_start": slot["abs_start"], "abs_end": slot["abs_end"]})
                        
        flat_slots.sort(key=lambda x: (x["day_idx"], x["abs_start"]))
        
        # BƯỚC 2: TỰ ĐỘNG ĐIỀU PHỐI THẨM ĐỊNH QUY TẮC ĐỘNG
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

        # Đóng gói kết quả tuần
        week_schedule = {}
        for day in DAYS_OF_WEEK:
            week_schedule[day] = {}
            for task, shifts in st.session_state.daily_structure[day].items():
                week_schedule[day][task] = {shift: [] for shift in shifts}
        for slot in flat_slots:
            week_schedule[slot["day_name"]][slot["task"]][slot["shift"]] = slot["assigned_people"]
            
        # Lưu bản chụp cấu hình lịch trực tuần này vào lịch sử log
        deep_copied_structure = {d: {t: list(s) for t, s in tasks.items()} for d, tasks in st.session_state.daily_structure.items()}
        st.session_state.history.append({
            "time": timestamp,
            "schedule": week_schedule,
            "structure": deep_copied_structure
        })
        st.rerun()

    # --- ĐỒ HỌA MA TRẬN LỊCH TRỰC DYNAMIC V10 ---
    st.write("---")
    if not st.session_state.history:
        st.info("💡 Chưa có bảng lịch hoạt động. Hãy cấu hình ca trực tại Tab 3 rồi bấm nút CHẠY hệ thống!")
    else:
        latest = st.session_state.history[-1]
        
        st.markdown("### 🔍 Bộ lọc tìm kiếm lịch cá nhân")
        selected_view_member = st.selectbox("Chọn nhân sự để hiển thị nổi bật trên lịch biểu:", options=["-- Xem toàn bộ hệ thống (Master Board) --"] + list(st.session_state.members.keys()))
        
        # Tạo ma trận danh sách ca trực duy nhất xuất hiện trong tuần để làm hàng (row)
        all_matrix_rows = []
        for day in DAYS_OF_WEEK:
            for task, shifts in latest["structure"].get(day, {}).items():
                for shift in shifts:
                    if (task, shift) not in all_matrix_rows:
                        all_matrix_rows.append((task, shift))
        # Sắp xếp theo tên công việc
        all_matrix_rows.sort(key=lambda x: x[0])
        
        # Xây dựng bảng HTML trực quan
        html_table = '<table class="calendar-table"><tr><th>Nhiệm vụ & Khung ca</th>'
        for day in DAYS_OF_WEEK:
            html_table += f'<th>{day}</th>'
        html_table += '</tr>'
        
        current_printed_task = ""
        for task, shift in all_matrix_rows:
            # Viết tiêu đề phân tách dòng công việc lớn nếu đổi việc
            if task != current_printed_task:
                current_printed_task = task
                html_table += f'<tr><td class="row-task-title" colspan="8">📂 {task}</td></tr>'
                
            html_table += f'<tr><td style="font-weight:500; background-color:#fcfcfc;">⏱️ {shift}</td>'
            
            for day in DAYS_OF_WEEK:
                # Kiểm tra xem ngày hôm nay có cấu hình ca trực này không
                day_tasks = latest["structure"].get(day, {})
                if task in day_tasks and shift in day_tasks[task]:
                    html_table += '<td>'
                    people_list = latest['schedule'].get(day, {}).get(task, {}).get(shift, [])
                    
                    if not people_list or "⚠️ Trống" in people_list:
                        html_table += '<span class="badge badge-danger">⚠️ Trống</span>'
                    else:
                        for person in people_list:
                            pin_key = f"{day}_{task}_{shift}"
                            is_pinned_cell = pin_key in st.session_state.pins and person in st.session_state.pins[pin_key]
                            class_badge = "badge-pin" if is_pinned_cell else "badge-auto"
                            
                            if selected_view_member != "-- Xem toàn bộ hệ thống (Master Board) --":
                                if person == selected_view_member:
                                    class_badge += " badge-highlight"
                                else:
                                    class_badge += " badge-fade"
                            html_table += f'<span class="badge {class_badge}">{person}</span>'
                    html_table += '</td>'
                else:
                    # Nếu ngày hôm đó không có ca này gán trên lịch
                    html_table += '<td class="no-shift-cell">—</td>'
            html_table += '</tr>'
            
        html_table += '</table>'
        st.markdown(html_table, unsafe_allow_html=True)
        
        with st.expander("📊 Thống kê khối lượng phân bổ đợt này"):
            for name, info in st.session_state.members.items():
                st.write(f"- 👤 **{name}** gác tổng cộng: `{info['workload']}` ca trực trong tuần này.")
