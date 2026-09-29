import json
import urllib.request
import ssl

# Open Data Hub Südtirol & Trentino - Abruf aller Parkstationen (inkl. Trento, Rovereto, Gröden etc.)
URL = "https://mobility.api.opendatahub.com/v2/flat/ParkingStation/*/latest?limit=4000"

def get_parking_data():
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

    raw_items = payload.get("data", [])
    print(f"Rohdaten empfangen: {len(raw_items)} Einträge")

    stations_map = {}

    for item in raw_items:
        sname = item.get("sname") or item.get("scode")
        if not sname:
            continue

        meta = item.get("smetadata") if isinstance(item.get("smetadata"), dict) else {}
        mval = item.get("mvalue")
        tname = str(item.get("tname", "")).lower()

        # Gemeinde bestimmen
        muni_raw = item.get("municipality") or meta.get("city") or meta.get("municipality") or ""
        muni_low = str(muni_raw).lower()
        sname_low = str(sname).lower()
        scode_low = str(item.get("scode", "")).lower()

        # Regional-Zuweisung
        if any(k in muni_low or k in sname_low or k in scode_low for k in ["trento", "trient"]):
            city = "Trento"
        elif any(k in muni_low or k in sname_low or k in scode_low for k in ["rovereto"]):
            city = "Rovereto"
        elif any(k in muni_low or k in sname_low or k in scode_low for k in ["gardena", "gröden", "wolkenstein", "st. christina", "st. ulrich", "ortisei", "selva"]):
            city = "Val Gardena"
        elif any(k in muni_low or k in sname_low or k in scode_low for k in ["meran", "merano", "marlin", "marling"]):
            city = "Meran"
        elif any(k in muni_low or k in sname_low or k in scode_low for k in ["bozen", "bolzano"]):
            city = "Bozen"
        elif any(k in muni_low or k in sname_low or k in scode_low for k in ["brixen", "bressanone"]):
            city = "Brixen"
        elif any(k in muni_low or k in sname_low or k in scode_low for k in ["bruneck", "brunico"]):
            city = "Bruneck"
        elif any(k in muni_low or k in sname_low or k in scode_low for k in ["kastelruth", "castelrotto"]):
            city = "Kastelruth"
        elif any(k in muni_low or k in sname_low or k in scode_low for k in ["ratschings", "racines"]):
            city = "Ratschings"
        else:
            city = muni_raw if muni_raw else "Südtirol"

        # Kapazität
        cap = item.get("pcapacity") or item.get("capacity") or meta.get("capacity") or meta.get("total_capacity")
        try:
            cap = int(float(cap)) if cap else None
        except (ValueError, TypeError):
            cap = None

        coords = item.get("scoordinate") if isinstance(item.get("scoordinate"), dict) else {}
        lat = coords.get("y")
        lng = coords.get("x")

        if sname not in stations_map:
            stations_map[sname] = {
                "name": sname,
                "city": city,
                "capacity": cap,
                "free": None,
                "occupied": None,
                "lat": lat,
                "lng": lng
            }

        if cap and not stations_map[sname]["capacity"]:
            stations_map[sname]["capacity"] = cap

        if lat and not stations_map[sname]["lat"]:
            stations_map[sname]["lat"] = lat
            stations_map[sname]["lng"] = lng

        # Messwert
        if mval is not None:
            try:
                num = int(float(mval))
                if tname in ["free", "freie_plaetze", "free_slots", "slots"]:
                    stations_map[sname]["free"] = num
                elif tname in ["occupied", "belegt", "occupied_slots"]:
                    stations_map[sname]["occupied"] = num
                elif stations_map[sname]["free"] is None:
                    stations_map[sname]["free"] = num
            except (ValueError, TypeError):
                pass

    final_list = []
    for sname, data in stations_map.items():
        cap = data["capacity"]
        free = data["free"]
        occ = data["occupied"]

        if free is None and occ is not None and cap is not None:
            free = max(0, cap - occ)
        elif free is not None and cap is not None and occ is None:
            occ = max(0, cap - free)

        if free is None:
            continue

        if cap and cap > 0:
            auslastung_percent = min(100, max(0, round(((cap - free) / cap) * 100)))
            percent_free = 100 - auslastung_percent
        else:
            auslastung_percent = 0
            percent_free = 100

        status = "voll" if free == 0 else ("knapp" if percent_free < 10 else "frei")

        final_list.append({
            "name": data["name"],
            "city": data["city"],
            "free": free,
            "capacity": cap,
            "auslastung": auslastung_percent,
            "percent_free": percent_free,
            "status": status,
            "lat": data["lat"],
            "lng": data["lng"]
        })

    # Sortierung nach Hauptzonen
    prio = {"bozen": 1, "meran": 2, "val gardena": 3, "brixen": 4, "bruneck": 5, "trento": 6, "rovereto": 7}
    final_list.sort(key=lambda s: (prio.get(s["city"].lower(), 99), s["city"], s["name"]))

    print(f"Erfolgreich {len(final_list)} Standorte extrahiert!")
    return final_list

if __name__ == "__main__":
    results = get_parking_data()
    with open("parken.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
