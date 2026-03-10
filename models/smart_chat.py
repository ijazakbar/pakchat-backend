# backend/models/smart_chat.py - COMPLETE INTELLIGENT CHAT PROCESSOR
# Jo khud samjhega ke user kya chahta hai aur best API use karega

import re
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
from collections import defaultdict

# Import all services
from .api_services import (
    WikipediaService, TavilyService, NewsService, GoogleBooksService,
    LLMService, HuggingFaceService, OpenLibraryService
)
from .chat import ChatModel
from .image import ImageProcessor
from .video import VideoGenerator
from .voice import VoiceProcessor
from .research import DeepResearch

logger = logging.getLogger(__name__)

class SmartChatProcessor:
    """Intelligent chat processor that understands user intent and uses best APIs"""
    
    def __init__(self):
        # Initialize all services
        self.wiki = WikipediaService()
        self.tavily = TavilyService()
        self.news = NewsService()
        self.books = GoogleBooksService()
        self.openlibrary = OpenLibraryService()
        self.llm = LLMService()
        self.huggingface = HuggingFaceService()
        self.chat = ChatModel()
        self.image = ImageProcessor()
        self.video = VideoGenerator()
        self.voice = VoiceProcessor()
        self.research = DeepResearch()
        
        # Language detection patterns
        self.urdu_pattern = re.compile(r'[۔،؟آابپتٹثجچحخدڈذرڑزژسشصضطظعغفقکگلمنوہھئی]')
        self.roman_urdu_pattern = re.compile(r'\b(ki|hai|ka|ke|se|ko|mein|tha|the|ho|hain|ga|gi)\b', re.IGNORECASE)
        
        # Intent detection patterns (Urdu + English + Roman Urdu)
        self.patterns = {
            'wikipedia': [
                # English
                r'\b(who is|what is|history of|definition of|meaning of|when was|where is)\b',
                r'\b(wiki|wikipedia|encyclopedia|information about)\b',
                # Urdu
                r'(کون ہے|کیا ہے|تاریخ|تعریف|مطلب|کس نے لکھا|کب پیدا ہوئے|کہاں ہے)',
                r'(ویکیپیڈیا|انسائیکلوپیڈیا|معلومات)',
                # Roman Urdu
                r'\b(kaun hai|kya hai|tareekh|matlab|kis ne likha|kab paida hua|kahan hai)\b',
                r'\b(wiki|information|maaloomat)\b'
            ],
            
            'news': [
                # English
                r'\b(news|latest|breaking|today|headlines|update|current affairs|weather|forecast)\b',
                # Urdu
                r'(خبر|تازہ|آج|حالیہ|نیوز|اخبار|موسم|پیشن گوئی)',
                # Roman Urdu
                r'\b(khabar|taaza|aaj|halia|news|akhbar|mosam|preshan goi)\b'
            ],
            
            'books': [
                # English
                r'\b(book|novel|story|author|writer|published|read|literature|poetry)\b',
                # Urdu
                r'(کتاب|ناول|کہانی|مصنف|پڑھنا|ناولٹ|افسانہ|ادب|شاعری)',
                # Roman Urdu
                r'\b(kitab|novel|kahani|musannif|parhna|adab|shayari)\b'
            ],
            
            'web_search': [
                # English
                r'\b(search|find|look for|google|internet|online|website|url)\b',
                # Urdu
                r'(تلاش|ڈھونڈنا|انٹرنیٹ|گوگل|سرچ|ویب سائٹ)',
                # Roman Urdu
                r'\b(talash|dhundna|internet|google|search|website)\b'
            ],
            
            'image_generation': [
                # English
                r'\b(generate image|create picture|draw|make image|photo of|picture of)\b',
                r'\b(dalle|stable diffusion|ai art|artwork|painting)\b',
                # Urdu
                r'(تصویر بناؤ|تصویر بنا|ڈرائنگ|آرٹ|پینٹنگ)',
                # Roman Urdu
                r'\b(tasveer banao|drawing|art|painting|picture banao)\b'
            ],
            
            'video_generation': [
                # English
                r'\b(generate video|create video|make video|animation|video of)\b',
                # Urdu
                r'(ویڈیو بناؤ|اینیمیشن|مووی بناؤ)',
                # Roman Urdu
                r'\b(video banao|animation|movie banao)\b'
            ],
            
            'voice': [
                # English
                r'\b(voice|speak|say|pronounce|audio|listen|speech|tell me)\b',
                # Urdu
                r'(آواز|بولو|سناؤ|تلفظ|آڈیو)',
                # Roman Urdu
                r'\b(aawaz|bolo|suno|audio|sunao)\b'
            ],
            
            'research': [
                # English
                r'\b(research|deep research|analyze|study|investigate|comprehensive)\b',
                # Urdu
                r'(تحقیق|گہری تحقیق|تجزیہ|مطالعہ|تفتیش)',
                # Roman Urdu
                r'\b(tehqeeq|gehri tehqeeq|tajzia|mutalia)\b'
            ],
            
            'weather': [
                # English
                r'\b(weather|temperature|rain|sunny|cloudy|forecast|climate)\b',
                # Urdu
                r'(موسم|درجہ حرارت|بارش|دھوپ|بادل|پیشن گوئی)',
                # Roman Urdu
                r'\b(mosam|darja hararat|baarish|dhoop|badal|preshan goi)\b'
            ],
            
            'time_date': [
                # English
                r'\b(time|date|day|month|year|today|tomorrow|yesterday|clock)\b',
                # Urdu
                r'(وقت|تاریخ|دن|مہینہ|سال|آج|کل|گزشتہ|گھڑی)',
                # Roman Urdu
                r'\b(waqt|tareekh|din|mahina|saal|aaj|kal|ghari)\b'
            ],
            
            'calculation': [
                # English
                r'\b(calculate|math|sum|add|subtract|multiply|divide|equation|formula)\b',
                # Urdu
                r'(حساب|ریاضی|جمع|تفریق|ضرب|تقسیم|مساوات|فارمولا)',
                # Roman Urdu
                r'\b(hisab|riyazi|jama|tafreek|zarb|taqseem|masawat|formula)\b'
            ],
            
            'translation': [
                # English
                r'\b(translate|meaning in urdu|english to urdu|urdu to english)\b',
                # Urdu
                r'(ترجمہ|اردو معنی|انگریزی سے اردو|اردو سے انگریزی)',
                # Roman Urdu
                r'\b(tarjuma|urdu meaning|english to urdu|urdu to english)\b'
            ],
            
            'code': [
                # English
                r'\b(code|programming|python|javascript|function|class|algorithm|developer)\b',
                # Urdu
                r'(کوڈ|پروگرامنگ|پائتھون|جاواسکرپٹ|فنکشن|کلاس|الگورتھم)',
                # Roman Urdu
                r'\b(code|programming|python|javascript|function|class|algorithm)\b'
            ]
        }
        
        # Response templates
        self.templates = {
            'wikipedia': {
                'urdu': "📚 **ویکیپیڈیا سے معلومات:**\n{extract}\n\nمزید پڑھیں: {url}",
                'roman-urdu': "📚 **Wikipedia se maloomat:**\n{extract}\n\nMazid parhain: {url}",
                'english': "📚 **From Wikipedia:**\n{extract}\n\nRead more: {url}"
            },
            'news': {
                'urdu': "📰 **تازہ ترین خبریں:**\n{news_items}\n\nمزید خبروں کے لیے پوچھیں۔",
                'roman-urdu': "📰 **Taza khabrein:**\n{news_items}\n\nMazid khabron ke liye poochain.",
                'english': "📰 **Latest News:**\n{news_items}\n\nAsk for more news."
            },
            'books': {
                'urdu': "📖 **متعلقہ کتابیں:**\n{books}\n\nیہ کتابیں {source} پر دستیاب ہیں۔",
                'roman-urdu': "📖 **Mutaliqa kitabein:**\n{books}\n\nYe kitabein {source} par dastyab hain.",
                'english': "📖 **Related Books:**\n{books}\n\nThese books are available on {source}."
            },
            'web_search': {
                'urdu': "🌐 **ویب تلاش کے نتائج:**\n{answer}\n\nمزید معلومات: {sources}",
                'roman-urdu': "🌐 **Web talash ke nataij:**\n{answer}\n\nMazid maloomat: {sources}",
                'english': "🌐 **Web Search Results:**\n{answer}\n\nMore info: {sources}"
            },
            'image': {
                'urdu': "🎨 **آپ کی تصویر تیار ہے!**\n{url}\n\nکیا آپ کوئی اور تصویر چاہیں گے؟",
                'roman-urdu': "🎨 **Ap ki tasveer tayyar hai!**\n{url}\n\nKya ap koi aur tasveer chahain gay?",
                'english': "🎨 **Your image is ready!**\n{url}\n\nWould you like another image?"
            },
            'research': {
                'urdu': "🔬 **تحقیقی رپورٹ:**\n{summary}\n\nاعتماد کا درجہ: {confidence}%\nماخذ: {sources_count} ذرائع",
                'roman-urdu': "🔬 **Tehqeeqi report:**\n{summary}\n\nAitmad ka darja: {confidence}%\nMakhiz: {sources_count} zaraey",
                'english': "🔬 **Research Report:**\n{summary}\n\nConfidence: {confidence}%\nSources: {sources_count}"
            },
            'default': {
                'urdu': "{response}",
                'roman-urdu': "{response}",
                'english': "{response}"
            }
        }
        
        # Conversation memory
        self.conversation_memory = defaultdict(lambda: {
            'history': [],
            'preferences': {},
            'last_intents': [],
            'last_language': 'urdu',
            'context': {}
        })
    
    # ========== DETECTION METHODS ==========
    
    def detect_language(self, query: str) -> str:
        """Detect user's language (Urdu, Roman Urdu, English)"""
        # Check for Urdu script
        if self.urdu_pattern.search(query):
            return 'urdu'
        
        # Check for Roman Urdu keywords
        if self.roman_urdu_pattern.search(query):
            return 'roman-urdu'
        
        # Default to English
        return 'english'
    
    def detect_intent(self, query: str) -> List[Tuple[str, float]]:
        """
        Detect user intent with confidence scores
        Returns list of (intent, confidence) tuples
        """
        query_lower = query.lower()
        intents_with_scores = []
        
        for intent, patterns in self.patterns.items():
            max_score = 0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    matches += 1
                    # Calculate score based on pattern length and match position
                    pattern_length = len(pattern)
                    match_pos = query_lower.find(re.search(pattern, query_lower, re.IGNORECASE).group())
                    score = (pattern_length / len(query)) * (1 - match_pos / len(query)) if query else 0
                    max_score = max(max_score, score)
            
            if matches > 0:
                confidence = min(0.5 + (matches * 0.1) + max_score, 1.0)
                intents_with_scores.append((intent, confidence))
        
        # Sort by confidence
        intents_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # If no intent detected, default to chat
        if not intents_with_scores:
            intents_with_scores = [('chat', 0.5)]
        
        return intents_with_scores
    
    def extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities like names, places, dates from query"""
        entities = {
            'names': [],
            'places': [],
            'dates': [],
            'numbers': [],
            'keywords': []
        }
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', query)
        entities['numbers'] = [int(n) for n in numbers]
        
        # Extract potential names (capitalized words)
        if self.detect_language(query) == 'english':
            words = query.split()
            for i, word in enumerate(words):
                if word and word[0].isupper() and len(word) > 2:
                    # Check if it might be a name
                    if i > 0 and words[i-1].lower() in ['mr', 'ms', 'dr', 'prof']:
                        entities['names'].append(word)
                    elif word not in ['The', 'This', 'That', 'What', 'Who']:
                        entities['names'].append(word)
        
        return entities
    
    # ========== CONTEXT MANAGEMENT ==========
    
    def update_context(self, user_id: str, query: str, response: Dict, intents: List):
        """Update conversation memory with context"""
        memory = self.conversation_memory[user_id]
        
        # Add to history
        memory['history'].append({
            'query': query,
            'response': response.get('response', ''),
            'intents': intents,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep last 10 messages
        if len(memory['history']) > 10:
            memory['history'] = memory['history'][-10:]
        
        # Update preferences based on intents
        for intent, score in intents:
            if intent not in memory['preferences']:
                memory['preferences'][intent] = []
            memory['preferences'][intent].append(score)
        
        # Update last intents and language
        memory['last_intents'] = [i[0] for i in intents[:3]]
        memory['last_language'] = response.get('language', 'urdu')
        
        # Update context
        memory['context']['last_query'] = query
        memory['context']['last_response_type'] = response.get('type', 'chat')
    
    def get_context(self, user_id: str) -> Dict:
        """Get conversation context for user"""
        return self.conversation_memory.get(user_id, {})
    
    # ========== MAIN PROCESSING METHOD ==========
    
    async def process_query(self, 
                           query: str, 
                           user_id: str = None,
                           options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main method - intelligently process user query and use best APIs
        """
        if not user_id:
            user_id = 'anonymous'
        
        # Detect language and intents
        language = self.detect_language(query)
        intents_with_scores = self.detect_intent(query)
        entities = self.extract_entities(query)
        
        logger.info(f"🔍 Query: '{query}' | Language: {language} | Intents: {intents_with_scores[:3]}")
        
        # Get conversation context
        context = self.get_context(user_id)
        
        # Prepare tasks based on intents
        tasks = []
        intent_results = {}
        
        # Get top intents (max 3)
        top_intents = intents_with_scores[:3]
        
        for intent, confidence in top_intents:
            if confidence > 0.3:  # Only process if confident enough
                task = self._create_task_for_intent(intent, query, language, entities, options)
                if task:
                    tasks.append((intent, task))
        
        # Always add chat as fallback if no tasks
        if not tasks:
            tasks.append(('chat', self.chat.chat(
                messages=[{"role": "user", "content": query}],
                provider="auto",
                language=language
            )))
        
        # Execute tasks concurrently
        if tasks:
            for intent, task in tasks:
                try:
                    result = await task
                    intent_results[intent] = result
                except Exception as e:
                    logger.error(f"Error in {intent} task: {e}")
                    intent_results[intent] = {"error": str(e)}
        
        # Generate final response
        response = await self._generate_response(
            query=query,
            intent_results=intent_results,
            language=language,
            context=context,
            options=options
        )
        
        # Update conversation memory
        self.update_context(user_id, query, response, intents_with_scores)
        
        return response
    
    def _create_task_for_intent(self, intent: str, query: str, language: str, entities: Dict, options: Dict) -> Optional[asyncio.Task]:
        """Create appropriate async task for intent"""
        
        if intent == 'wikipedia':
            wiki_lang = 'ur' if language == 'urdu' else 'en'
            return self.wiki.search(query, wiki_lang)
        
        elif intent == 'news':
            news_lang = 'ur,en' if language == 'urdu' else 'en'
            return self.news.get_all_news(query, news_lang)
        
        elif intent == 'books':
            book_lang = 'ur' if language == 'urdu' else 'en'
            # Try both Google Books and Open Library
            return asyncio.gather(
                self.books.search_books(query, book_lang),
                self.openlibrary.search_books(query, 1, 5),
                return_exceptions=True
            )
        
        elif intent == 'web_search':
            return self.tavily.search(query, max_results=5)
        
        elif intent == 'image_generation':
            return self.image.generate(
                prompt=query,
                model=options.get('image_model', 'dalle-3'),
                size=options.get('image_size', '1024x1024')
            )
        
        elif intent == 'research':
            return self.research.start_research(
                query=query,
                depth=options.get('research_depth', 'standard'),
                user_id='smart_chat'
            )
        
        elif intent == 'weather':
            # Weather API call (implement separately)
            return None
        
        elif intent == 'time_date':
            # Return current time/date
            now = datetime.now()
            return {
                'time': now.strftime('%H:%M'),
                'date': now.strftime('%Y-%m-%d'),
                'day': now.strftime('%A'),
                'month': now.strftime('%B')
            }
        
        elif intent == 'calculation':
            # Simple calculator (implement separately)
            return None
        
        elif intent == 'translation':
            # Use HuggingFace for translation
            return self.huggingface.inference(
                model="Helsinki-NLP/opus-mt-en-ur",
                inputs=query
            )
        
        elif intent == 'code':
            # Use DeepSeek for coding
            return self.chat.chat(
                messages=[
                    {"role": "system", "content": "You are a coding expert. Provide code solutions."},
                    {"role": "user", "content": query}
                ],
                provider="deepseek",
                language='english'
            )
        
        return None
    
    async def _generate_response(self, 
                                query: str,
                                intent_results: Dict,
                                language: str,
                                context: Dict,
                                options: Dict) -> Dict[str, Any]:
        """Generate final response from all results"""
        
        response_parts = []
        sources = []
        response_type = 'chat'
        
        # Process each intent result
        for intent, result in intent_results.items():
            if isinstance(result, dict) and result.get('error'):
                continue
            
            formatted = await self._format_intent_result(intent, result, language)
            if formatted:
                response_parts.append(formatted)
                sources.append(intent)
                response_type = intent
        
        # If no results, use chat
        if not response_parts:
            chat_result = await self.chat.chat(
                messages=[{"role": "user", "content": query}],
                provider="auto",
                language=language
            )
            
            if chat_result and chat_result.get('choices'):
                response_parts.append(chat_result['choices'][0]['message']['content'])
                response_type = 'chat'
        
        # Combine response parts
        final_response = '\n\n'.join(response_parts)
        
        # Truncate if too long
        if len(final_response) > 2000:
            final_response = final_response[:2000] + "..."
        
        return {
            'response': final_response,
            'sources': list(set(sources)),
            'language': language,
            'type': response_type,
            'intents': list(intent_results.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _format_intent_result(self, intent: str, result: Any, language: str) -> Optional[str]:
        """Format result based on intent type"""
        
        try:
            if intent == 'wikipedia' and isinstance(result, dict):
                template = self.templates['wikipedia'].get(language, self.templates['wikipedia']['english'])
                return template.format(
                    extract=result.get('extract', '')[:500],
                    url=result.get('url', '#')
                )
            
            elif intent == 'news' and isinstance(result, list):
                template = self.templates['news'].get(language, self.templates['news']['english'])
                news_items = '\n'.join([
                    f"• {item.get('title', '')[:100]}"
                    for item in result[:5]
                ])
                return template.format(news_items=news_items)
            
            elif intent == 'books' and isinstance(result, tuple):
                # Combined Google Books and Open Library
                google_books, open_library = result
                all_books = []
                
                if isinstance(google_books, dict) and not isinstance(google_books, Exception):
                    all_books.extend(google_books.get('books', [])[:3])
                
                if isinstance(open_library, dict) and not isinstance(open_library, Exception):
                    all_books.extend(open_library.get('books', [])[:3])
                
                if all_books:
                    template = self.templates['books'].get(language, self.templates['books']['english'])
                    books_text = '\n'.join([
                        f"• {book.get('title', '')} - {book.get('author', '')}"
                        for book in all_books[:5]
                    ])
                    return template.format(books=books_text, source='Google Books & Open Library')
            
            elif intent == 'web_search' and isinstance(result, dict):
                template = self.templates['web_search'].get(language, self.templates['web_search']['english'])
                answer = result.get('answer', '')
                sources_list = result.get('results', [])
                sources_text = ', '.join([s.get('title', '')[:30] for s in sources_list[:3]])
                
                return template.format(
                    answer=answer[:300],
                    sources=sources_text or 'Multiple sources'
                )
            
            elif intent == 'image_generation' and isinstance(result, dict):
                if result.get('success'):
                    template = self.templates['image'].get(language, self.templates['image']['english'])
                    return template.format(url=result.get('images', [{}])[0].get('url', '#'))
            
            elif intent == 'research' and isinstance(result, dict):
                if result.get('research_id'):
                    # Wait a bit for research to complete
                    await asyncio.sleep(2)
                    research_result = await self.research.get_results(result['research_id'])
                    
                    if research_result.get('status') == 'completed':
                        template = self.templates['research'].get(language, self.templates['research']['english'])
                        return template.format(
                            summary=research_result.get('summary', '')[:300],
                            confidence=int(research_result.get('confidence_score', 0) * 100),
                            sources_count=len(research_result.get('sources', []))
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Error formatting {intent} result: {e}")
            return None
    
    # ========== UTILITY METHODS ==========
    
    async def get_suggestions(self, query: str, user_id: str = None) -> List[str]:
        """Get smart suggestions based on query and context"""
        suggestions = []
        
        # Get context
        context = self.get_context(user_id) if user_id else {}
        
        # Detect intent
        intents = self.detect_intent(query)
        
        # Generate suggestions based on intents
        for intent, confidence in intents[:2]:
            if intent == 'wikipedia':
                suggestions.append("کیا آپ مزید تفصیلات چاہتے ہیں؟")
                suggestions.append("Tell me more about this topic")
            
            elif intent == 'news':
                suggestions.append("تازہ ترین خبریں دکھائیں")
                suggestions.append("Show me sports news")
            
            elif intent == 'books':
                suggestions.append("Similar books by this author")
                suggestions.append("اس موضوع پر مزید کتابیں")
            
            elif intent == 'image_generation':
                suggestions.append("Generate a different style")
                suggestions.append("اور بھی تصاویر بناؤ")
        
        # Add default suggestions
        if not suggestions:
            suggestions = [
                "Pakistan ke bary mein batayein",
                "Latest news in Pakistan",
                "Generate image of Lahore",
                "Urdu poetry books"
            ]
        
        return suggestions[:4]  # Max 4 suggestions
    
    async def get_capabilities(self, language: str = 'urdu') -> Dict:
        """Get bot capabilities in user's language"""
        
        capabilities = {
            'urdu': {
                'title': 'پاک چیٹ کی صلاحیتیں',
                'description': 'میں آپ کی ان کاموں میں مدد کر سکتا ہوں:',
                'features': [
                    '🤖 **مختلف AI ماڈلز** - DeepSeek, Groq, GPT-4, Claude',
                    '📚 **ویکیپیڈیا** - اردو، انگریزی، ہندی اور مزید',
                    '📰 **خبریں** - تازہ ترین خبریں',
                    '📖 **کتابیں** - Google Books اور Open Library',
                    '🌐 **ویب تلاش** - Tavily کے ذریعے',
                    '🎨 **تصویر بنانا** - DALL-E, Stable Diffusion',
                    '🔬 **تحقیق** - گہری تحقیق اور رپورٹس',
                    '🗣️ **آواز** - تقریر سے متن، متن سے تقریر',
                    '📊 **ڈیٹا** - Kaggle datasets',
                    '🤗 **Hugging Face** - 300,000+ AI ماڈلز'
                ]
            },
            'english': {
                'title': 'PakChat Capabilities',
                'description': 'I can help you with:',
                'features': [
                    '🤖 **Multiple AI Models** - DeepSeek, Groq, GPT-4, Claude',
                    '📚 **Wikipedia** - Urdu, English, Hindi, and more',
                    '📰 **News** - Latest headlines',
                    '📖 **Books** - Google Books & Open Library',
                    '🌐 **Web Search** - Powered by Tavily',
                    '🎨 **Image Generation** - DALL-E, Stable Diffusion',
                    '🔬 **Deep Research** - Comprehensive reports',
                    '🗣️ **Voice** - Speech to text, text to speech',
                    '📊 **Data** - Kaggle datasets',
                    '🤗 **Hugging Face** - 300,000+ AI models'
                ]
            }
        }
        
        return capabilities.get(language, capabilities['urdu'])