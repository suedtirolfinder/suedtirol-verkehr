import json
import urllib.request
import ssl

URL = "https://mobility.api.opendatahub.com/v2/flat/ParkingStation/*/latest?limit=1000"

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

    # Stationen nach Station-Code / Name gruppieren
    stations_map = {}

    for item in raw_items:
        sname = item.get("sname") or item.get("scode")
        if not sname:
            continue

        meta = item.get("smetadata") if isinstance(item.get("smetadata"), dict) else {}
        mval = item.get("mvalue")
        tname = str(item.get("tname", "")).lower()

        # Gemeinde bestimmen
        municipality = item.get("municipality") or meta.get("city") or meta.get("municipality") or ""
        
        # Falls Gemeinde leer, aus Namen raten
        if not municipality:
            sn_low = sname.lower()
            if "meran" in sn_low or "merano" in sn_low:
                municipality = "Meran"
            elif "brixen" in sn_low or "bressanone" in sn_low:
                municipality = "Brixen"
            elif "bruneck" in sn_low or "brunico" in sn_low:
                municipality = "Bruneck"
            elif "bozen" in sn_low or "bolzano" in sn_low:
                municipality = "Bozen"
            elif "kastelruth" in sn_low or "castelrotto" in sn_low:
                municipality = "Kastelruth"
            elif "ratschings" in sn_low or "racines" in sn_low:
                municipality = "Ratschings"
            else:
                municipality = "Südtirol"

        # Kapazität ermitteln
        cap = item.get("pcapacity") or item.get("capacity") or meta.get("capacity") or meta.get("total_capacity")
        try:
            cap = int(float(cap)) if cap else None
        except (ValueError, TypeError):
            cap = None

        coords = item.get("scoordinate") if isinstance(item.get("scoordinate"), dict) else {}
        lat = coords.get("y")
        lng = coords.get("x")

        # Initialisieren falls neu
        if sname not in stations_map:
            stations_map[sname] = {
                "name": sname,
                "city": municipality,
                "capacity": cap,
                "free": None,
                "occupied": None,
                "lat": lat,
                "lng": lng
            }
        
        if cap and not stations_map[sname]["capacity"]:
            stations_map[sname]["capacity"] = cap

        # Messwert auswerten
        if mval is not None:
            try:
                num = int(float(mval))
                if tname in ["free", "freie_plaetze", "free_slots"]:
                    stations_map[sname]["free"] = num
                elif tname in ["occupied", "belegt", "occupied_slots"]:
                    stations_map[sname]["occupied"] = num
                elif stations_map[sname]["free"] is None:
                    # Fallback falls kein tname
                    stations_map[sname]["free"] = num
            except (ValueError, TypeError):
                pass

    final_list = []
    for sname, data in stations_map.items():
        cap = data["capacity"]
        free = data["free"]
        occ = data["occupied"]

        # Freie Plätze errechnen, falls nur "belegt" geliefert wurde
        if free is None and occ is not None and cap is not None:
            free = max(0, cap - occ)
        elif free is not None and cap is not None and occ is None:
            occ = max(0, cap - free)

        # Wenn wir gar keinen Zahlenwert haben, überspringen
        if free is None:
            continue

        # Auslastung & Prozent
        if cap and cap > 0:
            auslastung_percent = min(100, max(0, round(((cap - free) / cap) * 100)))
            percent_free = 100 - auslastung_percent
        else:
            auslastung_percent = 0
            percent_free = 100

        # Status
        if free == 0:
            status = "voll"
        elif percent_free < 10:
            status = "knapp"
        else:
            status = "frei"

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

    # Sortieren: Bozen & Meran oben, dann alphabetisch
    final_list.sort(key=lambda x: (x["city"] in ["Südtirol"], x["city"], x["name"]))
    print(f"Erfolgreich {len(final_list)} Standorte extrahiert!")
    return final_list

if __name__ == "__main__":
    results = get_parking_data()
    with open("parken.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
