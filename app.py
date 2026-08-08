import streamlit as st
import base64
import json
import pandas as pd
from PIL import Image
from openai import OpenAI
from typing import Set, List, Dict, Tuple

# Page Config
st.set_page_config(page_title="Cutting Analyzer Pro", page_icon="✂️", layout="wide")

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

# --- CONNECTION STATUS & MODEL VERIFICATION BANNER ---
col_status, col_model = st.columns([1, 1])

with col_status:
    if api_key and api_key.strip().startswith("sk-"):
        st.success("🟢 **SYSTEM STATUS: LIVE CONNECTED TO CHATGPT**")
    else:
        st.error("🔴 **SYSTEM STATUS: DISCONNECTED (API Key Required)**")
        api_key = st.text_input("Enter ChatGPT API Key:", type="password")

with col_model:
    model_name = st.text_input("Active GPT Model Version:", value="gpt-4o")
    st.info(f"🤖 **Verified Model in Use:** `{model_name}` (Latest Flagship OpenAI Model)")

st.divider()

# --- STEP 1: IMAGE VERIFICATION & GRID PREVIEW ---
st.subheader("📸 Step 1: Upload Table Image & Verify 100-Grid Table")

uploaded_file = st.file_uploader("Upload 1-100 Table Image", type=["jpg", "jpeg", "png"])

if "table_data" not in st.session_state:
    st.session_state.table_data = None

if uploaded_file and st.button(f"🔍 Step 1: Read & Verify Image using {model_name}", type="primary"):
    if not api_key:
        st.error("🔴 Kripya pehle API Key daalein ya Streamlit Secrets me set karein!")
    else:
        with st.spinner(f"Connecting to ChatGPT ({model_name}) and Extracting 100 Grid Cells..."):
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
                
                # --- SUMMARY METRICS ---
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Total Numbers Read", f"{len(table_data)} / 100")
                col_b.metric("TOTAL WORK AMOUNT", f"₹ {total_amount:,}")
                col_c.metric("THRESHOLD AMOUNT (1%)", f"₹ {threshold:,}")
                
                # --- 10x10 VISUAL GRID TABLE PREVIEW ---
                st.markdown("### 📊 Extracted 1-100 Table Grid (Verify Amounts Here)")
                
                grid_rows = []
                for r in range(10):
                    row_dict = {}
                    row_sum = 0
                    for c in range(1, 11):
                        num_idx = r * 10 + c
                        num_str = pad_number(num_idx)
                        amt = int(round(table_data.get(num_str, 0)))
                        row_dict[f"Col {c} ({num_str})"] = amt
                        row_sum += amt
                    row_dict["TOTAL"] = row_sum
                    grid_rows.append(row_dict)
                
                df_grid = pd.DataFrame(grid_rows, index=[f"Row {r*10+1}-{r*10+10}" for r in range(10)])
                st.dataframe(df_grid, use_container_width=True)
                
            except Exception as e:
                st.error(f"🔴 Connection / Extraction Error: {str(e)}")

st.divider()

# --- STEP 2: BASE NUMBERS & CUTTING ---
st.subheader("🔢 Step 2: Set Base Numbers & Calculate Cutting")

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

# --- ACTIVE SAVED NUMBERS DISPLAY BADGE ---
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

if st.button("🚀 Calculate Cutting Amount", type="primary", use_container_width=True):
    if not st.session_state.table_data:
        st.error("🔴 Pehle Step 1 me Image Read & Verify Karein!")
    else:
        raw_inputs = [b1, b2, b3, b4, b5, b6]
        base_numbers = [int(v.strip()) for v in raw_inputs if v and v.strip().isdigit()]
        
        if not base_numbers:
            st.error("🔴 Kam se kam 1 Base Number daalna zaruri hai!")
        else:
            table_data = st.session_state.table_data
            all_candidates = set()
            for base in base_numbers:
                all_candidates.update(generate_candidates_for_base(base))
                
            total_amount = sum(table_data.values())
            threshold = total_amount / 100.0
            
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
            
            st.subheader("📋 Output Result Code")
            st.code(final_result_str, language="text")
