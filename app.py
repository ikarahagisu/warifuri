import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="患者割り振りシミュレーター", layout="wide")

st.title("🏥 患者割り振りシミュレーター")
st.write("各医師の現在の受け持ち人数と制限を考慮しつつ、新規患者の「大変さ」がなるべく均等になるように割り振ります。表は直接クリックして編集・追加・削除（Deleteキー）が可能です。")

with st.expander("ℹ️ 「大変さスコア」1〜5の目安について（クリックで開閉）"):
    st.markdown("""
    患者さんの受け持ち負担度を **1（最も軽い）〜 5（最も重い）の5段階** で評価します。
    ※以下の基準は目安です。実際の病棟や診療科の実情に合わせて運用してください。

    * **スコア 1（軽度）** : 状態が安定している。特別な処置が不要、または退院間近（ADL自立など）。
    * **スコア 2（やや注意）** : 1日1〜2回の定期的な観察や、軽度の処置・投薬管理が必要。
    * **スコア 3（中等度）** : 標準的な入院患者。定時の点滴や検査、一般的な病状説明（ムンテラ）がある。
    * **スコア 4（重症・手間）** : 頻回なバイタルチェックや複雑な処置が必要。または急変のリスクがやや高い。
    * **スコア 5（最重症）** : つきっきりの対応、長時間の家族ムンテラ（重い病状説明など）、または非常に高度な全身管理が必要。
    """)

# --- 1. 初期データの設定 ---
if "doctors_df" not in st.session_state:
    st.session_state.doctors_df = pd.DataFrame([
        {"名前": "医師A", "現在の患者数": 8, "上限患者数": 25, "許容最大スコア": 5},
        {"名前": "医師B", "現在の患者数": 3, "上限患者数": 25, "許容最大スコア": 5},
        {"名前": "医師C", "現在の患者数": 2, "上限患者数": 25, "許容最大スコア": 5},
        {"名前": "医師D", "現在の患者数": 1, "上限患者数": 10, "許容最大スコア": 3},
    ])

if "patients_df" not in st.session_state:
    st.session_state.patients_df = pd.DataFrame([
        {"名前": f"患者名_{i+1:02d}", "大変さスコア": random.randint(1, 5)} for i in range(40)
    ])

# --- 2. 画面UIの作成 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("👨‍⚕️ 割り振り前の医師ステータス")
    
    total_current = st.session_state.doctors_df["現在の患者数"].sum()
    total_new = len(st.session_state.patients_df)
    doc_count = len(st.session_state.doctors_df)
    avg_target = (total_current + total_new) / doc_count if doc_count > 0 else 0

    st.info(f"💡 **上限設定のヒント:** 現在の全患者({total_current}名)＋新規({total_new}名)を{doc_count}名で均等に割ると、**1人あたり約 {avg_target:.1f} 名** になります。")

    doc_table_height = (len(st.session_state.doctors_df) + 2) * 36
    edited_doctors_df = st.data_editor(
        st.session_state.doctors_df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=doc_table_height,
        hide_index=True,
        key="doctor_editor"
    )

with col2:
    st.subheader("🤒 新規割り振り患者リスト")
    
    uploaded_file = st.file_uploader("電子カルテ等から患者リスト(CSV)を読み込む", type=["csv"])
    if uploaded_file is not None:
        try:
            try:
                df_uploaded = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df_uploaded = pd.read_csv(uploaded_file, encoding='shift-jis')
            
            if "名前" in df_uploaded.columns and "大変さスコア" in df_uploaded.columns:
                st.session_state.patients_df = df_uploaded[["名前", "大変さスコア"]]
                
                if "patient_editor" in st.session_state:
                    del st.session_state["patient_editor"]
                    
                st.success("CSVを読み込みました！下の表に反映されています。")
            else:
                st.error("エラー：CSVの1行目に「名前」と「大変さスコア」という項目名が必要です。")
        except Exception as e:
            st.error(f"読み込みエラー: {e}")

    st.write("※直接編集、行の追加・削除が可能です")
    pat_table_height = (len(st.session_state.patients_df) + 2) * 36
    
    edited_patients_df = st.data_editor(
        st.session_state.patients_df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=pat_table_height,
        hide_index=True,
        key="patient_editor"
    )

# --- 3. 割り振りアルゴリズム実行 ---
st.divider()

