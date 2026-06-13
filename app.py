import streamlit as st
from datetime import datetime
import re

# Cấu hình hiển thị chuẩn di động & máy tính
st.set_page_config(page_title="Hệ Thống Điều Phối V8", page_icon="⚙️", layout="wide")

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

# 🔥 BỘ KHỞI TẠO CÁC QUY TẮC CẮT CỬ DO ADMIN TỰ THIẾT LẬP
if "rules" not in st.session_state:
    st.session_state.rules = {
        "block_consecutive": True,        # Bật/Tắt chống gác 2 ca liên tục
        "max_shifts_in_window": 2,        # Số ca gác tối đa trong cửa sổ thời gian
        "window_hours": 24.0,             # Số giờ của cửa sổ rolling-time (ví dụ: 24h)
        "min_rest_hours": 2.0,            # Số giờ nghỉ tối thiểu giữa 2 ca trực
        "anti_pairs": []                  # Danh sách các cặp không được làm chung ca [(A, B), ...]
    }

if "day_offs" not in st.session_state:
    st.session_state.day_offs = {day: [] for day in DAYS_OF_WEEK}

if "pins" not in st.session_state:
    st.session_state.pins = {}

if "history" not in st.session_state:
    st.session_state.history = []


# ==========================================================
# BỘ MÁY TÍNH TOÁN & THẨM ĐỊNH QUY TẮC LINH HOẠT
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
    abs_end = day_idx * 24.0 + end_t + (24.0 if end_t < start_t else 0.0)
    return start_t, end_t, abs_start, abs_end


def validate_custom_rules(name, slot, member_tracks, current_shift_people, rules):
    """Hàm thẩm định xem nhân sự có vi phạm bất kỳ quy tắc động nào của Admin không"""
    new_start = slot["abs_start"]
    new_end = slot["abs_end"]
    tracks = member_tracks[name]
    
    for t in tracks:
        # 1. KIỂM TRA QUY TẮC: Chống gác 2 ca liên tục (khoảng cách đầu cuối bằng 0)
        if rules["block_consecutive"]:
            if abs(t["abs_end"] - new_start) < 0.01 or abs(new_end - t["abs_start"]) < 0.01:
                return False
                
        # 2. KIỂM TRA QUY TẮC: Khoảng cách nghỉ tối thiểu giữa các ca trực
        if rules["min_rest_hours"] > 0:
            if new_start >= t["abs_end"]:
                if (new_start - t["abs_end"]) < rules["min_rest_hours"]: return False
            elif t["abs_start"] >= new_end:
                if (t["abs_start"] - new_end) < rules["min_rest_hours"]: return False

    # 3. KIỂM TRA QUY TẮC: Giới hạn số ca trong vòng X giờ rolling-time
    all_slots = tracks + [{"abs_start": new_start, "abs_end": new_end}]
    for s_x in all_slots:
        w_start = s_x["abs_start"]
        w_end = w_start + rules["window_hours"]
        count = sum(1 for s_y in all_slots if w_start <= s_y["abs_start"] < w_end)
        if count > rules["max_shifts_in_window"]:
            return False

    # 4. KIỂM TRA QUY TẮC: Cặp bài trùng không được xếp chung ca trực
    for p1, p2 in rules["anti_pairs"]:
        if name == p1 and p2 in current_shift_people: return False
        if name == p2 and p1 in current_shift_people: return False

    return True


# ==========================================================
# GIAO DIỆN CHÍNH
# ==========================================================
st.title("📆 Hệ Thống Cắt Cử Công Việc Tự Động V8")
st.markdown(" *Phiên bản Tối cao: Tự cấu hình Điều kiện quy tắc — Chống trùng lịch chéo* ")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Dữ Liệu Nhân Sự & Việc", "🛠️ Quản Lý Quy Tắc Cắt Cử", "📅 Thiết Lập Theo Ngày", "🚀 Thực Thi & Kết Quả"])

# ------------------------------------------------------
# TAB 1: CƠ SỞ DỮ LIỆU NHÂN SỰ VÀ ĐẦU VIỆC GỐC
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
            c_info.markdown(f"👤 **{name}** \n<small>Cấm làm: {', '.join(info['excluded']) if info['excluded'] else 'Không'} | Tối đa: {info['max']} việc/tuần</small>", unsafe_allow_html=True)
            if c_del.button("❌", key=f"del_m_{name}"):
                del st.session_state.members[name]
                st.rerun()

    with col_right:
        st.subheader("📌 Quản Lý Công Việc & Ca")
        with st.expander("➕ Tạo công việc mới", expanded=False):
            new_t_name = st.text_input("Tên công việc mới:")
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
                    st.rerun()
                for shift in shifts:
                    c_s_title, c_s_del = st.columns([5, 1])
                    c_s_title.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ {shift}")
                    if c_s_del.button("Xóa ca", key=f"del_s_{task}_{shift}"):
                        st.session_state.tasks_with_shifts[task].remove(shift)
                        st.rerun()

