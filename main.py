"""
DCF Calculator - Main Application

This is a Streamlit application for calculating the intrinsic value of a stock
using Discounted Cash Flow (DCF) model and multiple-based valuation methods.
"""
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import math
import yfinance as yf

# Import modules
from modules.data import fetch_data, extract_financials
from modules.financials import (
    calculate_financial_ratios, 
    calculate_two_stage_dcf, 
    calculate_dcf_earnings_based, 
    calculate_dcf_fcf_based, 
    calculate_peter_lynch_fair_value
)
from modules.visualization import create_dcf_visualization, create_sensitivity_analysis
from modules.ui import (
    create_company_header, 
    render_valuation_tab,
    render_financials_tab,
    safe_get_multi
)
from modules.translations import translations

# Import UI reset functionality - 리셋 버튼 기능 가져오기
# Reset buttons functionality has been removed

# JavaScript에서 전달된 메시지를 처리하는 함수
def handle_js_message():
    # Streamlit 컨텍스트 데코레이터를 사용하여 자바스크립트 메시지 처리
    st.markdown("""
    <script>
    // 메시지 이벤트 수신 설정
    window.addEventListener('message', function(event) {
        const message = event.data;
        
        // DCF 파라미터 리셋 요청 처리
        if (message.type === 'resetDcfParams') {
            // DCF 파라미터 기본값 설정
            const defaults = {
                'initial_fcf_input': 100.0,
                'forecast_years': 10,
                'growth_rate': 10.0,
                'net_debt_input': 0.0,
                'terminal_years': 10,
                'terminal_growth_rate': 2.5
            };
            
            // SessionState에 기본값 적용
            for (const [key, value] of Object.entries(defaults)) {
                // Streamlit 무상태 컴포넌트 API를 사용하여 세션 상태 업데이트
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {
                        widgetId: key,
                        value: value
                    }
                }, '*');
            }
            
            // Rerun 해야 함
            setTimeout(function() {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {
                        widgetId: 'dcf_reset_complete',
                        value: true
                    }
                }, '*');
            }, 100);
        }
        
        // WACC 파라미터 리셋 요청 처리
        else if (message.type === 'resetWaccParams') {
            // WACC 파라미터 기본값 설정
            const defaults = {
                'risk_free_rate': 3.5,
                'market_risk_premium': 6.0,
                'beta': 1.0,
                'cost_of_debt': 5.5,
                'tax_rate': 21.0,
                'weight_of_debt': 30.0
            };
            
            // SessionState에 기본값 적용
            for (const [key, value] of Object.entries(defaults)) {
                // Streamlit 무상태 컴포넌트 API를 사용하여 세션 상태 업데이트
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {
                        widgetId: key,
                        value: value
                    }
                }, '*');
            }
            
            // Rerun 해야 함
            setTimeout(function() {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {
                        widgetId: 'wacc_reset_complete',
                        value: true
                    }
                }, '*');
            }, 100);
        }
    });
    </script>
    """, unsafe_allow_html=True)

# 파라미터 리셋 함수
def reset_dcf_parameters():
    """DCF 모델 파라미터를 리셋합니다"""
    dcf_params = [
        'initial_fcf_input', 'forecast_years', 'growth_rate',
        'net_debt_input', 'terminal_years', 'terminal_growth_rate'
    ]
    
    # 기본값 설정
    defaults = {
        'initial_fcf_input': 100.0,
        'forecast_years': 10,
        'growth_rate': 10.0,
        'net_debt_input': 0.0,
        'terminal_years': 10,
        'terminal_growth_rate': 2.5
    }
    
    # 파라미터 삭제 후 기본값으로 재설정
    for param in dcf_params:
        if param in st.session_state:
            del st.session_state[param]
    
    # DCF parameters have been reset - trigger recalculation
    st.session_state['dcf_parameters_applied'] = True
    st.session_state['dcf_parameters_reset'] = True

# WACC 파라미터 리셋 함수
def reset_wacc_parameters():
    """WACC 파라미터를 리셋합니다"""
    wacc_params = [
        'risk_free_rate', 'market_risk_premium', 'beta',
        'cost_of_debt', 'tax_rate', 'weight_of_debt'
    ]
    
    # 파라미터 삭제
    for param in wacc_params:
        if param in st.session_state:
            del st.session_state[param]
    
    # WACC parameters have been reset - trigger recalculation
    st.session_state['wacc_parameters_applied'] = True
    st.session_state['wacc_parameters_reset'] = True

def apply_parameters():
    """Apply the current parameters to calculate DCF and valuation models"""
    st.session_state['dcf_parameters_applied'] = True
    st.session_state['wacc_parameters_applied'] = True



def reset_all_parameters():
    """모든 파라미터를 리셋합니다"""
    reset_dcf_parameters()
    # 추가 파라미터 리셋
    additional_params = ['shares_outstanding_input']
    for param in additional_params:
        if param in st.session_state:
            del st.session_state[param]

# Set page configuration
st.set_page_config(page_title="DCF Calculator", layout="wide")

# App title will be set in main() function based on language

# Initialize session state for fair value if not exists
if 'fair_value' not in st.session_state:
    st.session_state.fair_value = 0
if 'combined_fair_value' not in st.session_state:
    st.session_state.combined_fair_value = 0
    
# Initialize language selection in session state
if 'language' not in st.session_state:
    st.session_state.language = 'English'
    
# Initialize ticker tracking and reset state
if 'current_ticker' not in st.session_state:
    st.session_state.current_ticker = ''
if 'should_reset_parameters' not in st.session_state:
    st.session_state.should_reset_parameters = False

# Initialize session state for parameter application
if 'dcf_parameters_applied' not in st.session_state:
    st.session_state.dcf_parameters_applied = False
if 'wacc_parameters_applied' not in st.session_state:
    st.session_state.wacc_parameters_applied = False
if 'dcf_parameters_reset' not in st.session_state:
    st.session_state.dcf_parameters_reset = False
if 'wacc_parameters_reset' not in st.session_state:
    st.session_state.wacc_parameters_reset = False
