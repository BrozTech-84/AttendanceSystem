from django.core.cache import cache

def get_location_name(lat, lon):
    cache_key = f"loc_{lat}_{lon}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Your geocoding logic here...
    location_name = f"Lat: {lat:.4f}, Lon: {lon:.4f}"
    
    cache.set(cache_key, location_name, 3600)
    return location_name