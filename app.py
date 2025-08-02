from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS # Import CORS

app = Flask(__name__)
CORS(app)  # Initialize CORS with your app
# If you want to restrict access to specific origins, you can do:
# CORS(app, resources={r"/*": {"origins": ["https://ismat2.webflow.io", "http://localhost:8000"]}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    product_name = db.Column(db.String(200))
    short_description = db.Column(db.Text)  # New column
    long_description = db.Column(db.Text)   # New column
    price = db.Column(db.Float)             # New column
    discount = db.Column(db.Float)          # New column
    download_pdfs = db.Column(db.Text)
    product_image_url = db.Column(db.String(300))
    whatsapp_number = db.Column(db.String(20))

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "product_name": self.product_name,
            "short_description": self.short_description,
            "long_description": self.long_description,
            "price": self.price,
            "discount": self.discount,
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
        short_description=data.get('short_description'),
        long_description=data.get('long_description'),
        price=data.get('price'),
        discount=data.get('discount'),
        download_pdfs=",".join(data.get('download_pdfs', [])),
        product_image_url=data.get('product_image_url'),
        whatsapp_number=data.get('whatsapp_number')
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Product added", "product_id": product.id}), 201

# Read all products with pagination
@app.route('/products', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int) # Default 10 items per page

    products_pagination = Product.query.paginate(page=page, per_page=per_page, error_out=False)
    
    products = products_pagination.items
    total_pages = products_pagination.pages
    total_items = products_pagination.total

    return jsonify({
        "products": [p.to_dict() for p in products],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page
    }), 200

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
    product.short_description = data.get('short_description', product.short_description)
    product.long_description = data.get('long_description', product.long_description)
    product.price = data.get('price', product.price)
    product.discount = data.get('discount', product.discount)
    product.download_pdfs = ",".join(data.get('download_pdfs', product.download_pdfs.split(",") if product.download_pdfs else []))
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

# Search products with pagination
@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').lower()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int) # Default 10 items per page

    search_results_pagination = Product.query.filter(
        Product.product_name.ilike(f'%{query}%') |
        Product.category.ilike(f'%{query}%') |
        Product.short_description.ilike(f'%{query}%') | # Search in new columns
        Product.long_description.ilike(f'%{query}%')
    ).paginate(page=page, per_page=per_page, error_out=False)

    results = search_results_pagination.items
    total_pages = search_results_pagination.pages
    total_items = search_results_pagination.total

    return jsonify({
        "products": [p.to_dict() for p in results],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page
    }), 200

# Health check
@app.route('/')
def home():
    return "✅ Product API is running!"

if __name__ == '__main__':
    app.run(debug=True, port=5001)
