#!/usr/bin/env python3
"""
Web Search Tool for AI-INTERFACE.

This script provides web search capabilities with three modes:
1. Direct Web Search (single)
2. Queued Web Searches (multiple queries)
3. Extract and Search (prompt-driven, LLM extracts search queries first)

It is designed to be called by the AI-INTERFACE backend and integrates with
the manual tool selection UI.
"""

import requests
import json
import sys
import os
import argparse
import logging
from typing import Dict, List, Any, Optional

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)

DEFAULT_SEARXNG_URL = "http://localhost:5003/search"
DEFAULT_API_URL = "http://192.168.1.163:5000/v1/chat/completions"
DEFAULT_MODEL_NAME = "koboldcpp"
DEFAULT_API_TIMEOUT = 480
DEFAULT_MAX_RESULTS = 8

# --- Helper Functions ---

def call_llm(messages: List[Dict], api_url: str, model: str, api_timeout: int, max_tokens: int = 2048) -> Optional[str]:
    """Calls the LLM API with the given messages and returns the content."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        logger.info(f"Calling LLM at {api_url} with model {model}")
        response = requests.post(
            api_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=api_timeout
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API call failed: {e}")
        return None
    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return None

def optimize_search_query(prompt: str, api_url: str, model: str, api_timeout: int) -> str:
    """Converts a user prompt into an optimized short search query string."""
    system_prompt = """Convert the user's prompt into an optimal web search query (2-8 words).
- Use specific keywords
- Remove conversational words ("what", "how", "can you tell me")
- Focus on core information need
- Include time modifiers if relevant ("today", "current", "2024")
Return ONLY the optimized search query string."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Original prompt: {prompt}"}
    ]
    optimized = call_llm(messages, api_url, model, api_timeout, max_tokens=100)
    if optimized:
        return optimized.strip().strip('"').strip("'")
    logger.warning("LLM query optimization failed, falling back to original prompt.")
    return prompt

def extract_queries(prompt: str, api_url: str, model: str, api_timeout: int) -> List[str]:
    """Extracts 2-8 concise search queries from a user prompt using the LLM."""
    system_prompt = """You are an expert at formulating effective web search queries.
Based on the user's prompt, generate a JSON array of 2-8 concise search queries.
Each query should be relevant and optimized for a web search engine.
Return ONLY the JSON array, nothing else. Example: ["query 1", "query 2"]"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User prompt: {prompt}"}
    ]
    response_text = call_llm(messages, api_url, model, api_timeout, max_tokens=200)
    if not response_text:
        logger.error("LLM failed to extract queries.")
        return []

    # Robust JSON parsing
    try:
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_array_str = response_text[start_idx : end_idx + 1]
            queries = json.loads(json_array_str)
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                return [q.strip() for q in queries if q.strip()]
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {e}. Response was: {response_text}")
    
    logger.warning(f"Could not parse valid query list from LLM response: {response_text}")
    return []

def search_web(query: str, searxng_url: str, max_results: int) -> List[Dict]:
    """Performs a web search using SearxNG and returns processed results."""
    # Construct the correct SearxNG URL based on the user's curl example
    # Expected format: http://localhost:5003/search?q=latest+Nvidia+AI+chips+news&format=json
    search_url = f"{searxng_url}?q={requests.utils.quote(query)}&format=json"
    headers = {"Accept": "application/json"}
    try:
        logger.info(f"Searching SearxNG at {search_url}")
        response = requests.get(search_url, headers=headers, timeout=30) # Increased timeout for web search
        response.raise_for_status()
        data = response.json()
        results = data.get('results', [])
        processed_results = []
        for result in results[:max_results]:
            if all(key in result for key in ['url', 'title', 'content']):
                content = result.get('content', '')
                processed_results.append({
                    'title': result['title'],
                    'url': result['url'],
                    'content': content[:800] + ('...' if len(content) > 800 else ''),
                    'published': result.get('publishedDate', 'Unknown')
                })
        logger.info(f"Retrieved {len(processed_results)} search results for query: {query}")
        return processed_results
    except requests.exceptions.RequestException as e:
        logger.error(f"Web search failed for query '{query}': {e}")
        return []

def synthesize_answer(original_prompt: str, queries: List[str], results_by_query: List[Dict], api_url: str, model: str, api_timeout: int) -> str:
    """Synthesizes a final answer from search results using the LLM."""
    if not results_by_query or all(not rq.get('results') for rq in results_by_query):
        return "I couldn't find any relevant search results to answer your query."

    context = f"User's Original Prompt: {original_prompt}\n\n"
    source_idx = 1
    for i, query_data in enumerate(results_by_query):
        query = query_data['query']
        results = query_data['results']
        context += f"Search Query {i+1}: {query}\n"
        context += "-" * 40 + "\n"
        if results:
            for result in results:
                context += f"Source [{source_idx}]:\n"
                context += f"  Title: {result['title']}\n"
                context += f"  URL: {result['url']}\n"
                context += f"  Published: {result['published']}\n"
                context += f"  Content: {result['content']}\n\n"
                source_idx += 1
        else:
            context += "  No results found for this query.\n\n"
    
    system_prompt = """You are a research assistant. Use the provided search results to answer the user's original prompt comprehensively and accurately.