def main():
    # Create sidebar for language and stock input
    st.sidebar.header("Settings")
    
    # Language selection dropdown
    selected_language = st.sidebar.selectbox(
        "Language / 언어 / 语言",
        options=list(translations.keys()),
        index=list(translations.keys()).index(st.session_state.language)
    )
    
    # Update session state if language changed
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
        # 언어가 변경되었음을 명확히 표시
        st.sidebar.success(f"Language changed to {selected_language}. Refreshing...")
        st.rerun()
    
    # Get translations for the selected language
    t = translations[st.session_state.language]
    
    # Update app title based on selected language
    st.title(t['app_title'])
    
    # Create stock selection section
    st.sidebar.header(t['stock_selection'])
    
    # Ticker input - 세션에 저장된 current_ticker를 기본값으로 사용
    default_ticker = st.session_state.current_ticker if st.session_state.current_ticker else "AAPL"
    ticker = st.sidebar.text_input(t['enter_ticker'], value=default_ticker).upper()
    
    # Add a search button
    search_clicked = st.sidebar.button(t['search'])
    
    # Flag to track if analysis should be run
    run_analysis = False
    
    # Check if ticker has changed
    if st.session_state.current_ticker != '' and st.session_state.current_ticker != ticker:
        # 티커가 변경되면 파라미터 리셋
        reset_all_parameters()
        st.session_state.should_reset_parameters = True
        run_analysis = True
        
    # Check if the button was clicked or if there's a ticker and the page just loaded
    if search_clicked or ticker:
        run_analysis = True
        # Update current ticker in session state
        st.session_state.current_ticker = ticker
    
    # Run analysis if needed
    if run_analysis and ticker:
        with st.spinner(t['fetching_data'].format(ticker)):
            data = fetch_data(ticker)
        
        # Check if data fetch was successful
        if data.get("success", False):
            # Extract key financial metrics
            financials = extract_financials(data, ticker)
            
            # Calculate financial ratios and pass ticker parameter
            financial_ratios = calculate_financial_ratios(
                data["income_stmt"], 
                data["balance_sheet"], 
                data["cash_flow"], 
                data["history"], 
                financials["current_price"], 
                financials["shares_outstanding"],
                ticker,  
                language=st.session_state.language  
            )
            
            # Store ticker in financials dictionary for reference in UI
            financials["ticker"] = ticker
            
            # Display company header
            create_company_header(financials, financial_ratios, data)
            
            # Create tabs for different analysis sections
            tab1, tab2, tab3, tab4 = st.tabs([
                t['valuation_tab'], 
                t['financials_tab'], 
                t['charts_tab'], 
                t['about_tab']
            ])
            
            # Tab 1: Valuation
            with tab1:
                # 티커가 변경되었을 때 파라미터 리셋
                if st.session_state.should_reset_parameters:
                    reset_all_parameters()
                    st.session_state.should_reset_parameters = False
                
                # 세련된 리셋 버튼 추가 (허점 인스턴스 저장)
                reset_placeholder = st.empty()
                
                # streamlit:setComponentValue 이벤트 처리를 위한 js 커스텀 컴포넌트
                components_js = """
                <script>
                window.addEventListener('message', function(event) {
                    // Streamlit에서 전송된 메시지인지 확인
                    if (event.data.type === 'streamlit:setComponentValue') {
                        if (event.data.value === 'reset_dcf') {
                            // DCF 파라미터 리셋 동작 트리거
                            const resetForm = document.createElement('form');
                            resetForm.method = 'POST';
                            resetForm.action = '';
                            
                            const input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = 'reset_dcf';
                            input.value = 'true';
                            
                            resetForm.appendChild(input);
                            document.body.appendChild(resetForm);
                            resetForm.submit();
                        }
                        else if (event.data.value === 'reset_wacc') {
                            // WACC 파라미터 리셋 동작 트리거
                            const resetForm = document.createElement('form');
                            resetForm.method = 'POST';
                            resetForm.action = '';
                            
                            const input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = 'reset_wacc';
                            input.value = 'true';
                            
                            resetForm.appendChild(input);
                            document.body.appendChild(resetForm);
                            resetForm.submit();
                        }
                    }
                });
                </script>
                <div id="reset-handler"></div>
                """
                
                # 리셋 파라미터 확인 및 처리
                # handle_reset_params() - reset functionality removed
                
                # 실제 valuation_tab 렌더링
                valuation_params = render_valuation_tab(data, financials, financial_ratios)
                
                # JavaScript 메시지 처리 함수 호출
                handle_js_message()
                
                # 리셋 완료 플래그 확인
                if 'dcf_reset_complete' not in st.session_state:
                    st.session_state['dcf_reset_complete'] = False
                    
                if 'wacc_reset_complete' not in st.session_state:
                    st.session_state['wacc_reset_complete'] = False
                
                # 리셋 요청이 있을 경우 처리
                if st.session_state.get('dcf_reset_complete'):
                    reset_dcf_parameters()
                    st.session_state['dcf_reset_complete'] = False
                    
                if st.session_state.get('wacc_reset_complete'):
                    reset_wacc_parameters() 
                    st.session_state['wacc_reset_complete'] = False
                
                # 티커가 변경된 경우 처리
                if st.session_state.current_ticker != ticker:
                    # 현재 티커 업데이트
                    st.session_state.current_ticker = ticker
                
                # Use the two-stage style DCF function
                dcf_result = calculate_two_stage_dcf(
                    valuation_params["initial_fcf"],  # Initial earnings/FCF
                    valuation_params["growth_rate"],  # Growth rate (decimal)
                    valuation_params["terminal_growth_rate"],  # Terminal growth rate (decimal)
                    valuation_params["wacc"],  # Discount rate (decimal)
                    valuation_params["forecast_years"],  # Growth stage years
                    valuation_params.get("terminal_years", 10),  # Terminal stage years (from user input)
                    valuation_params["net_debt"],  # Net debt
                    valuation_params["shares_outstanding"],  # Shares outstanding
                    valuation_params.get("include_tangible_book", False),  # Include tangible book value
                    valuation_params.get("tangible_book_value", 0)  # Tangible book value
                )
                
                # Using weighted_fair_value instead of dcf_fair_value
                
                # Use the valuation functions that were already imported at the top of the file
                
                # DCF Valuation
                st.markdown("""
                <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                    DCF Valuation
                    <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                        <div style='width: 40px; height: 2px; background: #3182ce;'></div>
                    </div>
                </h3>
                """, unsafe_allow_html=True)
                
                # 현재 가격 가져오기
                current_price = financials["current_price"]
                
                # 필요한 입력값 가져오기
                # WACC 파라미터에서 값 가져오기
                discount_rate = valuation_params["wacc"]  # 기존 DCF 계산에 사용된 WACC 사용
                risk_free_rate = valuation_params["risk_free_rate"]
                
                # 성장률 가져오기
                growth_rate = valuation_params["growth_rate"]  # 기존 DCF 계산에 사용된 성장률
                terminal_growth_rate = valuation_params["terminal_growth_rate"]  # 기존 DCF 계산에 사용된 영구성장률
                
                # 해당 기업의 EPS 가져오기 - trailing EPS와 forward EPS 모두 가져오기
                eps_without_nri = financials.get("eps", 0)  # trailing EPS
                forward_eps = financials.get("forward_eps", 0)  # forward EPS
                
                # 유효한 값이 없는 경우 
                if eps_without_nri <= 0:
                    # 유효한 값이 없을 경우 사용자에게 알림
                    st.warning("DCF(Earnings Based) 계산이 정확하지 않을 수 있습니다.")
                    
                    # 대안으로 현재 가격과 평균 PER를 사용하여 추정
                    if current_price > 0:
                        avg_pe = 15  # 평균적인 PER 가정
                        eps_without_nri = current_price / avg_pe
                        
                    else:
                        # 최소값으로 설정
                        eps_without_nri = 0.01
                    
                    # 대안으로 EPS의 80%로 추정 (보수적)
                    if eps_without_nri > 0:
                        fcf_per_share = eps_without_nri * 0.8
                    else:
                        # 최소값으로 설정
                        fcf_per_share = 0.01
                
                # EBITDA 성장률 가져오기 - financial_ratios에서 찾거나 계산
                if financial_ratios and 'ebitda_growth' in financial_ratios:
                    # 직접적인 EBITDA 성장률이 있는 경우
                    ebitda_growth_rate = financial_ratios['ebitda_growth']
                elif 'eps_growth' in financial_ratios:
                    # EPS 성장률로 대체
                    ebitda_growth_rate = financial_ratios['eps_growth']
                elif 'revenue_growth' in financial_ratios:
                    # 매출 성장률로 대체
                    ebitda_growth_rate = financial_ratios['revenue_growth']
                else:
                    # 이전 기간 대비 EBITDA 계산 시도
                    if not data["income_stmt"].empty and len(data["income_stmt"].columns) > 1:
                        current_ebit = safe_get_multi(data["income_stmt"], ["EBIT", "Operating Income"], 0)
                        prev_ebit = safe_get_multi(data["income_stmt"], ["EBIT", "Operating Income"], 1)
                        
                        current_depreciation = safe_get_multi(data["income_stmt"], ["Depreciation", "Depreciation And Amortization"], 0)
                        if current_depreciation == 0 and not data["cash_flow"].empty:
                            current_depreciation = safe_get_multi(data["cash_flow"], ["Depreciation", "Depreciation And Amortization"], 0)
                        
                        prev_depreciation = safe_get_multi(data["income_stmt"], ["Depreciation", "Depreciation And Amortization"], 1)
                        if prev_depreciation == 0 and not data["cash_flow"].empty and len(data["cash_flow"].columns) > 1:
                            prev_depreciation = safe_get_multi(data["cash_flow"], ["Depreciation", "Depreciation And Amortization"], 1)
                        
                        current_ebitda = current_ebit + current_depreciation
                        prev_ebitda = prev_ebit + prev_depreciation
                        
                        if prev_ebitda > 0 and current_ebitda > 0:
                            ebitda_growth_rate = (current_ebitda / prev_ebitda) - 1
                        else:
                            # 사용자 입력 성장률 사용
                            ebitda_growth_rate = growth_rate
                    else:
                        # 사용자 입력 성장률 사용
                        ebitda_growth_rate = growth_rate
                
                # 0 또는 음수인 경우 사용자 입력 성장률 사용
                if ebitda_growth_rate <= 0:
                    ebitda_growth_rate = growth_rate
                
                # 백분율 확인 및 변환
                ebitda_growth_percentage = ebitda_growth_rate
                if isinstance(ebitda_growth_rate, (int, float)) and ebitda_growth_rate <= 1:
                    ebitda_growth_percentage = ebitda_growth_rate * 100
                
                # 합리적인 범위 확인 (5-25%)
                ebitda_growth_percentage = max(5, min(25, ebitda_growth_percentage))
                
                # DCF(Earnings based) 계산
                # 입력값에서 파라미터 가져오기 - 사용자 DCF 파라미터를 직접 사용
                
                # 재무제표에서 실제 EPS 성장률 계산 (1차 시도)
                historical_eps_growth_rate = 0.0
                if not data["income_stmt"].empty and len(data["income_stmt"].columns) > 1:
                    current_eps = safe_get_multi(data["income_stmt"], ["Earnings Per Share (Basic)", "Basic EPS"], 0)
                    prev_eps = safe_get_multi(data["income_stmt"], ["Earnings Per Share (Basic)", "Basic EPS"], 1)
                    
                    if current_eps > 0 and prev_eps > 0:
                        historical_eps_growth_rate = (current_eps / prev_eps) - 1
                
                # 2차 시도: 순이익 성장률 기반 추정
                if historical_eps_growth_rate == 0 and not data["income_stmt"].empty and len(data["income_stmt"].columns) > 1:
                    current_net_income = safe_get_multi(data["income_stmt"], ["Net Income", "Net Income Common Stockholders"], 0)
                    prev_net_income = safe_get_multi(data["income_stmt"], ["Net Income", "Net Income Common Stockholders"], 1)
                    
                    if current_net_income > 0 and prev_net_income > 0:
                        historical_eps_growth_rate = (current_net_income / prev_net_income) - 1
                
                # 3차 시도: financial_ratios에서 성장률 확인
                if historical_eps_growth_rate == 0 and 'eps_growth' in financial_ratios:
                    historical_eps_growth_rate = financial_ratios['eps_growth'] / 100  # 백분율에서 소수로 변환
                elif historical_eps_growth_rate == 0 and 'revenue_growth' in financial_ratios:
                    historical_eps_growth_rate = financial_ratios['revenue_growth'] / 100  # 백분율에서 소수로 변환
                
                # 최종적으로 사용자 입력값 사용 (기본값 혹은 실제 입력값)
                earnings_growth_rate = valuation_params["growth_rate"]
                # 이미 소수 형태인지 확인 (1보다 작으면 소수 형태)
                if earnings_growth_rate > 1:
                    earnings_growth_rate = earnings_growth_rate / 100
                
                # 사용자에게 정보 제공 및 추천
                if historical_eps_growth_rate > 0 and abs(historical_eps_growth_rate - earnings_growth_rate) > 0.05:
                    print(f"Note: Historical growth rate ({historical_eps_growth_rate*100:.2f}%) differs from input growth rate ({earnings_growth_rate*100:.2f}%)")
                    if historical_eps_growth_rate > 0:
                        print(f"Consider using historical growth rate: {historical_eps_growth_rate*100:.2f}%")
                
                # 할인율(d) - 사용자가 입력한 WACC 값 사용
                discount_rate = valuation_params["wacc"]
                # 이미 소수 형태인지 확인
                if discount_rate > 1:
                    discount_rate = discount_rate / 100
                
                # 영구성장률(g2) - 사용자가 입력한 값 사용
                terminal_growth_rate = valuation_params["terminal_growth_rate"]
                # 이미 소수 형태인지 확인
                if terminal_growth_rate > 1:
                    terminal_growth_rate = terminal_growth_rate / 100
                
                # 예측 기간(y1) 및 영구 기간(y2) 가져오기
                forecast_years = valuation_params["forecast_years"]
                terminal_years = valuation_params.get("terminal_years", 10)
                
                # 요청에 따라 Forward EPS를 우선적으로 사용
                # Forward EPS가 있는지 확인
                use_forward_eps = forward_eps > 0 and not math.isnan(forward_eps)
                
                # 사용할 EPS 값 결정
                eps_for_dcf = forward_eps if use_forward_eps else eps_without_nri
                
                #  DCF 계산 함수 호출 (요청에 따라 Forward EPS 사용)
                dcf_earnings_fair_value = calculate_dcf_earnings_based(
                    eps_without_nri=eps_for_dcf,  # forward_eps를 우선적으로 사용
                    growth_rate_stage1=earnings_growth_rate,  # 이미 소수 형태
                    discount_rate=discount_rate,  # 이미 소수 형태
                    growth_years=forecast_years,
                    terminal_growth_rate=terminal_growth_rate,  # 이미 소수 형태
                    terminal_years=terminal_years
                )
                
                # DCF (FCF Based) 계산
                
                # 재무제표에서 실제 FCF 성장률 계산 (1차 시도)
                historical_fcf_growth_rate = 0.0
                
                try:
                    # ticker 정보 가져오기
                    
                    yf_ticker = yf.Ticker(ticker)
                    yf_data = yf_ticker.info
                    
                    # freeCashflow와 sharesOutstanding 값 가져오기
                    free_cash_flow = yf_data.get("freeCashflow", 0)
                    shares_outstanding = yf_data.get("sharesOutstanding", financials.get("shares_outstanding", 0))
                    
                    if free_cash_flow > 0 and shares_outstanding > 0:
                        fcf_per_share = free_cash_flow / shares_outstanding
                    else:
                        # FCF 값이 없는 경우 EPS의 90%로 추정
                        fcf_per_share = eps_without_nri * 0.9
                except Exception as e:
                    print(f"Error getting FCF : {e}")
                    # 오류 발생 시 EPS의 90%로 추정
                    fcf_per_share = eps_without_nri * 0.9
                
                # 2차 시도: 재무비율에서 FCF 관련 성장률 찾기
                if historical_fcf_growth_rate == 0 and 'revenue_growth' in financial_ratios:
                    # FCF 성장률은 일반적으로 매출 성장률과 유사하거나 약간 낮음
                    historical_fcf_growth_rate = financial_ratios['revenue_growth'] / 100 * 0.9  # 매출성장의 90%로 가정
                elif historical_fcf_growth_rate == 0 and historical_eps_growth_rate > 0:
                    # 대안으로 EPS 성장률의 90%를 사용
                    historical_fcf_growth_rate = historical_eps_growth_rate * 0.9
                
                # 최종적으로 사용자 입력값 사용 (기본값 혹은 실제 입력값)
                fcf_growth_rate = valuation_params["growth_rate"]
                # 이미 소수 형태인지 확인 (1보다 작으면 소수 형태)
                if fcf_growth_rate > 1:
                    fcf_growth_rate = fcf_growth_rate / 100
                # DCF 계산 함수 호출
                dcf_fcf_fair_value = calculate_dcf_fcf_based(
                    fcf_per_share=fcf_per_share,
                    growth_rate_stage1=fcf_growth_rate,  # 이미 소수 형태
                    discount_rate=discount_rate,  # earnings based와 동일한 discount_rate 사용
                    growth_years=forecast_years,
                    terminal_growth_rate=terminal_growth_rate,
                    terminal_years=terminal_years
                )
                
                # 결과 표시
                col1, col2, col3 = st.columns(3)
                
                # DCF (Earnings Based)
                with col1:
                    earnings_difference = dcf_earnings_fair_value - current_price
                    earnings_percentage = (earnings_difference / current_price) * 100 if current_price > 0 else 0
                    earnings_color = "green" if earnings_percentage > 0 else "red"
                    
                    st.metric(
                        "DCF (Earnings Based)",
                        f"${dcf_earnings_fair_value:.2f}",
                        f"{earnings_percentage:+.1f}%",
                        delta_color="normal",
                        help=f"Discount Rate: {discount_rate*100:.2f}%, Growth Rate: {earnings_growth_rate*100:.2f}%, Terminal Growth: {terminal_growth_rate*100:.2f}%"
                    )
                    
                    if use_forward_eps:
                        st.caption(f"Based on Forward EPS (${forward_eps:.2f})")
                    else:
                        st.caption(f"Based on Trailing EPS (${eps_without_nri:.2f})")
                
                # DCF (FCF Based)
                with col2:
                    fcf_difference = dcf_fcf_fair_value - current_price
                    fcf_percentage = (fcf_difference / current_price) * 100 if current_price > 0 else 0
                    fcf_color = "green" if fcf_percentage > 0 else "red"
                    
                    st.metric(
                        "DCF (FCF Based)",
                        f"${dcf_fcf_fair_value:.2f}",
                        f"{fcf_percentage:+.1f}%",
                        delta_color="normal",
                        help=f"Discount Rate: {discount_rate*100:.2f}%, Growth Rate: {fcf_growth_rate*100:.2f}%, Terminal Growth: {terminal_growth_rate*100:.2f}%"
                    )
                    
                    st.caption(f"Based on FCF per Share (${fcf_per_share:.2f}) from cash flow statement")
                
                # Peter Lynch Fair Value - 변수 미리 초기화하여 항상 값이 있도록 함
                fair_value_lynch = 0  # 기본값 설정
                lynch_percentage = 0
                used_peg_ratio = 0
                used_growth_rate = 0
                used_eps = 0
                
                result_peter_lynch = calculate_peter_lynch_fair_value(ticker=ticker)
                if result_peter_lynch is not None:
                    fair_value_lynch, used_peg_ratio, used_growth_rate, used_eps = result_peter_lynch
                    lynch_difference = fair_value_lynch - current_price
                    lynch_percentage = (lynch_difference / current_price) * 100 if current_price > 0 else 0
                    lynch_color = "green" if lynch_percentage > 0 else "red"
                    
                    with col3:
                        st.metric(
                            "Peter Lynch Fair Value",
                            f"${fair_value_lynch:.2f}",
                            f"{lynch_percentage:+.1f}%",
                            delta_color="normal",
                            help=f"PEG Ratio: {used_peg_ratio:.2f}, Growth Rate: {used_growth_rate:.2f}%, EPS: ${used_eps:.2f}"
                        )
                        
                        st.caption(f"PEG × Growth × EPS = {used_peg_ratio:.2f} × {used_growth_rate:.2f} × {used_eps:.2f} = {fair_value_lynch:.2f}")
                else:
                    with col3:
                        st.write("Peter Lynch fair value could not be calculated.")
                
                # Peter Lynch Fair Value 표시용 변수 생성
                fair_value_lynch_display = f"${fair_value_lynch:.2f}" if fair_value_lynch > 0 else "N/A"
                
                # 통합 분석 결과 박스 표시
                # 가중평균 공정가치 계산 (DCF Earnings 50%, DCF FCF 50%)
                weighted_fair_value = (dcf_earnings_fair_value * 0.5) + (dcf_fcf_fair_value * 0.5)
                weighted_difference = weighted_fair_value - current_price
                weighted_percentage = (weighted_difference / current_price) * 100 if current_price > 0 else 0
                
                # 밸류에이션 상태 결정
                if weighted_percentage > 15:
                    valuation_status = "Significantly Undervalued"
                elif weighted_percentage > 5:
                    valuation_status = "Moderately Undervalued"
                elif weighted_percentage > -5:
                    valuation_status = "Fairly Valued"
                elif weighted_percentage > -15:
                    valuation_status = "Moderately Overvalued"
                else:
                    valuation_status = "Significantly Overvalued"
                
                # Define color based on status
                if valuation_status == "Significantly Undervalued":
                    valuation_status_color = "green"
                elif valuation_status == "Moderately Undervalued":
                    valuation_status_color = "lightgreen"
                elif valuation_status == "Fairly Valued":
                    valuation_status_color = "blue"
                elif valuation_status == "Moderately Overvalued":
                    valuation_status_color = "orange"
                else:  # Significantly Overvalued
                    valuation_status_color = "red"
                
                # DCF Model Results HTML
                st.markdown(f"""
                <div style='padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 20px;'>
                        <div style='flex: 1; padding: 0 10px;'>
                            <div style='font-size: 0.85em; color: #666; margin-bottom: 5px;'>DCF (Earnings Based)</div>
                            <div style='font-size: 1.1em; color: #333;'>${dcf_earnings_fair_value:.2f}</div>
                        </div>
                        <div style='flex: 1; padding: 0 10px;'>
                            <div style='font-size: 0.85em; color: #666; margin-bottom: 5px;'>DCF (FCF Based)</div>
                            <div style='font-size: 1.1em; color: #333;'>${dcf_fcf_fair_value:.2f}</div>
                        </div>
                        <div style='flex: 1; padding: 0 10px;'>
                            <div style='font-size: 0.85em; color: #666; margin-bottom: 5px;'>Peter Lynch Fair Value</div>
                            <div style='font-size: 1.1em; color: #333;'>{fair_value_lynch_display}</div>
                        </div>
                    </div>
                    <!-- Valuation Status at the bottom -->
                    <div style='display: flex; align-items: center; padding: 10px 0;'>
                        <div style="width: 8px; height: 40px; background-color: {valuation_status_color}; border-radius: 4px; margin-right: 15px;"></div>
                        <div>
                            <div style="font-size: 0.9em; color: #666;">{t['valuation_status']}</div>
                            <div style="font-size: 1.2em; font-weight: 500; color: {valuation_status_color};">{valuation_status}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Save the weighted fair value to session state for later use
                # Removed dcf_fair_value assignment, using weighted_fair_value directly
                
                # Valuation Models Explanation section has been moved to the About tab
                
                # --- EV/EBITDA Valuation Section ---
                st.markdown("""
                <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                    EV/EBITDA Valuation
                    <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                        <div style='width: 40px; height: 2px; background: #38a169;'></div>
                    </div>
                </h3>
                """, unsafe_allow_html=True)
                
                # Get EV/EBITDA multiple
                try:

                    stock = yf.Ticker(ticker).info
                    evebitda_multiple = stock.get('enterpriseToEbitda', 20.0)
                    
                    # Fallback to 20x if value is invalid
                    if not isinstance(evebitda_multiple, (int, float)) or evebitda_multiple <= 0:
                        evebitda_multiple = 20.0
                except Exception as e:
                    st.warning(f"Could not fetch EV/EBITDA multiple: {e}. Using default 20x.")
                    evebitda_multiple = 20.0
                
                # Get enterprise value and related metrics directly 
                try:
                    # Use the ticker from user input (stored in session state)
                    yf_ticker = yf.Ticker(st.session_state.current_ticker)
                    yf_data = yf_ticker.info
                    
                    # Get enterprise value and calculate other metrics
                    evebitda_enterprise_value = yf_data.get("enterpriseValue", 0)
                    
                    # Get net debt  (Total Debt - Total Cash)
                    total_debt = yf_data.get("totalDebt", 0) or 0
                    total_cash = yf_data.get("totalCash", 0) or 0
                    net_debt = max(0, total_debt - total_cash)  # 음수 방지
                    
                    # Calculate equity value (Enterprise Value - Net Debt)
                    evebitda_equity_value = max(0, evebitda_enterprise_value - net_debt)
                    
                    # Get shares outstanding for fair value calculation
                    shares_outstanding = yf_data.get("sharesOutstanding", 0)
                    if shares_outstanding == 0:
                        shares_outstanding = yf_data.get("floatShares", 0)
                    
                    # Calculate fair value per share
                    if shares_outstanding > 0:
                        evebitda_fair_value = evebitda_equity_value / shares_outstanding
                    else:
                        evebitda_fair_value = 0
                    
                    # Get EV/EBITDA multiple  or use default 20.0
                    evebitda_multiple = yf_data.get("enterpriseToEbitda", 20.0)
                    
                    # Calculate upside/downside percentage if current price is available
                    current_price = yf_data.get("currentPrice", 0)
                    if current_price == 0:
                        current_price = yf_data.get("regularMarketPrice", 0)
                    
                    if current_price > 0 and evebitda_fair_value > 0:
                        evebitda_percentage = ((evebitda_fair_value - current_price) / current_price) * 100
                    else:
                        evebitda_percentage = 0
                    
                    # Set color based on percentage
                    if evebitda_percentage > 10:
                        evebitda_color = "green"
                    elif evebitda_percentage > -10:
                        evebitda_color = "blue"
                    else:
                        evebitda_color = "red"
                        
                except Exception as e:
                    st.error(f"Error fetching data : {str(e)}")
                    # Set default values in case of error
                    evebitda_enterprise_value = 0
                    evebitda_equity_value = 0
                    evebitda_fair_value = 0
                    evebitda_multiple = 20.0
                    evebitda_percentage = 0
                    evebitda_color = "black"
                
                # Display all EV/EBITDA metrics in a single row
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("EV/EBITDA Multiple", f"{evebitda_multiple:.1f}x")
                
                with col2:
                    # Format Enterprise Value
                    if evebitda_enterprise_value >= 1e12:  # Trillions
                        ev_display = f"${evebitda_enterprise_value/1e12:.1f}T"
                    elif evebitda_enterprise_value >= 1e9:  # Billions
                        ev_display = f"${evebitda_enterprise_value/1e9:.1f}B"
                    else:  # Millions
                        ev_display = f"${evebitda_enterprise_value/1e6:.1f}M"
                    st.metric("Enterprise Value", ev_display)
                
                with col3:
                    # Format Equity Value
                    if evebitda_equity_value >= 1e12:  # Trillions
                        equity_display = f"${evebitda_equity_value/1e12:.1f}T"
                    elif evebitda_equity_value >= 1e9:  # Billions
                        equity_display = f"${evebitda_equity_value/1e9:.1f}B"
                    else:  # Millions
                        equity_display = f"${evebitda_equity_value/1e6:.1f}M"
                    st.metric("Equity Value", equity_display)
                
                with col4:
                    st.metric("Fair Value/Share", f"${evebitda_fair_value:.2f}")
                
                # Add some space
                st.markdown("")
                # Convert to billions or millions for display
                ev_display = f"${evebitda_enterprise_value/1e9:.2f}B" if evebitda_enterprise_value >= 1e9 else f"${evebitda_enterprise_value/1e6:.2f}M"
                equity_display = f"${evebitda_equity_value/1e9:.2f}B" if evebitda_equity_value >= 1e9 else f"${evebitda_equity_value/1e6:.2f}M"
                
                # Determine valuation status based on percentage difference
                if evebitda_percentage > 15:
                    evebitda_status = "Significantly Undervalued"
                elif evebitda_percentage > 5:
                    evebitda_status = "Moderately Undervalued"
                elif evebitda_percentage > -5:
                    evebitda_status = "Fairly Valued"
                elif evebitda_percentage > -15:
                    evebitda_status = "Moderately Overvalued"
                else:
                    evebitda_status = "Significantly Overvalued"
                
                # Define color based on status
                if evebitda_status == "Significantly Undervalued":
                    evebitda_status_color = "green"
                elif evebitda_status == "Moderately Undervalued":
                    evebitda_status_color = "lightgreen"
                elif evebitda_status == "Fairly Valued":
                    evebitda_status_color = "blue"
                elif evebitda_status == "Moderately Overvalued":
                    evebitda_status_color = "orange"
                else:  # Significantly Overvalued
                    evebitda_status_color = "red"
                
                st.markdown(f"""
                <div style='padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 20px;'>
                        <div style='flex: 1; padding: 0 10px;'>
                            <div style='font-size: 0.85em; color: #666; margin-bottom: 5px;'>EV/EBITDA Multiple</div>
                            <div style='font-size: 1.1em; color: #333;'>{evebitda_multiple:.1f}x</div>
                        </div>
                        <div style='flex: 1; padding: 0 10px;'>
                            <div style='font-size: 0.85em; color: #666; margin-bottom: 5px;'>Enterprise Value</div>
                            <div style='font-size: 1.1em; color: #333;'>{ev_display}</div>
                        </div>
                        <div style='flex: 1; padding: 0 10px;'>
                            <div style='font-size: 0.85em; color: #666; margin-bottom: 5px;'>Equity Value</div>
                            <div style='font-size: 1.1em; color: #333;'>{equity_display}</div>
                        </div>
                        <div style='flex: 1; padding: 0 10px;'>
                            <div style='font-size: 0.85em; color: #666; margin-bottom: 5px;'>Fair Value Per Share</div>
                            <div style='font-size: 1.1em; color: {evebitda_color};'>${evebitda_fair_value:.2f}</div>
                        </div>
                        <div style='flex: 1; padding: 0 10px;'>
                            <div style='font-size: 0.85em; color: #666; margin-bottom: 5px;'>Upside/Downside</div>
                            <div style='font-size: 1.1em; color: {evebitda_color};'>{evebitda_percentage:+.1f}%</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; padding: 10px 0;">
                        <div style="width: 8px; height: 40px; background-color: {evebitda_status_color}; border-radius: 4px; margin-right: 15px;"></div>
                        <div>
                            <div style="font-size: 0.9em; color: #666;">{t['valuation_status']}</div>
                            <div style="font-size: 1.2em; font-weight: 500; color: {evebitda_status_color};">{evebitda_status}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Calculate multiple-based valuation using more comprehensive approach
                pe_fair_value = 0
                pb_fair_value = 0
                ps_fair_value = 0
                evebitda_fair_value = 0
                
                # Get financial data  for EPS and other metrics
                yf_ticker = yf.Ticker(st.session_state.current_ticker)
                yf_data = yf_ticker.info
                
                # Get Forward EPS , fallback to trailing EPS if not available
                eps = yf_data.get('forwardEps', 0) or yf_data.get('trailingEps', 0)
                
                # Get key financial metrics from income statement
                if not data["income_stmt"].empty:
                    # Revenue
                    revenue = safe_get_multi(data["income_stmt"], ["Total Revenue", "Revenue"], 0)
                    # EBITDA
                    ebit = safe_get_multi(data["income_stmt"], ["EBIT", "Operating Income"], 0)
                    depreciation = safe_get_multi(data["income_stmt"], ["Depreciation", "Depreciation And Amortization"], 0)
                    
                    if depreciation == 0 and not data["cash_flow"].empty:
                        depreciation = safe_get_multi(data["cash_flow"], ["Depreciation", "Depreciation And Amortization"], 0)
                    
                    ebitda = ebit + depreciation
                
                # Calculate per share metrics
                if financials["shares_outstanding"] > 0:
                    revenue_per_share = revenue / financials["shares_outstanding"] if revenue > 0 else 0
                    ebitda_per_share = ebitda / financials["shares_outstanding"] if ebitda > 0 else 0
                    
                    # Get total debt and cash
                    # yf_data is already loaded at the beginning of this section
                    
                    # Calculate book value per share using 
                    # Get P/B ratio directly 
                    price_to_book = float(yf_data.get("priceToBook", 0)) or 0
                    # Calculate book value per share using P/B ratio and current price
                    book_value_per_share = current_price / price_to_book if price_to_book > 0 else 0
                    
                    # Calculate net debt per share using 
                    total_debt = yf_data.get("totalDebt", 0) or 0
                    total_cash = yf_data.get("totalCash", 0) or 0
                    net_debt = max(0, total_debt - total_cash)  # 음수 방지
                    net_debt_per_share = net_debt / financials["shares_outstanding"] if financials["shares_outstanding"] > 0 else 0
                
                # Calculate multiple-based fair values
                
                # Get company sector/industry from ticker info with better error handling
                ticker_info = data.get("ticker_info", {})
                company_sector = str(ticker_info.get("sector", "")).strip()
                company_industry = str(ticker_info.get("industry", "")).strip()
                
                # Define industry average multiples based on sector/industry
                # These are approximate values based on general market data
                industry_multiples = {
                    "technology": {"pe": 25, "pb": 5.5, "ps": 3.0, "evebitda": 15, "display_name": "Technology"},
                    "healthcare": {"pe": 22, "pb": 4.2, "ps": 2.5, "evebitda": 14, "display_name": "Healthcare"},
                    "consumer cyclical": {"pe": 18, "pb": 3.5, "ps": 1.5, "evebitda": 11, "display_name": "Consumer Cyclical"},
                    "consumer defensive": {"pe": 20, "pb": 4.0, "ps": 1.8, "evebitda": 13, "display_name": "Consumer Defensive"},
                    "financial": {"pe": 14, "pb": 1.8, "ps": 3.2, "evebitda": 10, "display_name": "Financial Services"},
                    "financial services": {"pe": 14, "pb": 1.8, "ps": 3.2, "evebitda": 10, "display_name": "Financial Services"},
                    "industrials": {"pe": 19, "pb": 3.2, "ps": 1.5, "evebitda": 12, "display_name": "Industrials"},
                    "basic materials": {"pe": 15, "pb": 2.2, "ps": 1.2, "evebitda": 9, "display_name": "Basic Materials"},
                    "materials": {"pe": 15, "pb": 2.2, "ps": 1.2, "evebitda": 9, "display_name": "Basic Materials"},
                    "energy": {"pe": 12, "pb": 1.6, "ps": 1.0, "evebitda": 7, "display_name": "Energy"},
                    "utilities": {"pe": 17, "pb": 2.0, "ps": 2.2, "evebitda": 10, "display_name": "Utilities"},
                    "communication": {"pe": 20, "pb": 3.8, "ps": 2.5, "evebitda": 12, "display_name": "Communication Services"},
                    "communication services": {"pe": 20, "pb": 3.8, "ps": 2.5, "evebitda": 12, "display_name": "Communication Services"},
                    "real estate": {"pe": 16, "pb": 2.2, "ps": 5.5, "evebitda": 16, "display_name": "Real Estate"}
                }
                
                # Default values if sector not found
                default_multiples = {"pe": 18, "pb": 2.5, "ps": 2.0, "evebitda": 12, "display_name": "Industry Average"}
                
                # Find the best matching sector (case-insensitive, partial match)
                matched_sector = None
                normalized_sector = company_sector.lower().strip() if company_sector else ""
                
                if normalized_sector:
                    # Try exact match first
                    if normalized_sector in industry_multiples:
                        matched_sector = normalized_sector
                    else:
                        # Try partial match
                        for sector_key in industry_multiples.keys():
                            if sector_key in normalized_sector or normalized_sector in sector_key:
                                matched_sector = sector_key
                                break
                
                # Get sector multiples or use defaults
                if matched_sector and matched_sector in industry_multiples:
                    sector_multiples = industry_multiples[matched_sector].copy()
                    sector_display_name = industry_multiples[matched_sector]["display_name"]
                else:
                    sector_multiples = default_multiples.copy()
                    sector_display_name = default_multiples["display_name"]
                
                # Industry average multiples section
                st.markdown("""
                <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                    Industry Averages
                    <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                        <div style='width: 40px; height: 2px; background: #805ad5;'></div>
                    </div>
                </h3>
                """, unsafe_allow_html=True)
                
                # Create a single row for both P/E and P/B inputs
                pe_col, pb_col = st.columns(2)
                
                # 1. P/E based valuation (weight: 30%)
                industry_pe = 0
                pe_fair_value = 0
                
                # Always show P/E input field, even if EPS is zero or negative
                # Get industry average P/E from sector data as the default value
                default_pe = sector_multiples["pe"]
                
                # Adjust PE based on growth rate for the default value
                if 'revenue_growth' in financial_ratios:
                    growth_rate = financial_ratios['revenue_growth']
                    if growth_rate > 15:
                        default_pe = default_pe * 1.2  # 20% higher PE for higher growth
                    elif growth_rate < 5:
                        default_pe = default_pe * 0.8  # 20% lower PE for lower growth
                
                # Allow user to directly input industry average PER
                with pe_col:
                    st.markdown("**P/E Multiple**")
                    st.markdown(f"*Industry Average: {sector_multiples['pe']:.1f}x*")
                    industry_pe = st.number_input(
                        "P/E multiple",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(default_pe),
                        step=0.5,
                        help=f"Input the P/E multiple for valuation (industry average: {sector_multiples['pe']:.1f}x)",
                        label_visibility="collapsed"
                    )
                    # Always calculate P/E Fair Value using Forward EPS
                    pe_fair_value = eps * industry_pe if eps > 0 else 0
                    eps_display = f"${eps:.2f}" if eps > 0 else "N/A"
                    pe_fair_display = f"${pe_fair_value:.2f}" if pe_fair_value > 0 else "N/A"
                    st.caption(f"Forward EPS: {eps_display} × P/E: {industry_pe:.1f}x = {pe_fair_display}")
                    if eps <= 0:
                        st.caption("Note: Forward EPS is not available. Using trailing EPS if available.")
                
                # 2. P/B based valuation (weight: 20%)
                industry_pb = 0
                pb_fair_value = 0
                if book_value_per_share > 0:
                    # Get industry average P/B from sector data as the default value
                    default_pb = sector_multiples["pb"]
                    
                    # Adjust P/B based on ROE for the default value
                    if 'roe' in financial_ratios:
                        roe = financial_ratios['roe']
                        if roe > 0.15:  # 15% ROE
                            default_pb = default_pb * 1.2  # 20% higher P/B for higher ROE
                        elif roe < 0.05:  # 5% ROE
                            default_pb = default_pb * 0.8  # 20% lower P/B for lower ROE
                    
                    # Allow user to directly input industry average PBR
                    with pb_col:
                        st.markdown("**P/B Multiple**")
                        st.markdown(f"*Industry Average: {sector_multiples['pb']:.1f}x*")
                        industry_pb = st.number_input(
                            "P/B multiple",
                            min_value=0.0,
                            max_value=20.0,
                            value=float(default_pb),
                            step=0.1,
                            help=f"Input the P/B multiple for valuation (industry average: {sector_multiples['pb']:.1f}x)",
                            label_visibility="collapsed"
                        )
                        pb_fair_value = book_value_per_share * industry_pb
                        st.caption(f"BPS: ${book_value_per_share:.2f} × P/B: {industry_pb:.1f}x = ${pb_fair_value:.2f}")
                
                # 3. P/S based valuation (weight: 20%)
                if revenue_per_share > 0:
                    # Get industry average P/S from sector data
                    industry_ps = sector_multiples["ps"]
                    
                    # Adjust P/S based on net profit margin
                    if 'net_profit_margin' in financial_ratios:
                        margin = financial_ratios['net_profit_margin']
                        if margin > 0.15:  # 15% net margin
                            industry_ps = industry_ps * 1.3  # 30% higher P/S for higher margin
                        elif margin < 0.05:  # 5% net margin
                            industry_ps = industry_ps * 0.7  # 30% lower P/S for lower margin
                    
                    ps_fair_value = revenue_per_share * industry_ps
                    
                    # Display the industry average used
                    st.caption(f"Using industry average P/S: {industry_ps:.1f}x")
                
                # 4. EV/EBITDA based valuation (weight: 30%)
                if ebitda_per_share > 0:
                    # Get industry average EV/EBITDA from sector data
                    industry_evebitda = sector_multiples["evebitda"]
                    
                    # Adjust EV/EBITDA based on growth and profitability
                    if 'revenue_growth' in financial_ratios and 'operating_margin' in financial_ratios:
                        growth = financial_ratios['revenue_growth']
                        margin = financial_ratios['operating_margin']
                        
                        if growth > 15 and margin > 0.2:
                            industry_evebitda = industry_evebitda * 1.25  # 25% higher multiple for high growth and high margin
                        elif growth < 5 or margin < 0.1:
                            industry_evebitda = industry_evebitda * 0.8  # 20% lower multiple for low growth or low margin
                    
                    # EV = EBITDA * Multiple
                    ev_per_share = ebitda_per_share * industry_evebitda
                    
                    # Equity Value = EV - Net Debt
                    evebitda_fair_value = ev_per_share - net_debt_per_share
                    
                    # Display the industry average used
                    st.caption(f"Using industry average EV/EBITDA: {industry_evebitda:.1f}x")
                
                # Calculate weighted multiple-based fair value
                multiple_weights = {
                    'pe': 0.30,  # 30% weight to P/E
                    'pb': 0.20,  # 20% weight to P/B
                    'ps': 0.20,  # 20% weight to P/S
                    'evebitda': 0.30  # 30% weight to EV/EBITDA
                }
                
                # Get valid multiples and adjust weights
                valid_multiples = {}
                if pe_fair_value > 0:
                    valid_multiples['pe'] = pe_fair_value
                if pb_fair_value > 0:
                    valid_multiples['pb'] = pb_fair_value
                if ps_fair_value > 0:
                    valid_multiples['ps'] = ps_fair_value
                if evebitda_fair_value > 0:
                    valid_multiples['evebitda'] = evebitda_fair_value
                
                if valid_multiples:
                    # Normalize weights for available multiples
                    total_weight = sum(multiple_weights[k] for k in valid_multiples.keys())
                    
                    if total_weight > 0:
                        normalized_weights = {k: multiple_weights[k] / total_weight for k in valid_multiples.keys()}
                        
                        # Calculate weighted average
                        multiple_fair_value = sum(valid_multiples[k] * normalized_weights[k] for k in valid_multiples.keys())
                    else:
                        # Simple average if normalizing fails
                        multiple_fair_value = sum(valid_multiples.values()) / len(valid_multiples)
                else:
                    multiple_fair_value = 0
                
                # Display multiple-based valuation results if calculated
                if multiple_fair_value > 0:
                    st.markdown("""
                    <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                        Multiple-Based Valuation
                        <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                            <div style='width: 40px; height: 2px; background: #e53e3e;'></div>
                        </div>
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    multiple_difference = multiple_fair_value - current_price
                    multiple_percentage = (multiple_difference / current_price) * 100 if current_price > 0 else 0
                    
                    # Determine color based on comparison to current price
                    if multiple_percentage > 10:
                        multiple_color = "green"
                    elif multiple_percentage > -10:
                        multiple_color = "blue"
                    else:
                        multiple_color = "red"
                    
                    # Create columns for multiple-based valuation details
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Always show P/E-Based Fair Value, even if zero or negative
                        pe_delta = f"{((pe_fair_value/current_price)-1)*100:.1f}%" if current_price > 0 and pe_fair_value > 0 else None
                        pe_help = f"Fair value based on industry average P/E ratio ({industry_pe:.1f}x) applied to company's earnings per share"
                        if pe_fair_value <= 0:
                            pe_help += "\n\nNote: Fair value is zero or negative due to negative or zero EPS."
                        
                        st.metric(
                            f"P/E-Based Fair Value (P/E: {industry_pe:.1f}x)",
                            f"${pe_fair_value:.2f}" if pe_fair_value > 0 else "N/A",
                            pe_delta,
                            help=pe_help
                        )
                    
                    with col2:
                        # Always show P/B-Based Fair Value, even if zero or negative
                        pb_delta = f"{((pb_fair_value/current_price)-1)*100:.1f}%" if current_price > 0 and pb_fair_value > 0 else None
                        pb_help = f"Fair value based on industry average P/B ratio ({industry_pb:.1f}x) applied to company's book value per share"
                        if pb_fair_value <= 0:
                            pb_help += "\n\nNote: Fair value is zero or negative due to negative or zero book value per share."
                        
                        st.metric(
                            f"P/B-Based Fair Value (P/B: {industry_pb:.1f}x)",
                            f"${pb_fair_value:.2f}" if pb_fair_value > 0 else "N/A",
                            pb_delta,
                            help=pb_help
                        )
                    
                    # Display Multiple-Based valuation in a style matching Combined Valuation Summary
                    # Determine if we should show N/A for any values
                    pe_value = f"${pe_fair_value:.2f}" if pe_fair_value > 0 else "N/A"
                    pb_value = f"${pb_fair_value:.2f}" if pb_fair_value > 0 else "N/A"
                    multiple_value = f"${multiple_fair_value:.2f}" if multiple_fair_value > 0 else "N/A"
                    
                    st.markdown(f"""
                    <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">P/E-Based Value</div>
                                <div style="font-size: 1.1em; color: #333;">{pe_value}</div>
                            </div>
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">P/B-Based Value (P/B: {industry_pb:.1f})</div>
                                <div style="font-size: 1.1em; color: #333;">{pb_value}</div>
                            </div>
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Multiple-Based Fair Value</div>
                                <div style="font-size: 1.1em; font-weight: 500; color: {multiple_color};">{multiple_value}</div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; padding: 10px 0;">
                            <div style="width: 8px; height: 40px; background-color: {multiple_color}; border-radius: 4px; margin-right: 15px;"></div>
                            <div>
                                <div style="font-size: 0.9em; color: #666;">{t['upside_downside']}</div>
                                <div style="font-size: 1.2em; font-weight: 500; color: {multiple_color};">{multiple_percentage:+.1f}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Combine DCF and multiple-based valuation
                # Store multiple-based fair value in session state
                st.session_state.combined_fair_value = multiple_fair_value
                
                # Calculate final fair value (weighted average of DCF and multiple-based)
                # Give more weight to DCF if available
                if weighted_fair_value > 0 and multiple_fair_value > 0:
                    # 70% weight to DCF, 30% to multiple-based
                    final_fair_value = (weighted_fair_value * 0.7) + (multiple_fair_value * 0.3)
                elif weighted_fair_value > 0:
                    final_fair_value = weighted_fair_value
                elif multiple_fair_value > 0:
                    final_fair_value = multiple_fair_value
                else:
                    final_fair_value = 0
                
                # Store final fair value in session state
                st.session_state.fair_value = final_fair_value
                
                # 현재 언어 확인 및 표준화
                current_lang = st.session_state.language
                # 언어 코드 표준화
                if current_lang.lower() == "english":
                    current_lang = "English"
                elif current_lang.lower() == "korean" or current_lang.lower() == "한국어":
                    current_lang = "한국어"
                elif current_lang.lower() == "chinese" or current_lang.lower() == "中文":
                    current_lang = "中文"
                
                # 번역 사전 가져오기
                from modules.ui import ui_translations
                t = ui_translations[current_lang]
                
                # Display final valuation summary
                if weighted_fair_value > 0 and multiple_fair_value > 0:
                    st.markdown(f"""
                    <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                        {t['valuation_result']}
                        <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                            <div style='width: 40px; height: 2px; background: #e53e3e;'></div>
                        </div>
                    </h3>
                    """, unsafe_allow_html=True)
                    # 추천 상태 번역 키 매핑
                    status_mapping = {
                        "Strong Buy": "strong_buy" if "strong_buy" in t else "Strong Buy",
                        "Buy": "buy" if "buy" in t else "Buy",
                        "Hold": "hold" if "hold" in t else "Hold",
                        "Sell": "sell" if "sell" in t else "Sell",
                        "Strong Sell": "strong_sell" if "strong_sell" in t else "Strong Sell",
                    }
                    
                    final_difference = final_fair_value - current_price
                    final_percentage = (final_difference / current_price) * 100 if current_price > 0 else 0
                    
                    if final_percentage > 15:
                        final_status = "Strong Buy"
                        final_color = "green"
                    elif final_percentage > 5:
                        final_status = "Buy"
                        final_color = "lightgreen"
                    elif final_percentage > -5:
                        final_status = "Hold"
                        final_color = "blue"
                    elif final_percentage > -15:
                        final_status = "Sell"
                        final_color = "orange"
                    else:
                        final_status = "Strong Sell"
                        final_color = "red"
                    
                    # Get the calculation details for display with proper error handling
                    try:
                        # Get WACC and handle potential missing keys
                        wacc = valuation_params.get("wacc", 0.1)  # Default to 10% if not found
                        
                        # Get other parameters with defaults
                        dcf_growth_rate = valuation_params.get("growth_rate", 0.05)  # As decimal for calculations
                        dcf_discount_rate = wacc  # Use WACC as the discount rate
                        dcf_terminal_growth = valuation_params.get("terminal_growth_rate", 0.02)  # As decimal for calculations
                        
                        # Get the actual DCF (Earnings Based) and DCF (FCF Based) values
                        dcf_eps = dcf_earnings_fair_value  # Actual DCF (Earnings Based) value
                        dcf_fcf = dcf_fcf_fair_value       # Actual DCF (FCF Based) value
                        
                        # Multiple-based components
                        multiple_pe = financial_ratios.get('pe_ratio', 0)
                        multiple_ps = financial_ratios.get('ps_ratio', 0)
                        multiple_pb = financial_ratios.get('pb_ratio', 0)
                        
                        # Display the valuation components in a single row with consistent styling
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # DCF Fair Value
                            st.metric(
                                "DCF Fair Value (70%)",
                                f"${weighted_fair_value:,.2f}",
                                help="Weighted average of DCF values from EPS and FCF models"
                            )
                            st.markdown(f"""
                            <div style="font-size: 0.8em; color: #666; margin-top: -10px; margin-bottom: 15px; line-height: 1.4;">
                                = 0.5 × DCF(Earnings) + 0.5 × DCF(FCF)<br>
                                = 0.5 × ${dcf_eps:,.2f} + 0.5 × ${dcf_fcf:,.2f}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            # Multiple-Based Value
                            st.metric(
                                "Multiple-Based Value (30%)",
                                f"${multiple_fair_value:,.2f}",
                                help="Weighted average of P/E, P/S, and P/B based valuations"
                            )
                            # Build the formula string based on available multiples
                            formula_parts = []
                            value_parts = []
                            
                            if 'pe' in valid_multiples:
                                formula_parts.append("0.30 × P/E")
                                value_parts.append(f"0.30 × ${pe_fair_value:,.2f}")
                            if 'ps' in valid_multiples:
                                formula_parts.append("0.20 × P/S")
                                value_parts.append(f"0.20 × ${ps_fair_value:,.2f}" if 'ps_fair_value' in locals() else "0.20 × $0.00")
                            if 'pb' in valid_multiples:
                                formula_parts.append("0.20 × P/B")
                                value_parts.append(f"0.20 × ${pb_fair_value:,.2f}")
                            if 'evebitda' in valid_multiples:
                                formula_parts.append("0.30 × EV/EBITDA")
                                value_parts.append(f"0.30 × ${evebitda_fair_value:,.2f}" if 'evebitda_fair_value' in locals() else "0.30 × $0.00")
                            
                            formula = " + ".join(formula_parts)
                            values = " + ".join(value_parts)
                            
                            st.markdown(f"""
                            <div style="font-size: 0.8em; color: #666; margin-top: -10px; margin-bottom: 15px; line-height: 1.4;">
                                = {formula}<br>
                                = {values}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            # Combined Fair Value
                            st.metric(
                                "Combined Fair Value",
                                f"${final_fair_value:,.2f}",
                                f"{((final_fair_value/current_price)-1)*100:.1f}%" if current_price > 0 else None,
                                help="Weighted average of DCF (70%) and Multiple-Based (30%) valuations"
                            )
                            st.markdown(f"""
                            <div style="font-size: 0.8em; color: #666; margin-top: -10px; margin-bottom: 15px; line-height: 1.4;">
                                = 0.7 × DCF + 0.3 × Multiple<br>
                                = 0.7 × ${weighted_fair_value:,.2f} + 0.3 × ${multiple_fair_value:,.2f}
                            </div>
                            """, unsafe_allow_html=True)
                            
                    except Exception as e:
                        # Fallback values in case of any error
                        print(f"Error getting valuation params: {e}")
                        dcf_growth_rate = 0.05  # 5% as default
                        dcf_discount_rate = 0.10  # 10% as default
                        dcf_terminal_growth = 0.02  # 2% as default
                    
                    # Get multiple-based valuation details
                    multiple_pe = financial_ratios.get('pe_ratio', 0)
                    multiple_ps = financial_ratios.get('ps_ratio', 0)
                    multiple_pb = financial_ratios.get('pb_ratio', 0)
                    
                    # Main valuation box
                    st.markdown(f"""
                    <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin: 10px 0 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between;">
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">DCF Fair Value (70%)</div>
                                <div style="font-size: 1.1em; color: #333;">${weighted_fair_value:.2f}</div>
                            </div>
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Multiple-Based Value (30%)</div>
                                <div style="font-size: 1.1em; color: #333;">${multiple_fair_value:.2f}</div>
                            </div>
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Combined Fair Value</div>
                                <div style="font-size: 1.1em; font-weight: 500; color: {final_color};">${final_fair_value:.2f}</div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; padding: 10px 0;">
                            <div style="width: 8px; height: 40px; background-color: {final_color}; border-radius: 4px; margin-right: 15px;"></div>
                            <div>
                                <div style="font-size: 0.9em; color: #666;">{t['recommendation']}</div>
                                <div style="font-size: 1.2em; font-weight: 500; color: {final_color};">
                                    {t[status_mapping[final_status]].replace('{0:.1f}', f'{final_percentage:+.1f}')} <span style="font-size: 0.9em; font-weight: normal; color: #666;">({t['upside_downside'].split('/')[0]}: {final_percentage:+.1f}%)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add ROIC vs WACC comparison section
                    st.markdown("""
                    <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                        Value Creation Analysis
                        <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                            <div style='width: 40px; height: 2px; background: #d69e2e;'></div>
                        </div>
                    </h3>
                    <p style='color: #6b7280; margin: 0 0 16px 0;'>ROIC vs WACC</p>
                    """, unsafe_allow_html=True)
                    
                    # Get ROIC from financial ratios and WACC from valuation parameters to ensure consistency
                    roic = financial_ratios.get("roic", 0) * 100  # Convert from decimal to percentage
                    wacc_value = valuation_params.get("wacc", 0) * 100  # Use WACC from DCF calculation for consistency
                    
                    # 현재 언어 확인 및 번역 사전 가져오기
                    current_lang = st.session_state.language
                    # 언어 코드 표준화
                    if current_lang.lower() == "english":
                        current_lang = "English"
                    elif current_lang.lower() == "korean" or current_lang.lower() == "한국어":
                        current_lang = "한국어"
                    elif current_lang.lower() == "chinese" or current_lang.lower() == "中文":
                        current_lang = "中文"
                    
                    # 번역 사전 가져오기
                    from modules.ui import ui_translations
                    t = ui_translations[current_lang]
                    
                    # 업데이트된 ROIC 계산 정보 표시 (다국어 지원)
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; font-size: 0.9em;">
                        <strong>{t['roic_calculation_title']}</strong><br>
                        {t['roic_formula']}<br>
                        <span style="color: #1E88E5;">{t['roic_tax_rate_note'].format(valuation_params.get("tax_rate", 0.25)*100)}</span><br>
                        {t['invested_capital_formula']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # WACC 파라미터의 세율로 ROIC 재계산 (필요한 경우)
                    # 이 부분은 'valuation_params'에서 세율을 가져와 ROIC를 조정하는데 사용됨
                    wacc_tax_rate = valuation_params.get("tax_rate", 0.25)  # WACC 계산에 사용된 세율
                    
                    # 재계산된 ROIC 값이 있으면 업데이트
                    if "roic" in financial_ratios and wacc_tax_rate > 0:
                        # 원래 financial_ratios에서 계산된 NOPAT의 세율을 제거하고 새 세율 적용
                        operating_income = safe_get_multi(data["income_stmt"], ["Operating Income", "EBIT"], 0)
                        if operating_income > 0:
                            # 기존 ROIC에서 투자자본 값을 추출 (역산)
                            old_roic = financial_ratios.get("roic", 0)
                            old_tax_rate = valuation_params.get("tax_rate", 0.25)  # WACC parameters의 tax rate 값 사용
                            
                            # 역산해서 투자자본 계산 (운영 중인 코드에 적용 가능하도록)
                            if old_roic > 0:
                                # 기존 NOPAT = operating_income * (1 - old_tax_rate)
                                # 기존 ROIC = 기존 NOPAT / invested_capital
                                # 따라서 invested_capital = 기존 NOPAT / 기존 ROIC
                                old_nopat = operating_income * (1 - old_tax_rate)
                                invested_capital = old_nopat / old_roic if old_roic > 0 else 0
                                
                                # 새로운 세율로 NOPAT와 ROIC 재계산
                                new_nopat = operating_income * (1 - wacc_tax_rate)
                                new_roic = new_nopat / invested_capital if invested_capital > 0 else 0
                                
                                # ROIC 업데이트
                                financial_ratios["roic"] = new_roic
                                
                                # ROIC 백분율 값 업데이트
                                roic = new_roic * 100
                    
                    # Update WACC in financial_ratios to ensure consistency across sections
                    financial_ratios["wacc"] = valuation_params.get("wacc", 0)
                    
                    # Recalculate value spread using consistent WACC
                    value_spread = roic - wacc_value  # Both already in percentage format
                    
                    # Create columns for comparison
                    value_col1, value_col2, value_col3 = st.columns(3)
                    
                    with value_col1:
                        # ROIC metric
                        roic_color = "green" if roic > wacc_value else "red"
                        st.metric(
                            "Return on Invested Capital (ROIC)",
                            f"{roic:.2f}%",
                            help=f"투자자본수익률(ROIC): (EBIT × (1 - Tax Rate)) / [(투자자본(직전연도) + 투자자본(최근))/2]. 세율: {valuation_params.get('tax_rate', 0.25)*100:.2f}%. 투자자본 = 총자산 - 미지급금 - (현금성자산 - 영업현금 필요액)"
                        )
                    
                    with value_col2:
                        # WACC metric
                        st.metric(
                            "Weighted Avg. Cost of Capital (WACC)",
                            f"{wacc_value:.2f}%",
                            help="The minimum required return that a company must earn on its capital"
                        )
                    
                    with value_col3:
                        # Value Spread (ROIC - WACC)
                        spread_color = "green" if value_spread > 0 else "red"
                        spread_delta = f"{value_spread:+.2f}%"
                        st.metric(
                            "Value Spread (ROIC - WACC)",
                            f"{value_spread:.2f}%",
                            delta=spread_delta,
                            delta_color="normal",
                            help="Measures value creation (positive) or destruction (negative)"
                        )
                    
                    # Get value creation status
                    value_creation_status = financial_ratios.get("value_creation_status", {})
                    status_level = value_creation_status.get("level", "N/A")
                    status_color = value_creation_status.get("color", "gray")
                    status_description = value_creation_status.get("description", "")
                    
                    # Get correct CSS color from standard color map
                    color_map = {
                        "red": "#FF5252",
                        "orange": "#FFA726",
                        "yellow": "#FFEB3B",
                        "green": "#66BB6A",
                        "blue": "#42A5F5",
                        "purple": "#7E57C2",
                        "gray": "#9E9E9E"
                    }
                    
                    status_color_hex = color_map.get(status_color, "#9E9E9E")
                    
                    # Format value spread with sign
                    value_spread_display = f"{value_spread:+.2f}%"
                    
                    # Display value creation analysis in the same style as price target
                    st.markdown(f"""
                    <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">ROIC</div>
                                <div style="font-size: 1.1em; color: #333;">{roic:.2f}%</div>
                            </div>
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">WACC</div>
                                <div style="font-size: 1.1em; color: #333;">{wacc_value:.2f}%</div>
                            </div>
                            <div style="flex: 1; padding: 0 10px;">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Value Spread</div>
                                <div style="font-size: 1.1em; font-weight: 500; color: {status_color_hex};">{value_spread_display}</div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; padding: 10px 0;">
                            <div style="width: 8px; height: 40px; background-color: {status_color_hex}; border-radius: 4px; margin-right: 15px;"></div>
                            <div>
                                <div style="font-size: 0.9em; color: #666;">{t['value_creation_status']}</div>
                                <div style="font-size: 1.2em; font-weight: 500; color: {status_color_hex};">
                                    {t[status_level.lower().replace(' ', '_')] if status_level.lower().replace(' ', '_') in t else status_level}
                                </div>
                            </div>
                        </div>
                        <div style="margin-top: 10px; font-size: 0.9em; color: #555; background-color: rgba({int(status_color_hex[1:3], 16)}, {int(status_color_hex[3:5], 16)}, {int(status_color_hex[5:7], 16)}, 0.1); padding: 10px; border-radius: 4px;">
                            {status_description}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add a visualization comparing ROIC and WACC
                    st.markdown(f"#### {t['roic_vs_wacc_comparison']}")
                    
                    # Create a bar chart comparing ROIC and WACC
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    
                    # Add ROIC bar
                    fig.add_trace(go.Bar(
                        x=["ROIC"],
                        y=[roic],
                        name="ROIC",
                        marker_color='#66BB6A' if roic > wacc_value else '#FF5252',
                        text=[f"{roic:.2f}%"],
                        textposition='auto'
                    ))
                    
                    # Add WACC bar
                    fig.add_trace(go.Bar(
                        x=["WACC"],
                        y=[wacc_value],
                        name="WACC",
                        marker_color='#42A5F5',
                        text=[f"{wacc_value:.2f}%"],
                        textposition='auto'
                    ))
                    
                    # Add Value Spread bar
                    fig.add_trace(go.Bar(
                        x=["Value Spread"],
                        y=[value_spread],
                        name="Value Spread",
                        marker_color='#66BB6A' if value_spread > 0 else '#FF5252',
                        text=[f"{value_spread:.2f}%"],
                        textposition='auto'
                    ))
                    
                    # Update layout
                    fig.update_layout(
                        title=t['roic_vs_wacc_comparison'],
                        xaxis_title="Metric",
                        yaxis_title="Percentage (%)",
                        yaxis=dict(ticksuffix="%"),
                        height=400,
                        uniformtext=dict(mode="hide", minsize=10),
                        bargap=0.3,
                        bargroupgap=0.1,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    
                    # Add a horizontal line at y=0 for reference
                    fig.add_shape(
                        type="line",
                        x0=-0.5,
                        x1=2.5,
                        y0=0,
                        y1=0,
                        line=dict(color="black", width=1, dash="dash"),
                    )
                    
                    # Add annotations explaining the implications
                    if value_spread > 0:
                        fig.add_annotation(
                            x=2,
                            y=value_spread / 2,
                            text="Value Creation",
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=2,
                            arrowcolor="#66BB6A"
                        )
                    else:
                        fig.add_annotation(
                            x=2,
                            y=value_spread / 2,
                            text="Value Destruction",
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=2,
                            arrowcolor="#FF5252"
                        )
                    
                    # Display chart
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Add explanation about ROIC vs WACC comparison
                    st.markdown(f"""
                    **{t['understanding_roic_vs_wacc']}**
                    
                    * **{t['roic_definition']}**
                    * **{t['wacc_definition']}**
                    * **{t['value_spread_definition']}**
                      * {t['roic_greater_wacc']}
                      * {t['roic_less_wacc']}
                    
                    {t['roic_wacc_importance']}
                    """)
                
                # Display DCF visualization
                st.markdown("""
                <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                    DCF Visualization
                    <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                        <div style='width: 40px; height: 2px; background: #38a169;'></div>
                    </div>
                </h3>
                """, unsafe_allow_html=True)
                
                # Patch dcf_result for visualization compatibility with the new field names
                dcf_vis_result = dict(dcf_result)
                
                # Map new field names to the ones expected by the visualization
                if 'projected_earnings' in dcf_vis_result:
                    dcf_vis_result['cash_flows'] = dcf_vis_result['projected_earnings']
                
                if 'cumulative_pv' in dcf_vis_result:
                    dcf_vis_result['pv_cash_flows'] = dcf_vis_result['cumulative_pv']
                
                # Create year labels - use the original ones if available
                dcf_vis_result['year_labels'] = dcf_vis_result.get('year_labels', 
                                                                  [f"Year {year}" for year in range(1, valuation_params["forecast_years"] + 11)])
                
                # Ensure other necessary fields are present
                if 'terminal_stage_value' in dcf_vis_result:
                    dcf_vis_result['terminal_value'] = dcf_vis_result['terminal_stage_value']
                
                if 'terminal_value' not in dcf_vis_result:
                    dcf_vis_result['terminal_value'] = dcf_vis_result.get('terminal_stage_value', 0)
                
                if 'pv_terminal_value' not in dcf_vis_result:
                    # Rough estimate if not present
                    dcf_vis_result['pv_terminal_value'] = dcf_vis_result.get('terminal_stage_value', 0) * 0.5
                
                # Display the visualization
                dcf_fig = create_dcf_visualization(
                    dcf_vis_result, 
                    financials["current_price"], 
                    ticker,
                    valuation_params["forecast_years"] + 10  # Growth stage + terminal stage
                )
                st.plotly_chart(dcf_fig, use_container_width=True)
                
                # Sensitivity analysis will be displayed after calculations
                
                with st.spinner("Generating sensitivity analysis..."):
                    try:
                        # Make sure values are in correct format
                        initial_fcf_value = valuation_params["initial_fcf"]
                        growth_rate_value = valuation_params["growth_rate"]  # Already in decimal
                        terminal_growth_value = valuation_params["terminal_growth_rate"]  # Already in decimal
                        wacc_value = valuation_params["wacc"] * 100  # Convert decimal to percentage
                        forecast_years_value = valuation_params["forecast_years"]
                        net_debt_value = valuation_params["net_debt"]
                        shares_outstanding_value = valuation_params["shares_outstanding"]
                        
                        # Make sure values are in correct format and capture the real input values
                        initial_fcf_value = valuation_params["initial_fcf"]
                        growth_rate_value = valuation_params["growth_rate"]  # Already in decimal
                        terminal_growth_value = valuation_params["terminal_growth_rate"]  # Already in decimal
                        wacc_value = valuation_params["wacc"]  # Already in decimal
                        forecast_years_value = valuation_params["forecast_years"]
                        net_debt_value = valuation_params["net_debt"]
                        shares_outstanding_value = valuation_params["shares_outstanding"]
                        
                        # Add a spinner while generating sensitivity analysis
                        with st.spinner("Generating sensitivity analysis... This might take a moment"):
                            # Ensure we pass the correct values to the sensitivity analysis function
                            sensitivity_table, sensitivity_fig = create_sensitivity_analysis(
                                initial_fcf_value,
                                growth_rate_value,
                                terminal_growth_value,
                                wacc_value,
                                forecast_years_value,
                                net_debt_value,
                                shares_outstanding_value,
                                calculate_two_stage_dcf,
                                current_price
                            )
                            
                            # Display sensitivity results with better formatting
                            st.markdown("""
                            <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                                Sensitivity Analysis
                                <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                                    <div style='width: 40px; height: 2px; background: #e53e3e;'></div>
                                </div>
                            </h3>
                            """, unsafe_allow_html=True)
                            
                            # Add description of the sensitivity analysis table - using translated strings
                            st.caption(t['sensitivity_analysis_explanation'])
                            
                            # Display notes about WACC and terminal growth rate impact
                            st.caption(f"- {t['wacc_sensitivity_note']}  \n- {t['terminal_growth_sensitivity_note']}")
                            
                            # Display the dataframe with improved styling
                            st.dataframe(sensitivity_table, use_container_width=True)
                            
                            # Display sensitivity heatmap with better size
                            st.plotly_chart(sensitivity_fig, use_container_width=True)
                            
                            # Add interpretation guidance for the sensitivity analysis
                            if 'sensitivity_analysis_help' in t:
                                st.info(t['sensitivity_analysis_help'])
                            else:
                                # Fallback to English if translation not available
                                st.info("""
                                **How to interpret:** This sensitivity analysis helps understand how changes in key assumptions affect the fair value estimate. 
                                
                                - **Terminal Growth Rate:** Higher values assume stronger long-term growth, leading to higher valuations.
                                - **WACC:** Lower values place more value on future cash flows, leading to higher valuations.
                                
                                The contour line represents the current market price. Areas above the line may indicate potential undervaluation, while areas below may indicate potential overvaluation.
                                """)
                    except Exception as e:
                        if 'sensitivity_analysis_error' in t:
                            st.error(t['sensitivity_analysis_error'].format(str(e)))
                        else:
                            st.error(f"Could not generate sensitivity analysis: {str(e)}")
                            
                        if 'sensitivity_analysis_error_help' in t:
                            st.info(t['sensitivity_analysis_error_help'])
                        else:
                            st.info("This could be due to mathematical constraints (e.g., terminal growth rate > WACC) or calculation errors. Try adjusting your input parameters.")
            
            # Tab 2: Financials
            with tab2:
                # Render the financials tab
                from modules.ui import render_financials_tab
                # Pass the EV/EBITDA multiple from the Valuation tab to the Financials tab
                render_financials_tab(financials, financial_ratios, data, ev_ebitda_multiple=evebitda_multiple)
            # Tab 3: Charts
            with tab3:
                # Stock Price History with consistent header style
                st.markdown(f"""
                <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                    {t['stock_price_history']}
                    <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                        <div style='width: 40px; height: 2px; background: #e53e3e;'></div>
                    </div>
                </h3>
                """, unsafe_allow_html=True)
                
                # Create a date range selector for the chart
                date_col1, date_col2 = st.columns(2)
                
                with date_col1:
                    start_date = st.date_input(
                        t['start_date'],
                        # 항상 2년 전부터 시작하도록 설정 (전체 기간이 아니라 2년 전으로 제한)
                        value=(datetime.date.today() - datetime.timedelta(days=730))  # 항상 2년 전 (365일*2)
                    )
                
                with date_col2:
                    end_date = st.date_input(
                        t['end_date'],
                        value=data["history"].index.max().date() if not data["history"].empty else datetime.date.today()
                    )
                
                # Filter the data based on selected date range
                if not data["history"].empty:
                    filtered_history = data["history"][
                        (data["history"].index.date >= start_date) & 
                        (data["history"].index.date <= end_date)
                    ]
                    
                    # Create a modern, clean candlestick chart with volume
                    import plotly.graph_objects as go
                    from plotly.subplots import make_subplots
                    
                    # Modern color scheme with better contrast and aesthetics
                    colors = {
                        'up': '#22C55E',    # Vibrant green for up days
                        'down': '#EF4444',  # Red for down days
                        'bg': '#FFFFFF',    # Pure white background
                        'grid': '#F1F5F9',  # Very light gray grid
                        'text': '#1E293B',  # Darker gray for better readability
                        'ma20': '#3B82F6',  # Blue for 20-day MA
                        'ma50': '#F59E0B',  # Amber for 50-day MA
                        'ma200': '#8B5CF6', # Purple for 200-day MA
                        'bollinger': 'rgba(59, 130, 246, 0.15)',  # Lighter blue for Bollinger band
                        'fair_value': '#7C3AED',  # Purple for fair value
                        'hover': '#F8FAFC',  # Lightest gray for hover
                        'volume_up': 'rgba(34, 197, 94, 0.3)',  # Semi-transparent green for up volume
                        'volume_down': 'rgba(239, 68, 68, 0.3)'  # Semi-transparent red for down volume
                    }
                    
                    # Create figure with secondary y-axis for volume and better spacing
                    fig = make_subplots(
                        rows=2, 
                        cols=1, 
                        shared_xaxes=True,
                        vertical_spacing=0.05,  # Reduced spacing for more compact look
                        row_heights=[0.75, 0.25],
                        subplot_titles=('', '')
                    )
                    
                    # Add modern candlesticks with better styling
                    fig.add_trace(
                        go.Candlestick(
                            x=filtered_history.index,
                            open=filtered_history['Open'],
                            high=filtered_history['High'],
                            low=filtered_history['Low'],
                            close=filtered_history['Close'],
                            name='Price',
                            increasing=dict(
                                line=dict(color=colors['up'], width=1.5),
                                fillcolor=colors['up']
                            ),
                            decreasing=dict(
                                line=dict(color=colors['down'], width=1.5),
                                fillcolor=colors['down']
                            ),
                            hoverlabel=dict(
                                bgcolor='white',
                                font_size=12,
                                font_family='Arial',
                                bordercolor=colors['grid']
                            ),
                            hovertext=[f"Open: {o}<br>High: {h}<br>Low: {l}<br>Close: {c}" 
                                     for o, h, l, c in zip(filtered_history['Open'], 
                                                         filtered_history['High'], 
                                                         filtered_history['Low'], 
                                                         filtered_history['Close'])]
                        ),
                        row=1, col=1
                    )
                    
                    # Add modern volume bars with better styling
                    volume_colors = [
                        colors['volume_up'] if close >= open_ else colors['volume_down']
                        for close, open_ in zip(filtered_history['Close'], filtered_history['Open'])
                    ]
                    
                    fig.add_trace(
                        go.Bar(
                            x=filtered_history.index,
                            y=filtered_history['Volume'],
                            name='Volume',
                            marker=dict(
                                color=volume_colors,
                                line=dict(width=0)  # Remove bar borders
                            ),
                            opacity=0.8,
                            showlegend=False,
                            hoverinfo='text',
                            hovertext=[f"Volume: {v:,.0f}" for v in filtered_history['Volume']],
                            hoverlabel=dict(
                                bgcolor='white',
                                font_size=12,
                                font_family='Arial'
                            )
                        ),
                        row=2, col=1
                    )
                    
                    # Get fiscal year end date for fair value line
                    fiscal_year_end = None
                    
                    # Get most recent fiscal year from income statement
                    if not data["income_stmt"].empty and len(data["income_stmt"].columns) > 0:
                        most_recent_year = data["income_stmt"].columns[0]
                        try:
                            date_str = str(most_recent_year).split()[0]
                            year_month_day = date_str.split('-')
                            if len(year_month_day) == 3:
                                fiscal_year = int(year_month_day[0])
                                fiscal_month = int(year_month_day[1])
                                fiscal_day = int(year_month_day[2])
                                fiscal_year_end = datetime.datetime(fiscal_year, fiscal_month, fiscal_day)
                        except Exception as e:
                            fiscal_year_end = datetime.datetime.now() - datetime.timedelta(days=365)
                    else:
                        fiscal_year_end = datetime.datetime.now() - datetime.timedelta(days=365)
                    
                    # Get fair value from session state or data
                    fair_value = (
                        data.get("fair_value", 0) or 
                        (st.session_state.fair_value if hasattr(st.session_state, 'fair_value') else 0) or
                        (filtered_history['Close'].iloc[-1] * 1.2)  # Default to 120% of last price
                    )
                    
                    # Get current price and today's date
                    current_price = filtered_history["Close"].iloc[-1]
                    today = datetime.datetime.now().replace(tzinfo=None)
                    
                    # Add fair value line with modern styling
                    if fair_value > 0:
                        fig.add_trace(
                            go.Scatter(
                                x=[fiscal_year_end, today],
                                y=[current_price, fair_value],
                                name=f"Fair Value: ${fair_value:,.2f}",
                                line=dict(
                                    color=colors['fair_value'],
                                    width=2,
                                    dash='dash'
                                ),
                                mode="lines",
                                hoverinfo="name+y",
                                opacity=0.9
                            ),
                            row=1, col=1
                        )
                        
                        # Add fair value annotation
                        fig.add_annotation(
                            x=today,
                            y=fair_value,
                            text=f"<b>Fair Value</b><br>${fair_value:,.2f}",
                            showarrow=False,
                            font=dict(
                                family="Arial",
                                color="white",
                                size=10
                            ),
                            align="center",
                            bgcolor=colors['fair_value'],
                            bordercolor=colors['fair_value'],
                            borderwidth=1,
                            borderpad=4,
                            opacity=0.9,
                            xshift=10
                        )
                    
                    # Add combined fair value if available
                    if hasattr(st.session_state, 'combined_fair_value') and st.session_state.combined_fair_value > 0 and st.session_state.combined_fair_value != fair_value:
                        fig.add_trace(
                            go.Scatter(
                                x=[fiscal_year_end, today],
                                y=[current_price, st.session_state.combined_fair_value],
                                name=f"{t['multiple_fair_value_label']}: ${st.session_state.combined_fair_value:,.2f}",
                                line=dict(
                                    color=colors['fair_value'],
                                    width=1.5,
                                    dash='dot'
                                ),
                                hoverinfo="name+y",
                                opacity=0.7
                            ),
                            row=1, col=1
                        )
                    
                    # Add technical indicators if enough data is available
                    if not filtered_history.empty and len(filtered_history) > 50:
                        # Calculate Bollinger Bands (20-day MA, 2 std dev)
                        bollinger_window = 20
                        ma20 = filtered_history['Close'].rolling(window=bollinger_window).mean()
                        bollinger_std = filtered_history['Close'].rolling(window=bollinger_window).std()
                        upper_band = ma20 + (bollinger_std * 2)
                        lower_band = ma20 - (bollinger_std * 2)
                        
                        # Add Bollinger Bands with subtle styling
                        fig.add_trace(
                            go.Scatter(
                                x=filtered_history.index,
                                y=upper_band,
                                name='Upper Band',
                                line=dict(color=colors['ma20'], width=0.8, dash='dot'),
                                opacity=0.7,
                                showlegend=False,
                                hoverinfo='skip'
                            ),
                            row=1, col=1
                        )
                        
                        # Add middle band (20-day MA)
                        fig.add_trace(
                            go.Scatter(
                                x=filtered_history.index,
                                y=ma20,
                                name='20-day MA',
                                line=dict(color=colors['ma20'], width=1.2),
                                opacity=0.9,
                                hoverinfo='name+y'
                            ),
                            row=1, col=1
                        )
                        
                        # Add lower band with fill between
                        fig.add_trace(
                            go.Scatter(
                                x=filtered_history.index,
                                y=lower_band,
                                name='Lower Band',
                                line=dict(color=colors['ma20'], width=0.8, dash='dot'),
                                fill='tonexty',
                                fillcolor='rgba(99, 102, 241, 0.1)',
                                opacity=0.7,
                                showlegend=False,
                                hoverinfo='skip'
                            ),
                            row=1, col=1
                        )
                        
                        # Add 50-day moving average
                        ma50 = filtered_history['Close'].rolling(window=50).mean()
                        fig.add_trace(
                            go.Scatter(
                                x=filtered_history.index,
                                y=ma50,
                                name='50-day MA',
                                line=dict(color=colors['ma50'], width=1.5),
                                opacity=0.9,
                                hoverinfo='name+y'
                            ),
                            row=1, col=1
                        )
                        
                        # Add 200-day moving average if enough data is available
                        if len(filtered_history) > 200:
                            ma200 = filtered_history['Close'].rolling(window=200).mean()
                            fig.add_trace(
                                go.Scatter(
                                    x=filtered_history.index,
                                    y=ma200,
                                    name='200-day MA',
                                    line=dict(color=colors['ma200'], width=1.8, dash='dash'),
                                    opacity=0.9,
                                    hoverinfo='name+y'
                                ),
                                row=1, col=1
                            )
                        
                    # Update layout with transparent background
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',  # Fully transparent plot area
                        paper_bgcolor='rgba(0,0,0,0)',  # Fully transparent surrounding area
                        margin=dict(l=10, r=10, t=10, b=10),
                        font=dict(
                            family='Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                            size=12,
                            color=colors['text']
                        ),
                        hovermode='x unified',
                        hoverlabel=dict(
                            bgcolor='white',
                            font_size=12,
                            font_family='Inter, sans-serif',
                            bordercolor=colors['grid']
                        ),
                        legend=dict(
                            orientation='h',
                            yanchor='bottom',
                            y=1.05,
                            xanchor='right',
                            x=1,
                            bgcolor='rgba(255, 255, 255, 0.9)',
                            bordercolor=colors['grid'],
                            borderwidth=1,
                            font=dict(size=11)
                        ),
                        xaxis=dict(
                            showgrid=True,
                            gridcolor=colors['grid'],
                            gridwidth=0.5,
                            showline=False,  # Remove x-axis line
                            linewidth=0.5,   # Thinner line if shown
                            linecolor='rgba(0,0,0,0.1)',  # Lighter line color
                            mirror=False,    # Remove mirror line
                            rangeslider=dict(visible=False),
                            tickfont=dict(size=10)
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor=colors['grid'],
                            gridwidth=0.5,
                            showline=False,  # Remove y-axis line
                            linewidth=0.5,   # Thinner line if shown
                            linecolor='rgba(0,0,0,0.1)',  # Lighter line color
                            mirror=False,    # Remove mirror line
                            fixedrange=False,
                            rangemode='tozero',
                            autorange=True,
                            tickfont=dict(size=10),
                            tickformat=',.0f',
                            tickprefix='$',
                            ticklen=5,
                            tickcolor=colors['grid']
                        ),
                        xaxis2=dict(
                            showgrid=False,
                            showline=False,  # Remove x-axis line for volume
                            linewidth=0.5,   # Thinner line if shown
                            linecolor='rgba(0,0,0,0.1)',  # Lighter line color
                            mirror=False,    # Remove mirror line
                            tickfont=dict(size=10)
                        ),
                        yaxis2=dict(
                            showgrid=False,
                            showticklabels=True,  # Show volume axis labels
                            tickfont=dict(size=9, color='#64748b'),  # Lighter text color
                            showline=False,  # Remove y-axis line for volume
                            linewidth=0.5,   # Thinner line if shown
                            linecolor='rgba(0,0,0,0.1)',  # Lighter line color
                            mirror=False,    # Remove mirror line
                            rangemode='tozero'  # Ensure volume y-axis starts from 0
                        ),
                        height=600,
                        showlegend=True
                    )
                    
                    # Update y-axis title for price chart
                    fig.update_yaxes(title_text='Price', row=1, col=1)
                    
                    # Remove range slider and other interactive elements that can make the chart look cluttered
                    fig.update_xaxes(rangeslider_visible=False)
                    
                    # Disable zoom and pan for a cleaner look
                    fig.update_xaxes(fixedrange=True)
                    fig.update_yaxes(fixedrange=False)  # Allow y-zoom for price chart
                    
                    # Add a subtle border around the chart
                    fig.update_layout(
                        xaxis=dict(domain=[0.03, 0.97]),
                        xaxis2=dict(domain=[0.03, 0.97]),
                        margin=dict(l=50, r=50, t=30, b=30)
                    )
                    
                    # Calculate net debt (Total Debt - Cash & Cash Equivalents)
                    total_debt = yf_data.get("totalDebt", 0) or 0
                    cash = yf_data.get("totalCash", 0) or 0
                    net_debt = max(0, total_debt - cash)  # 음수 방지
                    
                    # 애널리스트 목표가 데이터 가져오기
                    target_high = 0
                    target_low = 0
                    target_median = 0
                    
                    # data["info"]에서 목표가 데이터 확인
                    if "info" in data and hasattr(data["info"], "get"):
                        target_high = data["info"].get('targetHighPrice', 0)
                        target_low = data["info"].get('targetLowPrice', 0)
                        # median이 없으면 mean을 사용
                        target_median = data["info"].get('targetMedianPrice', data["info"].get('targetMeanPrice', 0))
                    
                    # financials에서 목표가 데이터 확인
                    if (target_high == 0 and target_low == 0 and target_median == 0) and hasattr(financials, "get"):
                        target_high = financials.get('targetHighPrice', 0)
                        target_low = financials.get('targetLowPrice', 0)
                        target_median = financials.get('targetMedianPrice', financials.get('targetMeanPrice', 0))
                    
                    # 데이터가 없는 경우 현재 가격 기준으로 예상 목표가 설정
                    if target_high == 0 and target_low == 0 and target_median == 0:
                        current_price = filtered_history["Close"].iloc[-1] if not filtered_history.empty else 0
                        if current_price > 0:
                            target_high = current_price * 1.2  # 20% 상승
                            target_median = current_price * 1.1  # 10% 상승 (중앙값으로 설정)
                            target_low = current_price * 0.9   # 10% 하락
                    
                    # 목표가 데이터가 있는 경우에만 추가
                    if target_high > 0 or target_median > 0 or target_low > 0:
                        # 목표가 전망 날짜 계산 (현재부터 1년 후)
                        last_date = filtered_history.index.max()
                        future_date = last_date + datetime.timedelta(days=365)
                        current_price = filtered_history["Close"].iloc[-1]

                        # 최고 목표가 추가 (첫 번째 서브플롯)
                        if target_high > 0:
                            # 그라데이션 색상 효과를 위한 설정
                            high_color = "rgba(0, 170, 0, 1.0)"  # 진한 녹색
                            
                            # 목표가 예측선 추가
                            fig.add_trace(
                                go.Scatter(
                                    x=[last_date, future_date],
                                    y=[current_price, target_high],
                                    name=f"High {target_high:.2f}",
                                    line=dict(color=high_color, width=2.5, dash="dash"),
                                    mode="lines",
                                    hoverinfo="name+y",
                                    hoverlabel=dict(bgcolor=high_color)
                                ),
                                row=1, col=1
                            )
                            
                            # 세련된 주석 상자
                            fig.add_annotation(
                                x=future_date,
                                y=target_high,
                                text=f"<b>High</b><br>${target_high:.2f}",
                                showarrow=False,
                                font=dict(family="Arial", color="white", size=10),
                                align="center",
                                xshift=10,
                                bgcolor=high_color,
                                bordercolor=high_color,
                                borderwidth=1,
                                borderpad=4,
                                opacity=0.9,
                                xanchor="left"
                            )

                        # 중앙값 목표가 추가 (첫 번째 서브플롯)
                        if target_median > 0:
                            # 중앙값 목표가를 위한 파란색 설정
                            median_color = "rgba(30, 136, 229, 1.0)"  # 진한 파란색
                            
                            # 중앙값 목표가 예측선 추가
                            fig.add_trace(
                                go.Scatter(
                                    x=[last_date, future_date],
                                    y=[current_price, target_median],
                                    name=f"Median {target_median:.2f}",
                                    line=dict(color=median_color, width=2.5, dash="dash"),
                                    mode="lines",
                                    hoverinfo="name+y",
                                    hoverlabel=dict(bgcolor=median_color)
                                ),
                                row=1, col=1
                            )
                            
                            # 중앙값 목표가 주석 추가
                            fig.add_annotation(
                                x=future_date,
                                y=target_median,
                                text=f"<b>Median</b><br>${target_median:.2f}",
                                showarrow=False,
                                font=dict(family="Arial", color="white", size=10),
                                align="center",
                                xshift=10,
                                bgcolor=median_color,
                                bordercolor=median_color,
                                borderwidth=1,
                                borderpad=4,
                                opacity=0.9,
                                xanchor="left"
                            )
                        
                        # 최저 목표가 추가 (첫 번째 서브플롯)
                        if target_low > 0:
                            # 최저 목표가를 위한 빨간색 설정
                            low_color = "rgba(214, 39, 40, 1.0)"  # 진한 빨간색
                            
                            # 최저 목표가 예측선 추가
                            fig.add_trace(
                                go.Scatter(
                                    x=[last_date, future_date],
                                    y=[current_price, target_low],
                                    name=f"Low {target_low:.2f}",
                                    line=dict(color=low_color, width=2.5, dash="dash"),
                                    mode="lines",
                                    hoverinfo="name+y",
                                    hoverlabel=dict(bgcolor=low_color)
                                ),
                                row=1, col=1
                            )
                            
                            # 최저 목표가 주석 추가
                            fig.add_annotation(
                                x=future_date,
                                y=target_low,
                                text=f"<b>Low</b><br>${target_low:.2f}",
                                showarrow=False,
                                font=dict(family="Arial", color="white", size=10),
                                align="center",
                                xshift=10,
                                bgcolor=low_color,
                                bordercolor=low_color,
                                borderwidth=1,
                                borderpad=4,
                                opacity=0.9,
                                xanchor="left"
                            )
                    
                    # 차트 레이아웃 개선
                    fig.update_layout(
                        title={
                            'text': f"{ticker} {t['stock_price_history']}",
                            'font': {'size': 20, 'family': 'Arial', 'color': '#444444'},
                            'y': 0.97
                        },
                        hovermode="x unified",
                        legend={
                            'orientation': "h",
                            'yanchor': "bottom",
                            'y': 1.02,
                            'xanchor': "right",
                            'x': 1,
                            'bgcolor': 'rgba(255, 255, 255, 0.7)',
                            'bordercolor': '#d0d0d0',
                            'font': {'size': 11}
                        },
                        height=600,  # 차트 높이 증가
                        margin={'l': 50, 'r': 80, 't': 80, 'b': 50},
                        plot_bgcolor='rgba(250, 250, 250, 0.9)',
                        paper_bgcolor='white',
                        font={'family': 'Arial'}
                    )
                    
                    # 첫 번째 서브플롯(가격 차트) 레이아웃 설정
                    fig.update_xaxes(
                        title="Date",  # 'start_date'에서 'Date'로 변경
                        showgrid=True,
                        gridcolor='rgba(220, 220, 220, 0.3)',
                        showline=True,
                        linecolor='#d0d0d0',
                        tickfont={'size': 11},
                        row=1, col=1
                    )
                    
                    fig.update_yaxes(
                        title="Price ($)",
                        showgrid=True,
                        gridcolor='rgba(220, 220, 220, 0.3)',
                        showline=True,
                        linecolor='#d0d0d0',
                        tickfont={'size': 11},
                        tickprefix='$',
                        row=1, col=1
                    )
                    
                    # 두 번째 서브플롯(볼륨 차트) 레이아웃 설정
                    fig.update_xaxes(
                        showgrid=True,
                        gridcolor='rgba(220, 220, 220, 0.3)',
                        showline=True,
                        linecolor='#d0d0d0',
                        tickfont={'size': 11},
                        row=2, col=1
                    )
                    
                    fig.update_yaxes(
                        title="Volume",
                        showgrid=True,
                        gridcolor='rgba(220, 220, 220, 0.2)',
                        showline=True,
                        linecolor='#d0d0d0',
                        tickfont={'size': 10, 'color': '#666666'},
                        nticks=5,  # 볼륨 축의 틱 수 제한
                        row=2, col=1
                    )
                    
                    # 그래프 범위 조정 (목표가가 잘 보이도록)
                    if target_high > 0:
                        y_max = max(filtered_history["Close"].max(), target_high) * 1.05
                        y_min = min(filtered_history["Close"].min(), target_low if target_low > 0 else filtered_history["Close"].min()) * 0.95
                        fig.update_yaxes(range=[y_min, y_max], row=1, col=1)  # 첫 번째 서브플롯에만 적용
                        
                    # 미래 예측 부분을 위해 x축 범위 확장
                    if 'future_date' in locals():
                        buffer_days = (future_date - last_date).days * 0.1  # 10% 버퍼 추가
                        extended_date = future_date + datetime.timedelta(days=int(buffer_days))
                        # 모든 서브플롯에 적용 (shared_xaxes 속성 때문에 첫 번째 서브플롯에만 적용해도 됨)
                        fig.update_xaxes(range=[filtered_history.index.min(), extended_date], row=1, col=1)
                        
                    # 볼륨 축 최대값 설정
                    vol_max = filtered_history["Volume"].max() * 1.2
                    fig.update_yaxes(range=[0, vol_max], row=2, col=1)  # 볼륨 축은 0부터 시작
                    
                    # 고정된 주석 위치를 위해 y축 도메인 직접 설정
                    fig.update_layout(
                        yaxis=dict(domain=[0.25, 1.0]),  # 가격 차트가 차지하는 영역 
                        yaxis2=dict(domain=[0, 0.2])     # 볼륨 차트가 차지하는 영역
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Add Price Change Metrics with consistent header style
                    st.markdown("""
                    <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                        Price Change Metrics
                        <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                            <div style='width: 40px; height: 2px; background: #e53e3e;'></div>
                        </div>
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    try:
                        # Get historical data for different time periods
                        today = datetime.datetime.now().date()
                        
                        # Get the most recent price
                        if not filtered_history.empty:
                            current_price = filtered_history['Close'].iloc[-1]
                            
                            # Calculate 1-day change
                            if len(filtered_history) > 1:
                                prev_close = filtered_history['Close'].iloc[-2]
                                day1_change = ((current_price / prev_close) - 1) * 100
                                day1_abs = current_price - prev_close
                            else:
                                day1_change = 0
                                day1_abs = 0
                            
                            # Calculate 5-day change
                            if len(filtered_history) > 5:
                                day5_ago_close = filtered_history['Close'].iloc[-6]
                                day5_change = ((current_price / day5_ago_close) - 1) * 100
                                day5_abs = current_price - day5_ago_close
                            else:
                                day5_change = 0
                                day5_abs = 0
                            
                            # Calculate 1-month, 3-month, 6-month changes (using 21, 63, 126 trading days)
                            days_1m = min(21, len(filtered_history) - 1)
                            days_3m = min(63, len(filtered_history) - 1)
                            days_6m = min(126, len(filtered_history) - 1)
                            
                            if days_1m > 0:
                                month1_ago_close = filtered_history['Close'].iloc[-1 - days_1m]
                                month1_change = ((current_price / month1_ago_close) - 1) * 100
                                month1_abs = current_price - month1_ago_close
                            else:
                                month1_change = 0
                                month1_abs = 0
                                
                            if days_3m > 0:
                                month3_ago_close = filtered_history['Close'].iloc[-1 - days_3m]
                                month3_change = ((current_price / month3_ago_close) - 1) * 100
                                month3_abs = current_price - month3_ago_close
                            else:
                                month3_change = 0
                                month3_abs = 0
                                
                            if days_6m > 0:
                                month6_ago_close = filtered_history['Close'].iloc[-1 - days_6m]
                                month6_change = ((current_price / month6_ago_close) - 1) * 100
                                month6_abs = current_price - month6_ago_close
                            else:
                                month6_change = 0
                                month6_abs = 0
                            
                            # Calculate YTD change
                            current_year = today.year
                            ytd_mask = filtered_history.index >= f"{current_year}-01-01"
                            if ytd_mask.any():
                                ytd_start = filtered_history[ytd_mask].iloc[0]['Close']
                                ytd_change = ((current_price / ytd_start) - 1) * 100
                                ytd_abs = current_price - ytd_start
                            else:
                                ytd_change = 0
                                ytd_abs = 0
                            
                            # Calculate 1-year change (252 trading days)
                            days_1y = min(252, len(filtered_history) - 1)
                            if days_1y > 0:
                                year1_ago_close = filtered_history['Close'].iloc[-1 - days_1y]
                                year1_change = ((current_price / year1_ago_close) - 1) * 100
                                year1_abs = current_price - year1_ago_close
                            else:
                                year1_change = 0
                                year1_abs = 0
                            
                            # Clean Price Change Metrics with OHLC
                            st.markdown("""
                            <style>
                            .price-section {
                                margin-bottom: 20px;
                            }
                            .price-ohlc {
                                display: flex;
                                gap: 20px;
                                margin-bottom: 15px;
                                font-size: 0.95rem;
                            }
                            .ohlc-item {
                                display: flex;
                                align-items: center;
                                gap: 6px;
                            }
                            .ohlc-label {
                                color: #64748b;
                                font-size: 0.85rem;
                            }
                            .ohlc-value {
                                font-weight: 500;
                                color: #1e293b;
                            }
                            .price-change-row {
                                display: flex;
                                gap: 35px;  /* Increased from 25px */
                                overflow-x: auto;
                                padding: 12px 15px 15px 0;  /* Added more padding */
                                margin-bottom: 10px;
                                scrollbar-width: thin;
                                scrollbar-color: #cbd5e1 #f1f5f9;
                            }
                            /* Custom scrollbar for WebKit browsers */
                            .price-change-row::-webkit-scrollbar {
                                height: 6px;
                            }
                            .price-change-row::-webkit-scrollbar-track {
                                background: #f1f5f9;
                                border-radius: 3px;
                            }
                            .price-change-row::-webkit-scrollbar-thumb {
                                background-color: #cbd5e1;
                                border-radius: 3px;
                            }
                            .price-change-item {
                                display: flex;
                                flex-direction: column;
                                align-items: flex-start;  /* Changed from center to flex-start */
                                min-width: 85px;  /* Increased from 70px */
                                padding: 8px 0;  /* Increased vertical padding */
                                position: relative;
                                margin: 0 10px;  /* Increased horizontal margin */
                            }
                            .price-change-item:not(:last-child)::after {
                                content: '';
                                position: absolute;
                                right: -15px;  /* Adjusted position for wider gap */
                                top: 8px;
                                height: 60%;
                                width: 1px;
                                background-color: #e2e8f0;
                            }
                            .price-period {
                                font-size: 0.82rem;
                                font-weight: 600;  /* Made bold */
                                color: #1e293b;  /* Darker color for better readability */
                                margin-bottom: 6px;  /* Increased bottom margin */
                                white-space: nowrap;
                                text-align: left;  /* Ensure left alignment */
                                width: 100%;  /* Ensure full width for alignment */
                            }
                            .price-change-value {
                                font-size: 1.05rem;  /* Slightly larger font */
                                font-weight: 600;
                                display: flex;
                                align-items: center;
                                gap: 4px;  /* Increased gap */
                                margin-bottom: 2px;
                                width: 100%;  /* Ensure full width for alignment */
                            }
                            .price-arrow {
                                font-size: 0.8em;
                                margin-right: 2px;
                            }
                            .price-up {
                                color: #10b981;
                            }
                            .price-down {
                                color: #ef4444;
                            }
                            .price-absolute {
                                font-size: 0.78rem;  /* Slightly larger */
                                color: #64748b;  /* Darker for better readability */
                                white-space: nowrap;
                                margin-top: 2px;  /* Added space between value and absolute */
                                width: 100%;  /* Ensure full width for alignment */
                                text-align: left;  /* Align text to left */
                            }
                            </style>
                            """, unsafe_allow_html=True)
                            
                            def format_price_change(change, abs_change):
                                """Format price change with appropriate styling"""
                                is_positive = change > 0
                                is_negative = change < 0
                                
                                # Format values
                                abs_prefix = "+" if abs_change > 0 else ("-" if abs_change < 0 else "")
                                abs_value = f"{abs_prefix}${abs(abs_change):.2f}"
                                pct_prefix = "+" if is_positive else ("" if change == 0 else "-")
                                pct_value = f"{pct_prefix}{abs(change):.1f}%"
                                
                                # Determine arrow and color class
                                if is_positive:
                                    arrow = "▲"
                                    color_class = "price-up"
                                elif is_negative:
                                    arrow = "▼"
                                    color_class = "price-down"
                                else:
                                    arrow = ""
                                    color_class = ""
                                
                                return {
                                    'pct_display': f"<span class='price-arrow'>{arrow}</span>{pct_value}",
                                    'abs_display': abs_value,
                                    'color_class': color_class
                                }
                            
                            # Get today's OHLC data
                            if not filtered_history.empty:
                                latest_data = filtered_history.iloc[-1]
                                ohlc_data = {
                                    'Open': latest_data.get('Open', 0),
                                    'High': latest_data.get('High', 0),
                                    'Low': latest_data.get('Low', 0),
                                    'Close': latest_data.get('Close', 0)
                                }
                            else:
                                ohlc_data = {'Open': 0, 'High': 0, 'Low': 0, 'Close': 0}
                            
                            # Create OHLC display
                            st.markdown("<div class='price-section'><div class='price-ohlc'>" + 
                                      f"""
                                      <div class='ohlc-item'><span class='ohlc-label'>Open:</span> <span class='ohlc-value'>${ohlc_data['Open']:,.2f}</span></div>
                                      <div class='ohlc-item'><span class='ohlc-label'>High:</span> <span class='ohlc-value' style='color: #10b981;'>${ohlc_data['High']:,.2f}</span></div>
                                      <div class='ohlc-item'><span class='ohlc-label'>Low:</span> <span class='ohlc-value' style='color: #ef4444;'>${ohlc_data['Low']:,.2f}</span></div>
                                      <div class='ohlc-item'><span class='ohlc-label'>Close:</span> <span class='ohlc-value'>${ohlc_data['Close']:,.2f}</span></div>
                                      </div>""", unsafe_allow_html=True)
                            
                            # Create price change items in a horizontal row
                            st.markdown("<div class='price-change-row'>" + 
                                      f"""
                                      <div class='price-change-item'>
                                          <div class='price-period'>1D</div>
                                          <div class='price-change-value {format_price_change(day1_change, day1_abs)['color_class']}'>
                                              {format_price_change(day1_change, day1_abs)['pct_display']}
                                          </div>
                                          <div class='price-absolute'>{format_price_change(day1_change, day1_abs)['abs_display']}</div>
                                      </div>
                                      <div class='price-change-item'>
                                          <div class='price-period'>5D</div>
                                          <div class='price-change-value {format_price_change(day5_change, day5_abs)['color_class']}'>
                                              {format_price_change(day5_change, day5_abs)['pct_display']}
                                          </div>
                                          <div class='price-absolute'>{format_price_change(day5_change, day5_abs)['abs_display']}</div>
                                      </div>
                                      <div class='price-change-item'>
                                          <div class='price-period'>1M</div>
                                          <div class='price-change-value {format_price_change(month1_change, month1_abs)['color_class']}'>
                                              {format_price_change(month1_change, month1_abs)['pct_display']}
                                          </div>
                                          <div class='price-absolute'>{format_price_change(month1_change, month1_abs)['abs_display']}</div>
                                      </div>
                                      <div class='price-change-item'>
                                          <div class='price-period'>3M</div>
                                          <div class='price-change-value {format_price_change(month3_change, month3_abs)['color_class']}'>
                                              {format_price_change(month3_change, month3_abs)['pct_display']}
                                          </div>
                                          <div class='price-absolute'>{format_price_change(month3_change, month3_abs)['abs_display']}</div>
                                      </div>
                                      <div class='price-change-item'>
                                          <div class='price-period'>6M</div>
                                          <div class='price-change-value {format_price_change(month6_change, month6_abs)['color_class']}'>
                                              {format_price_change(month6_change, month6_abs)['pct_display']}
                                          </div>
                                          <div class='price-absolute'>{format_price_change(month6_change, month6_abs)['abs_display']}</div>
                                      </div>
                                      <div class='price-change-item'>
                                          <div class='price-period'>YTD</div>
                                          <div class='price-change-value {format_price_change(ytd_change, ytd_abs)['color_class']}'>
                                              {format_price_change(ytd_change, ytd_abs)['pct_display']}
                                          </div>
                                          <div class='price-absolute'>{format_price_change(ytd_change, ytd_abs)['abs_display']}</div>
                                      </div>
                                      <div class='price-change-item'>
                                          <div class='price-period'>1Y</div>
                                          <div class='price-change-value {format_price_change(year1_change, year1_abs)['color_class']}'>
                                              {format_price_change(year1_change, year1_abs)['pct_display']}
                                          </div>
                                          <div class='price-absolute'>{format_price_change(year1_change, year1_abs)['abs_display']}</div>
                                      </div>
                                      </div></div>
                                      """, unsafe_allow_html=True)
                            
                            # Add some spacing after the metrics
                            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                                
                    except Exception as e:
                        st.error(f"Error calculating price changes: {str(e)}")
                    
                    # Add News Section with consistent header style
                    st.markdown("""
                    <h3 style='color: #1a365d; margin: 24px 0 16px; font-weight: 600; font-size: 1.4rem; position: relative; display: inline-block;'>
                        Latest News
                        <div style='position: absolute; bottom: -8px; left: 0; width: 100%; height: 2px; background: #e2e8f0;'>
                            <div style='width: 40px; height: 2px; background: #e53e3e;'></div>
                        </div>
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    try:
                        # Get news for the current ticker
                        stock = yf.Ticker(ticker)
                        news_list = stock.news
                        
                        if news_list and len(news_list) > 0:
                            for item in news_list:
                                try:
                                    # Skip if item is None
                                    if not item:
                                        continue
                                        
                                    # Safely get content with default empty dict if None
                                    content = item.get('content', {}) or {}
                                    
                                    # Extract data from the news item with proper None checks
                                    title = str(content.get('title', '')).strip()
                                    summary = str(content.get('summary', '')).strip()
                                    
                                    # Safely get URL with nested gets
                                    url = ''
                                    try:
                                        click_through = content.get('clickThroughUrl', {}) or {}
                                        url = str(click_through.get('url', '')).strip()
                                    except (AttributeError, KeyError):
                                        url = ''
                                    
                                    # Create a custom expander that's always expanded
                                    expander = st.expander("", expanded=True)
                                    
                                    # Custom title with larger font and bold
                                    if title:
                                        expander.markdown(f"<h4><b>{title}</b></h4>", unsafe_allow_html=True)
                                    else:
                                        expander.markdown("<h4><b>No title</b></h4>", unsafe_allow_html=True)
                                    
                                    # Display the summary if available
                                    if summary:
                                        expander.markdown(f"<div style='font-size: 14px; margin: 8px 0;'>{summary}</div>", unsafe_allow_html=True)
                                    
                                    # Display the URL as a clickable link that opens in new tab
                                    if url:
                                        expander.markdown(
                                            f"<a href='{url}' target='_blank' style='font-size: 14px; color: #1E88E5; text-decoration: none;'>"
                                            "Read more →</a>", 
                                            unsafe_allow_html=True
                                        )
                                    else:
                                        expander.write("No URL available")
                                            
                                except Exception as item_error:
                                    st.error(f"Error displaying news item: {str(item_error)}")
                        else:
                            st.warning("No news articles found for this stock.")
                    except Exception as e:
                        st.error(f"Error loading news: {str(e)}")
                        import traceback
                        st.text(traceback.format_exc())
                    
                else:
                    st.warning("No historical price data available.")
            
            # Tab 4: About
            with tab4:
                st.markdown("""
                <style>
                    .about-header {
                        font-size: 2.5em;
                        font-weight: 700;
                        color: #1E40AF;
                        margin-bottom: 0.5em;
                        padding-bottom: 0.5em;
                        border-bottom: 2px solid #E5E7EB;
                    }
                    .section-header {
                        font-size: 1.6em;
                        font-weight: 600;
                        color: #111827;
                        margin: 1.8em 0 1em 0;
                        padding: 0.5em 0;
                        position: relative;
                        display: flex;
                        align-items: center;
                    }
                    .section-header::before {
                        content: '';
                        display: inline-block;
                        width: 6px;
                        height: 1.2em;
                        background-color: #3B82F6;
                        margin-right: 12px;
                        border-radius: 3px;
                    }
                    .subsection-header {
                        font-size: 1.3em;
                        font-weight: 600;
                        color: #1F2937;
                        margin: 1.5em 0 0.8em 0;
                        padding-bottom: 0.4em;
                        border-bottom: 1px solid #E5E7EB;
                        display: flex;
                        align-items: center;
                    }
                    .subsection-header::before {
                        content: '→';
                        color: #6B7280;
                        margin-right: 8px;
                        font-size: 1.1em;
                        opacity: 0.7;
                    }
                    .card {
                        background: #FFFFFF;
                        border-radius: 10px;
                        padding: 1.5em;
                        margin: 1em 0;
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                        border-left: 4px solid #3B82F6;
                    }
                    .formula {
                        background: #F9FAFB;
                        padding: 1em;
                        border-radius: 8px;
                        font-family: 'Courier New', monospace;
                        margin: 1em 0;
                        border-left: 3px solid #3B82F6;
                    }
                    .highlight {
                        color: #3B82F6;
                        font-weight: 600;
                    }
                </style>
                """, unsafe_allow_html=True)

                # Header
                st.markdown("<div class='about-header'>About</div>", unsafe_allow_html=True)
                
                # Introduction
                st.markdown("""
                Welcome to our comprehensive financial analysis platform, designed for investors who demand professional-grade valuation tools.
                This application combines multiple valuation methodologies to provide you with a 360-degree view of a company's intrinsic value.
                """)

                # Key Features
                st.markdown("<div class='section-header'>Key Features</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                    <div class='card'>
                        <div class='subsection-header'>Multi-Model Valuation</div>
                        <ul style='margin-top: 0.5em; padding-left: 1.2em;'>
                            <li>Discounted Cash Flow (DCF) Analysis</li>
                            <li>Earnings-Based Valuation</li>
                            <li>Free Cash Flow to Equity (FCFE)</li>
                            <li>Relative Valuation Multiples</li>
                        </ul>
                    </div>
                    
                    <div class='card'>
                        <div class='subsection-header'>Comprehensive Financials</div>
                        <ul style='margin-top: 0.5em; padding-left: 1.2em;'>
                            <li>Income Statement Analysis</li>
                            <li>Balance Sheet Metrics</li>
                            <li>Cash Flow Statement Review</li>
                            <li>Key Financial Ratios</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div class='card'>
                        <div class='subsection-header'>Advanced Analytics</div>
                        <ul style='margin-top: 0.5em; padding-left: 1.2em;'>
                            <li>Sensitivity Analysis</li>
                            <li>Scenario Modeling</li>
                            <li>Historical Performance</li>
                            <li>Peer Comparison</li>
                        </ul>
                    </div>
                    
                    <div class='card'>
                        <div class='subsection-header'>User Experience</div>
                        <ul style='margin-top: 0.5em; padding-left: 1.2em;'>
                            <li>Interactive Visualizations</li>
                            <li>Responsive Design</li>
                            <li>Multi-language Support</li>
                            <li>Customizable Parameters</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)

                # Valuation Models
                st.markdown(
                    "<div class='section-header'>Core Valuation Methodologies</div>", 
                    unsafe_allow_html=True
                )
                
                # DCF Model
                st.markdown(
                    "<div class='subsection-header'>Discounted Cash Flow (DCF) Analysis</div>", 
                    unsafe_allow_html=True
                )
                st.markdown(
                    "The DCF model is a fundamental valuation method that estimates the intrinsic value of a company by forecasting its future cash flows and discounting them to their present value. This approach is based on the principle that the value of a company is equal to the present value of all its future cash flows."
                )
                
                dcf_formula = """
                Enterprise Value = ∑ (FCF_t / (1 + WACC)^t) + TV / (1 + WACC)^n
                
                Where:
                • FCF_t = Free Cash Flow in period t
                • WACC = Weighted Average Cost of Capital
                • TV = Terminal Value = FCF_n × (1 + g) / (WACC - g)
                • g = Perpetual growth rate
                • n = Number of forecast periods
                """
                st.markdown(
                    f"<div class='formula'>{dcf_formula}</div>",
                    unsafe_allow_html=True
                )
                
                assumptions = """
                <div style='background-color: #EFF6FF; padding: 1em; border-radius: 8px; margin: 1em 0;'>
                    <strong>Key Assumptions:</strong>
                    <ul style='margin: 0.5em 0 0 1.5em;'>
                        <li>Forecast Period: 10 years of explicit forecast</li>
                        <li>Terminal Growth: 2.5% (aligned with long-term GDP growth)</li>
                        <li>Discount Rate: Company-specific WACC</li>
                    </ul>
                </div>
                """
                st.markdown(assumptions, unsafe_allow_html=True)

                # WACC Explanation
                st.markdown(
                    "<div class='subsection-header'>Weighted Average Cost of Capital (WACC)</div>", 
                    unsafe_allow_html=True
                )
                st.markdown(
                    "WACC represents the average rate of return a company is expected to pay to all its security holders to finance its assets. It's a critical component in DCF analysis as it's used as the discount rate."
                )
                
                wacc_formula = """
                WACC = (E/V) × Re + (D/V) × Rd × (1 - Tc)
                
                Where:
                • E = Market value of equity
                • D = Market value of debt
                • V = Total market value (E + D)
                • Re = Cost of equity (CAPM: Rf + β × (Rm - Rf))
                • Rd = Cost of debt
                • Tc = Corporate tax rate
                """
                st.markdown(
                    f"<div class='formula'>{wacc_formula}</div>",
                    unsafe_allow_html=True
                )
                
                # Additional Resources
                st.markdown(
                    "<div class='section-header'>Additional Resources</div>",
                    unsafe_allow_html=True
                )
                additional_resources = (
                    "- **Financial Statement Guide**: How to interpret key metrics\n"
                    "- **Valuation Best Practices**: Industry standards and methodologies\n"
                    "- **Financial Modeling Standards**: Best practices for building robust models\n"
                    "- **Glossary of Terms**: Definitions of financial terms and metrics"
                )
                st.markdown(additional_resources)
                
                # Disclaimer
                st.markdown(
                    "<div class='section-header'>Important Disclaimer</div>",
                    unsafe_allow_html=True
                )
                disclaimer = """
                <div style='background-color: #F8FAFC; padding: 1.2em; border-radius: 8px; border-left: 4px solid #E5E7EB; color: #4B5563; line-height: 1.6;'>
                    <strong>Note:</strong> This application is for informational and educational purposes only. The valuations and analyses provided should not be considered as financial advice or recommendations to buy, sell, or hold any security. Always conduct your own research and consult with a qualified financial advisor before making investment decisions.
                </div>
                """
                st.markdown(disclaimer, unsafe_allow_html=True)
                
                # Additional Valuation Methods
                st.markdown(
                    "<div class='section-header'>Additional Valuation Methods</div>",
                    unsafe_allow_html=True
                )
                
                st.markdown(
                    "<div class='subsection-header'>DCF (Free Cash Flow Based)</div>",
                    unsafe_allow_html=True
                )
                st.markdown("""
                Similar to Earnings-based DCF, but uses Free Cash Flow per share instead of EPS. This approach is often 
                considered more accurate since it accounts for actual cash generation rather than accounting earnings.
                """)
                
                st.markdown(
                    "<div class='subsection-header'>ROIC (Return on Invested Capital)</div>",
                    unsafe_allow_html=True
                )
                roic_text = (
                    "ROIC measures how efficiently a company generates returns from the capital invested in its business. "
                    "It's a key metric for evaluating management's effectiveness at allocating capital to profitable investments.\n\n"
                    "**Formula:**\n"
                    "```\n"
                    "ROIC = NOPAT / Invested Capital\n\n"
                    "Where:\n"
                    "• NOPAT = Net Operating Profit After Tax = EBIT * (1 - Tax Rate)\n"
                    "• Invested Capital = Total Equity + Total Debt - Cash\n"
                    "```"
                )
                st.markdown(roic_text)
                
                # Final Note
                st.markdown(
                    "<div class='section-header'>Important Notice</div>",
                    unsafe_allow_html=True
                )
                notice = """
                <div style='background-color: #F8FAFC; padding: 1.2em; border-radius: 8px; border-left: 4px solid #E5E7EB; color: #4B5563; line-height: 1.6;'>
                    <strong>Note:</strong> This application is for informational and educational purposes only. The valuations and analyses provided should not be considered as financial advice or recommendations to buy, sell, or hold any security. Always conduct your own research and consult with a qualified financial advisor before making investment decisions.
                </div>
                """
                st.markdown(notice, unsafe_allow_html=True)
                st.markdown(disclaimer, unsafe_allow_html=True)
                
                # Additional Valuation Methods
                
                st.markdown(
                    "<div class='subsection-header'>DCF (Free Cash Flow Based)</div>",
                    unsafe_allow_html=True
                )
                st.markdown("""
                Similar to Earnings-based DCF, but uses Free Cash Flow per share instead of EPS. This approach is often 
                considered more accurate since it accounts for actual cash generation rather than accounting earnings.
                """)
                
                st.markdown(
                    "<div class='subsection-header'>ROIC (Return on Invested Capital)</div>",
                    unsafe_allow_html=True
                )
                roic_text = (
                    "ROIC measures how efficiently a company generates returns from the capital invested in its business. "
                    "It's a key metric for evaluating management's effectiveness at allocating capital to profitable investments.\n\n"
                    "**Formula:**\n"
                    "```\n"
                    "ROIC = NOPAT / Invested Capital\n\n"
                    "Where:\n"
                    "• NOPAT = Net Operating Profit After Tax = EBIT * (1 - Tax Rate)\n"
                    "• Invested Capital = Total Equity + Total Debt - Cash\n"
                    "```"
                )
                st.markdown(roic_text)
                
if __name__ == "__main__":
    main()
