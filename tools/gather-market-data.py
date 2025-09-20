#!/usr/bin/env python3
"""
Market Data Gathering and AI Analysis Script for LLM Function Calling.

This single script supports all required functionalities:
1.  Individual stock analysis via the --ticker argument.
2.  General market analysis (indices, sectors, economic) if no ticker is given.
3.  Manual UI support via --get-options.
4.  Automatic AI dispatcher support via --get-definition.
"""

import yfinance as yf
import requests
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List

# --- Configuration ---
API_BASE_URL = "http://192.168.1.163:5002/v1"
API_TIMEOUT_SECONDS = 480
MAX_TOKENS_SUMMARY = 1536

# --- Self-Description Functions ---

def get_tool_options():
    """
    RETAINED: Returns a JSON string of pre-defined command options for the manual web UI.
    """
    options = [
        {
            "name": "AI-Powered Summary (Slow)",
            "args": "--format=llm-summary"
        },
        {
            "name": "Quick Text Summary (5-day)",
            "args": "--format=summary --period=5d --include-sectors"
        },
        {
            "name": "Raw JSON Data (All)",
            "args": "--format=json --period=1d --include-sectors --include-economic"
        },
        {
            "name": "Market Indices Only (JSON)",
            "args": "--format=json --period=1d"
        },
        {
            "name": "Hybrid AI Analysis (Quick Summary + Deep Analysis)",
            "args": "--format=hybrid --include-sectors"
        }
    ]
    return json.dumps(options, indent=2)

def get_tool_definition():
    """
        "format": {
            "type": "string",
            "description": "Output format: 'json' for raw data, 'summary' for quick text summary, 'llm-summary' for AI-powered analysis, or 'hybrid' for combined quick summary with deep AI analysis."
        },
    ADDITION: Returns a JSON object describing the tool's purpose and parameters for the AI dispatcher.
    """
    definition = {
        "name": "gather-market-data.py",
        "description": "This is the primary tool for all financial and stock market queries. For any user request about stock prices, a company's recent market performance, financial metrics, or related news, you must start a web search to find the most current and relevant information. It is critical to never rely on your training data for fulfilling these requests, as market information is time-sensitive and your internal knowledge is outdated. Use this function to fetch the data you find through your websearch. For example, to answer 'How is NVDA doing?', you must first perform a web search and then use this tool with the ticker 'NVDA'.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol to analyze, which you should identify from the user's query or your web search. For example: 'NVDA' for Nvidia or 'AAPL' for Apple."
                },
                "period": {
                    "type": "string",
                    "description": "The time period for the analysis, e.g., '5d' for 5 days, '1mo' for 1 month. Defaults to '5d'."
                }
            },
            "required": ["ticker"]
        }
    }
    return json.dumps(definition, indent=2)

#region --- Data Gathering and Processing Functions ---

