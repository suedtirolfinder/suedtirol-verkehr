import json
import urllib.request
import ssl

# Endpunkt für alle aktuellen Verkehrsmeldungen, Baustellen und Sperren
URL = "https://mobility.api.opendatahub.com/v2/flat/TrafficIncident/*/latest?limit=500"

def get_traffic_data():
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
        print(f"Fehler beim Abruf der Verkehrsmeldungen: {e}")
        return []

    items = payload.get("data", [])
    print(f"API lieferte {len(items)} Verkehrseinträge.")

    events = []
    seen = set()

    for item in items:
        meta = item.get("smetadata") if isinstance(item.get("smetadata"), dict) else {}
        
        # Titel / Straße
        title = item.get("sname") or meta.get("road") or meta.get("title") or item.get("scode")
        if not title:
            continue

        desc_de = meta.get("description_de") or meta.get("text_de") or meta.get("description") or item.get("sdescription") or ""
        road = meta.get("road") or meta.get("road_number") or ""
        location = item.get("municipality") or meta.get("location") or meta.get("place") or "Südtirol"

        # Dubletten vermeiden
        dedup_key = f"{title}_{desc_de[:30]}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Typ und Status einstufen
        text_full = f"{title} {desc_de}".lower()
        if "sperre" in text_full or "gesperrt" in text_full or "chiuso" in text_full:
            if "nacht" in text_full or "notte" in text_full:
                category = "Nachtsperre"
                badge_type = "orange"
            else:
                category = "Sperre"
                badge_type = "red"
        elif "baustelle" in text_full or "lavori" in text_full or "arbeitsstelle" in text_full:
            category = "Baustelle"
            badge_type = "orange"
        elif "stau" in text_full or "stockend" in text_full or "rallentamenti" in text_full:
            category = "Stau / Verzögerung"
            badge_type = "yellow"
        else:
            category = "Verkehrsmeldung"
            badge_type = "blue"

        coords = item.get("scoordinate") if isinstance(item.get("scoordinate"), dict) else {}
        lat = coords.get("y")
        lng = coords.get("x")

        events.append({
            "title": title,
            "road": road,
            "location": location,
            "description": desc_de if desc_de else "Aktuelle Verkehrsbehinderung.",
            "category": category,
            "badge_type": badge_type,
            "lat": lat,
            "lng": lng
        })

    # Prio-Sortierung: Sperren zuerst, dann Baustellen
    type_order = {"red": 1, "orange": 2, "yellow": 3, "blue": 4}
    events.sort(key=lambda x: type_order.get(x["badge_type"], 9))

    return events

if __name__ == "__main__":
    results = get_traffic_data()
    print(f"Gefiltert: {len(results)} aktuelle Verkehrsmeldungen.")
    with open("verkehr.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
