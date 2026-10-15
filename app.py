import streamlit as st
import numpy as np
import pandas as pd

# 設定網頁版面
st.set_page_config(
    page_title="台灣高資產客群動態資產韌性評估系統",
    page_icon="💰",
    layout="wide"
)

class TaiwanHNWTRetirementModel:
    def __init__(self, profile_data, stress_options):
        self.cash = profile_data.get('cash', 0)
        self.stocks = profile_data.get('stocks', 0)
        self.real_estate = profile_data.get('real_estate', 0)
        self.insurance = profile_data.get('insurance', 0)
        self.other_assets = profile_data.get('other_assets', 0)
        
        self.liquid_and_investable = self.cash + self.stocks + self.insurance + self.other_assets
        self.total_assets = self.liquid_and_investable + self.real_estate
        
        self.current_age = profile_data.get('current_age', 60)
        self.target_retire_age = profile_data.get('retire_age', 60)
        self.annual_expense = profile_data.get('annual_expense', 1200000)
        self.target_bequest = profile_data.get('target_bequest', 20000000)
        
        self.stresses = stress_options
        self.estate_exemption = 13330000 # 2026台灣遺產稅免稅額

    def simulate_paths(self):
        ages = [self.current_age, 70, 80, 90]
        
        # 1. 正常情境路徑
        normal_path = []
        curr_w_normal = self.liquid_and_investable
        for i, age in enumerate(ages):
            if i == 0:
                normal_path.append(curr_w_normal)
            else:
                years_passed = ages[i] - ages[i-1]
                for _ in range(years_passed):
                    curr_w_normal = (curr_w_normal - self.annual_expense) * 1.04
                normal_path.append(max(0, curr_w_normal))
                
        # 2. 壓力情境路徑
        stress_path = []
        curr_w_stress = self.liquid_and_investable
        liquidity_gap_age = None
        
        extra_shock = 0
        if '重大疾病' in self.stresses:
            extra_shock += 3000000
        if '長期照顧 10 年' in self.stresses:
            extra_shock += 8400000
        elif '長期照顧 5 年' in self.stresses:
            extra_shock += 4200000
        if '提前失能' in self.stresses:
            extra_shock += 2000000
            
        for i, age in enumerate(ages):
            if i == 0:
                stress_path.append(curr_w_stress)
            else:
                years_passed = ages[i] - ages[i-1]
                for y_idx in range(years_passed):
                    actual_age = ages[i-1] + y_idx + 1
                    expense = self.annual_expense
                    if 70 <= actual_age <= 75 and (extra_shock > 0):
                        expense += (extra_shock / 5)
                        
                    curr_w_stress = (curr_w_stress - expense) * 1.03
                    if curr_w_stress <= 0 and liquidity_gap_age is None:
                        liquidity_gap_age = actual_age
                        
                stress_path.append(max(0, curr_w_stress))
                
        return ages, normal_path, stress_path, liquidity_gap_age

    def calculate_resilience_score(self, stress_path, liquidity_gap_age):
        scores = {}
        
        # 1. 退休安全性
        final_stress_80 = stress_path[2]
        if final_stress_80 > self.target_bequest:
            retire_score = 20
        elif final_stress_80 > 0:
            retire_score = 15 * (final_stress_80 / self.target_bequest)
        else:
            retire_score = 0
        scores['退休安全性'] = round(max(0, min(20, retire_score)), 1)
        
        # 2. 醫療承受力
        medical_score = 20 if (self.cash + self.stocks) >= 5000000 else 10
        scores['醫療承受力'] = medical_score
        
        # 3. 長照承受力
        if any('長期照顧' in s for s in self.stresses):
            ltc_score = 12 if stress_path[-1] > 10000000 else 6
        else:
            ltc_score = 18
        scores['長照承受力'] = ltc_score
        
        # 4. 資產流動性
        re_ratio = self.real_estate / self.total_assets if self.total_assets > 0 else 0
        if re_ratio <= 0.3:
            liq_score = 20
        elif re_ratio <= 0.6:
            liq_score = 12
        else:
            liq_score = 5
        scores['資產流動性'] = liq_score
        
        # 5. 傳承流動性
        taxable_estate = self.total_assets - self.estate_exemption
        est_tax = taxable_estate * 0.10 if taxable_estate > 0 else 0
        if self.cash >= est_tax:
            bequest_score = 20
        else:
            bequest_score = 8
        scores['傳承流動性'] = bequest_score
        
        total_score = sum(scores.values())
        return total_score, scores

# --- Streamlit 介面設計 ---
st.title("🏛️ 台灣高資產客群動態資產韌性評估模型")
st.markdown("專為資產超過新台幣 3,000 萬之高資產退休/準退休族群設計，結合醫療、長照與遺產稅動態情境模擬。")
st.markdown("---")

# 側邊欄或分段輸入
st.sidebar.header("📝 客戶參數輸入面板")

