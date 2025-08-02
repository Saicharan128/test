from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    product_name = db.Column(db.String(200))
    download_pdfs = db.Column(db.Text)
    product_image_url = db.Column(db.String(300))
    whatsapp_number = db.Column(db.String(20))

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "product_name": self.product_name,
            "download_pdfs": self.download_pdfs.split(",") if self.download_pdfs else [],
            "product_image_url": self.product_image_url,
            "whatsapp_number": self.whatsapp_number
        }

# Create DB
with app.app_context():
    db.create_all()

# Create product
@app.route('/add-product', methods=['POST'])
def add_product():
    data = request.get_json()
    product = Product(
        category=data.get('category'),
        product_name=data.get('product_name'),
        download_pdfs=",".join(data.get('download_pdfs', [])),
        product_image_url=data.get('product_image_url'),
        whatsapp_number=data.get('whatsapp_number')
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Product added", "product_id": product.id}), 201

# Read all products
@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products]), 200

# Read single product
@app.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict()), 200

# Update product
@app.route('/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    product = Product.query.get_or_404(product_id)
    product.category = data.get('category', product.category)
    product.product_name = data.get('product_name', product.product_name)
    product.download_pdfs = ",".join(data.get('download_pdfs', product.download_pdfs.split(",")))
    product.product_image_url = data.get('product_image_url', product.product_image_url)
    product.whatsapp_number = data.get('whatsapp_number', product.whatsapp_number)
    db.session.commit()
    return jsonify({"message": "Product updated"}), 200

# Delete product
@app.route('/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"}), 200

# Search products
@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').lower()
    results = Product.query.filter(
        Product.product_name.ilike(f'%{query}%') |
        Product.category.ilike(f'%{query}%')
    ).all()
    return jsonify([p.to_dict() for p in results]), 200

# Health check
@app.route('/')
def home():
    return "✅ Product API is running!"

if __name__ == '__main__':
    app.run(debug=True, port=5001)