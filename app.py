from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# SQLAlchemy Product model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    product_name = db.Column(db.String(200))
    download_pdfs = db.Column(db.Text)  # Comma-separated string
    product_image_url = db.Column(db.String(300))
    whatsapp_number = db.Column(db.String(20))

# Create the DB
with app.app_context():
    db.create_all()

# API route to add product
@app.route('/add-product', methods=['POST'])
def add_product():
    try:
        data = request.get_json()

        category = data.get('category')
        product_name = data.get('product_name')
        download_pdfs = data.get('download_pdfs', [])
        product_image_url = data.get('product_image_url')
        whatsapp_number = data.get('whatsapp_number')

        if not category or not product_name:
            return jsonify({"error": "category and product_name are required"}), 400

        pdf_str = ",".join(download_pdfs) if isinstance(download_pdfs, list) else str(download_pdfs)

        product = Product(
            category=category,
            product_name=product_name,
            download_pdfs=pdf_str,
            product_image_url=product_image_url,
            whatsapp_number=whatsapp_number
        )

        db.session.add(product)
        db.session.commit()

        return jsonify({"message": "Product added successfully", "product_id": product.id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Health check route (optional)
@app.route("/")
def home():
    return "✅ Flask API is running!"

if __name__ == '__main__':
    app.run(debug=True, port=5001)
