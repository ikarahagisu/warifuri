import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="患者割り振りシミュレーター", layout="wide")

st.title("🏥 患者割り振りシミュレーター")
st.write("各医師の現在の負担と制限を考慮して、新しい患者を均等に割り振ります。表は直接クリックして文字を編集したり、一番下の行から追加、行を選択して削除（Deleteキー）が可能です。")

# --- 1. 初期データの設定（セッションステートで保持） ---
# 医師の初期データ（日本語カラム名）
if "doctors_df" not in st.session_state:
    st.session_state.doctors_df = pd.DataFrame([
        {"名前": "医師A", "現在の患者数": 8, "現在の負担スコア": 24, "上限患者数": 25, "許容最大スコア": 5},
        {"名前": "医師B", "現在の患者数": 3, "現在の負担スコア": 9,  "上限患者数": 25, "許容最大スコア": 5},
        {"名前": "医師C", "現在の患者数": 2, "現在の負担スコア": 6,  "上限患者数": 25, "許容最大スコア": 5},
        {"名前": "医師D", "現在の患者数": 1, "現在の負担スコア": 3,  "上限患者数": 10, "許容最大スコア": 3},
    ])

# 新規患者の初期データ（IDではなく名前、日本語カラム名）
if "patients_df" not in st.session_state:
    st.session_state.patients_df = pd.DataFrame([
        {"名前": f"患者名_{i+1:02d}", "大変さスコア": random.randint(1, 5)} for i in range(40)
    ])

# --- 2. 画面UIの作成（直接編集可能な表） ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("👨‍⚕️ 割り振り前の医師ステータス")
    st.write("※直接編集、行の追加・削除が可能です")
    # data_editorを使用して、動的な追加・削除を許可する
    edited_doctors_df = st.data_editor(
        st.session_state.doctors_df, 
        num_rows="dynamic", 
        use_container_width=True,
        key="doctor_editor"
    )

with col2:
    st.subheader("🤒 新規割り振り患者リスト")
    st.write("※直接編集、行の追加・削除が可能です")
    # 縦並びの表として表示し、動的な追加・削除を許可する
    edited_patients_df = st.data_editor(
        st.session_state.patients_df, 
        num_rows="dynamic", 
        use_container_width=True,
        key="patient_editor"
    )

# --- 3. 割り振りアルゴリズム実行 ---
st.divider()

if st.button("このデータで患者を割り振る", type="primary"):
    # 編集後のデータフレームを辞書のリストに変換して処理しやすくする
    doctors = edited_doctors_df.to_dict('records')
    patients = edited_patients_df.to_dict('records')
    
    # 割り振り結果を保存する辞書
    allocations = {doc["名前"]: [] for doc in doctors}
    unallocated = []

    # ① 患者を大変さスコアが高い順（重症順）に並び替える
    sorted_patients = sorted(patients, key=lambda x: x["大変さスコア"], reverse=True)

    for p in sorted_patients:
        # 空の行が追加されたままになっている場合などのエラー対策
        if pd.isna(p["名前"]) or pd.isna(p["大変さスコア"]):
            continue

        # ② 条件を満たす医師を絞り込む
        eligible_docs = [
            d for d in doctors 
            if d["現在の患者数"] < d["上限患者数"] and p["大変さスコア"] <= d["許容最大スコア"]
        ]

        if not eligible_docs:
            unallocated.append(p)
            continue

        # ③ 最も余裕のある医師を選ぶ（スコア合計 -> 現在の患者数の順で評価）
        best_doc = min(eligible_docs, key=lambda d: (d["現在の負担スコア"], d["現在の患者数"]))

        # ④ 割り当てを実行してステータス更新
        best_doc["現在の患者数"] += 1
        best_doc["現在の負担スコア"] += p["大変さスコア"]
        allocations[best_doc["名前"]].append(p)
    
    # --- 4. 結果の表示 ---
    st.success("割り振りが完了しました！")
    
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.subheader("📊 割り振り後の医師ステータス")
        df_docs_final = pd.DataFrame(doctors)
        # 割り振り前との差分を計算
        df_docs_final["追加患者数"] = df_docs_final["現在の患者数"] - edited_doctors_df["現在の患者数"]
        st.dataframe(df_docs_final, use_container_width=True)

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
