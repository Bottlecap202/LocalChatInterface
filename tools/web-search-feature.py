#!/usr/bin/env python3
import requests
import json
import sys
from typing import List

# --- Configuration ---
SEARXNG_URL = "http://localhost:5003/search"
API_BASE_URL = "http://192.168.1.163:5000/v1/chat/completions"
API_TIMEOUT_SECONDS = 480  # 8 minutes
MAX_SEARCH_RESULTS = 10
MIN_RESULTS_THRESHOLD = 5
MAX_ITERATIONS = 5
MODEL_NAME = "koboldcpp"

def search_searxng(query: str, max_results: int = MAX_SEARCH_RESULTS) -> List[dict]:
    """Query local SearxNG and return a list of results."""
    try:
        resp = requests.get(SEARXNG_URL, params={"q": query, "format": "json", "count": max_results}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return [{"title": r.get("title", "No title"), "url": r.get("url", "No URL")} for r in data.get("results", [])]
    except Exception as e:
        return [{"title": "Error", "url": str(e)}]

def generate_search_queries(user_prompt: str) -> List[str]:
    """Use local LLM API to generate 2-3 highly relevant search queries."""
    system_msg = {"role": "system", "content": "You are an AI assistant that generates highly relevant web search queries."}
    user_msg = {
        "role": "user",
        "content": (
            f"Generate 2-3 concise, highly relevant web search queries for the following user prompt:\n"
            f"{user_prompt}\n"
            "Return a JSON array of strings only."
        )
    }
    try:
        payload = {"model": MODEL_NAME, "messages": [system_msg, user_msg], "temperature": 0.0}
        resp = requests.post(API_BASE_URL, json=payload, timeout=API_TIMEOUT_SECONDS)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        queries = json.loads(content)
        return [q for q in queries if isinstance(q, str)]
    except Exception:
        # Fallback
        terms = user_prompt.split()
        if len(terms) <= 5:
            return [user_prompt]
        return [user_prompt, " ".join(terms[:5]), " ".join(terms[-5:])]

def summarize_results_with_llm(aggregated_results: List[dict], user_prompt: str) -> str:
    """Feed aggregated search results to LLM and get a concise summary."""
    aggregated_text = "\n".join([f"{r['title']}: {r['url']}" for r in aggregated_results])
    final_prompt = (
        f"Using the following aggregated search results, provide a concise and accurate summary answer "
        f"for the user prompt:\n{aggregated_text}\n\nUser prompt: {user_prompt}"
    )
    try:
        system_msg = {"role": "system", "content": "You are an AI assistant that summarizes web search results accurately."}
        user_msg = {"role": "user", "content": final_prompt}
        payload = {"model": MODEL_NAME, "messages": [system_msg, user_msg], "temperature": 0.0}
        resp = requests.post(API_BASE_URL, json=payload, timeout=API_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error generating final summary: {str(e)}"

def iterative_web_search(user_prompt: str) -> dict:
    """Perform iterative searches, aggregate results, and summarize via LLM."""
    aggregated_results = []
    details_log = []
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        candidate_queries = generate_search_queries(user_prompt)
        if not candidate_queries:
            break

        iteration_log = {"iteration": iteration, "queries": [], "results": []}

        for q in candidate_queries:
            results = search_searxng(q)
            iteration_log["queries"].append(q)
            iteration_log["results"].append(results)
            aggregated_results.extend(results)

        details_log.append(iteration_log)

        if len(aggregated_results) >= MIN_RESULTS_THRESHOLD:
            break

    # Summarize aggregated results
    summary_text = summarize_results_with_llm(aggregated_results, user_prompt)

    return {
        "summary": summary_text,
        "details": details_log
    }

# --- Tool interface ---
if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        user_prompt = data.get("query") or data.get("prompt")
        if not user_prompt:
            print(json.dumps({"error": "Missing 'query' or 'prompt' input."}))
            sys.exit(1)
        
        results = iterative_web_search(user_prompt)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
