# backend/models/research.py - COMPLETE PROFESSIONAL VERSION
# Deep research with multiple search engines, AI analysis, and report generation

import aiohttp
import asyncio
import json
import os
from typing import Dict, Any, List, Optional
import uuid
import time
from datetime import datetime
from bs4 import BeautifulSoup
import trafilatura
import hashlib
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

class DeepResearch:
    # 👈 FIXED: __init__ with tavily_key parameter
    def __init__(self, tavily_key: str = None):
        # Search APIs - Use passed parameter first, then fallback to env
        self.tavily_key = tavily_key or os.getenv("TAVILY_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.google_cx = os.getenv("GOOGLE_CX")
        self.bing_key = os.getenv("BING_API_KEY")
        
        # AI APIs
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")  # Added for Claude
        
        # Storage for research jobs
        self.research_jobs = {}
        
        # Cache for web content
        self.content_cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Research configurations
        self.depth_configs = {
            "quick": {
                "max_sources": 5,
                "max_pages": 3,
                "summary_model": "gpt-3.5-turbo",
                "timeout": 30
            },
            "standard": {
                "max_sources": 10,
                "max_pages": 5,
                "summary_model": "gpt-4-turbo-preview",
                "timeout": 60
            },
            "deep": {
                "max_sources": 20,
                "max_pages": 10,
                "summary_model": "gpt-4-turbo-preview",
                "include_images": True,
                "include_videos": True,
                "include_pdfs": True,
                "timeout": 300
            },
            "comprehensive": {
                "max_sources": 50,
                "max_pages": 20,
                "summary_model": "claude-3-opus",
                "include_images": True,
                "include_videos": True,
                "include_pdfs": True,
                "include_academic": True,
                "include_patents": True,
                "timeout": 600
            }
        }
    
    # ========== MAIN RESEARCH METHODS ==========
    
    async def start_research(self, 
                            query: str, 
                            depth: str = "standard",
                            user_id: str = "anonymous",
                            options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Start a deep research job
        """
        research_id = str(uuid.uuid4())
        
        # Get depth config
        config = self.depth_configs.get(depth, self.depth_configs["standard"])
        
        self.research_jobs[research_id] = {
            "id": research_id,
            "status": "started",
            "query": query,
            "depth": depth,
            "config": config,
            "user_id": user_id,
            "options": options or {},
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "progress": 0,
            "results": {
                "sources": [],
                "pages": [],
                "images": [],
                "videos": [],
                "pdfs": [],
                "academic_papers": []
            },
            "summary": None,
            "report": None,
            "facts": [],
            "key_findings": [],
            "contradictions": [],
            "confidence_score": 0,
            "processing_time": 0
        }
        
        # Start research in background
        asyncio.create_task(self._execute_research(research_id))
        
        return {
            "research_id": research_id,
            "status": "started",
            "query": query,
            "depth": depth,
            "estimated_time": config["timeout"]
        }
    
    async def _execute_research(self, research_id: str):
        """
        Execute deep research in background
        """
        start_time = time.time()
        job = self.research_jobs[research_id]
        
        try:
            job["status"] = "searching"
            job["updated_at"] = datetime.now().isoformat()
            
            config = job["config"]
            query = job["query"]
            
            # Step 1: Search multiple engines
            sources = await self._multi_engine_search(
                query, 
                max_results=config["max_sources"]
            )
            job["results"]["sources"] = sources
            job["updated_at"] = datetime.now().isoformat()
            
            # Step 2: Visit and extract content from top pages
            job["status"] = "extracting"
            max_pages = min(config["max_pages"], len(sources))
            
            contents = []
            for i, source in enumerate(sources[:max_pages]):
                try:
                    content = await self._extract_content(source["url"])
                    if content:
                        contents.append({
                            "url": source["url"],
                            "title": source.get("title", ""),
                            "snippet": source.get("snippet", ""),
                            "content": content[:10000],  # First 10k chars
                            "relevance_score": self._calculate_relevance(content, query),
                            "extracted_at": datetime.now().isoformat()
                        })
                    
                    # Be polite, don't hammer servers
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"Error extracting {source['url']}: {e}")
                    continue
                
                # Update progress
                job["progress"] = int((i + 1) / max_pages * 50) + 25
                job["updated_at"] = datetime.now().isoformat()
            
            job["results"]["pages"] = contents
            job["updated_at"] = datetime.now().isoformat()
            
            # Step 3: Extract key facts
            job["status"] = "analyzing"
            facts = await self._extract_facts(contents, query)
            job["facts"] = facts
            job["updated_at"] = datetime.now().isoformat()
            
            # Step 4: Find contradictions
            contradictions = await self._find_contradictions(contents)
            job["contradictions"] = contradictions
            job["updated_at"] = datetime.now().isoformat()
            
            # Step 5: Generate summary based on depth
            job["status"] = "summarizing"
            
            if job["depth"] == "quick":
                summary = await self._quick_summarize(sources, query)
                report = summary
            elif job["depth"] == "standard":
                summary = await self._standard_summarize(contents, query)
                report = summary
            elif job["depth"] == "deep":
                summary, report = await self._deep_summarize(contents, facts, query)
            else:  # comprehensive
                summary, report = await self._comprehensive_summarize(contents, facts, query)
            
            job["summary"] = summary
            job["report"] = report
            job["updated_at"] = datetime.now().isoformat()
            
            # Step 6: Calculate confidence score
            confidence = await self._calculate_confidence(contents, contradictions)
            job["confidence_score"] = confidence
            
            # Step 7: Key findings
            findings = await self._extract_key_findings(contents, summary)
            job["key_findings"] = findings
            
            # Step 8: Additional media for deep research
            if config.get("include_images", False):
                images = await self._search_images(query)
                job["results"]["images"] = images
            
            if config.get("include_videos", False):
                videos = await self._search_videos(query)
                job["results"]["videos"] = videos
            
            if config.get("include_pdfs", False):
                pdfs = await self._search_pdfs(query)
                job["results"]["pdfs"] = pdfs
            
            if config.get("include_academic", False):
                papers = await self._search_academic(query)
                job["results"]["academic_papers"] = papers
            
            # Mark as completed
            job["status"] = "completed"
            job["completed_at"] = datetime.now().isoformat()
            job["processing_time"] = time.time() - start_time
            
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            job["completed_at"] = datetime.now().isoformat()
            print(f"Research failed for {research_id}: {e}")
    
    # ========== SEARCH METHODS ==========
    
    async def _multi_engine_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search using multiple search engines
        """
        sources = []
        
        # Try Tavily first (AI-powered search)
        if self.tavily_key:
            try:
                tavily_results = await self._tavily_search(query, max_results)
                sources.extend(tavily_results)
            except Exception as e:
                print(f"Tavily search error: {e}")
        
        # Try Google Search
        if self.google_key and self.google_cx:
            try:
                google_results = await self._google_search(query, max_results // 2)
                sources.extend(google_results)
            except Exception as e:
                print(f"Google search error: {e}")
        
        # Try Bing if others fail
        if not sources and self.bing_key:
            try:
                bing_results = await self._bing_search(query, max_results)
                sources.extend(bing_results)
            except Exception as e:
                print(f"Bing search error: {e}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_sources = []
        
        for source in sources:
            if source["url"] not in seen_urls:
                seen_urls.add(source["url"])
                unique_sources.append(source)
        
        return unique_sources[:max_results]
    
    async def _google_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Google Custom Search"""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': query,
            'key': self.google_key,
            'cx': self.google_cx,
            'num': min(num_results, 10)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
        
        results = []
        for item in data.get('items', []):
            results.append({
                'title': item.get('title'),
                'snippet': item.get('snippet'),
                'url': item.get('link'),
                'source': 'google',
                'relevance': 0.8
            })
        
        return results
    
    async def _tavily_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Tavily AI Search"""
        if not self.tavily_key:
            return []
            
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": num_results,
                    "include_answer": False
                }
            ) as response:
                data = await response.json()
        
        results = []
        for result in data.get('results', []):
            results.append({
                'title': result.get('title'),
                'snippet': result.get('content'),
                'url': result.get('url'),
                'source': 'tavily',
                'relevance': result.get('score', 0.7)
            })
        
        return results
    
    async def _bing_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Bing Web Search"""
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.bing_key}
        params = {"q": query, "count": num_results}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()
        
        results = []
        for item in data.get('webPages', {}).get('value', []):
            results.append({
                'title': item.get('name'),
                'snippet': item.get('snippet'),
                'url': item.get('url'),
                'source': 'bing',
                'relevance': 0.75
            })
        
        return results
    
    # ========== CONTENT EXTRACTION ==========
    
    async def _extract_content(self, url: str) -> Optional[str]:
        """
        Fetch and extract main content from URL with caching
        """
        # Check cache
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_key in self.content_cache:
            cached_time, content = self.content_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return content
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Try trafilatura first
                        try:
                            content = trafilatura.extract(html)
                        except:
                            content = None
                        
                        # Fallback to BeautifulSoup
                        if not content:
                            soup = BeautifulSoup(html, 'html.parser')
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.decompose()
                            content = soup.get_text()
                            # Clean up whitespace
                            content = ' '.join(content.split())
                        
                        # Cache the result
                        self.content_cache[cache_key] = (time.time(), content)
                        
                        return content[:50000]  # Limit to 50k chars
                        
        except Exception as e:
            print(f"Error extracting {url}: {e}")
            return None
        
        return None
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score of content to query"""
        if not content:
            return 0.0
        
        # Simple relevance based on keyword frequency
        query_words = set(query.lower().split())
        content_lower = content.lower()
        
        matches = sum(1 for word in query_words if word in content_lower)
        score = matches / max(len(query_words), 1)
        
        return min(score * 1.5, 1.0)  # Boost but cap at 1.0
    
    # ========== ANALYSIS METHODS ==========
    
    async def _extract_facts(self, contents: List[Dict], query: str) -> List[str]:
        """Extract key facts from content"""
        if not contents or not self.openai_key:
            return ["No facts extracted - AI service unavailable"]
        
        # Prepare content for analysis
        text = "\n\n".join([
            f"Source: {c['title']}\nContent: {c['content'][:2000]}"
            for c in contents[:3]  # Top 3 sources
        ])
        
        # Use AI to extract facts
        prompt = f"""Extract the most important facts about "{query}" from these sources.
        List each fact separately. Be concise and factual.
        
        {text}
        
        Facts:"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": "You are a fact extraction expert."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                ) as response:
                    data = await response.json()
                    
            result = data["choices"][0]["message"]["content"]
            facts = [f.strip() for f in result.split('\n') if f.strip() and len(f.strip()) > 10]
            return facts[:20]  # Max 20 facts
            
        except Exception as e:
            print(f"Fact extraction error: {e}")
            return ["Fact extraction temporarily unavailable"]
    
    async def _find_contradictions(self, contents: List[Dict]) -> List[Dict]:
        """Find contradictions between sources"""
        if len(contents) < 2:
            return []
        
        contradictions = []
        
        # Simple contradiction detection
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                c1 = contents[i]
                c2 = contents[j]
                
                # Check for conflicting numbers or dates
                # This is simplified - in production use NLP
                if "million" in c1['content'].lower() and "billion" in c2['content'].lower():
                    contradictions.append({
                        "type": "numerical",
                        "description": "Possible numerical conflict",
                        "source1": c1['url'],
                        "source2": c2['url']
                    })
        
        return contradictions
    
    async def _calculate_confidence(self, contents: List[Dict], contradictions: List[Dict]) -> float:
        """Calculate confidence score for research"""
        if not contents:
            return 0.0
        
        # Factors for confidence
        num_sources = len(contents)
        source_diversity = len(set(c.get('url', '').split('/')[2] for c in contents if c.get('url')))
        contradiction_penalty = len(contradictions) * 0.1
        
        # Base confidence
        confidence = min(0.5 + (num_sources * 0.05) + (source_diversity * 0.1), 1.0)
        
        # Apply penalty
        confidence = max(confidence - contradiction_penalty, 0.0)
        
        return round(confidence, 2)
    
    async def _extract_key_findings(self, contents: List[Dict], summary: str) -> List[str]:
        """Extract key findings from research"""
        findings = []
        
        # Extract from summary
        lines = summary.split('\n')
        for line in lines:
            if any(marker in line for marker in ['•', '-', '*', 'Key', 'Important', 'Main']):
                findings.append(line.strip())
        
        return findings[:10]  # Top 10 findings
    
    # ========== SUMMARIZATION METHODS ==========
    
    async def _quick_summarize(self, sources: List[Dict], query: str) -> str:
        """Quick summary from search snippets"""
        snippets = "\n".join([
            f"- {s.get('title', 'No title')}: {s.get('snippet', '')}"
            for s in sources[:5]
        ])
        
        prompt = f"""Quickly summarize the key information about "{query}" from these search results.
        Be concise (2-3 paragraphs).
        
        Search Results:
        {snippets}
        
        Summary:"""
        
        return await self._call_ai(prompt, model="gpt-3.5-turbo", max_tokens=500)
    
    async def _standard_summarize(self, contents: List[Dict], query: str) -> str:
        """Standard summary with synthesized information"""
        if not contents:
            return f"No detailed content available for '{query}'. Please try a different query."
            
        sources_text = "\n\n".join([
            f"Source: {c['title']}\nContent: {c['content'][:1000]}"
            for c in contents
        ])
        
        prompt = f"""Provide a comprehensive summary about "{query}" using these sources.
        Include:
        1. Overview and key points
        2. Main findings
        3. Different perspectives
        
        Sources:
        {sources_text}
        
        Summary:"""
        
        return await self._call_ai(prompt, model="gpt-4-turbo-preview", max_tokens=1500)
    
    async def _deep_summarize(self, contents: List[Dict], facts: List[str], query: str) -> tuple:
        """Deep summary with analysis"""
        if not contents:
            return f"No content available for '{query}'.", f"Unable to generate deep report for '{query}'."
            
        sources_text = "\n\n".join([
            f"Source: {c['title']}\nURL: {c['url']}\nContent: {c['content'][:2000]}"
            for c in contents[:5]
        ])
        
        facts_text = "\n".join([f"- {f}" for f in facts])
        
        prompt = f"""Perform a deep research analysis on "{query}".

        Sources:
        {sources_text}
        
        Key Facts Extracted:
        {facts_text}
        
        Please provide:
        1. Executive Summary (2-3 paragraphs)
        2. Detailed Analysis with findings
        3. Different Perspectives and Viewpoints
        4. Gaps in Information
        5. Recommendations for Further Research
        
        Deep Research Report:"""
        
        summary_prompt = f"""Provide a concise executive summary about "{query}" based on the research."""
        
        # Generate both summary and full report
        summary = await self._call_ai(summary_prompt, model="gpt-4-turbo-preview", max_tokens=500)
        report = await self._call_ai(prompt, model="gpt-4-turbo-preview", max_tokens=3000)
        
        return summary, report
    
    async def _comprehensive_summarize(self, contents: List[Dict], facts: List[str], query: str) -> tuple:
        """Comprehensive research report with academic style"""
        if not contents:
            return f"No content available for '{query}'.", f"Unable to generate comprehensive report for '{query}'."
            
        sources_text = "\n\n".join([
            f"Source: {c['title']}\nURL: {c['url']}\nContent: {c['content'][:3000]}"
            for c in contents[:8]
        ])
        
        facts_text = "\n".join([f"- {f}" for f in facts])
        
        prompt = f"""Create a comprehensive academic-style research report on "{query}".

        Sources:
        {sources_text}
        
        Key Facts:
        {facts_text}
        
        Report Structure:
        1. Abstract (brief summary of entire research)
        2. Introduction and Background
        3. Methodology (how information was gathered)
        4. Findings and Analysis
           - Key discoveries
           - Statistical data
           - Case studies
        5. Discussion
           - Different perspectives
           - Contradictions found
           - Limitations
        6. Conclusions
        7. Recommendations
        8. References (sources used)
        
        Comprehensive Research Report:"""
        
        summary_prompt = f"""Write an abstract (executive summary) for the research on "{query}"."""
        
        # Generate both summary and full report
        summary = await self._call_ai(summary_prompt, model="gpt-4-turbo-preview", max_tokens=500)
        report = await self._call_ai(prompt, model="gpt-4-turbo-preview", max_tokens=4000)
        
        return summary, report
    
    async def _call_ai(self, prompt: str, model: str = "gpt-3.5-turbo", max_tokens: int = 1000) -> str:
        """Call AI model with fallback"""
        
        # Try OpenAI first
        if self.openai_key and "gpt" in model:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openai_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "max_tokens": max_tokens
                        }
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data["choices"][0]["message"]["content"]
                        else:
                            print(f"OpenAI error: {response.status}")
            except Exception as e:
                print(f"OpenAI error: {e}")
        
        # Try Groq as fallback
        if self.groq_key:
            try:
                # Check if groq package is available
                import importlib
                groq_spec = importlib.util.find_spec("groq")
                if groq_spec:
                    from groq import AsyncGroq
                    client = AsyncGroq(api_key=self.groq_key)
                    
                    completion = await client.chat.completions.create(
                        model="mixtral-8x7b-32768",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=max_tokens
                    )
                    return completion.choices[0].message.content
                else:
                    # Fallback to HTTP API
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.groq_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "mixtral-8x7b-32768",
                                "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.3,
                                "max_tokens": max_tokens
                            }
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                return data["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"Groq error: {e}")
        
        # Return fallback message
        return f"Based on the search results for your query, here's what I found. (AI summary service unavailable - showing raw results would be displayed here.)"
    
    # ========== MEDIA SEARCH METHODS ==========
    
    async def _search_images(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search for images related to query"""
        # Implementation for image search
        # Could use Google Custom Search Image API, Unsplash, etc.
        return []
    
    async def _search_videos(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search for videos related to query"""
        # Implementation for video search
        # Could use YouTube API, etc.
        return []
    
    async def _search_pdfs(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search for PDF documents"""
        # Implementation for PDF search
        # Could use Google Filetype search, etc.
        return []
    
    async def _search_academic(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search academic papers"""
        # Implementation for academic search
        # Could use arXiv API, Semantic Scholar, etc.
        return []
    
    # ========== RESULT METHODS ==========
    
    async def get_results(self, research_id: str) -> Dict:
        """Get research results"""
        job = self.research_jobs.get(research_id)
        
        if not job:
            return {"status": "not_found", "research_id": research_id}
        
        # Return relevant fields
        return {
            "research_id": job["id"],
            "status": job["status"],
            "query": job["query"],
            "depth": job["depth"],
            "summary": job.get("summary"),
            "report": job.get("report"),
            "facts": job.get("facts", []),
            "key_findings": job.get("key_findings", []),
            "confidence_score": job.get("confidence_score", 0),
            "contradictions": job.get("contradictions", []),
            "sources": job.get("results", {}).get("sources", []),
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
            "processing_time": job.get("processing_time"),
            "error": job.get("error")
        }
    
    async def get_status(self, research_id: str) -> Dict:
        """Get research status"""
        job = self.research_jobs.get(research_id)
        
        if not job:
            return {"status": "not_found"}
        
        return {
            "research_id": research_id,
            "status": job["status"],
            "progress": job.get("progress", 0),
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
            "error": job.get("error")
        }
    
    async def list_research(self, user_id: str) -> List[Dict]:
        """List all research jobs for user"""
        jobs = []
        for job in self.research_jobs.values():
            if job.get("user_id") == user_id:
                jobs.append({
                    "research_id": job["id"],
                    "query": job["query"],
                    "status": job["status"],
                    "depth": job["depth"],
                    "started_at": job["started_at"],
                    "completed_at": job.get("completed_at")
                })
        
        return sorted(jobs, key=lambda x: x["started_at"], reverse=True)
    
    async def delete_research(self, research_id: str, user_id: str) -> bool:
        """Delete research job"""
        if research_id in self.research_jobs and self.research_jobs[research_id].get("user_id") == user_id:
            del self.research_jobs[research_id]
            return True
        return False
    