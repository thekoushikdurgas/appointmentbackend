"""Unit tests for Connectra client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients.connectra_client import ConnectraClient, ConnectraClientError
from app.schemas.vql import VQLQuery


class TestConnectraClient:
    """Test cases for ConnectraClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = ConnectraClient(
            base_url="http://localhost:8000",
            api_key="test-key",
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_search_contacts_success(self):
        """Test successful contact search."""
        mock_response = {
            "data": [{"id": 1, "uuid": "test-uuid"}],
            "success": True,
        }
        
        vql_query = VQLQuery(page=1, limit=25)
        
        with patch.object(self.client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await self.client.search_contacts(vql_query)
            
            assert result == mock_response
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_contacts_error(self):
        """Test contact search with error."""
        vql_query = VQLQuery(page=1, limit=25)
        
        with patch.object(self.client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = ConnectraClientError("API error")
            
            with pytest.raises(ConnectraClientError):
                await self.client.search_contacts(vql_query)

    @pytest.mark.asyncio
    async def test_count_contacts(self):
        """Test contact counting."""
        mock_response = {"count": 42, "success": True}
        
        vql_query = VQLQuery(page=1, limit=25)
        
        with patch.object(self.client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            count = await self.client.count_contacts(vql_query)
            
            assert count == 42

    @pytest.mark.asyncio
    async def test_get_filters(self):
        """Test getting filters."""
        mock_response = {
            "data": [
                {
                    "id": 1,
                    "key": "first_name",
                    "service": "contact",
                    "display_name": "First Name",
                    "direct_derived": True,
                }
            ],
            "success": True,
        }
        
        with patch.object(self.client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            filters = await self.client.get_filters("contact")
            
            assert len(filters) == 1
            assert filters[0]["key"] == "first_name"