# ------------------------------------------------------
# 🔥 TAB 2: QUẢN LÝ CÁC QUY TẮC CẮT CỬ ĐỘNG (MỚI NÂNG CẤP)
# ------------------------------------------------------
with tab2:
    st.subheader("🛠️ Cấu Hình Các Quy Tắc Điều Phối Hệ Thống")
    st.info("💡 Mọi thay đổi thông số dưới đây sẽ được áp dụng trực tiếp vào thuật toán chia việc tự động.")
    
    # Thiết lập luật gác liên tục và nghỉ ngơi
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.session_state.rules["block_consecutive"] = st.checkbox(
            "🔒 Chống gác 2 ca liên tiếp trong ngày", 
            value=st.session_state.rules["block_consecutive"]
        )
        st.session_state.rules["min_rest_hours"] = st.number_input(
            "⏱️ Khoảng thời gian nghỉ tối thiểu giữa 2 ca trực (Giờ):",
            min_value=0.0, max_value=12.0, value=st.session_state.rules["min_rest_hours"], step=0.5
        )
    with col_r2:
        st.session_state.rules["max_shifts_in_window"] = st.number_input(
            "🛡️ Số ca trực tối đa được phép gác:",
            min_value=1, max_value=5, value=st.session_state.rules["max_shifts_in_window"]
        )
        st.session_state.rules["window_hours"] = st.number_input(
            "⏳ Trong vòng bao nhiêu giờ rolling-time (Ví dụ: 24 giờ):",
            min_value=1.0, max_value=48.0, value=st.session_state.rules["window_hours"], step=1.0
        )
        
    st.write("---")
    # Cấu hình luật Cặp bài trùng không đứng chung ca
    st.markdown("### 👥 Quy tắc Cặp nhân sự chống đứng chung ca")
    if len(st.session_state.members) < 2:
        st.caption("Hãy thêm tối thiểu 2 nhân sự để thiết lập quy tắc này.")
    else:
        with st.form("form_anti_pair"):
            p1 = st.selectbox("Nhân sự thứ nhất:", list(st.session_state.members.keys()), key="ap_p1")
            p2 = st.selectbox("Nhân sự thứ hai:", list(st.session_state.members.keys()), key="ap_p2")
            submit_ap = st.form_submit_button("➕ Thêm quy tắc chặn cặp này")
            if submit_ap:
                if p1 == p2:
                    st.error("Không thể chặn một người với chính họ!")
                else:
                    pair = (p1, p2) if p1 < p2 else (p2, p1)
                    if pair not in st.session_state.rules["anti_pairs"]:
                        st.session_state.rules["anti_pairs"].append(pair)
                        st.rerun()

        # Hiển thị danh sách các cặp đang bị chặn
        if st.session_state.rules["anti_pairs"]:
            st.markdown("**Danh sách các cặp nhân sự tuyệt đối không xếp chung ca:**")
            for pair in list(st.session_state.rules["anti_pairs"]):
                c_p_txt, c_p_del = st.columns([4, 1])
                c_p_txt.write(f"🚫 Chặn đứng chung: **{pair[0]}** và **{pair[1]}**")
                if c_p_del.button("Hủy bỏ chặn", key=f"del_ap_{pair[0]}_{pair[1]}"):
                    st.session_state.rules["anti_pairs"].remove(pair)
                    st.rerun()

