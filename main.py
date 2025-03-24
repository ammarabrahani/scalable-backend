from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from pdf2image import convert_from_bytes
import os
import uuid
import logging
import boto3
from db import database  # ✅ Import database from db.py
from models import products, orders
from dotenv import load_dotenv
from sqlalchemy import select, update, delete
from mangum import Mangum



# ✅ Load Environment Variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
handler = Mangum(app)


# ✅ Connect to Database
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ✅ AWS S3 Configuration
AWS_ACCESS_KEY_ID = "ASIAXVH2SGC6VT5KZQIT"
AWS_SECRET_ACCESS_KEY = "kpIxfH/7iojxM615Ix5D8FkNq0cVUTaLXLKeTNZq"
AWS_S3_BUCKET_NAME = "scalablebucket1"
AWS_REGION = "us-east-1"
AWS_SESSION_TOKEN = "IQoJb3JpZ2luX2VjEI7//////////wEaCXVzLXdlc3QtMiJHMEUCIHSQogNqSdfMPYYoPWixyl06zziNNNmAAx11JSTQbDnZAiEAvrff7KBHHNbVcGeDsLKQCOnGHY0j09cU6wlmi9TnhJAqvQII5///////////ARAAGgw1MjY2NTg5NzM4ODUiDHDOof00OpaM2MJe8CqRApZlfF22Lrquqm9LkdfCpyX9GaJNJ21+GJ1bmKQPV8OqpJA6xoTrT+oLyWhF/n79MQXRb2+GD2hJlHstgVEDMNmS1ZcUHIvWZP7FEQDp7hiBxvZGIpNZBiYH9cRnMCvMW0Z6yiCeRNR+MjkXURo3tMt7Z3iW9chhswKZwnSd1eoqKyvks434/0Kt/1KvYiGVzN+3pAXmcRvjVnyL2hpw/PhYErfNioJrT+5NX4XUdVvbdmwm2OL7QeCV8BvjACIYng+EuYoGbWU7b3xJUY2+PFv+d6KoFr58I7YqXPGU2gd3w0QqyxGbY30WHZ2qqX6cWxIWisUO8AgAooGJx596fib9Od3uo7QwziDxjwgWbIatIjCo3IO/BjqdAZeRBT8H/7InprB6bCAFJ29fwCJiC0LeCTMeHRZvdcKLpVuEsSxpIVLjzj/SL+aY7L5L5sVbdn3luN3bpCnwbQlga5Ol4C4N0zAm0wAp/bb61xZJx9xKwdVT/NweMw6KKKjldrC8bh5aSHjKd2GFFDxoeY+hXzVafZErS8pSxaooegdhMpAuY2qqCBtIKrpc9G919clpr6jt8ochI4I="

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET_NAME]):
    raise RuntimeError("AWS credentials or bucket name are missing! Check your .env file.")

# ✅ Poppler Path (PDF to Image Converter)
POPPLER_PATH = r"C:\poppler\Library\bin"  # Windows Example
IMAGE_DIR = "static/images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# ✅ Serve Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ Initialize S3 Client
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN
)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI on AWS!"}

@app.post("/products/")
async def create_product(
    name: str,
    description: str,
    price: float,
    file: UploadFile = File(...)
):
    try:
        # ✅ Convert PDF to Image
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Invalid PDF file uploaded.")

        images = convert_from_bytes(pdf_bytes)
        if not images:
            raise HTTPException(status_code=500, detail="PDF conversion failed.")

        # ✅ Upload First Page of PDF as Product Image
        image_filename = f"{uuid.uuid4()}_page1.png"
        temp_image_path = os.path.join(IMAGE_DIR, image_filename)
        images[0].save(temp_image_path, format="PNG")

        s3_key = f"product_images/{image_filename}"
        s3_client.upload_file(temp_image_path, AWS_S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "image/png"})

        image_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

        # ✅ Store Product in Database with Image URL
        query = products.insert().values(name=name, description=description, price=price, image=image_url)
        await database.execute(query)

        # ✅ Delete Temporary Image
        os.remove(temp_image_path)

        return {"message": "Product created successfully", "image_url": image_url}

    except HTTPException as he:
        logger.error(f"HTTP Error: {he.detail}")
        return {"error": he.detail}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

