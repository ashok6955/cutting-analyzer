import streamlit as st
import base64
import json
import pandas as pd
from datetime import datetime
from PIL import Image
from openai import OpenAI
from typing import Set, List, Dict, Tuple

# Page Config
st.set_page_config(page_title="Cutting Analyzer Pro", page_icon="✂️", layout="wide")

# Custom CSS for Exact Paper Grid Replica
st.markdown("""
<style>
    .paper-grid-table {
        border-collapse: collapse;
        width: 100%;
        max-width: 900px;
        margin: 0 auto;
        background-color: #ffffff;
        font-family: Arial, sans-serif;
    }
    .paper-grid-table td {
        border: 1px solid #6b7280;
        padding: 2px 3px;
        text-align: center;
        vertical-align: top;
        position: relative;
        width: 9%;
        height: 42px;
    }
    .paper-grid-table td.row-total-cell {
        border: none;
        width: 10%;
        font-weight: bold;
        color: #111827;
        vertical-align: middle;
        font-size: 13px;
        padding-left: 8px;
        text-align: left;
    }
    .idx-red {
        color: #dc2626; /* Red Index Number */
        font-size: 10px;
        font-weight: bold;
        position: absolute;
        top: 2px;
        left: 3px;
    }
    .val-black {
        color: #000000; /* Dark Bold Amount */
        font-size: 13px;
        font-weight: 800;
        margin-top: 12px;
    }
    .grand-total-red-text {
        color: #dc2626;
        font-size: 20px;
        font-weight: bold;
        text-align: right;
        max-width: 900px;
        margin: 10px auto 0 auto;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State History
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

# --- HEADER ---
st.title("✂️ Cutting Analyzer System Pro")

# --- API KEY AUTO-LOAD ---
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
    st.info(f"🤖 **Verified Model in Use:** `{model_name}`")

st.divider()

# --- MAIN TABS ---
tab_calc, tab_history = st.tabs(["✂️ Cutting Calculator & Audit", "📜 Calculation History Log"])

with tab_calc:
    # --- STEP 1: IMAGE VERIFICATION & EXACT HTML TABLE ---
    st.subheader("📸 Step 1: Upload Table Image & Verify Replica Grid")

    uploaded_file = st.file_uploader("Upload 1-100 Table Image", type=["jpg", "jpeg", "png"])

    if "table_data" not in st.session_state:
        st.session_state.table_data = None

    if uploaded_file and st.button(f"🔍 Step 1: Read & Verify Image using {model_name}", type="primary"):
        if not api_key:
            st.error("🔴 Kripya pehle API Key daalein ya Streamlit Secrets me set karein!")
        else:
            with st.spinner(f"Connecting to ChatGPT ({model_name}) and Reading Entire Image..."):
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
                    
                    total_amount = int(round(sum(table_data.values())))
                    threshold = int(round(total_amount / 100.0))
                    
                    st.success(f"✅ Image Read Successfully via Verified Model: {model_name}!")
                    
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Total Numbers Read", f"{len(table_data)} / 100")
                    col_b.metric("TOTAL WORK AMOUNT", f"₹ {total_amount:,}")
                    col_c.metric("THRESHOLD AMOUNT (1%)", f"₹ {threshold:,}")
                    
                except Exception as e:
                    st.error(f"🔴 Connection / Extraction Error: {str(e)}")

    # RENDER EXACT PAPER REPLICA TABLE
    if st.session_state.table_data:
        table_data = st.session_state.table_data
        st.markdown("### 📊 Extracted Paper Table Replica")
        
        table_html = '<table class="paper-grid-table">'
        grand_total_sum = 0
        
        for r in range(10):
            table_html += '<tr>'
            row_sum = 0
            for c in range(1, 11):
                num_idx = r * 10 + c
                num_str = pad_number(num_idx)
                amt = int(round(table_data.get(num_str, 0)))
                row_sum += amt
                
                table_html += f'''
                <td>
                    <div class="idx-red">{num_idx}</div>
                    <div class="val-black">{amt:,}</div>
                </td>
                '''
            grand_total_sum += row_sum
            table_html += f'<td class="row-total-cell">{row_sum:,}</td>'
            table_html += '</tr>'
            
        table_html += '</table>'
        st.markdown(table_html, unsafe_allow_html=True)
        st.markdown(f'<div class="grand-total-red-text">{grand_total_sum:,}</div>', unsafe_allow_html=True)

    st.divider()

    # --- STEP 2: BASE NUMBERS & CATEGORY-WISE AUDIT ---
    st.subheader("🔢 Step 2: Set Base Numbers & Category Breakdown")

    for i in range(1, 7):
        if f"box_{i}" not in st.session_state:
            st.session_state[f"box_{i}"] = ""

    cols = st.columns(6)
    b1 = cols[0].text_input("Box 1", value=st.session_state.box_1, key="b1")
    b2 = cols[1].text_input("Box 2", value=st.session_state.box_2, key="b2")
    b3 = cols[2].text_input("Box 3", value=st.session_state.box_3, key="b3")
    b4 = cols[3].text_input("Box 4", value=st.session_state.box_4, key="b4")
    b5 = cols[4].text_input("Box 5", value=st.session_state.box_5, key="b5")
    b6 = cols[5].text_input("Box 6", value=st.session_state.box_6, key="b6")

    col_btn1, col_btn2 = st.columns([1, 1])
    if col_btn1.button("💾 SAVE BASE NUMBERS"):
        st.session_state.box_1 = b1
        st.session_state.box_2 = b2
        st.session_state.box_3 = b3
        st.session_state.box_4 = b4
        st.session_state.box_5 = b5
        st.session_state.box_6 = b6
        st.success("Base Numbers Saved Successfully!")

    if col_btn2.button("🔄 RESET BOXES"):
        for idx in range(1, 7):
            st.session_state[f"box_{idx}"] = ""
        st.rerun()

    saved_list = [
        st.session_state.box_1, st.session_state.box_2, st.session_state.box_3,
        st.session_state.box_4, st.session_state.box_5, st.session_state.box_6
    ]
    active_saved_nums = [v.strip() for v in saved_list if v and v.strip().isdigit()]

    if active_saved_nums:
        st.success(f"📌 **Active Saved Base Numbers:** `{', '.join(active_saved_nums)}`")
    else:
        st.warning("⚠️ **No Base Numbers currently saved.** Please enter numbers above and click Save.")

    st.write("")

    if st.button("🚀 Calculate Cutting Amount & Show Category Analysis", type="primary", use_container_width=True):
        if not st.session_state.table_data:
            st.error("🔴 Pehle Step 1 me Image Read & Verify Karein!")
        else:
            raw_inputs = [b1, b2, b3, b4, b5, b6]
            base_numbers = [int(v.strip()) for v in raw_inputs if v and v.strip().isdigit()]
            
            if not base_numbers:
                st.error("🔴 Kam se kam 1 Base Number daalna zaruri hai!")
            else:
                table_data = st.session_state.table_data
                total_amount = sum(table_data.values())
                threshold = total_amount / 100.0
                
                # --- CATEGORY-WISE BREAKDOWN ---
                st.markdown("### 📑 Categorized Rule Analysis")
                
                for base in base_numbers:
                    str_base = pad_number(base)
                    d1, d2 = str_base[0], str_base[1]
                    
                    # Categories Sets
                    inside_set = get_inside_line(d1).union(get_inside_line(d2))
                    outside_set = get_outside_line(d1).union(get_outside_line(d2))
                    palti_set = {reverse_number(base)}
                    
                    rev = reverse_number(base)
                    plus_minus_set = {
                        base + 10, base - 10, rev + 10, rev - 10
                    }
                    plus_minus_set = {x for x in plus_minus_set if 0 <= x <= 100}
                    
                    # Filtering Qualifying Items per Category
                    inside_qual = [(pad_number(n), int(round(table_data.get(pad_number(n), 0) - threshold))) for n in inside_set if table_data.get(pad_number(n), 0) > threshold]
                    outside_qual = [(pad_number(n), int(round(table_data.get(pad_number(n), 0) - threshold))) for n in outside_set if table_data.get(pad_number(n), 0) > threshold]
                    palti_qual = [(pad_number(n), int(round(table_data.get(pad_number(n), 0) - threshold))) for n in palti_set if table_data.get(pad_number(n), 0) > threshold]
                    pm_qual = [(pad_number(n), int(round(table_data.get(pad_number(n), 0) - threshold))) for n in plus_minus_set if table_data.get(pad_number(n), 0) > threshold]
                    
                    with st.expander(f"📊 Series Analysis for Base Number: {pad_number(base)}", expanded=True):
                        st.markdown(f"#### 1. अंदर लाइन (Inside Line):")
                        if inside_qual:
                            st.write(", ".join([f"`{num}={amt}`" for num, amt in inside_qual]) + f" — **(कुल: {len(inside_qual)} नंबर)**")
                        else:
                            st.write("कोई भी नंबर थ्रेशोल्ड से ऊपर नहीं निकला।")
                            
                        st.markdown(f"#### 2. बाहर लाइन (Outside Line):")
                        if outside_qual:
                            st.write(", ".join([f"`{num}={amt}`" for num, amt in outside_qual]) + f" — **(कुल: {len(outside_qual)} नंबर)**")
                        else:
                            st.write("कोई भी नंबर थ्रेशोल्ड से ऊपर नहीं निकला।")

                        st.markdown(f"#### 3. पलटी (Reverse / Invert):")
                        if palti_qual:
                            st.write(", ".join([f"`{num}={amt}`" for num, amt in palti_qual]))
                        else:
                            st.write(f"पलटी (`{pad_number(rev)}`) थ्रेशोल्ड से कम है।")

                        st.markdown(f"#### 4. प्लस / माइनस 10 (±10 Shifts):")
                        if pm_qual:
                            st.write(", ".join([f"`{num}={amt}`" for num, amt in pm_qual]))
                        else:
                            st.write("कोई भी ±10 नंबर थ्रेशोल्ड से ऊपर नहीं निकला।")

                # --- GLOBAL FINAL CUTTING CALCULATION ---
                all_candidates = set()
                for base in base_numbers:
                    all_candidates.update(generate_candidates_for_base(base))
                    
                results: List[Tuple[str, int]] = []
                for idx in all_candidates:
                    num_key = pad_number(idx)
                    amount = table_data.get(num_key, 0.0)
                    if amount > threshold:
                        cutting_amount = int(round(amount - threshold))
                        if cutting_amount > 0:
                            results.append((num_key, cutting_amount))
                        
                results.sort(key=lambda x: x[1], reverse=True)
                
                output_lines = []
                grand_total = 0
                for num_str, amt in results:
                    output_lines.append(f"{num_str} = {amt}")
                    grand_total += amt
                    
                output_lines.append(f"GRAND TOTAL = {grand_total}")
                final_result_str = "\n".join(output_lines)
                
                st.subheader("📋 Final Clipboard Output Code")
                st.code(final_result_str, language="text")
                
                # SAVE TO HISTORY LOG
                st.session_state.history_log.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_work": int(round(total_amount)),
                    "threshold": int(round(threshold)),
                    "base_numbers": ", ".join([pad_number(b) for b in base_numbers]),
                    "grand_total": grand_total,
                    "result_code": final_result_str
                })

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
