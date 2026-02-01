import sys
from pathlib import Path

import pytest

# Add src to python path to ensure rxon can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def event_loop_policy():
    """
    Prevent 'RuntimeError: Event loop is closed' issues with aiohttp in some environments.
    """
    import asyncio

    return asyncio.get_event_loop_policy()
