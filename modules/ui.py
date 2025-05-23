"""
UI components for the DCF Calculator application.
"""
import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
import math
from datetime import datetime, timedelta
import plotly.express as px
from .visualization import create_dcf_visualization, create_wacc_visualization
from .utils import safe_get
from .financials import calculate_wacc, calculate_financial_ratios, calculate_two_stage_dcf
from .translations import translations, ui_translations

# Helper function to get values from financial statements with multiple possible names
def safe_get_multi(df, possible_names, column_index=0):
    """Get value from DataFrame with multiple possible row names"""
    if isinstance(possible_names, str):
        possible_names = [possible_names]
    
    if df.empty or len(df.columns) <= column_index:
        return 0
    
    for name in possible_names:
        if name in df.index:
            value = df.loc[name].iloc[column_index]
            if pd.notnull(value) and value != 0:
                return value
    
    return 0

def create_company_header(financials, financial_ratios=None, data=None):
    """
    Create the company header section with key metrics.
    
    Parameters:
    - financials: Dictionary containing company financial data
    - financial_ratios: Dictionary containing financial ratios (optional)
    - data: Dictionary containing stock data including analyst information (optional)
    """
    # Get current language
    current_lang = st.session_state.language
    # Standardize language code
    if current_lang.lower() == "english":
        current_lang = "English"
    elif current_lang.lower() == "korean" or current_lang.lower() == "한국어":
        current_lang = "한국어"
    elif current_lang.lower() == "chinese" or current_lang.lower() == "中文":
        current_lang = "中文"
    t = ui_translations[current_lang]
    
    # Company Header with recommendation
    try:
        stock = yf.Ticker(financials['ticker'])
        stock_info = stock.get_info()
        recommendation = stock_info.get('recommendationKey', 'NONE').upper()
        
        # Recommendation 표시를 위해 언더스코어(_) 제거 (STRONG_BUY → STRONG BUY)
        display_recommendation = recommendation.replace('_', ' ')
        
        # Add forward EPS and forward P/E to financials
        financials['forward_eps'] = stock_info.get('forwardEps', None)
        financials['forward_pe'] = stock_info.get('forwardPE', None)
        
        # 회사명 표시 (추천 정보는 아래에 표시)
        st.markdown(f"## {financials['company_name']}", unsafe_allow_html=True)
        
        # 업종(industry) 정보 추가
        industry = stock_info.get('industry', 'N/A')
        sector = stock_info.get('sector', 'N/A')
        # 업종 정보가 있는 경우에만 표시
        if industry != 'N/A' or sector != 'N/A':
            industry_text = f"{industry}" if industry != 'N/A' else ""
            sector_text = f"{sector}" if sector != 'N/A' else ""
            
            # 업종과 섹터 모두 있는 경우 쉼표로 구분
            display_text = ""
            if industry_text and sector_text:
                display_text = f"{industry_text} · {sector_text}"
            else:
                display_text = industry_text or sector_text
                
            st.markdown(f"<div style='font-size: 0.9em; color: #666; margin-top: -15px; margin-bottom: 10px;'>{display_text}</div>", unsafe_allow_html=True)
            
            # 업종 아래에 애널리스트 의견 표시
            if recommendation != 'NONE':
                # 애널리스트 의견 레이블 다국어 처리
                analyst_opinion_label = "Analyst Opinion"
                if current_lang == "한국어":
                    analyst_opinion_label = "애널리스트 의견"
                elif current_lang == "中文":
                    analyst_opinion_label = "分析师建议"
                
                # 추천 색상 설정 (원래 값으로 비교)
                if recommendation == 'BUY' or recommendation == 'STRONG_BUY':
                    rec_color = '#009999'
                elif recommendation == 'SELL' or recommendation == 'STRONG_SELL':
                    rec_color = '#FF0000'
                else:
                    rec_color = '#808080'
                
                # Store the analyst opinion HTML for later use (larger font)
                analyst_opinion_html = f"""
                <div style='font-size: 1.7em; margin: 5px 0 5px 0;'>{analyst_opinion_label}: <span style='color:{rec_color};'><b>{display_recommendation}</b></span></div>
                """
                
                # Store analyst count for later use (will be displayed below Average Analyst Rating)
                analyst_count = financials.get('stock_info', {}).get('numberOfAnalystOpinions', 0)
                if current_lang == "한국어":
                    analyst_count_text = f"위 의견은 애널리스트 {analyst_count}명의 의견을 반영한 매매의견입니다."
                elif current_lang == "中文":
                    analyst_count_text = f"这是{analyst_count}位分析师意见的综合评分。"
                else:
                    analyst_count_text = f"This score is based on opinions from {analyst_count} analysts."
    except Exception as e:
        st.header(financials["company_name"])
        print(f"Recommendation key error: {e}")
    
    # 업종 정보와 다음 섹션 사이의 간격 추가
    st.markdown("""<div style="height: 15px"></div>""", unsafe_allow_html=True)
    
    # Initialize analyst_count with default value
    analyst_count = 0
    analyst_count_text = ""
    
    # 더 세련된 컨테이너 스타일로 섹션을 구분
    with st.container():
        # Analyst Recommendation 섹션 - 더 세련된 디자인
        try:
            stock = yf.Ticker(financials['ticker'])
            stock_info = stock.get_info()
            
            # 분석가 등급 가져오기
            analyst_rating_raw = stock_info.get('averageAnalystRating', 'N/A')
            
            # "2.1 - Buy" 형식에서 "2.1 / 5" 형식으로 변환
            if analyst_rating_raw != 'N/A' and isinstance(analyst_rating_raw, str) and ' - ' in analyst_rating_raw:
                try:
                    rating_value = analyst_rating_raw.split(' - ')[0].strip()
                    analyst_rating = f"{rating_value} / 5.0"
                except:
                    analyst_rating = analyst_rating_raw
            else:
                analyst_rating = analyst_rating_raw
            target_high = stock_info.get('targetHighPrice', 0)
            target_low = stock_info.get('targetLowPrice', 0)
            current_price = financials['current_price']
            
            # Get target price data from stock info
            target_median = stock_info.get('targetMedianPrice', 0)
            # Get previous close from stock info
            previous_close = stock_info.get('previousClose', 0)
            price_change = ((current_price - previous_close) / previous_close * 100) if previous_close > 0 else 0
            price_change_text = f"{price_change:+.2f}%"
            price_color = "red" if price_change < 0 else "green" if price_change > 0 else "gray"
            
            # Display Price with large text and small change indicator
            st.markdown(f"""
            <div style='display: flex; 
                        align-items: flex-end; 
                        gap: 8px;
                        margin: 0 0 16px 0;'>  <!-- Reduced top margin from 8px to 0 -->
                <span style='font-size: 2.2em; 
                             color: #1E40AF;
                             letter-spacing: 0.3px;
                             line-height: 1;'>
                    ${current_price:,.2f}
                </span>
                <span style='font-size: 0.85em;
                             font-weight: 500;
                             color: {price_color};
                             display: inline-flex;
                             align-items: center;
                             margin-bottom: 4px;'>
                    <span style='margin-right: 2px; font-size: 0.9em;'>
                        {'▼' if price_change < 0 else '▲' if price_change > 0 else '•'}
                    </span>
                    {price_change_text}
                </span>
            </div>
            <div style='margin: 16px 0 24px 0; position: relative;'>  <!-- Reduced top margin from 16px to 16px, increased bottom margin to 24px -->
                <div style='position: absolute; bottom: -8px; left: 0; width: 200px; height: 2px; background: #e2e8f0;'>
                    <div style='width: 40px; height: 2px; background: #e53e3e;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add space before Analyst Opinion
            st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
            
            # Display Analyst Opinion after Current Price (larger font)
            if 'analyst_opinion_html' in locals():
                st.markdown(analyst_opinion_html, unsafe_allow_html=True)
            
            # Add extra space before ANALYST RECOMMENDATIONS
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
            
            # Check if we have valid values to display
            if analyst_rating != 'N/A' or target_high > 0 or target_low > 0 or target_median > 0:
                # Stylish header
                st.markdown(f"""<div style="text-align: left; font-weight: 500; font-size: 1.05em; 
                             color: #424242; letter-spacing: 0.5px; margin-bottom: 12px;">
                             {t['analyst_recommendations_title'].upper()}</div>""", unsafe_allow_html=True)
                
                # Section divider - thinner and more elegant (1/3 width)
                st.markdown("""<div style="height: 1px; background-color: #E0E0E0; margin-bottom: 20px; width: 33.33%;"></div>""", unsafe_allow_html=True)
                
                # Create 3 columns
                a_col1, a_col2, a_col3 = st.columns(3)
                
                # Analyst average rating with count
                with a_col1:
                    # Get analyst count from data
                    num_analysts = 0
                    if data and 'info' in data and data['info']:
                        num_analysts = data['info'].get('numberOfAnalystOpinions', 0)
                    
                    # Create a container for the metric and analyst count text
                    metric_container = st.container()
                    with metric_container:
                        st.metric(
                            t['analyst_rating_label'],
                            analyst_rating,
                            help=t['analyst_rating_help']
                        )
                        
                        # Display number of analysts in a smaller font below the rating
                        if num_analysts > 0:
                            if current_lang == '한국어':
                                st.markdown(f"<div style='color: #666666; font-size: 0.8em; margin-top: -10px;'>"
                                          f"{int(num_analysts)}명의 분석가가 평가한 점수입니다</div>", unsafe_allow_html=True)
                            elif current_lang == '中文':
                                st.markdown(f"<div style='color: #666666; font-size: 0.8em; margin-top: -10px;'>"
                                          f"这是{int(num_analysts)}位分析师给出的评分</div>", unsafe_allow_html=True)
                            else:  # English
                                st.markdown(f"<div style='color: #666666; font-size: 0.8em; margin-top: -10px;'>"
                                          f"This score is based on {int(num_analysts)} analysts' ratings</div>", unsafe_allow_html=True)
                
                # 목표 중간가 대비 현재가
                with a_col2:
                    if target_median > 0:
                        target_diff = target_median - current_price
                        target_pct = (target_diff / current_price) * 100 if current_price > 0 else 0
                        
                        st.metric(
                            t['target_median_price_label'],
                            f"${target_median:.2f}",
                            f"{target_pct:+.1f}%",
                            help=t['target_median_price_help']
                        )
                    else:
                        st.metric(t['target_median_price_label'], t['na_text'])
                
                # 목표가 범위(최대-최소)
                with a_col3:
                    if target_high > 0 and target_low > 0:
                        st.metric(
                            t['target_price_range_label'],
                            f"${target_low:.2f} - ${target_high:.2f}",
                            help=t['target_price_range_help']
                        )
                    else:
                        st.metric(t['target_price_range_label'], t['na_text'])
        except Exception as e:
            st.error(t['analyst_recommendations_error'].format(str(e)))
    
    # 섹션 사이 간격
    st.markdown("""<div style="height: 25px"></div>""", unsafe_allow_html=True)
    
    # Summarise 섹션 - 더 세련된 디자인
    with st.container():
        # 세련된 헤더 스타일
        st.markdown("""<div style="text-align: left; font-weight: 500; font-size: 1.05em; 
                     color: #424242; letter-spacing: 0.5px; margin-bottom: 12px;">
                     SUMMARISE</div>""", unsafe_allow_html=True)
        
        # 섹션 구분선 - 더 얇고 세련되게 (1/3 width)
        st.markdown("""<div style="height: 1px; background-color: #E0E0E0; margin-bottom: 20px; width: 33.33%;"></div>""", unsafe_allow_html=True)
        
        # Summarise 섹션 아래에 6개의 주요 지표를 배치
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])
    
    # Market Cap
    col1.metric(
        t['market_cap'],
        f"${financials['market_cap']/1e12:.2f} T" if financials['market_cap'] >= 1e12 else
        f"${financials['market_cap']/1e9:.2f} B" if financials['market_cap'] >= 1e9 else
        f"${financials['market_cap']/1e6:.2f} M"
    )
    
    # Enterprise Value
    enterprise_value = financials.get('enterprise_value', 0)
    col2.metric(
        t['enterprise_value'],
        f"${enterprise_value/1e12:.2f} T" if enterprise_value >= 1e12 else
        f"${enterprise_value/1e9:.2f} B" if enterprise_value >= 1e9 else
        f"${enterprise_value/1e6:.2f} M"
    )
    
    # P/E Ratio
    pe_ratio = financials.get('pe_ratio', 0)
    
    # Get P/B Ratio 
    stock = yf.Ticker(financials['ticker'])
    stock_info = stock.get_info()
    pb_ratio = stock_info.get('priceToBook', 0)
    
    # P/E Ratio with metric format
    col3.metric(
        t['pe_ratio'],
        f"{pe_ratio:.2f}" if pe_ratio and pe_ratio > 0 else "N/A"
    )
    
    # P/B Ratio with metric format
    col4.metric(
        t['pb_ratio'],
        f"{pb_ratio:.2f}" if pb_ratio and pb_ratio > 0 else "N/A"
    )
    
    # EPS
    col5.metric(
        t['eps_ttm'],
        f"${financials['eps']:.2f}"
    )
    
    # ROE
    col6.metric(
        'ROE',
        f"{financials.get('roe', 'N/A')*100:.2f}%" if isinstance(financials.get('roe'), (int, float)) else 'N/A'
    )

    st.markdown("""<div style="height: 20px"></div>""", unsafe_allow_html=True)

def render_valuation_tab(data, financials, financial_ratios):
    """Render the DCF valuation inputs and calculations"""
    st.header("DCF Valuation Model")
    # Get financial data
    income_stmt = data.get("income_stmt", pd.DataFrame())
    cash_flow = data.get("cash_flow", pd.DataFrame())
    balance_sheet = data.get("balance_sheet", pd.DataFrame())
    
    # Calculate initial FCF from financial statements if available
    initial_fcf_million = 0
    fcf_calculated = False
    
    if not cash_flow.empty and not income_stmt.empty:
        try:
            # Get the most recent year's operating cash flow
            operating_cf = safe_get_multi(cash_flow, ["Operating Cash Flow", "Cash From Operations"], 0)
            
            # Get capital expenditures (usually negative)
            capex = safe_get_multi(cash_flow, ["Capital Expenditure", "Capital Expenditures"], 0)
            
            # Make sure capex is negative for the calculation
            if capex > 0:
                capex = -capex
                
            # Calculate FCF
            calculated_fcf = operating_cf + capex
            
            # Keep the actual value
            initial_fcf_million = calculated_fcf
            fcf_calculated = True
            
        except:
            pass    

    # Use st.container instead of form to automatically calculate without a button
    # Get current language
    current_lang = st.session_state.language
    # Standardize language code
    if current_lang.lower() == "english":
        current_lang = "English"
    elif current_lang.lower() == "korean" or current_lang.lower() == "한국어":
        current_lang = "한국어"
    elif current_lang.lower() == "chinese" or current_lang.lower() == "中文":
        current_lang = "中文"
    t = ui_translations[current_lang]
    
    with st.container():
        st.subheader(t['dcf_model_params'])
        
        # 첫 번째 행: Forecast Years, Growth Rate (쿼리에 따라 Initial FCF 제거)
        row1_col1, row1_col2 = st.columns(2)
        
        # initial_fcf는 뒤에서 처리하도록 값만 유지
        initial_fcf_actual = initial_fcf_million
        initial_fcf = initial_fcf_actual  # 기존 값 유지
        
        with row1_col1:
            # Forecast Years
            forecast_years = st.number_input(
                t['forecast_years'],
                min_value=5,
                max_value=15,
                value=10,
                help=t['forecast_years_help'],
                key="forecast_years"
            )
        
        with row1_col2:
            # Calculate default growth rate based on EPS growth
            default_growth_rate = 10.0  # Default fallback value
            try:
                stock = yf.Ticker(financials['ticker'])
                yf_data = stock.info
                eps_current_year = yf_data.get("epsCurrentYear", 0)
                eps_ttm = yf_data.get("epsTrailingTwelveMonths", 0)
                
                if eps_ttm != 0:
                    calculated_growth = ((eps_current_year - eps_ttm) / eps_ttm) * 100
                    # Ensure the calculated growth is within reasonable bounds
                    default_growth_rate = max(min(calculated_growth, 100.0), -50.0)
            except Exception as e:
                print(f"Error calculating growth rate: {e}")
                # Fall back to default if there's an error
                default_growth_rate = 10.0
            
            # Growth Rate (%)
            growth_rate = st.number_input(
                t['growth_rate'],
                min_value=-50.0,
                max_value=100.0,
                value=float(default_growth_rate),
                format="%.2f",
                help=t['growth_rate_help'],
                key="growth_rate"
            ) / 100  # Convert to decimal
            
        # 두 번째 행: Terminal Years, Terminal Growth Rate
        row2_col1, row2_col2 = st.columns(2)
        
        # Get net debt (Total Debt - Total Cash)
        try:
            yf_ticker = yf.Ticker(st.session_state.current_ticker)
            yf_data = yf_ticker.info
            total_debt = yf_data.get("totalDebt", 0) or 0
            total_cash = yf_data.get("totalCash", 0) or 0
            net_debt = max(0, total_debt - total_cash)  # 음수 방지
        except Exception as e:
            print(f"Error calculating Net Debt: {e}")
            net_debt = 0.0
        
        with row2_col1:
            # Terminal Years
            terminal_years = st.number_input(
                t['terminal_years'],
                min_value=5,
                max_value=50,
                value=10,
                help=t['terminal_years_help'],
                key="terminal_years"
            )
            
        with row2_col2:
            # Terminal Growth Rate (%)
            terminal_growth_rate = st.number_input(
                t['terminal_growth'],
                min_value=-5.0,
                max_value=15.0,
                value=3.0,
                format="%.2f",
                help=t['terminal_growth_rate_help'],
                key="terminal_growth_rate"
            ) / 100  # Convert to decimal
        
        # Create three columns        # 세 번째 행: WACC, 나머지 입력 필드
        row3_col1, row3_col2 = st.columns(2)
        
        with row3_col1:
            pass  # 이미 위에서 Net Debt 코드를 생성했으므로 여기서는 빈 블록만 유지
        
        # WACC calculation section
        # WACC 파라미터 섹션 헤더
        st.subheader(t['wacc_params'])
        
        # Create three columns for WACC inputs
        wcol1, wcol2, wcol3 = st.columns(3)
        
        with wcol1:
            # Risk-free rate - 1. ^TNX에서 가져오도록 수정
            risk_free_rate_default = 3.5  # 기본값 설정
            try:
                treasury = yf.Ticker("^TNX")
                current_treasury_yield = treasury.info.get('regularMarketPrice', 0)
                if current_treasury_yield > 0:
                    risk_free_rate_default = current_treasury_yield
            except Exception as e:
                print(f"Error fetching risk-free rate from ^TNX: {e}")
                pass  # 오류 발생 시 기본값 사용
                
            risk_free_rate = st.number_input(
                t['risk_free_rate'], 
                min_value=0.0,
                max_value=10.0,
                value=float(risk_free_rate_default),
                help=t['risk_free_rate_help'],
                key="risk_free_rate"
            ) / 100  # Convert to decimal
            
            # Market risk premium
            market_risk_premium = st.number_input(
                t['market_risk_premium'],
                min_value=1.0,
                max_value=10.0,
                value=6.0,
                help=t['market_risk_premium_help'],
                key="market_risk_premium"
            ) / 100 # Convert to decimal
            
            # Get beta default
            beta_default = 1.0
            try:
                ticker = financials.get('ticker', '')
                if ticker:
                    stock = yf.Ticker(ticker)
                    stock_info = stock.info
                    beta_default = stock_info.get('beta', 1.0)
            except Exception as e:
                print(f"Error fetching beta: {e}")
                pass
            
            # Beta - editable but with calculated default and wider range
            beta = st.number_input(
                t['beta'],
                min_value=-2.0,  # Allow negative beta for inverse correlation
                max_value=5.0,   # Allow higher beta for more volatile stocks
                value=beta_default,
                help=t['beta_help'],
                key="beta"
            )
        
        with wcol2:
            # Calculate average debt from balance sheet
            average_debt = 0.0
            total_debt_values = []
            
            if not data["balance_sheet"].empty and len(data["balance_sheet"].columns) > 0:
                # 최근 3년치 debt 데이터 추출
                for col_idx in range(min(3, len(data["balance_sheet"].columns))):
                    col = data["balance_sheet"].columns[col_idx]
                    # Total Debt 직접 찾기
                    if "Total Debt" in data["balance_sheet"].index:
                        debt_value = data["balance_sheet"].loc["Total Debt", col]
                        if pd.notnull(debt_value) and debt_value > 0:
                            total_debt_values.append(debt_value)
                    # 또는 Long Term Debt + Short Term Debt 합산
                    elif "Long Term Debt" in data["balance_sheet"].index and "Short Term Debt" in data["balance_sheet"].index:
                        ltd = data["balance_sheet"].loc["Long Term Debt", col]
                        std = data["balance_sheet"].loc["Short Term Debt", col]
                        if pd.notnull(ltd) and pd.notnull(std):
                            total_debt_values.append(ltd + std)
            
            # 평균 debt 계산
            if total_debt_values:
                average_debt = sum(total_debt_values) / len(total_debt_values)
            
            # 2. Cost of Debt는 재무표에서 interest expense / average of total debt로 계산
            calculated_cod = 0.0
            
            # 이자비용 계산
            interest_expense = 0
            interest_expense_is_zero = True
            
            if not data["income_stmt"].empty:
                interest_expense = safe_get_multi(data["income_stmt"], ["Interest Expense", "Interest Expense Non Operating"], 0)
                interest_expense_is_zero = interest_expense <= 0
            
            # 이자비용과 average debt로 Cost of Debt 계산
            if not interest_expense_is_zero and average_debt > 0:
                calculated_cod = (interest_expense / average_debt) * 100  # 퍼센트로 변환
                # 합리적인 범위 체크 (1-15%)
                if calculated_cod < 1:
                    calculated_cod = 1.0
                elif calculated_cod > 15:
                    calculated_cod = 15.0
            else:
                # Fallback: risk-free rate + 2%
                calculated_cod = float(risk_free_rate_default) + 2.0
            # Show cost of debt as an editable field with calculated default
            cost_of_debt = st.number_input(
                t['cost_of_debt'],
                min_value=0.0,
                max_value=20.0,
                value=calculated_cod,
                help="Interest Expense Non Operating / average of total debt from balance sheet (4% = 0.04)",
                key="cost_of_debt"
            ) / 100  # Convert to decimal
            
            # 3. Tax rate는 tax provision / pretax income으로 계산
            calculated_tax_rate = 21.0  # 기본 세율 21%
            
            if not data["income_stmt"].empty:
                # 세전이익 및 법인세비용 데이터 가져오기
                pretax_income = safe_get_multi(data["income_stmt"], ["Pretax Income", "Income Before Tax", "Earnings Before Tax"], 0)
                tax_provision = safe_get_multi(data["income_stmt"], ["Tax Provision", "Income Tax Expense", "Tax Expense"], 0)
                
                # 유효세율 계산 (세전이익이 양수이고 법인세비용이 0 이상인 경우에만)
                if pretax_income > 0 and tax_provision >= 0:
                    effective_tax_rate = (tax_provision / pretax_income) * 100
                    # 합리적 범위 내에 있는지 확인 (5-45%)
                    if 5 <= effective_tax_rate <= 45:
                        calculated_tax_rate = effective_tax_rate
            
            # Tax rate input
            tax_rate = st.number_input(
                t['tax_rate'],
                min_value=0.0,
                max_value=50.0,
                value=float(calculated_tax_rate),  # 계산된 유효세율 사용
                help="Corporate tax rate (calculated from Tax Provision / Pretax Income)",
                key="tax_rate"
            ) / 100  # Convert to decimal
            
        with wcol3:
            # Calculate weight of debt (for default value)
            calculated_weight_of_debt = 0.0
            if not data["balance_sheet"].empty:
                total_debt = safe_get_multi(data["balance_sheet"], ["Total Debt", "Long Term Debt"], 0)
                market_cap = financials.get("market_cap", 0)
                
                if total_debt > 0 and market_cap > 0:
                    total_capital = total_debt + market_cap
                    calculated_weight_of_debt = (total_debt / total_capital) * 100  # In percentage
                else:
                    calculated_weight_of_debt = 30.0  # Default value
            
            # Show weight of debt as an editable field with calculated default
            weight_of_debt = st.number_input(
                t['weight_of_debt'],
                min_value=0.0,
                max_value=100.0,
                value=calculated_weight_of_debt,
                help=t['weight_of_debt_help'],
                key="weight_of_debt"
            ) / 100  # Convert to decimal
            
            # Tangible book value 기능 제거됨
            tangible_book_value = 0
            
            # 4. Shares outstanding은 financials.py에서 info.get("sharesOutstanding",0)의 값으로 가져오도록 수정
            shares_outstanding_actual = 0
            try:
                ticker = financials.get('ticker', '')
                if ticker:
                    stock = yf.Ticker(ticker)
                    stock_info = stock.info
                    shares_outstanding_actual = stock_info.get("sharesOutstanding", 0)
            except Exception as e:
                print(f"Error fetching shares outstanding: {e}")
                pass
            
            # Convert to millions for display in UI
            shares_outstanding_millions = shares_outstanding_actual / 1e6 if shares_outstanding_actual > 0 else 100.0
            
            # User input in millions
            shares_outstanding_input = st.number_input(
                t['shares_outstanding'],
                min_value=0.001,
                max_value=100000.0,
                value=float(max(0.001, shares_outstanding_millions)),
                format="%.2f",
                help=t['shares_outstanding_help']
            )
            
            # Convert back to actual value for calculations
            shares_outstanding = shares_outstanding_input * 1e6
        
        # Now calculate and display Weight of Equity and WACC with calculation details
        st.markdown("""
        <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
            WACC Calculation Details
            <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                <div style='width: 40px; height: 2px; background: #e53e3e;'></div>
            </div>
        </h3>
        """, unsafe_allow_html=True)
        
        # Create custom inputs dictionary for calculate_wacc
        # 사용자가 입력한 모든 WACC 파라미터를 custom_inputs 딘클래어리에 포함
        custom_inputs = {
            "cost_of_debt": cost_of_debt,
            "weight_of_debt": weight_of_debt,
            "beta": beta,
            "risk_free_rate": risk_free_rate,
            "market_risk_premium": market_risk_premium,
            "tax_rate": tax_rate,
            "user_provided": True  # 사용자가 입력한 값임을 표시
        }
        
        # Prepare financials dictionary for calculate_wacc
        financials_temp = financials.copy()
        financials_temp["beta"] = beta  # Use the beta from UI input
        financials_temp["tax_rate"] = tax_rate * 100 if tax_rate <= 1 else tax_rate  # Ensure correct format
        
        # Calculate WACC directly here without calling calculate_wacc again
        # This ensures consistency between UI inputs and calculation
        weight_of_equity = 1 - weight_of_debt
        cost_of_equity = risk_free_rate + beta * market_risk_premium
        after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
        wacc = (weight_of_equity * cost_of_equity) + (weight_of_debt * after_tax_cost_of_debt)
        
        # Create metrics in a row - 4 columns now
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric(
                t['weight_of_equity'],
                f"{weight_of_equity * 100:.2f}%",
                help=t['weight_of_equity_help']
            )
        
        with metric_col2:
            st.metric(
                t['cost_of_equity'],
                f"{cost_of_equity * 100:.2f}%",
                help=t['cost_of_equity_help']
            )
            
        with metric_col3:
            st.metric(
                t['weight_of_debt'],
                f"{weight_of_debt * 100:.2f}%",
                help=t['weight_of_debt_help']
            )
        
        with metric_col4:
            st.metric(
                t['after_tax_cost_of_debt'],
                f"{after_tax_cost_of_debt * 100:.2f}%",
                help=t['after_tax_cost_of_debt_help']
            )
        
        # Format average debt to millions or billions for display
        avg_debt_display = f"${average_debt/1e9:.2f}B" if average_debt >= 1e9 else f"${average_debt/1e6:.2f}M"
        
        # Display WACC calculation formula
        wacc_value_formatted = f"{wacc * 100:.2f}%"
        
        # Calculate components based on the original UI input values
        equity_component = weight_of_equity * cost_of_equity * 100
        debt_component = weight_of_debt * after_tax_cost_of_debt * 100
        
        # Calculate the sum directly from our components
        calculated_sum = equity_component + debt_component
        
        # 소수점 표시 제한 (최대 2자리까지)
        equity_component_formatted = f"{equity_component:.2f}%"
        debt_component_formatted = f"{debt_component:.2f}%"
        calculated_sum_formatted = f"{calculated_sum:.2f}%"
        
        # Display the WACC calculation details
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px; margin-bottom: 20px;">
            <div style="font-size: 1.2em; font-weight: 600; margin-bottom: 10px; color: #1565C0;">WACC = {wacc_value_formatted}</div>
            <div style="margin-bottom: 10px; font-weight: 500;">{t['calculation_formula']}:</div>
            <div style="margin-left: 15px; font-family: monospace; background-color: #f1f1f1; padding: 10px; border-radius: 5px;">
                WACC = (Weight of Equity × Cost of Equity) + (Weight of Debt × Cost of Debt × (1 - Tax Rate))
            </div>
            <div style="margin-top: 10px; margin-left: 15px; font-family: monospace; color: #555;">
                = ({weight_of_equity * 100:.2f}% × {cost_of_equity * 100:.2f}%) + ({weight_of_debt * 100:.2f}% × {cost_of_debt * 100:.2f}% × (1 - {tax_rate:.2f}))
                <br>= ({weight_of_equity * 100:.2f}% × {cost_of_equity * 100:.2f}%) + ({weight_of_debt * 100:.2f}% × {after_tax_cost_of_debt * 100:.2f}%)
                <br>= {equity_component_formatted} + {debt_component_formatted}
                <br>= {calculated_sum_formatted}
            </div>
            <div style="margin-top: 10px; font-size: 0.85em; color: #666;">
                <table style="border-collapse: collapse; width: 100%; margin-top: 5px;">
                    <tr>
                        <td style="padding: 5px; text-align: left; width: 200px;"><b>{t['average_debt']}:</b></td>
                        <td style="padding: 5px; text-align: left;">{avg_debt_display}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; text-align: left;"><b>{t['cost_of_debt']}:</b></td>
                        <td style="padding: 5px; text-align: left;">{cost_of_debt*100:.2f}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; text-align: left;"><b>{t['after_tax_cost_of_debt']}:</b></td>
                        <td style="padding: 5px; text-align: left;">{t['after_tax_cost_of_debt_formula']} = {after_tax_cost_of_debt*100:.2f}%</td>
                    </tr>
                </table>
                <div style="margin-top: 5px;"><b>{t['tax_rate_note'].format(tax_rate*100)}</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate DCF results for potential use elsewhere
        from .financials import calculate_two_stage_dcf
        
        # Calculate DCF with the two-stage 
        dcf_result = calculate_two_stage_dcf(
            initial_fcf * 1e6,  # Convert from millions to actual value
            growth_rate,  # Already in decimal
            terminal_growth_rate,  # Already in decimal
            wacc,  # Already in decimal
            forecast_years,  # Number of years for growth stage
            10,  # Default to 10 years for terminal stage
            net_debt * 1e6,  # Convert from millions to actual value
            shares_outstanding * 1e6,  # Convert from millions to actual value
            False,  # Always set to False (tangible book value feature removed)
            0  # tangible book value is set to 0
        )
        
        # Calculate fair value per share for potential use
        if "fair_value_per_share" in dcf_result:
            fair_value_per_share = dcf_result["fair_value_per_share"]
        elif "per_share_value" in dcf_result:
            fair_value_per_share = dcf_result["per_share_value"]
        else:
            fair_value_per_share = 0
            
        # Get current price for potential use
        current_price = financials.get("current_price", 0)
            
        # Return all parameters as a dictionary
        return {
            "initial_fcf": initial_fcf,  # Already converted to actual value
            "growth_rate": growth_rate,  # Already converted to decimal in the input section
            "terminal_growth_rate": terminal_growth_rate,  # Already converted to decimal in the input section
            "forecast_years": forecast_years,
            "terminal_years": terminal_years,  # Terminal stage years
            "wacc": wacc,  # Already in decimal form
            "risk_free_rate": risk_free_rate,  # Already converted to decimal in the input section
            "beta": beta,
            "market_risk_premium": market_risk_premium,  # Already converted to decimal in the input section
            "tax_rate": tax_rate,  # Already in decimal form
            "weight_of_debt": weight_of_debt,  # Already in decimal form
            "weight_of_equity": weight_of_equity,  # Already in decimal form
            "cost_of_equity": cost_of_equity,  # Already in decimal form
            "cost_of_debt": cost_of_debt,  # Already converted to decimal in the input section
            "net_debt": net_debt,  # Already converted to actual value
            "shares_outstanding": shares_outstanding  # Already converted to actual value
        }

def render_financials_tab(financials, financial_ratios, data, ev_ebitda_multiple=None):
    """
    Render the financials tab with key financial metrics and ratios.
    
    Parameters:
    - financials: Dictionary containing financial metrics
    - financial_ratios: Dictionary containing financial ratios
    - data: Dictionary containing stock data
    - ev_ebitda_multiple: Optional EV/EBITDA multiple from Valuation tab
    """
    # Get current language
    current_lang = st.session_state.language
    # Standardize language code
    if current_lang.lower() == "english":
        current_lang = "English"
    elif current_lang.lower() == "korean" or current_lang.lower() == "한국어":
        current_lang = "한국어"
    elif current_lang.lower() == "chinese" or current_lang.lower() == "中文":
        current_lang = "中文"
    
    # Enhanced debugging information
    print("\n=== DEBUG: Data Structure Analysis ===")
    print(f"1. Current language: {current_lang}")
    
    # Check data parameter structure
    print("\n2. Data Parameter Structure:")
    if data is None:
        print("   - data is None")
    else:
        print(f"   - Type: {type(data)}")
        print(f"   - Keys/Dir: {dir(data) if hasattr(data, '__dir__') else 'No dir'}")
        

        if hasattr(data, 'info'):
            print("   - Has 'info' attribute")
            info_data = data.info
            print(f"   - Info type: {type(info_data)}")
            if hasattr(info_data, 'keys'):
                print("   - Info keys (first 20):", list(info_data.keys())[:20])
                print("   - numberOfAnalystOpinions:", info_data.get('numberOfAnalystOpinions', 'Not found'))
                print("   - averageAnalystRating:", info_data.get('averageAnalystRating', 'Not found'))
        
        # Check if data is a dictionary
        elif isinstance(data, dict):
            print("   - Is a dictionary")
            print("   - Keys:", list(data.keys()))
            if 'info' in data:
                print("   - 'info' key exists")
                print("   - Info keys:", list(data['info'].keys()) if hasattr(data['info'], 'keys') else 'Not a dict')
    
    # Check financials parameter
    print("\n3. Financials Parameter:")
    if financials is None:
        print("   - financials is None")
    else:
        print(f"   - Type: {type(financials)}")
        if hasattr(financials, 'keys'):
            print("   - Keys (first 20):", list(financials.keys())[:20])
            print("   - numberOfAnalystOpinions:", financials.get('numberOfAnalystOpinions', 'Not found'))
            print("   - averageAnalystRating:", financials.get('averageAnalystRating', 'Not found'))
    
    print("\n")
    
    t = ui_translations[current_lang]
    
    # 재무 비율 섹션을 위한 번역 딕셔너리
    financial_section_translations = {
        'English': {
            'liquidity_title': "Liquidity Ratios",
            'profitability_title': "Profitability Ratios",
            'efficiency_title': "Efficiency Ratios",
            'leverage_title': "Leverage Ratios",
            'valuation_title': "Valuation Metrics",
            'capex_title': "CAPEX Metrics",
            'growth_title': "Growth Metrics",
            
            'current_ratio_label': "Current Ratio",
            'current_ratio_desc': "Evaluates short-term debt paying ability, calculated as current assets divided by current liabilities.",
            
            'quick_ratio_label': "Quick Ratio",
            'quick_ratio_desc': "Measures immediate liquidity, calculated as current assets minus inventory divided by current liabilities.",
            
            'gross_margin_label': "Gross Margin",
            'gross_margin_desc': "Represents gross profit as a percentage of revenue.",
            
            'operating_margin_label': "Operating Margin",
            'operating_margin_desc': "Measures operating profit as a percentage of revenue, showing operational efficiency.",
            
            'net_profit_margin_label': "Net Profit Margin",
            'net_profit_margin_desc': "Shows how much net profit is generated from each dollar of revenue.",
            
            'roa_label': "Return on Assets (ROA)",
            'roa_desc': "Measures efficiency of asset utilization in generating profits.",
            
            'roe_label': "Return on Equity (ROE)",
            'roe_desc': "Measures how efficiently a company uses shareholders' equity to generate profits.",
            
            'debt_to_equity_label': "Debt-to-Equity Ratio",
            'debt_to_equity_desc': "Ratio of debt to equity, evaluating financial stability.",
            
            'interest_coverage_label': "Interest Coverage Ratio",
            'interest_coverage_desc': "Measures ability to pay interest on debt.",
            
            'debt_ratio_label': "Debt Ratio",
            'debt_ratio_desc': "Proportion of assets financed by debt.",
            
            'equity_ratio_label': "Equity Ratio",
            'equity_ratio_desc': "Proportion of assets financed by shareholders.",
            
            'capex_to_sales_label': "CAPEX-to-Sales Ratio",
            'capex_to_sales_desc': "Shows capital expenditure relative to revenue, indicating capital intensity of the business.",
            
            'capex_to_depreciation_label': "CAPEX-to-Depreciation Ratio",
            'capex_to_depreciation_desc': "Compares capital expenditure to depreciation, indicating if the company is growing or just maintaining assets.",
            
            'cash_flow_to_capex_label': "Cash Flow to CAPEX Ratio",
            'cash_flow_to_capex_desc': "Shows how easily operating cash flow can cover capital expenditures."
        },
        '한국어': {
            'liquidity_title': "1. 유동성 비율",
            'profitability_title': "2. 수익성 비율",
            'efficiency_title': "3. 효율성 비율",
            'leverage_title': "4. 레버리지 비율",
            'valuation_title': "5. 가치평가 지표",
            'capex_title': "6. 자본지출 지표",
            'growth_title': "7. 성장성 지표",
            
            'current_ratio_label': "유동비율",
            'current_ratio_desc': "단기 채무 상환 능력을 평가하며, 유동자산을 유동부채로 나눈 값입니다.",
            
            'quick_ratio_label': "당좌비율",
            'quick_ratio_desc': "즉각적인 유동성을 평가하며, 재고를 제외한 유동자산을 유동부채로 나눈 값입니다.",
            
            'gross_margin_label': "매출총이익률",
            'gross_margin_desc': "매출에서 원가를 뺀 총이익이 매출에서 차지하는 비율입니다.",
            
            'operating_margin_label': "영업이익률",
            'operating_margin_desc': "영업활동으로 창출된 이익이 매출에서 차지하는 비율입니다.",
            
            'net_profit_margin_label': "순이익률",
            'net_profit_margin_desc': "최종 순이익이 매출에서 차지하는 비율입니다.",
            
            'roa_label': "총자산이익률 (ROA)",
            'roa_desc': "자산을 활용해 창출한 이익의 효율성을 측정합니다.",
            
            'roe_label': "자기자본이익률 (ROE)",
            'roe_desc': "주주 자본으로 창출한 이익의 효율성을 측정합니다.",
            
            'debt_to_equity_label': "부채비율 (Debt-to-Equity)",
            'debt_to_equity_desc': "자본 대비 부채의 비율로 재무 건전성을 평가합니다.",
            
            'interest_coverage_label': "이자보상비율 (Interest Coverage)",
            'interest_coverage_desc': "이자 지급 능력을 측정합니다.",
            
            'debt_ratio_label': "부채 대 자산 비율 (Debt Ratio)",
            'debt_ratio_desc': "자산 중 부채가 차지하는 비율입니다.",
            
            'equity_ratio_label': "자기자본비율 (Equity Ratio)",
            'equity_ratio_desc': "자산 중 자기자본이 차지하는 비율입니다.",
            
            'capex_to_sales_label': "자본지출 대 매출 비율",
            'capex_to_sales_desc': "매출 대비 자본지출 비율로 기업의 자본 집약도를 나타냅니다.",
            
            'capex_to_depreciation_label': "자본지출 대 감가상각비 비율",
            'capex_to_depreciation_desc': "자본지출과 감가상각비를 비교하여 기업이 자산을 유지하는지 성장시키는지 보여줍니다.",
            
            'cash_flow_to_capex_label': "현금흐름 대 자본지출 비율",
            'cash_flow_to_capex_desc': "영업현금흐름이 자본지출을 얼마나 쉽게 충당할 수 있는지 나타냅니다."
        },
        '中文': {
            'liquidity_title': "1. 流动性比率",
            'profitability_title': "2. 盈利能力比率",
            'efficiency_title': "3. 效率比率",
            'leverage_title': "4. 杠杆比率",
            'valuation_title': "5. 估值指标",
            'capex_title': "6. 资本支出指标",
            'growth_title': "7. 增长指标",
            
            'current_ratio_label': "流动比率",
            'current_ratio_desc': "评估短期偿债能力，计算为流动资产除以流动负债。",
            
            'quick_ratio_label': "速动比率",
            'quick_ratio_desc': "衡量即时流动性，计算为流动资产减去存货除以流动负债。",
            
            'gross_margin_label': "毛利率",
            'gross_margin_desc': "毛利润占收入的百分比。",
            
            'operating_margin_label': "营业利润率",
            'operating_margin_desc': "营业利润占收入的百分比，显示运营效率。",
            
            'net_profit_margin_label': "净利润率",
            'net_profit_margin_desc': "净利润占收入的百分比。",
            
            'roa_label': "资产回报率 (ROA)",
            'roa_desc': "衡量利用资产创造利润的效率。",
            
            'roe_label': "股本回报率 (ROE)",
            'roe_desc': "衡量公司利用股东资金创造利润的效率。",
            
            'debt_to_equity_label': "债务权益比 (Debt-to-Equity)",
            'debt_to_equity_desc': "衡量债务与权益的比率，评估财务稳定性。",
            
            'interest_coverage_label': "利息覆盖率 (Interest Coverage)",
            'interest_coverage_desc': "衡量支付债务利息的能力。",
            
            'debt_ratio_label': "债务比率 (Debt Ratio)",
            'debt_ratio_desc': "由债务融资的资产比例。",
            
            'equity_ratio_label': "权益比率 (Equity Ratio)",
            'equity_ratio_desc': "由股东融资的资产比例。",
            
            'capex_to_sales_label': "资本支出对销售比率",
            'capex_to_sales_desc': "显示资本支出相对于收入的比例，表明业务的资本密集程度。",
            
            'capex_to_depreciation_label': "资本支出对折旧比率",
            'capex_to_depreciation_desc': "比较资本支出和折旧，表明公司是在成长还是仅维持资产。",
            
            'cash_flow_to_capex_label': "现金流对资本支出比率",
            'cash_flow_to_capex_desc': "显示经营现金流能够多容易地覆盖资本支出。"
        }
    }
    
    # 현재 언어에 맞는 번역 선택
    ft = financial_section_translations.get(current_lang, financial_section_translations['English'])
    
    # Show the Financials tab content
    st.header(t['financial_overview'])
    
    # Create tabs for different financial statements - removed overview tab as it's redundant
    fin_tab1, fin_tab2, fin_tab3 = st.tabs([
        t['income_stmt_tab'], 
        t['balance_sheet_tab'], 
        t['cash_flow_tab']
    ])
    
    # Helper function to display ratio with status
    def display_ratio_with_status(label, value, format_string, description, status_dict, ttm_value=None, html_format=None):
        """
        Display financial ratio with status indicator.
        
        Parameters:
        - label: Label for the ratio
        - value: Numeric value of the ratio
        - format_string: Format string for the value
        - description: Description text
        - status_dict: Dictionary with level, color, and description keys
        - ttm_value: Optional TTM (Trailing Twelve Months) value to display
        - html_format: Optional HTML format string
        """
        # Get current language
        current_lang = st.session_state.language
        # Standardize language code
        if current_lang.lower() == "english":
            current_lang = "English"
        elif current_lang.lower() == "korean" or current_lang.lower() == "한국어":
            current_lang = "한국어"
        elif current_lang.lower() == "chinese" or current_lang.lower() == "中文":
            current_lang = "中文"
        
        # Handle infinite or NA values
        if (pd.isna(value) or 
            value in [float('inf'), float('-inf'), np.inf, -np.inf] or 
            (isinstance(value, (int, float)) and (value == 0 or np.isinf(value)))):
            # Show 'Not supported for this company' message
            t = translations[st.session_state.language]
            st.markdown(f"""
            <div style="margin-bottom: 20px;">
                <div style="font-size: 1.1em; font-weight: bold; color: #333;">{label}</div>
                <div style="font-size: 1em; color: #666; font-style: italic; margin: 5px 0;">
                    {t.get('ratio_not_supported', 'Not supported for this company')}
                </div>
                <div style="color: #666; font-size: 0.85em; margin-bottom: 5px;">{description}</div>
            </div>
            """, unsafe_allow_html=True)
            return
            
        # Format the value string for valid values
        try:
            formatted_value = format_string.format(value)
        except (ValueError, TypeError):
            # If formatting fails, show not supported
            t = translations[st.session_state.language]
            st.markdown(f"""
            <div style="margin-bottom: 20px;">
                <div style="font-size: 1.1em; font-weight: bold; color: #333;">{label}</div>
                <div style="font-size: 1em; color: #666; font-style: italic; margin: 5px 0;">
                    {t.get('ratio_not_supported', 'Not supported for this company')}
                </div>
                <div style="color: #666; font-size: 0.85em; margin-bottom: 5px;">{description}</div>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Apply custom HTML formatting if provided
        if html_format and value != 0:
            st.markdown(f"""
            <div style="margin-bottom: 20px;">
                <div style="font-size: 1.1em; font-weight: bold; color: #333;">{label}</div>
                <div style="font-size: 1.6em; font-weight: bold; color: #1E88E5; margin: 5px 0;">
                    {html_format.format(value)}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # If no HTML tags, use standard metric
            st.metric(label, formatted_value, delta=None, delta_color="normal")
        
        # Prepare TTM value if provided
        if ttm_value is not None:
            st.markdown(f"""<div style="font-size: 0.95em; color: #666; margin-top: 0; margin-bottom: 5px;">{ttm_value}</div>""", unsafe_allow_html=True)
        
        # 설명을 더 작고 세련되게 표시
        st.markdown(f"""<div style="color: #666; font-size: 0.85em; margin-bottom: 5px;">{description}</div>""", 
                   unsafe_allow_html=True)
        
        if status_dict and value != 0:
            # 상태 색상 맵
            color_map = {
                "red": "#FF5252",
                "orange": "#FFA726",
                "yellow": "#FFEB3B",
                "green": "#66BB6A",
                "blue": "#42A5F5",
                "purple": "#7E57C2",
                "gray": "#9E9E9E"
            }
            
            # Check if 'color' key exists in the status dictionary
            status_color = color_map.get(status_dict.get('color', 'gray'), "#9E9E9E")
            
            # Make sure other keys exist as well
            if 'level' not in status_dict:
                status_dict['level'] = 'Unknown'
            if 'description' not in status_dict:
                status_dict['description'] = 'No description available'
                
            # Language-specific level key mapping
            level_key_map = {
                'English': 'level_en',
                '한국어': 'level_ko',
                '中文': 'level_zh'
            }
            
            # Language-specific description key mapping
            desc_key_map = {
                'English': 'description_en',
                '한국어': 'description_ko', 
                '中文': 'description_zh'
            }
            
            # Get language-specific level (fallback chain: current language → language-specific level → English → default level)
            current_lang_level_key = level_key_map.get(current_lang, 'level_en')
            if current_lang_level_key in status_dict and status_dict[current_lang_level_key]:
                current_status_level = status_dict[current_lang_level_key]
            elif 'level_en' in status_dict and status_dict['level_en']:
                current_status_level = status_dict['level_en']
            else:
                current_status_level = status_dict['level']
                
            # Get language-specific description (fallback chain: current language → language-specific description → English → default description)
            current_lang_desc_key = desc_key_map.get(current_lang, 'description_en')
            if current_lang_desc_key in status_dict and status_dict[current_lang_desc_key]:
                current_status_desc = status_dict[current_lang_desc_key]
            elif 'description_en' in status_dict and status_dict['description_en']:
                current_status_desc = status_dict['description_en']
            else:
                current_status_desc = status_dict['description']
            
            st.markdown(f"""
            <div style="
                border-left: 4px solid {status_color}; 
                padding: 10px; 
                margin: 10px 0 20px 0;
                background-color: rgba({int(status_color[1:3], 16)}, {int(status_color[3:5], 16)}, {int(status_color[5:7], 16)}, 0.1);
                border-radius: 4px;
            ">
                <div style="font-weight: bold; margin-bottom: 5px; display: flex; align-items: center;">
                    <span style="
                        display: inline-block;
                        width: 10px;
                        height: 10px;
                        background-color: {status_color};
                        border-radius: 50%;
                        margin-right: 8px;
                    "></span>
                    <span style="color: {status_color};">{current_status_level}</span>
                </div>
                <div style="font-size: 0.95em; line-height: 1.5;">
                    {current_status_desc}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Get analyst data for the top section
    analyst_data = {}
    if data and 'info' in data and data['info']:
        analyst_data = {
            'numberOfAnalystOpinions': data['info'].get('numberOfAnalystOpinions', 0),
            'averageAnalystRating': data['info'].get('averageAnalystRating', ''),
            'recommendationKey': data['info'].get('recommendationKey', ''),
            'targetMeanPrice': data['info'].get('targetMeanPrice', 0),
            'currentPrice': data['info'].get('currentPrice', 0),
            'targetHighPrice': data['info'].get('targetHighPrice', 0),
            'targetLowPrice': data['info'].get('targetLowPrice', 0)
        }
        
    
    # Financial Highlights section - shown under each tab
    st.markdown("""<div style="text-align: left; font-weight: bold; font-size: 1.5em; color: #004C99; 
                      padding: 10px 10px 0px 10px; margin-bottom: 0px; margin-top: 20px;">
                      Financial Highlights</div>""", unsafe_allow_html=True)
    
    # Get key metrics from financial statements
    if not data["income_stmt"].empty and not data["balance_sheet"].empty and not data["cash_flow"].empty:
        # Get current language
        current_lang = st.session_state.language
        # Standardize language code
        if current_lang.lower() == "english":
            current_lang = "English"
            fiscal_year_label = " * Fiscal Year:"
        elif current_lang.lower() == "korean" or current_lang.lower() == "한국어":
            current_lang = "한국어"
            fiscal_year_label = " * 회계연도:"
        elif current_lang.lower() == "chinese" or current_lang.lower() == "中文":
            current_lang = "中文"
            fiscal_year_label = " * 财政年度:"
        
        # Display fiscal year date - only the most recent one, left-aligned, between title and border
        if len(data["income_stmt"].columns) > 0:
            # 가장 최근 회계연도 하나만 가져오기
            most_recent_year = data["income_stmt"].columns[0]
            
            # 날짜 형식 변환: YYYY-MM-DD 00:00:00 -> YYYY.MM.DD
            try:
                # 문자열에서 날짜 부분만 추출해서 형식 변환
                date_str = str(most_recent_year).split()[0]  # YYYY-MM-DD 부분만 가져오기
                year_month_day = date_str.split('-')
                if len(year_month_day) == 3:
                    formatted_date = f"{year_month_day[0]}.{year_month_day[1]}.{year_month_day[2]}"
                else:
                    formatted_date = str(most_recent_year)
            except:
                formatted_date = str(most_recent_year)
            
            # Store fiscal year information for later display
            fiscal_year_info = f"{fiscal_year_label} {formatted_date}"
            
            # Display the border
            st.markdown("""<div style='border-bottom: 2px solid #004C99; margin: 5px 0px 20px 0px;'></div>""", unsafe_allow_html=True)
        
        # Create a stylish overview dashboard with 3 columns for each statement
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""<div style="text-align: center; font-weight: bold; font-size: 1.1em; color: #1E88E5; 
                         padding: 10px; border-bottom: 2px solid #1E88E5; margin-bottom: 15px;">
                         Income Statement Highlights</div>""", unsafe_allow_html=True)
            
            # Extract key income statement metrics
            revenue = safe_get_multi(data["income_stmt"], ["Total Revenue", "Revenue", "Sales"], 0)
            prev_revenue = safe_get_multi(data["income_stmt"], ["Total Revenue", "Revenue", "Sales"], 1)
            
            gross_profit = safe_get_multi(data["income_stmt"], ["Gross Profit"], 0)
            operating_income = safe_get_multi(data["income_stmt"], ["Operating Income", "EBIT"], 0)
            net_income = safe_get_multi(data["income_stmt"], ["Net Income", "Net Income Common Stockholders"], 0)
            
            # Revenue
            growth_pct = ((revenue / prev_revenue) - 1) * 100 if prev_revenue > 0 else 0
            st.metric(
                "Revenue", 
                f"${revenue/1e9:.2f}B" if revenue >= 1e9 else f"${revenue/1e6:.2f}M",
                f"{growth_pct:.1f}%" if growth_pct != 0 else None,
                help="Total sales generated by the company"
            )
            
            # Gross Profit Margin - Use value from financial_ratios if available
            gross_margin = financial_ratios.get("gross_margin", 0)
            if gross_margin == 0 and revenue > 0:
                gross_margin = gross_profit / revenue
            st.metric(
                "Gross Profit Margin", 
                f"{gross_margin*100:.1f}%",
                help="Percentage of revenue left after accounting for cost of goods sold"
            )
            
            # Operating Margin - Use value from financial_ratios if available
            operating_margin = financial_ratios.get("operating_margin", 0)
            if operating_margin == 0 and revenue > 0:
                operating_margin = operating_income / revenue
            st.metric(
                "Operating Margin", 
                f"{operating_margin*100:.1f}%",
                help="Percentage of revenue left after operating expenses"
            )
            
            # Net Profit Margin - Use value from financial_ratios if available
            net_margin = financial_ratios.get("net_profit_margin", 0)
            if net_margin == 0 and revenue > 0:
                net_margin = net_income / revenue
            st.metric(
                "Net Profit Margin", 
                f"{net_margin*100:.1f}%",
                help="Percentage of revenue that becomes profit"
            )
        
        with col2:
            st.markdown("""<div style="text-align: center; font-weight: bold; font-size: 1.1em; color: #43A047; 
                         padding: 10px; border-bottom: 2px solid #43A047; margin-bottom: 15px;">
                         Balance Sheet Highlights</div>""", unsafe_allow_html=True)
            
            # 기존에 계산된 값 사용 또는 Balance Sheet에서 가져오기
            # financial_ratios에서 이미 계산된 값이 있는지 확인
            total_assets = financial_ratios.get("total_assets", 0)
            total_liabilities = financial_ratios.get("total_liabilities", 0)
            total_equity = financial_ratios.get("total_equity", 0)
            cash_and_equivalents = financial_ratios.get("cash", 0)
            total_debt = financial_ratios.get("total_debt", 0)
            
            # 계산된 값이 0인 경우 balance sheet에서 직접 가져오기
            if total_assets == 0:
                total_assets = safe_get_multi(data["balance_sheet"], ["Total Assets"], 0)
            if total_liabilities == 0:
                total_liabilities = safe_get_multi(data["balance_sheet"], ["Total Liabilities", "Total Liabilities Net Minority Interest"], 0)
            if total_equity == 0:
                total_equity = safe_get_multi(data["balance_sheet"], ["Total Equity", "Total Stockholder Equity", "Stockholders' Equity"], 0)
            if cash_and_equivalents == 0:
                cash_and_equivalents = safe_get_multi(data["balance_sheet"], ["Cash And Cash Equivalents", "Cash and Short Term Investments"], 0)
            if total_debt == 0:
                total_debt = safe_get_multi(data["balance_sheet"], ["Total Debt", "Long Term Debt"], 0)
            
            # Total Assets
            st.metric(
                "Total Assets", 
                f"${total_assets/1e9:.2f}B" if total_assets >= 1e9 else f"${total_assets/1e6:.2f}M",
                help="Everything the company owns"
            )
            
            # Cash & Equivalents
            cash_pct = cash_and_equivalents / total_assets * 100 if total_assets > 0 else 0
            st.metric(
                "Cash & Equivalents", 
                f"${cash_and_equivalents/1e9:.2f}B" if cash_and_equivalents >= 1e9 else f"${cash_and_equivalents/1e6:.2f}M",
                f"{cash_pct:.1f}% of Assets" if cash_pct > 0 else None,
                help="Highly liquid assets available for immediate use"
            )
            
            # Debt-to-Equity - financial_ratios에 있는 값 사용
            # Leverage Ratios 섹션과 동일한 데이터 소스 사용
            debt_to_equity = financial_ratios.get('debt_to_equity', 0)
            
            # financial_ratios에 값이 없을 경우 직접 계산
            if debt_to_equity == 0:
                debt_to_equity = total_debt / total_equity if total_equity > 0 else 0
                
                # 만약 debt_to_equity가 수치적으로 이상한 값이면 보정
                if not 0 <= debt_to_equity < 1000:
                    # 너무 크거나 음수인 경우
                    if total_debt > 0 and total_equity > 0:
                        debt_to_equity = total_debt / total_equity
                    else:
                        debt_to_equity = 0
            
            # debt_to_equity 값에 x 표시 추가
            debt_to_equity_display = f"{debt_to_equity:.2f}x" if 0 <= debt_to_equity < 1000 else "N/A"
            
            st.metric(
                "Debt-to-Equity", 
                debt_to_equity_display,
                help="Ratio of total debt to shareholders' equity"
            )
            
            # Equity Ratio (자기자본비율) 계산 - Total Equity / Total Assets
            # financial_ratios에서 직접 가져오기 (있는 경우)
            equity_ratio = financial_ratios.get('equity_ratio', 0)
            
            # financial_ratios에 없으면 직접 계산 (이전과 동일한 로직이지만 데이터 유효성 검사 강화)
            if equity_ratio == 0 and total_assets > 0:
                # 자기자본이 음수인 경우도 처리 (재무상 어려움에 처한 기업의 경우 발생 가능)
                if total_equity <= 0:
                    equity_ratio = 0  # 자기자본이 0 이하면 0%로 표시
                else:
                    # 자기자본비율 = 자기자본 / 총자산 * 100%
                    equity_ratio = (total_equity / total_assets) * 100
                    
                    # 유효성 검사 - 비율은 0-100% 범위 내에 있어야 함
                    if equity_ratio > 100:
                        # 데이터 불일치로 100%를 초과하는 경우 100%로 제한
                        equity_ratio = 100
            st.metric(
                "Equity Ratio", 
                f"{equity_ratio*100:.1f}%",
                help="Ratio of shareholders' equity to total assets"
            )
        
        with col3:
            st.markdown("""<div style="text-align: center; font-weight: bold; font-size: 1.1em; color: #FB8C00; 
                         padding: 10px; border-bottom: 2px solid #FB8C00; margin-bottom: 15px;">
                         Cash Flow Highlights</div>""", unsafe_allow_html=True)
            
            # Extract key cash flow metrics
            operating_cash_flow = safe_get_multi(data["cash_flow"], ["Operating Cash Flow", "Total Cash From Operating Activities"], 0)
            capital_expenditure = safe_get_multi(data["cash_flow"], ["Capital Expenditure", "Purchases Of Plant Property And Equipment"], 0)
            
            # Make capex negative if positive (accounting convention)
            if capital_expenditure > 0:
                capital_expenditure = -capital_expenditure
                
            free_cash_flow = operating_cash_flow + capital_expenditure
            
            # Operating Cash Flow
            ocf_margin = operating_cash_flow / revenue if revenue > 0 else 0
            st.metric(
                "Operating Cash Flow", 
                f"${operating_cash_flow/1e9:.2f}B" if operating_cash_flow >= 1e9 else f"${operating_cash_flow/1e6:.2f}M",
                f"{ocf_margin:.1f}% of Revenue" if ocf_margin > 0 else None,
                help="Cash generated from core business operations"
            )
            
            # Capital Expenditure
            capex_pct = abs(capital_expenditure) / revenue * 100 if revenue > 0 else 0
            st.metric(
                "Capital Expenditure", 
                f"${capital_expenditure/1e9:.2f}B" if abs(capital_expenditure) >= 1e9 else f"${capital_expenditure/1e6:.2f}M",
                f"{capex_pct:.1f}% of Revenue" if capex_pct > 0 else None,
                help="Investments in long-term assets (negative value indicates cash outflow)"
            )
            
            # Free Cash Flow
            fcf_margin = free_cash_flow / revenue if revenue > 0 else 0
            st.metric(
                "Free Cash Flow", 
                f"${free_cash_flow/1e9:.2f}B" if free_cash_flow >= 1e9 else f"${free_cash_flow/1e6:.2f}M",
                f"{fcf_margin:.1f}% of Revenue" if fcf_margin > 0 else None,
                help="Cash available after operations and capital expenditures"
            )
            
            # FCF to Net Income
            fcf_to_ni = free_cash_flow / net_income if net_income > 0 else 0
            st.metric(
                "FCF to Net Income", 
                f"{fcf_to_ni:.2f}x",
                help="Ratio of free cash flow to net income, indicates earnings quality"
            )
    
    # Display fiscal year information below the financial highlights with left alignment
    if 'fiscal_year_info' in locals():
        st.markdown(f"""<div style='text-align: left; color: #555; font-size: 0.9em; padding: 10px 0; margin: 0;'>
                      {fiscal_year_info}</div>""", unsafe_allow_html=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Now display the detailed financial ratios
    if financial_ratios:
        # Forward PER 및 EPS 섹션 추가 
        with st.expander(t['forward_pe_eps_title'], expanded=True):
            st.markdown(f"""<div style="font-weight: bold; font-size: 1.2em; color: #1E88E5;">{t['forward_pe_eps_metrics']}</div>""", unsafe_allow_html=True)
            
            # Financial ratios display
            
            # Single row for Forward P/E and Forward EPS
            cols = st.columns(2)
            
            # Forward P/E section
            with cols[0]:

                ttm_pe = financials.get('pe_ratio', 0)  
                forward_pe = financials.get('forward_pe', 0) 
                pe_status = None

                if ttm_pe and forward_pe and ttm_pe > 0 and not math.isnan(ttm_pe) and not math.isnan(forward_pe):
                    if forward_pe > ttm_pe:
                        pe_status = {
                            'level': 'Growth Expected', 
                            'level_en': 'Growth Expected', 
                            'level_ko': '성장 기대', 
                            'level_zh': '增长预期',
                            'color': 'green', 
                            'description': 'Forward P/E is higher than TTM P/E, indicating positive growth expectations.',
                            'description_en': 'Forward P/E is higher than TTM P/E, indicating positive growth expectations.',
                            'description_ko': 'Forward P/E가 TTM P/E보다 높아 미래 성장 기대.',
                            'description_zh': '预期市盈率高于TTM市盈率，表明积极的增长预期。'
                        }
                    elif forward_pe < ttm_pe:
                        pe_status = {
                            'level': 'Potential Decline', 
                            'level_en': 'Potential Decline',
                            'level_ko': '감소 기대',
                            'level_zh': '潜在下降',
                            'color': 'red', 
                            'description': 'Forward P/E is lower than TTM P/E, indicating potential decreased expectations.',
                            'description_en': 'Forward P/E is lower than TTM P/E, indicating potential decreased expectations.',
                            'description_ko': 'Forward P/E가 TTM P/E보다 낮아 잠재적 위협.',
                            'description_zh': '预期市盈率低于TTM市盈率，表明可能的预期下降。'
                        }
                    else:
                        pe_status = {
                            'level': 'Stable', 
                            'level_en': 'Stable', 
                            'level_ko': '안정',
                            'level_zh': '稳定',
                            'color': 'gray', 
                            'description': 'Forward P/E is similar to TTM P/E, indicating stable expectations.',
                            'description_en': 'Forward P/E is similar to TTM P/E, indicating stable expectations.',
                            'description_ko': 'Forward P/E가 TTM P/E와 유사.',
                            'description_zh': '预期市盈率与TTM市盈率相似，表明稳定的预期。'
                        }
                    
                    display_ratio_with_status(
                        t['forward_pe_label'], 
                        forward_pe, 
                        f'{forward_pe:.2f}x', 
                        t['forward_pe_help'], 
                        pe_status, 
                        ttm_value=f'{t["ttm_label"]}: {ttm_pe:.2f}'
                    )
                else:
                    st.metric(t['forward_pe_label'], t['na_text'], help=t['forward_pe_help'])
            
            # Forward EPS section
            with cols[1]:
                forward_eps = financials.get('forward_eps', 0) 
                ttm_eps = financials.get('eps', 0) 
                eps_status = None

                if forward_eps and ttm_eps and ttm_eps != 0 and not math.isnan(forward_eps) and not math.isnan(ttm_eps):
                    eps_change_ttm = (forward_eps - ttm_eps) / ttm_eps * 100
                    if forward_eps > ttm_eps:
                        eps_status = {
                            'level': 'Positive Growth Outlook', 
                            'level_en': 'Positive Growth Outlook', 
                            'level_ko': '성장 전망 긍정적',
                            'level_zh': '积极增长前景',
                            'color': 'green', 
                            'description': 'Market expects future earnings to improve.',
                            'description_en': 'Market expects future earnings to improve.',
                            'description_ko': '시장은 미래 수익이 개선될 것으로 예상합니다.',
                            'description_zh': '市场预计未来收益将有所改善。'
                        }
                    elif forward_eps < ttm_eps:
                        eps_status = {
                            'level': 'Potential Performance Challenges', 
                            'level_en': 'Potential Performance Challenges', 
                            'level_ko': '잠재적 실적 저하 우려',
                            'level_zh': '潜在的业绩挣扑',
                            'color': 'red', 
                            'description': 'Market anticipates potential earnings decline.',
                            'description_en': 'Market anticipates potential earnings decline.',
                            'description_ko': '시장은 향후 수익 감소 가능성을 예상합니다.',
                            'description_zh': '市场预计潜在的收益下降。'
                        }
                    else:
                        eps_status = {
                            'level': 'Stable Earnings Projection', 
                            'level_en': 'Stable Earnings Projection', 
                            'level_ko': '안정적 수익 전망',
                            'level_zh': '稳定盈利预测',
                            'color': 'gray', 
                            'description': 'Forward EPS consistent with current performance.',
                            'description_en': 'Forward EPS consistent with current performance.',
                            'description_ko': '예상 EPS가 현재 실적과 일치합니다.',
                            'description_zh': '预期每股收益与当前表现一致。'
                        }
                    
                    display_ratio_with_status(
                        t['forward_eps_label'], 
                        forward_eps, 
                        f'${forward_eps:.2f}', 
                        t['forward_eps_help'], 
                        eps_status, 
                        ttm_value=f'{t["ttm_label"]}: ${ttm_eps:.2f}'
                    )
                else:
                    st.metric(t['forward_eps_label'], t['na_text'], help=t['forward_eps_help'])
        
        # 1. 유동성 비율 (Liquidity Ratios)
        with st.expander(ft['liquidity_title'], expanded=True):
            st.markdown(f"""<div style="font-weight: bold; font-size: 1.2em; color: #0277BD;">{ft['liquidity_title']}</div>""", unsafe_allow_html=True)
            cols = st.columns(2)
            
            with cols[0]:
                # Current Ratio - Using value from financial_ratios (already fetched in financials.py)
                ratio_value = financial_ratios.get('current_ratio', 0)
                status_dict = financial_ratios.get('current_ratio_status')
                display_ratio_with_status(
                    ft['current_ratio_label'], 
                    ratio_value, 
                    "{:.2f}x", 
                    ft['current_ratio_desc'], 
                    status_dict
                )
            
            with cols[1]:
                # Quick Ratio - 오른쪽 컬럼으로 이동
                ratio_value = financial_ratios.get('quick_ratio', 0)
                status_dict = financial_ratios.get('quick_ratio_status')
                display_ratio_with_status(
                    ft['quick_ratio_label'], 
                    ratio_value, 
                    "{:.2f}x", 
                    ft['quick_ratio_desc'], 
                    status_dict
                )
        
        # 2. 수익성 비율 (Profitability Ratios)
        with st.expander(ft['profitability_title'], expanded=True):
            st.markdown(f"""<div style="font-weight: bold; font-size: 1.2em; color: #43A047;">{ft['profitability_title']}</div>""", unsafe_allow_html=True)
            cols = st.columns(2)
            
            with cols[0]:
                ratio_value = financial_ratios.get('gross_margin', 0)
                status_dict = financial_ratios.get('gross_margin_status')
                display_ratio_with_status(
                    ft['gross_margin_label'], 
                    ratio_value * 100, 
                    "{:.2f}%", 
                    ft['gross_margin_desc'], 
                    status_dict
                )
                
                ratio_value = financial_ratios.get('operating_margin', 0)
                status_dict = financial_ratios.get('operating_margin_status')
                display_ratio_with_status(
                    ft['operating_margin_label'], 
                    ratio_value * 100, 
                    "{:.2f}%", 
                    ft['operating_margin_desc'], 
                    status_dict
                )
                
                # ROA - Using value from financial_ratios (already fetched in financials.py)
                ratio_value = financial_ratios.get('roa', 0)
                ratio_value_display = ratio_value * 100
                status_dict = financial_ratios.get('roa_status')
                display_ratio_with_status(
                    ft['roa_label'], 
                    ratio_value_display, 
                    "{:.2f}%", 
                    ft['roa_desc'], 
                    status_dict
                )
            
            with cols[1]:
                ratio_value = financial_ratios.get('net_profit_margin', 0)
                status_dict = financial_ratios.get('net_profit_status')  # 변경된 키 이름 참조
                display_ratio_with_status(
                    ft['net_profit_margin_label'], 
                    ratio_value * 100, 
                    "{:.2f}%", 
                    ft['net_profit_margin_desc'], 
                    status_dict
                )
                
                # Earnings Growth - Using either yf_eps_growth from financial_ratios or net_income_growth
                if 'yf_eps_growth' in financial_ratios and financial_ratios['yf_eps_growth'] != 0:
                    # Use EPS growth as calculated in financials.py
                    earnings_growth = financial_ratios['yf_eps_growth']
                    status_dict = financial_ratios.get('yf_eps_growth_status')
                    
                    display_ratio_with_status(
                        t['earnings_growth_label'], 
                        earnings_growth, 
                        "{:.2f}%", 
                        t['earnings_growth_help'], 
                        status_dict
                    )
                    
                elif 'net_income_growth' in financial_ratios and financial_ratios['net_income_growth'] != 0:
                    # Fallback to net income growth
                    earnings_growth = financial_ratios['net_income_growth']
                    status_dict = financial_ratios.get('net_income_growth_status')
                    
                    display_ratio_with_status(
                        t['earnings_growth_label'], 
                        earnings_growth, 
                        "{:.2f}%", 
                        t['earnings_growth_help'], 
                        status_dict
                    )
                # No need for exception handling as we're not making external API calls
                
                # ROE - Using value from financial_ratios (already fetched in financials.py)
                ratio_value = financial_ratios.get('roe', 0)
                ratio_value_display = ratio_value * 100
                status_dict = financial_ratios.get('roe_status')
                display_ratio_with_status(
                    ft['roe_label'], 
                    ratio_value_display, 
                    "{:.2f}%", 
                    ft['roe_desc'], 
                    status_dict
                )
        
        # 3. 효율성 비율 (Efficiency Ratios)
        with st.expander(ft['efficiency_title'], expanded=True):
            st.markdown(f"""<div style="font-weight: bold; font-size: 1.2em; color: #7B1FA2;">{ft['efficiency_title']}</div>""", unsafe_allow_html=True)
            cols = st.columns(2)
            
            # Add translations for efficiency metrics
            efficiency_translations = {
                'English': {
                    'asset_turnover_label': "Asset Turnover",
                    'asset_turnover_desc': "Measures how efficiently assets are used to generate revenue.",
                    'inventory_turnover_label': "Inventory Turnover",
                    'inventory_turnover_desc': "Shows how quickly inventory is sold.",
                    'receivables_turnover_label': "Receivables Turnover",
                    'receivables_turnover_desc': "Indicates how quickly receivables are collected.",
                    'days_sales_outstanding_label': "Days Sales Outstanding",
                    'days_sales_outstanding_desc': "Average number of days to collect receivables.",
                    'days_inventory_label': "Days Inventory",
                    'days_inventory_desc': "Average number of days inventory is held before being sold.",
                    'days_suffix': "days"
                },
                '한국어': {
                    'asset_turnover_label': "자산회전율 (Asset Turnover)",
                    'asset_turnover_desc': "자산을 활용해 매출을 창출하는 효율성을 측정합니다.",
                    'inventory_turnover_label': "재고회전율 (Inventory Turnover)",
                    'inventory_turnover_desc': "재고를 얼마나 빨리 판매하는지를 나타냅니다.",
                    'receivables_turnover_label': "매출채권회전율 (Receivables Turnover)",
                    'receivables_turnover_desc': "매출채권을 얼마나 빨리 회수하는지를 나타냅니다.",
                    'days_sales_outstanding_label': "매출채권 회수기간 (Days Sales Outstanding)",
                    'days_sales_outstanding_desc': "매출채권을 회수하는 데 평균적으로 걸리는 일수입니다.",
                    'days_inventory_label': "재고 보유 일수 (Days Inventory)",
                    'days_inventory_desc': "재고가 판매되기까지 평균적으로 보유하는 일수입니다.",
                    'days_suffix': "일"
                },
                '中文': {
                    'asset_turnover_label': "资产周转率 (Asset Turnover)",
                    'asset_turnover_desc': "衡量利用资产创造收入的效率。",
                    'inventory_turnover_label': "存货周转率 (Inventory Turnover)",
                    'inventory_turnover_desc': "显示存货销售速度。",
                    'receivables_turnover_label': "应收账款周转率 (Receivables Turnover)",
                    'receivables_turnover_desc': "表明应收账款收回速度。",
                    'days_sales_outstanding_label': "应收账款周转天数 (Days Sales Outstanding)",
                    'days_sales_outstanding_desc': "收回应收账款的平均天数。",
                    'days_inventory_label': "存货周转天数 (Days Inventory)",
                    'days_inventory_desc': "存货在售出前的平均持有天数。",
                    'days_suffix': "天"
                }
            }
            
            # Get translations for current language (using the standardized language code from parent function)
            ef_t = efficiency_translations.get(current_lang, efficiency_translations['English'])
            
            # Row 1: Asset Turnover and Inventory Turnover
            with cols[0]:
                ratio_value = financial_ratios.get('asset_turnover', 0)
                status_dict = financial_ratios.get('asset_turnover_status')
                display_ratio_with_status(
                    ef_t['asset_turnover_label'], 
                    ratio_value, 
                    "{:.2f}", 
                    ef_t['asset_turnover_desc'], 
                    status_dict
                )
            
            with cols[1]:
                ratio_value = financial_ratios.get('inventory_turnover', 0)
                status_dict = financial_ratios.get('inventory_turnover_status')
                display_ratio_with_status(
                    ef_t['inventory_turnover_label'], 
                    ratio_value, 
                    "{:.2f}", 
                    ef_t['inventory_turnover_desc'], 
                    status_dict
                )
            
            # Row 2: Receivables Turnover (only in the left column)
            cols2 = st.columns(2)
            with cols2[0]:
                ratio_value = financial_ratios.get('receivables_turnover', 0)
                status_dict = financial_ratios.get('receivables_turnover_status')
                display_ratio_with_status(
                    ef_t['receivables_turnover_label'], 
                    ratio_value, 
                    "{:.2f}", 
                    ef_t['receivables_turnover_desc'], 
                    status_dict
                )
            
            # Row 3: Days Sales Outstanding and Days Inventory side by side
            cols3 = st.columns(2)
            with cols3[0]:
                ratio_value = financial_ratios.get('days_sales_outstanding', 0)
                status_dict = financial_ratios.get('days_sales_outstanding_status')
                display_ratio_with_status(
                    ef_t['days_sales_outstanding_label'], 
                    ratio_value, 
                    f"{{:.1f}} {ef_t['days_suffix']}", 
                    ef_t['days_sales_outstanding_desc'], 
                    status_dict
                )
                
            with cols3[1]:
                ratio_value = financial_ratios.get('days_inventory', 0)
                status_dict = financial_ratios.get('days_inventory_status')
                display_ratio_with_status(
                    ef_t['days_inventory_label'], 
                    ratio_value, 
                    f"{{:.1f}} {ef_t['days_suffix']}", 
                    ef_t['days_inventory_desc'], 
                    status_dict
                )
        
        # 4. 레버리지 비율 (Leverage Ratios)
        with st.expander(ft['leverage_title'], expanded=True):
            st.markdown(f"""<div style="font-weight: bold; font-size: 1.2em; color: #FB8C00;">{ft['leverage_title']}</div>""", unsafe_allow_html=True)
            cols = st.columns(2)
            
            with cols[0]:
                ratio_value = financial_ratios.get('debt_to_equity', 0)
                status_dict = financial_ratios.get('leverage_status')  # 변경된 키 이름 참조
                display_ratio_with_status(
                    ft['debt_to_equity_label'], 
                    ratio_value, 
                    "{:.2f}", 
                    ft['debt_to_equity_desc'], 
                    status_dict
                )
            
            with cols[1]:
                ratio_value = financial_ratios.get('debt_ratio', 0)
                status_dict = financial_ratios.get('debt_ratio_status')
                display_ratio_with_status(
                    ft['debt_ratio_label'], 
                    ratio_value * 100, 
                    "{:.2f}%", 
                    ft['debt_ratio_desc'], 
                    status_dict
                )
        
        # 5. 가치평가 비율 (Valuation Ratios)
        with st.expander(ft['valuation_title'], expanded=True):
            st.markdown(f"""<div style="font-weight: bold; font-size: 1.2em; color: #E53935;">{ft['valuation_title']}</div>""", unsafe_allow_html=True)
            cols = st.columns(2)
            
            with cols[0]:
                # Adding translations for P/E, P/S, P/B ratios and EV/EBITDA
                valuation_translations = {
                    'English': {
                        'pe_ratio_label': "P/E Ratio",
                        'pe_ratio_desc': "Measures the price paid for a share relative to the annual net income generated by the firm per share.",
                        'ps_ratio_label': "P/S Ratio",
                        'ps_ratio_desc': "Measures the price paid for a share relative to the annual revenue generated by the firm per share.",
                        'pb_ratio_label': "P/B Ratio",
                        'pb_ratio_desc': "Compares a company's market value to its book value, showing the value investors place on the company's equity.",
                        'ev_ebitda_label': "EV/EBITDA",
                        'ev_ebitda_desc': "Measures the value of a company, including debt and other liabilities, relative to its earnings before interest, taxes, depreciation, and amortization."
                    },
                    '한국어': {
                        'pe_ratio_label': "주가수익비율 (P/E Ratio)",
                        'pe_ratio_desc': "주당순이익 대비 주가 비율로, 기업의 수익성 대비 주가 수준을 나타냅니다.",
                        'ps_ratio_label': "주가매출비율 (P/S Ratio)",
                        'ps_ratio_desc': "주당매출액 대비 주가 비율로, 기업의 매출 대비 주가 수준을 나타냅니다.",
                        'pb_ratio_label': "주가장부가치비율 (P/B Ratio)",
                        'pb_ratio_desc': "주당순자산가치 대비 주가 비율로, 기업의 순자산 대비 주가 수준을 나타냅니다.",
                        'ev_ebitda_label': "EV/EBITDA (기업가치/EBITDA)",
                        'ev_ebitda_desc': "기업의 전체 가치를 EBITDA로 나눈 값으로, 이자, 세금, 감가상각비, 무형자산상각비를 제외한 영업이익 대비 기업 가치를 나타냅니다."
                    },
                    '中文': {
                        'pe_ratio_label': "市盈率 (P/E Ratio)",
                        'pe_ratio_desc': "每股价格与每股收益的比率，衡量投资者愿意为公司每单位收益支付的价格。",
                        'ps_ratio_label': "市销率 (P/S Ratio)",
                        'ps_ratio_desc': "每股价格与每股销售额的比率，用于评估公司的销售业绩。",
                        'pb_ratio_label': "市净率 (P/B Ratio)",
                        'pb_ratio_desc': "每股价格与每股净资产的比率，衡量公司的市场价值与账面价值的关系。",
                        'ev_ebitda_label': "EV/EBITDA (企业价值/EBITDA)",
                        'ev_ebitda_desc': "企业价值与息税折旧及摊销前利润的比率，用于评估公司的估值水平。"
                    }
                }
                
                # Get current language translations (using the standardized language code from parent function)
                vt = valuation_translations.get(current_lang, valuation_translations['English'])
                
                # P/E Ratio
                st.metric(
                    label=vt['pe_ratio_label'],
                    value=f"{financial_ratios.get('pe_ratio', 0):.2f}x"
                )
                st.caption(vt['pe_ratio_desc'])
                
                # P/S Ratio
                st.metric(
                    label=vt['ps_ratio_label'],
                    value=f"{financial_ratios.get('ps_ratio', 0):.2f}x"
                )
                st.caption(vt['ps_ratio_desc'])
            
            with cols[1]:
                # P/B Ratio
                st.metric(
                    label=vt['pb_ratio_label'],
                    value=f"{financial_ratios.get('pb_ratio', 0):.2f}x"
                )
                st.caption(vt['pb_ratio_desc'])
                
                # EV/EBITDA - Use the provided multiple from Valuation tab if available
                ev_ebitda_value = ev_ebitda_multiple if ev_ebitda_multiple is not None else financial_ratios.get('ev_to_ebitda', 0)
                st.metric(
                    label=vt['ev_ebitda_label'],
                    value=f"{ev_ebitda_value:.2f}x"
                )
                st.caption(vt['ev_ebitda_desc'])
        
        # 6. CAPEX Metrics
        with st.expander(ft['capex_title'], expanded=True):
            st.markdown(f"""<div style="font-weight: bold; font-size: 1.2em; color: #2196F3;">{ft['capex_title']}</div>""", unsafe_allow_html=True)
            cols = st.columns(2)
            
            with cols[0]:
                ratio_value = financial_ratios.get('capex_to_sales', 0)
                status_dict = financial_ratios.get('capex_to_sales_status')
                display_ratio_with_status(
                    ft['capex_to_sales_label'], 
                    ratio_value, 
                    "{:.2f}", 
                    ft['capex_to_sales_desc'], 
                    status_dict
                )
                
                ratio_value = financial_ratios.get('cash_flow_to_capex', 0)
                status_dict = financial_ratios.get('cash_flow_to_capex_status')
                display_ratio_with_status(
                    ft['cash_flow_to_capex_label'], 
                    ratio_value, 
                    "{:.2f}x", 
                    ft['cash_flow_to_capex_desc'], 
                    status_dict
                )
            
            with cols[1]:
                ratio_value = financial_ratios.get('capex_to_depreciation', 0)
                status_dict = financial_ratios.get('capex_to_depreciation_status')
                display_ratio_with_status(
                    ft['capex_to_depreciation_label'], 
                    ratio_value, 
                    "{:.2f}x", 
                    ft['capex_to_depreciation_desc'], 
                    status_dict
                )
        
        # Add translations for growth metrics
        growth_translations = {
            'English': {
                'revenue_growth_label': "Revenue Growth",
                'revenue_growth_desc': "Year-over-year growth in total revenue.",
                'net_income_growth_label': "Net Income Growth",
                'net_income_growth_desc': "Year-over-year growth in net income.",
                'operating_income_growth_label': "Operating Income Growth",
                'operating_income_growth_desc': "Year-over-year growth in operating income (EBIT)."
            },
            '한국어': {
                'revenue_growth_label': "매출 성장률 (Revenue Growth)",
                'revenue_growth_desc': "전년 대비 매출 성장률입니다.",
                'net_income_growth_label': "순이익 성장률 (Net Income Growth)",
                'net_income_growth_desc': "전년 대비 순이익 성장률입니다.",
                'operating_income_growth_label': "영업이익 성장률 (Operating Income Growth)",
                'operating_income_growth_desc': "전년 대비 영업이익(EBIT) 성장률입니다."
            },
            '中文': {
                'revenue_growth_label': "收入增长率 (Revenue Growth)",
                'revenue_growth_desc': "收入的同比增长。",
                'net_income_growth_label': "净利润增长率 (Net Income Growth)",
                'net_income_growth_desc': "净利润的同比增长。",
                'operating_income_growth_label': "营业利润增长率 (Operating Income Growth)",
                'operating_income_growth_desc': "营业利润(EBIT)的同比增长。"
            }
        }
        
        # Get translations for current language (using the standardized language code from parent function)
        gr_t = growth_translations.get(current_lang, growth_translations['English'])
        
        # 7. Growth Metrics
        with st.expander(ft['growth_title'], expanded=True):
            st.markdown(f"""<div style="font-weight: bold; font-size: 1.2em; color: #4CAF50;">{ft['growth_title']}</div>""", unsafe_allow_html=True)
            cols = st.columns(2)
            
            with cols[0]:
                ratio_value = financial_ratios.get('revenue_growth', 0)
                status_dict = financial_ratios.get('revenue_growth_status')
                display_ratio_with_status(
                    gr_t['revenue_growth_label'], 
                    ratio_value, 
                    "{:.2f}%", 
                    gr_t['revenue_growth_desc'], 
                    status_dict
                )
            
            with cols[1]:
                ratio_value = financial_ratios.get('net_income_growth', 0)
                status_dict = financial_ratios.get('net_income_growth_status')
                display_ratio_with_status(
                    gr_t['net_income_growth_label'], 
                    ratio_value, 
                    "{:.2f}%", 
                    gr_t['net_income_growth_desc'], 
                    status_dict
                )
            
            # Operating Income Growth 배치
            cols2 = st.columns(2)
            with cols2[0]:
                ratio_value = financial_ratios.get('operating_income_growth', 0)
                status_dict = financial_ratios.get('operating_income_growth_status')
                display_ratio_with_status(
                    gr_t['operating_income_growth_label'], 
                    ratio_value, 
                    "{:.2f}%", 
                    gr_t['operating_income_growth_desc'], 
                    status_dict
                )
    
    # Add more ratio categories as needed
    
    with fin_tab1:
        st.subheader(t['income_stmt_tab'])
        if not data["income_stmt"].empty:
            # 원본 데이터 사용 (전치 없이)
            income_df = data["income_stmt"].copy()
            # 수치 포맷팅
            formatted_income = income_df.applymap(lambda x: f"${x:,.0f}" if pd.notnull(x) else "")
            st.dataframe(formatted_income, use_container_width=True)
        else:
            st.warning(f"{t['income_stmt_tab']} data not available.")
    
    with fin_tab2:
        st.subheader(t['balance_sheet_tab'])
        if not data["balance_sheet"].empty:
            # 원본 데이터 사용 (전치 없이)
            balance_df = data["balance_sheet"].copy()
            # 수치 포맷팅
            formatted_balance = balance_df.applymap(lambda x: f"${x:,.0f}" if pd.notnull(x) else "")
            st.dataframe(formatted_balance, use_container_width=True)
        else:
            st.warning(f"{t['balance_sheet_tab']} data not available.")
    
    with fin_tab3:
        st.subheader(t['cash_flow_tab'])
        if not data["cash_flow"].empty:
            # 원본 데이터 사용 (전치 없이)
            cashflow_df = data["cash_flow"].copy()
            # 수치 포맷팅
            formatted_cashflow = cashflow_df.applymap(lambda x: f"${x:,.0f}" if pd.notnull(x) else "")
            st.dataframe(formatted_cashflow, use_container_width=True)
        else:
            st.warning(f"{t['cash_flow_tab']} data not available.")
    
    return

def create_fair_value_comparison_chart(summary_df, current_price, display_currency, language='English', target_high=0, target_low=0, target_mean=0):
    """Create a visual chart comparing different fair values"""
    import plotly.graph_objects as go
    
    # Extract data for the chart
    methods = summary_df[ui_translations[language]['valuation_method_label']].tolist()
    values = []
    
    for val in summary_df[ui_translations[language]['fair_value_label']].tolist():
        # Extract the numeric part from strings like "$120.50"
        try:
            values.append(float(val.replace(display_currency, '').strip()))
        except:
            values.append(0)
    
    # Calculate upside percentages for coloring
    upsides = [(val - current_price) / current_price * 100 if current_price > 0 else 0 for val in values]
    
    # Create color scale based on upside
    colors = []
    for upside in upsides:
        if upside > 20:
            colors.append('#2E7D32')  # Strong green
        elif upside > 10:
            colors.append('#4CAF50')  # Medium green
        elif upside > 0:
            colors.append('#81C784')  # Light green
        elif upside > -10:
            colors.append('#EF9A9A')  # Light red
        elif upside > -20:
            colors.append('#E57373')  # Medium red
        else:
            colors.append('#C62828')  # Strong red
    
    # Create horizontal bar chart
    fig = go.Figure()
    
    # Add the bars in reverse order (to have current price at the top)
    for i in range(len(methods)-1, -1, -1):
        fig.add_trace(go.Bar(
            y=[methods[i]],
            x=[values[i]],
            orientation='h',
            marker=dict(color=colors[i]),
            text=[f"{display_currency} {values[i]:.2f}<br>({upsides[i]:+.1f}%)"],
            textposition='outside',
            hoverinfo='text',
            hovertext=[f"{methods[i]}: {display_currency} {values[i]:.2f}<br>Upside: {upsides[i]:+.1f}%"],
            name=methods[i]
        ))
    
    # Add a vertical line for current price
    fig.add_shape(
        type="line",
        x0=current_price,
        x1=current_price,
        y0=-0.5,
        y1=len(methods) - 0.5,
        line=dict(color="black", width=1, dash="dash"),
    )
    
    # Add annotation for the current price line
    fig.add_annotation(
        x=current_price,
        y=len(methods) - 0.5,
        text=f"{ui_translations[language]['current_price_label']}: {display_currency} {current_price:.2f}",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40
    )
    
    # Add target price lines if they exist
    target_price_labels = {
        'English': {'high': 'Target High', 'low': 'Target Low', 'mean': 'Target Median'},
        '한국어': {'high': '목표가 최고', 'low': '목표가 최저', 'mean': '목표가 중앙값'},
        '中文': {'high': '目标价格最高', 'low': '目标价格最低', 'mean': '目标价格中位数'}
    }
    
    labels = target_price_labels.get(language, target_price_labels['English'])
    
    # Add Target High line and annotation
    if target_high > 0:
        fig.add_shape(
            type="line",
            x0=target_high,
            x1=target_high,
            y0=-0.5,
            y1=len(methods) - 0.5,
            line=dict(color="green", width=1, dash="dash"),
        )
        
        fig.add_annotation(
            x=target_high,
            y=len(methods) - 0.7,
            text=f"{labels['high']}: {display_currency} {target_high:.2f}",
            showarrow=True,
            arrowhead=1,
            ax=40,
            ay=30,
            font=dict(color="green")
        )
    
    # Add Target Low line and annotation
    if target_low > 0:
        fig.add_shape(
            type="line",
            x0=target_low,
            x1=target_low,
            y0=-0.5,
            y1=len(methods) - 0.5,
            line=dict(color="red", width=1, dash="dash"),
        )
        
        fig.add_annotation(
            x=target_low,
            y=len(methods) - 0.9,
            text=f"{labels['low']}: {display_currency} {target_low:.2f}",
            showarrow=True,
            arrowhead=1,
            ax=-40,
            ay=50,
            font=dict(color="red")
        )
    
    # Add Target Median line and annotation
    if target_mean > 0:
        fig.add_shape(
            type="line",
            x0=target_mean,
            x1=target_mean,
            y0=-0.5,
            y1=len(methods) - 0.5,
            line=dict(color="#FF9800", width=1, dash="dash"),
        )
        
        fig.add_annotation(
            x=target_mean,
            y=len(methods) - 0.3,
            text=f"{labels['mean']}: {display_currency} {target_mean:.2f}",
            showarrow=True,
            arrowhead=1,
            ax=-40,
            ay=-20,
            font=dict(color="#FF9800")
        )
    
    # Update layout
    fig.update_layout(
        title="Fair Value Comparison",
        xaxis_title="Fair Value Per Share",
        yaxis=dict(
            title=None,
            showgrid=False,
            showline=False,
            showticklabels=True,
            tickfont=dict(size=12)
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        height=max(300, 100 + 40 * len(methods)),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        hovermode='closest'
    )
    
    # Add shaded regions for undervalued/overvalued
    undervalued_threshold = current_price * 1.1  # 10% above current price
    overvalued_threshold = current_price * 0.9  # 10% below current price
    
    # Find chart x-axis range considering target prices
    all_values = values.copy()
    if target_high > 0:
        all_values.append(target_high)
    if target_low > 0:
        all_values.append(target_low)
    if target_mean > 0:
        all_values.append(target_mean)
        
    max_val = max(all_values)
    min_val = min(all_values)
    range_padding = (max_val - min_val) * 0.2 if max_val > min_val else current_price * 0.2
    x_min = max(0, min_val - range_padding)
    x_max = max_val + range_padding
    
    # Add colored regions for value zones
    fig.add_shape(
        type="rect",
        x0=x_min,
        x1=overvalued_threshold,
        y0=-0.5,
        y1=len(methods) - 0.5,
        fillcolor="rgba(244, 67, 54, 0.1)",
        line=dict(width=0),
        layer="below"
    )
    
    fig.add_shape(
        type="rect",
        x0=overvalued_threshold,
        x1=undervalued_threshold,
        y0=-0.5,
        y1=len(methods) - 0.5,
        fillcolor="rgba(3, 169, 244, 0.1)",
        line=dict(width=0),
        layer="below"
    )
    
    fig.add_shape(
        type="rect",
        x0=undervalued_threshold,
        x1=x_max,
        y0=-0.5,
        y1=len(methods) - 0.5,
        fillcolor="rgba(76, 175, 80, 0.1)",
        line=dict(width=0),
        layer="below"
    )
    
    # Add annotations for the colored regions
    region_labels = {
        'English': ['Overvalued', 'Fair Value', 'Undervalued'],
        '한국어': ['고평가', '공정가치', '저평가'],
        '中文': ['高估', '公允价值', '低估']
    }
    
    labels = region_labels.get(language, region_labels['English'])
    
    # Add labels for regions
    fig.add_annotation(
        x=(x_min + overvalued_threshold) / 2,
        y=len(methods) - 0.5,
        text=labels[0],
        showarrow=False,
        font=dict(size=10, color="#C62828")
    )
    
    fig.add_annotation(
        x=(overvalued_threshold + undervalued_threshold) / 2,
        y=len(methods) - 0.5,
        text=labels[1],
        showarrow=False,
        font=dict(size=10, color="#0277BD")
    )
    
    fig.add_annotation(
        x=(undervalued_threshold + x_max) / 2,
        y=len(methods) - 0.5,
        text=labels[2],
        showarrow=False,
        font=dict(size=10, color="#2E7D32")
    )
    
    # Set x-axis range
    fig.update_xaxes(range=[x_min, x_max])
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)
