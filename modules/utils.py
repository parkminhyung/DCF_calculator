"""
Utility functions for the DCF calculator application.
"""
import pandas as pd

def safe_get(df, row_names, column_index=0):
    """
    Safely retrieve values from financial statement dataframes.
    
    Parameters:
    - df: DataFrame containing financial data
    - row_names: String or list of strings representing possible row names
    - column_index: Column index to retrieve (default is 0 for most recent period)
    
    Returns:
    - Value if found, 0 otherwise
    """
    if isinstance(row_names, str):
        row_names = [row_names]
    
    if df.empty or len(df.columns) <= column_index:
        return 0
    
    for name in row_names:
        if name in df.index:
            value = df.loc[name].iloc[column_index]
            if pd.notnull(value) and value != 0:
                return value
    
    return 0

def safe_get_multi(df, possible_names, column_index=0):
    """
    Get value from DataFrame with multiple possible row names.
    
    Parameters:
    - df: DataFrame containing financial data
    - possible_names: String or list of strings representing possible row names
    - column_index: Column index to retrieve (default is 0 for most recent period)
    
    Returns:
    - Value if found, 0 otherwise
    """
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

def calculate_historical_ratios(history, income_stmt, balance_sheet, shares_outstanding):
    """
    Calculate historical P/E and P/B ratios.
    
    Parameters:
    - history: Historical price data
    - income_stmt: Income statement data
    - balance_sheet: Balance sheet data
    - shares_outstanding: Current shares outstanding
    
    Returns:
    - pe_ratio_history: Historical P/E ratios
    - pb_ratio_history: Historical P/B ratios
    - pe_stats: Statistical summary of P/E ratios
    - pb_stats: Statistical summary of P/B ratios
    """
    # Extract historical prices
    if history.empty:
        return {}, {}, {}, {}
    
    # Create a copy of the history DataFrame to avoid modifying the original
    hist_copy = history.copy()
    
    # Calculate annual EPS and book value per share for each year
    pe_ratio_history = {}
    pb_ratio_history = {}

    # Get available years in the data
    if not income_stmt.empty and len(income_stmt.columns) > 0:
        years = [col.year for col in income_stmt.columns]
        
        for year in years:
            # Get annual net income for the year
            year_income = None
            for col in income_stmt.columns:
                if col.year == year and 'Net Income' in income_stmt.index:
                    year_income = income_stmt.loc['Net Income', col]
                    break
                    
            # Get annual equity for the year
            year_equity = None
            for col in balance_sheet.columns:
                if col.year == year and 'Total Equity' in balance_sheet.index:
                    year_equity = balance_sheet.loc['Total Equity', col]
                    break
            
            # Filter history for the specific year
            year_prices = hist_copy[hist_copy.index.year == year]
            
            if not year_prices.empty and year_income is not None and year_income > 0:
                # Calculate EPS for the year
                # Note: This is an approximation as historical shares outstanding may differ
                year_eps = year_income / shares_outstanding
                
                # Calculate average P/E ratio for the year
                avg_price = year_prices['Close'].mean()
                pe_ratio = avg_price / year_eps
                
                # Store in history dictionary
                pe_ratio_history[year] = pe_ratio
            
            if not year_prices.empty and year_equity is not None and year_equity > 0:
                # Calculate book value per share for the year
                year_bvps = year_equity / shares_outstanding
                
                # Calculate average P/B ratio for the year
                avg_price = year_prices['Close'].mean()
                pb_ratio = avg_price / year_bvps
                
                # Store in history dictionary
                pb_ratio_history[year] = pb_ratio
    
    # Calculate statistical summaries if enough data
    pe_stats = {}
    pb_stats = {}
    
    if len(pe_ratio_history) > 0:
        pe_values = list(pe_ratio_history.values())
        pe_values = [v for v in pe_values if v > 0 and v < 200]  # Filter out extreme values
        
        if pe_values:
            pe_stats = {
                'min': min(pe_values),
                'max': max(pe_values),
                'avg': sum(pe_values) / len(pe_values),
                'median': sorted(pe_values)[len(pe_values) // 2]
            }
    
    if len(pb_ratio_history) > 0:
        pb_values = list(pb_ratio_history.values())
        pb_values = [v for v in pb_values if v > 0 and v < 20]  # Filter out extreme values
        
        if pb_values:
            pb_stats = {
                'min': min(pb_values),
                'max': max(pb_values),
                'avg': sum(pb_values) / len(pb_values),
                'median': sorted(pb_values)[len(pb_values) // 2]
            }
    
    return pe_ratio_history, pb_ratio_history, pe_stats, pb_stats
