from backend.normalization.url import normalize_url, is_same_endpoint, extract_path_pattern, canonicalize_url
from backend.normalization.scope import ScopeConfig, is_in_scope, is_private_network, validate_redirect


class TestURLNormalization:
    def test_lowercase_scheme_and_host(self):
        assert normalize_url("HTTPS://Example.COM/path") == "https://example.com/path"

    def test_remove_default_port_https(self):
        assert normalize_url("https://example.com:443/path") == "https://example.com/path"

    def test_remove_default_port_http(self):
        assert normalize_url("http://example.com:80/path") == "http://example.com/path"

    def test_keep_non_default_port(self):
        result = normalize_url("https://example.com:8443/path")
        assert ":8443" in result

    def test_sort_query_params(self):
        result = normalize_url("https://example.com/path?z=1&a=2&m=3")
        assert "a=2" in result
        assert result.index("a=2") < result.index("m=3") < result.index("z=1")

    def test_remove_fragment(self):
        result = normalize_url("https://example.com/path#section")
        assert "#" not in result

    def test_resolve_dot_segments(self):
        result = normalize_url("https://example.com/a/b/../c")
        assert "/a/c" in result

    def test_strip_trailing_slash(self):
        assert normalize_url("https://example.com/path/").endswith("/path")

    def test_keep_root_slash(self):
        assert normalize_url("https://example.com/") == "https://example.com/"


class TestIsSameEndpoint:
    def test_same(self):
        assert is_same_endpoint("https://example.com/api", "https://example.com/api", "GET", "GET")

    def test_different_method(self):
        assert not is_same_endpoint("https://example.com/api", "https://example.com/api", "GET", "POST")

    def test_normalized_match(self):
        assert is_same_endpoint("https://Example.COM:443/api", "https://example.com/api", "GET", "GET")


class TestExtractPathPattern:
    def test_numeric_id(self):
        assert "{id}" in extract_path_pattern("https://example.com/api/users/123")

    def test_uuid_id(self):
        assert "{id}" in extract_path_pattern("https://example.com/api/users/550e8400-e29b-41d4-a716-446655440000")

    def test_no_id(self):
        assert "{id}" not in extract_path_pattern("https://example.com/api/users")


class TestScopeEnforcement:
    def test_in_scope(self):
        scope = ScopeConfig(allowed_hosts=["example.com"])
        assert is_in_scope("https://example.com/api", scope)

    def test_out_of_scope_host(self):
        scope = ScopeConfig(allowed_hosts=["example.com"])
        assert not is_in_scope("https://evil.com/api", scope)

    def test_out_of_scope_scheme(self):
        scope = ScopeConfig(allowed_hosts=["example.com"], allowed_schemes=["https"])
        assert not is_in_scope("http://example.com/api", scope)

    def test_excluded_path(self):
        scope = ScopeConfig(allowed_hosts=["example.com"], exclude_paths=["/admin"])
        assert not is_in_scope("https://example.com/admin/settings", scope)

    def test_private_network_blocked(self):
        scope = ScopeConfig(allowed_hosts=["localhost"], allow_private_networks=False)
        assert not is_in_scope("http://localhost/api", scope)

    def test_private_network_allowed(self):
        scope = ScopeConfig(allowed_hosts=["localhost"], allow_private_networks=True)
        assert is_in_scope("http://localhost/api", scope)


class TestPrivateNetwork:
    def test_localhost(self):
        assert is_private_network("localhost")

    def test_loopback(self):
        assert is_private_network("127.0.0.1")

    def test_ipv6_loopback(self):
        assert is_private_network("::1")

    def test_public_ip(self):
        assert not is_private_network("8.8.8.8")


class TestRedirectValidation:
    def test_valid_redirect(self):
        scope = ScopeConfig(allowed_hosts=["example.com"])
        assert validate_redirect("https://example.com/a", "https://example.com/b", scope)

    def test_redirect_escapes_scope(self):
        scope = ScopeConfig(allowed_hosts=["example.com"])
        assert not validate_redirect("https://example.com/a", "https://evil.com/b", scope)
