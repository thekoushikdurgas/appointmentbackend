"""Service for analyzing contact and company data quality."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.companies import Company
from app.models.contacts import Contact
from app.utils.company_name_utils import clean_company_name, is_valid_company_name
from app.utils.keyword_utils import clean_keyword_array, is_valid_keyword
from app.utils.title_utils import clean_title, is_valid_title

logger = get_logger(__name__)


class AnalysisService:
    """Service for analyzing data quality."""

    def __init__(self):
        """Initialize analysis service."""
        # Use cleaning utilities from app.utils
        self.clean_company_name = clean_company_name
        self.clean_keyword_array = clean_keyword_array
        self.clean_title = clean_title
        self.is_valid_company_name = is_valid_company_name
        self.is_valid_keyword = is_valid_keyword
        self.is_valid_title = is_valid_title

    def _check_international_chars(self, text: Optional[str]) -> bool:
        """Check if text contains international characters."""
        if not text:
            return False
        return any(ord(c) > 127 for c in text)

    def _check_encoding_issues(self, text: Optional[str]) -> bool:
        """Check if text has encoding issues (question marks, replacement chars)."""
        if not text:
            return False
        return "?" in text or "\ufffd" in text

    def _check_emoji(self, text: Optional[str]) -> bool:
        """Check if text contains emoji."""
        if not text:
            return False
        # Common emoji ranges
        emoji_ranges = [
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
            (0x1F680, 0x1F6FF),  # Transport and Map
            (0x1F1E0, 0x1F1FF),  # Flags
            (0x2600, 0x26FF),    # Misc symbols
            (0x2700, 0x27BF),    # Dingbats
        ]
        for char in text:
            code = ord(char)
            for start, end in emoji_ranges:
                if start <= code <= end:
                    return True
        return False

    async def analyze_contact(
        self,
        session: AsyncSession,
        contact_uuid: str,
    ) -> Optional[dict]:
        """
        Analyze a single contact.
        
        Args:
            session: Database session
            contact_uuid: Contact UUID
            
        Returns:
            Dictionary with analysis results or None if contact not found
        """
        try:
            # Get contact
            result = await session.execute(
                select(Contact).where(Contact.uuid == contact_uuid)
            )
            contact = result.scalar_one_or_none()
            
            if not contact:
                return None
            
            title = contact.title
            title_valid = self.is_valid_title(title) if title else False
            title_cleaned = None
            title_needs_cleaning = False
            title_issues = []
            
            if title:
                title_cleaned = self.clean_title(title)
                title_needs_cleaning = title_cleaned != title
                
                if not title_valid:
                    title_issues.append("Invalid title format")
                if title_needs_cleaning:
                    title_issues.append("Title needs cleaning")
                if self._check_encoding_issues(title):
                    title_issues.append("Encoding issues detected")
                if self._check_emoji(title):
                    title_issues.append("Contains emoji")
            else:
                title_issues.append("Title is missing")
            
            return {
                "contact_uuid": contact_uuid,
                "title": title,
                "title_valid": title_valid,
                "title_needs_cleaning": title_needs_cleaning,
                "title_cleaned": title_cleaned,
                "title_issues": title_issues,
                "has_international_chars": self._check_international_chars(title),
                "has_encoding_issues": self._check_encoding_issues(title),
                "has_emoji": self._check_emoji(title),
            }
        except Exception as e:
            logger.exception("Error analyzing contact: uuid=%s", contact_uuid)
            raise

    async def analyze_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> Optional[dict]:
        """
        Analyze a single company.
        
        Args:
            session: Database session
            company_uuid: Company UUID
            
        Returns:
            Dictionary with analysis results or None if company not found
        """
        try:
            # Get company
            result = await session.execute(
                select(Company).where(Company.uuid == company_uuid)
            )
            company = result.scalar_one_or_none()
            
            if not company:
                return None
            
            name = company.name
            name_valid = self.is_valid_company_name(name) if name else False
            name_cleaned = None
            name_needs_cleaning = False
            name_issues = []
            
            if name:
                name_cleaned = self.clean_company_name(name)
                name_needs_cleaning = name_cleaned != name
                
                if not name_valid:
                    name_issues.append("Invalid company name format")
                if name_needs_cleaning:
                    name_issues.append("Name needs cleaning")
                if self._check_encoding_issues(name):
                    name_issues.append("Encoding issues detected")
                if self._check_emoji(name):
                    name_issues.append("Contains emoji")
            else:
                name_issues.append("Company name is missing")
            
            # Analyze keywords
            keywords = company.keywords
            keywords_valid = True
            keywords_needs_cleaning = False
            keywords_issues = []
            invalid_keywords_count = 0
            
            if keywords:
                cleaned_keywords = self.clean_keyword_array(keywords)
                keywords_needs_cleaning = cleaned_keywords != keywords
                
                for keyword in keywords:
                    if not self.is_valid_keyword(keyword):
                        invalid_keywords_count += 1
                        keywords_valid = False
                
                if invalid_keywords_count > 0:
                    keywords_issues.append(f"{invalid_keywords_count} invalid keyword(s)")
                if keywords_needs_cleaning:
                    keywords_issues.append("Keywords need cleaning")
            else:
                keywords_issues.append("No keywords")
            
            return {
                "company_uuid": company_uuid,
                "name": name,
                "name_valid": name_valid,
                "name_needs_cleaning": name_needs_cleaning,
                "name_cleaned": name_cleaned,
                "name_issues": name_issues,
                "has_international_chars": self._check_international_chars(name),
                "has_encoding_issues": self._check_encoding_issues(name),
                "has_emoji": self._check_emoji(name),
                "keywords_valid": keywords_valid,
                "keywords_needs_cleaning": keywords_needs_cleaning,
                "keywords_issues": keywords_issues,
                "invalid_keywords_count": invalid_keywords_count,
            }
        except Exception as e:
            logger.exception("Error analyzing company: uuid=%s", company_uuid)
            raise

    async def analyze_contacts_batch(
        self,
        session: AsyncSession,
        contact_uuids: list[str],
    ) -> list[dict]:
        """
        Analyze a batch of contacts.
        
        Args:
            session: Database session
            contact_uuids: List of contact UUIDs
            
        Returns:
            List of analysis results
        """
        results = []
        for uuid in contact_uuids:
            result = await self.analyze_contact(session, uuid)
            if result:
                results.append(result)
            else:
                # Contact not found - include with error
                results.append({
                    "contact_uuid": uuid,
                    "title": None,
                    "title_valid": False,
                    "title_needs_cleaning": False,
                    "title_cleaned": None,
                    "title_issues": ["Contact not found"],
                    "has_international_chars": False,
                    "has_encoding_issues": False,
                    "has_emoji": False,
                })
        return results

    async def analyze_companies_batch(
        self,
        session: AsyncSession,
        company_uuids: list[str],
    ) -> list[dict]:
        """
        Analyze a batch of companies.
        
        Args:
            session: Database session
            company_uuids: List of company UUIDs
            
        Returns:
            List of analysis results
        """
        results = []
        for uuid in company_uuids:
            result = await self.analyze_company(session, uuid)
            if result:
                results.append(result)
            else:
                # Company not found - include with error
                results.append({
                    "company_uuid": uuid,
                    "name": None,
                    "name_valid": False,
                    "name_needs_cleaning": False,
                    "name_cleaned": None,
                    "name_issues": ["Company not found"],
                    "has_international_chars": False,
                    "has_encoding_issues": False,
                    "has_emoji": False,
                    "keywords_valid": False,
                    "keywords_needs_cleaning": False,
                    "keywords_issues": ["Company not found"],
                    "invalid_keywords_count": 0,
                })
        return results

