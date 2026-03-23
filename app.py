import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="患者割り振りシミュレーター", layout="wide")

st.title("🏥 患者割り振りシミュレーター")
st.write("各医師の現在の負担と制限を考慮して、新しい患者を均等に割り振ります。")

# --- 1. 初期データの設定 ---
# 医師の初期ステータス（本来はデータベース等から取得）
# max_score_allowed: 受け入れ可能な1患者あたりの最大スコア（医師Dは3までに制限）
initial_doctors = [
    {"name": "医師A", "current_patients": 8, "current_score": 24, "max_patients": 25, "max_score_allowed": 5},
    {"name": "医師B", "current_patients": 3, "current_score": 9,  "max_patients": 25, "max_score_allowed": 5},
    {"name": "医師C", "current_patients": 2, "current_score": 6,  "max_patients": 25, "max_score_allowed": 5},
    {"name": "医師D", "current_patients": 1, "current_score": 3,  "max_patients": 10, "max_score_allowed": 3},
]

# 新規患者40名（スコア1〜5をランダムに生成。本来はExcel等から読み込む）
if "new_patients" not in st.session_state:
    st.session_state.new_patients = [{"id": f"患者{i+1:02d}", "score": random.randint(1, 5)} for i in range(40)]

# --- 2. 画面UIの作成 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("👨‍⚕️ 割り振り前の医師ステータス")
    df_docs_initial = pd.DataFrame(initial_doctors)
    st.dataframe(df_docs_initial, use_container_width=True)

with col2:
    st.subheader("🤒 新規割り振り患者 (40名)")
    df_patients = pd.DataFrame(st.session_state.new_patients)
    st.dataframe(df_patients.T, use_container_width=True) # 横長で見やすく

# --- 3. 割り振りアルゴリズム実行 ---
st.divider()

if st.button("患者を割り振る", type="primary"):
    # 医師データを更新用にコピー
    doctors = [dict(doc) for doc in initial_doctors]
    
    # 割り振り結果を保存する辞書
    allocations = {doc["name"]: [] for doc in doctors}
    unallocated = []

    # ① 患者を大変さスコアが高い順（重症順）に並び替える
    sorted_patients = sorted(st.session_state.new_patients, key=lambda x: x["score"], reverse=True)

    for p in sorted_patients:
        # ② 条件を満たす医師を絞り込む
        # 条件: MAX患者数に達していない ＆ その患者のスコアが受け入れ上限以下
        eligible_docs = [
            d for d in doctors 
            if d["current_patients"] < d["max_patients"] and p["score"] <= d["max_score_allowed"]
        ]

        if not eligible_docs:
            # 誰も受け入れられない場合
            unallocated.append(p)
            continue

        # ③ 最も余裕のある医師を選ぶ
        # 優先順位1: 現在の負担スコア合計が低い
        # 優先順位2: 現在の持ち患者数が少ない
        best_doc = min(eligible_docs, key=lambda d: (d["current_score"], d["current_patients"]))

        # ④ 割り当てを実行してステータス更新
        best_doc["current_patients"] += 1
        best_doc["current_score"] += p["score"]
        allocations[best_doc["name"]].append(p)
    
    # --- 4. 結果の表示 ---
    st.success("割り振りが完了しました！")
    
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.subheader("📊 割り振り後の医師ステータス")
        df_docs_final = pd.DataFrame(doctors)
        # 割り振り前との差分をわかりやすくする
        df_docs_final["追加患者数"] = df_docs_final["current_patients"] - df_docs_initial["current_patients"]
        st.dataframe(df_docs_final, use_container_width=True)

    with res_col2:
        st.subheader("📋 各医師の新規受け入れリスト")
        for doc_name, assigned in allocations.items():
            if assigned:
                patient_texts = [f"{p['id']}(ｽｺｱ{p['score']})" for p in assigned]
                st.write(f"**{doc_name}** ({len(assigned)}名): {', '.join(patient_texts)}")
            else:
                st.write(f"**{doc_name}**: なし")
        
        if unallocated:
            st.warning(f"⚠️ 割り当てられなかった患者が {len(unallocated)} 名います。上限設定を見直してください。")