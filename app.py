import streamlit as st
import base64
import json
import streamlit.components.v1 as components
from datetime import datetime
from PIL import Image
from openai import OpenAI
from typing import Set, List, Dict, Tuple

# Page Config
st.set_page_config(page_title="Cutting Analyzer Pro", page_icon="✂️", layout="wide")

# Initialize Session State
for i in range(1, 7):
    if f"box_{i}" not in st.session_state:
        st.session_state[f"box_{i}"] = ""

if "table_data" not in st.session_state:
    st.session_state.table_data = None

if "cut_numbers_set" not in st.session_state:
    st.session_state.cut_numbers_set = set()

if "history_log" not in st.session_state:
    st.session_state.history_log = []

# --- CUTTING ANALYZER CORE LOGIC ---
def pad_number(n: int) -> str:
    return f"{n:02d}"

def get_inside_line(digit: str) -> Set[int]:
    d = int(digit)
    return {d * 10 + i for i in range(1, 10)}

def get_outside_line(digit: str) -> Set[int]:
    d = int(digit)
    return {i * 10 + d for i in range(10)}

def reverse_number(n: int) -> int:
    s = pad_number(n)
    return int(s[::-1])

def generate_candidates_for_base(base_num: int) -> Set[int]:
    candidates: Set[int] = set()
    str_base = pad_number(base_num)
    d1, d2 = str_base[0], str_base[1]
    
    candidates.add(base_num)
    candidates.update(get_inside_line(d1))
    candidates.update(get_outside_line(d1))
    candidates.update(get_inside_line(d2))
    candidates.update(get_outside_line(d2))
    
    rev_num = reverse_number(base_num)
    candidates.add(rev_num)
    
    candidates.add(base_num - 10)
    candidates.add(base_num + 10)
    candidates.add(rev_num - 10)
    candidates.add(rev_num + 10)
    
    seeds = list(candidates)
    for s in seeds:
        candidates.add(s - 1)
        candidates.add(s + 1)
        
    return {c for c in candidates if 0 <= c <= 100}

# --- CLEAN HEADER UI ---
st.markdown("## ✂️ Cutting Analyzer System Pro")

api_key = ""
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]

col_status, col_model = st.columns([1, 1])

with col_status:
    if api_key and api_key.strip().startswith("sk-"):
        st.success("🟢 **SYSTEM STATUS: LIVE CONNECTED TO CHATGPT**")
    else:
        st.error("🔴 **SYSTEM STATUS: DISCONNECTED (API Key Required)**")
        api_key = st.text_input("Enter ChatGPT API Key:", type="password")

with col_model:
    model_name = st.text_input("Active GPT Model Version:", value="gpt-4o")

st.divider()

# --- MAIN TABS ---
tab_calc, tab_history = st.tabs(["✂️ Cutting Calculator", "📜 History Log"])

