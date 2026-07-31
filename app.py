import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.utils import secure_filename
from models import db, User, Product, CartItem, Order, OrderItem, Wishlist

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///abaya_store.db'
app.config['SECRET_KEY'] = 'change-this-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file_storage):
    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_file(file_storage.filename):
        flash('Invalid image type. Use PNG, JPG, or WEBP.', 'error')
        return None
    filename = secure_filename(file_storage.filename)
    unique_name = f"{os.urandom(8).hex()}_{filename}"
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file_storage.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
    return unique_name


def resolve_existing_image(filename_typed):
    """Used when the image file was manually copied into static/uploads
    already, and the admin just types the filename instead of re-uploading."""
    filename_typed = (filename_typed or '').strip()
    if not filename_typed:
        return None
    safe_name = secure_filename(filename_typed)
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    if not os.path.isfile(full_path):
        flash(f'No file named "{filename_typed}" found in static/uploads.', 'error')
        return None
    return safe_name


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('storefront'))
        return f(*args, **kwargs)
    return wrapper


# ==============================
# Authentication
# ==============================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('storefront'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash('That username is already taken.', 'error')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return redirect(url_for('signup'))

        user = User(username=username, email=email, role='Customer')
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('storefront'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('storefront'))

        flash('Invalid username or password.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    if request.method == 'POST':
        logout_user()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('login'))
    return render_template('logout.html')


# ==============================
# Storefront
# ==============================

@app.route('/')
def storefront():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    selected_colors = request.args.getlist('color')
    sort = request.args.get('sort', 'default')
    show = request.args.get('show', '15')

    base_query = Product.query.filter_by(is_active=True)

    # Color counts computed before other filters are applied (so counts stay stable)
    color_counts = {}
    for p in base_query.all():
        if p.color:
            color_counts[p.color] = color_counts.get(p.color, 0) + 1

    products_query = base_query

    if query:
        products_query = products_query.filter(Product.name.ilike(f'%{query}%'))
    if category:
        products_query = products_query.filter_by(category=category)
    if selected_colors:
        products_query = products_query.filter(Product.color.in_(selected_colors))

    if sort == 'price_asc':
        products_query = products_query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        products_query = products_query.order_by(Product.price.desc())
    elif sort == 'name':
        products_query = products_query.order_by(Product.name.asc())
    else:
        products_query = products_query.order_by(Product.created_at.desc())

    products = products_query.all()

    if show != 'all':
        try:
            products = products[:int(show)]
        except ValueError:
            pass

    categories = [c[0] for c in db.session.query(Product.category).distinct() if c[0]]

    wishlist_ids = set()
    if current_user.is_authenticated:
        wishlist_ids = {w.product_id for w in Wishlist.query.filter_by(user_id=current_user.id).all()}

    return render_template(
        'storefront.html',
        products=products,
        categories=categories,
        color_counts=color_counts,
        selected_colors=selected_colors,
        query=query,
        selected_category=category,
        sort=sort,
        show=show,
        wishlist_ids=wishlist_ids
    )


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)


# ==============================
# Wishlist
# ==============================

@app.route('/wishlist')
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id).all()
    return render_template('wishlist.html', items=items)


@app.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_wishlist(product_id):
    product = Product.query.get_or_404(product_id)
    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f'Removed "{product.name}" from your wishlist.', 'success')
    else:
        db.session.add(Wishlist(user_id=current_user.id, product_id=product_id))
        db.session.commit()
        flash(f'Added "{product.name}" to your wishlist.', 'success')

    return redirect(request.referrer or url_for('storefront'))


# ==============================
# Newsletter
# ==============================

@app.route('/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    email = request.form.get('email', '').strip()
    if email:
        flash('Thanks for subscribing to our newsletter!', 'success')
    else:
        flash('Please enter a valid email address.', 'error')
    return redirect(request.referrer or url_for('storefront'))


# ==============================
# Cart
# ==============================

@app.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.subtotal for item in items)
    return render_template('cart.html', items=items, total=total)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    size = request.form.get('size', '').strip()
    quantity = max(1, int(request.form.get('quantity', 1)))

    if product.stock < quantity:
        flash('Not enough stock available.', 'error')
        return redirect(url_for('product_detail', product_id=product_id))

    existing = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id, size=size
    ).first()

    if existing:
        existing.quantity += quantity
    else:
        db.session.add(CartItem(
            user_id=current_user.id,
            product_id=product_id,
            size=size,
            quantity=quantity
        ))

    db.session.commit()
    flash(f'Added "{product.name}" to your cart.', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart_item(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)

    quantity = int(request.form.get('quantity', 1))
    if quantity < 1:
        db.session.delete(item)
    else:
        item.quantity = quantity

    db.session.commit()
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from cart.', 'success')
    return redirect(url_for('cart'))


# ==============================
# Checkout
# ==============================

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not items:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('storefront'))

    if request.method == 'POST':
        address = request.form['address'].strip()
        phone = request.form['phone'].strip()

        # Validate stock before committing the order
        for item in items:
            if item.product.stock < item.quantity:
                flash(f'"{item.product.name}" no longer has enough stock.', 'error')
                return redirect(url_for('cart'))

        order = Order(
            user_id=current_user.id,
            shipping_address=address,
            shipping_phone=phone,
            payment_method='Cash on Delivery',
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        total = 0
        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product.name,
                size=item.size,
                quantity=item.quantity,
                price_at_purchase=item.product.price
            )
            item.product.stock -= item.quantity
            total += order_item.subtotal
            db.session.add(order_item)
            db.session.delete(item)

        order.total_amount = total
        db.session.commit()

        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_detail', order_id=order.id))

    total = sum(item.subtotal for item in items)
    return render_template('checkout.html', items=items, total=total)


