from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import enum
from werkzeug.security import generate_password_hash, check_password_hash
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

    id = db.Column(db.Integer, primary_key = True, nullable=False)
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
            "role": self.role,
            "created_at":self.created_at
        }

class Product(db.Model):

    __tablename__ = 'products'

    id = db.Column(db.String(36), primary_key = True, nullable=False, unique=True, default = lambda: str(uuid.uuid4()))
    sku = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    base_price = db.Column(db.NUmeric(15,2), nullable=False, default=0.0)
    type = db.Column(db.Enum(ProductEnum), default=ProductEnum.PHYSICAL)
    attributes = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, nullable=False, default = True)

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "title": self.title,
            "base_price": self.base_price,
            "type": self.type,
            "is_active": self.is_active,
        }

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.String(36), primary_key = True, nullable=False, unique=True, default = lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    guest_email = db.Column(db.String(50), nullable = True)
    total_amount = db.Column(db.Numeric(15, 2), default = 0.0)
    status = db.Column(db.Enum(OrderEnum), default = OrderEnum.PENDING)
    payment_refrence = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default = db.func.current_timestamp())

    user = db.relationship('User', backref='user', lazy=True)

    def to_dict(self):
        return{
            "id": self.id,
            "name": self.user.first_name + self.user.last_name,
            "guest_email": self.guest_email,
            "total_amount": self.total_amount,
            "status": self.status,
            "payment_reference": self.payment_refrence,
            "created_at": self.created_at
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
            "price_at_purchase": self.price_at_purchase,
            "product_name": self.product.title,
            "product_sku": self.product.sku,
            "product_type": self.product.type
        }

class Address(db.Model):

    __tablename__ = 'addresses'

    id = db.Column(db.String(36), primary_key = True, nullable=False, unique=True, default = lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable = True)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"))
    street = db.Column(db.String(255))
    city = db.Column(db.String(120))
    postal_code = db.Column(db.String(120))
    country = db.Column(db.Strings(120))

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



    