with tab_calc:
    # --- CARD 1: IMAGE SCANNER ---
    st.markdown("### 📸 Step 1: Upload Image & Verify Replica Grid")
    
    uploaded_file = st.file_uploader("Upload 1-100 Table Image", type=["jpg", "jpeg", "png"])

    if uploaded_file and st.button(f"🔍 Read & Verify Image using {model_name}", type="primary"):
        if not api_key:
            st.error("🔴 Kripya pehle API Key daalein ya Streamlit Secrets me set karein!")
        else:
            with st.spinner("Connecting to ChatGPT and Extracting Table..."):
                try:
                    client = OpenAI(api_key=api_key.strip())
                    image_bytes = uploaded_file.read()
                    base64_image = base64.b64encode(image_bytes).decode('utf-8')
                    
                    prompt = """
                    You are an expert table OCR scanner. Extract all numbers (01 to 100) and their amounts from this image.
                    Return ONLY a JSON object mapping padded 2-digit string numbers ("01", "02", ..., "100") to numeric amounts.
                    Example: {"01": 500, "02": 1200, ..., "100": 300}.
                    Do not include markdown or extra text.
                    """

                    response = client.chat.completions.create(
                        model=model_name.strip(),
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                                    },
                                ],
                            }
                        ],
                        response_format={"type": "json_object"}
                    )
                    
                    table_data_raw = json.loads(response.choices[0].message.content)
                    table_data = {str(k).zfill(2): float(v) for k, v in table_data_raw.items()}
                    st.session_state.table_data = table_data
                    st.session_state.cut_numbers_set = set() # Reset cuts on new image
                    st.success("✅ Image Read Successfully!")
                    
                except Exception as e:
                    st.error(f"🔴 Connection / Extraction Error: {str(e)}")

    # RENDER PAPER REPLICA TABLE WITH RED CUT HIGHLIGHTS
    if st.session_state.table_data:
        table_data = st.session_state.table_data
        cut_set = st.session_state.cut_numbers_set
        
        total_amount = int(round(sum(table_data.values())))
        threshold = int(round(total_amount / 100.0))
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Numbers Read", f"{len(table_data)} / 100")
        col_m2.metric("TOTAL WORK AMOUNT", f"₹ {total_amount:,}")
        col_m3.metric("THRESHOLD AMOUNT (1%)", f"₹ {threshold:,}")
        
        if cut_set:
            st.markdown(f"#### 📊 Extracted Paper Table Replica (<span style='color:#dc2626; font-weight:bold;'>🔴 RED BOXES = Cutting Selected ({len(cut_set)} Numbers)</span>)", unsafe_allow_html=True)
        else:
            st.markdown("#### 📊 Extracted Paper Table Replica")
        
        table_html = """
        <html>
        <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #ffffff; }
            .paper-grid-wrapper { width: 100%; max-width: 820px; margin: 0 auto; overflow-x: auto; }
            .scale-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
            .scale-table td { border: 1px solid #4a5568; height: 44px; padding: 2px; vertical-align: top; position: relative; background-color: #ffffff; }
            
            /* RED HIGHLIGHT FOR CUTTING NUMBERS */
            .scale-table td.cut-red-cell {
                background-color: #fee2e2 !important;
                border: 2.5px solid #dc2626 !important;
            }
            .scale-table td.cut-red-cell .cell-black-amt {
                color: #b91c1c !important;
                font-weight: 900 !important;
            }
            
            .scale-table td.row-sum-col { border: none; width: 70px; vertical-align: middle; text-align: left; padding-left: 10px; font-weight: 800; font-size: 14px; color: #1a202c; }
            .cell-red-idx { color: #e53e3e; font-size: 10px; font-weight: 700; position: absolute; top: 2px; left: 4px; line-height: 1; }
            .cell-black-amt { color: #1a202c; font-size: 13px; font-weight: 800; text-align: center; margin-top: 14px; line-height: 1; }
            .grand-total-footer { text-align: right; font-size: 22px; font-weight: 900; color: #e53e3e; padding-top: 8px; padding-right: 15px; }
        </style>
        </head>
        <body>
        <div class="paper-grid-wrapper">
        <table class="scale-table">
        """
        
        grand_total_sum = 0
        for r in range(10):
            table_html += "<tr>"
            row_sum = 0
            for c in range(1, 11):
                num_idx = r * 10 + c
                num_str = pad_number(num_idx)
                amt = int(round(table_data.get(num_str, 0)))
                row_sum += amt
                
                # Apply Red Highlight if number is in cutting output
                is_cut = "cut-red-cell" if num_str in cut_set else ""
                
                table_html += f'<td class="{is_cut}"><div class="cell-red-idx">{num_idx}</div><div class="cell-black-amt">{amt:,}</div></td>'
            
            grand_total_sum += row_sum
            table_html += f'<td class="row-sum-col">{row_sum:,}</td></tr>'
            
        table_html += f'</table><div class="grand-total-footer">{grand_total_sum:,}</div></div></body></html>'
        
        components.html(table_html, height=520, scrolling=True)

    st.divider()

    # --- CARD 2: BLANK BASE NUMBERS INPUT WITH SAVE BUTTON ---
    st.markdown("### 🔢 Step 2: Enter Base Numbers")

    cols = st.columns(6)
    b1 = cols[0].text_input("Box 1", value=st.session_state.box_1, key="in_b1")
    b2 = cols[1].text_input("Box 2", value=st.session_state.box_2, key="in_b2")
    b3 = cols[2].text_input("Box 3", value=st.session_state.box_3, key="in_b3")
    b4 = cols[3].text_input("Box 4", value=st.session_state.box_4, key="in_b4")
    b5 = cols[4].text_input("Box 5", value=st.session_state.box_5, key="in_b5")
    b6 = cols[5].text_input("Box 6", value=st.session_state.box_6, key="in_b6")

    col_btn1, col_btn2 = st.columns([1, 1])

    if col_btn1.button("💾 SAVE BASE NUMBERS", type="primary"):
        st.session_state.box_1 = b1
        st.session_state.box_2 = b2
        st.session_state.box_3 = b3
        st.session_state.box_4 = b4
        st.session_state.box_5 = b5
        st.session_state.box_6 = b6
        st.success("Base Numbers Saved Successfully!")

    if col_btn2.button("🔄 RESET ALL BOXES", type="secondary"):
        for i in range(1, 7):
            st.session_state[f"box_{i}"] = ""
        st.session_state.cut_numbers_set = set()
        st.rerun()

    active_saved_nums = [
        st.session_state[f"box_{i}"].strip()
        for i in range(1, 7)
        if st.session_state[f"box_{i}"].strip().isdigit()
    ]

    if active_saved_nums:
        st.info(f"📌 **Active Saved Base Numbers:** `{', '.join(active_saved_nums)}` (Numbers will stay saved until Reset)")
    else:
        st.warning("⚠️ Enter base numbers in the boxes above and click SAVE BASE NUMBERS.")

    st.write("")

    # --- CARD 3: RUN CUTTING & HIGHLIGHT RED ---
    if st.button("🚀 RUN CUTTING ANALYSIS", type="primary", use_container_width=True):
        if not st.session_state.table_data:
            st.error("🔴 Pehle Step 1 me Image Read & Verify Karein!")
        elif not active_saved_nums:
            st.error("🔴 Kam se kam 1 Base Number daalna aur SAVE karna zaruri hai!")
        else:
            table_data = st.session_state.table_data
            total_amount = sum(table_data.values())
            threshold = total_amount / 100.0
            base_numbers = [int(x) for x in active_saved_nums]
            
            # 1. GENERATE COMBINED CANDIDATES TO HIGHLIGHT IN RED ON GRID
            all_candidates = set()
            for base in base_numbers:
                all_candidates.update(generate_candidates_for_base(base))
                
            cut_set = set()
            combined_results = []
            for c_idx in all_candidates:
                num_key = pad_number(c_idx)
                amt = table_data.get(num_key, 0.0)
                if amt > threshold:
                    cut_amt = int(round(amt - threshold))
                    if cut_amt > 0:
                        combined_results.append((num_key, cut_amt))
                        cut_set.add(num_key)
            
            # Save Cut Numbers Set into Session State & Rerun Grid
            st.session_state.cut_numbers_set = cut_set
            
            st.divider()
            
            # --- COMPACT CATEGORY RULE ANALYSIS ---
            st.markdown("### 📊 Compact Category Rule Analysis")
            
            for base in base_numbers:
                str_base = pad_number(base)
                d1, d2 = str_base[0], str_base[1]
                
                inside_set = get_inside_line(d1).union(get_inside_line(d2))
                outside_set = get_outside_line(d1).union(get_outside_line(d2))
                palti_set = {reverse_number(base)}
                
                rev = reverse_number(base)
                plus_minus_set = {base + 10, base - 10, rev + 10, rev - 10}
                plus_minus_set = {x for x in plus_minus_set if 0 <= x <= 100}
                
                inside_qual = [(pad_number(n), int(round(table_data.get(pad_number(n), 0) - threshold))) for n in inside_set if table_data.get(pad_number(n), 0) > threshold]
                outside_qual = [(pad_number(n), int(round(table_data.get(pad_number(n), 0) - threshold))) for n in outside_set if table_data.get(pad_number(n), 0) > threshold]
                palti_qual = [(pad_number(n), int(round(table_data.get(pad_number(n), 0) - threshold))) for n in palti_set if table_data.get(pad_number(n), 0) > threshold]
                pm_qual = [(pad_number(n), int(round(table_data.get(pad_number(n), 0) - threshold))) for n in plus_minus_set if table_data.get(pad_number(n), 0) > threshold]
                
                with st.expander(f"🔹 Series {pad_number(base)} Category Breakdown", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**1. अंदर (Inside Line):**")
                        if inside_qual:
                            st.write(", ".join([f"`{n}={a}`" for n, a in inside_qual]) + f" — **(Total: {len(inside_qual)})**")
                        else:
                            st.write("None")

                        st.markdown("**2. पलटी (Reverse):**")
                        if palti_qual:
                            st.write(", ".join([f"`{n}={a}`" for n, a in palti_qual]))
                        else:
                            st.write("None")

                    with col2:
                        st.markdown("**3. बाहर (Outside Line):**")
                        if outside_qual:
                            st.write(", ".join([f"`{n}={a}`" for n, a in outside_qual]) + f" — **(Total: {len(outside_qual)})**")
                        else:
                            st.write("None")

                        st.markdown("**4. ±10 Shifts:**")
                        if pm_qual:
                            st.write(", ".join([f"`{num}={amt}`" for num, amt in pm_qual]))
                        else:
                            st.write("None")

            st.divider()
            st.markdown("### 📋 SEPARATE SERIES CUTTING RESULTS")
            
            # --- INDIVIDUAL SERIES CUTTING BLOCKS ---
            series_tab_names = [f"Series {pad_number(b)}" for b in base_numbers] + ["⭐ COMBINED FINAL RESULT"]
            series_tabs = st.tabs(series_tab_names)
            
            for idx_b, base in enumerate(base_numbers):
                with series_tabs[idx_b]:
                    series_candidates = generate_candidates_for_base(base)
                    series_results = []
                    
                    for c_idx in series_candidates:
                        num_key = pad_number(c_idx)
                        amt = table_data.get(num_key, 0.0)
                        if amt > threshold:
                            cut_amt = int(round(amt - threshold))
                            if cut_amt > 0:
                                series_results.append((num_key, cut_amt))
                                
                    series_results.sort(key=lambda x: x[1], reverse=True)
                    
                    s_lines = []
                    s_grand_total = 0
                    for num_str, c_amt in series_results:
                        s_lines.append(f"{num_str} = {c_amt}")
                        s_grand_total += c_amt
                    s_lines.append(f"GRAND TOTAL = {s_grand_total}")
                    
                    s_code = "\n".join(s_lines)
                    st.markdown(f"#### Series {pad_number(base)} Copy Code:")
                    st.code(s_code, language="text")

            # --- COMBINED FINAL RESULT BLOCK ---
            with series_tabs[-1]:
                combined_results.sort(key=lambda x: x[1], reverse=True)
                
                c_lines = []
                c_grand_total = 0
                for num_str, c_amt in combined_results:
                    c_lines.append(f"{num_str} = {c_amt}")
                    c_grand_total += c_amt
                c_lines.append(f"GRAND TOTAL = {c_grand_total}")
                
                final_combined_code = "\n".join(c_lines)
                st.markdown("#### ⭐ Combined Final Cutting Result Code:")
                st.code(final_combined_code, language="text")
                
                # SAVE TO HISTORY
                st.session_state.history_log.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_work": int(round(total_amount)),
                    "threshold": int(round(threshold)),
                    "base_numbers": ", ".join([pad_number(b) for b in base_numbers]),
                    "grand_total": c_grand_total,
                    "result_code": final_combined_code
                })
                
            st.rerun() # Refresh to update red grid

# --- TAB 2: HISTORY LOG ---
with tab_history:
    st.subheader("📜 Saved Cutting History Log")
    if not st.session_state.history_log:
        st.info("No calculations performed yet in this session.")
    else:
        for idx, entry in enumerate(reversed(st.session_state.history_log), 1):
            with st.expander(f"🕒 History Entry #{idx} - {entry['timestamp']} (Grand Total: {entry['grand_total']:,})"):
                st.write(f"**Total Work Amount:** ₹ {entry['total_work']:,}")
                st.write(f"**Threshold (1%):** ₹ {entry['threshold']:,}")
                st.write(f"**Base Numbers Used:** `{entry['base_numbers']}`")
                st.code(entry['result_code'], language="text")
                
        if st.button("🗑️ Clear History Log"):
            st.session_state.history_log = []
            st.rerun()