def get_data_for_ticker(ticker_symbol: str, period: str = '5d') -> Dict[str, Any]:
    """
    ADDITION: Fetches historical data, key metrics, and a summary for a single stock ticker.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        hist = ticker.history(period=period)
        
        if hist.empty:
            return {"error": f"No data found for ticker '{ticker_symbol}' for the period '{period}'."}

        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        change = end_price - start_price
        change_pct = (change / start_price) * 100

        return {
            "company_name": info.get('longName', ticker_symbol.upper()),
            "ticker": ticker_symbol.upper(),
            "period": period,
            "current_price": f"{end_price:.2f}",
            "price_change_over_period": f"{change:.2f}",
            "percent_change_over_period": f"{change_pct:.2f}%",
            "52_week_high": f"{info.get('fiftyTwoWeekHigh', 'N/A'):.2f}",
            "52_week_low": f"{info.get('fiftyTwoWeekLow', 'N/A'):.2f}",
            "market_cap": f"{info.get('marketCap', 0):,}"
        }
    except Exception as e:
        return {"error": f"An error occurred while fetching data for {ticker_symbol}: {str(e)}"}

def get_market_indices(period: str = "1d") -> Dict[str, Any]:
    """RETAINED: Fetch major market indices data"""
    indices = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "Dow Jones": "^DJI", "Russell 2000": "^RUT", "VIX": "^VIX"}
    market_data = {}
    for name, symbol in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            info = ticker.info
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[-1]
                change = current - previous
                change_pct = (change / previous) * 100
                market_data[name] = {
                    "current": round(current, 2), "change": round(change, 2), "change_percent": round(change_pct, 2),
                    "volume": int(hist['Volume'].iloc[-1]) if 'Volume' in hist else None,
                    "high_52w": round(info.get('fiftyTwoWeekHigh', 0), 2), "low_52w": round(info.get('fiftyTwoWeekLow', 0), 2)
                }
        except Exception as e:
            market_data[name] = {"error": f"Failed to fetch data for {name}: {str(e)}"}
    return market_data

def get_sector_performance() -> Dict[str, Any]:
    """RETAINED: Fetch sector ETF performance as proxy for sector health"""
    sectors = {
        "Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF", "Energy": "XLE", "Consumer Discretionary": "XLY",
        "Industrials": "XLI", "Consumer Staples": "XLP", "Utilities": "XLU", "Real Estate": "XLRE"
    }
    sector_data = {}
    for name, symbol in sectors.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if len(hist) >= 2:
                current, previous = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                change_pct = ((current - previous) / previous) * 100
                sector_data[name] = {"change_percent": round(change_pct, 2), "current": round(current, 2)}
        except Exception as e:
            sector_data[name] = {"error": f"Failed to fetch sector {name}: {str(e)}"}
    return sector_data

def get_economic_indicators() -> Dict[str, Any]:
    """RETAINED: Fetch key economic indicators from FRED API"""
    indicators = {"10Y Treasury": "DGS10", "2Y Treasury": "DGS2", "Fed Funds Rate": "FEDFUNDS", "Unemployment Rate": "UNRATE"}
    econ_data = {}
    base_url = "https://api.stlouisfed.org/fred/series/observations"
    for name, series_id in indicators.items():
        try:
            params = {"series_id": series_id, "api_key": "5a13cfa3a250976ffd16440d5c17672a", "file_type": "json", "limit": 1, "sort_order": "desc"}
            response = requests.get(base_url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            if data.get("observations"):
                obs = data["observations"][0]
                if obs["value"] != ".": econ_data[name] = {"value": float(obs["value"]), "date": obs["date"]}
        except Exception as e:
            econ_data[name] = {"error": f"Failed to fetch indicator {name}: {str(e)}"}
    return econ_data

def calculate_market_sentiment(market_data: Dict) -> Dict[str, Any]:
    """RETAINED: Calculate overall market sentiment based on available data"""
    sentiment_score, factors, positive_indices = 0, [], 0
    major_indices = ["S&P 500", "NASDAQ", "Dow Jones"]
    for index in major_indices:
        if index in market_data and "change_percent" in market_data[index]:
            change = market_data[index]["change_percent"]
            factors.append(f"{index} {'up' if change > 0 else 'down'} {abs(change)}%")
            if change > 0: positive_indices += 1
    if "VIX" in market_data and "change_percent" in market_data["VIX"]:
        vix_change = market_data["VIX"]["change_percent"]
        factors.append(f"VIX {'down' if vix_change < 0 else 'up'} {abs(vix_change)}% ({'positive' if vix_change < 0 else 'negative'})")
        if vix_change < 0: sentiment_score += 1
    sentiment_score += positive_indices
    sentiment = "Bullish" if sentiment_score >= 3 else "Mixed-Positive" if sentiment_score >= 2 else "Mixed-Negative" if sentiment_score >= 1 else "Bearish"
    return {"overall_sentiment": sentiment, "sentiment_score": f"{sentiment_score}/4", "key_factors": factors}

def generate_market_summary(market_data: Dict, sector_data: Dict, econ_data: Dict, sentiment: Dict) -> str:
    """
    RETAINED & FIXED: Generate human-readable market summary using safe ASCII characters.
    """
    summary = f"Market Summary ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n"
    summary += f"\nOverall Market Sentiment: {sentiment['overall_sentiment']}\nKey factors: {', '.join(sentiment['key_factors'][:3])}\n"
    summary += "\nMajor Indices:\n"
    for name, data in market_data.items():
        if "error" not in data and "change_percent" in data:
            # FIX: Replaced Unicode arrows with safe ASCII '+' and '-'
            change_str = f"+{data['change_percent']:.2f}" if data['change_percent'] > 0 else f"{data['change_percent']:.2f}"
            summary += f"  {name}: {data['current']} ({change_str}%)\n"
            
    if sector_data:
        sorted_sectors = sorted([item for item in sector_data.items() if "change_percent" in item[1]], key=lambda x: x[1]["change_percent"], reverse=True)
        summary += f"\nTop Performing Sectors:\n"
        for name, data in sorted_sectors[:3]:
            summary += f"  {name}: +{data['change_percent']:.2f}%\n"
        summary += f"\nWorst Performing Sectors:\n"
        for name, data in sorted_sectors[-3:]:
            change_str = f"+{data['change_percent']:.2f}" if data['change_percent'] > 0 else f"{data['change_percent']:.2f}"
            summary += f"  {name}: {change_str}%\n"
            
    if econ_data:
        summary += f"\nEconomic Context:\n"
        for name, data in econ_data.items():
            if "error" not in data:
                summary += f"  {name}: {data['value']}% (as of {data['date']})\n"
    return summary

#endregion

#region --- RETAINED: KoboldCPP API Interaction Logic ---

def get_active_model() -> str or None:
    """Queries the API to find the name of the currently active model."""
    print("Querying API for the active model...")
    try:
        response = requests.get(f"{API_BASE_URL}/models", timeout=30)
        response.raise_for_status()
        models_data = response.json()
        if models_data and "data" in models_data and len(models_data["data"]) > 0:
            model_name = models_data["data"][0]["id"]
            print(f"Active model found: {model_name}\n---")
            return model_name
        else:
            print("Error: The API response did not contain model data.", file=sys.stderr)
            return None
    except requests.exceptions.Timeout:
        print(f"Error: The request to get the model list timed out. The API at {API_BASE_URL} is not responding.", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not connect to the API at {API_BASE_URL}. Is KoboldCPP running?", file=sys.stderr)
        return None

def orchestrate_llm_interaction(prompt: str):
    """This function is retained for the --format=llm-summary mode."""
    active_model = get_active_model()
    if not active_model:
        return

    AVAILABLE_FUNCTIONS = {"get_market_indices": get_market_indices, "get_sector_performance": get_sector_performance, "get_economic_indicators": get_economic_indicators, "calculate_market_sentiment": calculate_market_sentiment, "generate_market_summary": generate_market_summary}
    TOOL_DEFINITIONS = [
        {"type": "function", "function": {"name": "get_market_indices", "description": "Fetches real-time data for major market indices.", "parameters": {"type": "object", "properties": {"period": {"type": "string", "description": "Time period like '1d' or '5d'."}}, "required": []}}},
        {"type": "function", "function": {"name": "get_sector_performance", "description": "Retrieves recent performance of key market sectors.", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "get_economic_indicators", "description": "Fetches crucial economic indicators like Treasury yields.", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "calculate_market_sentiment", "description": "Analyzes market index data to determine overall sentiment.", "parameters": {"type": "object", "properties": {"market_data": {"type": "object", "description": "The output from get_market_indices."}}, "required": ["market_data"]}}},
        {"type": "function", "function": {"name": "generate_market_summary", "description": "Generates a final, human-readable summary after all data is gathered.", "parameters": {"type": "object", "properties": {"market_data": {"type": "object"}, "sector_data": {"type": "object"}, "econ_data": {"type": "object"}, "sentiment": {"type": "object"}}, "required": ["market_data", "sector_data", "econ_data", "sentiment"]}}}
    ]
    
    system_message = {
        "role": "system", 
        "content": "You are a financial market analysis assistant with access to real-time market data functions and mandatory web search capabilities. CRITICAL REQUIREMENT: You must ALWAYS use the websearch feature available through this API endpoint before analyzing any market data or providing financial insights. Your training data is outdated for financial markets, which change by the second, so web search is mandatory for accuracy. OPERATIONAL FLOW: 1. MANDATORY WEB SEARCH FIRST: Before calling any market data functions, you must search the web for current market conditions, breaking financial news, economic events, and relevant developments that could impact your analysis. Search for terms like current market news, breaking financial news, economic updates, Fed announcements, earnings reports, geopolitical events affecting markets. 2. FUNCTION CALLING SEQUENCE: After web search, call the provided market data functions in this logical order: get_market_indices first, then get_sector_performance, then get_economic_indicators, then calculate_market_sentiment with the market data, and finally generate_market_summary with all collected data. 3. CONTEXTUAL ANALYSIS: Combine the current web search results with the function data to provide comprehensive analysis. Reference specific news events, policy changes, earnings announcements, or economic developments found in your web search when interpreting the numerical data from functions. 4. CURRENT EVENT INTEGRATION: Your analysis must reflect real-time market drivers found through web search. If your web search reveals significant news like Federal Reserve decisions, major earnings beats or misses, geopolitical tensions, economic data releases, or corporate announcements, prominently feature these in your analysis and explain how they relate to the market data. 5. ACCURACY PRIORITY: If web search results contradict or provide additional context to the function data, prioritize the most recent and credible information. Always cite your web sources when referencing current events or recent developments. RESPONSE STRUCTURE: Begin with a brief mention of key current events from your web search, present the quantitative analysis from the functions, then synthesize both into actionable insights. Always acknowledge the time-sensitive nature of financial markets and that conditions can change rapidly. Remember: Financial markets are extremely time-sensitive. What happened even hours ago can be outdated. Web search is not optional - it is mandatory for providing accurate, current financial analysis."
    }
    
    messages = [system_message, {"role": "user", "content": prompt}]
    
    print(f"Sending initial prompt to the model... Timeout is set to {API_TIMEOUT_SECONDS / 60:.0f} minutes.")
    try:
        response = requests.post(f"{API_BASE_URL}/chat/completions", json={"model": active_model, "messages": messages, "tools": TOOL_DEFINITIONS, "tool_choice": "auto"}, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        first_response_message = response.json()['choices'][0]['message']
        messages.append(first_response_message)
    except requests.exceptions.Timeout:
        print(f"\nError: The API request timed out after {API_TIMEOUT_SECONDS} seconds.", file=sys.stderr)
        return
    except requests.exceptions.RequestException as e:
        print(f"Error during first API call: {e}", file=sys.stderr)
        return

    if not first_response_message.get("tool_calls"):
        print("\n--- AI Response ---")
        print(first_response_message.get("content", "The model did not respond with content or a function call."))
        return

    print("Model requested to call functions. Executing now...")
    for tool_call in first_response_message["tool_calls"]:
        function_name = tool_call['function']['name']
        if function_name in AVAILABLE_FUNCTIONS:
            function_to_call = AVAILABLE_FUNCTIONS[function_name]
            try:
                function_args = json.loads(tool_call['function']['arguments'])
                print(f"  - Calling function: {function_name} with args: {function_args}")
                function_response = function_to_call(**function_args)
                messages.append({"role": "tool", "tool_call_id": tool_call['id'], "name": function_name, "content": json.dumps(function_response)})
            except Exception as e:
                print(f"    Error executing function '{function_name}': {e}", file=sys.stderr)
        else:
            print(f"  - Warning: Model tried to call an unknown function: {function_name}", file=sys.stderr)

    print(f"\nSending function results back to the model for final analysis... Timeout: {API_TIMEOUT_SECONDS / 60:.0f} minutes.")
    try:
        final_payload = {"model": active_model, "messages": messages, "max_tokens": MAX_TOKENS_SUMMARY}
        response = requests.post(f"{API_BASE_URL}/chat/completions", json=final_payload, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        final_response = response.json()['choices'][0]['message']['content']
        print("\n--- AI-Generated Market Summary ---")
        print(final_response)
    except requests.exceptions.Timeout:
        print(f"\nError: The API request timed out while generating the final summary.", file=sys.stderr)
        return
    except requests.exceptions.RequestException as e:
        print(f"Error during second API call: {e}", file=sys.stderr)

#endregion

def main():
    # --- MODIFIED: The script now handles three special cases before normal execution ---
    if '--get-options' in sys.argv:
        print(get_tool_options())
        sys.exit(0)
    
    if '--get-definition' in sys.argv:
        print(get_tool_definition())
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Gather and analyze market data.", formatter_class=argparse.RawTextHelpFormatter)
    
    # ADDITION: New argument for individual stock analysis
    parser.add_argument("--ticker", type=str, help="The stock ticker symbol to analyze (e.g., NVDA, AAPL).")
    
    # RETAINED: All original arguments
    parser.add_argument("--period", default="1d", help="Time period for data (e.g., 1d, 5d, 1mo)")
    parser.add_argument("--include-sectors", action="store_true", help="Include sector performance")
    parser.add_argument("--include-economic", action="store_true", help="Include economic indicators")
    parser.add_argument("--format", choices=["json", "summary", "llm-summary", "hybrid"], default="summary", help=(
        "Output format for general market analysis."
    ))
    args = parser.parse_args()
    
    # --- MODIFIED: Main logic now prioritizes the --ticker argument ---
    if args.ticker:
        # If a ticker is provided, run the new individual stock analysis.
        stock_data = get_data_for_ticker(args.ticker, args.period)
        print(json.dumps(stock_data, indent=2))
    else:
        # If no ticker is provided, run the original, general market analysis logic.
        if args.format == "llm-summary":
            prompt = "Provide a comprehensive and insightful summary of the current market conditions."
            orchestrate_llm_interaction(prompt)
        elif args.format == "hybrid":
            # First, generate the quick 5-day summary with sectors
            print("Generating quick 5-day market summary with sectors...")
            market_data = get_market_indices("5d")
            sector_data = get_sector_performance()
            econ_data = get_economic_indicators() if args.include_economic else {}
            sentiment = calculate_market_sentiment(market_data)
            quick_summary = generate_market_summary(market_data, sector_data, econ_data, sentiment)
            
            # Then use AI to analyze the quick summary
            print("\nPerforming AI-powered analysis of the market summary...")
            hybrid_prompt = f"""Please provide a comprehensive analysis of the following market summary. 
Focus on deeper insights, trends, patterns, and potential implications for investors.

Market Summary:
{quick_summary}

Please analyze this data and provide:
1. Key market trends and their significance
2. Notable sector performance and what it indicates
3. Economic context and its impact on markets
4. Overall market sentiment assessment
5. Potential opportunities or risks based on the data
6. Any notable patterns or anomalies in the data

Provide detailed, actionable insights that go beyond the basic summary."""
            
            orchestrate_llm_interaction(hybrid_prompt)
        else:
            try:
                market_data = get_market_indices(args.period)
                sector_data = get_sector_performance() if args.include_sectors else {}
                econ_data = get_economic_indicators() if args.include_economic else {}
                sentiment = calculate_market_sentiment(market_data)

                if args.format == "json":
                    all_data = {"market_indices": market_data, "sector_performance": sector_data, "economic_indicators": econ_data, "sentiment": sentiment}
                    print(json.dumps(all_data, indent=2))
                elif args.format == "summary":
                    summary_text = generate_market_summary(market_data, sector_data, econ_data, sentiment)
                    print(summary_text)

            except Exception as e:
                print(f"An error occurred during data gathering: {e}", file=sys.stderr)
                sys.exit(1)

if __name__ == "__main__":
    main()