"""
Financial calculation functions for the DCF calculator application.
"""
from .utils import safe_get
import pandas as pd
import math
import yfinance as yf

def calculate_wacc(financials, risk_free_rate, market_risk_premium=0.06, custom_inputs=None):
    """
    Calculate WACC (Weighted Average Cost of Capital).
    
    Parameters:
    - financials: Dictionary containing financial metrics
    - risk_free_rate: Risk-free rate (decimal, 0.035 means 3.5%)
    - market_risk_premium: Market risk premium (decimal, 0.06 means 6%)
    - custom_inputs: Dictionary of custom inputs for override
    
    Returns:
    - Dictionary containing WACC and its components
    """
    # 모든 기본 변수 초기화
    interest_expense = 0
    average_debt = 0
    if custom_inputs and custom_inputs.get("use_custom_wacc", False):
        # Ensure custom WACC is in decimal form
        custom_wacc = custom_inputs.get("wacc", 0.09)
        if custom_wacc > 1:
            custom_wacc = custom_wacc / 100
        return custom_wacc
    
    # Convert percentage inputs to decimals if needed
    # (ONLY CONVERT IF USER HASN'T ALREADY)
    if risk_free_rate > 1:
        risk_free_rate = risk_free_rate / 100
    if market_risk_premium > 1:
        market_risk_premium = market_risk_premium / 100
    
    # 사용자 입력값을 우선적으로 사용, 없으면 재무데이터에서 값 사용
    # custom_inputs가 있는 경우 해당 값을 우선 사용
    if custom_inputs and custom_inputs.get("user_provided", False):
        # Beta 값 가져오기 - 사용자 입력(있는 경우) 또는 financials에서 가져오기
        beta = custom_inputs.get("beta", financials.get("beta", 1.0))
        
        # Risk-free rate 가져오기 - 사용자 입력 우선 (사용자가 이미 입력한 소수점 값 유지)
        if "risk_free_rate" in custom_inputs:
            risk_free_rate = custom_inputs.get("risk_free_rate")
            # 백분율일 경우 소수점으로 변환은 UI에서 처리하므로 여기서는 생략
        
        # Market risk premium 가져오기 - 사용자 입력 우선 (사용자가 이미 입력한 소수점 값 유지)
        if "market_risk_premium" in custom_inputs:
            market_risk_premium = custom_inputs.get("market_risk_premium")
            # 백분율일 경우 소수점으로 변환은 UI에서 처리하므로 여기서는 생략
        
        # Tax rate 가져오기 - 사용자 입력 우선 (사용자가 이미 입력한 소수점 값 유지)
        if "tax_rate" in custom_inputs:
            tax_rate = custom_inputs.get("tax_rate")
            # 백분율일 경우 소수점으로 변환은 UI에서 처리하므로 여기서는 생략
            # 합리적 범위로 제한 (0-50%)
            tax_rate = min(max(tax_rate, 0), 0.5)
    else:
        # 사용자 입력이 없는 경우 기본값 사용
        beta = financials.get("beta", 1.0)  # Use exact beta value 
        tax_rate = min(max(financials.get("tax_rate", 21.0) / 100 if financials.get("tax_rate", 21.0) > 1 else financials.get("tax_rate", 0.21), 0), 0.5)
    
    # 항상 필요한 기본 값들
    total_debt = max(0, financials.get("total_debt", 0))
    market_cap = max(0, financials.get("market_cap", 0))
    
    # Initialize average_debt to ensure it's always defined
    average_debt = financials.get("total_debt", 0)
    
    # Calculate cost of equity using CAPM with validation
    # If user provided cost_of_equity directly, use that value
    if custom_inputs and custom_inputs.get("user_provided", False) and "cost_of_equity" in custom_inputs:
        cost_of_equity = custom_inputs.get("cost_of_equity")
    else:
        cost_of_equity = max(risk_free_rate + beta * market_risk_premium, risk_free_rate + 0.02)
    
    # Calculate cost of debt with validation
    # 사용자가 명시적으로 cost_of_debt를 제공했는지 확인
    user_provided_cod = False
    if custom_inputs and custom_inputs.get("user_provided", False) and "cost_of_debt" in custom_inputs:
        cost_of_debt = custom_inputs.get("cost_of_debt")
        user_provided_cod = True
    else:
        cost_of_debt = 0
    
    # 백분율 검사는 UI에서 처리하므로 여기서는 생략
    
    # 사용자가 명시적으로 값을 입력한 경우 그 값을 사용 (비록 0이라도)
    # 그렇지 않은 경우에만 재무데이터에서 계산
    if not user_provided_cod and cost_of_debt <= 0:
        # Try to get interest expense from financial data
        interest_expense = financials.get("interest_expense_non_operating", 0)
        
        # If Interest Expense Non Operating is not available, fall back to regular interest expense
        if interest_expense <= 0:
            interest_expense = financials.get("interest_expense", 0)
            
        # 이자비용이 모두 0이면 직접 income_stmt에서 찾아보기
        if interest_expense <= 0 and "income_stmt" in financials:
            income_stmt = financials.get("income_stmt")
            
            if income_stmt is not None and not income_stmt.empty and len(income_stmt.columns) > 0:
                # Ensure we're using the first column (most recent fiscal year)
                most_recent_column = income_stmt.columns[0]
                
                interest_field_names = [
                    "Interest Expense", 
                    "Interest Expense, Net", 
                    "Interest Expense Net",
                    "Net Interest Expense",
                    "Interest Paid",
                    "Finance Costs",
                    "Financial Expenses",
                    "Interest Expense Non Operating",
                    "Interest Expense, Net Non Operating", 
                    "Non Operating Interest Expense"
                ]
                
                for field in interest_field_names:
                    if field in income_stmt.index:
                        # Explicitly using .loc[field, most_recent_column] to get first column value
                        value = income_stmt.loc[field, most_recent_column]
                        if pd.notnull(value) and value != 0:
                            interest_expense = abs(value)  # 음수로 표시될 수 있으므로 절대값 사용
                            break
        
        # Get total debt values from balance sheet for multiple years
        balance_sheet = financials.get("balance_sheet", None)
        total_debt_values = []
        
        if balance_sheet is not None and not balance_sheet.empty:
            # Try to get "Total Debt" for up to 3 most recent years
            for col_idx in range(min(3, len(balance_sheet.columns))):
                col = balance_sheet.columns[col_idx]
                
                # Check for "Total Debt" directly
                if "Total Debt" in balance_sheet.index:
                    total_debt = balance_sheet.loc["Total Debt", col]
                    if pd.notnull(total_debt) and total_debt > 0:
                        total_debt_values.append(total_debt)
                # Otherwise, try Long Term + Short Term Debt
                elif "Long Term Debt" in balance_sheet.index and "Short Term Debt" in balance_sheet.index:
                    ltd = balance_sheet.loc["Long Term Debt", col]
                    std = balance_sheet.loc["Short Term Debt", col]
                    if pd.notnull(ltd) and pd.notnull(std):
                        total_debt = ltd + std
                        if total_debt > 0:
                            total_debt_values.append(total_debt)
        
        # Calculate average debt
        average_debt = 0
        if total_debt_values:
            average_debt = sum(total_debt_values) / len(total_debt_values)
        else:
            # Fall back to the single total debt value if no multiple years data
            average_debt = financials.get("total_debt", 0)
        
        # 이자비용 및 cost of debt 계산 관련 정보 저장
        cod_info = {
            "interest_expense": interest_expense,
            "average_debt": average_debt,
            "interest_expense_is_zero": interest_expense <= 0,
            "source": "calculated"
        }
        
        # Calculate cost of debt using average debt
        if interest_expense > 0 and average_debt > 0:
            cost_of_debt = interest_expense / average_debt
            cod_info["source"] = "calculated"
        else:
            # Default to risk-free rate plus a spread if can't calculate
            cost_of_debt = risk_free_rate + 0.02
            cod_info["source"] = "default"
            
            # 이자비용이 0인 경우 표시 (애플과 같은 회사는 실제로 부채가 거의 없을 수 있음)
            if interest_expense <= 0:
                print(f"WARNING: Interest Expense is zero or negative. Company may have minimal debt or special financial structure.")
                # 이 경우 사용자가 직접 입력할 수 있도록 UI에 정보 전달
    
    # Cost of debt는 주로 risk-free rate보다 높아야 함 (risk premium)
    if cost_of_debt < risk_free_rate:
        # risk-free rate에 적절한 risk premium을 추가 (회사의 규모/신용도에 따라 다를 수 있음)
        cost_of_debt = risk_free_rate + 0.02  # 일반적으로 2%의 스프레드 적용
    
    # Ensure cost_of_debt is within reasonable bounds
    cost_of_debt = max(min(cost_of_debt, 0.20), risk_free_rate + 0.01)  # Constrain between Rf+1% and 20%
    
    # Calculate weights for WACC with validation
    # 사용자가 weight_of_debt를 직접 입력한 경우 우선 사용
    if custom_inputs and custom_inputs.get("user_provided", False) and "weight_of_debt" in custom_inputs:
        weight_of_debt = custom_inputs.get("weight_of_debt")
        
        # 백분율 검사는 UI에서 처리하므로 여기서는 생략
        
        # 합리적 범위 확인 (0-90%)
        weight_of_debt = min(max(weight_of_debt, 0), 0.9)
    else:
        # 사용자 입력이 없는 경우 재무데이터로 계산
        total_value = market_cap + total_debt
        if total_value > 0:
            # Calculate weight of equity (E / (D+E))
            weight_of_equity = market_cap / total_value
            weight_of_debt = 1 - weight_of_equity
        else:
            # 데이터가 없는 경우 기본값 설정
            weight_of_debt = 0.3
            weight_of_equity = 0.7
    
    # weight_of_equity는 항상 계산해주기 (weight_of_debt만 정의된 경우 대비)
    weight_of_equity = 1 - weight_of_debt
    
    # Calculate after-tax cost of debt (Cost of Debt * (1 - Tax Rate))
    # - 세금 효과를 고려한 세후 부채 비용 계산
    after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
    
    # Calculate WACC components
    wacc_equity_component = weight_of_equity * cost_of_equity
    wacc_debt_component = weight_of_debt * after_tax_cost_of_debt
    
    # Calculate final WACC (WACC = wE * rE + wD * rD * (1-t))
    wacc = wacc_equity_component + wacc_debt_component
    
    # Ensure WACC is within reasonable bounds
    wacc = max(min(wacc, 0.30), risk_free_rate + 0.02)
    
    # Prepare the result dictionary with all relevant values
    # Store all values exactly as they are, without any conversions
    wacc_result = {
        "wacc": wacc,  # Final WACC
        "cost_of_equity": cost_of_equity,  # Cost of Equity (rE)
        "cost_of_debt": cost_of_debt,  # Cost of Debt (rD)
        "tax_rate": tax_rate,  # Tax Rate (t)
        "after_tax_cost_of_debt": after_tax_cost_of_debt,  # After-tax Cost of Debt (rD * (1-t))
        "weight_of_equity": weight_of_equity,  # Weight of Equity (wE)
        "weight_of_debt": weight_of_debt,  # Weight of Debt (wD)
        "beta": beta,  # Beta (β)
        "risk_free_rate": risk_free_rate,  # Risk-free Rate (rf)
        "market_risk_premium": market_risk_premium,  # Market Risk Premium (rm - rf)
        "wacc_equity_component": weight_of_equity * cost_of_equity * 100,  # Equity Component (wE * rE) in percentage
        "wacc_debt_component": weight_of_debt * after_tax_cost_of_debt * 100,  # Debt Component (wD * rD * (1-t)) in percentage
        "average_debt": average_debt,  # Average Debt calculated from balance sheet
    }
    
    return wacc_result

def safe_get_multi(df, possible_names, column_index=0):
    """Get value from DataFrame with multiple possible row names"""
    if isinstance(possible_names, str):
        possible_names = [possible_names]
    
    if df is None or df.empty or len(df.columns) <= column_index:
        return None  # Return None instead of 0 to indicate missing data
    
    for name in possible_names:
        if name in df.index:
            value = df.loc[name].iloc[column_index]
            if pd.notnull(value):
                try:
                    return float(value)  # Convert string to number if needed
                except (ValueError, TypeError):
                    return None
    
    return None  # Return None if no valid value found

