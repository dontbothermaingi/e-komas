from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import enum
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import JSONB
import uuid

db = SQLAlchemy()

class UserRoleEnum(enum.Enum):
    ADMIN = 'admin'
    CUSTOMER = 'customer'

class ProductEnum(enum.Enum):
    PHYSICAL = 'physical'
    DIGITAL = 'digital'
    SERVICE = 'service'

class OrderEnum(enum.Enum):
    PENDING = 'pending'
    PAID = 'paid'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'



class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), index=True, nullable=False, unique = True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRoleEnum), default=UserRoleEnum.ADMIN)
    created_at = db.Column(db.DateTime, nullable=False, default = db.func.current_timestamp())


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return{
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "role": self.role.value if self.role else None,
            "created_at":self.created_at.isoformat() if self.created_at else None
        }

class Product(db.Model):

    __tablename__ = 'products'

    id = db.Column(db.String(36), primary_key = True, nullable=False, unique=True, default = lambda: str(uuid.uuid4()))
    sku = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    base_price = db.Column(db.Numeric(15,2), nullable=False, default=0.0)
    type = db.Column(db.Enum(ProductEnum), default=ProductEnum.PHYSICAL)
    attributes = db.Column(JSONB)
    is_active = db.Column(db.Boolean, nullable=False, default = True)

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "title": self.title,
            "base_price": float(self.base_price),
            "type": self.type.value if self.type else None,
            "attributes": self.attributes,
            "is_active": self.is_active,
        }

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.String(36), primary_key = True, nullable=False, unique=True, default = lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    guest_email = db.Column(db.String(50), nullable = True)
    total_amount = db.Column(db.Numeric(15, 2), default = 0.0)
    status = db.Column(db.Enum(OrderEnum), default = OrderEnum.PENDING)
    payment_reference = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default = db.func.current_timestamp())

    user = db.relationship('User', backref='user', lazy=True)

    def to_dict(self):

        customer_name = f"{self.user.first_name} {self.user.last_name}" if self.user else "Guest"

        return{
            "id": self.id,
            "name": customer_name,
            "guest_email": self.guest_email,
            "total_amount": float(self.total_amount),
            "status": self.status.value if self.status else None,
            "payment_reference": self.payment_reference,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.String(36), primary_key = True, nullable=False, unique=True, default = lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"))
    product_id = db.Column(db.String(36), db.ForeignKey("products.id"))
    quantity = db.Column(db.Integer, nullable=False, default = 0)
    price_at_purchase = db.Column(db.Numeric(15, 2), nullable = False, default = 0.0)

    product = db.relationship('Product', backref = 'order_product', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "price_at_purchase": float(self.price_at_purchase),
            "product_name": self.product.title if self.product else None,
            "product_sku": self.product.sku if self.product else None,
            "product_type": self.product.type.value if self.product and self.product.type else None
        }

class Address(db.Model):

    __tablename__ = 'addresses'

    id = db.Column(db.String(36), primary_key = True, nullable=False, unique=True, default = lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable = True)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"))
    street = db.Column(db.String(255))
    city = db.Column(db.String(120))
    postal_code = db.Column(db.String(120))
    country = db.Column(db.String(120))

    def to_dict(self):
        return{
            "id":self.id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "street": self.street,
            "city": self.city,
            "postal_code": self.postal_code,
            "country": self.country
        }

class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "jti": self.jti,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# The association table for the many-to-many relationship
product_categories = db.Table('product_categories',
    db.Column('category_id', db.String(36), db.ForeignKey('categories.id'), primary_key=True),
    db.Column('product_id', db.String(36), db.ForeignKey('products.id'), primary_key=True)
)

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.String(36), primary_key=True, nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # The relationship to link back to the Product model
    products = db.relationship('Product', secondary=product_categories, lazy='subquery',
        backref=db.backref('categories', lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug
        }

class Cart(db.Model):
    __tablename__ = 'carts'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), unique=True, nullable=False) # One cart per user
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    items = db.relationship('CartItem', backref='cart', lazy='joined', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cart_id = db.Column(db.String(36), db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # We do NOT store price here. Price is always fetched fresh from the Product table to prevent staleness.

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity
        }

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_item_id = db.Column(db.String(36), db.ForeignKey('order_items.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
    # Status allows an admin to cancel or reschedule a specific booking 
    # without cancelling the entire financial order.
    status = db.Column(db.String(50), default='confirmed') 

    order_item = db.relationship('OrderItem', backref=db.backref('booking', uselist=False))

    def to_dict(self):
        return {
            "id": self.id,
            "order_item_id": self.order_item_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status
        }