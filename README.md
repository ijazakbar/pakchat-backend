# PakChat Backend API

FastAPI backend for PakChat with 23+ AI providers.

## 🚀 Features
- 23+ AI Providers (OpenAI, Google, Groq, DeepSeek, Anthropic, etc.)
- Wikipedia Search (10+ languages)
- Tavily Web Search
- News Aggregator (3 providers)
- Google Books & Open Library
- Voice Processing (AssemblyAI + ElevenLabs)
- Image Generation (Replicate + FAL AI)
- JWT Authentication
- Supabase Integration
- Redis Caching

## 📦 Installation

```bash
git clone https://github.com/ijazakbar/pakchat-backend.git
cd pakchat-backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn main:app --reload
