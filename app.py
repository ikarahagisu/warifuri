import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="患者割り振りシミュレーター", layout="wide")

# --- 古いデータのリセット処理（エラー防止） ---
if "doctors_df" in st.session_state:
    bad_cols = ["現在の患者数", "現患者_数"]
    if any(col in st.session_state.doctors_df.columns for col in bad_cols):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

st.title("🏥 患者割り振りシミュレーター")

# --- メイン画面：マニュアル常時表示 ---
st.markdown("""
### 📖 使い方マニュアル
このアプリは、病棟の新規患者を医師間で**「公平・均等」**に割り振るためのツールです。

**1. 医師の状態を設定**
左側の表で、各医師の**「現患者数」**を入力します。
* **割振後max患者数**: 上限人数です。
* **大変さのmaxスコア**: 3（重症）まで受け入れ可能か設定します。

**2. 患者リストの準備**
右側の表に、割り振りたい患者を入力します。
* **CSV読込**: 名前、現在の主治医、大変さスコア(1-3)の列が必要です。
* **直接編集**: 直接書き換え・コピペも可能です。

**3. 割り振りの実行**
中央のボタンを押すと、「新しく追加されるスコア」が均等になるよう自動計算します。
""")
st.divider()

st.write("※「新しく受け持つ患者の大変さ（スコア）」が医師間で均等になることを最優先とし、全体の「現患者数」も考慮しながら割り振ります。")

# --- 3段階スコアの目安 ---
st.info("""
**ℹ️ 「大変さスコア」1〜3の目安** （シンプルな3段階評価）
* **スコア 1（軽度）** : 状態安定。特別な処置不要、または退院間近。
* **スコア 2（中等度）** : 標準的な入院患者。定時の点滴・検査、一般的なムンテラあり。
* **スコア 3（高度）** : 頻回な観察、複雑な処置、または長時間の家族対応が必要な重症。
""")

# --- 1. 初期データの設定 ---
if "doctors_df" not in st.session_state:
    st.session_state.doctors_df = pd.DataFrame([
        {"名前": "医師A", "現患者数": 8, "割振後max患者数": 15, "大変さのmaxスコア": 3},
        {"名前": "医師B", "現患者数": 3, "割振後max患者数": 15, "大変さのmaxスコア": 3},
        {"名前": "医師C", "現患者数": 2, "割振後max患者数": 15, "大変さのmaxスコア": 3},
        {"名前": "医師D", "現患者数": 1, "割振後max患者数": 15, "大変さのmaxスコア": 2},
    ])

if "patients_df" not in st.session_state:
    st.session_state.patients_df = pd.DataFrame([
        {"名前": f"患者名_{i+1:02d}", "現在の主治医": "未設定", "大変さスコア": random.randint(1, 3)} for i in range(20)
    ])

# --- 2. 画面UIの作成 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("👨‍⚕️ 割り振り前の医師ステータス")
    total_current = st.session_state.doctors_df["現患者数"].sum()
    total_new = len(st.session_state.patients_df)
    doc_count = len(st.session_state.doctors_df)
    avg_target = (total_current + total_new) / doc_count if doc_count > 0 else 0
    
    st.success(f"💡 ヒント: 現受け持ち患者({total_current}名)＋新規({total_new}名)を{doc_count}名で割ると、1人あたり約 **{avg_target:.1f} 名** です。")

    doc_table_height = (len(st.session_state.doctors_df) + 2) * 36
    edited_doctors_df = st.data_editor(st.session_state.doctors_df, num_rows="dynamic", use_container_width=True, height=doc_table_height, hide_index=True, key="doctor_editor")

with col2:
    st.subheader("🤒 新規割り振り患者リスト")
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
                    st.success("CSVを読み込みました！")
                else:
                    st.error("エラー：CSVには「名前」「現在の主治医」「大変さスコア」が必要です。")
            except Exception as e:
                st.error(f"読み込みエラー: {e}")

    pat_table_height = (len(st.session_state.patients_df) + 2) * 36
    edited_patients_df = st.data_editor(st.session_state.patients_df, num_rows="dynamic", use_container_width=True, height=pat_table_height, hide_index=True, key="patient_editor")

# --- 3. 割り振りアルゴリズム実行 ---
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
        best_doc = min(eligible_docs, key=lambda d: (d["新規追加スコア合計"], d["現患者数"]))
        best_doc["現患者数"] += 1
        best_doc["新規追加スコア合計"] += p["大変さスコア"]
        allocations[best_doc["名前"]].append(p)
    
    # --- 4. 結果表示 ---
    st.divider()
    if len(unallocated) == 0:
        st.success(f"🎉 全 {valid_patients_count} 名の患者がもれなく割り振られました。")
    else:
        st.warning(f"⚠️ {valid_patients_count - len(unallocated)} 名完了、{len(unallocated)} 名が未割り当てです。")
    
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.subheader("📊 割り振り後の医師ステータス")
        df_docs_final = pd.DataFrame(doctors)
        df_docs_final.rename(columns={"現患者数": "割振後総患者数"}, inplace=True)
        df_docs_final["追加患者数"] = df_docs_final["割振後総患者数"] - edited_doctors_df["現患者数"]
        display_df = df_docs_final[["名前", "割振後総患者数", "追加患者数", "新規追加スコア合計"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with res_col2:
        st.subheader("📋 各医師の新規受け入れリスト")
        for doc_name, assigned in allocations.items():
            if assigned:
                patient_texts = [f"{p['名前']}(ｽｺｱ{p['大変さスコア']})" for p in assigned]
                st.write(f"**{doc_name}** ({len(assigned)}名): {', '.join(patient_texts)}")
            else:
                st.write(f"**{doc_name}**: なし")

    # --- 5. 個別患者の割り振り結果 ---
    st.divider()
    st.subheader("🔍 個別患者の割り振り結果")
    patient_to_assigned_doc = {}
    for doc_name, assigned_list in allocations.items():
        for p in assigned_list:
            patient_to_assigned_doc[p['名前']] = doc_name
    for p in unallocated:
        patient_to_assigned_doc[p['名前']] = "⚠️ 未割り当て"

    final_patient_list = []
    for p in valid_patients:
        final_patient_list.append({
            "患者名": p["名前"],
            "現在の主治医": p.get("現在の主治医", "未設定"),
            "大変さスコア": p["大変さスコア"],
            "新担当医": patient_to_assigned_doc.get(p["名前"], "エラー")
        })
    df_final_patients = pd.DataFrame(final_patient_list)
    csv = df_final_patients.to_csv(index=False).encode('utf-8-sig')
    final_table_height = (len(df_final_patients) + 2) * 36
    
    col_table, col_btn = st.columns([3, 1])
    with col_table:
        st.dataframe(df_final_patients, use_container_width=True, hide_index=True, height=final_table_height)
    with col_btn:
        st.download_button(label="📥 CSVで保存", data=csv, file_name='result.csv', mime='text/csv', use_container_width=True)
