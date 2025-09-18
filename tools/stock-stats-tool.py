#!/usr/bin/env python3
"""
Stock Statistics and Financials Gathering Tool.

This script provides detailed financial information for a specific stock ticker.
It is designed to be called by an AI assistant or used manually to gather in-depth data for stock research.
"""

import yfinance as yf
import json
import sys
import argparse
import inspect
import math
from typing import Dict, Any

# --- Decorator and list for exposing functions as modes ---
EXPOSED_MODES = []

def expose_as_mode(func):
    """A decorator that registers a function to be exposed as a command-line mode."""
    EXPOSED_MODES.append(func)
    return func

# --- Self-Description Functions ---

def get_tool_definition():
    """
    Returns a JSON object describing the tool's purpose and parameters for an AI dispatcher.
    """
    definition = {
        "name": "stock-stats-tool.py",
        "description": "This tool retrieves detailed financial statistics, statements, or a human-readable performance summary for a specific stock ticker.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol to research, for example: 'NVDA' for Nvidia or 'AAPL' for Apple."
                },
                "mode": {
                    "type": "string",
                    "description": "The specific data to retrieve. Options include 'get-performance-summary', 'get-key-statistics', etc."
                }
            },
            "required": ["ticker", "mode"]
        }
    }
    return json.dumps(definition, indent=2)

def get_tool_options() -> str:
    """
    Dynamically generates a list of selectable modes for the UI based on
    functions marked with the @expose_as_mode decorator.
    """
    options = []
    for func in EXPOSED_MODES:
        mode_arg = func.__name__.replace('_', '-')
        docstring = inspect.getdoc(func)
        friendly_name = docstring.strip().split('\n')[0] if docstring else mode_arg
        options.append({
            "name": friendly_name,
            "args": f"--mode {mode_arg}"
        })
    options.append({
        "name": "Get All Stock Information (JSON)",
        "args": "--mode all"
    })
    return json.dumps(options, indent=2)

# --- Data Cleaning and Formatting Helpers ---

def format_financial_dataframe(df):
    """
    Converts a pandas DataFrame's Timestamp columns to string keys
    to make it compatible with JSON serialization.
    """
    if df is None or df.empty:
        return {}
    df_copy = df.copy()
    df_copy.columns = [col.strftime('%Y-%m-%d') for col in df_copy.columns]
    return df_copy.to_dict()

def clean_nan_values(obj):
    """
    Recursively traverses a data structure and replaces float('nan')
    with None, which serializes to JSON 'null'.
    """
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(elem) for elem in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

# --- Data Gathering Functions ---

# --- THIS IS THE MODIFIED FUNCTION ---
@expose_as_mode
def get_performance_summary(ticker_symbol: str) -> str:
    """Research Specific Stock (Human-Readable Summary)"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        hist = ticker.history(period="5d")

        if hist.empty:
            return f"Error: No historical data found for ticker '{ticker_symbol}'."

        company_name = info.get('longName', ticker_symbol.upper())
        current_price = hist['Close'].iloc[-1]
        start_price = hist['Close'].iloc[0]
        change = current_price - start_price
        change_pct = (change / start_price) * 100
        high_52w = info.get('fiftyTwoWeekHigh', 'N/A')
        low_52w = info.get('fiftyTwoWeekLow', 'N/A')
        market_cap = info.get('marketCap', 0)
        news = ticker.news[:4]

        summary = f"Performance Summary for {company_name} ({ticker_symbol.upper()})\n"
        summary += "--------------------------------------------------\n"
        summary += f"- Current Price: ${current_price:,.2f}\n"
        summary += f"- 5-Day Change: ${change:,.2f} ({change_pct:.2f}%)\n"
        summary += f"- 52-Week Range: ${low_52w:,.2f} - ${high_52w:,.2f}\n"
        summary += f"- Market Cap: ${market_cap:,.0f}\n"

        if news:
            summary += "\nRecent Headlines:\n"
            for article in news:
                # --- THE FIX IS HERE ---
                # Safely get the title using .get(). If 'title' doesn't exist, it returns None.
                title = article.get('title')
                # Only add the headline to the summary if a title was successfully found.
                if title:
                    summary += f"  - {title}\n"
        
        return summary

    except Exception as e:
        return f"An error occurred while researching {ticker_symbol}: {str(e)}"

@expose_as_mode
def get_stock_financials(ticker_symbol: str) -> Dict[str, Any]:
    """Fetches annual and quarterly financial statements (JSON)."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        financials = {
            "annual_income_statement": format_financial_dataframe(ticker.income_stmt),
            "quarterly_income_statement": format_financial_dataframe(ticker.quarterly_income_stmt),
            "annual_balance_sheet": format_financial_dataframe(ticker.balance_sheet),
            "quarterly_balance_sheet": format_financial_dataframe(ticker.quarterly_balance_sheet),
            "annual_cash_flow": format_financial_dataframe(ticker.cashflow),
            "quarterly_cash_flow": format_financial_dataframe(ticker.quarterly_cashflow)
        }
        return financials
    except Exception as e:
        return {"error": f"Could not retrieve financial statements for {ticker_symbol}: {str(e)}"}

