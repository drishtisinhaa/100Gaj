import httpx
from llama_index.core.tools import FunctionTool
from typing import Optional, List, Dict, Union
import certifi
import re
import logging

logger = logging.getLogger(__name__)
API_URL = "https://100gaj.vercel.app/api/properties"
_property_data_cache: Optional[List[Dict]] = None

def _fetch_all_data() -> List[Dict]:
    global _property_data_cache
    if _property_data_cache is not None:
        return _property_data_cache
    
    logger.info(f"--- Fetching ALL properties from {API_URL} (This should happen only once per server start) ---")
    try:
        ssl_context = httpx.create_ssl_context(verify=certifi.where())
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(API_URL, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        if data.get("success") and isinstance(data.get("properties"), list):
            _property_data_cache = data["properties"]
            return _property_data_cache
        return []
    except Exception as e:
        logger.error(f"FATAL ERROR fetching property data: {e}", exc_info=True)
        return []

def format_price(price: Union[int, float, str]) -> str:
    if not isinstance(price, (int, float)): return str(price)
    if price >= 10000000: return f"₹{price / 10000000:.2f} Crores"
    return f"₹{price / 100000:.2f} Lakhs"

def query_property_database(
    city: Optional[str] = None,
    listing_type: Optional[Union[str, List[str]]] = None,
    property_type: Optional[str] = None
) -> str:
    """
    Searches the in-memory property database with a robust, universal search for any city.
    """
    all_properties = _fetch_all_data()
    if not all_properties:
        return "I apologize, but I'm unable to access the property database at the moment."

    results = all_properties

    # --- THIS IS THE FLEXIBLE, RECOMMENDED SEARCH LOGIC THAT WORKS FOR ALL CITIES ---
    if city:
        city_lower = city.lower().strip()
        search_terms = [city_lower]
        # Add common aliases to make the search smarter
        if city_lower == "gurgaon":
            search_terms.append("gurugram")
        
        results = [
            p for p in results if any(
                term in p.get("address", {}).get("city", "").lower() or
                term in p.get("address", {}).get("state", "").lower() or
                term in p.get("address", {}).get("street", "").lower()
                for term in search_terms
            )
        ]
    # --- END OF FLEXIBLE LOGIC ---

    if listing_type:
        if isinstance(listing_type, str):
            listing_type_filters = [listing_type.lower().replace("buy", "sale")]
        else:
            listing_type_filters = [lt.lower().replace("buy", "sale") for lt in listing_type]
        results = [p for p in results if p.get("listingType", "").lower() in listing_type_filters]

    if property_type:
        results = [p for p in results if p.get("propertyType", "").lower() == property_type.lower()]

    if not results:
        return f"I could not find any properties matching your criteria. Try searching in other nearby areas or adjusting your search criteria."

    # Format results
    formatted_results = []
    for prop in results[:5]:
        address = prop.get("address", {})
        price_str = format_price(prop.get("price", 0))
        street = address.get("street", "").strip()
        city_name = address.get("city", "").strip()
        state = address.get("state", "").strip()
        location_parts = [p for p in [street, city_name, state] if p]
        location = ", ".join(location_parts) if location_parts else "Location not specified"
        details = [f"\n🏠 Property Details:", f"Title: {prop.get('title', 'N/A')}", f"Location: {location}", f"Price: {price_str}", f"Type: {prop.get('propertyType', 'N/A').capitalize()}", f"Configuration: {prop.get('bedrooms', 'N/A')} BHK, {prop.get('bathrooms', 'N/A')} Bath", f"Area: {prop.get('area', 'N/A')} sq ft", f"Status: {'Furnished' if prop.get('furnished') else 'Unfurnished'}", f"Available for: {prop.get('listingType', 'N/A').upper()}"]
        amenities = prop.get("amenities", [])
        if amenities: details.append(f"Amenities: {', '.join(amenities)}")
        owner = prop.get("ownerDetails", {})
        if owner and owner.get('name'): details.extend(["\n📞 Contact Information:", f"Owner: {owner.get('name', 'N/A')}", f"Phone: {owner.get('phone', 'N/A')}"])
        formatted_results.append("\n".join(details))

    return "\n\n" + "\n\n---\n\n".join(formatted_results)

property_database_tool = FunctionTool.from_defaults(
    fn=query_property_database,
    name="query_property_database",
    description="Use this to find and list properties. You can filter by `city`, `listing_type` (sale/rent), and `property_type`."
)