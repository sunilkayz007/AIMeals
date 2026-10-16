"""
=========================================================
AIMeals Backend
IP Geolocation Helper

Responsibilities:
    - Resolve a client IP address to a two-letter country code

Dependencies:
    - Python standard library only (urllib) -- deliberately no
      new pip dependency, given how many small dependency-
      mismatch bugs this project hit in a single day already.

Notes:
    - This is a REPLACEMENT for the earlier device-locale-based
      region signal (Profile.region_code was previously set from
      the frontend's expo-localization reading, which conflated
      LANGUAGE preference with PHYSICAL location -- a user can
      set their phone to "English (United States)" while living
      in India, which is exactly the bug that prompted this
      switch). IP geolocation reflects where the network
      connection is actually coming from instead.
    - IMPORTANT LIMITATION: this cannot resolve localhost/private
      IP addresses (127.0.0.1, 192.168.x.x, 10.x.x.x, etc.) to a
      real location -- there is no geography to look up. Local
      backend testing (uvicorn on your own machine) will always
      get None here; this only produces real results against a
      backend receiving traffic from genuine public IPs (e.g. the
      deployed EC2 server). See _is_private_ip()'s own docstring.
    - Uses ip-api.com's free, no-API-key endpoint (reasonable
      rate limits for a single small app's traffic). Fails
      silently (returns None) on ANY error -- a network hiccup or
      third-party outage here should NEVER break the user's
      actual request; region is always a soft, optional hint,
      never a hard dependency (see AIService._build_region_context()).
    - Sending a user's IP to this third-party service is a real,
      if minor, privacy consideration worth being explicit about
      -- the IP is already visible to this server via the
      connection itself, but this is an additional external party
      seeing it.

Example usage:
    from app.core.geolocation import get_country_code_from_ip

    country = get_country_code_from_ip(client_ip)
=========================================================
"""

import ipaddress
import json
import urllib.request
from typing import Optional

from app.C_logger import app_logger

# Short timeout -- this must never meaningfully delay the request
# it's attached to. A slow/unreachable geolocation service should
# just mean "no region detected this time," not a slow user-facing
# response.
_REQUEST_TIMEOUT_SECONDS = 2.0


def _is_private_or_local_ip(ip: str) -> bool:
    """
    True for localhost, private network ranges (192.168.x.x,
    10.x.x.x, 172.16-31.x.x), and other non-globally-routable
    addresses -- none of these can be geolocated to a real place.
    This is the expected, normal case for local backend testing
    (uvicorn on your own machine) -- see module docstring.
    """
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        # Not a parseable IP at all (e.g. empty string, malformed
        # header) -- treat the same as "can't geolocate this."
        return True


def get_country_code_from_ip(ip: str) -> Optional[str]:
    """
    Resolves a client IP address to a two-letter ISO country code
    (e.g. "IN", "US"), or None if it can't be determined -- either
    because the IP is private/local (see module docstring), the
    lookup service is unreachable, or the response couldn't be
    parsed. NEVER raises -- every failure path returns None.
    """
    if not ip or _is_private_or_local_ip(ip):
        return None

    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,countryCode"
        with urllib.request.urlopen(url, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("status") != "success":
            return None

        country_code = data.get("countryCode")
        return country_code if country_code else None

    except Exception as e:  # noqa: BLE001 -- intentionally broad, see docstring
        app_logger.warning(f"IP geolocation lookup failed for an IP (not logging the IP itself): {e}")
        return None