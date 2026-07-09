from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
import psycopg2

app = Flask(__name__)
CORS(app)

APP_NAME = os.getenv("APP_NAME", "ShopEasy")
SERVICE_NAME = os.getenv("SERVICE_NAME", "product-service")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
PORT = int(os.getenv("PORT", "5000"))

DB_HOST = os.getenv("DB_HOST", "postgres-service")
DB_NAME = os.getenv("DB_NAME", "shopeasy")
DB_USER = os.getenv("DB_USERNAME", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin123")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


@app.route("/", methods=["GET"])
def home():
    return jsonify(
        {
            "service": SERVICE_NAME,
            "environment": ENVIRONMENT,
            "message": f"Welcome to {APP_NAME} Product Service - Dev GitOps Manual Test"
        }
    )


@app.route("/api/products", methods=["GET"])
def get_products():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, price
            FROM products
            ORDER BY id
            """
        )

        rows = cursor.fetchall()

        products = []

        for row in rows:
            products.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "price": row[2]
                }
            )

        cursor.close()
        conn.close()

        return jsonify(products)

    except Exception as e:
        logging.error(f"Database error: {e}")

        return jsonify(
            {
                "error": str(e)
            }
        ), 500


@app.route("/api/products/count", methods=["GET"])
def get_product_count():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM products
            """
        )

        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return jsonify(
            {
                "count": count
            }
        )

    except Exception as e:
        logging.error(f"Database error: {e}")

        return jsonify(
            {
                "error": str(e)
            }
        ), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "UP",
            "service": SERVICE_NAME,
            "environment": ENVIRONMENT
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT
    )