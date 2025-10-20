"""
Database initialization script for the FastAPI example.

This script:
1. Creates the products table
2. Inserts 1000+ sample products in batches
3. Demonstrates batch insertion for reduced DB load
"""

import asyncio
import os

import asyncpg
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def init_database():
    """Initialize the database with schema and sample data"""
    print("🔄 Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Drop existing table if it exists
        print("🗑️  Dropping existing products table (if exists)...")
        await conn.execute("DROP TABLE IF EXISTS products CASCADE")

        # Create products table
        print("🏗️  Creating products table...")
        await conn.execute(
            """
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                price NUMERIC(10, 2) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Insert sample products in batches
        print("📝 Inserting 1000 sample products in batches...")
        # Base product templates to duplicate
        base_products = [
            (
                "MacBook Pro 16-inch",
                2499.99,
                "Powerful laptop with M3 Pro chip, 16GB RAM, 512GB SSD",
            ),
            (
                "iPhone 15 Pro",
                999.99,
                "Latest iPhone with A17 Pro chip, titanium design, 256GB",
            ),
            (
                "AirPods Pro",
                249.99,
                "Active noise cancellation, adaptive audio, USB-C charging",
            ),
            (
                "iPad Air",
                599.99,
                "10.9-inch Liquid Retina display, M1 chip, 64GB",
            ),
            (
                "Apple Watch Series 9",
                399.99,
                "Always-on Retina display, health monitoring, GPS",
            ),
            (
                "Magic Keyboard",
                99.99,
                "Wireless keyboard with numeric keypad, rechargeable battery",
            ),
            (
                "Magic Mouse",
                79.99,
                "Wireless mouse with Multi-Touch surface",
            ),
            ("Studio Display", 1599.99, "27-inch 5K Retina display, 12MP camera"),
            (
                "HomePod mini",
                99.99,
                "Smart speaker with Siri, room-filling sound",
            ),
            (
                "AirTag 4 pack",
                99.99,
                "Precision finding with Ultra Wideband technology",
            ),
        ]

        # Generate 1000 products by duplicating the base products
        total_products = 1000
        all_products = []
        for i in range(total_products):
            # Cycle through base products
            base_product = base_products[i % len(base_products)]
            # Add a suffix to make them slightly different
            name = f"{base_product[0]} (#{i+1})"
            all_products.append((name, base_product[1], base_product[2]))

        # Insert in batches to reduce database load
        batch_size = 100
        total_inserted = 0

        for i in range(0, len(all_products), batch_size):
            batch = all_products[i : i + batch_size]
            await conn.executemany(
                """
                INSERT INTO products (name, price, description)
                VALUES ($1, $2, $3)
                """,
                batch,
            )
            total_inserted += len(batch)
            print(f"  Inserted {total_inserted}/{total_products} products...")

        # Verify insertion
        count = await conn.fetchval("SELECT COUNT(*) FROM products")
        print(f"✅ Database initialized successfully with {count} products!")

        # Display sample data
        print("\n📦 Sample products:")
        rows = await conn.fetch("SELECT id, name, price FROM products LIMIT 5")
        for row in rows:
            print(f"  - ID {row['id']}: {row['name']} (${row['price']})")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init_database())
