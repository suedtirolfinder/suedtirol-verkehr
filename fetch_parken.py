import json
import urllib.request
import ssl

# Open Data Hub Südtirol: Alle ParkingStation-Echtzeitdaten
URL = "https://mobility.api.opendatahub.com/v2/flat/ParkingStation/*/latest?limit=500"

def get_parking_data():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SuedtirolMagazin/1.0)"}
    )
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Fehler beim Abruf: {e}")
        return []

    raw_items = payload.get("data", [])
    print(f"API lieferte insgesamt {len(raw_items)} Datensätze.")

    stations = []
    seen = set()

    for item in raw_items:
        # Nur Einträge mit freiem Parkplatz-Messwert (tname == 'free' oder vorhandener mvalue)
        tname = item.get("tname")
        if tname and tname != "free":
            continue

        name = item.get("sname") or item.get("scode")
        if not name:
            continue

        # Duplikate vermeiden
        if name in seen:
            continue

        # Metadaten auslesen
        meta = item.get("smetadata") or {}
        if not isinstance(meta, dict):
            meta = {}

        # Stadt ermitteln
        city = item.get("municipality") or meta.get("city") or meta.get("municipality") or ""
        
        name_lower = name.lower()
        if not city or city == "Südtirol":
            if any(x in name_lower for x in ["bozen", "bolzano", "walther", "laurin", "central parking", "city parking"]):
                city = "Bozen"
            elif any(x in name_lower for x in ["meran", "merano", "therme", "karl wolf", "plankenstein"]):
                city = "Meran"
            elif any(x in name_lower for x in ["brixen", "bressanone"]):
                city = "Brixen"
            elif any(x in name_lower for x in ["bruneck", "brunico"]):
                city = "Bruneck"
            else:
                city = "Südtirol"

        # Freie Plätze ermitteln
        free_val = item.get("mvalue")
        if free_val is None:
            continue

        try:
            free = int(float(free_val))
        except (ValueError, TypeError):
            continue

        # Kapazität ermitteln
        cap_val = meta.get("capacity") or meta.get("total_capacity") or item.get("pcapacity")
        try:
            cap = int(float(cap_val)) if cap_val is not None else None
        except (ValueError, TypeError):
            cap = None

        # Prozentwert
        if cap and cap > 0:
            percent_free = max(0, min(100, round((free / cap) * 100)))
        else:
            percent_free = None

        # Status
        if free == 0:
            status = "voll"
        elif percent_free is not None and percent_free < 10:
            status = "knapp"
        else:
            status = "frei"

        # Koordinaten
        coords = item.get("scoordinate") or {}
        lat = coords.get("y") if isinstance(coords, dict) else None
        lng = coords.get("x") if isinstance(coords, dict) else None

        stations.append({
            "name": name,
            "city": city,
            "free": free,
            "capacity": cap,
            "percent_free": percent_free,
            "status": status,
            "lat": lat,
            "lng": lng
        })
        seen.add(name)

    # Nach Stadt (Bozen & Meran zuerst) und Name sortieren
    prio_order = {"bozen": 1, "bolzano": 1, "meran": 2, "merano": 2, "brixen": 3, "bruneck": 4}
    stations.sort(key=lambda s: (prio_order.get(s["city"].lower(), 99), s["name"]))

    return stations

if __name__ == "__main__":
    results = get_parking_data()
    print(f"Erfolgreich {len(results)} Parkhäuser aufbereitet.")
    
    with open("parken.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
