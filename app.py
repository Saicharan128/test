from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
from datetime import datetime
import base64
import uuid

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf', 'mp4', 'mov'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    orders = db.relationship('Order', backref='user', lazy=True)

# Variant Model
class Variant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    variant_name = db.Column(db.String(50), nullable=False)
    variant_price = db.Column(db.Float, nullable=False)

# Order Model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Paid')  # Paid, Out for Delivery, Delivered

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    product_name = db.Column(db.String(200))
    brand = db.Column(db.String(100), nullable=True)  # New brand column
    short_description = db.Column(db.Text)
    long_description = db.Column(db.Text)
    detailed_description = db.Column(db.Text)
    mrp = db.Column(db.Float)
    offer_price = db.Column(db.Float)
    sku = db.Column(db.String(50))
    in_stock = db.Column(db.Boolean, default=True)
    stock_number = db.Column(db.Integer)
    download_pdfs = db.Column(db.Text)
    product_image_urls = db.Column(db.Text)
    additional_media_urls = db.Column(db.Text)
    youtube_links = db.Column(db.Text)
    technical_information = db.Column(db.Text)
    manufacturer = db.Column(db.String(200))
    special_note = db.Column(db.Text)
    whatsapp_number = db.Column(db.String(20))
    is_rubber = db.Column(db.Boolean, default=False)
    rubber_density = db.Column(db.Float, nullable=True)
    rubber_height = db.Column(db.Float, nullable=True)
    rubber_length = db.Column(db.Float, nullable=True)
    rubber_thickness = db.Column(db.Float, nullable=True)
    rubber_description = db.Column(db.Text, nullable=True)
    show_in_store = db.Column(db.Boolean, default=True)
    variants = db.relationship('Variant', backref='product', lazy=True, cascade="all, delete-orphan")
    orders = db.relationship('Order', backref='product', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "product_name": self.product_name,
            "brand": self.brand,  # Added brand
            "short_description": self.short_description,
            "long_description": self.long_description,
            "detailed_description": self.detailed_description,
            "mrp": self.mrp,
            "offer_price": self.offer_price,
            "sku": self.sku,
            "in_stock": self.in_stock,
            "stock_number": self.stock_number,
            "download_pdfs": self.download_pdfs.split(",") if self.download_pdfs else [],
            "product_image_urls": self.product_image_urls.split(",") if self.product_image_urls else [],
            "additional_media_urls": self.additional_media_urls.split(",") if self.additional_media_urls else [],
            "youtube_links": self.youtube_links.split(",") if self.youtube_links else [],
            "technical_information": self.technical_information,
            "manufacturer": self.manufacturer,
            "special_note": self.special_note,
            "whatsapp_number": self.whatsapp_number,
            "is_rubber": self.is_rubber,
            "rubber_density": self.rubber_density,
            "rubber_height": self.rubber_height,
            "rubber_length": self.rubber_length,
            "rubber_thickness": self.rubber_thickness,
            "rubber_description": self.rubber_description,
            "show_in_store": self.show_in_store,
            "variants": [{"variant_name": v.variant_name, "variant_price": v.variant_price} for v in self.variants]
        }

# Create DB
with app.app_context():
    db.create_all()

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Helper function to save Base64 image
def save_base64_image(base64_string, folder):
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        filename = f"{uuid.uuid4().hex}.png"
        filepath = os.path.join(folder, filename)
        with open(filepath, 'wb') as f:
            f.write(img_data)
        return f"{folder}/{filename}"
    except Exception as e:
        app.logger.error(f"Error saving Base64 image: {str(e)}")
        return None

