"""
Visualization functions for the DCF calculator application.
"""
import streamlit as st
import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots

def create_sensitivity_analysis(initial_fcf, growth_rate, terminal_growth_rate, wacc, forecast_years, net_debt, shares_outstanding, calculate_dcf_function, current_price=None):
    """
    Create a sensitivity analysis visualization for DCF model.
    All rates (growth, terminal, wacc) are expected as decimals (e.g., 0.05 for 5%).
    
    Parameters:
    - initial_fcf: Initial free cash flow
    - growth_rate: Growth rate during forecast period (decimal form)
    - terminal_growth_rate: Terminal growth rate (percentage form)
    - wacc: Weighted average cost of capital (percentage form)
    - forecast_years: Number of years in forecast period
    - net_debt: Net debt
    - shares_outstanding: Number of shares outstanding
    - calculate_dcf_function: Function to calculate DCF model
    - current_price: Current stock price (optional)
    
    Returns:
    - sensitivity_table: Pandas DataFrame with sensitivity analysis results
    - fig: Plotly figure object with heatmap
    """
    import pandas as pd
    import plotly.graph_objects as go
    import numpy as np
    
    # Sensitivity ranges (in decimal)
    base_wacc = wacc
    base_terminal_growth = terminal_growth_rate
    
    # 1. 성장률 범위 설정 (0% ~ 15%)
    min_growth = 0.0
    max_growth = 0.15  # 15%로 상향 조정
    growth_step = 0.01  # 1% 단위
    
    # 2. WACC 범위 설정 (성장률 각 값에 대해 최소 1% 높은 값부터 시작)
    # 각 성장률에 대해 해당하는 WACC 범위를 동적으로 생성
    growth_values = [round(g, 4) for g in np.arange(min_growth, max_growth + growth_step/2, growth_step)]
    
    # 3. WACC 값 생성 (기본 WACC를 중심으로 ±15% 범위에서 생성)
    wacc_values_dict = {}
    wacc_range = 0.15  # WACC 범위 (±15%)
    wacc_step = 0.01   # 1% 단위
    
    # 기본 WACC를 중심으로 범위 생성 (최소 1% 단위로 조정)
    min_wacc = max(0.01, round(base_wacc - wacc_range, 2))
    max_wacc = round(base_wacc + wacc_range, 2)
    
    # 모든 성장률에 대해 동일한 WACC 범위 사용 (성장률과의 관계는 계산 시점에 확인)
    common_wacc_values = [round(w, 4) for w in np.arange(min_wacc, max_wacc + wacc_step/2, wacc_step)]
    
    # 각 성장률에 대해 WACC가 성장률보다 최소 1% 높은 값들만 포함
    for g in growth_values:
        valid_waccs = [w for w in common_wacc_values if w > g + 0.0099]  # 부동소수점 오차 고려
        if valid_waccs:
            wacc_values_dict[g] = valid_waccs
        else:
            # 유효한 WACC가 없는 경우 성장률 + 1%를 추가
            min_valid_wacc = round(g + 0.01, 2)
            wacc_values_dict[g] = [min_valid_wacc] + [w for w in common_wacc_values if w > min_valid_wacc]
    
    # 4. 모든 WACC 값 수집 및 정렬 (중복 제거)
    all_wacc_values = sorted(list(set([w for w_list in wacc_values_dict.values() for w in w_list])))
    
    # 기본 WACC가 범위에 없으면 추가
    if base_wacc not in all_wacc_values:
        all_wacc_values.append(round(base_wacc, 4))
        all_wacc_values.sort()
    
    # 5. 기본 성장률이 범위 내에 없으면 추가
    if base_terminal_growth not in growth_values:
        growth_values.append(round(base_terminal_growth, 4))
    
    # 6. 정렬 및 중복 제거
    growth_values = sorted(list(set(growth_values)))
    wacc_values = sorted(list(set(all_wacc_values)))
    
    # 7. WACC가 항상 성장률보다 최소 1%는 높도록 보장 (이미 위에서 처리됨)
    
    # Table headers (show as percent)
    column_headers = [f"{g*100:.2f}%" for g in growth_values]
    row_headers = [f"{w*100:.2f}%" for w in wacc_values]
    sensitivity_table = pd.DataFrame(index=row_headers, columns=column_headers)
    heatmap_data = []
    
    # 사전에 모든 DCF 결과를 계산하여 저장
    dcf_results = {}
    
    # 1. 먼저 모든 유효한 조합에 대해 DCF 계산
    for i, w in enumerate(wacc_values):
        for j, g in enumerate(growth_values):
            if w > g:  # WACC가 성장률보다 클 때만 계산
                try:
                    result = calculate_dcf_function(
                        initial_fcf,
                        growth_rate,
                        g,
                        w,
                        forecast_years,
                        10,  # terminal years
                        net_debt,
                        shares_outstanding
                    )
                    if isinstance(result, dict) and "fair_value_per_share" in result:
                        dcf_results[(i, j)] = result["fair_value_per_share"]
                    else:
                        dcf_results[(i, j)] = None
                except Exception:
                    dcf_results[(i, j)] = None
    
    # 2. 계산된 결과를 기반으로 테이블 및 히트맵 데이터 생성
    for i, w in enumerate(wacc_values):
        row_data = []
        for j, g in enumerate(growth_values):
            if w <= g:
                # WACC가 성장률 이하인 경우, 인접한 유효한 값으로 보간
                sensitivity_table.iloc[i, j] = "N/A"
                
                # 인접한 유효한 값 찾기
                valid_value = None
                # 1. 같은 WACC에서 더 높은 성장률의 유효한 값 찾기
                for k in range(j+1, len(growth_values)):
                    if (i, k) in dcf_results and dcf_results[(i, k)] is not None:
                        valid_value = dcf_results[(i, k)]
                        break
                # 2. 같은 성장률에서 더 낮은 WACC의 유효한 값 찾기
                if valid_value is None:
                    for k in range(i-1, -1, -1):
                        if (k, j) in dcf_results and dcf_results[(k, j)] is not None:
                            valid_value = dcf_results[(k, j)]
                            break
                # 3. 대각선 방향으로 가장 가까운 유효한 값 찾기
                if valid_value is None:
                    for k in range(1, max(len(wacc_values), len(growth_values))):
                        found = False
                        for di, dj in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                            ni, nj = i + di*k, j + dj*k
                            if 0 <= ni < len(wacc_values) and 0 <= nj < len(growth_values):
                                if (ni, nj) in dcf_results and dcf_results[(ni, nj)] is not None:
                                    valid_value = dcf_results[(ni, nj)]
                                    found = True
                                    break
                        if found:
                            break
                
                if valid_value is not None:
                    sensitivity_table.iloc[i, j] = f"${valid_value:.2f}*"
                    row_data.append(valid_value)
                else:
                    row_data.append(None)
            else:
                # 정상적인 경우
                if (i, j) in dcf_results and dcf_results[(i, j)] is not None:
                    fair_value = dcf_results[(i, j)]
                    sensitivity_table.iloc[i, j] = f"${fair_value:.2f}"
                    row_data.append(fair_value)
                else:
                    sensitivity_table.iloc[i, j] = "Error"
                    row_data.append(None)
        heatmap_data.append(row_data)
    
    # Identify base case values to highlight
    base_row_idx = None
    for i, w in enumerate(wacc_values):
        if abs(w - base_wacc) < 0.01:  # Close enough to base WACC
            base_row_idx = i
            break
    
    base_col_idx = None
    for j, g in enumerate(growth_values):
        if abs(g - base_terminal_growth) < 0.01:  # Close enough to base terminal growth
            base_col_idx = j
            break
    
    # Format sensitivity table for display
    # Use CSS styling to improve the display
    styled_table = sensitivity_table.copy()
    
    # Apply styling to highlight the base case
    if base_row_idx is not None and base_col_idx is not None:
        orig_value = styled_table.iloc[base_row_idx, base_col_idx]
        if orig_value != "N/A" and orig_value != "Error":
            styled_table.iloc[base_row_idx, base_col_idx] = f"<b style='color: #1E88E5; background-color: rgba(30, 136, 229, 0.1);'>{orig_value}</b>"
    
    # Clean up the heatmap data to handle invalid values better
    # Replace None with NaN for better heatmap display
    for i in range(len(heatmap_data)):
        for j in range(len(heatmap_data[i]) if i < len(heatmap_data) else 0):
            if heatmap_data[i][j] is None:
                heatmap_data[i][j] = np.nan
    
    # Manually calculate zmin and zmax for colorscale
    valid_values = []
    for row in heatmap_data:
        for val in row:
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                valid_values.append(val)
    
    # Calculate zmin and zmax if we have valid values
    zmin = None
    zmax = None
    if valid_values:
        zmin = min(valid_values) * 0.8
        zmax = max(valid_values) * 1.2
    
    # Create the heatmap with improved formatting
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=column_headers,
        y=[f"{w:.2f}%" for w in wacc_values],
        colorscale='RdBu_r',
        colorbar=dict(
            title="Fair Value ($)",
            titleside="right",
            thickness=25,
            len=0.8,
            tickformat="$,.2f"
        ),
        hovertemplate="WACC: %{y}<br>Terminal Growth Rate: %{x}<br>Fair Value: $%{z:.2f}<extra></extra>",
        hoverongaps=False,
        zmin=zmin,
        zmax=zmax
    ))
    
    # Add current price markers if provided
    if current_price is not None and current_price > 0:
        # Find positions where fair value is close to current price
        current_price_points = []
        
        # First pass: find all values that are within 5% of current price
        price_threshold = current_price * 0.05  # 5% threshold
        
        for i, row in enumerate(heatmap_data):
            for j, val in enumerate(row):
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    if abs(val - current_price) < price_threshold:
                        current_price_points.append({
                            'row': i,
                            'col': j,
                            'wacc': wacc_values[i],
                            'growth': growth_values[j],
                            'value': val,
                            'diff': abs(val - current_price)
                        })
        
        # If no points are within threshold, find the closest points
        if not current_price_points:
            min_diff = float('inf')
            closest_point = None
            
            for i, row in enumerate(heatmap_data):
                for j, val in enumerate(row):
                    if val is not None and not (isinstance(val, float) and np.isnan(val)):
                        diff = abs(val - current_price)
                        if diff < min_diff:
                            min_diff = diff
                            closest_point = {
                                'row': i,
                                'col': j,
                                'wacc': wacc_values[i],
                                'growth': growth_values[j],
                                'value': val,
                                'diff': diff
                            }
            
            if closest_point:
                current_price_points.append(closest_point)
        
        # Sort points by closeness to current price and get top 3
        current_price_points.sort(key=lambda p: p['diff'])
        display_points = current_price_points[:min(3, len(current_price_points))]
        
        # Add markers for these points
        for point in display_points:
            fig.add_trace(go.Scatter(
                x=[column_headers[point['col']]],
                y=[f"{point['wacc']:.1f}%"],
                mode="markers",
                marker=dict(
                    symbol="circle",
                    size=15,
                    color="rgba(255, 140, 0, 0.9)",  # Orange
                    line=dict(width=2, color="black")
                ),
                name=f"Current Price (${current_price:.2f})",
                text=f"Fair Value: ${point['value']:.2f}",
                hovertemplate=
                    "<b>Current Price Point</b><br>" +
                    "WACC: %{y}<br>" +
                    "Growth: %{x}<br>" +
                    "Fair Value: ${:.2f}<br>".format(point['value']) +
                    "Current Price: ${:.2f}<br>".format(current_price) +
                    "Difference: {:.1f}%".format((point['value']/current_price - 1)*100) +
                    "<extra></extra>"
            ))
        
        # Add annotation for current price
        fig.add_annotation(
            text=f"Current Price: ${current_price:.2f}",
            x=0.01,
            y=0.01,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=14, color='rgba(255, 140, 0, 1)'),
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="rgba(255, 140, 0, 0.8)",
            borderwidth=2,
            borderpad=4,
            align="left"
        )
    
    # Use actual values directly instead of indices which might not match
    # Find the closest values in our grid to the actual input values
    actual_wacc = base_wacc  # This is the actual WACC value from inputs
    actual_growth = base_terminal_growth  # This is the actual terminal growth rate from inputs
    
    # Find the closest growth column and wacc row that actually exist in our table
    closest_growth_idx = None
    min_growth_diff = float('inf')
    for j, g in enumerate(growth_values):
        diff = abs(g - actual_growth)
        if diff < min_growth_diff:
            min_growth_diff = diff
            closest_growth_idx = j
    
    closest_wacc_idx = None
    min_wacc_diff = float('inf')
    for i, w in enumerate(wacc_values):
        diff = abs(w - actual_wacc)
        if diff < min_wacc_diff:
            min_wacc_diff = diff
            closest_wacc_idx = i
    
    # If we found valid indices, add the marker and annotation
    if closest_wacc_idx is not None and closest_growth_idx is not None:
        actual_wacc_str = f"{actual_wacc:.2f}%"
        actual_growth_str = f"{actual_growth:.2f}%"
        
        # Get the fair value at this point
        cell_value = None
        if (closest_wacc_idx < len(heatmap_data) and 
            closest_growth_idx < len(heatmap_data[closest_wacc_idx]) if closest_wacc_idx < len(heatmap_data) else 0):
            cell_value = heatmap_data[closest_wacc_idx][closest_growth_idx]
        
        # Only add the marker if we have a valid value
        if cell_value is not None and not (isinstance(cell_value, float) and np.isnan(cell_value)):
            # Add marker for base case with much more prominence
            fig.add_trace(go.Scatter(
                x=[column_headers[closest_growth_idx]],
                y=[f"{wacc_values[closest_wacc_idx]:.1f}%"],
                mode="markers+text",
                marker=dict(
                    symbol="star",
                    size=20,
                    color="#FF5722",  # Bright orange color
                    line=dict(color="white", width=2),
                    opacity=1.0
                ),
                text="Current Params",
                textposition="top center",
                textfont=dict(
                    family="Arial",
                    size=14,
                    color="black",
                    weight="bold"
                ),
                name="Current Values",
                hovertemplate="<b>Current Model Parameters</b><br>" +
                             f"WACC: {actual_wacc:.2f}%<br>" +
                             f"Growth Rate: {actual_growth:.2f}%<br>" +
                             f"Fair Value: ${cell_value:.2f}" +
                             "<extra></extra>"
            ))
            
            # Add an annotation arrow pointing to the current point
            fig.add_annotation(
                x=column_headers[closest_growth_idx],
                y=f"{wacc_values[closest_wacc_idx]:.1f}%",
                text=f"Current: WACC={actual_wacc:.1f}%, Growth={actual_growth:.1f}%",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="#FF5722",
                ax=40,
                ay=-40,
                font=dict(size=12, color="#333", family="Arial", weight="bold")
            )
    
    # Calculate fair value stats if current price is provided
    if current_price is not None and current_price > 0:
        # Flatten the heatmap data for analysis
        flat_values = [value for row in heatmap_data for value in row if value is not None and not (isinstance(value, float) and np.isnan(value))]
        
        if flat_values:
            min_value = min(flat_values)
            max_value = max(flat_values)
            avg_value = sum(flat_values) / len(flat_values)
            
            # Count scenarios above and below current price
            scenarios_above = sum(1 for value in flat_values if value > current_price)
            scenarios_below = sum(1 for value in flat_values if value < current_price)
            total_scenarios = len(flat_values)
            
            above_percent = scenarios_above / total_scenarios * 100 if total_scenarios > 0 else 0
            below_percent = scenarios_below / total_scenarios * 100 if total_scenarios > 0 else 0
            
            # Determine if stock is likely overvalued or undervalued
            valuation_status = ""
            if above_percent > 75:
                valuation_status = "Likely Undervalued"
                status_color = "green"
            elif above_percent > 50:
                valuation_status = "Possibly Undervalued"
                status_color = "lightgreen"
            elif below_percent > 75:
                valuation_status = "Likely Overvalued"
                status_color = "red"
            elif below_percent > 50:
                valuation_status = "Possibly Overvalued"
                status_color = "orange"
            else:
                valuation_status = "Fairly Valued"
                status_color = "blue"
            
            # Create annotations for statistics
            stats_annotations = [
                dict(
                    x=0.5,
                    y=1.12,
                    xref="paper",
                    yref="paper",
                    text="Higher terminal growth rates and lower WACC values (blue regions) result in higher fair values",
                    showarrow=False,
                    font=dict(size=12, color="#555"),
                    bgcolor="rgba(248,249,250,0.8)",
                    bordercolor="#ddd",
                    borderwidth=1,
                    borderpad=4
                ),
                dict(
                    x=0.01,
                    y=-0.17,
                    xref="paper",
                    yref="paper",
                    text=f"<b>Sensitivity Analysis Results:</b><br>" + 
                         f"• Range: ${min_value:.2f} to ${max_value:.2f}<br>" +
                         f"• Average Fair Value: ${avg_value:.2f}<br>" +
                         f"• Current Price: ${current_price:.2f}<br>" +
                         f"• Scenarios above current price: {above_percent:.1f}%<br>" +
                         f"• Assessment: <span style='color:{status_color}'>{valuation_status}</span>",
                    showarrow=False,
                    align="left",
                    font=dict(size=12),
                    bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="#ddd",
                    borderwidth=1,
                    borderpad=6
                )
            ]
        else:
            stats_annotations = [
                dict(
                    x=0.5,
                    y=1.12,
                    xref="paper",
                    yref="paper",
                    text="Higher terminal growth rates and lower WACC values (blue regions) result in higher fair values",
                    showarrow=False,
                    font=dict(size=12, color="#555"),
                    bgcolor="rgba(248,249,250,0.8)",
                    bordercolor="#ddd",
                    borderwidth=1,
                    borderpad=4
                )
            ]
    else:
        stats_annotations = [
            dict(
                x=0.5,
                y=1.12,
                xref="paper",
                yref="paper",
                text="Higher terminal growth rates and lower WACC values (blue regions) result in higher fair values",
                showarrow=False,
                font=dict(size=12, color="#555"),
                bgcolor="rgba(248,249,250,0.8)",
                bordercolor="#ddd",
                borderwidth=1,
                borderpad=4
            )
        ]
    
    # Update layout with improved styling
    fig.update_layout(
        title={
            'text': "Sensitivity Analysis: WACC vs Terminal Growth Rate",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 20, 'color': '#333'}
        },
        xaxis_title={
            'text': "Terminal Growth Rate",
            'font': {'size': 14, 'color': '#333'}
        },
        yaxis_title={
            'text': "WACC",
            'font': {'size': 14, 'color': '#333'}
        },
        yaxis=dict(
            autorange="reversed",  # Put lower WACC at top
            gridcolor='rgba(220,220,220,0.5)'
        ),
        xaxis=dict(
            gridcolor='rgba(220,220,220,0.5)'
        ),
        margin=dict(l=70, r=50, t=100, b=120),  # Increased bottom margin for stats
        plot_bgcolor='rgba(248,249,250,1)',
        annotations=stats_annotations,
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        ),
        height=600  # Increase height for better visualization and stats
    )
    
    return sensitivity_table, fig