def calculate_financial_ratios(income_stmt, balance_sheet, cash_flow, history, current_price, shares_outstanding, ticker=None, language='English'):
    """
    Calculate key financial ratios from financial statements.
    
    Parameters:
    - income_stmt: DataFrame containing income statement data
    - balance_sheet: DataFrame containing balance sheet data
    - cash_flow: DataFrame containing cash flow statement data
    - history: DataFrame containing historical price data
    - current_price: Current stock price
    - shares_outstanding: Number of shares outstanding
    - ticker: Stock ticker symbol to fetch data  (optional)
    
    Returns:
    - Dictionary with calculated financial ratios
    """
    ratios = {}

    # Helper function to get values safely from financial statements
    def safe_get_multi(df, possible_names, column_index=0):
        """Get value from DataFrame with multiple possible row names"""
        if isinstance(possible_names, str):
            possible_names = [possible_names]
        
        if df is None or df.empty or len(df.columns) <= column_index:
            return 0
        
        for name in possible_names:
            if name in df.index:
                value = df.loc[name].iloc[column_index]
                if pd.notnull(value):
                    try:
                        return float(value)  # Convert string to number if needed
                    except (ValueError, TypeError):
                        return 0
        
        return 0
    
    try:        
        if ticker is not None:
            try:
                stock = yf.Ticker(ticker)
                yf_data = stock.info
                
                # Fetch and log TTM and Forward values
                ratios['ttm_pe'] = yf_data.get('trailingPE', 0)
                ratios['forward_pe'] = yf_data.get('forwardPE', 0)
                # 사용자 요청에 따라 정확한 키 이름 사용
                ratios['ttm_eps'] = yf_data.get('trailingEps', 0)
                ratios['forward_eps'] = yf_data.get('forwardEps', 0)
                
                # trailingEPS가 없지만 다른 방법으로 EPS 계산이 가능한 경우
                if ratios['ttm_eps'] == 0 and yf_data.get('netIncome', 0) > 0 and yf_data.get('sharesOutstanding', 0) > 0:
                    backup_eps = yf_data.get('netIncome', 0) / yf_data.get('sharesOutstanding', 0)
                    # 이 값이 현실적인지 확인 (주가의 50% 이하인 경우에만 사용)
                    if backup_eps > 0 and backup_eps < yf_data.get('currentPrice', 1000) * 0.5:
                        ratios['ttm_eps'] = backup_eps
                
            except Exception as e:
                print(f"Error fetching data: {e}")
                # Set default values on error
                ratios['ttm_pe'] = 0
                ratios['forward_pe'] = 0
                ratios['ttm_eps'] = 0
                ratios['forward_eps'] = 0
        else:
            ratios['ttm_pe'] = 0
            ratios['forward_pe'] = 0
            ratios['ttm_eps'] = 0
            ratios['forward_eps'] = 0
        
        # Get values from income statement
        total_revenue = safe_get_multi(income_stmt, ["Total Revenue", "Revenue"], 0)
        prev_year_revenue = safe_get_multi(income_stmt, ["Total Revenue", "Revenue"], 1) if income_stmt is not None and len(income_stmt.columns) > 1 else 0
        
        gross_profit = safe_get_multi(income_stmt, ["Gross Profit"], 0)
        operating_income = safe_get_multi(income_stmt, ["Operating Income", "EBIT"], 0)
        net_income = safe_get_multi(income_stmt, ["Net Income", "Net Income Common Stockholders"], 0)
        prev_net_income = safe_get_multi(income_stmt, ["Net Income", "Net Income Common Stockholders"], 1) if income_stmt is not None and len(income_stmt.columns) > 1 else 0
        
        ebit = safe_get_multi(income_stmt, ["EBIT", "Operating Income"], 0)
        ebitda = safe_get_multi(income_stmt, ["EBITDA"], 0)
        income_tax = safe_get_multi(income_stmt, ["Income Tax Expense", "Tax Provision"], 0)
        
        # Get values from balance sheet
        total_assets = safe_get_multi(balance_sheet, ["Total Assets"], 0)
        total_equity = safe_get_multi(balance_sheet, ["Total Equity", "Stockholders Equity", "Shareholders Equity", "Common Stock Equity"], 0)
        total_liabilities = safe_get_multi(balance_sheet, ["Total Liabilities", "Total Liabilities Net Minority Interest"], 0)
        if total_liabilities == 0 and total_assets > 0 and total_equity > 0:
            total_liabilities = total_assets - total_equity
            
        # Get more values from balance sheet for liquidity ratios
        current_assets = safe_get_multi(balance_sheet, ["Current Assets", "Total Current Assets"], 0)
        current_liabilities = safe_get_multi(balance_sheet, ["Current Liabilities", "Total Current Liabilities"], 0)
        cash_and_equivalents = safe_get_multi(balance_sheet, ["Cash And Cash Equivalents", "Cash and Short Term Investments"], 0)
        inventories = safe_get_multi(balance_sheet, ["Inventory", "Inventories"], 0)
        accounts_receivable = safe_get_multi(balance_sheet, ["Accounts Receivable", "Net Receivables"], 0)
        
        # Get values from cash flow
        operating_cash_flow = safe_get_multi(cash_flow, ["Operating Cash Flow", "Cash from Operations"], 0)
        capital_expenditure = safe_get_multi(cash_flow, ["Capital Expenditure", "Capital Expenditures"], 0)
        free_cash_flow = safe_get_multi(cash_flow, ["Free Cash Flow"], 0)
        if free_cash_flow == 0 and operating_cash_flow != 0 and capital_expenditure != 0:
            # Often capital_expenditure is negative, so add it to operating_cash_flow
            free_cash_flow = operating_cash_flow + capital_expenditure
        
        # Calculate market cap
        market_cap = current_price * shares_outstanding if shares_outstanding > 0 else 0
        
        # 1. Profitability Ratios
        
        # 1.1 Gross Profit Margin (매출총이익률)
        if ticker is not None and yf_data:
            try:
                if 'grossProfits' in yf_data and 'totalRevenue' in yf_data and yf_data['grossProfits'] is not None and yf_data['totalRevenue'] is not None and yf_data['totalRevenue'] > 0:
                    ratios["gross_margin"] = yf_data['grossProfits'] / yf_data['totalRevenue']
                else:
                    # Fallback to old calculation if necessary fields are missing
                    if total_revenue > 0:
                        ratios["gross_margin"] = gross_profit / total_revenue
            except Exception as e:
                print(f"Error calculating gross margin : {e}")
                if total_revenue > 0:
                    ratios["gross_margin"] = gross_profit / total_revenue
        elif total_revenue > 0:
            ratios["gross_margin"] = gross_profit / total_revenue
            
        # Status evaluation based on the provided table - performed regardless of data source
        if ratios["gross_margin"] < 0.05:
            ratios["gross_margin_status"] = {
                "level": "Poor", 
                "level_en": "Poor", 
                "level_ko": "저조", 
                "level_zh": "较差",
                "color": "red", 
                "description": "Low profit structure due to poor cost control.",
                "description_en": "Low profit structure due to poor cost control.",
                "description_ko": "원가 통제 미흡으로 인한 저수익 구조입니다.",
                "description_zh": "由于总成本管理不良导致低收益结构。"
            }
        elif ratios["gross_margin"] < 0.10:
            ratios["gross_margin_status"] = {
                "level": "Average", 
                "level_en": "Average", 
                "level_ko": "보통", 
                "level_zh": "一般",
                "color": "yellow", 
                "description": "Industry average level of gross profit margin.",
                "description_en": "Industry average level of gross profit margin.",
                "description_ko": "업계 평균 수준의 매출총이익률입니다.",
                "description_zh": "行业平均水平的毛利率。"
            }
        elif ratios["gross_margin"] > 0.10:
            ratios["gross_margin_status"] = {
                "level": "Good", 
                "level_en": "Good", 
                "level_ko": "우수", 
                "level_zh": "良好",
                "color": "green", 
                "description": "Good pricing power and cost efficiency.",
                "description_en": "Good pricing power and cost efficiency.",
                "description_ko": "가격 결정력과 원가 효율이 양호합니다.",
                "description_zh": "良好的定价能力和成本效率。"
            }
        else:
            ratios["gross_margin"] = 0
            ratios["gross_margin_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Cannot calculate due to missing revenue data.",
                "description_en": "Cannot calculate due to missing revenue data.",
                "description_ko": "매출 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少收入数据，无法计算。"
            }
        
        # 1.2 Operating Profit Margin (영업이익률)
        if ticker is not None and yf_data:
            try:
                if 'operatingMargins' in yf_data and yf_data['operatingMargins'] is not None:
                    ratios["operating_margin"] = yf_data['operatingMargins']
                else:
                    # Fallback to old calculation if necessary fields are missing
                    if total_revenue > 0:
                        ratios["operating_margin"] = operating_income / total_revenue
            except Exception as e:
                if total_revenue > 0:
                    ratios["operating_margin"] = operating_income / total_revenue
        elif total_revenue > 0:
            ratios["operating_margin"] = operating_income / total_revenue
            
        # Status evaluation based on the provided table - performed regardless of data source
        if ratios["operating_margin"] < 0.05:
            ratios["operating_margin_status"] = {
                "level": "Weak", 
                "level_en": "Weak", 
                "level_ko": "취약", 
                "level_zh": "薄弱",
                "color": "red", 
                "description": "Operational efficiency is weak.",
                "description_en": "Operational efficiency is weak.",
                "description_ko": "운영 효율성이 취약합니다.",
                "description_zh": "运营效率薄弱。"
            }
        elif ratios["operating_margin"] < 0.15:
            ratios["operating_margin_status"] = {
                "level": "Average", 
                "level_en": "Average", 
                "level_ko": "보통", 
                "level_zh": "一般",
                "color": "yellow", 
                "description": "Shows operating performance within industry average.",
                "description_en": "Shows operating performance within industry average.",
                "description_ko": "업종 평균 내 운영성과를 보여줍니다.",
                "description_zh": "显示在行业平均水平内的运营表现。"
            }
        elif ratios["operating_margin"] > 0.15:
            ratios["operating_margin_status"] = {
                "level": "Excellent", 
                "level_en": "Excellent", 
                "level_ko": "우수", 
                "level_zh": "优秀",
                "color": "green", 
                "description": "Has a high-value business structure.",
                "description_en": "Has a high-value business structure.",
                "description_ko": "고부가 사업구조를 갖추고 있습니다.",
                "description_zh": "具有高附加值的业务结构。"
            }
        else:
            ratios["operating_margin"] = 0
            ratios["operating_margin_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Cannot calculate due to missing revenue data.",
                "description_en": "Cannot calculate due to missing revenue data.",
                "description_ko": "매출 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少收入数据，无法计算。"
            }
        
        # 1.3 Net Profit Margin (순이익률)
        if ticker is not None and yf_data:
            try:
                if 'netIncomeToCommon' in yf_data and 'totalRevenue' in yf_data and yf_data['netIncomeToCommon'] is not None and yf_data['totalRevenue'] is not None and yf_data['totalRevenue'] > 0:
                    ratios["net_profit_margin"] = yf_data['netIncomeToCommon'] / yf_data['totalRevenue']
                else:
                    if total_revenue > 0:
                        ratios["net_profit_margin"] = net_income / total_revenue
            except Exception as e:
                if total_revenue > 0:
                    ratios["net_profit_margin"] = net_income / total_revenue
        elif total_revenue > 0:
            ratios["net_profit_margin"] = net_income / total_revenue
            
        # Status evaluation based on the provided table - performed regardless of data source
        if ratios["net_profit_margin"] < 0.05:
            ratios["net_profit_status"] = {
                "level": "Poor", 
                "level_en": "Poor", 
                "level_ko": "저조", 
                "level_zh": "较差",
                "color": "red", 
                "description": "Low profit structure due to poor total cost management.",
                "description_en": "Low profit structure due to poor total cost management.",
                "description_ko": "총비용 관리 미흡으로 인한 저수익 구조입니다.",
                "description_zh": "由于总成本管理不良导致低收益结构。"
            }
        elif ratios["net_profit_margin"] < 0.10:
            ratios["net_profit_status"] = {
                "level": "Average", 
                "level_en": "Average", 
                "level_ko": "보통", 
                "level_zh": "一般",
                "color": "yellow", 
                "description": "Shows net profit margin at industry average.",
                "description_en": "Shows net profit margin at industry average.",
                "description_ko": "업종 평균 수준의 순이익률을 보이고 있습니다.",
                "description_zh": "显示行业平均水平的净利润率。"
            }
        elif ratios["net_profit_margin"] > 0.10:
            ratios["net_profit_status"] = {
                "level": "Excellent", 
                "level_en": "Excellent", 
                "level_ko": "우수", 
                "level_zh": "优秀",
                "color": "green", 
                "description": "Has a high-profit business model.",
                "description_en": "Has a high-profit business model.",
                "description_ko": "고수익 사업모델을 갖추고 있습니다.",
                "description_zh": "具有高盈利的业务模式。"
            }
        else:
            ratios["net_profit_margin"] = 0
            ratios["net_profit_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Cannot calculate due to missing revenue data.",
                "description_en": "Cannot calculate due to missing revenue data.",
                "description_ko": "매출 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少收入数据，无法计算。"
            }
        
        # 2. Efficiency/Return Ratios
        
        # 2.1 Return on Assets (ROA, 총자산수익률)
        if yf_data and 'returnOnAssets' in yf_data and yf_data['returnOnAssets'] is not None:
            ratios["roa"] = yf_data['returnOnAssets']
        elif total_assets > 0:
            ratios["roa"] = net_income / total_assets
        else:
            ratios["roa"] = 0
            
        # Status evaluation based on the provided table
        if ratios["roa"] < 0.05:
            ratios["roa_status"] = {
                "level": "Inefficient",
                "level_en": "Inefficient",
                "level_ko": "비효율",
                "level_zh": "低效率",
                "color": "red",
                "description": "Asset utilization is inefficient.",
                "description_en": "Asset utilization is inefficient.",
                "description_ko": "자산 활용 비효율적입니다.",
                "description_zh": "资产利用效率低。"
            }
        elif ratios["roa"] < 0.10:
            ratios["roa_status"] = {
                "level": "Average",
                "level_en": "Average",
                "level_ko": "보통",
                "level_zh": "平均",
                "color": "yellow",
                "description": "Using assets efficiently.",
                "description_en": "Using assets efficiently.",
                "description_ko": "자산을 효율적으로 사용하고 있습니다.",
                "description_zh": "有效利用资产。"
            }
        elif ratios["roa"] < 0.20:
            ratios["roa_status"] = {
                "level": "Excellent",
                "level_en": "Excellent",
                "level_ko": "우수",
                "level_zh": "优秀",
                "color": "green",
                "description": "Shows outstanding asset profitability.",
                "description_en": "Shows outstanding asset profitability.",
                "description_ko": "뛰어난 자산 수익성을 보여줍니다.",
                "description_zh": "显示出色的资产盈利能力。"
            }
        else:
            ratios["roa_status"] = {
                "level": "Outstanding",
                "level_en": "Outstanding",
                "level_ko": "탁월",
                "level_zh": "卓越",
                "color": "blue",
                "description": "Generating excess returns on assets.",
                "description_en": "Generating excess returns on assets.",
                "description_ko": "자산 대비 초과 수익을 창출하고 있습니다.",
                "description_zh": "产生超额的资产回报。"
            }
        
        # 2.2 Return on Equity (ROE, 자기자본수익률)
        if yf_data and 'returnOnEquity' in yf_data and yf_data['returnOnEquity'] is not None:
            ratios["roe"] = yf_data['returnOnEquity']
        elif total_equity > 0:
            ratios["roe"] = net_income / total_equity
        else:
            ratios["roe"] = 0
        
        # Status evaluation based on the provided table
        if ratios["roe"] < 0.10:
            ratios["roe_status"] = {
                "level": "Weak",
                "level_en": "Weak",
                "level_ko": "취약",
                "level_zh": "薄弱",
                "color": "red",
                "description": "Capital operation is weak.",
                "description_en": "Capital operation is weak.",
                "description_ko": "자본 운용이 취약합니다.",
                "description_zh": "资本运作薄弱。"
            }
        elif ratios["roe"] < 0.15:
            ratios["roe_status"] = {
                "level": "Average",
                "level_en": "Average",
                "level_ko": "보통",
                "level_zh": "平均",
                "color": "yellow",
                "description": "Industry average level of return on equity.",
                "description_en": "Industry average level of return on equity.",
                "description_ko": "업계 평균 수준의 자기자본수익률입니다.",
                "description_zh": "行业平均水平的股本回报率。"
            }
        elif ratios["roe"] < 0.20:
            ratios["roe_status"] = {
                "level": "Excellent",
                "level_en": "Excellent",
                "level_ko": "우수",
                "level_zh": "优秀",
                "color": "green",
                "description": "Generating solid capital returns.",
                "description_en": "Generating solid capital returns.",
                "description_ko": "견고한 자본 수익을 창출하고 있습니다.",
                "description_zh": "正在创造坚实的资本回报。"
            }
        else:
            ratios["roe_status"] = {
                "level": "Outstanding",
                "level_en": "Outstanding",
                "level_ko": "탁월",
                "level_zh": "卓越",
                "color": "blue",
                "description": "Excellent leverage utilization.",
                "description_en": "Excellent leverage utilization.",
                "description_ko": "레버리지 활용이 우수합니다.",
                "description_zh": "杰出的杠杆利用。"
            }
        
        # 2.3 Return on Invested Capital (ROIC, 투자자본수익률) - 요청한 새 계산 방식 적용
        try:
            # 1. 투자자본(Invested Capital) 계산 - 수정된 공식 적용
            # 공식: Total Assets - Payables And Accrued Expenses - (Cash Cash Equivalents And Short Term Investments - max(0,Current Liabilities - Current Assets + Cash Cash Equivalents And Short Term Investments))
            
            # 1.1 당기(현재) 투자자본 계산 (가장 최근 값)
            
            # 당기 총자산(Total Assets)
            total_assets_current = safe_get_multi(balance_sheet, ["Total Assets"], 0)
            
            # 당기 미지급금 및 발생비용(Payables And Accrued Expenses)
            accounts_payable_current = safe_get_multi(balance_sheet, ["Accounts Payable", "Trade Payables"], 0)
            accrued_expense_current = safe_get_multi(balance_sheet, ["Accrued Liabilities", "Accrued Expenses"], 0)
            payables_and_accrued_expenses_current = accounts_payable_current + accrued_expense_current
            
            # 당기 현금, 현금성자산 및 단기투자(Cash Cash Equivalents And Short Term Investments)
            cash_and_equivalents_current = safe_get_multi(balance_sheet, ["Cash And Cash Equivalents", "Cash and Short Term Investments"], 0)
            marketable_securities_current = safe_get_multi(balance_sheet, ["Short Term Investments", "Marketable Securities"], 0)
            cash_and_short_term_investments_current = cash_and_equivalents_current + marketable_securities_current
            
            # 당기 유동부채(Current Liabilities)
            current_liabilities_current = safe_get_multi(balance_sheet, ["Current Liabilities", "Total Current Liabilities"], 0)
            
            # 당기 유동자산(Current Assets)
            current_assets_current = safe_get_multi(balance_sheet, ["Current Assets", "Total Current Assets"], 0)
            
            # 당기 투자자본 계산
            # max(0, Current Liabilities - Current Assets + Cash Cash Equivalents And Short Term Investments)
            operating_cash_needs_current = max(0, current_liabilities_current - current_assets_current + cash_and_short_term_investments_current)
            
            # 초과 현금 계산 (Cash Cash Equivalents And Short Term Investments - Operating Cash Needs)
            excess_cash_adjustment_current = cash_and_short_term_investments_current - operating_cash_needs_current
            
            # 투자자본 계산
            invested_capital_current = total_assets_current - payables_and_accrued_expenses_current - excess_cash_adjustment_current
            
            # 1.2 전기(이전) 투자자본 계산 (직전 연도 값)
            invested_capital_previous = invested_capital_current  # 기본값(전년도 데이터가 없는 경우)
            
            # 전년도 데이터를 사용할 수 있는 경우
            if (balance_sheet is not None and not balance_sheet.empty 
                and len(balance_sheet.columns) > 1):
                
                # 전년도 총자산
                total_assets_previous = safe_get_multi(balance_sheet, ["Total Assets"], 1)
                
                # 전년도 미지급금 및 발생비용
                accounts_payable_previous = safe_get_multi(balance_sheet, ["Accounts Payable", "Trade Payables"], 1)
                accrued_expense_previous = safe_get_multi(balance_sheet, ["Accrued Liabilities", "Accrued Expenses"], 1)
                payables_and_accrued_expenses_previous = accounts_payable_previous + accrued_expense_previous
                
                # 전년도 현금, 현금성자산 및 단기투자
                cash_and_equivalents_previous = safe_get_multi(balance_sheet, ["Cash And Cash Equivalents", "Cash and Short Term Investments"], 1)
                marketable_securities_previous = safe_get_multi(balance_sheet, ["Short Term Investments", "Marketable Securities"], 1)
                cash_and_short_term_investments_previous = cash_and_equivalents_previous + marketable_securities_previous
                
                # 전년도 유동부채
                current_liabilities_previous = safe_get_multi(balance_sheet, ["Current Liabilities", "Total Current Liabilities"], 1)
                
                # 전년도 유동자산
                current_assets_previous = safe_get_multi(balance_sheet, ["Current Assets", "Total Current Assets"], 1)
                
                # 전년도 투자자본 계산
                # max(0, Current Liabilities - Current Assets + Cash Cash Equivalents And Short Term Investments)
                operating_cash_needs_previous = max(0, current_liabilities_previous - current_assets_previous + cash_and_short_term_investments_previous)
                
                # 초과 현금 계산 (Cash Cash Equivalents And Short Term Investments - Operating Cash Needs)
                excess_cash_adjustment_previous = cash_and_short_term_investments_previous - operating_cash_needs_previous
                
                if total_assets_previous > 0:  # 전년도 총자산 데이터가 있는 경우에만
                    invested_capital_previous = total_assets_previous - payables_and_accrued_expenses_previous - excess_cash_adjustment_previous
            
            # 2. NOPAT(Net Operating Profit After Tax) 계산
            # 영업이익(EBIT) 사용
            operating_income = safe_get_multi(income_stmt, ["Operating Income", "EBIT"], 0)
            
            # 세율 계산
            effective_tax_rate = 0.21  # 기본 세율 25%
            
            # 세전이익과 법인세비용이 있으면 실효세율 계산
            pretax_income = safe_get_multi(income_stmt, ["Pretax Income", "Income Before Tax"], 0)
            if pretax_income > 0 and income_tax > 0:
                calculated_tax_rate = income_tax / pretax_income
                # 합리적인 세율 범위인지 확인 (10% ~ 40%)
                if 0.1 <= calculated_tax_rate <= 0.4:
                    effective_tax_rate = calculated_tax_rate
                    
            # 주의: 이 세율은 UI에서 WACC 계산으로 override될 수 있음
            # (main.py에서 WACC Parameters의 세율을 사용하여 ROIC 재계산)
            
            # 3. ROIC 계산 = (EBIT * (1 - Tax Rate)) / [(IC(직전연도) + IC(최근))/2]
            nopat = operating_income * (1 - effective_tax_rate)
            avg_invested_capital = (invested_capital_previous + invested_capital_current) / 2
            
            if avg_invested_capital > 0:
                # 수정된 수식: ROIC = (EBIT * (1-tax rate)) / [(IC(직전연도) + IC(최근))/2]
                ratios["roic"] = nopat / avg_invested_capital
                
                # 다국어 지원을 위한 상태 평가
                if ratios["roic"] < 0.05:
                    ratios["roic_status"] = {
                        "level": "저조", 
                        "level_en": "Poor", 
                        "level_ko": "저조", 
                        "level_zh": "较差",
                        "color": "red", 
                        "description": "투자자본 대비 수익률이 낮아 가치 창출이 미흡합니다.",
                        "description_en": "Low return on invested capital, insufficient value creation.",
                        "description_ko": "투자자본 대비 수익률이 낮아 가치 창출이 미흡합니다.",
                        "description_zh": "投资资本回报率低，价值创造不足。"
                    }
                elif ratios["roic"] < 0.08:
                    ratios["roic_status"] = {
                        "level": "주의", 
                        "level_en": "Caution", 
                        "level_ko": "주의", 
                        "level_zh": "注意",
                        "color": "orange", 
                        "description": "평균 이하의 투자자본 수익률로 자본비용 미만일 가능성이 있습니다.",
                        "description_en": "Below average return on invested capital, possibly below cost of capital.",
                        "description_ko": "평균 이하의 투자자본 수익률로 자본비용 미만일 가능성이 있습니다.",
                        "description_zh": "投资资本回报率低于平均水平，可能低于资本成本。"
                    }
                elif ratios["roic"] < 0.12:
                    ratios["roic_status"] = {
                        "level": "보통", 
                        "level_en": "Average", 
                        "level_ko": "보통", 
                        "level_zh": "一般",
                        "color": "yellow", 
                        "description": "평균적인 투자자본 수익률로 자본비용에 근접합니다.",
                        "description_en": "Average return on invested capital, close to cost of capital.",
                        "description_ko": "평균적인 투자자본 수익률로 자본비용에 근접합니다.",
                        "description_zh": "投资资本回报率处于平均水平，接近资本成本。"
                    }
                elif ratios["roic"] < 0.20:
                    ratios["roic_status"] = {
                        "level": "우수", 
                        "level_en": "Good", 
                        "level_ko": "우수", 
                        "level_zh": "优秀",
                        "color": "green", 
                        "description": "양호한 투자자본 수익률로 자본비용을 상회하며 가치를 창출합니다.",
                        "description_en": "Good return on invested capital, exceeding cost of capital and creating value.",
                        "description_ko": "양호한 투자자본 수익률로 자본비용을 상회하며 가치를 창출합니다.",
                        "description_zh": "投资资本回报率良好，超过资本成本并创造价值。"
                    }
                else:
                    ratios["roic_status"] = {
                        "level": "탁월", 
                        "level_en": "Excellent", 
                        "level_ko": "탁월", 
                        "level_zh": "卓越",
                        "color": "blue", 
                        "description": "투자자본 대비 초과 수익을 창출하고 있습니다.",
                        "description_en": "Generating exceptional returns on invested capital.",
                        "description_ko": "투자자본 대비 초과 수익을 창출하고 있습니다.",
                        "description_zh": "产生超额投资资本回报。"
                    }
            else:
                ratios["roic"] = 0
            ratios["roic_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "N/A", 
                "level_zh": "N/A",
                "color": "gray", 
                "description": "투자자본이 0 이하이거나 데이터가 없습니다.",
                "description_en": "Invested capital is 0 or below, or data is not available.",
                "description_ko": "투자자본이 0 이하이거나 데이터가 없습니다.",
                "description_zh": "投资资本为0或以下，或数据不可用。"
            }
        except Exception as e:
            print(f"Error calculating ROIC: {e}")
            ratios["roic"] = 0
            ratios["roic_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "N/A", 
                "level_zh": "N/A",
                "color": "gray", 
                "description": "ROIC 계산 중 오류가 발생했습니다.",
                "description_en": "Error occurred while calculating ROIC.",
                "description_ko": "ROIC 계산 중 오류가 발생했습니다.",
                "description_zh": "计算ROIC时出错。"
            }
        
        # 3. Leverage Ratios
        
        # 3.1 Debt to Equity (D/E, 부채비율)
        if ticker is not None and yf_data:
            try:
                if 'debtToEquity' in yf_data and yf_data['debtToEquity'] is not None:
                    ratios["debt_to_equity"] = yf_data['debtToEquity'] / 100.0 
                
                else:
                    # Fallback to old calculation if necessary fields are missing
                    if total_equity > 0:
                        ratios["debt_to_equity"] = total_liabilities / total_equity
            except Exception as e:
                if total_equity > 0:
                    ratios["debt_to_equity"] = total_liabilities / total_equity
        elif total_equity > 0:
            ratios["debt_to_equity"] = total_liabilities / total_equity
        else:
            ratios["debt_to_equity"] = 0
            ratios["leverage_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Unable to calculate due to missing equity data.",
                "description_en": "Unable to calculate due to missing equity data.",
                "description_ko": "자기자본 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少权益数据，无法计算。"
            }
            
        # Status evaluation for debt_to_equity regardless of data source
        if "debt_to_equity" in ratios and ratios["debt_to_equity"] > 0:
            if ratios["debt_to_equity"] < 1.0:
                ratios["leverage_status"] = {
                    "level": "Conservative", 
                    "level_en": "Conservative", 
                    "level_ko": "보수적", 
                    "level_zh": "保守",
                    "color": "blue", 
                    "description": "Low dependence on debt.",
                    "description_en": "Low dependence on debt.",
                    "description_ko": "부채 의존도가 낮습니다.",
                    "description_zh": "债务依赖度低。"
                }
            elif ratios["debt_to_equity"] < 2.0:
                ratios["leverage_status"] = {
                    "level": "Moderate", 
                    "level_en": "Moderate", 
                    "level_ko": "적정", 
                    "level_zh": "适中",
                    "color": "green", 
                    "description": "Industry-level debt ratio.",
                    "description_en": "Industry-level debt ratio.",
                    "description_ko": "업종 수준의 부채비율입니다.",
                    "description_zh": "符合行业水平的债务比率。"
                }
            else:
                ratios["leverage_status"] = {
                    "level": "Excessive", 
                    "level_en": "Excessive", 
                    "level_ko": "과도", 
                    "level_zh": "过度",
                    "color": "red", 
                    "description": "High interest burden and financial risk.",
                    "description_en": "High interest burden and financial risk.",
                    "description_ko": "이자부담과 재무위험이 높습니다.",
                    "description_zh": "利息负担和财务风险较高。"
                }
        
        # 3.2 Equity Ratio (자기자본비율) and Debt Ratio (총부채비율)
        # Directly calculate Equity Ratio  data as requested
        if ticker is not None and yf_data:
            try:
                # Calculate equity ratio as requested: (bookValue * sharesOutstanding) / (netIncomeToCommon / returnOnAssets)
                if all(key in yf_data and yf_data[key] is not None for key in ['bookValue', 'sharesOutstanding', 'netIncomeToCommon', 'returnOnAssets']) and yf_data['returnOnAssets'] > 0 and yf_data['netIncomeToCommon'] != 0:
                    # Total Equity = Book Value per Share * Number of Shares
                    book_value_equity = yf_data['bookValue'] * yf_data['sharesOutstanding']
                    # Total Assets = Net Income / ROA
                    calculated_total_assets = yf_data['netIncomeToCommon'] / yf_data['returnOnAssets']
                    
                    if calculated_total_assets > 0:
                        ratios["equity_ratio"] = book_value_equity / calculated_total_assets
                        ratios["debt_ratio"] = 1 - ratios["equity_ratio"]
                    else:
                        # Fallback to old calculation
                        if total_assets > 0:
                            ratios["debt_ratio"] = total_liabilities / total_assets
                            ratios["equity_ratio"] = total_equity / total_assets
                else:
                    # Fallback to old calculation if necessary fields are missing
                    if total_assets > 0:
                        ratios["debt_ratio"] = total_liabilities / total_assets
                        ratios["equity_ratio"] = total_equity / total_assets
            except Exception as e:
                if total_assets > 0:
                    ratios["debt_ratio"] = total_liabilities / total_assets
                    ratios["equity_ratio"] = total_equity / total_assets
        elif total_assets > 0:
            ratios["debt_ratio"] = total_liabilities / total_assets
            ratios["equity_ratio"] = total_equity / total_assets
        
        # Status evaluation for debt_ratio regardless of data source
        if "debt_ratio" in ratios and "equity_ratio" in ratios:
            if ratios["debt_ratio"] < 0.4:
                ratios["debt_ratio_status"] = {
                    "level": "Conservative", 
                    "level_en": "Conservative", 
                    "level_ko": "보수적", 
                    "level_zh": "保守",
                    "color": "blue", 
                    "description": "Low debt ratio.",
                    "description_en": "Low debt ratio.",
                    "description_ko": "부채비중이 낮습니다.",
                    "description_zh": "债务比例较低。"
                }
            elif ratios["debt_ratio"] < 0.6:
                ratios["debt_ratio_status"] = {
                    "level": "Moderate", 
                    "level_en": "Moderate", 
                    "level_ko": "적정", 
                    "level_zh": "适中",
                    "color": "green", 
                    "description": "Balanced financial structure.",
                    "description_en": "Balanced financial structure.",
                    "description_ko": "균형 잡힌 재무구조를 가지고 있습니다.",
                    "description_zh": "拥有均衡的财务结构。"
                }
            else:
                ratios["debt_ratio_status"] = {
                    "level": "Excessive", 
                    "level_en": "Excessive", 
                    "level_ko": "과도", 
                    "level_zh": "过度",
                    "color": "red", 
                    "description": "High debt relative to assets.",
                    "description_en": "High debt relative to assets.",
                    "description_ko": "자산 대비 부채가 높습니다.",
                    "description_zh": "相对于资产，债务较高。"
                }
        
        # 3.3 Interest Coverage Ratio (이자보상배율)
        interest_expense = safe_get_multi(income_stmt, ["Interest Expense", "Interest Expense, Net"], 0)
        if interest_expense != 0:
            ratios["interest_coverage"] = ebit / abs(interest_expense)
        else:
            ratios["interest_coverage"] = float('inf')  # 이자비용이 없는 경우
            ratios["interest_coverage_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Unable to calculate due to missing interest expense data.",
                "description_en": "Unable to calculate due to missing interest expense data.",
                "description_ko": "이자비용 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少利息费用数据，无法计算。"
            }
            
        # Status evaluation for interest_coverage regardless of data source
        if "interest_coverage" in ratios and ratios["interest_coverage"] != float('inf'):
            if ratios["interest_coverage"] < 1.5:
                ratios["interest_coverage_status"] = {
                    "level": "Danger", 
                    "level_en": "Danger", 
                    "level_ko": "위험", 
                    "level_zh": "危险",
                    "color": "red", 
                    "description": "High risk of payment difficulty.",
                    "description_en": "High risk of payment difficulty.",
                    "description_ko": "지급곤란 위험이 높습니다.",
                    "description_zh": "付款困难风险高。"
                }
            elif ratios["interest_coverage"] < 3.0:
                ratios["interest_coverage_status"] = {
                    "level": "Caution", 
                    "level_en": "Caution", 
                    "level_ko": "주의", 
                    "level_zh": "警戒",
                    "color": "yellow", 
                    "description": "High interest burden.",
                    "description_en": "High interest burden.",
                    "description_ko": "이자부담이 높습니다.",
                    "description_zh": "利息负担高。"
                }
            else:
                ratios["interest_coverage_status"] = {
                    "level": "Safe", 
                    "level_en": "Safe", 
                    "level_ko": "안전", 
                    "level_zh": "安全",
                    "color": "green", 
                    "description": "Sufficient capacity for interest payment.",
                    "description_en": "Sufficient capacity for interest payment.",
                    "description_ko": "이자지급 여력이 충분합니다.",
                    "description_zh": "利息支付能力充足。"
                }
        
        
        # 3.4 Equity Ratio (자기자본비율)
        if total_assets > 0 and total_equity > 0:
            # 자기자본비율 = 자기자본 / 총자산
            ratios["equity_ratio"] = total_equity / total_assets
            
            # Status evaluation based on standard financial analysis
            if ratios["equity_ratio"] < 0.2:
                ratios["equity_ratio_status"] = {
                    "level": "Risky", 
                    "level_en": "Risky", 
                    "level_ko": "위험", 
                    "level_zh": "危险",
                    "color": "red", 
                    "description": "Very low equity ratio, which makes financial stability vulnerable.",
                    "description_en": "Very low equity ratio, which makes financial stability vulnerable.",
                    "description_ko": "자기자본 비율이 매우 낮아 재무 안정성이 취약합니다.",
                    "description_zh": "权益比率非常低，使财务稳定性脆弱。"
                }
            elif ratios["equity_ratio"] < 0.4:
                ratios["equity_ratio_status"] = {
                    "level": "Caution", 
                    "level_en": "Caution", 
                    "level_ko": "주의", 
                    "level_zh": "警戒",
                    "color": "orange", 
                    "description": "Somewhat low equity ratio, requiring attention to long-term stability.",
                    "description_en": "Somewhat low equity ratio, requiring attention to long-term stability.",
                    "description_ko": "자기자본 비율이 다소 낮아 장기적 안정성에 주의가 필요합니다.",
                    "description_zh": "权益比率较低，需要注意长期稳定性。"
                }
            elif ratios["equity_ratio"] < 0.6:
                ratios["equity_ratio_status"] = {
                    "level": "Good", 
                    "level_en": "Good", 
                    "level_ko": "양호", 
                    "level_zh": "良好",
                    "color": "yellow", 
                    "description": "Adequate equity ratio with good financial stability.",
                    "description_en": "Adequate equity ratio with good financial stability.",
                    "description_ko": "적정 수준의 자기자본 비율로 재무 안정성이 양호합니다.",
                    "description_zh": "适当的权益比率，财务稳定性良好。"
                }
            else:
                ratios["equity_ratio_status"] = {
                    "level": "Excellent", 
                    "level_en": "Excellent", 
                    "level_ko": "우수", 
                    "level_zh": "优秀",
                    "color": "green", 
                    "description": "High equity ratio indicating very stable financial position.",
                    "description_en": "High equity ratio indicating very stable financial position.",
                    "description_ko": "높은 자기자본 비율로 재무적으로 매우 안정적입니다.",
                    "description_zh": "高权益比率表明财务状况非常稳定。"
                }
        else:
            ratios["equity_ratio"] = 0
            ratios["equity_ratio_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Unable to calculate due to missing asset or capital data.",
                "description_en": "Unable to calculate due to missing asset or capital data.",
                "description_ko": "자산 또는 자본 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少资产或资本数据，无法计算。"
            }
        
        # 4. Growth Rates
        
        # 4.1 Revenue Growth (매출 성장률)
        if prev_year_revenue > 0:
            ratios["revenue_growth"] = (total_revenue / prev_year_revenue - 1) * 100  # 백분율로 변환
            
            # Status evaluation based on the provided table
            if ratios["revenue_growth"] < 5:
                ratios["revenue_growth_status"] = {
                    "level": "Low Growth", 
                    "level_en": "Low Growth", 
                    "level_ko": "저성장", 
                    "level_zh": "低增长",
                    "color": "red", 
                    "description": "Concerns about market position or demand slowdown.",
                    "description_en": "Concerns about market position or demand slowdown.",
                    "description_ko": "시장지위 또는 수요 둔화가 우려됩니다.",
                    "description_zh": "对市场地位或需求放缓的担忧。"
                }
            elif ratios["revenue_growth"] < 15:
                ratios["revenue_growth_status"] = {
                    "level": "Moderate", 
                    "level_en": "Moderate", 
                    "level_ko": "보통", 
                    "level_zh": "中等",
                    "color": "yellow", 
                    "description": "Maintaining healthy growth trend.",
                    "description_en": "Maintaining healthy growth trend.",
                    "description_ko": "건전한 성장세를 유지하고 있습니다.",
                    "description_zh": "保持健康的增长趋势。"
                }
            elif ratios["revenue_growth"] < 30:
                ratios["revenue_growth_status"] = {
                    "level": "High Growth", 
                    "level_en": "High Growth", 
                    "level_ko": "고성장", 
                    "level_zh": "高增长",
                    "color": "green", 
                    "description": "Indicates market expansion or favorable demand conditions.",
                    "description_en": "Indicates market expansion or favorable demand conditions.",
                    "description_ko": "시장확장 또는 수요호조를 나타냅니다.",
                    "description_zh": "表明市场扩张或需求条件良好。"
                }
            else:
                ratios["revenue_growth_status"] = {
                    "level": "Exceptional Growth", 
                    "level_en": "Exceptional Growth", 
                    "level_ko": "초고성장", 
                    "level_zh": "异常增长",
                    "color": "blue", 
                    "description": "Shows innovative products or niche market leadership.",
                    "description_en": "Shows innovative products or niche market leadership.",
                    "description_ko": "혁신적인 제품이나 니치 시장 리더십을 보여줍니다.",
                    "description_zh": "展示创新产品或利基市场领导地位。"
                }
        else:
            ratios["revenue_growth"] = 0
            ratios["revenue_growth_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Unable to calculate due to missing previous year revenue data.",
                "description_en": "Unable to calculate due to missing previous year revenue data.",
                "description_ko": "전년 매출 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少上年度收入数据，无法计算。"
            }
        
        # 4.2 Net Income Growth (순이익 성장률)
        if prev_net_income > 0:
            ratios["net_income_growth"] = (net_income / prev_net_income - 1) * 100  # 백분율로 변환
            
            # Status evaluation
            if ratios["net_income_growth"] < 0:
                ratios["net_income_growth_status"] = {
                    "level": "Negative", 
                    "level_en": "Negative", 
                    "level_ko": "마이너스", 
                    "level_zh": "负增长",
                    "color": "red", 
                    "description": "Net income is decreasing, weakening profitability.",
                    "description_en": "Net income is decreasing, weakening profitability.",
                    "description_ko": "순이익이 감소하여 수익성이 약화되고 있습니다.",
                    "description_zh": "净利润正在下降，盈利能力减弱。"
                }
            elif ratios["net_income_growth"] < 5:
                ratios["net_income_growth_status"] = {
                    "level": "Slow", 
                    "level_en": "Slow", 
                    "level_ko": "저성장", 
                    "level_zh": "缓慢",
                    "color": "orange", 
                    "description": "Slow net income growth, limited profitability improvement.",
                    "description_en": "Slow net income growth, limited profitability improvement.",
                    "description_ko": "순이익 성장이 느려 수익성 개선이 제한적입니다.",
                    "description_zh": "净利润增长缓慢，盈利能力改善有限。"
                }
            elif ratios["net_income_growth"] < 15:
                ratios["net_income_growth_status"] = {
                    "level": "Average", 
                    "level_en": "Average", 
                    "level_ko": "중간", 
                    "level_zh": "平均",
                    "color": "yellow", 
                    "description": "Average net income growth showing reasonable operational efficiency.",
                    "description_en": "Average net income growth showing reasonable operational efficiency.",
                    "description_ko": "적정 수준의 순이익 성장으로 합리적인 운영 효율성을 보여줍니다.",
                    "description_zh": "平均净利润增长，显示合理的运营效率。"
                }
            elif ratios["net_income_growth"] < 25:
                ratios["net_income_growth_status"] = {
                    "level": "Strong", 
                    "level_en": "Strong", 
                    "level_ko": "강함", 
                    "level_zh": "强劲",
                    "color": "green", 
                    "description": "Strong net income growth showing improved operational efficiency or economies of scale.",
                    "description_en": "Strong net income growth showing improved operational efficiency or economies of scale.",
                    "description_ko": "강한 순이익 성장으로 운영 효율성 향상이나 규모의 경제를 보여줍니다.",
                    "description_zh": "强劲的净利润增长，显示运营效率提高或规模经济。"
                }
            else:
                ratios["net_income_growth_status"] = {
                    "level": "Exceptional", 
                    "level_en": "Exceptional", 
                    "level_ko": "탄월함", 
                    "level_zh": "卓越",
                    "color": "blue", 
                    "description": "Exceptional net income growth far exceeding revenue growth, showing operational improvements.",
                    "description_en": "Exceptional net income growth far exceeding revenue growth, showing operational improvements.",
                    "description_ko": "매우 뛰어난 순이익 성장으로 매출 성장을 크게 상회하며 운영 개선을 보여줍니다.",
                    "description_zh": "卓越的净利润增长远超收入增长，表明运营改善。"
                }
        else:
            ratios["net_income_growth"] = 0
            ratios["net_income_growth_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Unable to calculate due to missing previous year net income data.",
                "description_en": "Unable to calculate due to missing previous year net income data.",
                "description_ko": "전년 순이익 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少上年度净利润数据，无法计算。"
            }
        
        # 4.3 Operating Income Growth (영업이익 성장률)
        prev_operating_income = safe_get_multi(income_stmt, ["Operating Income", "EBIT"], 1) if income_stmt is not None and len(income_stmt.columns) > 1 else 0
        
        if prev_operating_income > 0 and operating_income is not None:
            ratios["operating_income_growth"] = (operating_income / prev_operating_income - 1) * 100  # 백분율로 변환
            
            # Status evaluation
            if ratios["operating_income_growth"] < 0:
                ratios["operating_income_growth_status"] = {
                    "level": "Negative", 
                    "level_en": "Negative", 
                    "level_ko": "마이너스", 
                    "level_zh": "负增长",
                    "color": "red", 
                    "description": "Operating income is decreasing, indicating operational challenges.",
                    "description_en": "Operating income is decreasing, indicating operational challenges.",
                    "description_ko": "영업이익이 감소하여 운영상의 어려움이 예상됩니다.",
                    "description_zh": "营业利润正在下降，表明运营面临挑战。"
                }
            elif ratios["operating_income_growth"] < 5:
                ratios["operating_income_growth_status"] = {
                    "level": "Slow", 
                    "level_en": "Slow", 
                    "level_ko": "저성장", 
                    "level_zh": "缓慢",
                    "color": "orange", 
                    "description": "Slow operating income growth, limited operational improvement.",
                    "description_en": "Slow operating income growth, limited operational improvement.",
                    "description_ko": "영업이익 성장이 더딘 편으로, 운영 개선이 제한적입니다.",
                    "description_zh": "营业利润增长缓慢，运营改善有限。"
                }
            elif ratios["operating_income_growth"] < 15:
                ratios["operating_income_growth_status"] = {
                    "level": "Average", 
                    "level_en": "Average", 
                    "level_ko": "중간", 
                    "level_zh": "平均",
                    "color": "yellow", 
                    "description": "Average operating income growth showing reasonable operational efficiency.",
                    "description_en": "Average operating income growth showing reasonable operational efficiency.",
                    "description_ko": "적정 수준의 영업이익 성장으로 합리적인 운영 효율성을 보여줍니다.",
                    "description_zh": "平均营业利润增长，显示合理的运营效率。"
                }
            elif ratios["operating_income_growth"] < 25:
                ratios["operating_income_growth_status"] = {
                    "level": "Strong", 
                    "level_en": "Strong", 
                    "level_ko": "강함", 
                    "level_zh": "强劲",
                    "color": "green", 
                    "description": "Strong operating income growth showing improved operational efficiency.",
                    "description_en": "Strong operating income growth showing improved operational efficiency.",
                    "description_ko": "강한 영업이익 성장으로 운영 효율성 향상을 보여줍니다.",
                    "description_zh": "强劲的营业利润增长，显示运营效率提高。"
                }
            else:
                ratios["operating_income_growth_status"] = {
                    "level": "Exceptional", 
                    "level_en": "Exceptional", 
                    "level_ko": "탁월함", 
                    "level_zh": "卓越",
                    "color": "blue", 
                    "description": "Exceptional operating income growth, indicating strong operational performance.",
                    "description_en": "Exceptional operating income growth, indicating strong operational performance.",
                    "description_ko": "매우 뛰어난 영업이익 성장으로 강력한 운영 성과를 보여줍니다.",
                    "description_zh": "卓越的营业利润增长，表明运营业绩强劲。"
                }
        else:
            ratios["operating_income_growth"] = 0
            ratios["operating_income_growth_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Unable to calculate due to missing previous year operating income data.",
                "description_en": "Unable to calculate due to missing previous year operating income data.",
                "description_ko": "전년 영업이익 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少上年度营业利润数据，无法计算。"
            }
        
        # 5. Liquidity Ratios
        
        # 5.1 Current Ratio (유동비율)
        if yf_data and 'currentRatio' in yf_data and yf_data['currentRatio'] is not None:
            ratios["current_ratio"] = yf_data['currentRatio']
        elif current_liabilities > 0:
            ratios["current_ratio"] = current_assets / current_liabilities
        else:
            ratios["current_ratio"] = float('inf')  # 유동부채가 없는 경우
        
        # Status evaluation based on the provided table
        if ratios["current_ratio"] < 1.0:
            ratios["current_ratio_status"] = {
                "level": "Risky", 
                "level_en": "Risky", 
                "level_ko": "위험", 
                "level_zh": "危险",
                "color": "red", 
                "description": "High risk of short-term debt default.",
                "description_en": "High risk of short-term debt default.",
                "description_ko": "단기채무 불이행 위험이 높습니다.",
                "description_zh": "短期债务违约风险高。"
            }
        elif ratios["current_ratio"] < 1.5:
            ratios["current_ratio_status"] = {
                "level": "Weak", 
                "level_en": "Weak", 
                "level_ko": "취약", 
                "level_zh": "薄弱",
                "color": "orange", 
                "description": "Liquidity is weak with limited debt repayment capacity.",
                "description_en": "Liquidity is weak with limited debt repayment capacity.",
                "description_ko": "유동성이 취약하며 채무상환 여력이 약합니다.",
                "description_zh": "流动性薄弱，债务偿还能力有限。"
            }
        elif ratios["current_ratio"] < 2.0:
            ratios["current_ratio_status"] = {
                "level": "Good", 
                "level_en": "Good", 
                "level_ko": "양호", 
                "level_zh": "良好",
                "color": "green", 
                "description": "Has stable short-term payment capability.",
                "description_en": "Has stable short-term payment capability.",
                "description_ko": "안정적인 단기지급능력을 갖추고 있습니다.",
                "description_zh": "具有稳定的短期付款能力。"
            }
        else:
            ratios["current_ratio_status"] = {
                "level": "Excessive", 
                "level_en": "Excessive", 
                "level_ko": "과도", 
                "level_zh": "过度",
                "color": "yellow", 
                "description": "Excessive liquidity may indicate inefficient asset utilization.",
                "description_en": "Excessive liquidity may indicate inefficient asset utilization.",
                "description_ko": "과도한 유동성으로 자산 비효율 운용이 우려됩니다.",
                "description_zh": "过度流动性可能表明资产利用不效率。"
            }
        
        # 5.2 Quick Ratio (당좌비율)
        if yf_data and 'quickRatio' in yf_data and yf_data['quickRatio'] is not None:
            ratios["quick_ratio"] = yf_data['quickRatio']
        elif current_liabilities > 0:
            quick_assets = current_assets - inventories  # 재고자산을 제외한 유동자산
            ratios["quick_ratio"] = quick_assets / current_liabilities
        else:
            ratios["quick_ratio"] = float('inf')  # 유동부채가 없는 경우
        
        # Status evaluation based on the provided table
        if ratios["quick_ratio"] < 1.0:
            ratios["quick_ratio_status"] = {
                "level": "Warning", 
                "level_en": "Warning", 
                "level_ko": "경고", 
                "level_zh": "警告",
                "color": "red", 
                "description": "Payment ability is insufficient even excluding inventory.",
                "description_en": "Payment ability is insufficient even excluding inventory.",
                "description_ko": "재고 제외 시에도 지급능력이 부족합니다.",
                "description_zh": "即使不包括库存，付款能力也不足。"
            }
        else:
            ratios["quick_ratio_status"] = {
                "level": "Good", 
                "level_en": "Good", 
                "level_ko": "양호", 
                "level_zh": "良好",
                "color": "green", 
                "description": "Has secured conservative short-term payment capability.",
                "description_en": "Has secured conservative short-term payment capability.",
                "description_ko": "보수적 단기지급능력을 확보하고 있습니다.",
                "description_zh": "已确保保守的短期付款能力。"
            }
        
        # 5.3 Cash Ratio (현금비율)
        if current_liabilities > 0:
            ratios["cash_ratio"] = cash_and_equivalents / current_liabilities
            
            # Status evaluation based on the provided table
            if ratios["cash_ratio"] < 0.5:
                ratios["cash_ratio_status"] = {
                    "level": "Risky", 
                    "level_en": "Risky", 
                    "level_ko": "위험", 
                    "level_zh": "危险",
                    "color": "red", 
                    "description": "At risk of cash shortage.",
                    "description_en": "At risk of cash shortage.",
                    "description_ko": "현금부족 위험군입니다.",
                    "description_zh": "存在现金短缺风险。"
                }
            elif ratios["cash_ratio"] < 1.0:
                ratios["cash_ratio_status"] = {
                    "level": "Average", 
                    "level_en": "Average", 
                    "level_ko": "보통", 
                    "level_zh": "一般",
                    "color": "yellow", 
                    "description": "Has secured minimum cash coverage.",
                    "description_en": "Has secured minimum cash coverage.",
                    "description_ko": "최소 현금 커버리지를 확보하고 있습니다.",
                    "description_zh": "已确保最低现金覆盖率。"
                }
            else:
                ratios["cash_ratio_status"] = {
                    "level": "Sufficient", 
                    "level_en": "Sufficient", 
                    "level_ko": "충분", 
                    "level_zh": "充足",
                    "color": "green", 
                    "description": "Has sufficient cash even in worst-case scenarios.",
                    "description_en": "Has sufficient cash even in worst-case scenarios.",
                    "description_ko": "최악의 시나리오에도 현금을 충분히 보유하고 있습니다.",
                    "description_zh": "即使在最坏情况下也有足够的现金。"
                }
        else:
            ratios["cash_ratio"] = float('inf')  # 유동부채가 없는 경우
            ratios["cash_ratio_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": "Cannot calculate due to missing current liabilities data.",
                "description_en": "Cannot calculate due to missing current liabilities data.",
                "description_ko": "유동부채 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少流动负债数据，无法计算。"
            }
        
        # 6. Efficiency Ratios
        
        # 6.1 Asset Turnover Ratio (총자산회전율)
        if total_assets > 0:
            ratios["asset_turnover"] = total_revenue / total_assets
            
            # Status evaluation based on the provided table
            if ratios["asset_turnover"] < 0.5:
                ratios["asset_turnover_status"] = {
                    "level": "Inefficient",
                    "level_en": "Inefficient",
                    "level_ko": "비효율",
                    "level_zh": "低效率",
                    "color": "red",
                    "description": "Asset utilization is inefficient.",
                    "description_en": "Asset utilization is inefficient.",
                    "description_ko": "자산 운용이 비효율적입니다.",
                    "description_zh": "资产利用效率低。"
                }
            elif ratios["asset_turnover"] < 1.0:
                ratios["asset_turnover_status"] = {
                    "level": "Average",
                    "level_en": "Average",
                    "level_ko": "보통",
                    "level_zh": "平均",
                    "color": "yellow",
                    "description": "Shows average asset utilization efficiency for the industry.",
                    "description_en": "Shows average asset utilization efficiency for the industry.",
                    "description_ko": "업종 평균 수준의 자산 운용 효율을 보여줍니다.",
                    "description_zh": "显示行业平均水平的资产利用效率。"
                }
            else:
                ratios["asset_turnover_status"] = {
                    "level": "Excellent",
                    "level_en": "Excellent",
                    "level_ko": "우수",
                    "level_zh": "优秀",
                    "color": "green",
                    "description": "Maximizing asset utilization.",
                    "description_en": "Maximizing asset utilization.",
                    "description_ko": "자산 이용을 극대화하고 있습니다.",
                    "description_zh": "正在最大化资产利用。"
                }
        else:
            ratios["asset_turnover"] = 0
            ratios["asset_turnover_status"] = {
                "level": "N/A",
                "level_en": "N/A",
                "level_ko": "데이터 없음",
                "level_zh": "无数据",
                "color": "gray",
                "description": "Cannot calculate due to missing asset data.",
                "description_en": "Cannot calculate due to missing asset data.",
                "description_ko": "자산 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少资产数据，无法计算。"
            }
        
        # 7. Cash Flow Ratios
        
        # 7.1 Operating Cash Flow to Revenue Ratio
        if total_revenue > 0:
            ratios["ocf_to_revenue"] = operating_cash_flow / total_revenue
            
            # Status evaluation
            if ratios["ocf_to_revenue"] < 0.05:
                ratios["ocf_to_revenue_status"] = {"level": "Poor", "color": "red", 
                    "description": "매출이 현금흐름으로 전환되는 비율이 낮습니다."}
            elif ratios["ocf_to_revenue"] < 0.1:
                ratios["ocf_to_revenue_status"] = {"level": "Below Average", "color": "orange", 
                    "description": "매출이 현금흐름으로 전환되는 비율이 평균 이하입니다."}
            elif ratios["ocf_to_revenue"] < 0.15:
                ratios["ocf_to_revenue_status"] = {"level": "Average", "color": "yellow", 
                    "description": "매출이 현금흐름으로 전환되는 비율이 적정 수준입니다."}
            elif ratios["ocf_to_revenue"] < 0.25:
                ratios["ocf_to_revenue_status"] = {"level": "Good", "color": "green", 
                    "description": "매출이 현금흐름으로 전환되는 비율이 우수합니다."}
            else:
                ratios["ocf_to_revenue_status"] = {"level": "Excellent", "color": "blue", 
                    "description": "매출이 현금흐름으로 전환되는 비율이 매우 우수합니다."}
        else:
            ratios["ocf_to_revenue"] = 0
            ratios["ocf_to_revenue_status"] = {"level": "N/A", "color": "gray", 
                "description": "매출 데이터가 없어 계산할 수 없습니다."}
        
        # 7.2 Free Cash Flow to Operating Cash Flow Ratio
        if operating_cash_flow > 0:
            ratios["fcf_to_ocf"] = free_cash_flow / operating_cash_flow
            
            # Status evaluation
            if ratios["fcf_to_ocf"] < 0.3:
                ratios["fcf_to_ocf_status"] = {"level": "Low", "color": "red", 
                    "description": "영업 현금흐름 중 실제 가용한 현금 비율이 낮습니다. 자본 지출이 높을 수 있습니다."}
            elif ratios["fcf_to_ocf"] < 0.6:
                ratios["fcf_to_ocf_status"] = {"level": "Moderate", "color": "yellow", 
                    "description": "영업 현금흐름 중 실제 가용한 현금 비율이 적정 수준입니다."}
            else:
                ratios["fcf_to_ocf_status"] = {"level": "High", "color": "green", 
                    "description": "영업 현금흐름 중 실제 가용한 현금 비율이 높아 자본 배분의 유연성이 있습니다."}
        else:
            ratios["fcf_to_ocf"] = 0
            ratios["fcf_to_ocf_status"] = {"level": "N/A", "color": "gray", 
                "description": "영업 현금흐름 데이터가 없어 계산할 수 없습니다."}
        
        # 8. Valuation Ratios
        
        # 8.1 P/E Ratio (Price to Earnings)
        if yf_data:
            # Try to get trailing PE ratio 
            trailing_pe = yf_data.get('trailingPE')
            forward_pe = yf_data.get('forwardPE')
            trailing_eps = yf_data.get('trailingEPS')
            forward_eps = yf_data.get('forwardEPS')
            
            # Handle trailing P/E
            if trailing_pe is not None and not math.isnan(trailing_pe):
                ratios["pe_ratio"] = trailing_pe
            elif trailing_eps is not None and trailing_eps > 0 and not math.isnan(trailing_eps):
                ratios["pe_ratio"] = current_price / trailing_eps
            elif net_income > 0 and shares_outstanding > 0:
                eps = net_income / shares_outstanding
                ratios["pe_ratio"] = current_price / eps if eps > 0 else float('inf')
                ratios["eps"] = eps
                ratios["forward_pe_ratio"] = ratios["pe_ratio"]
                ratios["forward_eps"] = eps
            else:
                ratios["pe_ratio"] = float('inf')
                
            # Handle forward P/E 
            if forward_pe is not None and not math.isnan(forward_pe):
                ratios["forward_pe_ratio"] = forward_pe
            elif forward_eps is not None and forward_eps > 0 and not math.isnan(forward_eps):
                ratios["forward_pe_ratio"] = current_price / forward_eps
            else:
                # If forward P/E is not available, use trailing as fallback
                ratios["forward_pe_ratio"] = ratios.get("pe_ratio", float('inf'))
                
            # Store EPS values
            if trailing_eps is not None and not math.isnan(trailing_eps):
                ratios["eps"] = trailing_eps
            elif net_income > 0 and shares_outstanding > 0:
                ratios["eps"] = net_income / shares_outstanding
            else:
                ratios["eps"] = 0
                
            if forward_eps is not None and not math.isnan(forward_eps):
                ratios["forward_eps"] = forward_eps
            else:
                ratios["forward_eps"] = ratios.get("eps", 0)
                
            # Get ROE and ROA 
            roe = yf_data.get('returnOnEquity')
            if roe is not None and not math.isnan(roe):
                ratios["roe"] = roe
                
            roa = yf_data.get('returnOnAssets')
            if roa is not None and not math.isnan(roa):
                ratios["roa"] = roa
                
            # Get quick/current ratios 
            quick_ratio = yf_data.get('quickRatio')
            if quick_ratio is not None and not math.isnan(quick_ratio):
                ratios["quick_ratio"] = quick_ratio
                
            current_ratio = yf_data.get('currentRatio')
            if current_ratio is not None and not math.isnan(current_ratio):
                ratios["current_ratio"] = current_ratio
        else:
            if net_income > 0 and shares_outstanding > 0:
                eps = net_income / shares_outstanding
                ratios["pe_ratio"] = current_price / eps if eps > 0 else float('inf')
                ratios["eps"] = eps
                ratios["forward_pe_ratio"] = ratios["pe_ratio"]
                ratios["forward_eps"] = eps
            else:
                ratios["pe_ratio"] = float('inf')
                ratios["forward_pe_ratio"] = float('inf')
                ratios["eps"] = 0
                ratios["forward_eps"] = 0
        
        # Ensure TTM P/E and Forward P/E are explicitly handled
        if yf_data:
            ratios['ttm_pe'] = yf_data.get('trailingPE', 0)
            ratios['forward_pe'] = yf_data.get('forwardPE', 0)
        else:
            ratios['ttm_pe'] = 0
            ratios['forward_pe'] = 0
        
        # Store forward PE separately if available
        if yf_data and 'forwardPE' in yf_data and yf_data['forwardPE'] is not None:
            ratios["forward_pe_ratio"] = yf_data['forwardPE']
            
        # Get EPS data  if available
        if yf_data:
            # Try to get trailing and forward EPS 
            trailing_eps = yf_data.get('trailingEPS')
            forward_eps = yf_data.get('forwardEPS')
            
            if trailing_eps is not None:
                ratios["eps"] = trailing_eps
            
            if forward_eps is not None:
                ratios["forward_eps"] = forward_eps
                
            # Calculate EPS growth if we have both values
            if trailing_eps is not None and forward_eps is not None and trailing_eps > 0:
                ratios["yf_eps_growth"] = (forward_eps / trailing_eps - 1) * 100
                
                # Add status for yf_eps_growth
                if ratios["yf_eps_growth"] < 5:
                    ratios["yf_eps_growth_status"] = {
                        "level": "Low Growth", 
                        "level_en": "Low Growth", 
                        "level_ko": "저성장", 
                        "level_zh": "低增长",
                        "color": "red", 
                        "description": "Stagnant earnings growth.",
                        "description_en": "Stagnant earnings growth.",
                        "description_ko": "이익 정체 상태입니다.",
                        "description_zh": "盈利增长停满。"
                    }
                elif ratios["yf_eps_growth"] < 20:
                    ratios["yf_eps_growth_status"] = {
                        "level": "Moderate", 
                        "level_en": "Moderate", 
                        "level_ko": "보통", 
                        "level_zh": "中等",
                        "color": "yellow", 
                        "description": "Shows stable earnings growth.",
                        "description_en": "Shows stable earnings growth.",
                        "description_ko": "안정적인 이익 성장을 보여줍니다.",
                        "description_zh": "显示稳定的盈利增长。"
                    }
                else:
                    ratios["yf_eps_growth_status"] = {
                        "level": "High Growth", 
                        "level_en": "High Growth", 
                        "level_ko": "고성장", 
                        "level_zh": "高增长",
                        "color": "green", 
                        "description": "Profitability is expanding significantly.",
                        "description_en": "Profitability is expanding significantly.",
                        "description_ko": "수익성이 크게 확대되고 있습니다.",
                        "description_zh": "盈利能力正在显著扩大。"
                    }
        
        # Status evaluation based on the provided table
        if ratios["pe_ratio"] < 14:
            ratios["pe_ratio_status"] = {"level": "저평가", "color": "blue", 
                "description": "저평가 가능성이 있습니다."}
        elif ratios["pe_ratio"] < 25:
            ratios["pe_ratio_status"] = {"level": "적정", "color": "green", 
                "description": "업종 평균에 근접한 적정 밸류에이션입니다."}
        else:
            ratios["pe_ratio_status"] = {"level": "고평가", "color": "red", 
                "description": "고평가 우려가 있습니다."}
        
        # 8.2 P/B Ratio (Price to Book)
        # Get P/B ratio directly  data
        if ticker is not None and yf_data and 'priceToBook' in yf_data and yf_data['priceToBook'] is not None:
            ratios["pb_ratio"] = yf_data['priceToBook']
            
            # Status evaluation based on the provided table
            if ratios["pb_ratio"] < 1.0:
                ratios["pb_ratio_status"] = {"level": "저평가", "color": "blue", 
                    "description": "순자산 대비 저평가되어 있습니다."}
            elif ratios["pb_ratio"] < 3.0:
                ratios["pb_ratio_status"] = {"level": "적정", "color": "green", 
                    "description": "적정 범위 내의 밸류에이션입니다."}
            else:
                ratios["pb_ratio_status"] = {"level": "고평가", "color": "red", 
                    "description": "고평가이거나 고수익 구조를 가지고 있습니다."}
        else:
            ratios["pb_ratio"] = float('inf')
            ratios["pb_ratio_status"] = {"level": "N/A", "color": "gray", 
                "description": "P/B 비율 데이터를 가져올 수 없습니다."}
        
        # 8.3 P/S Ratio (Price to Sales)
        if total_revenue > 0 and shares_outstanding > 0:
            sales_per_share = total_revenue / shares_outstanding
            ratios["ps_ratio"] = current_price / sales_per_share if sales_per_share > 0 else float('inf')
            
            # Status evaluation based on the provided table
            if ratios["ps_ratio"] < 1.0:
                ratios["ps_ratio_status"] = {"level": "저평가", "color": "blue", 
                    "description": "저평가 가능성이 있습니다."}
            elif ratios["ps_ratio"] < 3.0:
                ratios["ps_ratio_status"] = {"level": "적정", "color": "green", 
                    "description": "적정 범위 내의 밸류에이션입니다."}
            else:
                ratios["ps_ratio_status"] = {"level": "고평가", "color": "red", 
                    "description": "고평가 우려가 있습니다."}
        else:
            ratios["ps_ratio"] = float('inf')
            ratios["ps_ratio_status"] = {"level": "N/A", "color": "gray", 
                "description": "매출 또는 발행주식수 데이터가 없어 계산할 수 없습니다."}
        
        # 8.4 EV/EBITDA Ratio
        if ebitda > 0:
            enterprise_value = market_cap + total_liabilities - cash_and_equivalents
            ratios["ev_to_ebitda"] = enterprise_value / ebitda
            
            # Status evaluation based on the provided table
            if ratios["ev_to_ebitda"] < 8:
                ratios["ev_to_ebitda_status"] = {"level": "저평가", "color": "blue", 
                    "description": "저평가 가능성이 있습니다."}
            elif ratios["ev_to_ebitda"] < 15:
                ratios["ev_to_ebitda_status"] = {"level": "적정", "color": "green", 
                    "description": "적정 범위 내의 기업가치입니다."}
            else:
                ratios["ev_to_ebitda_status"] = {"level": "과대평가", "color": "red", 
                    "description": "과대평가 우려가 있습니다."}
        else:
            ratios["ev_to_ebitda"] = float('inf')
            ratios["ev_to_ebitda_status"] = {"level": "N/A", "color": "gray", 
                "description": "EBITDA 데이터가 없어 계산할 수 없습니다."}
        
        # 9. Operating Efficiency Ratios
        
        # 9.1 Inventory Turnover (재고자산회전율)
        if inventories > 0:
            cost_of_goods_sold = total_revenue - gross_profit if gross_profit > 0 else 0
            ratios["inventory_turnover"] = cost_of_goods_sold / inventories
            
            # Status evaluation based on the provided table
            if ratios["inventory_turnover"] < 4:
                ratios["inventory_turnover_status"] = {
                    "level": "Risky",
                    "level_en": "Risky",
                    "level_ko": "위험",
                    "level_zh": "危险",
                    "color": "red",
                    "description": "Risk of excess inventory or poor sales.",
                    "description_en": "Risk of excess inventory or poor sales.",
                    "description_ko": "과잉재고 또는 판매부진 위험이 있습니다.",
                    "description_zh": "有过量库存或销售不挪的风险。"
                }
            elif ratios["inventory_turnover"] < 8:
                ratios["inventory_turnover_status"] = {
                    "level": "Average",
                    "level_en": "Average",
                    "level_ko": "보통",
                    "level_zh": "平均",
                    "color": "yellow",
                    "description": "Inventory and sales are balanced.",
                    "description_en": "Inventory and sales are balanced.",
                    "description_ko": "재고와 판매가 균형을 이루고 있습니다.",
                    "description_zh": "库存和销售保持平衡。"
                }
            else:
                ratios["inventory_turnover_status"] = {
                    "level": "Excellent",
                    "level_en": "Excellent",
                    "level_ko": "우수",
                    "level_zh": "优秀",
                    "color": "green",
                    "description": "Good inventory management and sales.",
                    "description_en": "Good inventory management and sales.",
                    "description_ko": "재고관리와 판매가 양호합니다.",
                    "description_zh": "库存管理和销售良好。"
                }
        else:
            ratios["inventory_turnover"] = float('inf')
            ratios["inventory_turnover_status"] = {
                "level": "N/A",
                "level_en": "N/A",
                "level_ko": "데이터 없음",
                "level_zh": "无数据",
                "color": "gray",
                "description": "Cannot calculate due to missing inventory data.",
                "description_en": "Cannot calculate due to missing inventory data.",
                "description_ko": "재고자산 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少库存数据，无法计算。"
            }
        
        # 9.2 Receivables Turnover (매출채권회전율)
        if accounts_receivable > 0:
            ratios["receivables_turnover"] = total_revenue / accounts_receivable
            
            # Status evaluation based on the provided table
            if ratios["receivables_turnover"] < 5:
                ratios["receivables_turnover_status"] = {
                    "level": "Risky",
                    "level_en": "Risky",
                    "level_ko": "위험",
                    "level_zh": "危险",
                    "color": "red",
                    "description": "High risk of collection delays.",
                    "description_en": "High risk of collection delays.",
                    "description_ko": "회수지연 위험이 높습니다.",
                    "description_zh": "收款延迟风险高。"
                }
            elif ratios["receivables_turnover"] < 10:
                ratios["receivables_turnover_status"] = {
                    "level": "Average",
                    "level_en": "Average",
                    "level_ko": "보통",
                    "level_zh": "平均",
                    "color": "yellow",
                    "description": "Shows average collection speed.",
                    "description_en": "Shows average collection speed.",
                    "description_ko": "평균적인 회수속도를 보여줍니다.",
                    "description_zh": "显示平均收款速度。"
                }
            else:
                ratios["receivables_turnover_status"] = {
                    "level": "Excellent",
                    "level_en": "Excellent",
                    "level_ko": "우수",
                    "level_zh": "优秀",
                    "color": "green",
                    "description": "Rapid collection of receivables is occurring.",
                    "description_en": "Rapid collection of receivables is occurring.",
                    "description_ko": "신속한 채권회수가 이루어지고 있습니다.",
                    "description_zh": "正在进行快速的应收账款收回。"
                }
        else:
            ratios["receivables_turnover"] = float('inf')
            ratios["receivables_turnover_status"] = {
                "level": "N/A",
                "level_en": "N/A",
                "level_ko": "데이터 없음",
                "level_zh": "无数据",
                "color": "gray",
                "description": "Cannot calculate due to missing receivables data.",
                "description_en": "Cannot calculate due to missing receivables data.",
                "description_ko": "매출채권 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少应收账款数据，无法计算。"
            }
        
        # 9.3 Days Inventory Outstanding (DIO)
        if ratios["inventory_turnover"] != float('inf'):
            ratios["days_inventory"] = 365 / ratios["inventory_turnover"]
            
            # Status evaluation
            if ratios["days_inventory"] > 90:
                ratios["days_inventory_status"] = {
                    "level": "Inefficient",
                    "level_en": "Inefficient",
                    "level_ko": "비효율",
                    "level_zh": "低效率",
                    "color": "red",
                    "description": "Long inventory holding period indicating low inventory management efficiency.",
                    "description_en": "Long inventory holding period indicating low inventory management efficiency.",
                    "description_ko": "재고자산 보유 기간이 길어 재고관리 효율성이 낮습니다.",
                    "description_zh": "库存持有期长，表明库存管理效率低。"
                }
            elif ratios["days_inventory"] > 60:
                ratios["days_inventory_status"] = {
                    "level": "Caution",
                    "level_en": "Caution",
                    "level_ko": "주의",
                    "level_zh": "警戒",
                    "color": "orange",
                    "description": "Somewhat long inventory holding period requiring management attention.",
                    "description_en": "Somewhat long inventory holding period requiring management attention.",
                    "description_ko": "재고자산 보유 기간이 다소 길어 관리가 필요합니다.",
                    "description_zh": "库存持有期稍长，需要管理关注。"
                }
            elif ratios["days_inventory"] > 45:
                ratios["days_inventory_status"] = {
                    "level": "Average",
                    "level_en": "Average",
                    "level_ko": "보통",
                    "level_zh": "平均",
                    "color": "yellow",
                    "description": "Shows average inventory holding period.",
                    "description_en": "Shows average inventory holding period.",
                    "description_ko": "평균적인 재고자산 보유 기간을 나타냅니다.",
                    "description_zh": "显示平均库存持有期。"
                }
            else:
                ratios["days_inventory_status"] = {
                    "level": "Excellent",
                    "level_en": "Excellent",
                    "level_ko": "우수",
                    "level_zh": "优秀",
                    "color": "green",
                    "description": "Short inventory holding period indicating efficient inventory management.",
                    "description_en": "Short inventory holding period indicating efficient inventory management.",
                    "description_ko": "재고자산 보유 기간이 짧아 재고관리가 효율적입니다.",
                    "description_zh": "库存持有期短，表明库存管理效率高。"
                }
        else:
            ratios["days_inventory"] = float('inf')
            ratios["days_inventory_status"] = {
                "level": "N/A",
                "level_en": "N/A",
                "level_ko": "데이터 없음",
                "level_zh": "无数据",
                "color": "gray",
                "description": "Cannot calculate due to missing inventory data.",
                "description_en": "Cannot calculate due to missing inventory data.",
                "description_ko": "재고자산 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少库存数据，无法计算。"
            }
        
        # 9.4 Days Sales Outstanding (DSO)
        if ratios["receivables_turnover"] != float('inf'):
            ratios["days_sales_outstanding"] = 365 / ratios["receivables_turnover"]
            
            # Status evaluation
            if ratios["days_sales_outstanding"] > 60:
                ratios["days_sales_outstanding_status"] = {
                    "level": "Inefficient",
                    "level_en": "Inefficient",
                    "level_ko": "비효율",
                    "level_zh": "低效率",
                    "color": "red",
                    "description": "Long receivables collection period indicating low cash conversion efficiency.",
                    "description_en": "Long receivables collection period indicating low cash conversion efficiency.",
                    "description_ko": "매출채권 회수 기간이 길어 현금 전환 효율성이 낮습니다.",
                    "description_zh": "应收账款收回期长，表明现金转换效率低。"
                }
            elif ratios["days_sales_outstanding"] > 45:
                ratios["days_sales_outstanding_status"] = {
                    "level": "Caution",
                    "level_en": "Caution",
                    "level_ko": "주의",
                    "level_zh": "警戒",
                    "color": "orange",
                    "description": "Somewhat long receivables collection period requiring management attention.",
                    "description_en": "Somewhat long receivables collection period requiring management attention.",
                    "description_ko": "매출채권 회수 기간이 다소 길어 관리가 필요합니다.",
                    "description_zh": "应收账款收回期稍长，需要管理关注。"
                }
            elif ratios["days_sales_outstanding"] > 30:
                ratios["days_sales_outstanding_status"] = {
                    "level": "Average",
                    "level_en": "Average",
                    "level_ko": "보통",
                    "level_zh": "平均",
                    "color": "yellow",
                    "description": "Shows average receivables collection period.",
                    "description_en": "Shows average receivables collection period.",
                    "description_ko": "평균적인 매출채권 회수 기간을 나타냅니다.",
                    "description_zh": "显示平均应收账款收回期。"
                }
            else:
                ratios["days_sales_outstanding_status"] = {
                    "level": "Excellent",
                    "level_en": "Excellent",
                    "level_ko": "우수",
                    "level_zh": "优秀",
                    "color": "green",
                    "description": "Short receivables collection period indicating efficient cash conversion.",
                    "description_en": "Short receivables collection period indicating efficient cash conversion.",
                    "description_ko": "매출채권 회수 기간이 짧아 현금 전환이 효율적입니다.",
                    "description_zh": "应收账款收回期短，表明现金转换效率高。"
                }
        else:
            ratios["days_sales_outstanding"] = float('inf')
            ratios["days_sales_outstanding_status"] = {
                "level": "N/A",
                "level_en": "N/A",
                "level_ko": "데이터 없음",
                "level_zh": "无数据",
                "color": "gray",
                "description": "Cannot calculate due to missing receivables data.",
                "description_en": "Cannot calculate due to missing receivables data.",
                "description_ko": "매출채권 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少应收账款数据，无法计算。"
            }
        
        # 9.5 Operating Cycle (영업주기)
        if ratios["inventory_turnover"] != float('inf') and ratios["receivables_turnover"] != float('inf'):
            days_inventory = ratios["days_inventory"]
            days_receivables = ratios["days_sales_outstanding"]
            ratios["operating_cycle"] = days_inventory + days_receivables
            
            # Status evaluation
            if ratios["operating_cycle"] > 120:
                ratios["operating_cycle_status"] = {"level": "비효율", "color": "red", 
                    "description": "영업주기가 길어 운전자본 관리 효율성 개선이 필요합니다."}
            elif ratios["operating_cycle"] > 90:
                ratios["operating_cycle_status"] = {"level": "주의", "color": "orange", 
                    "description": "영업주기가 평균 이상으로 운전자본 관리 검토가 필요합니다."}
            elif ratios["operating_cycle"] > 60:
                ratios["operating_cycle_status"] = {"level": "보통", "color": "yellow", 
                    "description": "영업주기가 적정 수준으로 운전자본 관리가 양호합니다."}
            else:
                ratios["operating_cycle_status"] = {"level": "우수", "color": "green", 
                    "description": "영업주기가 짧아 효율적인 운전자본 관리를 보여줍니다."}
        else:
            ratios["operating_cycle"] = float('inf')
            ratios["operating_cycle_status"] = {"level": "N/A", "color": "gray", 
                "description": "재고자산 또는 매출채권 데이터가 없어 계산할 수 없습니다."}
        
        # 10. Capital Expenditure (CAPEX) Ratios
        
        # 10.1 CAPEX-to-Sales Ratio
        if total_revenue > 0 and capital_expenditure != 0:
            capex_abs = abs(capital_expenditure)  # Capital expenditure is often negative in cash flow statements
            ratios["capex_to_sales"] = capex_abs / total_revenue
            
            # Status evaluation
            if ratios["capex_to_sales"] < 0.05:
                ratios["capex_to_sales_status"] = {
                    "level": "Conservative",
                    "level_en": "Conservative",
                    "level_ko": "보수적",
                    "level_zh": "保守的",
                    "color": "yellow",
                    "description": "Shows conservative capital investment tendency.",
                    "description_en": "Shows conservative capital investment tendency.",
                    "description_ko": "보수적인 자본 투자 성향을 보입니다.",
                    "description_zh": "显示保守的资本投资倾向。"
                }
            elif ratios["capex_to_sales"] < 0.10:
                ratios["capex_to_sales_status"] = {
                    "level": "Average",
                    "level_en": "Average",
                    "level_ko": "보통",
                    "level_zh": "平均",
                    "color": "green",
                    "description": "Maintaining adequate level of capital investment.",
                    "description_en": "Maintaining adequate level of capital investment.",
                    "description_ko": "적정 수준의 자본 투자를 유지하고 있습니다.",
                    "description_zh": "维持适当水平的资本投资。"
                }
            else:
                ratios["capex_to_sales_status"] = {
                    "level": "Aggressive",
                    "level_en": "Aggressive",
                    "level_ko": "공격적",
                    "level_zh": "积极的",
                    "color": "blue",
                    "description": "Focusing on growth with aggressive capital investment.",
                    "description_en": "Focusing on growth with aggressive capital investment.",
                    "description_ko": "공격적인 자본 투자로 성장에 집중하고 있습니다.",
                    "description_zh": "通过积极的资本投资关注增长。"
                }
        else:
            ratios["capex_to_sales"] = 0
            ratios["capex_to_sales_status"] = {
                "level": "N/A",
                "level_en": "N/A",
                "level_ko": "데이터 없음",
                "level_zh": "无数据",
                "color": "gray",
                "description": "Cannot calculate due to missing sales or capital expenditure data.",
                "description_en": "Cannot calculate due to missing sales or capital expenditure data.",
                "description_ko": "매출 또는 자본지출 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少销售或资本支出数据，无法计算。"
            }
        
        # 10.2 CAPEX-to-Depreciation Ratio
        depreciation = safe_get_multi(income_stmt, ["Depreciation", "Depreciation And Amortization"], 0)
        if depreciation == 0 and cash_flow is not None and not cash_flow.empty:
            depreciation = safe_get_multi(cash_flow, ["Depreciation", "Depreciation And Amortization"], 0)
        
        if depreciation > 0 and capital_expenditure != 0:
            capex_abs = abs(capital_expenditure)
            ratios["capex_to_depreciation"] = capex_abs / depreciation
            
            # Status evaluation
            if ratios["capex_to_depreciation"] < 1.0:
                ratios["capex_to_depreciation_status"] = {
                    "level": "Maintenance",
                    "level_en": "Maintenance",
                    "level_ko": "유지보수",
                    "level_zh": "维护",
                    "color": "red",
                    "description": "Investment below depreciation may lead to asset base reduction.",
                    "description_en": "Investment below depreciation may lead to asset base reduction.",
                    "description_ko": "감가상각 미만 투자로 자산 기반이 축소될 수 있습니다.",
                    "description_zh": "投资低于折旧可能导致资产基础减少。"
                }
            elif ratios["capex_to_depreciation"] < 1.5:
                ratios["capex_to_depreciation_status"] = {
                    "level": "Replacement",
                    "level_en": "Replacement",
                    "level_ko": "대체투자",
                    "level_zh": "替代性投资",
                    "color": "yellow",
                    "description": "Focusing mainly on replacement investments, which may limit growth.",
                    "description_en": "Focusing mainly on replacement investments, which may limit growth.",
                    "description_ko": "주로 대체투자에 집중하고 있어 성장이 제한적일 수 있습니다.",
                    "description_zh": "主要关注于替代性投资，可能会限制增长。"
                }
            elif ratios["capex_to_depreciation"] < 2.0:
                ratios["capex_to_depreciation_status"] = {
                    "level": "Balanced",
                    "level_en": "Balanced",
                    "level_ko": "균형",
                    "level_zh": "均衡",
                    "color": "green",
                    "description": "Balanced investment appropriately expanding the asset base.",
                    "description_en": "Balanced investment appropriately expanding the asset base.",
                    "description_ko": "균형 잡힌 투자로 자산 기반을 적절히 확장하고 있습니다.",
                    "description_zh": "均衡投资适当扩大资产基础。"
                }
            else:
                ratios["capex_to_depreciation_status"] = {
                    "level": "Growth",
                    "level_en": "Growth",
                    "level_ko": "성장투자",
                    "level_zh": "增长型投资",
                    "color": "blue",
                    "description": "Expanding asset base with aggressive growth investments.",
                    "description_en": "Expanding asset base with aggressive growth investments.",
                    "description_ko": "적극적인 성장 투자로 자산 기반을 확대하고 있습니다.",
                    "description_zh": "通过积极的增长型投资扩大资产基础。"
                }
        else:
            ratios["capex_to_depreciation"] = 0
            ratios["capex_to_depreciation_status"] = {
                "level": "N/A",
                "level_en": "N/A",
                "level_ko": "데이터 없음",
                "level_zh": "无数据",
                "color": "gray",
                "description": "Cannot calculate due to missing depreciation or capital expenditure data.",
                "description_en": "Cannot calculate due to missing depreciation or capital expenditure data.",
                "description_ko": "감가상각 또는 자본지출 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少折旧或资本支出数据，无法计算。"
            }
        
        # 10.3 Cash Flow to CAPEX Ratio
        if capital_expenditure != 0 and operating_cash_flow > 0:
            capex_abs = abs(capital_expenditure)
            ratios["cash_flow_to_capex"] = operating_cash_flow / capex_abs
            
            # Status evaluation based on the provided table
            if ratios["cash_flow_to_capex"] < 1.0:
                ratios["cash_flow_to_capex_status"] = {
                    "level": "External Funding Dependent",
                    "level_en": "External Funding Dependent",
                    "level_ko": "외부자금의존",
                    "level_zh": "依赖外部资金",
                    "color": "red",
                    "description": "High dependence on external funding.",
                    "description_en": "High dependence on external funding.",
                    "description_ko": "외부자금 의존도가 높습니다.",
                    "description_zh": "对外部资金的依赖度高。"
                }
            elif ratios["cash_flow_to_capex"] < 1.5:
                ratios["cash_flow_to_capex_status"] = {
                    "level": "Average",
                    "level_en": "Average",
                    "level_ko": "보통",
                    "level_zh": "平均",
                    "color": "yellow",
                    "description": "Able to invest using internal cash at an adequate level.",
                    "description_en": "Able to invest using internal cash at an adequate level.",
                    "description_ko": "자체현금으로 투자가 가능한 수준입니다.",
                    "description_zh": "能够使用内部现金进行适当水平的投资。"
                }
            else:
                ratios["cash_flow_to_capex_status"] = {
                    "level": "Surplus",
                    "level_en": "Surplus",
                    "level_ko": "잉여자금",
                    "level_zh": "盈余",
                    "color": "green",
                    "description": "Surplus funds are sufficient.",
                    "description_en": "Surplus funds are sufficient.",
                    "description_ko": "여유자금이 충분합니다.",
                    "description_zh": "盈余资金充足。"
                }
        else:
            ratios["cash_flow_to_capex"] = 0
            ratios["cash_flow_to_capex_status"] = {
                "level": "N/A",
                "level_en": "N/A",
                "level_ko": "데이터 없음",
                "level_zh": "无数据",
                "color": "gray",
                "description": "Cannot calculate due to missing capital expenditure or operating cash flow data.",
                "description_en": "Cannot calculate due to missing capital expenditure or operating cash flow data.",
                "description_ko": "자본지출 또는 영업현금흐름 데이터가 없어 계산할 수 없습니다.",
                "description_zh": "由于缺少资本支出或运营现金流数据，无法计算。"
            }
        
        # 10.4 FCF-to-Sales Ratio (Free Cash Flow Margin)
        if total_revenue > 0 and free_cash_flow != 0:
            ratios["fcf_to_sales"] = free_cash_flow / total_revenue
            
            # Status evaluation based on the provided table
            if ratios["fcf_to_sales"] < 0:
                ratios["fcf_to_sales_status"] = {"level": "현금부족", "color": "red", 
                    "description": "현금부족 또는 고성장 단계입니다."}
            elif ratios["fcf_to_sales"] < 0.10:
                ratios["fcf_to_sales_status"] = {"level": "보통", "color": "yellow", 
                    "description": "보통 수준의 잉여현금 창출 능력을 보여줍니다."}
            else:
                ratios["fcf_to_sales_status"] = {"level": "우수", "color": "green", 
                    "description": "잉여현금 창출 능력이 우수합니다."}
        else:
            ratios["fcf_to_sales"] = 0
            ratios["fcf_to_sales_status"] = {"level": "N/A", "color": "gray", 
                "description": "매출 또는 잉여현금흐름 데이터가 없어 계산할 수 없습니다."}
        
        # 11. WACC and Value Creation Analysis
        
        # 11.1 WACC Components
        financials = {
            "beta": safe_get_multi(history, ["Beta"]) if history is not None and not history.empty else 1.0,
            "total_debt": total_liabilities,
            "market_cap": market_cap,
            "tax_rate": income_tax / ebit if ebit != 0 and income_tax != 0 else 0.21  # Default to 21% if can't calculate
        }

        # 기본 무위험 수익률 (10년 국채 수익률) 설정
        risk_free_rate = 0.035  # 3.5%를 기본 무위험 수익률로 설정
        market_risk_premium = 0.05  # 5%를 기본 시장 위험 프리미엄으로 설정

        # WACC 계산
        wacc_result = calculate_wacc(financials, risk_free_rate, market_risk_premium)
        ratios["wacc"] = wacc_result["wacc"]
        
        # WACC 평가
        if ratios["wacc"] > 0:
            if ratios["wacc"] < 0.06:
                ratios["wacc_status"] = {"level": "Very Low", "color": "blue", 
                    "description": "매우 낮은 자본비용으로 투자와 성장에 유리한 환경입니다."}
            elif ratios["wacc"] < 0.08:
                ratios["wacc_status"] = {"level": "Low", "color": "green", 
                    "description": "낮은 자본비용으로 안정적인 투자가 가능한 상태입니다."}
            elif ratios["wacc"] < 0.10:
                ratios["wacc_status"] = {"level": "Moderate", "color": "yellow", 
                    "description": "적정 수준의 자본비용으로 균형잡힌 자본구조를 보여줍니다."}
            elif ratios["wacc"] < 0.12:
                ratios["wacc_status"] = {"level": "High", "color": "orange", 
                    "description": "높은 자본비용으로 투자 결정시 신중한 검토가 필요합니다."}
            else:
                ratios["wacc_status"] = {"level": "Very High", "color": "red", 
                    "description": "매우 높은 자본비용으로 수익성 개선이나 자본구조 조정이 필요할 수 있습니다."}
        
           # 10.2 Value Creation Analysis
        if ratios["roic"] > 0 and ratios["wacc"] > 0:
            ratios["value_spread"] = ratios["roic"] - ratios["wacc"]
            
            # Value creation status translations with level text
            value_creation_translations = {
                'English': {
                    'value_destruction': "ROIC is significantly lower than WACC, indicating serious value destruction.",
                    'slight_value_destruction': "ROIC is lower than WACC, resulting in gradual value destruction.",
                    'neutral': "ROIC is close to WACC, indicating the company is maintaining its value.",
                    'moderate_value_creation': "ROIC moderately exceeds WACC, creating value for shareholders.",
                    'strong_value_creation': "ROIC significantly exceeds WACC, continuously creating high value for shareholders.",
                    'no_data': "Unable to analyze due to missing ROIC or WACC data.",
                    'level_value_destruction': "Value Destruction",
                    'level_slight_value_destruction': "Slight Value Destruction",
                    'level_neutral': "Neutral",
                    'level_moderate_value_creation': "Moderate Value Creation",
                    'level_strong_value_creation': "Strong Value Creation"
                },
                '한국어': {
                    'value_destruction': "투자자본수익률(ROIC)이 자본비용(WACC)보다 크게 낮아 기업가치가 심각하게 훼손되고 있습니다.",
                    'slight_value_destruction': "투자자본수익률(ROIC)이 자본비용(WACC)보다 낮아 기업가치가 점진적으로 감소하고 있습니다.",
                    'neutral': "투자자본수익률(ROIC)이 자본비용(WACC)과 비슷한 수준으로 기업가치를 유지하고 있습니다.",
                    'moderate_value_creation': "투자자본수익률(ROIC)이 자본비용(WACC)을 적절히 상회하여 기업가치를 창출하고 있습니다.",
                    'strong_value_creation': "투자자본수익률(ROIC)이 자본비용(WACC)을 크게 상회하여 지속적으로 높은 기업가치를 창출하고 있습니다.",
                    'no_data': "투자자본수익률(ROIC) 또는 자본비용(WACC) 데이터가 없어 분석할 수 없습니다.",
                    'level_value_destruction': "가치 훼손",
                    'level_slight_value_destruction': "약간의 가치 훼손",
                    'level_neutral': "중립",
                    'level_moderate_value_creation': "적절한 가치 창출",
                    'level_strong_value_creation': "강력한 가치 창출"
                },
                '中文': {
                    'value_destruction': "投资资本回报率(ROIC)显著低于加权平均资本成本(WACC)，表明严重的价值损失。",
                    'slight_value_destruction': "投资资本回报率(ROIC)低于加权平均资本成本(WACC)，导致价值逐渐减少。",
                    'neutral': "投资资本回报率(ROIC)接近加权平均资本成本(WACC)，表明公司正在维持其价值。",
                    'moderate_value_creation': "投资资本回报率(ROIC)适度超过加权平均资本成本(WACC)，为股东创造价值。",
                    'strong_value_creation': "投资资本回报率(ROIC)显著超过加权平均资本成本(WACC)，持续为股东创造高价值。",
                    'no_data': "由于缺少投资资本回报率(ROIC)或加权平均资本成本(WACC)数据，无法进行分析。",
                    'level_value_destruction': "价值损失",
                    'level_slight_value_destruction': "轻微价值损失",
                    'level_neutral': "中性",
                    'level_moderate_value_creation': "适度价值创造",
                    'level_strong_value_creation': "强力价值创造"
                }
            }
            
            # Standardize language parameter
            if language.lower() == 'english':
                lang = 'English'
            elif language.lower() == 'korean' or language.lower() == '한국어':
                lang = '한국어'
            elif language.lower() == 'chinese' or language.lower() == '中文':
                lang = '中文'
            else:
                lang = 'English'  # Default to English
            
            # Get translations for the current language
            translations = value_creation_translations.get(lang, value_creation_translations['English'])
            
            # 가치 창출 여부 평가
            if ratios["value_spread"] < -0.05:
                ratios["value_creation_status"] = {
                    "level": translations.get('level_value_destruction', "Value Destruction"), 
                    "level_en": "Value Destruction",
                    "level_ko": "가치 훼손", 
                    "level_zh": "价值损失",
                    "color": "red", 
                    "description": translations['value_destruction'],
                    "description_en": value_creation_translations['English']['value_destruction'],
                    "description_ko": value_creation_translations['한국어']['value_destruction'],
                    "description_zh": value_creation_translations['中文']['value_destruction']
                }
            elif ratios["value_spread"] < -0.02:
                ratios["value_creation_status"] = {
                    "level": translations.get('level_slight_value_destruction', "Slight Value Destruction"), 
                    "level_en": "Slight Value Destruction", 
                    "level_ko": "약간의 가치 훼손", 
                    "level_zh": "轻微价值损失",
                    "color": "orange", 
                    "description": translations['slight_value_destruction'],
                    "description_en": value_creation_translations['English']['slight_value_destruction'],
                    "description_ko": value_creation_translations['한국어']['slight_value_destruction'],
                    "description_zh": value_creation_translations['中文']['slight_value_destruction']
                }
            elif ratios["value_spread"] < 0.02:
                ratios["value_creation_status"] = {
                    "level": translations.get('level_neutral', "Neutral"), 
                    "level_en": "Neutral", 
                    "level_ko": "중립", 
                    "level_zh": "中性",
                    "color": "yellow", 
                    "description": translations['neutral'],
                    "description_en": value_creation_translations['English']['neutral'],
                    "description_ko": value_creation_translations['한국어']['neutral'],
                    "description_zh": value_creation_translations['中文']['neutral']
                }
            elif ratios["value_spread"] < 0.05:
                ratios["value_creation_status"] = {
                    "level": translations.get('level_moderate_value_creation', "Moderate Value Creation"), 
                    "level_en": "Moderate Value Creation", 
                    "level_ko": "적절한 가치 창출", 
                    "level_zh": "适度价值创造",
                    "color": "green", 
                    "description": translations['moderate_value_creation'],
                    "description_en": value_creation_translations['English']['moderate_value_creation'],
                    "description_ko": value_creation_translations['한국어']['moderate_value_creation'],
                    "description_zh": value_creation_translations['中文']['moderate_value_creation']
                }
            else:
                ratios["value_creation_status"] = {
                    "level": translations.get('level_strong_value_creation', "Strong Value Creation"), 
                    "level_en": "Strong Value Creation", 
                    "level_ko": "강력한 가치 창출", 
                    "level_zh": "强力价值创造",
                    "color": "blue", 
                    "description": translations['strong_value_creation'],
                    "description_en": value_creation_translations['English']['strong_value_creation'],
                    "description_ko": value_creation_translations['한국어']['strong_value_creation'],
                    "description_zh": value_creation_translations['中文']['strong_value_creation']
                }
        else:
            ratios["value_spread"] = 0
            # Get translations for the current language
            if 'translations' not in locals():
                # Standardize language parameter
                if language.lower() == 'english':
                    lang = 'English'
                elif language.lower() == 'korean' or language.lower() == '한국어':
                    lang = '한국어'
                elif language.lower() == 'chinese' or language.lower() == '中文':
                    lang = '中文'
                else:
                    lang = 'English'  # Default to English
                    
                value_creation_translations = {
                    'English': {
                        'no_data': "Unable to analyze due to missing ROIC or WACC data."
                    },
                    '한국어': {
                        'no_data': "투자자본수익률(ROIC) 또는 자본비용(WACC) 데이터가 없어 분석할 수 없습니다."
                    },
                    '中文': {
                        'no_data': "由于缺少投资资本回报率(ROIC)或加权平均资本成本(WACC)数据，无法进行分析。"
                    }
                }
                translations = value_creation_translations.get(lang, value_creation_translations['English'])
            
            ratios["value_creation_status"] = {
                "level": "N/A", 
                "level_en": "N/A", 
                "level_ko": "데이터 없음", 
                "level_zh": "无数据",
                "color": "gray", 
                "description": translations['no_data'],
                "description_en": value_creation_translations.get('English', {}).get('no_data', "Unable to analyze due to missing data."),
                "description_ko": value_creation_translations.get('한국어', {}).get('no_data', "데이터가 없어 분석할 수 없습니다."),
                "description_zh": value_creation_translations.get('中文', {}).get('no_data', "由于缺少数据，无法进行分析。")
            }
            
    except Exception as e:
        print(f"Error calculating financial ratios: {e}")
        # In case of calculation error, return empty ratios
        ratios = {}
    return ratios