Requirements:
- Base your answer ONLY on the search results provided.
- Cite sources using [Source 1], [Source 2], etc., corresponding to the numbered sources in the context.
- If information conflicts between sources, mention the discrepancies.
- Provide direct, factual answers.
- If results don't fully answer the question, clearly state what information is missing.
- Be thorough but concise.
- Organize your response logically, addressing the user's prompt directly.
- If multiple queries were used, structure your answer to cover insights from all of them, providing a consolidated summary at the end if appropriate."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]
    answer = call_llm(messages, api_url, model, api_timeout, max_tokens=4000)
    
    if not answer:
        return "I was unable to synthesize the search results into a coherent answer due to an LLM error."
    
    # Append sources list
    sources_section = "\n\nSources:\n"
    current_source_idx = 1
    for query_data in results_by_query:
        for result in query_data['results']:
            sources_section += f"[{current_source_idx}] {result['url']}\n"
            current_source_idx += 1
            
    return answer + sources_section

# --- Main Execution Logic ---

def main():
    """Main function to parse arguments and execute the web search."""
    if '--get-options' in sys.argv:
        options = [
            {"name": "Direct Web Search (single)", "args": "--mode single"},
            {"name": "Queued Web Searches", "args": "--mode queue --separator=;"},
            {"name": "Extract and Search (prompt-driven)", "args": "--mode extract"}
        ]
        print(json.dumps(options, indent=2))
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Web Search Tool with multiple modes.")
    parser.add_argument("--mode", type=str, choices=['single', 'queue', 'extract'], default='single',
                        help="Mode of operation: single, queue, or extract.")
    parser.add_argument("--separator", type=str, default=';',
                        help="Separator for queued queries (default: ';').")
    parser.add_argument("--max-results", type=int, default=int(os.getenv("MAX_SEARCH_RESULTS", DEFAULT_MAX_RESULTS)),
                        help="Maximum number of search results per query.")
    parser.add_argument("--api-timeout", type=int, default=int(os.getenv("API_TIMEOUT", DEFAULT_API_TIMEOUT)),
                        help="Timeout in seconds for LLM API calls.")
    parser.add_argument("--searxng-url", type=str, default=os.getenv("SEARXNG_URL", DEFAULT_SEARXNG_URL),
                        help="SearxNG API endpoint.")
    parser.add_argument("--api-url", type=str, default=os.getenv("API_BASE_URL", DEFAULT_API_URL),
                        help="LLM API endpoint for chat completions.")
    parser.add_argument("--model", type=str, default=os.getenv("MODEL_NAME", DEFAULT_MODEL_NAME),
                        help="LLM model identifier.")
    parser.add_argument("input", nargs="*", help="User input prompt or queries.")
    
    args = parser.parse_args()
    prompt_str = " ".join(args.input).strip()

    if not prompt_str:
        print(json.dumps({"success": False, "error": "Empty input"}))
        sys.exit(1)

    logger.info(f"Mode: {args.mode}, Input: {prompt_str[:100]}...")

    try:
        if args.mode == 'single':
            query = optimize_search_query(prompt_str, args.api_url, args.model, args.api_timeout)
            logger.info(f"Optimized query for single mode: {query}")
            results = search_web(query, args.searxng_url, args.max_results)
            results_by_query = [{'query': query, 'results': results}]
            final_answer = synthesize_answer(prompt_str, [query], results_by_query, args.api_url, args.model, args.api_timeout)
            print(final_answer)

        elif args.mode == 'queue':
            # Split by newline first, then by separator if no newlines
            if '\n' in prompt_str:
                queries = [q.strip() for q in prompt_str.split('\n') if q.strip()]
            else:
                queries = [q.strip() for q in prompt_str.split(args.separator) if q.strip()]
            
            if not queries:
                print(json.dumps({"success": False, "error": "No queries found after splitting input."}))
                sys.exit(1)
            
            logger.info(f"Queued queries: {queries}")
            all_results = []
            for q in queries:
                # No optimization for queued searches, assume user provides good queries
                results = search_web(q, args.searxng_url, args.max_results)
                all_results.append({'query': q, 'results': results})
            
            final_answer = synthesize_answer(prompt_str, queries, all_results, args.api_url, args.model, args.api_timeout)
            print(final_answer)

        elif args.mode == 'extract':
            extracted_queries = extract_queries(prompt_str, args.api_url, args.model, args.api_timeout)
            if not extracted_queries:
                print(json.dumps({"success": False, "error": "Failed to extract search queries from prompt."}))
                sys.exit(1)
            
            logger.info(f"Extracted queries: {extracted_queries}")
            all_results = []
            for q in extracted_queries:
                results = search_web(q, args.searxng_url, args.max_results)
                all_results.append({'query': q, 'results': results})
            
            final_answer = synthesize_answer(prompt_str, extracted_queries, all_results, args.api_url, args.model, args.api_timeout)
            print(final_answer)

    except Exception as e:
        logger.error(f"An unhandled error occurred: {e}", exc_info=True)
        print(json.dumps({"success": False, "error": f"An unexpected error occurred: {str(e)}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()