#!/usr/bin/env python3
"""
Web Search Tool for LocalChatInterface
Always performs web searches for every prompt.
"""

import requests
import json
import sys
import os
import logging
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class WebSearchTool:
    def __init__(self):
        self.searxng_url = os.getenv("SEARXNG_URL", "http://localhost:5003/search")
        self.api_base_url = os.getenv("API_BASE_URL", "http://192.168.1.163:5000/v1/chat/completions")
        self.model_name = os.getenv("MODEL_NAME", "koboldcpp")
        self.api_timeout = int(os.getenv("API_TIMEOUT", "120"))
        self.max_results = int(os.getenv("MAX_SEARCH_RESULTS", "8"))
        logger.info("WebSearchTool initialized")
    
    def _call_llm(self, messages: List[Dict[str, str]], max_tokens: int = 2048) -> Optional[str]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        try:
            response = requests.post(
                self.api_base_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=self.api_timeout
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None
    
    def should_use_tool(self, prompt: str) -> bool:
        return True
    
    def _optimize_search_query(self, prompt: str) -> str:
        system_prompt = """Convert the user's prompt into an optimal web search query.

Guidelines:
- Keep concise (2-8 words typically)
- Use specific keywords search engines understand
- Remove conversational words ("what", "how", "can you tell me")
- Focus on core information need
- Include time modifiers if relevant ("today", "current", "2024")
- Use quotes for exact phrases when needed

Examples:
"What did Trump do today?" → "Trump today news activities"
"What's Google's stock price right now?" → "GOOGL stock price current"
"How much does a Tesla cost?" → "Tesla price 2024"
"What time is it in Boston?" → "current time Boston"

Return ONLY the optimized search query."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original prompt: {prompt}"}
        ]
        optimized = self._call_llm(messages, 100)
        if optimized:
            optimized = optimized.strip().strip('"').strip("'")
            return optimized
        return prompt
    
    def _search_web(self, query: str) -> List[Dict[str, Any]]:
        params = {'q': query, 'format': 'json'}
        try:
            logger.info(f"Searching web for: {query}")
            response = requests.get(self.searxng_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])
            processed_results = []
            for result in results[:self.max_results]:
                if all(key in result for key in ['url', 'title', 'content']):
                    processed_results.append({
                        'title': result['title'],
                        'url': result['url'],
                        'content': result['content'][:800] + ('...' if len(result.get('content', '')) > 800 else ''),
                        'published': result.get('publishedDate', 'Unknown')
                    })
            logger.info(f"Retrieved {len(processed_results)} search results")
            return processed_results
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    def _synthesize_answer(self, original_prompt: str, search_results: List[Dict[str, Any]]) -> str:
        if not search_results:
            return "I couldn't find any relevant search results to answer your query."
        context = f"User's Question: {original_prompt}\n\nWeb Search Results:\n" + "=" * 60 + "\n\n"
        for i, result in enumerate(search_results, 1):
            context += f"Source {i}:\nTitle: {result['title']}\nURL: {result['url']}\nPublished: {result['published']}\nContent: {result['content']}\n\n"
        system_prompt = """You are a research assistant. Use the provided search results to answer the user's question comprehensively and accurately.

Requirements:
- Base your answer ONLY on the search results provided
- Cite sources using [Source 1], [Source 2], etc.
- If information conflicts between sources, mention the discrepancies
- Provide direct, factual answers
- If results don't fully answer the question, clearly state what information is missing
- Be thorough but concise"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        answer = self._call_llm(messages, 3000)
        return answer or "I was unable to synthesize the search results into a coherent answer."
    
    def _direct_answer(self, prompt: str) -> str:
        system_prompt = """You are a knowledgeable assistant. Answer the user's question based on your training data. Be accurate, helpful, and concise. If you're uncertain about current information, mention that limitation and suggest they might need up-to-date sources."""
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        answer = self._call_llm(messages, 1500)
        return answer or "I'm unable to provide an answer to your question."
    
    def process(self, prompt: str) -> Dict[str, Any]:
        try:
            logger.info(f"Processing prompt: {prompt[:100]}...")
            search_analysis = {"needs_search": True, "confidence": 100, "reason": "Forced web search"}
            search_query = self._optimize_search_query(prompt)
            search_results = self._search_web(search_query)
            if not search_results:
                return {"success": False, "error": "No search results found", "method": "web_search", "search_query": search_query}
            answer = self._synthesize_answer(prompt, search_results)
            return {
                "success": True,
                "answer": answer,
                "method": "web_search",
                "search_query": search_query,
                "sources": [result['url'] for result in search_results],
                "source_count": len(search_results),
                "analysis": search_analysis
            }
        except Exception as e:
            logger.error(f"Error processing prompt: {e}")
            return {"success": False, "error": f"Processing error: {str(e)}", "method": "error"}

def main():
    tool = WebSearchTool()
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        try:
            input_data = sys.stdin.read().strip()
            if not input_data:
                print(json.dumps({"success": False, "error": "No input provided"}))
                sys.exit(1)
            try:
                parsed_data = json.loads(input_data)
                prompt = parsed_data.get('prompt') or parsed_data.get('query') or parsed_data.get('message', '')
            except json.JSONDecodeError:
                prompt = input_data
        except Exception as e:
            print(json.dumps({"success": False, "error": f"Failed to read input: {str(e)}"}))
            sys.exit(1)
    if not prompt:
        print(json.dumps({"success": False, "error": "Empty prompt provided"}))
        sys.exit(1)
    result = tool.process(prompt)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()