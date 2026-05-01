from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.services.cache import get_cache, set_cache
from app.core.rate_limit import rate_limit_public_search


def test_set_cache_and_get_cache_with_mocked_redis():
    mock_redis = MagicMock()
    mock_redis.get.return_value = '{"value": 123}'

    with patch("app.services.cache.redis_client", mock_redis):
        set_cache("test:key", {"value": 123}, 60)
        result = get_cache("test:key")

    mock_redis.setex.assert_called_once_with(
        "test:key",
        60,
        '{"value": 123}',
    )
    mock_redis.get.assert_called_once_with("test:key")
    assert result == {"value": 123}


def test_get_cache_returns_none_on_missing_key():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch("app.services.cache.redis_client", mock_redis):
        result = get_cache("missing:key")

    assert result is None


def test_rate_limit_allows_requests_under_limit():
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"

    mock_redis = MagicMock()
    mock_redis.incr.side_effect = [1, 1]
    mock_redis.expire.return_value = True

    with patch("app.core.rate_limit.redis_client", mock_redis):
        result = rate_limit_public_search(mock_request)

    assert result is None
    assert mock_redis.incr.call_count == 2


def test_rate_limit_blocks_more_than_10_per_minute():
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"

    mock_redis = MagicMock()
    mock_redis.incr.side_effect = [11, 1]
    mock_redis.expire.return_value = True

    with patch("app.core.rate_limit.redis_client", mock_redis):
        try:
            rate_limit_public_search(mock_request)
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 429
            assert "10 requests per minute" in exc.detail
            assert exc.headers["Retry-After"] == "60"


def test_rate_limit_blocks_more_than_100_per_hour():
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"

    mock_redis = MagicMock()
    mock_redis.incr.side_effect = [1, 101]
    mock_redis.expire.return_value = True

    with patch("app.core.rate_limit.redis_client", mock_redis):
        try:
            rate_limit_public_search(mock_request)
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 429
            assert "100 requests per hour" in exc.detail
            assert exc.headers["Retry-After"] == "3600"