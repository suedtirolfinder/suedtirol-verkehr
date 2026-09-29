import json
import urllib.request
import ssl

# Endpunkt für alle Parkstationen & Sensoren in Südtirol
URL = "https://mobility.api.opendatahub.com/v2/flat/ParkingStation/*/latest?limit=1000"

def get_parking_data():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SuedtirolMagazin/1.0"}
    )
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=25) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Fehler beim Abruf: {e}")
        return []

    raw_items = payload.get("data", [])
    print(f"API lieferte {len(raw_items)} Datensätze.")

    stations = []
    seen = {}

    for item in raw_items:
        name = item.get("sname") or item.get("scode")
        if not name:
            continue

        # Messwert (freie Plätze)
        mval = item.get("mvalue")
        if mval is None:
            continue

        try:
            free = int(float(mval))
        except (ValueError, TypeError):
            continue

        scode = str(item.get("scode", "")).lower()
        sname = str(name).lower()
        muni = str(item.get("municipality", "")).lower()
        meta = item.get("smetadata") if isinstance(item.get("smetadata"), dict) else {}

        # Stadt-Erkennung (präzise Match-Tabelle für Südtirol)
        city = "Südtirol"
        if any(k in muni or k in sname or k in scode for k in ["meran", "merano", "therme", "karl wolf", "plankenstein", "prader", "maia bassa", "untermais"]):
            city = "Meran"
        elif any(k in muni or k in sname or k in scode for k in ["brixen", "bressanone", "priel", "rosslauf", "stufels", "acquarena"]):
            city = "Brixen"
        elif any(k in muni or k in sname or k in scode for k in ["bruneck", "brunico", "mobilitätszentrum", "steggern", "rathaus"]):
            city = "Bruneck"
        elif any(k in muni or k in sname or k in scode for k in ["bozen", "bolzano", "walther", "laurin", "central", "city parking", "bozen mitte"]):
            city = "Bozen"

        # Kapazität ermitteln
        cap = item.get("pcapacity") or item.get("capacity") or meta.get("capacity") or meta.get("total_capacity")
        try:
            cap = int(float(cap)) if cap else None
        except (ValueError, TypeError):
            cap = None

        coords = item.get("scoordinate") if isinstance(item.get("scoordinate"), dict) else {}
        lat = coords.get("y")
        lng = coords.get("x")

        # Prozent freie Plätze berechnen
        percent = round((free / cap) * 100) if (cap and cap > 0) else None

        # Status
        if free <= 0:
            status = "voll"
        elif percent is not None and percent < 10:
            status = "knapp"
        else:
            status = "frei"

        entry = {
            "name": name,
            "city": city,
            "free": free,
            "capacity": cap,
            "percent_free": percent,
            "status": status,
            "lat": lat,
            "lng": lng
        }

        # Dubletten vermeiden (aktuellsten Datensatz behalten)
        seen[name] = entry

    stations = list(seen.values())

    # Sortierung: Bozen, Meran, Brixen, Bruneck, Rest
    order = {"bozen": 1, "meran": 2, "brixen": 3, "bruneck": 4, "südtirol": 5}
    stations.sort(key=lambda s: (order.get(s["city"].lower(), 99), s["name"]))

    return stations

if __name__ == "__main__":
    results = get_parking_data()
    print(f"Fertig: {len(results)} Parkstationen gespeichert.")
    with open("parken.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