def calculate_dcf_earnings_based(
    eps_without_nri,        # EPS without Non-Recurring Items
    growth_rate_stage1=0.159,  # Growth rate in growth stage (default 15.9% from Apple example)
    discount_rate=0.11,     # Discount rate (default 11%)
    growth_years=10,        # Number of growth stage years (default 10)
    terminal_growth_rate=0.04,  # Terminal growth rate (default 4%)
    terminal_years=10       # Number of terminal stage years (default 10)
):
    """
    Calculate DCF (Earnings Based) valuation
    
    Formula:
    DCF (Earnings Based) = EPS without NRI * {[(1+g1)/(1+d) + (1+g1)^2/(1+d)^2 + ... + (1+g1)^10/(1+d)^10] 
                           + (1+g1)^10/(1+d)^10 * [(1+g2)/(1+d) + (1+g2)^2/(1+d)^2 + ... + (1+g2)^10/(1+d)^10]}
    
    Simplified as:
    DCF (Earnings Based) = EPS without NRI * [x * (1-x^10) / (1-x) + x^10 * y * (1-y^10) / (1-y)]
    where x = (1+g1)/(1+d) and y = (1+g2)/(1+d)
    
    Parameters:
    - eps_without_nri: EPS without Non-Recurring Items 
    - growth_rate_stage1: Growth rate in growth stage (decimal, default 15.9%)
    - discount_rate: Discount rate (decimal, default 11%)
    - growth_years: Number of growth stage years (default 10)
    - terminal_growth_rate: Terminal growth rate (default 4%)
    - terminal_years: Number of terminal stage years (default 10)
    
    Returns:
    - DCF (Earnings Based) value
    """
    # 입력값이 백분율로 들어온 경우 소수로 변환
    if growth_rate_stage1 > 1:
        growth_rate_stage1 = growth_rate_stage1 / 100
    if discount_rate > 1:
        discount_rate = discount_rate / 100
    if terminal_growth_rate > 1:
        terminal_growth_rate = terminal_growth_rate / 100
        
    # 성장률 범위 확인 (5% - 20%)
    growth_rate_stage1 = max(0.05, min(0.20, growth_rate_stage1))
    
    # 할인율과 영구성장률 검증
    if discount_rate <= terminal_growth_rate:
        # 안전장치: 할인율은 항상 영구성장률보다 최소 2% 이상 높게 설정
        discount_rate = max(discount_rate, terminal_growth_rate + 0.02)
    
    # x와 y 계산 
    x = (1 + growth_rate_stage1) / (1 + discount_rate)
    y = (1 + terminal_growth_rate) / (1 + discount_rate)
    
    # 첫 번째 합계 계산: x + x^2 + ... + x^growth_years
    if abs(x - 1) < 1e-10:  # x가 거의 1인 경우
        sum1 = growth_years
    else:
        # 기하급수 합: x * (1 - x^growth_years) / (1 - x)
        sum1 = x * (1 - x**growth_years) / (1 - x)
    
    # 두 번째 합계 계산: y + y^2 + ... + y^terminal_years
    if abs(y - 1) < 1e-10:  # y가 거의 1인 경우
        sum2 = terminal_years
    else:
        # 기하급수 합: y * (1 - y^terminal_years) / (1 - y)
        sum2 = y * (1 - y**terminal_years) / (1 - y)
    
    # 최종 DCF 계산
    total_multiplier = sum1 + (x**growth_years) * sum2
    dcf_value = eps_without_nri * total_multiplier
    
    # 성장 단계 현금흐름
    growth_stage_pv_sum = 0
    for year in range(1, growth_years + 1):
        cf = eps_without_nri * (1 + growth_rate_stage1) ** year
        pv_factor = 1 / ((1 + discount_rate) ** year)
        pv = cf * pv_factor
        growth_stage_pv_sum += pv
        
    
    # 영구 단계 시작 현금흐름
    cf_at_growth_end = eps_without_nri * (1 + growth_rate_stage1) ** growth_years
    
    # 영구 단계 현금흐름
    terminal_stage_pv_sum = 0
    for year in range(1, terminal_years + 1):
        cf = cf_at_growth_end * (1 + terminal_growth_rate) ** year
        pv_factor = 1 / ((1 + discount_rate) ** (growth_years + year))
        pv = cf * pv_factor
        terminal_stage_pv_sum += pv
    
    # 공식 계산과 직접 계산 비교
    direct_dcf_value = growth_stage_pv_sum + terminal_stage_pv_sum
    
    # 차이가 크면 경고
    if abs(dcf_value - direct_dcf_value) > 0.5:
        print(f"Warning: Large difference between formula and direct calculation: {abs(dcf_value - direct_dcf_value):.2f}")
    
    return dcf_value

