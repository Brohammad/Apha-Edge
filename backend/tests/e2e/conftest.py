import asyncio
import os
import socket
from collections.abc import AsyncGenerator
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import pytest

E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
E2E_POLL_INTERVAL = float(os.environ.get("E2E_POLL_INTERVAL", "0.5"))
E2E_TASK_TIMEOUT = float(os.environ.get("E2E_TASK_TIMEOUT", "30"))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end tests against a running API stack",
    )


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    return E2E_BASE_URL


@pytest.fixture(scope="session")
async def require_e2e_stack(e2e_base_url: str) -> None:
    """Skip when the live API or its dependencies are unavailable."""
    parsed = urlparse(e2e_base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not _port_open(host, port):
        pytest.skip(f"E2E API not reachable at {e2e_base_url}")

    async with httpx.AsyncClient(base_url=e2e_base_url, timeout=10.0) as client:
        live = await client.get("/api/v1/health/live")
        if live.status_code != 200:
            pytest.skip(f"E2E API liveness failed: {live.status_code}")

        ready = await client.get("/api/v1/health/ready")
        if ready.status_code != 200:
            body = ready.text
            pytest.skip(f"E2E stack not ready ({ready.status_code}): {body}")


@pytest.fixture
async def e2e_client(
    e2e_base_url: str, require_e2e_stack: None
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=e2e_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
async def e2e_auth_client(
    e2e_base_url: str, require_e2e_stack: None
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=e2e_base_url, timeout=30.0) as client:
        email = f"e2e_{uuid4().hex[:10]}@alphaedge.io"
        register = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecurePass1234", "display_name": "E2E User"},
        )
        assert register.status_code == 201, register.text

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecurePass1234"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["data"]["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


async def wait_for_status(
    client: httpx.AsyncClient,
    path: str,
    *,
    field: str = "status",
    expected: str | set[str],
    timeout: float = E2E_TASK_TIMEOUT,
) -> dict:
    """Poll a resource until status reaches an expected value."""
    expected_values = {expected} if isinstance(expected, str) else set(expected)

    deadline = asyncio.get_event_loop().time() + timeout
    last_body: dict | None = None
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(path)
        assert response.status_code == 200, response.text
        last_body = response.json()["data"]
        if last_body.get(field) in expected_values:
            return last_body
        await asyncio.sleep(E2E_POLL_INTERVAL)

    raise AssertionError(
        f"Timed out waiting for {path} {field} in {expected_values}; last={last_body}"
    )
