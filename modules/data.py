"""
Data fetching and processing functions for the DCF calculator application.
"""
import yfinance as yf
import streamlit as st
import pandas as pd
import math
from .utils import safe_get, calculate_historical_ratios

def fetch_data(ticker, force_refresh=False):
    """
    Fetch financial data for a given ticker.
    
    Parameters:
    - ticker: Stock ticker symbol
    - force_refresh: Force refresh data ignoring cache
    
    Returns:
    - Dictionary containing stock information, financial statements, and risk-free rate
    """
    # 강제 새로고침이면 캐시 무시하고 새로 가져옴
    if force_refresh:
        # Clear specific cache entry for this ticker
        fetch_data_cached.clear()
    
    # 캐시된 함수 호출 (force_refresh=False인 경우에만)
    return fetch_data_cached(ticker)

@st.cache_data(ttl=600)
def fetch_data_cached(ticker):
    """캐시 처리를 위한 내부 함수"""
    try:
        # Get stock info
        stock = yf.Ticker(ticker)
        
        # Get all available info including analyst data
        info = stock.info
        
        # Debug: Print available analyst data
        print("\n=== Debug: Available Analyst Data ===")
        print("numberOfAnalystOpinions:", info.get('numberOfAnalystOpinions', 'Not found'))
        print("averageAnalystRating:", info.get('averageAnalystRating', 'Not found'))
        print("recommendationKey:", info.get('recommendationKey', 'Not found'))
        
        # Get historical prices
        history = stock.history(period="5y")  # Extended to 5 years for better historical analysis
        
        # Get financial statements
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        # Get risk-free rate (10-year Treasury yield)
        try:
            treasury = yf.Ticker("^TNX")
            risk_free_rate = treasury.info.get('previousClose', 3.5) / 100
        except:
            risk_free_rate = 0.035  # Default to 3.5% if unable to fetch
        
        return {
            "info": info,
            "history": history,
            "income_stmt": income_stmt,
            "balance_sheet": balance_sheet,
            "cash_flow": cash_flow,
            "risk_free_rate": risk_free_rate,
            "ticker_info": info,  # info 중복 제거를 위해 나중에 refactor 필요
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    try:
        # Get stock info
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get historical prices
        history = stock.history(period="5y")  # Extended to 5 years for better historical analysis
        
        # Get financial statements
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        # Get risk-free rate (10-year Treasury yield)
        try:
            treasury = yf.Ticker("^TNX")
            risk_free_rate = treasury.info.get('previousClose', 3.5) / 100
        except:
            risk_free_rate = 0.035  # Default to 3.5% if unable to fetch
        
        return {
            "info": info,
            "history": history,
            "income_stmt": income_stmt,
            "balance_sheet": balance_sheet,
            "cash_flow": cash_flow,
            "risk_free_rate": risk_free_rate,
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_financials(data, ticker=None):
    """
    Extract key financial metrics from the fetched data.
    
    Parameters:
    - data: Dictionary containing stock data from fetch_data function
    
    Returns:
    - Dictionary containing key financial metrics
    """
    info = data["info"]
    income_stmt = data["income_stmt"]
    balance_sheet = data["balance_sheet"]
    cash_flow = data["cash_flow"]
    history = data["history"]
    
    # General info
    company_name = info.get("longName", "")
    current_price = info.get("currentPrice", 0)
    shares_outstanding = info.get("sharesOutstanding", 0)
    market_cap = info.get("marketCap", 0)
    
    # ticker가 전달되지 않은 경우 info에서 가져오기
    if ticker is None:
        ticker = info.get('symbol', '')
    # Beta - 여러 방법으로 가져오기 시도
    beta = 1.0  # 기본값으로 설정
    
    # 1. info에서 beta 필드로 시도
    raw_beta = info.get("beta")
    if raw_beta is not None and isinstance(raw_beta, (int, float)):
        beta = raw_beta
    else:
        # 2. 다른 필드명 시도
        alternative_beta_fields = ["beta3Year", "beta5Year", "betaValue"]
        for field in alternative_beta_fields:
            if field in info and info[field] is not None and isinstance(info[field], (int, float)):
                beta = info[field]
                break
                
        # 3. 심볼 정보에서 가져오기 시도
        try:
            quick_info = stock.get_info()
            if "beta" in quick_info and quick_info["beta"] is not None:
                beta = quick_info["beta"]
        except Exception as e:
            pass
            
    # Beta가 졸린 값(5이상)이 나오면 보정
    if beta > 5.0:
        beta = 1.0
    elif beta < 0.1:
        beta = 0.1
    
    # Income statement items
    if len(income_stmt.columns) > 0:
        revenue = safe_get(income_stmt, "Total Revenue")
        gross_profit = safe_get(income_stmt, "Gross Profit") or safe_get(income_stmt, "Total Revenue") - safe_get(income_stmt, "Cost Of Revenue")
        ebit = safe_get(income_stmt, "EBIT") or safe_get(income_stmt, "Operating Income")
        net_income = safe_get(income_stmt, "Net Income")
        
        # Extract Interest Expense with more possible field names
        interest_expense = 0
        interest_field_names = [
            "Interest Expense", 
            "Interest Expense, Net", 
            "Interest Expense Net", 
            "Net Interest Expense",
            "Interest Paid",
            "Finance Costs",
            "Financial Expenses"
        ]
        
        # 최근 회계연도의 이자비용 찾기
        for field in interest_field_names:
            if field in income_stmt.index:
                value = income_stmt.loc[field].iloc[0]
                if pd.notnull(value) and value != 0:
                    interest_expense = abs(value)  # 음수로 표시될 수 있으므로 절대값 사용
                    break
        
        # 최근 회계연도의 이자비용이 0이고, 직전 연도 데이터가 있는 경우 직전 연도 데이터 사용
        if interest_expense == 0 and len(income_stmt.columns) > 1:
            # 모든 이자비용 필드에 대해 각 열 별로 값을 직접 확인
            for col_idx in range(1, min(3, len(income_stmt.columns))):  # 최대 3개 열까지 확인
                for field in interest_field_names:
                    if field in income_stmt.index:
                        try:
                            value = income_stmt.loc[field].iloc[col_idx]
                            if pd.notnull(value) and value != 0:
                                interest_expense = abs(value)
                                break
                        except Exception as e:
                            pass
                if interest_expense != 0:
                    break
                    
        # Non-operating interest expense
        interest_expense_non_operating = 0
        non_op_interest_field_names = [
            "Interest Expense Non Operating", 
            "Interest Expense, Net Non Operating",
            "Non Operating Interest Expense", 
            "Nonoperating Interest Expense",
            "Other Non Operating Expense"
        ]
        
        # 최근 회계연도의 non-operating 이자비용 찾기
        for field in non_op_interest_field_names:
            if field in income_stmt.index:
                value = income_stmt.loc[field].iloc[0]
                if pd.notnull(value) and value != 0:
                    interest_expense_non_operating = abs(value)  # 음수로 표시될 수 있으므로 절대값 사용
                    break
        
        # 최근 회계연도의 non-operating 이자비용이 0이고, 직전 연도 데이터가 있는 경우 직전 연도 데이터 사용
        if interest_expense_non_operating == 0 and len(income_stmt.columns) > 1:
            
            # 모든 non-operating 이자비용 필드에 대해 각 열 별로 값을 직접 확인
            for col_idx in range(1, min(3, len(income_stmt.columns))):  # 최대 3개 열까지 확인
                for field in non_op_interest_field_names:
                    if field in income_stmt.index:
                        try:
                            value = income_stmt.loc[field].iloc[col_idx]
                            if pd.notnull(value) and value != 0:
                                interest_expense_non_operating = abs(value)
                                break
                        except Exception as e:
                            pass
                if interest_expense_non_operating != 0:
                    break
        
        # 이자비용이 없으면 일반 이자비용을 non-operating 값으로 사용
        if interest_expense_non_operating == 0 and interest_expense > 0:
            interest_expense_non_operating = interest_expense
        
        # 마지막 수단: 이자비용을 여전히 찾을 수 없을 경우, 대안으로 total_debt 기반 추정치 사용
        if interest_expense == 0 and interest_expense_non_operating == 0:
            # 평균 부채 데이터가 있다면 그것을 사용해 추정
            if len(balance_sheet.columns) > 0:
                total_debt_current = safe_get(balance_sheet, "Total Debt") or (safe_get(balance_sheet, "Short Term Debt") + safe_get(balance_sheet, "Long Term Debt"))
                if total_debt_current > 0:
                    # 평균적인 cost of debt 비율을 4%로 가정하고 이자비용 추정
                    estimated_interest = total_debt_current * 0.04
                    print(f"No interest expense found, estimating based on total debt: {estimated_interest:,.2f}")
                    interest_expense = estimated_interest
                    interest_expense_non_operating = estimated_interest
        
        # Get historical revenue growth
        revenue_growth = 0
        if len(income_stmt.columns) >= 2 and "Total Revenue" in income_stmt.index:
            current_revenue = safe_get(income_stmt, "Total Revenue", 0)
            previous_revenue = safe_get(income_stmt, "Total Revenue", 1)
            if previous_revenue > 0:
                revenue_growth = (current_revenue / previous_revenue - 1) * 100
    else:
        revenue = 0
        gross_profit = 0
        ebit = 0
        net_income = 0
        revenue_growth = 0
        interest_expense = 0
        interest_expense_non_operating = 0
    
    # Balance sheet items
    if len(balance_sheet.columns) > 0:
        total_assets = safe_get(balance_sheet, "Total Assets")
        total_liabilities = safe_get(balance_sheet, "Total Liabilities Net Minority Interest") or safe_get(balance_sheet, "Total Liabilities")
        total_equity = safe_get(balance_sheet, "Total Equity") or safe_get(balance_sheet, "Total Stockholder Equity")
        total_debt = safe_get(balance_sheet, "Total Debt") or (safe_get(balance_sheet, "Short Term Debt") + safe_get(balance_sheet, "Long Term Debt"))
        cash = safe_get(balance_sheet, "Cash And Cash Equivalents") or safe_get(balance_sheet, "Cash")
    else:
        total_assets = 0
        total_liabilities = 0
        total_equity = 0
        total_debt = 0
        cash = 0
    
    # Cash flow items
    if len(cash_flow.columns) > 0:
        operating_cash_flow = safe_get(cash_flow, "Operating Cash Flow") or safe_get(cash_flow, "Total Cash From Operating Activities")
        capital_expenditure = safe_get(cash_flow, "Capital Expenditure")
        fcf = safe_get(cash_flow, "Free Cash Flow")
        if fcf == 0:  # Calculate if not directly available
            fcf = operating_cash_flow + capital_expenditure
        
        # Get historical FCF growth
        fcf_growth = 0
        if len(cash_flow.columns) >= 2:
            if "Free Cash Flow" in cash_flow.index:
                current_fcf = safe_get(cash_flow, "Free Cash Flow", 0)
                previous_fcf = safe_get(cash_flow, "Free Cash Flow", 1)
                if previous_fcf > 0:
                    fcf_growth = (current_fcf / previous_fcf - 1) * 100
            elif "Operating Cash Flow" in cash_flow.index and "Capital Expenditure" in cash_flow.index:
                current_ocf = safe_get(cash_flow, "Operating Cash Flow", 0)
                current_capex = safe_get(cash_flow, "Capital Expenditure", 0)
                previous_ocf = safe_get(cash_flow, "Operating Cash Flow", 1)
                previous_capex = safe_get(cash_flow, "Capital Expenditure", 1)
                current_fcf = current_ocf + current_capex
                previous_fcf = previous_ocf + previous_capex
                if previous_fcf != 0:
                    fcf_growth = (current_fcf / previous_fcf - 1) * 100
    else:
        operating_cash_flow = 0
        capital_expenditure = 0
        fcf = 0
        fcf_growth = 0
    
    # Derived metrics
    enterprise_value = market_cap + total_debt - cash
    net_debt = total_debt - cash
    fcf_per_share = fcf / shares_outstanding if shares_outstanding > 0 else 0
    book_value_per_share = total_equity / shares_outstanding if shares_outstanding > 0 else 0
    
    # Calculate tangible book value
    intangible_assets = 0
    if len(balance_sheet.columns) > 0:
        intangible_assets = safe_get(balance_sheet, "Intangible Assets") or safe_get(balance_sheet, "Goodwill")
    
    tangible_equity = total_equity - intangible_assets
    tangible_book_per_share = tangible_equity / shares_outstanding if shares_outstanding > 0 else 0
    

    # trailingEps 가져오기 (정확한 키 이름 사용)
    trailingEps = info.get("trailingEps", None)
    
    if trailingEps is not None and trailingEps != 0 and not math.isnan(trailingEps):
        eps = trailingEps
    else:
        # P/E 비율이 15정도라고 가정하고 과도한 계산 대신 현재 가격을 기반으로 간단하게 추정
        eps = current_price / 15.0  # 표준적인 P/E 비율으로 역산
    
    forward_eps = info.get("forwardEps", 0)
    
    # Calculate historical ratios
    pe_ratio_history, pb_ratio_history, pe_stats, pb_stats = calculate_historical_ratios(
        history, income_stmt, balance_sheet, shares_outstanding
    )
    
    # Get P/E and P/B ratios (first try , then calculate if not available)
    # Trailing P/E
    pe_ratio = info.get("trailingPE", 0)  # 이 키는 대문자 PE가 맞음
    if pe_ratio == 0 or pe_ratio is None or math.isnan(pe_ratio):
        if eps > 0:
            pe_ratio = current_price / eps
    
    # Forward P/E 
    forward_pe = info.get("forwardPE", 0)
    if forward_pe == 0 or forward_pe is None or math.isnan(forward_pe):
        if forward_eps > 0:
            forward_pe = current_price / forward_eps
    
    # Price to Book
    pbr = info.get("priceToBook", 0)
    if pbr == 0 or pbr is None or math.isnan(pbr):
        if book_value_per_share and book_value_per_share > 0:
            pbr = current_price / book_value_per_share
    
    # Get additional metrics for quick ratio and current ratio
    quick_ratio = info.get("quickRatio", 0)
    current_ratio = info.get("currentRatio", 0)
    
    # ROE and ROA - directly use data when available
    roe = info.get('returnOnEquity', 0)
    if roe == 0 or roe is None or math.isnan(roe):
        # Fallback calculation if value is not available
        roe = net_income / total_equity if total_equity > 0 else 0
    
    roa = info.get('returnOnAssets', 0)
    if roa == 0 or roa is None or math.isnan(roa):
        # Fallback calculation if value is not available
        roa = net_income / total_assets if total_assets > 0 else 0
    
    # Tax rate
    tax_rate = 0.21  # Default US corporate tax rate
    if "Income Tax Expense" in income_stmt.index and "Pretax Income" in income_stmt.index:
        pretax_income = safe_get(income_stmt, "Pretax Income")
        income_tax = safe_get(income_stmt, "Income Tax Expense")
        if pretax_income != 0:
            tax_rate = abs(income_tax / pretax_income)
    
    # Dividends
    dividend_rate = info.get("dividendRate", 0)
    dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
    
    # Return calculated financial metrics
    return {
        "company_name": company_name,
        "ticker": ticker,
        "current_price": current_price,
        "shares_outstanding": shares_outstanding,
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "trailing_eps": trailingEps,
        "pe_ratio": pe_ratio,
        "revenue": revenue,
        "gross_profit": gross_profit,
        "ebit": ebit,
        "net_income": net_income,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "total_debt": total_debt,
        "cash": cash,
        "net_debt": net_debt,
        "operating_cash_flow": operating_cash_flow,
        "capital_expenditure": capital_expenditure,
        "fcf": fcf,
        "fcf_growth": fcf_growth,
        "fcf_per_share": fcf_per_share,
        "book_value_per_share": book_value_per_share,
        "eps": eps,
        "forward_eps": forward_eps,
        "forward_pe_ratio": forward_pe,  # Forward P/E ratio added
        "pbr": pbr,
        "roe": roe,
        "roa": roa,
        "tax_rate": tax_rate,
        "dividend_rate": dividend_rate,
        "dividend_yield": dividend_yield,
        "interest_expense": interest_expense,
        "interest_expense_non_operating": interest_expense_non_operating,
        "beta": beta,
        "quick_ratio": quick_ratio,
        "current_ratio": current_ratio,
        "balance_sheet": balance_sheet,
        "ticker": info.get('symbol', '')
    }
