import time
import pytest
from src.security.rate_limiter import RateLimiter

def test_rate_limiter_allows_requests_within_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    assert limiter.is_allowed("client-1") is True
    assert limiter.is_allowed("client-1") is True
    assert limiter.is_allowed("client-1") is True


def test_rate_limiter_blocks_requests_over_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.is_allowed("client-1") is True
    assert limiter.is_allowed("client-1") is True
    assert limiter.is_allowed("client-1") is False


def test_rate_limiter_tracks_clients_independently():
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    assert limiter.is_allowed("client-1") is True
    assert limiter.is_allowed("client-1") is False

    assert limiter.is_allowed("client-2") is True


def test_rate_limiter_allows_requests_after_window_expires():
    limiter = RateLimiter(max_requests=1, window_seconds=1)

    assert limiter.is_allowed("client-1") is True
    assert limiter.is_allowed("client-1") is False

    time.sleep(1.1)

    assert limiter.is_allowed("client-1") is True


@pytest.mark.parametrize(("max_requests", "window_seconds"), [(0, 60), (-1, 60), (30, 0), (30, -1)])
def test_rate_limiter_rejects_invalid_configuration(max_requests: int, window_seconds: int):
    with pytest.raises(ValueError):
        RateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds
        )