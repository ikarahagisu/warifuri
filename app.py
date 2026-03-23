import streamlit as st
import pandas as pd
import random

# レイアウト設定
st.set_page_config(page_title="患者割り振り", layout="wide")

# --- 古いデータのリセット処理 ---
if "doctors_df" in st.session_state:
    # 古い項目名やタイポした項目名が残っている場合に備えてリセット
    bad_cols = ["現在の患者数", "現患者_数"]
    if any(col in st.session_state.doctors_df.columns for col in bad_cols):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# --- サイドバー：操作マニュアル ---
with st.sidebar:
    st.header("📖 マニュアル")
    st.markdown("""
    1. **医師設定**: 「現患者数」などを入力
    2. **患者準備**: リストを入力またはCSV読込
    3. **実行**: ボタンを押して配分
    4. **保存**: 結果をCSVで保存
    """)
    st.divider()
    st.caption("ver 1.4 - タイポ修正済")

st.title("🏥 患者割り振り")

# --- 1. 初期データの設定 ---
if "doctors_df" not in st.session_state:
    st.session_state.doctors_df = pd.DataFrame([
        {"名前": "医師A", "現患者数": 8, "割振後max患者数": 15, "大変さのmaxスコア": 5},
        {"名前": "医師B", "現患者数": 3, "割振後max患者数": 15, "大変さのmaxスコア": 5},
        {"名前": "医師C", "現患者数": 2, "割振後max患者数": 15, "大変さのmaxスコア": 5},
        {"名前": "医師D", "現患者数": 1, "割振後max患者数": 15, "大変さのmaxスコア": 3},
    ])

if "patients_df" not in st.session_state:
    st.session_state.patients_df = pd.DataFrame([
        {"名前": f"患者名_{i+1:02d}", "現在の主治医": "未設定", "大変さスコア": random.randint(1, 5)} for i in range(40)
    ])

# --- 2. タブによるUI最適化（スマホ対策） ---
tab_doc, tab_pat = st.tabs(["👨‍⚕️ 医師設定", "🤒 患者リスト"])

with tab_doc:
    total_current = st.session_state.doctors_df["現患者数"].sum()
    total_new = len(st.session_state.patients_df)
    doc_count = len(st.session_state.doctors_df)
    avg_target = (total_current + total_new) / doc_count if doc_count > 0 else 0
    st.info(f"💡 全員で割ると1人あたり約 {avg_target:.1f} 名")

    doc_table_height = (len(st.session_state.doctors_df) + 2) * 36
    edited_doctors_df = st.data_editor(st.session_state.doctors_df, num_rows="dynamic", use_container_width=True, height=doc_table_height, hide_index=True, key="doctor_editor")

with tab_pat:
    uploaded_file = st.file_uploader("CSV読込", type=["csv"])
    if uploaded_file is not None:
        if st.session_state.get("last_uploaded_file_id") != uploaded_file.file_id:
            try:
                try:
                    df_uploaded = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df_uploaded = pd.read_csv(uploaded_file, encoding='shift-jis')
                required_cols = ["名前", "現在の主治医", "大変さスコア"]
                if all(col in df_uploaded.columns for col in required_cols):
                    st.session_state.patients_df = df_uploaded[required_cols]
                    if "patient_editor" in st.session_state:
                        del st.session_state["patient_editor"]
                    st.session_state["last_uploaded_file_id"] = uploaded_file.file_id
                    st.success("読込完了")
                else:
                    st.error("エラー：CSV項目が不足しています。")
            except Exception as e:
                st.error(f"読込エラー: {e}")

    pat_table_height = (len(st.session_state.patients_df) + 2) * 36
    edited_patients_df = st.data_editor(st.session_state.patients_df, num_rows="dynamic", use_container_width=True, height=pat_table_height, hide_index=True, key="patient_editor")

# --- 3. 割り振り実行 ---
st.divider()
if st.button("このデータで患者を割り振る", type="primary", use_container_width=True):
    doctors = edited_doctors_df.to_dict('records')
    patients = edited_patients_df.to_dict('records')
    allocations = {doc["名前"]: [] for doc in doctors}
    unallocated = []
    valid_patients = [p for p in patients if not (pd.isna(p.get("名前")) or pd.isna(p.get("大変さスコア")))]
    valid_patients_count = len(valid_patients)

    for doc in doctors:
        doc["新規追加スコア合計"] = 0

    patients_for_allocation = list(valid_patients)
    random.shuffle(patients_for_allocation) 
    sorted_patients = sorted(patients_for_allocation, key=lambda x: x["大変さスコア"], reverse=True)

    for p in sorted_patients:
        eligible_docs = [
            d for d in doctors 
            if d["現患者数"] < d["割振後max患者数"] and p["大変さスコア"] <= d["大変さのmaxスコア"]
        ]
        if not eligible_docs:
            unallocated.append(p)
            continue
        random.shuffle(eligible_docs)
        # ここを「現患者数」に修正しました！
        best_doc = min(eligible_docs, key=lambda d: (d["新規追加スコア合計"], d["現患者数"])) 
        best_doc["現患者数"] += 1
        best_doc["新規追加スコア合計"] += p["大変さスコア"]
        allocations[best_doc["名前"]].append(p)
    
    # --- 4. 結果表示 ---
    st.divider()
    if len(unallocated) == 0:
        st.success(f"🎉 全 {valid_patients_count} 名 完了")
    else:
        st.warning(f"⚠️ {len(unallocated)} 名 未割り当て")
    
    res_tab1, res_tab2 = st.tabs(["📊 医師合計", "📋 個別リスト"])
    
    with res_tab1:
        df_docs_final = pd.DataFrame(doctors)
        df_docs_final.rename(columns={"現患者数": "割振後総数"}, inplace=True)
        df_docs_final["追加数"] = df_docs_final["割振後総数"] - edited_doctors_df["現患者数"]
        display_df = df_docs_final[["名前", "割振後総数", "追加数", "新規追加スコア合計"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with res_tab2:
        patient_to_assigned_doc = {}
        for doc_name, assigned_list in allocations.items():
            for p in assigned_list:
                patient_to_assigned_doc[p['名前']] = doc_name
        for p in unallocated:
            patient_to_assigned_doc[p['名前']] = "⚠️ 未割り当て"

        final_patient_list = []
        for p in valid_patients:
            final_patient_list.append({
                "名前": p["名前"],
                "主治医": p.get("現在の主治医", "未設定"),
                "スコア": p["大変さスコア"],
                "新担当": patient_to_assigned_doc.get(p["名前"], "エラー")
            })
        df_final_patients = pd.DataFrame(final_patient_list)
        st.dataframe(df_final_patients, use_container_width=True, hide_index=True, height=(len(df_final_patients)+2)*36)
        
        csv = df_final_patients.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 CSV保存", data=csv, file_name='result.csv', mime='text/csv', use_container_width=True)

# 目安は邪魔にならないよう一番下に
with st.expander("ℹ️ スコア目安"):
    st.write("1:安定 / 3:標準 / 5:最重症")
