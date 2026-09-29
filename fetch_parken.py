import json
import urllib.request
import ssl

URL = "https://mobility.api.opendatahub.com/v2/flat/ParkingStation/latest"

def fetch_data():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SuedtirolMagazin/1.0)"}
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Fehler beim Abruf: {e}")
        return []

    items = payload.get("data", [])
    parsed = []

    for item in items:
        name = item.get("sname") or "Parkplatz"
        meta = item.get("smetadata", {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except:
                meta = {}

        city = meta.get("municipality") or meta.get("city") or item.get("municipality") or "Südtirol"

        free = item.get("free")
        if free is None:
            free = meta.get("free") or meta.get("available") or 0
        try:
            free = int(free)
        except:
            free = 0

        capacity = item.get("capacity")
        if capacity is None:
            capacity = meta.get("capacity") or meta.get("total") or 0
        try:
            capacity = int(capacity)
        except:
            capacity = 0

        auslastung = 0
        if capacity > 0:
            occupied = max(0, capacity - free)
            auslastung = round((occupied / capacity) * 100)
            if auslastung > 100:
                auslastung = 100

        percent_free = round((free / capacity * 100)) if capacity > 0 else 0

        coords = item.get("scoordinate", {})
        lat = coords.get("y") if isinstance(coords, dict) else None
        lng = coords.get("x") if isinstance(coords, dict) else None

        parsed.append({
            "name": name,
            "city": city,
            "free": free,
            "capacity": capacity,
            "auslastung": auslastung,
            "percent_free": percent_free,
            "lat": lat,
            "lng": lng
        })

    return parsed

if __name__ == "__main__":
    data = fetch_data()
    with open("parken.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{len(data)} Parkplätze gespeichert.")