with st.sidebar.expander("Step 1｜輸入資產配置 (NT$)", expanded=True):
    cash = st.number_input("現金", value=3000000, step=500000)
    stocks = st.number_input("股票／ETF", value=12000000, step=1000000)
    real_estate = st.number_input("不動產", value=40000000, step=5000000)
    insurance = st.number_input("保險現金價值", value=5000000, step=1000000)
    other_assets = st.number_input("其他資產", value=0, step=500000)

with st.sidebar.expander("Step 2｜設定人生目標", expanded=True):
    current_age = st.number_input("目前年齡", value=60, min_value=40, max_value=90)
    retire_age = st.number_input("預計退休年齡", value=65, min_value=40, max_value=95)
    annual_expense = st.number_input("每年退休生活費", value=1200000, step=100000)
    target_bequest = st.number_input("希望留下資產目標", value=20000000, step=1000000)

with st.sidebar.expander("Step 3｜設定 Stress Scenario", expanded=True):
    stress_options = []
    if st.checkbox("重大疾病"): stress_options.append('重大疾病')
    if st.checkbox("自費醫療"): stress_options.append('自費醫療')
    if st.checkbox("長期照顧 5 年"): stress_options.append('長期照顧 5 年')
    if st.checkbox("長期照顧 10 年", value=True): stress_options.append('長期照顧 10 年')
    if st.checkbox("提前失能"): stress_options.append('提前失能')

run_btn = st.sidebar.button("🚀 開始執行資產韌性模擬", type="primary")

# 主畫面結果產出
if run_btn:
    profile = {
        'cash': cash, 'stocks': stocks, 'real_estate': real_estate,
        'insurance': insurance, 'other_assets': other_assets,
        'current_age': current_age, 'retire_age': retire_age,
        'annual_expense': annual_expense, 'target_bequest': target_bequest
    }
    
    model = TaiwanHNWTRetirementModel(profile, stress_options)
    ages, normal_path, stress_path, gap_age = model.simulate_paths()
    total_score, dim_scores = model.calculate_resilience_score(stress_path, gap_age)
    re_ratio = (real_estate / model.total_assets) * 100 if model.total_assets > 0 else 0
    
    # 呈現韌性分數大卡片
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric(label="🎯 資產韌性總分 (Asset Resilience Score)", value=f"{total_score} / 100 分")
        if total_score >= 80:
            st.success("評語：資產結構穩健，具備極佳的風險抵抗力。")
        elif total_score >= 60:
            st.warning("評語：資產具一定規模，但在特定壓力情境下有流動性隱憂。")
        else:
            st.error("評語：資產韌性偏低，高度暴露於不動產卡死與長照/遺產稅缺口風險。")
            
    with col2:
        st.subheader("📊 五大維度得分拆解")
        score_df = pd.DataFrame(list(dim_scores.items()), columns=['維度', '得分 (滿分20)'])
        st.dataframe(score_df.set_index('維度').T, use_container_width=True)
        
    st.markdown("---")
    st.subheader("📈 Step 4｜系統資產變化模擬比較 (正常情境 vs. 壓力情境)")
    
    chart_data = pd.DataFrame({
        '正常情境': normal_path,
        '壓力情境 (含醫療/長照衝擊)': stress_path
    }, index=[f"{a}歲" for a in ages])
    
    st.line_chart(chart_data)
    
    # 表格對比
    comparison_df = pd.DataFrame({
        '年齡': [f"{a}歲" for a in ages],
        '正常情境 (NT$)': [f"{v:,.0f}" for v in normal_path],
        '壓力情境 (NT$)': [f"{v:,.0f}" for v in stress_path]
    })
    st.table(comparison_df)
    
    st.markdown("---")
    st.subheader("⚠️ 系統診斷與風險警示")
    if gap_age:
        st.warning(f"⚠️ **{gap_age}歲** 開始出現流動性缺口！")
    if re_ratio > 50:
        st.warning(f"⚠️ **{re_ratio:.1f}%** 的資產集中於不動產，流動性嚴重受限。")
    st.warning("⚠️ 傳承階段可能面臨現金不足以繳納遺產稅之風險。")
    
    st.markdown("---")
    st.subheader("💡 Planning Suggestions (專業規劃建議)")
    st.markdown("""
    1. **提高緊急醫療準備金**：建議增設短期高流動性固定收益或短天期債券部位。
    2. **重新調整流動資產比例**：活化不動產資產，降低不動產集中度，配置利於變現的多元金融商品。
    3. **評估醫療／長照風險轉移**：利用失能險或長照險轉移晚年龐大現金流出風險。
    4. **提前規劃傳承流動性**：利用分年贈與或保險信託，預留未來身故遺產稅源。
    """)
else:
    st.info("👈 請先在左側面板輸入客戶資產與人生目標，並勾選壓力情境後，點擊「開始執行資產韌性模擬」。")