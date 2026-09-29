import json
import urllib.request
import ssl

URL = "https://mobility.api.opendatahub.com/v2/flat/ParkingStation/*/latest?limit=200"

def get_parking_data():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "SuedtirolMagazin/1.0 (Contact: info@suedtirolmagazin.it)"}
    )
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Fehler beim Abruf: {e}")
        return []

    stations = []
    
    for item in data.get("data", []):
        name = item.get("sname") or item.get("name")
        city = item.get("municipality", "Südtirol")
        
        free_spots = item.get("mvalue")
        capacity = item.get("pcapacity") or item.get("capacity")
        
        if name and free_spots is not None and free_spots >= 0:
            free = int(free_spots)
            cap = int(capacity) if capacity and capacity > 0 else None
            
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
                
            stations.append({
                "name": name,
                "city": city,
                "free": free,
                "capacity": cap,
                "percent_free": percent_free,
                "status": status,
                "lat": item.get("scoordinate", {}).get("y") if isinstance(item.get("scoordinate"), dict) else None,
                "lng": item.get("scoordinate", {}).get("x") if isinstance(item.get("scoordinate"), dict) else None
            })

    stations.sort(key=lambda x: (x["city"] not in ["Bozen", "Bolzano", "Meran", "Merano"], x["name"]))
    return stations

if __name__ == "__main__":
    results = get_parking_data()
    print(f"Erfolgreich {len(results)} Parkstationen gefunden.")
    
    with open("parken.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