def calculate_dcf_fcf_based(
    fcf_per_share,          # Free Cash Flow per Share
    growth_rate_stage1=0.137,  # Growth rate in growth stage (default 13.7% from Apple example)
    discount_rate=0.11,     # Discount rate (default 11%)
    growth_years=10,        # Number of growth stage years (default 10)
    terminal_growth_rate=0.04,  # Terminal growth rate (default 4%)
    terminal_years=10       # Number of terminal stage years (default 10)
):
    """
    Calculate DCF (FCF Based) valuation using example method.
    
    Formula:
    DCF (FCF Based) = FCF per Share * {[(1+g1)/(1+d) + (1+g1)^2/(1+d)^2 + ... + (1+g1)^10/(1+d)^10] 
                     + (1+g1)^10/(1+d)^10 * [(1+g2)/(1+d) + (1+g2)^2/(1+d)^2 + ... + (1+g2)^10/(1+d)^10]}
    
    Simplified as:
    DCF (FCF Based) = FCF per Share * [x * (1-x^10) / (1-x) + x^10 * y * (1-y^10) / (1-y)]
    where x = (1+g1)/(1+d) and y = (1+g2)/(1+d)
    
    Parameters:
    - fcf_per_share: Free Cash Flow per Share
    - growth_rate_stage1: Growth rate in growth stage (decimal, default 13.7%)
    - discount_rate: Discount rate (decimal, default 11%)
    - growth_years: Number of growth stage years (default 10)
    - terminal_growth_rate: Terminal growth rate (default 4%)
    - terminal_years: Number of terminal stage years (default 10)
    
    Returns:
    - DCF (FCF Based) value
    """
    # 입력값이 백분율로 들어온 경우 소수로 변환
    if growth_rate_stage1 > 1:
        growth_rate_stage1 = growth_rate_stage1 / 100
    if discount_rate > 1:
        discount_rate = discount_rate / 100
    if terminal_growth_rate > 1:
        terminal_growth_rate = terminal_growth_rate / 100
    
    # 성장률 범위 확인 (5% - 20%)
    growth_rate_stage1 = max(0.05, min(0.20, growth_rate_stage1))
    
    # x와 y 계산 
    x = (1 + growth_rate_stage1) / (1 + discount_rate)
    y = (1 + terminal_growth_rate) / (1 + discount_rate)
    
    # 첫 번째 합계 계산: x + x^2 + ... + x^growth_years
    if abs(x - 1) < 1e-10:  # x가 거의 1인 경우
        sum1 = growth_years
    else:
        # 기하급수 합: x * (1 - x^growth_years) / (1 - x)
        sum1 = x * (1 - x**growth_years) / (1 - x)
    
    # 두 번째 합계 계산: y + y^2 + ... + y^terminal_years
    if abs(y - 1) < 1e-10:  # y가 거의 1인 경우
        sum2 = terminal_years
    else:
        # 기하급수 합: y * (1 - y^terminal_years) / (1 - y)
        sum2 = y * (1 - y**terminal_years) / (1 - y)
    
    # 최종 DCF 계산
    total_multiplier = sum1 + (x**growth_years) * sum2
    dcf_value = fcf_per_share * total_multiplier

    growth_stage_pv_sum = 0
    for year in range(1, growth_years + 1):
        cf = fcf_per_share * (1 + growth_rate_stage1) ** year
        pv_factor = 1 / ((1 + discount_rate) ** year)
        pv = cf * pv_factor
        growth_stage_pv_sum += pv
    
    # 영구 단계 시작 현금흐름
    cf_at_growth_end = fcf_per_share * (1 + growth_rate_stage1) ** growth_years
    
    # 영구 단계 현금흐름
    terminal_stage_pv_sum = 0
    for year in range(1, terminal_years + 1):
        cf = cf_at_growth_end * (1 + terminal_growth_rate) ** year
        pv_factor = 1 / ((1 + discount_rate) ** (growth_years + year))
        pv = cf * pv_factor
        terminal_stage_pv_sum += pv
    
    # 공식 계산과 직접 계산 비교
    direct_dcf_value = growth_stage_pv_sum + terminal_stage_pv_sum
    
    # 차이가 크면 경고
    if abs(dcf_value - direct_dcf_value) > 0.5:
        print(f"Warning: Large difference between formula and direct calculation: {abs(dcf_value - direct_dcf_value):.2f}")
    
    return dcf_value

