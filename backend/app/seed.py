import logging
from typing import Any, Dict, List

from .database import db
from .models import Product, advertised_price, default_variant

logger = logging.getLogger(__name__)

SEED_PRODUCTS: List[Dict[str, Any]] = [
    {
        "name": "Nayara Washing Soap Bar",
        "slug": "washing-soap-bar",
        "category": "laundry",
        "short_description": "Pure herbal laundry soap bar that lifts stains without harshness.",
        "description": "A gentle yet powerful laundry soap bar made with plant-derived actives. Removes tough stains from cottons, silks and everyday wear while keeping fabric colours bright. Factory-pressed in small batches for a premium, long-lasting bar.",
        "price": 45.0,
        "mrp": 60.0,
        "image": "https://images.unsplash.com/photo-1542038335240-86aea625b913?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzV8MHwxfHNlYXJjaHwyfHxtaW5pbWFsJTIwc29hcCUyMHBhY2thZ2luZ3xlbnwwfHx8fDE3NzY2ODM4Nzh8MA&ixlib=rb-4.1.0&q=85",
        "badges": ["Made in India", "Factory Direct"],
        "featured": True,
        "stock": 250,
    },
    {
        "name": "Nayara Washing Powder Detergent 1kg",
        "slug": "washing-powder-1kg",
        "category": "laundry",
        "short_description": "Active-enzyme powder detergent for machine & hand wash.",
        "description": "Premium high-foam washing powder with active enzymes that attack tough stains on collars, cuffs and underarms. Safe for both top-load and front-load machines. Fresh citrus fragrance that lingers all day.",
        "price": 180.0,
        "mrp": 240.0,
        "image": "https://images.unsplash.com/photo-1582020711621-ab153a0f3631?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjV8MHwxfHNlYXJjaHwzfHxmcmVzaCUyMGNsZWFuaW5nJTIwcHJvZHVjdHN8ZW58MHx8fHwxNzc2NjgzODQ4fDA&ixlib=rb-4.1.0&q=85",
        "badges": ["Made in India", "Factory Direct"],
        "featured": True,
        "stock": 180,
    },
    {
        "name": "Nayara Liquid Detergent 1L",
        "slug": "liquid-detergent-1l",
        "category": "laundry",
        "short_description": "Concentrated liquid detergent — low suds, deep clean.",
        "description": "A concentrated formula designed for modern washing machines. Dissolves fully in cold or hot water with no residue. 1 litre delivers up to 33 washes. Dermatologically tested for sensitive skin.",
        "price": 249.0,
        "mrp": 329.0,
        "image": "",
        "badges": ["Made in India", "Skin Safe"],
        "featured": True,
        "stock": 150,
    },
    {
        "name": "Nayara Handwash Soap Bar",
        "slug": "handwash-soap-bar",
        "category": "personal-care",
        "short_description": "Germ-fighting hand soap bar with neem & tulsi.",
        "description": "Traditional Indian hand soap bar enriched with neem and tulsi extracts. Kills 99.9% of common household germs while keeping hands soft. Long-lasting bar with a grounded herbal fragrance.",
        "price": 35.0,
        "mrp": 50.0,
        "image": "https://images.unsplash.com/photo-1600857544200-b2f666a9a2ec?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
        "badges": ["Made in India", "Herbal"],
        "featured": False,
        "stock": 300,
    },
    {
        "name": "Nayara Handwash Liquid 250ml",
        "slug": "handwash-liquid-250ml",
        "category": "personal-care",
        "short_description": "Moisturising liquid handwash with aloe & glycerin.",
        "description": "A pH-balanced liquid handwash that cleanses without stripping natural moisture. Aloe vera and glycerin keep skin hydrated; a fresh green-tea fragrance leaves you feeling renewed after every wash.",
        "price": 99.0,
        "mrp": 145.0,
        "image": "",
        "badges": ["Made in India", "pH Balanced"],
        "featured": True,
        "stock": 220,
    },
    {
        "name": "Nayara Bathing Soap",
        "slug": "bathing-soap",
        "category": "personal-care",
        "short_description": "Premium bathing bar with shea butter & sandalwood.",
        "description": "A luxurious daily bathing bar enriched with shea butter and Mysore sandalwood oil. Leaves skin silky smooth with a lingering temple-grade sandalwood aroma. Crafted in small factory batches.",
        "price": 55.0,
        "mrp": 75.0,
        "image": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
        "badges": ["Made in India", "Shea Butter"],
        "featured": True,
        "stock": 400,
    },
    {
        "name": "Nayara Toilet Cleaner 500ml",
        "slug": "toilet-cleaner-500ml",
        "category": "home-care",
        "short_description": "Thick disinfectant gel for sparkling toilets.",
        "description": "Ultra-thick toilet bowl cleaner that clings to vertical surfaces for maximum contact time. Dissolves hard water stains, limescale and yellow deposits. Kills 99.9% germs with a fresh pine fragrance.",
        "price": 120.0,
        "mrp": 165.0,
        "image": "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
        "badges": ["Made in India", "99.9% Germ Kill"],
        "featured": False,
        "stock": 160,
    },
]


async def seed_products() -> int:
    """Fill an empty catalogue with the starter products.

    Nothing is written when products already exist, so prices and stock edited
    through the admin screens are never overwritten. The count of inserted
    products is returned so callers can report what happened.
    """
    if await db.products.count_documents({}) > 0:
        return 0

    documents = []
    for seed_product in SEED_PRODUCTS:
        # Seeded products satisfy the same rule as any other: at least one
        # variant, and an advertised price taken from it.
        data = {**seed_product, "variants": [default_variant(seed_product)]}
        document = Product(**data).model_dump()
        document["created_at"] = document["created_at"].isoformat()
        document["price_from"] = advertised_price(document["variants"])
        documents.append(document)

    await db.products.insert_many(documents)
    logger.info("Seeded starter products", extra={"count": len(documents)})
    return len(documents)