@expose_as_mode
def get_key_statistics(ticker_symbol: str) -> Dict[str, Any]:
    """Retrieves key financial ratios and statistics (JSON)."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        stats = {
            "market_cap": info.get('marketCap'), "enterprise_value": info.get('enterpriseValue'),
            "trailing_pe": info.get('trailingPE'), "forward_pe": info.get('forwardPE'),
            "peg_ratio": info.get('pegRatio'), "price_to_sales": info.get('priceToSalesTrailing12Months'),
            "price_to_book": info.get('priceToBook'), "enterprise_to_revenue": info.get('enterpriseToRevenue'),
            "enterprise_to_ebitda": info.get('enterpriseToEbitda'), "beta": info.get('beta'),
            "earnings_per_share": info.get('trailingEps'), "dividend_yield": info.get('dividendYield'),
            "profit_margins": info.get('profitMargins'), "return_on_equity": info.get('returnOnEquity'),
        }
        return stats
    except Exception as e:
        return {"error": f"Could not retrieve key statistics for {ticker_symbol}: {str(e)}"}

@expose_as_mode
def get_analyst_recommendations(ticker_symbol: str) -> Dict[str, Any]:
    """Fetches the latest analyst recommendations (JSON)."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        recommendations = ticker.recommendations
        if recommendations is not None and not recommendations.empty:
            return recommendations.tail(5).to_dict('records')
        return {"message": "No analyst recommendations found."}
    except Exception as e:
        return {"error": f"Could not retrieve analyst recommendations for {ticker_symbol}: {str(e)}"}

# --- Main Execution Logic ---

def main():
    """Main function to parse arguments and execute the appropriate data gathering function."""
    if '--get-definition' in sys.argv:
        print(get_tool_definition())
        sys.exit(0)

    if '--get-options' in sys.argv:
        print(get_tool_options())
        sys.exit(0)

    parser = argparse.ArgumentParser(description="A tool to gather detailed financial statistics for a specific stock.")
    parser.add_argument("--ticker", type=str, required=True, help="The stock ticker symbol to analyze (e.g., NVDA, AAPL).")
    parser.add_argument("--mode", type=str, default="all", help="The type of data to retrieve.")
    args = parser.parse_args()

    MODE_MAP = {func.__name__.replace('_', '-'): func for func in EXPOSED_MODES}
    
    if args.mode == "all":
        print(f"Gathering all financial data for {args.ticker}...")
        output_data = {
            "ticker": args.ticker.upper(),
            "key_statistics": get_key_statistics(args.ticker),
            "analyst_recommendations": get_analyst_recommendations(args.ticker),
            "financial_statements": get_stock_financials(args.ticker)
        }
        cleaned_output = clean_nan_values(output_data)
        print(json.dumps(cleaned_output, indent=2, default=str))

    elif args.mode in MODE_MAP:
        function_to_call = MODE_MAP[args.mode]
        print(f"Executing: {args.mode.replace('-', ' ')} for {args.ticker}...")
        result = function_to_call(args.ticker)

        if isinstance(result, str):
            print(result)
        else:
            cleaned_output = clean_nan_values(result)
            print(json.dumps(cleaned_output, indent=2, default=str))
    else:
        print(f"Error: Invalid mode '{args.mode}'. Valid modes are: {list(MODE_MAP.keys()) + ['all']}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()