def calculate_peter_lynch_fair_value(ticker, eps_without_nri=None, ebitda_growth_rate=None, peg_ratio=1.0):
    """Peter Lynch 공정가치 계산 함수 - 
    
    Parameters:
    - ticker: Stock ticker symbol
    - eps_without_nri: Optional EPS without NRI for fallback (if provided)
    - ebitda_growth_rate: Optional EBITDA growth rate for fallback (if provided)
    - peg_ratio: PEG ratio for fallback (default 1.0)
    
    Returns:
    - A tuple containing (fair_value, used_peg_ratio, used_growth_rate, used_eps) or None if calculation fails
    """
    try:
        stock = yf.Ticker(ticker)
        stock_info = stock.get_info()
        
        trailing_peg_ratio = stock_info.get('trailingPegRatio', 0)
        eps_ttm = stock_info.get('epsTrailingTwelveMonths', 0)
        earnings_growth = stock_info.get('earningsGrowth', 0)
        
        fair_value = trailing_peg_ratio * eps_ttm * earnings_growth * 100
        used_peg_ratio = trailing_peg_ratio
        used_growth_rate = earnings_growth * 100  # Convert to percentage for display
        used_eps = eps_ttm
        
        if fair_value <= 0 or math.isnan(fair_value):
            print(f"Debug: New Peter Lynch formula returned invalid value, falling back to original")
            if eps_without_nri is not None and ebitda_growth_rate is not None:
                if isinstance(ebitda_growth_rate, (int, float)) and ebitda_growth_rate <= 1:
                    ebitda_growth_percentage = ebitda_growth_rate * 100
                else:
                    ebitda_growth_percentage = ebitda_growth_rate
                fair_value = peg_ratio * ebitda_growth_percentage * eps_without_nri
                used_peg_ratio = peg_ratio
                used_growth_rate = ebitda_growth_percentage
                used_eps = eps_without_nri
            else:
                return None  # Cannot fallback if parameters missing
        
        return fair_value, used_peg_ratio, used_growth_rate, used_eps
    except Exception as e:
        print(f"Error in Peter Lynch calculation: {e}")
        return None

