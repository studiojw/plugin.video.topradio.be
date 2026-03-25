import pytest


def test_html_to_text_empty_and_falsy(plugin):
    assert plugin.html_to_text("") == ""
    assert plugin.html_to_text(None) == ""


def test_html_to_text_strips_tags_unescapes_and_collapses_whitespace(plugin):
    raw = "  <p>Foo &amp; <b>bar</b></p>  \n\tbaz  "
    assert plugin.html_to_text(raw) == "Foo & bar baz"


def test_extract_next_data_parses_json(plugin):
    html = (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        '{"props":{"pageProps":{"x":1}}}'
        "</script></html>"
    )
    data = plugin.extract_next_data(html)
    assert data["props"]["pageProps"]["x"] == 1


def test_extract_next_data_missing_raises(plugin):
    with pytest.raises(ValueError, match="__NEXT_DATA__"):
        plugin.extract_next_data("<html></html>")


def test_normalize_station_maps_fields_and_defaults(plugin):
    station = {
        "id": 1,
        "title": "TOP",
        "sub_title": "Live",
        "slug": "top",
        "description": "<p>Hello</p>",
        "station_url": "https://audio.example/stream",
        "station_main_url": "https://backup.example/stream",
        "logo": {"data": {"crop": "https://logo.example/x.jpg"}},
        "background": {"data": {"crop": "https://bg.example/y.jpg"}},
        "is_main_station": 1,
    }
    out = plugin.normalize_station(station)
    assert out["id"] == 1
    assert out["title"] == "TOP"
    assert out["subtitle"] == "Live"
    assert out["slug"] == "top"
    assert out["description"] == "Hello"
    assert out["stream_url"] == "https://audio.example/stream"
    assert out["fallback_stream_url"] == "https://backup.example/stream"
    assert out["logo"] == "https://logo.example/x.jpg"
    assert out["fanart"] == "https://bg.example/y.jpg"
    assert out["is_main_station"] is True


def test_normalize_station_empty_uses_defaults_and_alternate_urls(plugin):
    station = {
        "station_main_url": "https://main.only/mp3",
        "logo": {},
        "background": {},
    }
    out = plugin.normalize_station(station)
    assert out["stream_url"] == "https://main.only/mp3"
    assert out["fallback_stream_url"] == "https://main.only/mp3"
    assert out["logo"] == plugin.DEFAULT_ICON
    assert out["fanart"] == plugin.DEFAULT_FANART
    assert out["is_main_station"] is False


def test_resolve_station_stream_uses_primary_or_fallback(plugin):
    assert (
        plugin.resolve_station_stream(
            {"stream_url": "https://a", "fallback_stream_url": "https://b"}
        )
        == "https://a"
    )
    assert (
        plugin.resolve_station_stream({"stream_url": "", "fallback_stream_url": "https://b"})
        == "https://b"
    )


def test_resolve_station_stream_missing_raises(plugin):
    with pytest.raises(ValueError, match="Geen stream-URL"):
        plugin.resolve_station_stream({"title": "X", "stream_url": "", "fallback_stream_url": ""})


def test_resolve_video_stream_prefers_highest_score(plugin, monkeypatch):
    monkeypatch.setattr(
        plugin,
        "fetch_json",
        lambda _url: [
            {"score": "1", "streamURL": "http://low"},
            {"score": "10", "streamURL": "http://high"},
        ],
    )
    assert plugin.resolve_video_stream() == "http://high"


def test_resolve_video_stream_skips_entries_without_url(plugin, monkeypatch):
    monkeypatch.setattr(
        plugin,
        "fetch_json",
        lambda _url: [
            {"score": "99", "streamURL": ""},
            {"score": "1", "streamURL": "http://ok"},
        ],
    )
    assert plugin.resolve_video_stream() == "http://ok"


def test_resolve_video_stream_invalid_payload_raises(plugin, monkeypatch):
    monkeypatch.setattr(plugin, "fetch_json", lambda _url: {})
    with pytest.raises(ValueError, match="Geen videostreams"):
        plugin.resolve_video_stream()

    monkeypatch.setattr(plugin, "fetch_json", lambda _url: [])
    with pytest.raises(ValueError, match="Geen videostreams"):
        plugin.resolve_video_stream()


def test_resolve_video_stream_no_valid_url_raises(plugin, monkeypatch):
    monkeypatch.setattr(
        plugin,
        "fetch_json",
        lambda _url: [{"score": "5", "streamURL": ""}],
    )
    with pytest.raises(ValueError, match="Geen geldige videostreamURL"):
        plugin.resolve_video_stream()


def test_build_url_encodes_query(plugin):
    url = plugin.build_url({"action": "play_station", "slug": "foo bar"})
    assert url.startswith(plugin.ADDON_BASE_URL)
    assert "action=play_station" in url
    assert "slug=foo+bar" in url or "slug=foo%20bar" in url


def test_router_no_action_invokes_root_menu(plugin, monkeypatch):
    captured = []

    monkeypatch.setattr(plugin, "get_station_entries", lambda: [])
    monkeypatch.setattr(
        plugin,
        "add_directory_item",
        lambda **kwargs: captured.append(kwargs),
    )
    monkeypatch.setattr(plugin, "end_directory", lambda **kwargs: captured.append(kwargs))

    plugin.router("")

    assert len(captured) >= 2
    assert captured[0]["query"] == {"action": "play_video"}
    assert captured[-1] == {"content": "files"}


def test_router_unknown_action_raises(plugin):
    with pytest.raises(ValueError, match="Onbekende actie"):
        plugin.router("action=unknown_thing")
