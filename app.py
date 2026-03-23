import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="患者割り振りシミュレーター", layout="wide")

st.title("🏥 患者割り振りシミュレーター")
st.write("各医師の現在の受け持ち人数と制限を考慮しつつ、新規患者の「大変さ」がなるべく均等になるように割り振ります。表は直接クリックして編集・追加・削除（Deleteキー）が可能です。")

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
    st.write("※直接編集、行の追加・削除が可能です")
    
    # データ件数から表の高さを自動計算 (1行あたり約36ピクセルで計算)
    doc_table_height = (len(st.session_state.doctors_df) + 2) * 36
    
    edited_doctors_df = st.data_editor(
        st.session_state.doctors_df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=doc_table_height, # 計算した高さを指定して縦スクロールを消す
        hide_index=True,         # 左端の不要な数字(0,1,2...)を消して横幅を節約
        key="doctor_editor"
    )

with col2:
    st.subheader("🤒 新規割り振り患者リスト")
    st.write("※直接編集、行の追加・削除が可能です")
    
    # データ件数から表の高さを自動計算
    pat_table_height = (len(st.session_state.patients_df) + 2) * 36
    
    edited_patients_df = st.data_editor(
        st.session_state.patients_df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=pat_table_height, # 40名分でも縦に全表示されるように高さを指定
        hide_index=True,         # 左端の不要な数字を消して横幅を節約
        key="patient_editor"
    )

# --- 3. 割り振りアルゴリズム実行 ---
st.divider()

if st.button("このデータで患者を割り振る", type="primary"):
    doctors = edited_doctors_df.to_dict('records')
    patients = edited_patients_df.to_dict('records')
    
    allocations = {doc["名前"]: [] for doc in doctors}
    unallocated = []

    for doc in doctors:
        doc["新規追加スコア合計"] = 0

    sorted_patients = sorted(patients, key=lambda x: x["大変さスコア"], reverse=True)

    for p in sorted_patients:
        if pd.isna(p["名前"]) or pd.isna(p["大変さスコア"]):
            continue

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
    st.success("割り振りが完了しました！")
    
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.subheader("📊 割り振り後の医師ステータス")
        df_docs_final = pd.DataFrame(doctors)
        df_docs_final["追加患者数"] = df_docs_final["現在の患者数"] - edited_doctors_df["現在の患者数"]
        display_df = df_docs_final[["名前", "現在の患者数", "追加患者数", "新規追加スコア合計", "上限患者数"]]
        # 結果の表も不要な左端の数字を消す
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
            st.error(f"⚠️ 割り当てられなかった患者が {len(unallocated)} 名います。上限設定を見直してください。")
            unallocated_names = [p['名前'] for p in unallocated]
            st.write(f"未割り当て: {', '.join(unallocated_names)}")