def create_dcf_visualization(dcf_result, current_price, ticker, forecast_years=5):
    """
    Create a visualization of the DCF model results.
    
    Parameters:
    - dcf_result: Dictionary containing DCF model results
    - current_price: Current stock price
    - ticker: Stock ticker symbol
    - forecast_years: Number of years in explicit forecast period
    
    Returns:
    - Plotly figure object
    """
    # Extract data from DCF result
    cash_flows = dcf_result["cash_flows"]
    pv_cash_flows = dcf_result["pv_cash_flows"]
    terminal_value = dcf_result["terminal_value"]
    pv_terminal_value = dcf_result["pv_terminal_value"]
    equity_value = dcf_result["equity_value"]
    fair_value = dcf_result["fair_value_per_share"]
    
    # Create subplot figure with 2 rows
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("DCF Model Components", "Enterprise Value Breakdown"),
        vertical_spacing=0.15,
        specs=[[{"type": "bar"}], [{"type": "pie"}]]
    )
    
    # Define years for x-axis
    years = [f"Year {i+1}" for i in range(forecast_years)]
    years.append("Terminal<br>Value")
    
    # Prepare data for bar chart (cash flows)
    bar_values = cash_flows + [terminal_value]
    pv_values = pv_cash_flows + [pv_terminal_value]
    
    # Add bar chart for cash flows
    fig.add_trace(
        go.Bar(
            x=years,
            y=bar_values,
            name="Future Value",
            marker_color="lightblue",
            opacity=0.7,
            text=[f"${v/1e6:.1f}M" for v in bar_values],
            textposition="auto"
        ),
        row=1, col=1
    )
    
    # Add bar chart for present values
    fig.add_trace(
        go.Bar(
            x=years,
            y=pv_values,
            name="Present Value",
            marker_color="darkblue",
            text=[f"${v/1e6:.1f}M" for v in pv_values],
            textposition="auto"
        ),
        row=1, col=1
    )
    
    # Calculate percentages for pie chart
    total_pv_explicit = sum(pv_cash_flows)
    total_pv = total_pv_explicit + pv_terminal_value
    
    explicit_percentage = (total_pv_explicit / total_pv) * 100 if total_pv > 0 else 0
    terminal_percentage = (pv_terminal_value / total_pv) * 100 if total_pv > 0 else 0
    
    # Add pie chart for value breakdown
    fig.add_trace(
        go.Pie(
            labels=["Explicit Forecast Period", "Terminal Value"],
            values=[explicit_percentage, terminal_percentage],
            textinfo="label+percent",
            insidetextorientation="radial",
            marker=dict(colors=["royalblue", "lightblue"]),
            hole=0.4
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        title_text=f"DCF Valuation Model for {ticker}",
        barmode="group",
        bargap=0.15,
        bargroupgap=0.1,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    return fig

def create_wacc_visualization(wacc_components):
    """
    Create a visualization for WACC components.
    
    Parameters:
    - wacc_components: Dictionary containing WACC components
    
    Returns:
    - Plotly figure object
    """
    # Extract data
    wacc = wacc_components.get("wacc", 0) * 100
    cost_of_equity = wacc_components.get("cost_of_equity", 0) * 100
    cost_of_debt = wacc_components.get("cost_of_debt", 0) * 100
    tax_rate = wacc_components.get("tax_rate", 0) * 100
    weight_of_equity = wacc_components.get("weight_of_equity", 0) * 100
    weight_of_debt = wacc_components.get("weight_of_debt", 0) * 100
    beta = wacc_components.get("beta", 1.0)
    
    after_tax_cost_of_debt = cost_of_debt * (1 - wacc_components.get("tax_rate", 0))
    
    # Create waterfall chart data
    fig = go.Figure(go.Waterfall(
        name="WACC Calculation",
        orientation="v",
        measure=["relative", "relative", "total"],
        x=["Equity<br>" + f"{weight_of_equity:.1f}%", 
           "Debt (After Tax)<br>" + f"{weight_of_debt:.1f}%", 
           "WACC"],
        textposition="outside",
        text=[f"{cost_of_equity:.2f}% × {weight_of_equity/100:.2f}",
              f"{after_tax_cost_of_debt:.2f}% × {weight_of_debt/100:.2f}",
              f"{wacc:.2f}%"],
        y=[cost_of_equity * weight_of_equity / 100,
           after_tax_cost_of_debt * weight_of_debt / 100,
           0],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "rgba(219, 64, 82, 0.7)"}},
        increasing={"marker": {"color": "rgba(50, 171, 96, 0.7)"}},
        totals={"marker": {"color": "royalblue"}}
    ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': "WACC Components Breakdown",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        showlegend=False,
        height=400,
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    return fig