# ------------------------------------------------------
# TAB 3: THIẾT LẬP ĐẶC THÙ THEO NGÀY VÀ GHIM TỐC HÀNH
# ------------------------------------------------------
with tab2:
    day_tabs = st.tabs(DAYS_OF_WEEK)
    for idx, day in enumerate(DAYS_OF_WEEK):
        with day_tabs[idx]:
            st.markdown(f"### 🛠️ Cài đặt cho **{day}**")
            valid_defaults = [m for m in st.session_state.day_offs[day] if m in st.session_state.members]
            st.session_state.day_offs[day] = st.multiselect(
                f"❌ Chọn người nghỉ (BẬN cả ngày) vào {day}:",
                options=list(st.session_state.members.keys()),
                default=valid_defaults, key=f"off_{day}"
            )
            st.write("---")
            st.markdown("### ⚡ Trợ lý Ghim Tốc Hành (Nhập nhanh văn bản)")
            quick_input = st.text_input("Nhập câu lệnh ghim nhanh:", placeholder="Ví dụ: Ánh - Trực UAV - Ca 1 (7h30-11h)", key=f"text_input_{day}")
            
            if st.button("🚀 Kích hoạt ghim nhanh", key=f"btn_quick_{day}"):
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
            st.markdown("#### 📌 Danh sách các vị trí cần phân bổ trong ngày:")
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
# TAB 4: THỰC THI THUẬT TOÁN ĐIỀU PHỐI VÀ XEM NHẬT KÝ
# ------------------------------------------------------
with tab4:
    st.subheader("⚡ Chạy thuật toán điều phối tích hợp")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        run_v8 = st.button("🚀 TỰ ĐỘNG CẮT CỬ ĐỀU TOÀN TUẦN", type="primary", use_container_width=True)
    with c_btn2:
        if st.button("🗑️ Xóa sạch lịch sử", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    if run_v8:
        if not st.session_state.members or not st.session_state.tasks_with_shifts:
            st.error("Không có đủ dữ liệu gốc để vận hành tính toán!")
        else:
            for name in st.session_state.members:
                st.session_state.members[name]['workload'] = 0
            
            timestamp = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            
            # Khởi tạo danh sách phẳng chứa toàn bộ các slot cần xếp
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
            
            member_tracks = {name: [] for name in st.session_state.members}
            
            # BƯỚC 1: ĐIỀN CÁC LỆNH GHIM TRƯỚC
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
            
            # Sắp xếp các ca theo dòng thời gian tuyến tính để chia tự động tuần tự
            flat_slots.sort(key=lambda x: (x["day_idx"], x["abs_start"]))
            
            # BƯỚC 2: TỰ ĐỘNG CẮT CỬ DỰA TRÊN CÁC QUY TẮC ĐỘNG CỦA ADMIN
            for slot in flat_slots:
                if not slot["assigned_people"]:
                    busy_day_people = st.session_state.day_offs[slot["day_name"]]
                    eligible_members = []
                    
                    # Lấy danh sách những người đã được xếp vào ca này (cho các việc khác) để check luật anti-pair
                    current_shift_people = []
                    for s_check in flat_slots:
                        if s_check["day_idx"] == slot["day_idx"] and abs(s_check["abs_start"] - slot["abs_start"]) < 0.01:
                            current_shift_people.extend(s_check["assigned_people"])
                    
                    for name, info in st.session_state.members.items():
                        # Kiểm tra các điều kiện nền tảng
                        if name in busy_day_people: continue
                        if slot["task"] in info["excluded"]: continue
                        if info["workload"] >= info["max"]: continue
                        
                        # Chống trùng lịch cơ bản: Không thể làm 2 việc cùng lúc trong 1 ca trực
                        is_overlapping = False
                        for track in member_tracks[name]:
                            if not (slot["abs_end"] <= track["abs_start"] or slot["abs_start"] >= track["abs_end"]):
                                is_overlapping = True
                                break
                        if is_overlapping: continue
                        
                        # 🔥 THẨM ĐỊNH QUA BỘ QUY TẮC ĐỘNG CỦA ADMIN
                        if not validate_custom_rules(name, slot, member_tracks, current_shift_people, st.session_state.rules):
                            continue
                            
                        eligible_members.append(name)
                        
                    if not eligible_members:
                        slot["assigned_people"].append("⚠️ Không ai đủ điều kiện")
                        continue
                    
                    # Ưu tiên tính công bằng: Chọn người ít việc nhất tuần đợt này
                    eligible_members.sort(key=lambda x: (st.session_state.members[x]['workload'], len(st.session_state.members[x]['history'])))
                    chosen = eligible_members[0]
                    
                    slot["assigned_people"].append(chosen)
                    st.session_state.members[chosen]['workload'] += 1
                    st.session_state.members[chosen]['history'].append(f"{slot['day_name']} - {slot['task']}: {slot['shift']}")
                    member_tracks[chosen].append({
                        "abs_start": slot["abs_start"], "abs_end": slot["abs_end"], "day_idx": slot["day_idx"]
                    })
            
            # Đóng gói kết quả để xuất ra màn hình UI
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
