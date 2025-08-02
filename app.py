from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    product_name = db.Column(db.String(200))
    short_description = db.Column(db.Text)
    long_description = db.Column(db.Text)
    price = db.Column(db.Float)
    discount = db.Column(db.Float)
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

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# UI Routes
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    products_pagination = Product.query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('index.html', products=products_pagination.items, pagination=products_pagination)

@app.route('/add', methods=['GET', 'POST'])
def add_product_ui():
    if request.method == 'POST':
        data = request.form
        files = request.files.getlist('pdfs')
        image = request.files.get('image')

        image_url = ''
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_url = f"/{image_path}"

        pdf_urls = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(pdf_path)
                pdf_urls.append(f"/{pdf_path}")

        product = Product(
            category=data.get('category'),
            product_name=data.get('product_name'),
            short_description=data.get('short_description'),
            long_description=data.get('long_description'),
            price=float(data.get('price')) if data.get('price') else 0.0,
            discount=float(data.get('discount')) if data.get('discount') else 0.0,
            download_pdfs=",".join(pdf_urls),
            product_image_url=image_url,
            whatsapp_number=data.get('whatsapp_number')
        )
        db.session.add(product)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('add_product.html')

@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product_ui(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        data = request.form
        files = request.files.getlist('pdfs')
        image = request.files.get('image')

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            product.product_image_url = f"/{image_path}"

        pdf_urls = product.download_pdfs.split(",") if product.download_pdfs else []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(pdf_path)
                pdf_urls.append(f"/{pdf_path}")

        product.category = data.get('category', product.category)
        product.product_name = data.get('product_name', product.product_name)
        product.short_description = data.get('short_description', product.short_description)
        product.long_description = data.get('long_description', product.long_description)
        product.price = float(data.get('price', product.price)) if data.get('price') else product.price
        product.discount = float(data.get('discount', product.discount)) if data.get('discount') else product.discount
        product.download_pdfs = ",".join(pdf_urls)
        product.whatsapp_number = data.get('whatsapp_number', product.whatsapp_number)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('edit_product.html', product=product)

@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product_ui(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

# Existing API Routes
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

@app.route('/products', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    products_pagination = Product.query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "products": [p.to_dict() for p in products_pagination.items],
        "total_items": products_pagination.total,
        "total_pages": products_pagination.pages,
        "current_page": page,
        "per_page": per_page
    }), 200

@app.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict()), 200

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

@app.route('/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').lower()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_results_pagination = Product.query.filter(
        Product.product_name.ilike(f'%{query}%') |
        Product.category.ilike(f'%{query}%') |
        Product.short_description.ilike(f'%{query}%') |
        Product.long_description.ilike(f'%{query}%')
    ).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "products": [p.to_dict() for p in search_results_pagination.items],
        "total_items": search_results_pagination.total,
        "total_pages": search_results_pagination.pages,
        "current_page": page,
        "per_page": per_page
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)