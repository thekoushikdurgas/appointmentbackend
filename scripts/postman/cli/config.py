"""CLI configuration management."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


@dataclass
class CLIProfile:
    """CLI profile configuration."""
    name: str
    base_url: str
    email: Optional[str] = None
    password: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    write_key: Optional[str] = None
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None
    timeout: int = 30
    retry_max: int = 3
    retry_backoff: float = 1.5
    test_mode: str = "hybrid"
    output_dir: Optional[str] = None
    auto_create_test_user: bool = True


@dataclass
class CLIConfig:
    """Main CLI configuration."""
    default_profile: str = "default"
    profiles: Dict[str, CLIProfile] = field(default_factory=dict)
    csv_dir: Optional[str] = None
    collection_dir: Optional[str] = None
    reports_dir: Optional[str] = None
    monitoring_enabled: bool = False
    monitoring_interval: int = 300  # seconds
    monitoring_alert_threshold: float = 0.8  # 80% failure rate triggers alert


class ConfigManager:
    """Manages CLI configuration and profiles."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to config file (default: ~/.contact360-cli/config.json)
        """
        if config_path is None:
            config_dir = Path.home() / ".contact360-cli"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "config.json"
        
        self.config_path = config_path
        self.config = self._load_config()
        self._ensure_default_profile()
    
    def _load_config(self) -> CLIConfig:
        """Load configuration from file."""
        if not self.config_path.exists():
            return CLIConfig()
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            config = CLIConfig(
                default_profile=data.get("default_profile", "default"),
                csv_dir=data.get("csv_dir"),
                collection_dir=data.get("collection_dir"),
                reports_dir=data.get("reports_dir"),
                monitoring_enabled=data.get("monitoring_enabled", False),
                monitoring_interval=data.get("monitoring_interval", 300),
                monitoring_alert_threshold=data.get("monitoring_alert_threshold", 0.8)
            )
            
            # Load profiles
            for name, profile_data in data.get("profiles", {}).items():
                config.profiles[name] = CLIProfile(**profile_data)
            
            return config
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return CLIConfig()
    
    def _ensure_default_profile(self):
        """Ensure default profile exists."""
        if "default" not in self.config.profiles:
            # Create default profile from environment
            default_profile = CLIProfile(
                name="default",
                base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
                email=os.getenv("TEST_EMAIL") or os.getenv("API_TEST_EMAIL"),
                password=os.getenv("TEST_PASSWORD") or os.getenv("API_TEST_PASSWORD"),
                access_token=os.getenv("ACCESS_TOKEN"),
                refresh_token=os.getenv("REFRESH_TOKEN"),
                write_key=os.getenv("WRITE_KEY"),
                admin_email=os.getenv("ADMIN_EMAIL") or os.getenv("TEST_ADMIN_EMAIL"),
                admin_password=os.getenv("ADMIN_PASSWORD") or os.getenv("TEST_ADMIN_PASSWORD"),
                timeout=int(os.getenv("TIMEOUT", "30")),
                retry_max=int(os.getenv("RETRY_MAX", "3")),
                retry_backoff=float(os.getenv("RETRY_BACKOFF", "1.5")),
                test_mode=os.getenv("TEST_MODE", "hybrid"),
                output_dir=os.getenv("OUTPUT_DIR"),
                auto_create_test_user=os.getenv("AUTO_CREATE_TEST_USER", "true").lower() == "true"
            )
            self.config.profiles["default"] = default_profile
            self.save_config()
    
    def save_config(self):
        """Save configuration to file."""
        try:
            data = {
                "default_profile": self.config.default_profile,
                "csv_dir": self.config.csv_dir,
                "collection_dir": self.config.collection_dir,
                "reports_dir": self.config.reports_dir,
                "monitoring_enabled": self.config.monitoring_enabled,
                "monitoring_interval": self.config.monitoring_interval,
                "monitoring_alert_threshold": self.config.monitoring_alert_threshold,
                "profiles": {name: asdict(profile) for name, profile in self.config.profiles.items()}
            }
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
    
    def get_profile(self, name: Optional[str] = None) -> CLIProfile:
        """Get a profile by name.
        
        Args:
            name: Profile name (default: uses default_profile)
        
        Returns:
            CLIProfile instance
        """
        profile_name = name or self.config.default_profile
        if profile_name not in self.config.profiles:
            raise ValueError(f"Profile '{profile_name}' not found")
        return self.config.profiles[profile_name]
    
    def add_profile(self, profile: CLIProfile):
        """Add or update a profile.
        
        Args:
            profile: CLIProfile instance
        """
        self.config.profiles[profile.name] = profile
        self.save_config()
    
    def remove_profile(self, name: str):
        """Remove a profile.
        
        Args:
            name: Profile name
        """
        if name == "default":
            raise ValueError("Cannot remove default profile")
        if name in self.config.profiles:
            del self.config.profiles[name]
            self.save_config()
    
    def list_profiles(self) -> Dict[str, CLIProfile]:
        """List all profiles.
        
        Returns:
            Dictionary of profile names to CLIProfile instances
        """
        return self.config.profiles.copy()
    
    def set_default_profile(self, name: str):
        """Set default profile.
        
        Args:
            name: Profile name
        """
        if name not in self.config.profiles:
            raise ValueError(f"Profile '{name}' not found")
        self.config.default_profile = name
        self.save_config()

