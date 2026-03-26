import json
import re
import sys
from html import unescape
from urllib.parse import parse_qsl, urlencode
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin


ADDON = xbmcaddon.Addon()
ADDON_HANDLE = int(sys.argv[1])
ADDON_BASE_URL = sys.argv[0]

TOP_PLAYER_URL = "https://topradio.be/player/top"
VIDEO_API_URL = (
    "https://takeoff.jetstre.am/?account=TopRadio&file=kijklive&type=live"
    "&service=wowza&protocol=https&token=undefined&port=undefined"
    "&output=playlist.m3u8&format=all_servers_json"
)
DEFAULT_POSTAL_CODE = "9000"
DEFAULT_ICON = "https://api.topradio.be/images/34292.d95ddae.16-9.1000.90.jpg"
DEFAULT_FANART = "https://api.topradio.be/images/7172.f2bf7bd.16-9.1000.90.jpg"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def log(message, level=xbmc.LOGWARNING):
    xbmc.log("[plugin.video.topradio.be] {0}".format(message), level)


def build_url(query):
    return "{0}?{1}".format(ADDON_BASE_URL, urlencode(query))


def fetch_text(url):
    request = Request(url, headers=REQUEST_HEADERS)
    with urlopen(request, timeout=15) as response:
        charset = response.headers.get_content_charset("utf-8")
        return response.read().decode(charset, errors="replace")


def fetch_json(url):
    return json.loads(fetch_text(url))


def html_to_text(value):
    if not value:
        return ""
    clean = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", unescape(clean)).strip()


def extract_next_data(html):
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise ValueError("__NEXT_DATA__ script tag not found")
    return json.loads(match.group(1))


def get_station_entries():
    data = extract_next_data(fetch_text(TOP_PLAYER_URL))
    page_props = data.get("props", {}).get("pageProps", {})

    stations = page_props.get("initialState", {}).get("stations", {}).get("stations")
    if not stations:
        stations = page_props.get("stations", {}).get("data", [])

    return [normalize_station(station) for station in stations]


def normalize_station(station):
    logo_data = station.get("logo", {}).get("data", {})
    background_data = station.get("background", {}).get("data", {})
    return {
        "id": station.get("id"),
        "title": station.get("title") or "",
        "subtitle": station.get("sub_title") or "",
        "slug": station.get("slug") or "",
        "description": html_to_text(station.get("description")),
        "stream_url": station.get("station_url")
        or station.get("station_main_url")
        or "",
        "fallback_stream_url": station.get("station_main_url")
        or station.get("station_url")
        or "",
        "logo": logo_data.get("crop") or DEFAULT_ICON,
        "fanart": background_data.get("crop") or DEFAULT_FANART,
        "is_main_station": bool(station.get("is_main_station")),
    }


def resolve_station_stream(station):
    stream_url = station.get("stream_url") or station.get("fallback_stream_url")
    if not stream_url:
        raise ValueError(
            "Geen stream-URL gevonden voor station {0}".format(station.get("title"))
        )
    return stream_url


def resolve_video_stream():
    streams = fetch_json(VIDEO_API_URL)
    if not isinstance(streams, list) or not streams:
        raise ValueError("Geen videostreams ontvangen")

    preferred = sorted(
        streams, key=lambda item: int(item.get("score", "0")), reverse=True
    )
    for entry in preferred:
        stream_url = entry.get("streamURL")
        if stream_url:
            return stream_url

    raise ValueError("Geen geldige videostreamURL gevonden")


def create_list_item(label, plot="", art=None, playable=False):
    list_item = xbmcgui.ListItem(label=label)
    info_tag = list_item.getVideoInfoTag()
    info_tag.setTitle(label)
    if plot:
        info_tag.setPlot(plot)
    list_item.setProperty("IsPlayable", "true" if playable else "false")
    if art:
        list_item.setArt(art)
    return list_item


def add_directory_item(label, query, plot="", art=None):
    list_item = create_list_item(label=label, plot=plot, art=art, playable=True)
    xbmcplugin.addDirectoryItem(
        handle=ADDON_HANDLE,
        url=build_url(query),
        listitem=list_item,
        isFolder=False,
    )


def end_directory(content="files"):
    xbmcplugin.setContent(ADDON_HANDLE, content)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def show_root_menu():
    video_art = {"thumb": DEFAULT_ICON, "icon": DEFAULT_ICON, "fanart": DEFAULT_FANART}
    add_directory_item(
        label="[B]TOP[/B] - Live Videostream",
        query={"action": "play_video"},
        plot="[B]TOP[/B]\nLive Videostream",
        art=video_art,
    )

    for station in get_station_entries():
        title = station["title"]
        subtitle = station["subtitle"]
        description = station["description"]

        label = title
        plot = "[B]{0}[/B]\n{1}".format(title, description)

        if subtitle:
            label = "[B]{0}[/B] - {1}".format(title, subtitle)
        art = {
            "thumb": station["logo"],
            "icon": station["logo"],
            "fanart": station["fanart"],
        }
        add_directory_item(
            label=label,
            query={"action": "play_station", "slug": station["slug"]},
            plot=plot,
            art=art,
        )

    end_directory(content="files")


def play_video():
    stream_url = resolve_video_stream()
    list_item = create_list_item(
        label="TOPradio Live TV",
        plot="Live videostream van TOPradio.",
        art={"thumb": DEFAULT_ICON, "icon": DEFAULT_ICON, "fanart": DEFAULT_FANART},
        playable=True,
    )
    list_item.setPath(stream_url)
    list_item.setMimeType("application/vnd.apple.mpegurl")
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, list_item)


def play_station(slug):
    stations = get_station_entries()
    station = next((item for item in stations if item["slug"] == slug), None)
    if not station:
        raise ValueError("Station niet gevonden: {0}".format(slug))

    stream_url = resolve_station_stream(station)
    list_item = create_list_item(
        label=station["title"],
        plot=station["description"],
        art={
            "thumb": station["logo"],
            "icon": station["logo"],
            "fanart": station["fanart"],
        },
        playable=True,
    )
    list_item.setPath(stream_url)
    list_item.setMimeType("audio/mpeg")
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, list_item)


def router(param_string):
    params = dict(parse_qsl(param_string.lstrip("?")))
    action = params.get("action")

    if not action:
        show_root_menu()
        return
    if action == "play_video":
        play_video()
        return
    if action == "play_station":
        play_station(params.get("slug", ""))
        return

    raise ValueError("Onbekende actie: {0}".format(action))


def run():
    try:
        router(sys.argv[2])
    except Exception as exc:  # pylint: disable=broad-except
        log("Fout: {0}".format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().notification("TOPradio", str(exc), xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(ADDON_HANDLE, succeeded=False)
