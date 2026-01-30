"""ClawHub API client for skill discovery and installation.

ClawHub (https://clawhub.ai) is the official skill marketplace for OpenClaw/Moltbot.
This module provides a client to search, download, and install skills from ClawHub.
"""

import hashlib
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# Data Models
# ============================================================================


class ClawHubSkill(BaseModel):
    """Skill metadata from ClawHub API."""

    slug: str = Field(..., description="Unique skill identifier (e.g., 'openclaw/weather')")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Brief description")
    version: str = Field(..., description="Latest version (semver)")
    author: str = Field(..., description="Author username")
    tags: list[str] = Field(default_factory=list, description="Skill tags")
    downloads: int = Field(default=0, description="Total download count")
    rating: float | None = Field(default=None, description="Average rating (0-5)")
    homepage: str | None = Field(default=None, description="Homepage URL")
    repository: str | None = Field(default=None, description="Source repository URL")
    license: str | None = Field(default=None, description="License (e.g., 'MIT')")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    updated_at: str = Field(..., description="ISO 8601 timestamp")


class ClawHubVersion(BaseModel):
    """Specific version of a skill."""

    version: str = Field(..., description="Version string (semver)")
    download_url: str = Field(..., description="Download URL for skill package")
    checksum: str = Field(..., description="SHA256 checksum")
    size_bytes: int = Field(..., description="Package size in bytes")
    dependencies: list[str] = Field(default_factory=list, description="Skill dependencies")
    requires: dict[str, Any] = Field(
        default_factory=dict, description="System requirements (bins, env)"
    )
    released_at: str = Field(..., description="ISO 8601 timestamp")


# ============================================================================
# ClawHub API Client
# ============================================================================


class ClawHubClient:
    """Client for ClawHub API.

    Provides methods to search, download, and retrieve skill information.
    """

    def __init__(
        self,
        api_url: str = "https://api.clawhub.ai/v1",
        timeout: float = 30.0,
        user_agent: str = "lurkbot/0.1.0",
    ):
        """Initialize ClawHub client.

        Args:
            api_url: ClawHub API base URL
            timeout: Request timeout in seconds
            user_agent: User-Agent header
        """
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
            },
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "ClawHubClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------------
    # Search and Discovery
    # ------------------------------------------------------------------------

    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        tags: list[str] | None = None,
    ) -> list[ClawHubSkill]:
        """Search for skills on ClawHub.

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Pagination offset
            tags: Filter by tags (optional)

        Returns:
            List of matching skills

        Raises:
            httpx.HTTPError: On API errors
        """
        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }
        if tags:
            params["tags"] = ",".join(tags)

        logger.debug(f"Searching ClawHub: query={query}, limit={limit}")
        response = await self.client.get(f"{self.api_url}/skills/search", params=params)
        response.raise_for_status()

        data = response.json()
        skills = [ClawHubSkill(**item) for item in data.get("results", [])]
        logger.info(f"Found {len(skills)} skills for query: {query}")
        return skills

    async def info(self, slug: str) -> ClawHubSkill:
        """Get detailed information about a skill.

        Args:
            slug: Skill slug (e.g., 'openclaw/weather')

        Returns:
            Skill metadata

        Raises:
            httpx.HTTPError: On API errors (404 if not found)
        """
        logger.debug(f"Fetching skill info: {slug}")
        response = await self.client.get(f"{self.api_url}/skills/{slug}")
        response.raise_for_status()

        return ClawHubSkill(**response.json())

    async def list_versions(self, slug: str) -> list[ClawHubVersion]:
        """List all versions of a skill.

        Args:
            slug: Skill slug (e.g., 'openclaw/weather')

        Returns:
            List of versions (sorted by release date, newest first)

        Raises:
            httpx.HTTPError: On API errors
        """
        logger.debug(f"Fetching versions for: {slug}")
        response = await self.client.get(f"{self.api_url}/skills/{slug}/versions")
        response.raise_for_status()

        data = response.json()
        versions = [ClawHubVersion(**item) for item in data.get("versions", [])]
        return versions

    # ------------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------------

    async def download(
        self,
        slug: str,
        version: str | None = None,
        verify_checksum: bool = True,
    ) -> bytes:
        """Download a skill package.

        Args:
            slug: Skill slug (e.g., 'openclaw/weather')
            version: Specific version to download (default: latest)
            verify_checksum: Whether to verify SHA256 checksum

        Returns:
            Raw package bytes (typically a .tar.gz or .zip file)

        Raises:
            httpx.HTTPError: On API errors
            ValueError: If checksum verification fails
        """
        # Get version info
        if version is None:
            skill_info = await self.info(slug)
            version = skill_info.version

        versions = await self.list_versions(slug)
        version_info = next((v for v in versions if v.version == version), None)
        if not version_info:
            raise ValueError(f"Version {version} not found for skill {slug}")

        # Download package
        logger.info(f"Downloading {slug}@{version} ({version_info.size_bytes} bytes)")
        response = await self.client.get(version_info.download_url)
        response.raise_for_status()

        package_bytes = response.content

        # Verify checksum
        if verify_checksum:
            actual_checksum = hashlib.sha256(package_bytes).hexdigest()
            if actual_checksum != version_info.checksum:
                raise ValueError(
                    f"Checksum mismatch for {slug}@{version}: "
                    f"expected {version_info.checksum}, got {actual_checksum}"
                )
            logger.debug(f"Checksum verified for {slug}@{version}")

        logger.info(f"Successfully downloaded {slug}@{version}")
        return package_bytes

    # ------------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------------

    async def get_dependencies(self, slug: str, version: str | None = None) -> list[str]:
        """Get skill dependencies.

        Args:
            slug: Skill slug
            version: Specific version (default: latest)

        Returns:
            List of dependency slugs (e.g., ['openclaw/base', 'openclaw/utils'])

        Raises:
            httpx.HTTPError: On API errors
        """
        if version is None:
            skill_info = await self.info(slug)
            version = skill_info.version

        versions = await self.list_versions(slug)
        version_info = next((v for v in versions if v.version == version), None)
        if not version_info:
            raise ValueError(f"Version {version} not found for skill {slug}")

        return version_info.dependencies


# ============================================================================
# Convenience Functions
# ============================================================================


async def search_skills(query: str, limit: int = 20) -> list[ClawHubSkill]:
    """Search for skills on ClawHub (convenience function).

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching skills
    """
    async with ClawHubClient() as client:
        return await client.search(query, limit=limit)


async def get_skill_info(slug: str) -> ClawHubSkill:
    """Get skill information (convenience function).

    Args:
        slug: Skill slug

    Returns:
        Skill metadata
    """
    async with ClawHubClient() as client:
        return await client.info(slug)


async def download_skill(
    slug: str,
    version: str | None = None,
    verify_checksum: bool = True,
) -> bytes:
    """Download a skill package (convenience function).

    Args:
        slug: Skill slug
        version: Specific version (default: latest)
        verify_checksum: Whether to verify checksum

    Returns:
        Package bytes
    """
    async with ClawHubClient() as client:
        return await client.download(slug, version=version, verify_checksum=verify_checksum)