# ==============================
# Customer Orders
# ==============================

@app.route('/orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('my_orders.html', orders=orders)


@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template('order_detail.html', order=order)


# ==============================
# Admin: Dashboard
# ==============================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    low_stock = Product.query.filter(Product.stock <= 3).count()
    total_customers = User.query.filter_by(role='Customer').count()

    return render_template(
        'admin_dashboard.html',
        total_products=total_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        low_stock=low_stock,
        total_customers=total_customers
    )


# ==============================
# Admin: Products
# ==============================

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    query = request.args.get('q', '').strip()
    products_query = Product.query
    if query:
        products_query = products_query.filter(Product.name.ilike(f'%{query}%'))
    products = products_query.order_by(Product.created_at.desc()).all()
    return render_template('admin_products.html', products=products, query=query)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        image_filename = save_product_image(request.files.get('image'))
        if not image_filename:
            image_filename = resolve_existing_image(request.form.get('image_filename_manual'))

        product = Product(
            name=request.form['name'].strip(),
            description=request.form.get('description', '').strip(),
            price=float(request.form['price']),
            category=request.form.get('category', '').strip(),
            fabric=request.form.get('fabric', '').strip(),
            color=request.form.get('color', '').strip(),
            sizes=request.form.get('sizes', '').strip(),
            stock=int(request.form.get('stock', 0)),
            image_filename=image_filename,
            is_active=True,
            is_new_arrival='is_new_arrival' in request.form
        )

        db.session.add(product)
        db.session.commit()

        flash(f'Product "{product.name}" added.', 'success')
        return redirect(url_for('admin_products'))

    return render_template('add_product.html')


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        new_image = save_product_image(request.files.get('image'))
        if not new_image:
            new_image = resolve_existing_image(request.form.get('image_filename_manual'))
        if new_image:
            product.image_filename = new_image

        product.name = request.form['name'].strip()
        product.description = request.form.get('description', '').strip()
        product.price = float(request.form['price'])
        product.category = request.form.get('category', '').strip()
        product.fabric = request.form.get('fabric', '').strip()
        product.color = request.form.get('color', '').strip()
        product.sizes = request.form.get('sizes', '').strip()
        product.stock = int(request.form.get('stock', 0))
        product.is_active = 'is_active' in request.form
        product.is_new_arrival = 'is_new_arrival' in request.form

        db.session.commit()

        flash('Product updated successfully.', 'success')
        return redirect(url_for('admin_products'))

    return render_template('add_product.html', product=product)


@app.route('/admin/products/delete/<int:product_id>')
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    has_orders = OrderItem.query.filter_by(product_id=product.id).first() is not None

    if has_orders:
        # Preserve order history: deactivate rather than hard-delete
        product.is_active = False
        db.session.commit()
        flash('Product has past orders, so it was deactivated instead of deleted.', 'success')
    else:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted.', 'success')

    return redirect(url_for('admin_products'))


# ==============================
# Admin: Orders
# ==============================

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    status_filter = request.args.get('status', '').strip()
    orders_query = Order.query
    if status_filter:
        orders_query = orders_query.filter_by(status=status_filter)
    orders = orders_query.order_by(Order.order_date.desc()).all()
    return render_template('admin_orders.html', orders=orders, status_filter=status_filter)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    valid_statuses = ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled']
    if new_status in valid_statuses:
        order.status = new_status
        db.session.commit()
        flash(f'Order #{order.id} marked as {new_status}.', 'success')
    else:
        flash('Invalid status.', 'error')

    return redirect(url_for('admin_orders'))


# ==============================
# Run Application
# ==============================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Seed a default admin account if none exists yet
        if not User.query.filter_by(role='Admin').first():
            admin = User(username='admin', email='admin@abayastore.local', role='Admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Seeded default admin -> username: admin / password: admin123 (change this!)")

    app.run(debug=True)
