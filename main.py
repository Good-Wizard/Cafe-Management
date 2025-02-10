from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    abort,
)
from flask_sqlalchemy import SQLAlchemy

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, date, timedelta
import random
import re
from functools import wraps


app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cafe.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship("Order", backref="user", lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    in_stock = db.Column(db.Boolean, default=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    items = db.relationship("OrderItem", backref="order", lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship("Product", lazy=True)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    product = db.relationship("Product", lazy=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Basic routes
@app.route("/")
def home():
    products = Product.query.all()
    return render_template("home.html", products=products)


def generate_verification_code():
    return str(random.randint(100000, 999999))


def is_valid_phone(phone):
    # Basic phone validation - can be adjusted based on your country's format
    pattern = re.compile(r"^\+?1?\d{9,15}$")
    return bool(pattern.match(phone))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        phone = request.form.get("phone")

        if not is_valid_phone(phone):
            return jsonify({"error": "Invalid phone number format"}), 400

        if User.query.filter_by(phone_number=phone).first():
            return jsonify({"error": "Phone number already registered"}), 400

        # Generate and store verification code
        verification_code = generate_verification_code()
        session["verification_code"] = verification_code
        session["phone_pending"] = phone

        # TODO: Integrate with SMS service to send verification code
        # For development, just print the code
        print(f"Verification code: {verification_code}")

        return jsonify({"message": "Verification code sent"})

    return render_template("register.html")


@app.route("/verify", methods=["POST"])
def verify():
    code = request.form.get("code")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    password = request.form.get("password")

    if not all([code, first_name, last_name, password]):
        return jsonify({"error": "All fields are required"}), 400

    if code != session.get("verification_code"):
        return jsonify({"error": "Invalid verification code"}), 400

    # Create new user
    new_user = User(
        phone_number=session["phone_pending"],
        first_name=first_name,
        last_name=last_name,
        password_hash=generate_password_hash(password),
    )

    db.session.add(new_user)
    db.session.commit()

    # Clean up session
    session.pop("verification_code", None)
    session.pop("phone_pending", None)

    return jsonify({"message": "Registration successful"})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone")
        password = request.form.get("password")

        user = User.query.filter_by(phone_number=phone).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid phone number or password"}), 401

        login_user(user)
        return jsonify({"message": "Login successful"})

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/cart")
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not product_id:
        return jsonify({"error": "Product ID is required"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Check if item already in cart
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id, product_id=product_id, quantity=quantity
        )
        db.session.add(cart_item)

    db.session.commit()
    return jsonify({"message": "Product added to cart"})


@app.route("/cart/update", methods=["POST"])
@login_required
def update_cart():
    data = request.get_json()
    item_id = data.get("item_id")
    quantity = data.get("quantity", 0)

    cart_item = CartItem.query.get(item_id)
    if not cart_item or cart_item.user_id != current_user.id:
        return jsonify({"error": "Item not found"}), 404

    if quantity > 0:
        cart_item.quantity = quantity
    else:
        db.session.delete(cart_item)

    db.session.commit()
    return jsonify({"message": "Cart updated"})


@app.route("/cart/clear", methods=["POST"])
@login_required
def clear_cart():
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"message": "Cart cleared"})


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        return redirect(url_for("cart"))

    if request.method == "POST":
        # Calculate total
        total_price = sum(item.product.price * item.quantity for item in cart_items)

        try:
            # Create order
            order = Order(
                user_id=current_user.id,
                date=datetime.utcnow(),
                total_price=total_price,
                status="pending",
            )
            db.session.add(order)
            # Flush to get the order ID
            db.session.flush()

            # Create order items
            for cart_item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,  # Now we have the order.id
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                )
                db.session.add(order_item)

            # Clear cart
            CartItem.query.filter_by(user_id=current_user.id).delete()

            # Commit all changes
            db.session.commit()
            return redirect(url_for("order_confirmation", order_id=order.id))

        except Exception as e:
            db.session.rollback()
            print(f"Error during checkout: {str(e)}")
            return render_template(
                "checkout.html",
                cart_items=cart_items,
                total=total_price,
                error="An error occurred during checkout. Please try again.",
            )

    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template("checkout.html", cart_items=cart_items, total=total)


@app.route("/order/confirmation/<int:order_id>")
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template("order_confirmation.html", order=order)


# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route("/admin/products")
@login_required
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template("admin/products.html", products=products)


@app.route("/admin/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_product():
    if request.method == "POST":
        product = Product(
            name=request.form.get("name"),
            description=request.form.get("description"),
            price=float(request.form.get("price")),
            category=request.form.get("category"),
        )
        db.session.add(product)
        db.session.commit()
        return redirect(url_for("admin_products"))

    return render_template("admin/add_product.html")


@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.date.desc()).all()
    return render_template("admin/orders.html", orders=orders)


@app.route("/admin/orders/pending")
@login_required
@admin_required
def admin_pending_orders():
    orders = Order.query.filter_by(status="pending").order_by(Order.date.desc()).all()
    return render_template("admin/orders.html", orders=orders, pending_only=True)


@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template("admin/users.html", users=users)


@app.route("/admin/reports/sales")
@login_required
@admin_required
def admin_sales_report():
    # Get sales data for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    orders = Order.query.filter(Order.date >= thirty_days_ago).all()

    # Prepare data for the sales chart
    dates = []
    daily_sales = []
    current_date = thirty_days_ago.date()
    end_date = datetime.utcnow().date()

    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        day_sales = sum(
            order.total_price for order in orders if order.date.date() == current_date
        )
        daily_sales.append(day_sales)
        current_date += timedelta(days=1)

    # Calculate top selling products
    product_sales = {}
    for order in orders:
        for item in order.items:
            if item.product_id not in product_sales:
                product_sales[item.product_id] = {
                    "name": item.product.name,
                    "units_sold": 0,
                    "revenue": 0,
                }
            product_sales[item.product_id]["units_sold"] += item.quantity
            product_sales[item.product_id]["revenue"] += item.price * item.quantity

    top_products = sorted(
        product_sales.values(), key=lambda x: x["revenue"], reverse=True
    )[
        :5
    ]  # Top 5 products

    return render_template(
        "admin/sales_report.html",
        orders=orders,
        dates=dates,
        daily_sales=daily_sales,
        top_products=top_products,
    )


@app.route("/admin/reports/revenue")
@login_required
@admin_required
def admin_revenue_report():
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    year_ago = today - timedelta(days=365)

    # Calculate revenue for different time periods
    today_revenue = (
        db.session.query(db.func.sum(Order.total_price))
        .filter(db.func.date(Order.date) == today)
        .scalar()
        or 0
    )

    week_revenue = (
        db.session.query(db.func.sum(Order.total_price))
        .filter(Order.date >= week_ago)
        .scalar()
        or 0
    )

    month_revenue = (
        db.session.query(db.func.sum(Order.total_price))
        .filter(Order.date >= month_ago)
        .scalar()
        or 0
    )

    year_revenue = (
        db.session.query(db.func.sum(Order.total_price))
        .filter(Order.date >= year_ago)
        .scalar()
        or 0
    )

    # Monthly revenue data
    months = []
    monthly_revenue = []
    current_date = year_ago
    while current_date <= today:
        month_start = current_date.replace(day=1)
        if current_date.month == 12:
            month_end = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            month_end = current_date.replace(month=current_date.month + 1, day=1)

        revenue = (
            db.session.query(db.func.sum(Order.total_price))
            .filter(Order.date >= month_start, Order.date < month_end)
            .scalar()
            or 0
        )

        months.append(current_date.strftime("%B %Y"))
        monthly_revenue.append(revenue)

        current_date = month_end

    # Revenue by category
    categories = ["coffee", "tea", "dessert"]
    category_revenue = []

    for category in categories:
        revenue = (
            db.session.query(db.func.sum(Order.total_price))
            .join(OrderItem)
            .join(Product)
            .filter(Product.category == category)
            .scalar()
            or 0
        )
        category_revenue.append(revenue)

    return render_template(
        "admin/revenue_report.html",
        today_revenue=today_revenue,
        week_revenue=week_revenue,
        month_revenue=month_revenue,
        year_revenue=year_revenue,
        months=months,
        monthly_revenue=monthly_revenue,
        categories=categories,
        category_revenue=category_revenue,
    )


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    # Calculate statistics
    stats = {
        "total_orders": Order.query.count(),
        "today_revenue": Order.query.filter(Order.date >= date.today())
        .with_entities(db.func.sum(Order.total_price))
        .scalar()
        or 0,
        "total_products": Product.query.count(),
        "total_users": User.query.count(),
    }
    return render_template("admin/dashboard.html", stats=stats)


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":

        product.name = request.form.get("name")
        product.description = request.form.get("description")
        product.price = float(request.form.get("price"))
        product.category = request.form.get("category")

        db.session.commit()
        return redirect(url_for("admin_products"))

    return render_template("admin/edit_product.html", product=product)


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"})


@app.route("/dashboard")
@login_required
def user_dashboard():
    # Get user's orders, sorted by date descending
    orders = (
        Order.query.filter_by(user_id=current_user.id).order_by(Order.date.desc()).all()
    )

    # Get active orders (pending, preparing, ready)
    active_orders = [
        order for order in orders if order.status in ["pending", "preparing", "ready"]
    ]

    return render_template(
        "user/dashboard.html", orders=orders, active_orders=active_orders
    )


@app.route("/dashboard/change-password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    if not check_password_hash(current_user.password_hash, current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    if new_password != confirm_password:
        return jsonify({"error": "New passwords do not match"}), 400

    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"message": "Password updated successfully"})


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@login_required
@admin_required
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get("status")

    if not new_status:
        return jsonify({"error": "Status is required"}), 400

    order = Order.query.get_or_404(order_id)
    order.status = new_status
    db.session.commit()

    return jsonify({"message": "Order status updated successfully"})


@app.route("/admin/orders/<int:order_id>/details")
@login_required
@admin_required
def get_order_details(order_id):
    order = Order.query.get_or_404(order_id)

    # Prepare HTML for the modal
    html = render_template("admin/order_details.html", order=order)
    return jsonify({"html": html})


@app.route("/admin/orders/<int:order_id>/receipt")
@login_required
@admin_required
def order_receipt(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin/receipt.html", order=order)


@app.route("/admin/products/<int:product_id>/stock", methods=["POST"])
@login_required
@admin_required
def toggle_product_stock(product_id):
    data = request.get_json()
    in_stock = data.get("in_stock")

    if in_stock is None:
        return jsonify({"error": "Stock status is required"}), 400

    product = Product.query.get_or_404(product_id)
    product.in_stock = in_stock
    db.session.commit()

    return jsonify({"message": "Stock status updated successfully"})


def create_admin_user(phone, password, first_name, last_name):
    with app.app_context():  # Essential!
        existing_user = User.query.filter_by(phone_number=phone).first()
        if existing_user:
            print("Phone number already registered")
            return

        hashed_password = generate_password_hash(password)
        admin = User(
            phone_number=phone,
            first_name=first_name,
            last_name=last_name,
            password_hash=hashed_password,
            is_admin=True,
        )

        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")

phone = ""
password = ""
first_name = ""
last_name = ""


if __name__ == "__main__":

    # Create the database tables (do this ONCE when you set up your database)
    with app.app_context():
        db.create_all()  # Only needed the first time

    create_admin_user(phone, password, first_name, last_name)

    app.run(debug=True)
