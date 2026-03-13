#!/usr/bin/python3

# python3 lookup.py "{query}"

import re
import sys
import urllib.parse
from workflow import Workflow, ICON_WEB, ICON_WARNING, ICON_NETWORK, PasswordNotFound

log = None

# Matches ITU callsign format:
#   1-3 alphanumeric prefix (e.g. W, VK, 9A) + district digit + 1-4 letter suffix
#   optional portable/mobile indicator (e.g. /P, /7, /MM)
_CALLSIGN_RE = re.compile(r'^[A-Z0-9]{1,3}[0-9][A-Z]{1,4}(/[A-Z0-9]{1,4})?$')

def is_valid_callsign(callsign):
    return bool(_CALLSIGN_RE.match(callsign))


def grid_to_latlon(grid):
    """Convert a Maidenhead grid square to a (lat, lon) centre-point tuple.

    Supports 4-character (e.g. DM79) and 6-character (e.g. DM79JH) locators.
    Returns None if the grid string is too short or malformed.
    """
    grid = grid.upper()
    if len(grid) < 4:
        return None
    try:
        lon = (ord(grid[0]) - ord('A')) * 20 - 180
        lat = (ord(grid[1]) - ord('A')) * 10 - 90
        lon += int(grid[2]) * 2
        lat += int(grid[3])
        if len(grid) >= 6:
            lon += (ord(grid[4]) - ord('A')) * (2 / 24)
            lat += (ord(grid[5]) - ord('A')) * (1 / 24)
            lon += 1 / 24       # centre of sub-square
            lat += 0.5 / 24
        else:
            lon += 1            # centre of 2° × 1° square
            lat += 0.5
    except (ValueError, IndexError):
        return None
    return (lat, lon)


def maps_url_and_label(qrz, callsign):
    """Return (apple_maps_url, subtitle) using the best available location data.

    Priority:
      1. Human-readable address (city, state, zip, country)
      2. Latitude/longitude from QRZ
      3. Lat/lon derived from the Maidenhead grid square
    Returns (None, None) if no location data is available.
    """
    # 1. Address
    parts = [p for p in [qrz.addr1, qrz.addr2, qrz.state, qrz.zip, qrz.country] if p]
    if parts:
        address = ', '.join(parts)
        return (f"maps://?q={urllib.parse.quote(address)}", address)

    # 2. Lat/lon from QRZ
    if qrz.latlon:
        lat, lon = qrz.latlon
        return (
            f"maps://?ll={lat:.5f},{lon:.5f}&q={urllib.parse.quote(callsign)}",
            f"{lat:.5f}, {lon:.5f}",
        )

    # 3. Lat/lon derived from grid square
    if qrz.grid:
        latlon = grid_to_latlon(qrz.grid)
        if latlon:
            lat, lon = latlon
            return (
                f"maps://?ll={lat:.5f},{lon:.5f}&q={urllib.parse.quote(callsign)}",
                f"Grid {qrz.grid}",
            )

    return (None, None)


def main(wf):
    from qrzlib import qrzlib

    log.info('Started')

    try:
        qrz_username = wf.get_password('qrz_username')
        qrz_password = wf.get_password('qrz_password')
    except PasswordNotFound:
        wf.add_item('QRZ credentials not set.',
                    'Please use "qrzset USERNAME PASSWORD" to save your QRZ credentials.',
                    valid=False,
                    icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    # get query from alfred
    if len(wf.args):
        # log.info(f"Args {str(wf.args)}")
        # wf.add_item(f"Args {str(wf.args)}", icon=ICON_WARNING)
        query = wf.args[0].upper()
    else:
        query = None
    
    if not query:
        wf.add_item('No hams found', icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    if not is_valid_callsign(query):
        wf.add_item(f'"{query}" is not a valid callsign.',
                    'Callsigns must follow the format: prefix + digit + suffix (e.g. W1AW, VK3ABC)',
                    valid=False,
                    icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    safe_query = urllib.parse.quote(query, safe='/')

    qrz = qrzlib.QRZ()
    qrz.authenticate(qrz_username, qrz_password)
    try:
        qrz.get_call(query)
        wf.add_item(title=f"{qrz.call} - {qrz.country} - {qrz.fullname}",
                    subtitle=f"{qrz.addr2}, {qrz.state} {qrz.latlon} {qrz.grid} {qrz.email}",
                    arg=f"https://qrz.com/db/{safe_query}",
                    valid=True,
                    icon=ICON_WEB)

        wf.add_item(title=f"Go to QRZ page",
                    subtitle=f"https://qrz.com/db/{safe_query}",
                    arg=f"https://qrz.com/db/{safe_query}",
                    valid=True,
                    icon=ICON_WEB)

        wf.add_item(title=f"Search PSKReporter",
                    subtitle=f"https://pskreporter.info/pskmap?callsign={safe_query}&search=Find",
                    arg=f"https://pskreporter.info/pskmap?callsign={safe_query}&search=Find",
                    valid=True,
                    icon=ICON_WEB)

        wf.add_item(title=f"Search POTA",
                    subtitle=f"https://pota.app/#/profile/{safe_query}",
                    arg=f"https://pota.app/#/profile/{safe_query}",
                    valid=True,
                    icon=ICON_WEB)

        wf.add_item(title=f"Search RBN",
                    subtitle=f"https://www.reversebeacon.net/main.php?rows=10&max_age=10,hours&spotted_call={safe_query}&hide=distance_km",
                    arg=f"https://www.reversebeacon.net/main.php?rows=10&max_age=10,hours&spotted_call={safe_query}&hide=distance_km",
                    valid=True,
                    icon=ICON_WEB)

        wf.add_item(title=f"Search DXSummit",
                    subtitle=f"http://dxsummit.fi/#/?dx_calls={safe_query}",
                    arg=f"http://dxsummit.fi/#/?dx_calls={safe_query}",
                    valid=True,
                    icon=ICON_WEB)
    
        wf.add_item(title=f"Send an email",
                    subtitle=f"mailto:{qrz.email}",
                    arg=f"mailto:{qrz.email}",
                    valid=True,
                    icon=ICON_NETWORK)

        maps_url, maps_label = maps_url_and_label(qrz, query)
        if maps_url:
            wf.add_item(title="Open in Apple Maps",
                        subtitle=maps_label,
                        arg=maps_url,
                        valid=True,
                        icon=ICON_NETWORK)

    except qrzlib.QRZ.NotFound as err:
        print(err)

    wf.send_feedback()


if __name__ == u"__main__":
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
