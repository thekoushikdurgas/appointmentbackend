"""Service for Google Gemini AI integration with chat sessions and streaming."""

import asyncio
import json
import re
from typing import Any, AsyncGenerator, Optional

from app.core.ai_config import get_ai_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiService:
    """Service for interacting with Google Gemini AI with chat session support."""

    def __init__(self, ai_settings: Optional[Any] = None):
        """Initialize Gemini service."""
        self.ai_settings = ai_settings or get_ai_settings()
        self.api_key = self.ai_settings.GEMINI_API_KEY
        
        if not self.api_key:
            self.configured = False
        else:
            self.configured = True
            
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                self.configured = False
        else:
            self.configured = False
            
        # Store active chat sessions per conversation
        self._chat_sessions: dict[str, Any] = {}

    async def analyze_email_risk(self, email: str) -> dict:
        """
        Analyze email address for potential risk factors.
        
        Args:
            email: Email address to analyze
            
        Returns:
            Dictionary with riskScore, analysis, isRoleBased, isDisposable
        """
        if not self.configured:
            return {
                "riskScore": 15,
                "analysis": "AI analysis unavailable (Check API Key). Returning simulated safe result.",
                "isRoleBased": False,
                "isDisposable": False,
            }

        try:
            prompt = f"""Analyze the email address "{email}" for potential risk factors in a B2B context. 
            Consider the domain reputation (simulate a check based on common patterns), syntax, and likelihood of being a disposable or role-based email.
            Return a JSON object with:
            - riskScore: number from 0 (safe) to 100 (high risk)
            - analysis: brief 1-2 sentence explanation
            - isRoleBased: boolean
            - isDisposable: boolean"""

            model = self._get_model("gemini-1.5-flash")
            if not model:
                raise Exception("Model not available")
                
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                ),
            )
            result = json.loads(response.text)
            return result
        except Exception as e:
            return {
                "riskScore": 15,
                "analysis": "AI analysis unavailable. Returning simulated safe result.",
                "isRoleBased": False,
                "isDisposable": False,
            }

    async def generate_company_summary(self, company_name: str, industry: str) -> str:
        """
        Generate AI-powered company summary.
        
        Args:
            company_name: Name of the company
            industry: Industry sector
            
        Returns:
            Company summary text
        """
        if not self.configured:
            return f"Leading innovator in the {industry} space, providing scalable solutions for modern enterprises."

        try:
            prompt = f"""Write a professional, concise 2-sentence business summary for a company named "{company_name}" in the "{industry}" industry. Focus on their potential value proposition."""

            model = self._get_model("gemini-1.5-flash")
            if not model:
                raise Exception("Model not available")
                
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text.strip()
        except Exception as e:
            return f"Leading innovator in the {industry} space, providing scalable solutions for modern enterprises."

    async def parse_contact_filters(self, query: str) -> dict:
        """
        Parse natural language query into structured contact filter parameters.
        
        Args:
            query: Natural language query (e.g., "VP of Engineering at tech companies")
            
        Returns:
            Dictionary with filter parameters: job_titles, company_names, industry, 
            location, employees, seniority
        """
        if not self.configured:
            # Fallback to basic pattern matching
            return self._fallback_parse_filters(query)

        try:
            prompt = f"""Parse the following natural language query into structured contact filter parameters.
Query: "{query}"

Extract the following information if present:
- Job titles (e.g., "VP", "CEO", "Director", "Engineer")
- Company names
- Industry sectors
- Location (city, state, country)
- Employee count range (e.g., ">100", "50-200")
- Seniority levels (e.g., "CXO", "VP", "Director", "Manager")

Return a JSON object with these keys (use null for missing values):
{{
    "job_titles": ["list of job titles"],
    "company_names": ["list of company names"],
    "industry": ["list of industries"],
    "location": ["list of locations"],
    "employees": [min, max] or null,
    "seniority": ["list of seniority levels"]
}}

Only include keys that have values. Return valid JSON only."""

            model = self._get_model("gemini-1.5-flash")
            if not model:
                return self._fallback_parse_filters(query)
                
            response = await asyncio.to_thread(model.generate_content, prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response (might have markdown code blocks)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(result_text)
            return parsed
        except Exception as e:
            # Fallback to pattern matching on error
            return self._fallback_parse_filters(query)

    def _fallback_parse_filters(self, query: str) -> dict:
        """Fallback pattern matching for filter parsing."""
        result = {}
        lower_query = query.lower()
        
        # Job titles
        job_titles = []
        if "vp" in lower_query or "vice president" in lower_query:
            job_titles.append("VP")
        if "ceo" in lower_query or "chief executive" in lower_query:
            job_titles.append("CEO")
        if "director" in lower_query:
            job_titles.append("Director")
        if "manager" in lower_query:
            job_titles.append("Manager")
        if "engineer" in lower_query or "engineering" in lower_query:
            job_titles.append("Engineer")
        if job_titles:
            result["job_titles"] = job_titles
        
        # Industry
        if "tech" in lower_query or "technology" in lower_query:
            result["industry"] = ["Technology"]
        if "finance" in lower_query or "financial" in lower_query:
            result["industry"] = result.get("industry", []) + ["Finance"]
        
        # Employee count
        employee_match = re.search(r'(\d+)', query)
        if employee_match:
            num = int(employee_match.group(1))
            if ">" in query or "more than" in lower_query or "over" in lower_query:
                result["employees"] = [num, 10000]
        
        # Seniority
        seniority = []
        if "executive" in lower_query or "exec" in lower_query:
            seniority.append("CXO")
        if "vp" in lower_query:
            seniority.append("VP")
        if seniority:
            result["seniority"] = seniority
        
        return result

    def _get_model(self, model_name: Optional[str] = None) -> Any:
        """Get a configured Gemini model instance."""
        if not self.configured or not GEMINI_AVAILABLE:
            return None
            
        model_name = model_name or self.ai_settings.GEMINI_MODEL
        
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=self.ai_settings.GEMINI_TEMPERATURE,
                top_p=self.ai_settings.GEMINI_TOP_P,
                top_k=self.ai_settings.GEMINI_TOP_K,
                max_output_tokens=self.ai_settings.GEMINI_MAX_OUTPUT_TOKENS,
            )
            
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config,
                system_instruction=self.ai_settings.GEMINI_SYSTEM_INSTRUCTION,
            )
            return model
        except Exception as e:
            return None

    def _convert_history_to_gemini_format(
        self, chat_history: Optional[list[dict[str, Any]]] = None
    ) -> list[dict[str, str]]:
        """Convert chat history from our format to Gemini's format."""
        if not chat_history:
            return []
        
        gemini_history = []
        for msg in chat_history:
            sender = msg.get("sender", "")
            text = msg.get("text", "")
            
            if sender == "user":
                gemini_history.append({"role": "user", "parts": [text]})
            elif sender == "ai":
                gemini_history.append({"role": "model", "parts": [text]})
        
        return gemini_history

    def _get_or_create_chat_session(
        self,
        conversation_id: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        model_name: Optional[str] = None,
    ) -> Optional[Any]:
        """Get or create a chat session for a conversation."""
        if not self.configured:
            return None
            
        # Check if we have an existing session
        if conversation_id in self._chat_sessions:
            return self._chat_sessions[conversation_id]
        
        # Create new session
        model = self._get_model(model_name)
        if not model:
            return None
        
        # Convert history to Gemini format
        history = self._convert_history_to_gemini_format(chat_history)
        
        try:
            chat = model.start_chat(history=history)
            self._chat_sessions[conversation_id] = chat
            return chat
        except Exception as e:
            return None

    async def generate_chat_response(
        self,
        user_message: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        conversation_id: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """
        Generate AI chat response using Gemini with proper chat session management.
        
        Args:
            user_message: The user's message
            chat_history: Optional list of previous messages in the conversation
            conversation_id: Optional conversation ID for session management
            model_name: Optional model name override
            
        Returns:
            AI response text
        """
        if not self.configured:
            return "I'm NexusAI, your smart CRM assistant. I can help you find contacts, search for leads, and get insights about companies. However, AI features are currently unavailable. Please check the API configuration."

        # Use conversation_id or generate one
        conv_id = conversation_id or "default"
        
        # Get or create chat session
        chat = self._get_or_create_chat_session(conv_id, chat_history, model_name)
        if not chat:
            return "I apologize, but I'm having trouble processing your request right now. Please try again later or rephrase your question."

        try:
            # Send message and get response
            response = await asyncio.to_thread(chat.send_message, user_message)
            return response.text.strip()
        except Exception as e:
            # Clear the session on error to force recreation
            if conv_id in self._chat_sessions:
                del self._chat_sessions[conv_id]
            return "I apologize, but I'm having trouble processing your request right now. Please try again later or rephrase your question."

    async def generate_chat_response_stream(
        self,
        user_message: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        conversation_id: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI chat response using Gemini with proper chat session management.
        
        Args:
            user_message: The user's message
            chat_history: Optional list of previous messages in the conversation
            conversation_id: Optional conversation ID for session management
            model_name: Optional model name override
            
        Yields:
            Chunks of AI response text
        """
        if not self.configured:
            yield "I'm NexusAI, your smart CRM assistant. I can help you find contacts, search for leads, and get insights about companies. However, AI features are currently unavailable. Please check the API configuration."
            return

        # Use conversation_id or generate one
        conv_id = conversation_id or "default"
        
        # Get or create chat session
        chat = self._get_or_create_chat_session(conv_id, chat_history, model_name)
        if not chat:
            yield "I apologize, but I'm having trouble processing your request right now. Please try again later or rephrase your question."
            return

        try:
            # Send message with streaming
            response = await asyncio.to_thread(chat.send_message, user_message, stream=True)
            
            # Yield chunks as they arrive
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            # Clear the session on error
            if conv_id in self._chat_sessions:
                del self._chat_sessions[conv_id]
            yield "I apologize, but I'm having trouble processing your request right now. Please try again later or rephrase your question."

    def clear_chat_session(self, conversation_id: str) -> None:
        """Clear a chat session."""
        if conversation_id in self._chat_sessions:
            del self._chat_sessions[conversation_id]

    def clear_all_sessions(self) -> None:
        """Clear all chat sessions."""
        self._chat_sessions.clear()

