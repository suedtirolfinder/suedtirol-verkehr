import json
import urllib.request
import ssl

# Open Data Hub Südtirol - Endpoint für freie Parkplätze
URL = "https://mobility.api.opendatahub.com/v2/flat/ParkingStation/free/latest?limit=250"

def get_parking_data():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "SuedtirolMagazin/1.0 (info@suedtirolmagazin.it)"}
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

    stations = []
    data_items = payload.get("data", [])
    print(f"API lieferte {len(data_items)} Rohdaten-Einträge.")

    for item in data_items:
        name = item.get("sname") or item.get("scode")
        if not name:
            continue

        # Stadt ermitteln (aus municipality oder metadata)
        city = item.get("municipality") or ""
        meta = item.get("smetadata") or {}
        if not city and isinstance(meta, dict):
            city = meta.get("city") or meta.get("municipality") or ""

        # Falls keine Stadt gesetzt ist, aus Stationsnamen/Code ableiten
        name_lower = name.lower()
        if not city:
            if "bolzano" in name_lower or "bozen" in name_lower:
                city = "Bozen"
            elif "meran" in name_lower or "merano" in name_lower:
                city = "Meran"
            elif "brixen" in name_lower or "bressanone" in name_lower:
                city = "Brixen"
            elif "bruneck" in name_lower or "brunico" in name_lower:
                city = "Bruneck"
            else:
                city = "Südtirol"

        # Freie Plätze & Kapazität
        free_val = item.get("mvalue")
        cap_val = item.get("pcapacity") or item.get("capacity")
        if not cap_val and isinstance(meta, dict):
            cap_val = meta.get("capacity") or meta.get("total_capacity")

        try:
            free = int(float(free_val)) if free_val is not None else 0
        except (ValueError, TypeError):
            free = 0

        try:
            cap = int(float(cap_val)) if cap_val is not None else None
        except (ValueError, TypeError):
            cap = None

        if cap and cap > 0:
            percent_free = round((free / cap) * 100)
        else:
            percent_free = None

        if free == 0:
            status = "voll"
        elif percent_free is not None and percent_free < 10:
            status = "knapp"
        else:
            status = "frei"

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

    # Sortieren nach Priorität: Bozen, Meran, Brixen, Bruneck, Rest
    prio_cities = ["bozen", "bolzano", "meran", "merano", "brixen", "bruneck"]
    stations.sort(key=lambda x: (
        not any(pc in (x["city"] or "").lower() for pc in prio_cities),
        x["city"],
        x["name"]
    ))
    return stations

if __name__ == "__main__":
    results = get_parking_data()
    print(f"Gefiltert: {len(results)} Parkhäuser erfasst.")
    
    with open("parken.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