if st.button("このデータで患者を割り振る", type="primary"):
    doctors = edited_doctors_df.to_dict('records')
    patients = edited_patients_df.to_dict('records')
    
    allocations = {doc["名前"]: [] for doc in doctors}
    unallocated = []
    
    # 割り振り対象となる有効な患者をカウントし、元の順番を保存しておく
    valid_patients = [p for p in patients if not (pd.isna(p.get("名前")) or pd.isna(p.get("大変さスコア")))]
    valid_patients_count = len(valid_patients)

    for doc in doctors:
        doc["新規追加スコア合計"] = 0

    sorted_patients = sorted(valid_patients, key=lambda x: x["大変さスコア"], reverse=True)

    for p in sorted_patients:
        eligible_docs = [
            d for d in doctors 
            if d["現在の患者数"] < d["上限患者数"] and p["大変さスコア"] <= d["許容最大スコア"]
        ]

        if not eligible_docs:
            unallocated.append(p)
            continue

        best_doc = min(eligible_docs, key=lambda d: (d["新規追加スコア合計"], d["現在の患者数"]))

        best_doc["現在の患者数"] += 1
        best_doc["新規追加スコア合計"] += p["大変さスコア"]
        allocations[best_doc["名前"]].append(p)
    
    # --- 4. 結果の表示 ---
    allocated_count = valid_patients_count - len(unallocated)
    
    if len(unallocated) == 0:
        st.success(f"🎉 完璧です！ 全 {valid_patients_count} 名の患者がもれなく割り振られました。")
    else:
        st.warning(f"⚠️ 全 {valid_patients_count} 名のうち、{allocated_count}名が割り振られましたが、条件に合わない {len(unallocated)} 名が未割り当てとなっています。")
    
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.subheader("📊 割り振り後の医師ステータス")
        df_docs_final = pd.DataFrame(doctors)
        df_docs_final.rename(columns={"現在の患者数": "割り振り後総患者数"}, inplace=True)
        df_docs_final["追加患者数"] = df_docs_final["割り振り後総患者数"] - edited_doctors_df["現在の患者数"]
        
        display_df = df_docs_final[["名前", "割り振り後総患者数", "追加患者数", "新規追加スコア合計", "上限患者数"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with res_col2:
        st.subheader("📋 各医師の新規受け入れリスト")
        
        for doc_name, assigned in allocations.items():
            if assigned:
                patient_texts = [f"{p['名前']}(ｽｺｱ{p['大変さスコア']})" for p in assigned]
                st.write(f"**{doc_name}** ({len(assigned)}名): {', '.join(patient_texts)}")
            else:
                st.write(f"**{doc_name}**: なし")
        
        if unallocated:
            st.error(f"⚠️ 未割り当ての患者リスト ({len(unallocated)} 名)")
            unallocated_names = [p['名前'] for p in unallocated]
            st.write(f"{', '.join(unallocated_names)}")

    # --- 5. 新機能：元の順番での全体照合リスト ---
    st.divider()
    st.subheader("🔍 個別患者の割り振り結果（入力順での突合用）")
    
    # 患者名から担当医を引ける辞書を作成
    patient_to_doc = {}
    for doc_name, assigned_list in allocations.items():
        for p in assigned_list:
            patient_to_doc[p['名前']] = doc_name
    for p in unallocated:
        patient_to_doc[p['名前']] = "⚠️ 未割り当て"

    # 入力時（valid_patients）の順番のままリストを作成
    final_patient_list = []
    for p in valid_patients:
        final_patient_list.append({
            "患者名": p["名前"],
            "大変さスコア": p["大変さスコア"],
            "担当医": patient_to_doc.get(p["名前"], "エラー")
        })
    
    df_final_patients = pd.DataFrame(final_patient_list)
    
    # ダウンロード用データもこの「入力順の表」をベースにする
    csv = df_final_patients.to_csv(index=False).encode('utf-8-sig')
    
    col_table, col_btn = st.columns([3, 1])
    with col_table:
        st.dataframe(df_final_patients, use_container_width=True, hide_index=True)
    with col_btn:
        st.download_button(
            label="📥 この表をCSVでダウンロード",
            data=csv,
            file_name='allocation_result_ordered.csv',
            mime='text/csv',
            use_container_width=True
        )