# Login required decorator
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error="Username already exists")
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Serve static files explicitly
@app.route('/static/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# UI Routes
@app.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '').lower()
    category = request.args.get('category')
    brand = request.args.get('brand')
    in_stock = request.args.get('in_stock')
    show_in_store = request.args.get('show_in_store')
    per_page = 10
    
    query_obj = Product.query
    if query:
        query_obj = query_obj.filter(
            Product.product_name.ilike(f'%{query}%') |
            Product.category.ilike(f'%{query}%') |
            Product.brand.ilike(f'%{query}%') |
            Product.short_description.ilike(f'%{query}%') |
            Product.long_description.ilike(f'%{query}%') |
            Product.detailed_description.ilike(f'%{query}%') |
            Product.rubber_description.ilike(f'%{query}%')
        )
    if category:
        query_obj = query_obj.filter(Product.category.ilike(f'%{category}%'))
    if brand:
        query_obj = query_obj.filter(Product.brand.ilike(f'%{category}%'))
    if in_stock:
        query_obj = query_obj.filter(Product.in_stock == (in_stock == 'true'))
    if show_in_store:
        query_obj = query_obj.filter(Product.show_in_store == (show_in_store == 'true'))
    
    products_pagination = query_obj.paginate(page=page, per_page=per_page, error_out=False)
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.order_date.desc()).all()
    return render_template('index.html', products=products_pagination.items, pagination=products_pagination, orders=orders, query=query)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product_ui():
    if request.method == 'POST':
        data = request.form
        images = request.files.getlist('images')
        pdfs = request.files.getlist('pdfs')
        media_files = request.files.getlist('media_files')
        variant_names = request.form.getlist('variant_name[]')
        variant_prices = request.form.getlist('variant_price[]')
        base64_images = request.form.getlist('base64_images[]')
        
        image_urls = []
        for image in images:
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    image.save(image_path)
                    image_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved image: {image_path}")
                except Exception as e:
                    app.logger.error(f"Error saving image {filename}: {str(e)}")
        
        for base64_image in base64_images:
            if base64_image:
                image_path = save_base64_image(base64_image, app.config['UPLOAD_FOLDER'])
                if image_path:
                    image_urls.append(image_path)
        
        pdf_urls = []
        for pdf in pdfs:
            if pdf and allowed_file(pdf.filename):
                filename = secure_filename(pdf.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    pdf.save(pdf_path)
                    pdf_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved PDF: {pdf_path}")
                except Exception as e:
                    app.logger.error(f"Error saving PDF {filename}: {str(e)}")
        
        media_urls = []
        for media in media_files:
            if media and allowed_file(media.filename):
                filename = secure_filename(media.filename)
                media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    media.save(media_path)
                    media_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved media: {media_path}")
                except Exception as e:
                    app.logger.error(f"Error saving media {filename}: {str(e)}")
        
        product = Product(
            category=data.get('category'),
            product_name=data.get('product_name'),
            brand=data.get('brand'),  # Added brand
            short_description=data.get('short_description'),
            long_description=data.get('long_description'),
            detailed_description=data.get('detailed_description'),
            mrp=float(data.get('mrp')) if data.get('mrp') else 0.0,
            offer_price=float(data.get('offer_price')) if data.get('offer_price') else 0.0,
            sku=data.get('sku'),
            in_stock=data.get('in_stock') == 'on',
            stock_number=int(data.get('stock_number')) if data.get('stock_number') else 0,
            download_pdfs=",".join(pdf_urls),
            product_image_urls=",".join(image_urls),
            additional_media_urls=",".join(media_urls),
            youtube_links=data.get('youtube_links'),
            technical_information=data.get('technical_information'),
            manufacturer=data.get('manufacturer'),
            special_note=data.get('special_note'),
            whatsapp_number=data.get('whatsapp_number'),
            is_rubber=data.get('is_rubber') == 'on',
            rubber_density=float(data.get('rubber_density')) if data.get('rubber_density') else None,
            rubber_height=float(data.get('rubber_height')) if data.get('rubber_height') else None,
            rubber_length=float(data.get('rubber_length')) if data.get('rubber_length') else None,
            rubber_thickness=float(data.get('rubber_thickness')) if data.get('rubber_thickness') else None,
            rubber_description=data.get('rubber_description'),
            show_in_store=data.get('show_in_store') == 'on'
        )
        db.session.add(product)
        db.session.flush()
        
        for name, price in zip(variant_names, variant_prices):
            if name and price:
                variant = Variant(
                    product_id=product.id,
                    variant_name=name,
                    variant_price=float(price) if price else 0.0
                )
                db.session.add(variant)
        
        db.session.commit()
        app.logger.debug(f"Added product: {product.product_name}, Image URLs: {product.product_image_urls}")
        return redirect(url_for('index'))
    
    return render_template('add_product.html')

@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product_ui(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        data = request.form
        images = request.files.getlist('images')
        pdfs = request.files.getlist('pdfs')
        media_files = request.files.getlist('media_files')
        variant_names = request.form.getlist('variant_name[]')
        variant_prices = request.form.getlist('variant_price[]')
        variant_ids = request.form.getlist('variant_id[]')
        base64_images = request.form.getlist('base64_images[]')
        delete_images = data.getlist('delete_images[]')
        image_order = data.getlist('image_order[]')
        
        image_urls = product.product_image_urls.split(",") if product.product_image_urls else []
        image_urls = [url for url in image_urls if url not in delete_images]
        
        for image in images:
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    image.save(image_path)
                    image_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved image: {image_path}")
                except Exception as e:
                    app.logger.error(f"Error saving image {filename}: {str(e)}")
        
        for base64_image in base64_images:
            if base64_image:
                image_path = save_base64_image(base64_image, app.config['UPLOAD_FOLDER'])
                if image_path:
                    image_urls.append(image_path)
        
        if image_order:
            ordered_urls = []
            for url in image_order:
                if url in image_urls:
                    ordered_urls.append(url)
            for url in image_urls:
                if url not in ordered_urls:
                    ordered_urls.append(url)
            image_urls = ordered_urls
        
        pdf_urls = product.download_pdfs.split(",") if product.download_pdfs else []
        for pdf in pdfs:
            if pdf and allowed_file(pdf.filename):
                filename = secure_filename(pdf.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    pdf.save(pdf_path)
                    pdf_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved PDF: {pdf_path}")
                except Exception as e:
                    app.logger.error(f"Error saving PDF {filename}: {str(e)}")
        
        media_urls = product.additional_media_urls.split(",") if product.additional_media_urls else []
        for media in media_files:
            if media and allowed_file(media.filename):
                filename = secure_filename(media.filename)
                media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    media.save(media_path)
                    media_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved media: {media_path}")
                except Exception as e:
                    app.logger.error(f"Error saving media {filename}: {str(e)}")
        
        product.category = data.get('category', product.category)
        product.product_name = data.get('product_name', product.product_name)
        product.brand = data.get('brand', product.brand)
        product.short_description = data.get('short_description', product.short_description)
        product.long_description = data.get('long_description', product.long_description)
        product.detailed_description = data.get('detailed_description', product.detailed_description)
        product.mrp = float(data.get('mrp', product.mrp)) if data.get('mrp') else product.mrp
        product.offer_price = float(data.get('offer_price', product.offer_price)) if data.get('offer_price') else product.offer_price
        product.sku = data.get('sku', product.sku)
        product.in_stock = data.get('in_stock') == 'on'
        product.stock_number = int(data.get('stock_number', product.stock_number)) if data.get('stock_number') else product.stock_number
        product.download_pdfs = ",".join(pdf_urls)
        product.product_image_urls = ",".join(image_urls)
        product.additional_media_urls = ",".join(media_urls)
        product.youtube_links = data.get('youtube_links', product.youtube_links)
        product.technical_information = data.get('technical_information', product.technical_information)
        product.manufacturer = data.get('manufacturer', product.manufacturer)
        product.special_note = data.get('special_note', product.special_note)
        product.whatsapp_number = data.get('whatsapp_number', product.whatsapp_number)
        product.is_rubber = data.get('is_rubber') == 'on'
        product.rubber_density = float(data.get('rubber_density')) if data.get('rubber_density') else None
        product.rubber_height = float(data.get('rubber_height')) if data.get('rubber_height') else None
        product.rubber_length = float(data.get('rubber_length')) if data.get('rubber_length') else None
        product.rubber_thickness = float(data.get('rubber_thickness')) if data.get('rubber_thickness') else None
        product.rubber_description = data.get('rubber_description', product.rubber_description)
        product.show_in_store = data.get('show_in_store') == 'on'
        
        existing_variant_ids = set(v.id for v in product.variants)
        submitted_variant_ids = set(int(vid) for vid in variant_ids if vid)
        variants_to_delete = existing_variant_ids - submitted_variant_ids
        for vid in variants_to_delete:
            variant = Variant.query.get(vid)
            if variant:
                db.session.delete(variant)
        
        for i, (name, price) in enumerate(zip(variant_names, variant_prices)):
            if name and price:
                if i < len(variant_ids) and variant_ids[i]:
                    variant = Variant.query.get(int(variant_ids[i]))
                    if variant:
                        variant.variant_name = name
                        variant.variant_price = float(price) if price else 0.0
                else:
                    variant = Variant(
                        product_id=product.id,
                        variant_name=name,
                        variant_price=float(price) if price else 0.0
                    )
                    db.session.add(variant)
        
        db.session.commit()
        app.logger.debug(f"Updated product: {product.product_name}, Image URLs: {product.product_image_urls}")
        return redirect(url_for('index'))
    
    return render_template('edit_product.html', product=product)

@app.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product_ui(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    app.logger.debug(f"Deleted product ID: {product_id}")
    return redirect(url_for('index'))

@app.route('/delete-products', methods=['POST'])
@login_required
def delete_products():
    product_ids = request.form.getlist('product_ids[]')
    for product_id in product_ids:
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
    db.session.commit()
    app.logger.debug(f"Deleted products: {product_ids}")
    return redirect(url_for('index'))

# API Routes
@app.route('/add-product', methods=['POST'])
def add_product():
    data = request.get_json()
    image_urls = []
    for base64_image in data.get('base64_images', []):
        if base64_image:
            image_path = save_base64_image(base64_image, app.config['UPLOAD_FOLDER'])
            if image_path:
                image_urls.append(image_path)
    
    product = Product(
        category=data.get('category'),
        product_name=data.get('product_name'),
        brand=data.get('brand'),
        short_description=data.get('short_description'),
        long_description=data.get('long_description'),
        detailed_description=data.get('detailed_description'),
        mrp=data.get('mrp'),
        offer_price=data.get('offer_price'),
        sku=data.get('sku'),
        in_stock=data.get('in_stock', True),
        stock_number=data.get('stock_number', 0),
        download_pdfs=",".join(data.get('download_pdfs', [])),
        product_image_urls=",".join(image_urls + data.get('product_image_urls', [])),
        additional_media_urls=",".join(data.get('additional_media_urls', [])),
        youtube_links=data.get('youtube_links'),
        technical_information=data.get('technical_information'),
        manufacturer=data.get('manufacturer'),
        special_note=data.get('special_note'),
        whatsapp_number=data.get('whatsapp_number'),
        is_rubber=data.get('is_rubber', False),
        rubber_density=data.get('rubber_density'),
        rubber_height=data.get('rubber_height'),
        rubber_length=data.get('rubber_length'),
        rubber_thickness=data.get('rubber_thickness'),
        rubber_description=data.get('rubber_description'),
        show_in_store=data.get('show_in_store', True)
    )
    db.session.add(product)
    db.session.flush()
    
    for variant_data in data.get('variants', []):
        if variant_data.get('variant_name') and variant_data.get('variant_price'):
            variant = Variant(
                product_id=product.id,
                variant_name=variant_data.get('variant_name'),
                variant_price=variant_data.get('variant_price')
            )
            db.session.add(variant)
    
    db.session.commit()
    app.logger.debug(f"API: Added product: {product.product_name}")
    return jsonify({"message": "Product added", "product_id": product.id}), 201

@app.route('/products', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category')
    brand = request.args.get('brand')
    in_stock = request.args.get('in_stock', type=bool)
    show_in_store = request.args.get('show_in_store', type=bool)
    
    query = Product.query
    if category:
        query = query.filter(Product.category.ilike(f'%{category}%'))
    if brand:
        query = query.filter(Product.brand.ilike(f'%{brand}%'))
    if in_stock is not None:
        query = query.filter(Product.in_stock == in_stock)
    if show_in_store is not None:
        query = query.filter(Product.show_in_store == show_in_store)
    
    products_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
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
    image_urls = product.product_image_urls.split(",") if product.product_image_urls else []
    
    for base64_image in data.get('base64_images', []):
        if base64_image:
            image_path = save_base64_image(base64_image, app.config['UPLOAD_FOLDER'])
            if image_path:
                image_urls.append(image_path)
    
    product.category = data.get('category', product.category)
    product.product_name = data.get('product_name', product.product_name)
    product.brand = data.get('brand', product.brand)
    product.short_description = data.get('short_description', product.short_description)
    product.long_description = data.get('long_description', product.long_description)
    product.detailed_description = data.get('detailed_description', product.detailed_description)
    product.mrp = data.get('mrp', product.mrp)
    product.offer_price = data.get('offer_price', product.offer_price)
    product.sku = data.get('sku', product.sku)
    product.in_stock = data.get('in_stock', product.in_stock)
    product.stock_number = data.get('stock_number', product.stock_number)
    product.download_pdfs = ",".join(data.get('download_pdfs', product.download_pdfs.split(",") if product.download_pdfs else []))
    product.product_image_urls = ",".join(image_urls + data.get('product_image_urls', []))
    product.additional_media_urls = ",".join(data.get('additional_media_urls', product.additional_media_urls.split(",") if product.additional_media_urls else []))
    product.youtube_links = data.get('youtube_links', product.youtube_links)
    product.technical_information = data.get('technical_information', product.technical_information)
    product.manufacturer = data.get('manufacturer', product.manufacturer)
    product.special_note = data.get('special_note', product.special_note)
    product.whatsapp_number = data.get('whatsapp_number', product.whatsapp_number)
    product.is_rubber = data.get('is_rubber', product.is_rubber)
    product.rubber_density = data.get('rubber_density', product.rubber_density)
    product.rubber_height = data.get('rubber_height', product.rubber_height)
    product.rubber_length = data.get('rubber_length', product.rubber_length)
    product.rubber_thickness = data.get('rubber_thickness', product.rubber_thickness)
    product.rubber_description = data.get('rubber_description', product.rubber_description)
    product.show_in_store = data.get('show_in_store', product.show_in_store)
    
    existing_variant_ids = set(v.id for v in product.variants)
    submitted_variant_ids = set(v.get('id', 0) for v in data.get('variants', []) if v.get('id'))
    variants_to_delete = existing_variant_ids - submitted_variant_ids
    for vid in variants_to_delete:
        variant = Variant.query.get(vid)
        if variant:
            db.session.delete(variant)
    
    for variant_data in data.get('variants', []):
        if variant_data.get('variant_name') and variant_data.get('variant_price'):
            if variant_data.get('id'):
                variant = Variant.query.get(variant_data.get('id'))
                if variant:
                    variant.variant_name = variant_data.get('variant_name')
                    variant.variant_price = variant_data.get('variant_price')
            else:
                variant = Variant(
                    product_id=product.id,
                    variant_name=variant_data.get('variant_name'),
                    variant_price=variant_data.get('variant_price')
                )
                db.session.add(variant)
    
    db.session.commit()
    app.logger.debug(f"API: Updated product ID: {product_id}")
    return jsonify({"message": "Product updated"}), 200

@app.route('/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    app.logger.debug(f"API: Deleted product ID: {product_id}")
    return jsonify({"message": "Product deleted"}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').lower()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_results_pagination = Product.query.filter(
        Product.product_name.ilike(f'%{query}%') |
        Product.category.ilike(f'%{query}%') |
        Product.brand.ilike(f'%{query}%') |
        Product.short_description.ilike(f'%{query}%') |
        Product.long_description.ilike(f'%{query}%') |
        Product.detailed_description.ilike(f'%{query}%') |
        Product.rubber_description.ilike(f'%{query}%')
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