@app.get("/products/")
async def get_products():
    query = select(products)  # ✅ Correct way to select all columns from the table
    result = await database.fetch_all(query)  # ✅ Execute query in FastAPI
    return {"products": result} if result else {"message": "No products found"}



### **📌 Update (Edit) Product API**
@app.put("/products/{product_id}")
async def update_product(
    product_id: int,
    name: str,
    description: str,
    price: float,
    file: UploadFile = File(None)
):
    try:
        # ✅ Check if the product exists
        product_query = select(products).where(products.c.id == product_id)
        existing_product = await database.fetch_one(product_query)

        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")

        # ✅ Update fields dynamically
        update_values = {}
        if name: update_values["name"] = name
        if description: update_values["description"] = description
        if price: update_values["price"] = price

        # ✅ Handle new image upload if provided
        if file:
            pdf_bytes = await file.read()
            images = convert_from_bytes(pdf_bytes)
            if not images:
                raise HTTPException(status_code=500, detail="PDF conversion failed.")

            image_filename = f"{uuid.uuid4()}_page1.png"
            temp_image_path = os.path.join(IMAGE_DIR, image_filename)
            images[0].save(temp_image_path, format="PNG")

            s3_key = f"product_images/{image_filename}"
            s3_client.upload_file(temp_image_path, AWS_S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "image/png"})
            image_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

            update_values["image"] = image_url
            os.remove(temp_image_path)

        # ✅ Update Product in Database
        update_query = update(products).where(products.c.id == product_id).values(update_values)
        await database.execute(update_query)

        return {"message": "Product updated successfully", "updated_fields": update_values}

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


### **📌 Delete Product API**
@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    try:
        # ✅ Check if product exists
        product_query = select(products).where(products.c.id == product_id)
        existing_product = await database.fetch_one(product_query)

        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")

        # ✅ Delete from database
        delete_query = delete(products).where(products.c.id == product_id)
        await database.execute(delete_query)

        return {"message": "Product deleted successfully"}

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@app.post("/convert-pdf/")
async def convert_pdf(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Invalid PDF file uploaded.")

        images = convert_from_bytes(pdf_bytes)
        if not images:
            raise HTTPException(status_code=500, detail="PDF conversion failed.")

        image_urls = []
        for i, image in enumerate(images):
            image_filename = f"{uuid.uuid4()}_page{i+1}.png"
            temp_image_path = os.path.join(IMAGE_DIR, image_filename)

            image.save(temp_image_path, format="PNG")

            if not os.path.exists(temp_image_path):
                raise FileNotFoundError(f"File not found: {temp_image_path}")

            s3_key = f"pdf_images/{image_filename}"
            s3_client.upload_file(temp_image_path, AWS_S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "image/png"})

            image_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
            image_urls.append(image_url)

            os.remove(temp_image_path)

        return {"filename": file.filename, "image_urls": image_urls, "message": "PDF converted and uploaded to S3 successfully."}

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
    

@app.post("/orders/")
async def create_order(
    product_id,
    quantity,
    customer_name
):
    try:
        # ✅ Check if product exists
        product_query = select(products).where(products.c.id == product_id)
        product = await database.fetch_one(product_query)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # ✅ Insert order into the database
        order_query = orders.insert().values(
            product_id=product_id,
            quantity=quantity,
            customer_name=customer_name
        )
        order_id = await database.execute(order_query)

        return {
            "message": "Order created successfully",
            "order": {
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "customer_name": customer_name
            }
        }

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# ✅ Get All Orders
@app.get("/orders/")
async def get_orders():
    query = select(orders)
    result = await database.fetch_all(query)
    return {"orders": result} if result else {"message": "No orders found"}

# ✅ Get a Single Order by ID
@app.get("/orders/{order_id}")
async def get_order(order_id: int):
    query = select(orders).where(orders.c.id == order_id)
    order = await database.fetch_one(query)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {"order": order}

