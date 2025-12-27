"""Seed test entities with valid UUIDs for testing."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from .test_data import TestDataFixtures
from ..tests.config import TestConfig
from ..tests.auth import AuthHandler


class TestEntitySeeder:
    """Pre-create valid UUIDs for test entities."""
    
    def __init__(self, config: TestConfig, auth_handler: AuthHandler):
        """Initialize test entity seeder.
        
        Args:
            config: Test configuration
            auth_handler: Authentication handler
        """
        self.config = config
        self.auth_handler = auth_handler
        self.fixtures = TestDataFixtures(config, auth_handler)
        self.seed_file = config.output_dir / "test_seeds.json"
        self._seeds: Dict[str, Any] = {}
    
    def load_seeds(self) -> Dict[str, Any]:
        """Load existing seeds from file.
        
        Returns:
            Dictionary of seeded entity IDs
        """
        if self.seed_file.exists():
            try:
                with open(self.seed_file, 'r') as f:
                    self._seeds = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load seeds: {e}")
                self._seeds = {}
        else:
            self._seeds = {}
        
        return self._seeds
    
    def save_seeds(self):
        """Save seeds to file."""
        try:
            with open(self.seed_file, 'w') as f:
                json.dump(self._seeds, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save seeds: {e}")
    
    def seed_all(self) -> Dict[str, Any]:
        """Seed all test entities.
        
        Returns:
            Dictionary of seeded entity IDs
        """
        seeds = {}
        
        # Seed chat IDs
        chat_id = self.fixtures.get_test_chat_id()
        if chat_id:
            seeds["chat_id"] = chat_id
        
        # Seed company UUIDs (if Connectra API available)
        company_uuid = self.fixtures.get_test_company_uuid()
        if company_uuid:
            seeds["company_uuid"] = company_uuid
        
        # Seed contact UUIDs (if Connectra API available)
        contact_uuid = self.fixtures.get_test_contact_uuid()
        if contact_uuid:
            seeds["contact_uuid"] = contact_uuid
        
        # Seed export IDs
        export_id = self.fixtures.get_test_export_id()
        if export_id:
            seeds["export_id"] = export_id
        
        # Seed page IDs
        page_id = self.fixtures.get_test_page_id()
        if page_id:
            seeds["page_id"] = page_id
        
        self._seeds = seeds
        self.save_seeds()
        
        return seeds
    
    def get_seed(self, entity_type: str) -> Optional[str]:
        """Get a seeded entity ID by type.
        
        Args:
            entity_type: Type of entity (chat_id, company_uuid, contact_uuid, etc.)
        
        Returns:
            Entity ID string or None
        """
        return self._seeds.get(entity_type)
    
    def replace_placeholders(self, endpoint_path: str) -> str:
        """Replace placeholder IDs in endpoint path with actual seeded IDs.
        
        Args:
            endpoint_path: Endpoint path with placeholders like {chat_id}, {company_uuid}
        
        Returns:
            Endpoint path with placeholders replaced
        """
        path = endpoint_path
        
        # Replace common placeholders
        replacements = {
            "{chat_id}": self.get_seed("chat_id"),
            "{company_uuid}": self.get_seed("company_uuid"),
            "{contact_uuid}": self.get_seed("contact_uuid"),
            "{export_id}": self.get_seed("export_id"),
            "{page_id}": self.get_seed("page_id"),
            "{user_id}": self.get_seed("user_id"),
            "{tier}": self.get_seed("tier") or "starter",
            "{package_id}": self.get_seed("package_id"),
            "{file_id}": self.get_seed("file_id"),
            "{file_type}": self.get_seed("file_type") or "csv",
            "{slug}": self.get_seed("slug") or "test-slug",
        }
        
        for placeholder, value in replacements.items():
            if placeholder in path and value:
                path = path.replace(placeholder, value)
        
        return path

