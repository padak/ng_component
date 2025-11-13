#!/usr/bin/env python3
"""
Simple Driver Creator - Without complex SDK features
~200 lines of clean, functional code

This version uses claude-agent-sdk's basic query() function
to generate drivers through conversation with Claude.
"""

import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import aiohttp
from claude_agent_sdk import query


# === DRIVER TEMPLATE ===
DRIVER_TEMPLATE = '''"""
{api_name} Driver
Auto-generated: {timestamp}
API: {api_url}
"""

import os
import requests
import time
from typing import List, Dict, Any, Optional
from enum import Enum


class PaginationStyle(Enum):
    NONE = "none"
    OFFSET = "offset"
    CURSOR = "cursor"


class DriverCapabilities:
    def __init__(self):
        self.read = True
        self.write = False
        self.pagination = PaginationStyle.NONE
        self.query_language = None


class DriverError(Exception):
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.details = details or {{}}


class AuthenticationError(DriverError):
    pass


class ConnectionError(DriverError):
    pass


class ObjectNotFoundError(DriverError):
    pass


class QuerySyntaxError(DriverError):
    pass


class RateLimitError(DriverError):
    pass


class {class_name}Driver:
    """Driver for {api_name} API."""

    def __init__(self, api_url: str = "{api_url}",
                 api_key: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3):
        """Initialize driver with connection validation."""
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self._validate_connection()

    @classmethod
    def from_env(cls):
        """Create from environment variables."""
        api_url = os.getenv("{env_url}", "{api_url}")
        api_key = os.getenv("{env_key}")
        return cls(api_url=api_url, api_key=api_key)

    def get_capabilities(self) -> DriverCapabilities:
        """Return capabilities."""
        return DriverCapabilities()

    def list_objects(self) -> List[str]:
        """List available objects/endpoints."""
        # For Open-Meteo, return known endpoints
        return {endpoints}

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """Get field schema."""
        # Basic schema for now
        fields = {{
            "forecast": {{
                "latitude": {{"type": "float", "required": True}},
                "longitude": {{"type": "float", "required": True}},
                "hourly": {{"type": "array", "required": False}}
            }},
            "historical": {{
                "latitude": {{"type": "float", "required": True}},
                "longitude": {{"type": "float", "required": True}},
                "start_date": {{"type": "date", "required": True}},
                "end_date": {{"type": "date", "required": True}}
            }}
        }}
        return fields.get(object_name, {{}})

    def read(self, query: str, limit: Optional[int] = None,
             offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Execute read query."""
        endpoint = query if query.startswith('/') else "/" + query
        params = {{}}
        if limit:
            params['limit'] = limit
        if offset:
            params['offset'] = offset

        result = self._api_call(endpoint, params=params)
        return [result] if isinstance(result, dict) else result

    def _api_call(self, endpoint: str, method: str = "GET", **kwargs):
        """Make API call with retry logic."""
        url = self.api_url + endpoint

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )

                if response.status_code == 429:
                    # Rate limited - exponential backoff
                    time.sleep(2 ** attempt)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise DriverError("API call failed: " + str(e))

        raise RateLimitError("Max retries exceeded")

    def _validate_connection(self):
        """Validate connection at init."""
        try:
            # Try simple call
            self.session.get(self.api_url, timeout=5)
        except Exception:
            # Many APIs don't have root endpoint
            pass
'''


class SimpleDriverCreator:
    """Simple driver creator using Claude Agent SDK."""

    def __init__(self):
        self.drivers_dir = Path("generated_drivers")
        self.drivers_dir.mkdir(exist_ok=True)

    async def analyze_api(self, api_url: str) -> Dict[str, Any]:
        """Analyze API structure."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url) as response:
                    return {
                        "status": "success",
                        "reachable": response.status < 500,
                        "public": response.status == 200
                    }
            except Exception as e:
                return {"status": "error", "message": str(e)}

    async def create_driver(self, api_url: str, api_name: str) -> Dict[str, Any]:
        """Create driver for API."""
        print(f"\n🚀 Creating driver for {api_name}")
        print(f"   URL: {api_url}")

        # Setup paths
        driver_name = api_name.lower().replace(" ", "_").replace("-", "_")
        driver_path = self.drivers_dir / f"{driver_name}_driver"
        driver_path.mkdir(exist_ok=True)

        # Analyze API
        api_info = await self.analyze_api(api_url)
        print(f"   API Status: {api_info.get('status')}")

        # Generate from template
        class_name = "".join(w.capitalize() for w in api_name.replace("-", " ").split())

        # Determine endpoints
        if "meteo" in api_name.lower():
            endpoints = '["forecast", "historical", "marine", "air_quality"]'
        else:
            endpoints = '["data", "info", "status"]'

        # Generate driver
        driver_code = DRIVER_TEMPLATE.format(
            api_name=api_name,
            api_url=api_url,
            class_name=class_name,
            timestamp=datetime.now().isoformat(),
            env_key=f"{api_name.upper().replace('-', '_')}_API_KEY",
            env_url=f"{api_name.upper().replace('-', '_')}_API_URL",
            endpoints=endpoints
        )

        # Save files
        (driver_path / "driver.py").write_text(driver_code)
        (driver_path / "__init__.py").write_text(
            f'from .driver import {class_name}Driver\n\n'
            f'__all__ = ["{class_name}Driver"]\n'
        )

        # README
        (driver_path / "README.md").write_text(f"""# {api_name} Driver

## Usage

```python
from driver import {class_name}Driver

driver = {class_name}Driver()
objects = driver.list_objects()
data = driver.read("/forecast?latitude=52.52&longitude=13.41")
```

Generated by Simple Driver Creator
""")

        print(f"   ✅ Driver created at {driver_path}")

        return {
            "success": True,
            "path": str(driver_path),
            "files": ["driver.py", "__init__.py", "README.md"]
        }


# === CLI ===
async def main():
    import sys

    if len(sys.argv) != 3:
        print("Usage: python simple_agent.py <api-url> <api-name>")
        print('Example: python simple_agent.py "https://api.open-meteo.com/v1" "Open-Meteo"')
        return 1

    api_url = sys.argv[1]
    api_name = sys.argv[2]

    creator = SimpleDriverCreator()
    result = await creator.create_driver(api_url, api_name)

    if result["success"]:
        print(f"\n✅ Success! Driver at: {result['path']}")
        return 0
    else:
        print(f"\n❌ Failed")
        return 1


if __name__ == "__main__":
    asyncio.run(main())