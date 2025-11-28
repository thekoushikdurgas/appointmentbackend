"""Service for Google Gemini AI integration."""

from typing import Any, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Gemini SDK not available. Install with: pip install google-genai")


class GeminiService:
    """Service for interacting with Google Gemini AI."""

    def __init__(self):
        """Initialize Gemini service."""
        self.api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured")
        self.client = None
        if GEMINI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.client = None

    async def analyze_email_risk(self, email: str) -> dict:
        """
        Analyze email address for potential risk factors.
        
        Args:
            email: Email address to analyze
            
        Returns:
            Dictionary with riskScore, analysis, isRoleBased, isDisposable
        """
        if not self.client:
            logger.warning("Gemini client not available, returning fallback response")
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

            model = self.client.models.get("gemini-2.0-flash-exp")
            response = model.generate_content(
                prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "riskScore": {"type": "number"},
                            "analysis": {"type": "string"},
                            "isRoleBased": {"type": "boolean"},
                            "isDisposable": {"type": "boolean"},
                        },
                        "required": ["riskScore", "analysis", "isRoleBased", "isDisposable"],
                    },
                },
            )
            import json
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
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
        if not self.client:
            logger.warning("Gemini client not available, returning fallback summary")
            return f"Leading innovator in the {industry} space, providing scalable solutions for modern enterprises."

        try:
            prompt = f"""Write a professional, concise 2-sentence business summary for a company named "{company_name}" in the "{industry}" industry. Focus on their potential value proposition."""

            model = self.client.models.get("gemini-2.0-flash-exp")
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return f"Leading innovator in the {industry} space, providing scalable solutions for modern enterprises."

    async def generate_chat_response(
        self,
        user_message: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        """
        Generate AI chat response using Gemini.
        
        Args:
            user_message: The user's message
            chat_history: Optional list of previous messages in the conversation
            
        Returns:
            AI response text
        """
        if not self.client:
            logger.warning("Gemini client not available, returning fallback response")
            return "I'm NexusAI, your smart CRM assistant. I can help you find contacts, search for leads, and get insights about companies. However, AI features are currently unavailable. Please check the API configuration."

        try:
            # Build system context about CRM capabilities
            system_context = """You are NexusAI, a smart CRM assistant for Contact360. You help users with:
- Finding contacts matching specific criteria (titles, locations, industries, etc.)
- Searching for leads in specific industries or locations
- Getting insights about companies
- Answering questions about CRM data
- Natural language queries about contacts and companies

Be helpful, concise, and professional. When users ask about finding contacts or leads, provide guidance on what criteria they can use. If they ask specific questions about data, acknowledge that you can help them search once they provide the criteria."""

            # Build conversation history
            conversation_parts = [system_context]
            
            if chat_history:
                for msg in chat_history[-10:]:  # Limit to last 10 messages for context
                    sender = msg.get("sender", "")
                    text = msg.get("text", "")
                    if sender == "user":
                        conversation_parts.append(f"User: {text}")
                    elif sender == "ai":
                        conversation_parts.append(f"Assistant: {text}")
            
            # Add current user message
            conversation_parts.append(f"User: {user_message}")
            conversation_parts.append("Assistant:")
            
            # Combine into prompt
            prompt = "\n\n".join(conversation_parts)

            model = self.client.models.get("gemini-2.0-flash-exp")
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API Error in chat: {e}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again later or rephrase your question."

