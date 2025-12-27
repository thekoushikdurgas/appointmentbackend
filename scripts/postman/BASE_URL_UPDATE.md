# Base URL Update Summary

## Changes Made

All base URL configurations have been updated from `http://127.0.0.1:8000` to `http://34.229.94.175/` across the codebase.

## Files Updated

### 1. Configuration Files

#### `cli/config.py`
- **Line 101**: Updated default base URL in `_ensure_default_profile()` method
- Changed from: `os.getenv("API_BASE_URL", "http://34.229.94.175")`
- Changed to: `os.getenv("API_BASE_URL", "http://34.229.94.175/")`

#### `tests/config.py`
- **Line 52**: Updated default base URL in `TestConfig.__init__()`
- Changed from: `os.getenv("API_BASE_URL", "http://34.229.94.175")`
- Changed to: `os.getenv("API_BASE_URL", "http://34.229.94.175/")`

### 2. Command Files

#### `cli/commands/discover_commands.py`
- **Line 21**: Updated default in `scan()` command
- **Line 38**: Updated default in `sync_csv()` command
- Changed from: `"http://34.229.94.175"`
- Changed to: `"http://34.229.94.175/"`

### 3. URL Construction Normalization

To handle trailing slashes properly, URL construction has been normalized in:

#### `tests/executor.py`
- **Line 129**: Added URL normalization to prevent double slashes
- Normalizes base_url by removing trailing slash before constructing URLs

#### `tests/auth.py`
- **Line 72**: Normalized URL in `_register_user()` method
- **Line 109**: Normalized URL in `_login()` method  
- **Line 157**: Normalized URL in `refresh_access_token()` method
- **Line 285**: Normalized URL in `authenticate_admin()` method

#### `cli/commands/interactive_commands.py`
- **Line 108**: Normalized URL in `_handle_get()` method
- **Line 125-134**: Normalized URL in `_handle_post()` method
- **Line 157-165**: Normalized URL in `_handle_put()` method
- **Line 188**: Normalized URL in `_handle_delete()` method
- **Line 206-207**: Normalized URL in `_handle_auth()` method

## URL Normalization Strategy

All URL construction now follows this pattern:

```python
# Normalize base_url (remove trailing slash)
base_url = self.base_url.rstrip('/')
# Ensure endpoint starts with /
if not endpoint_path.startswith('/'):
    endpoint_path = '/' + endpoint_path
url = f"{base_url}{endpoint_path}"
```

This ensures:
- Base URL can be stored with or without trailing slash
- Endpoints can be provided with or without leading slash
- Final URLs are always correctly formatted (no double slashes)

## Configuration Priority

The base URL is determined in this order:
1. Command-line argument (if provided)
2. Environment variable `API_BASE_URL`
3. Default value: `http://34.229.94.175/`

## User Action Required

**IMPORTANT**: If you have an existing config file at `~/.contact360-cli/config.json` with the old URL (`127.0.0.1:8000`), you need to update it.

### Option 1: Delete and recreate config (Recommended)
```bash
# Delete old config (Windows)
del %USERPROFILE%\.contact360-cli\config.json

# Delete old config (Linux/Mac)
rm ~/.contact360-cli/config.json

# Run any command - new config will be created with correct URL
python main.py test run
```

### Option 2: Update existing config using CLI
```bash
# Update the default profile
python main.py config add default --base-url http://34.229.94.175/
```

### Option 3: Use environment variable
```bash
# Set environment variable (Windows)
set API_BASE_URL=http://34.229.94.175/

# Set environment variable (Linux/Mac)
export API_BASE_URL=http://34.229.94.175/
```

### Option 4: Manually edit config file
Edit `~/.contact360-cli/config.json` (or `%USERPROFILE%\.contact360-cli\config.json` on Windows) and change:
```json
{
  "profiles": {
    "default": {
      "base_url": "http://127.0.0.1:8000",  // OLD
      ...
    }
  }
}
```
to:
```json
{
  "profiles": {
    "default": {
      "base_url": "http://34.229.94.175/",  // NEW
      ...
    }
  }
}
```

## Testing

After updating, verify the configuration:

```bash
# Check current config
python main.py config show

# Test connection
python main.py test run --mode smoke
```

## Notes

- The trailing slash in the default URL (`http://34.229.94.175/`) is optional
- URL normalization handles both formats correctly
- All URL constructions now properly handle trailing slashes to prevent double slashes

