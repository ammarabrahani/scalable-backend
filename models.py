from sqlalchemy import Table, Column, Integer, String, ForeignKey, MetaData

metadata = MetaData()

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("description", String(500), nullable=True),
    Column("price", nullable=False),
    Column("image", String(1000), nullable=True)  # Store S3 image URL
)

orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("customer_name", String(255), nullable=False)  # New column for customer names
)