def calculate_two_stage_dcf(
    initial_earnings,         # Initial earnings in millions of USD
    growth_rate,              # Growth rate (decimal, e.g. 0.10 = 10%)
    terminal_growth_rate,     # Terminal growth rate (decimal)
    discount_rate,            # Discount rate (decimal, e.g. WACC)
    growth_years,             # Number of high-growth years (integer)
    terminal_years,           # Number of terminal years for non-perpetuity (integer)
    net_debt,                 # Net debt in millions of USD
    shares_outstanding,       # Shares outstanding in millions of shares
    include_tangible_book=False,
    tangible_book_value=0,    # Tangible book value in millions of USD
    use_perpetuity=False      # If True, use Gordon Growth (perpetuity) for terminal value
):
    """
    Two-stage DCF valuation.
    
    Units:
      - initial_earnings, net_debt, tangible_book_value: million USD
      - shares_outstanding: million shares
      
    Returns a dict with:
      - growth_stage_value: PV of high-growth cash flows (million USD)
      - pv_terminal_value: PV of terminal value (million USD)
      - intrinsic_value: sum of PVs + tangible book (if included)
      - equity_value: intrinsic_value minus net_debt
      - fair_value_per_share: USD per share
      - projected_earnings, pv_cash_flows 등 시각화용 리스트
    """
    # 1) Input validation
    if not (-1.0 < growth_rate < 2.0 and -0.5 < terminal_growth_rate < 0.5):
        return {"success": False,
                "error": "Growth rates out of realistic range",
                "fair_value_per_share": 0}
    if discount_rate <= terminal_growth_rate:
        return {"success": False,
                "error": "Discount rate must exceed terminal growth rate",
                "fair_value_per_share": 0}
    if shares_outstanding <= 0:
        shares_outstanding = 1.0

    # 2) Growth-stage PV 계산
    # CF_t = initial_earnings * (1+g)^t
    # PV = Σ CF_t / (1+r)^t
    x = (1 + growth_rate) / (1 + discount_rate)
    if x == 1:
        growth_stage_value = initial_earnings * growth_years / (1 + discount_rate)
    else:
        growth_stage_value = initial_earnings * x * (1 - x**growth_years) / (1 - x)

    # 3) Terminal-stage PV 계산
    # CF at end of growth: CF_N = initial_earnings * (1+g)^growth_years
    cf_at_growth_end = initial_earnings * (1 + growth_rate)**growth_years

    if use_perpetuity:
        # Gordon Growth Model
        terminal_value_at_t = cf_at_growth_end * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        pv_terminal_value = terminal_value_at_t / ((1 + discount_rate)**growth_years)
    else:
        # Finite horizon terminal stage
        pv_terminal_value = 0.0
        for t in range(1, terminal_years + 1):
            cf_t = cf_at_growth_end * (1 + terminal_growth_rate)**t
            pv_t = cf_t / ((1 + discount_rate)**(growth_years + t))
            pv_terminal_value += pv_t

    # 4) Intrinsic & Equity value 계산
    intrinsic_value = growth_stage_value + pv_terminal_value
    if include_tangible_book and tangible_book_value > 0:
        intrinsic_value += tangible_book_value

    equity_value = intrinsic_value - net_debt

    fair_value_per_share = max(equity_value, 0.0) / shares_outstanding

    # 6) 시각화용 리스트 (옵션)
    projected_earnings = []
    pv_cash_flows = []
    current_cf = initial_earnings
    # Growth phase
    for year in range(1, growth_years + 1):
        current_cf *= (1 + growth_rate)
        projected_earnings.append(current_cf)
        pv_cash_flows.append(current_cf / ((1 + discount_rate)**year))
    # Terminal phase
    # (여기서는 간단히 perpetuity 제외 시 실제 CF만)
    last_cf = projected_earnings[-1] if projected_earnings else cf_at_growth_end
    for year in range(1, terminal_years + 1):
        cf_t = last_cf * (1 + terminal_growth_rate)**year
        projected_earnings.append(cf_t)
        pv_cash_flows.append(cf_t / ((1 + discount_rate)**(growth_years + year)))

    return {
        "success": True,
        "growth_stage_value": growth_stage_value,
        "pv_terminal_value": pv_terminal_value,
        "intrinsic_value": intrinsic_value,
        "enterprise_value": intrinsic_value,  # 엔터프라이즈 밸류 추가
        "equity_value": equity_value,
        "fair_value_per_share": fair_value_per_share,
        "per_share_value": fair_value_per_share,  # 키 이름 호환성을 위해 추가
        "projected_earnings": projected_earnings,
        "pv_cash_flows": pv_cash_flows,
    }
