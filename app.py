from models import db, User, TokenBlocklist, Cart, CartItem, Order, OrderItem, OrderEnum, Product, Booking, UserRoleEnum, ProductEnum
from flask import Flask
from datetime import timedelta, datetime
from flask_restful import Api, reqparse, Resource
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, jwt_required
import requests
import base64
import os

app = Flask(__name__)

# App Configuration
app.config['SECRET_KEY'] = 'your-super-secret-key-app'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/ecommerce_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT Configuration
app.config['JWT_SECRET_KEY'] = 'your-super-secret-jwt-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db.init_app(app)
api = Api(app)
jwt = JWTManager(app)

# This function runs automatically @jwt_required route is hit
# It checks whether the token is in the bloacklist
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload['jti']
    token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
    return token is not None

# JWT error response
@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return {"message":"The token has been revoked. Please log in again."}, 401

#Authentication Request Parsers
register_parser = reqparse.RequestParser()
register_parser.add_argument('first_name', type=str, required=True, help="First name is required.")
register_parser.add_argument('last_name', type=str, required=True, help="last name is required.")
register_parser.add_argument('email', type=str, required=True, help="Email is required")
register_parser.add_argument('password', type=str, required=True, help="Password is required")

login_parser = reqparse.RequestParser()
login_parser.add_argument('email', type=str, required=True, help="Email is required")
login_parser.add_argument('password', type=str, required=True, help="Password is required")



# Resources
class UserRegister(Resource):
    def post(self):
        data = register_parser.parse_args()

        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return {"message": "A user with that email already exists"}, 400

        # Create new user
        new_user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email']
        )
        new_user.set_password(data['password'])

        try:
            db.session.add(new_user)
            db.session.commit()
            return {"message": "User created successfully", "user": new_user.to_dict()}, 201
        except Exception as e:
            db.session.rollback()
            return {"message": "An error occurred creating the user.", "error": str(e)}, 500

api.add_resource(UserRegister, '/api/auth/register')

class UserLogin(Resource):
    def post(self):
        data = login_parser.parse_args()
        user = User.query.filter_by(email=data['email']).first()

        # Validate user and password
        if not user or not user.check_password(data['password']):
            return {"message": "Invalid email or password"}, 401

        # Generate the access token. 
        # We store the user's ID in the token's identity payload.
        access_token = create_access_token(identity=user.id)
        
        return {
            "message": "Login successful",
            "access_token": access_token,
            "user": user.to_dict()
        }, 200

api.add_resource(UserLogin, '/api/auth/login')

class UserLogout(Resource):
    @jwt_required() # This decorator ensures only users with a valid token can log out
    def post(self):
        # Extract the JTI (unique identifier) from the token
        jti = get_jwt()["jti"]
        
        # Add the JTI to the blocklist database
        revoked_token = TokenBlocklist(jti=jti)
        
        try:
            db.session.add(revoked_token)
            db.session.commit()
            return {"message": "Successfully logged out"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": "Could not log out", "error": str(e)}, 500

api.add_resource(UserLogout, '/api/auth/logout')

# Parser for creating/updating products
product_parser = reqparse.RequestParser()
product_parser.add_argument('sku', type=str, required=True, help="SKU is required")
product_parser.add_argument('title', type=str, required=True, help="Title is required")
product_parser.add_argument('base_price', type=float, required=True, help="Base price is required")
product_parser.add_argument('type', type=str, required=True, help="Product type (physical, digital, service)")
product_parser.add_argument('attributes', type=dict, required=False, default={})
product_parser.add_argument('is_active', type=bool, required=False, default=True)


# Parser for query string pagination
pagination_parser = reqparse.RequestParser()
pagination_parser.add_argument('page', type=int, default=1, location='args')
pagination_parser.add_argument('per_page', type=int, default=20, location='args')

class ProductListResource(Resource):
    def get(self):
        args = pagination_parser.parse_args()
        page = args['page']
        per_page = args['per_page']

        # Database-level pagination. error_out=False prevents crashing if a user asks for page 999
        paginated_products = Product.query.filter_by(is_active=True).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "products": [product.to_dict() for product in paginated_products.items],
            "meta": {
                "total_items": paginated_products.total,
                "total_pages": paginated_products.pages,
                "current_page": paginated_products.page,
                "per_page": paginated_products.per_page,
                "has_next": paginated_products.has_next,
                "has_prev": paginated_products.has_prev
            }
        }, 200

    @jwt_required()
    def post(self):
        # Admin route: Only store owners can create products
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRoleEnum.ADMIN:
            return {"message": "Admin privileges required"}, 403

        data = product_parser.parse_args()

        # Validate the Enum
        try:
            product_type = ProductEnum(data['type'].lower())
        except ValueError:
            return {"message": "Invalid product type. Must be physical, digital, or service"}, 400

        # Check for duplicate SKU
        if Product.query.filter_by(sku=data['sku']).first():
            return {"message": f"A product with SKU '{data['sku']}' already exists"}, 400

        new_product = Product(
            sku=data['sku'],
            title=data['title'],
            base_price=data['base_price'],
            type=product_type,
            attributes=data['attributes'],
            is_active=data['is_active']
        )

        try:
            db.session.add(new_product)
            db.session.commit()
            return {"message": "Product created successfully", "product": new_product.to_dict()}, 201
        except Exception as e:
            db.session.rollback()
            return {"message": "Failed to create product", "error": str(e)}, 500
        
api.add_resource(ProductListResource, '/api/products')

class ProductResource(Resource):
    def get(self, product_id):
        product = Product.query.fliter_by(id=product_id).first()

        if not product or not product.is_active:
            return {"message": "Product not found"}, 404
        return product.to_dict(), 200

    @jwt_required()
    def patch(self, product_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRoleEnum.ADMIN:
            return {"message": "Admin privileges required"}, 403

        product = Product.query.get(product_id)
        if not product:
            return {"message": "Product not found"}, 404

        data = product_parser.parse_args()

        try:
            product_type = ProductEnum(data['type'].lower())
        except ValueError:
            return {"message": "Invalid product type"}, 400

        # Update fields
        product.sku = data['sku']
        product.title = data['title']
        product.base_price = data['base_price']
        product.type = product_type
        product.attributes = data['attributes']
        product.is_active = data['is_active']

        try:
            db.session.commit()
            return {"message": "Product updated successfully", "product": product.to_dict()}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": "Failed to update product", "error": str(e)}, 500

    @jwt_required()
    def delete(self, product_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRoleEnum.ADMIN:
            return {"message": "Admin privileges required"}, 403

        product = Product.query.get(product_id)
        if not product:
            return {"message": "Product not found"}, 404

        product.is_active = False
        
        try:
            db.session.commit()
            return {"message": "Product removed from storefront"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": "Failed to delete product", "error": str(e)}, 500
        
api.add_resource(ProductResource, '/api/products/<string:product_id>')

# Cart Parser to accept an array of items from the Vite frontend
cart_sync_parser = reqparse.RequestParser()
cart_sync_parser.add_argument('items', type=dict, action='append', required=True, help="An array of cart items is required")

class CartSyncResource(Resource):
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        data = cart_sync_parser.parse_args()
        frontend_items = data['items']

        # Find or create the user's cart
        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.flush() # Get the cart ID without fully committing

        # Clear existing items to mirror the frontend's exact state
        CartItem.query.filter_by(cart_id=cart.id).delete()

        # Rebuild the cart items
        for item in frontend_items:
            # We don't trust the frontend price, only the product_id and quantity
            new_item = CartItem(
                cart_id=cart.id,
                product_id=item['product_id'],
                quantity=item['quantity']
            )
            db.session.add(new_item)

        try:
            db.session.commit()
            return {"message": "Cart synced successfully", "cart": cart.to_dict()}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": "Failed to sync cart", "error": str(e)}, 500

api.add_resource(CartSyncResource, '/api/cart/sync')

# Checkout Parsers
checkout_parser = reqparse.RequestParser()
checkout_parser.add_argument('items', type=dict, action='append', required=True)
checkout_parser.add_argument('guest_email', type=str, required=False)

class CheckoutResource(Resource):
    @jwt_required(optional=True) # Allows both logged-in users and guests
    def post(self):
        user_id = get_jwt_identity() # Will be None if it's a guest
        data = checkout_parser.parse_args()
        items = data['items']

        if not items:
            return {"message": "Cart is empty"}, 400

        # Initialize the order
        new_order = Order(
            user_id=user_id,
            guest_email=data.get('guest_email'),
            status=OrderEnum.PENDING,
            total_amount=0.0
        )
        db.session.add(new_order)
        db.session.flush() # Get the order ID

        calculated_total = 0.0

        for item in items:
            product = Product.query.get(item['product_id'])
            
            if not product or not product.is_active:
                db.session.rollback()
                return {"message": f"Product {item['product_id']} is unavailable"}, 400

            quantity = item['quantity']
            # Authoritative price check directly from the database
            line_total = float(product.base_price) * quantity
            calculated_total += line_total

            # Lock in the price at the moment of purchase
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=quantity,
                price_at_purchase=product.base_price
            )
            db.session.add(order_item)
            db.session.flush()

            # --- The Polymorphic Split ---
            # If the product is a service (e.g., a truck rental or freight booking), 
            # we require date parameters from the frontend and lock the calendar.
            if product.type.value == 'service':
                # You would normally validate these dates exist in the payload first
                start_time = datetime.fromisoformat(item['start_time'])
                end_time = datetime.fromisoformat(item['end_time'])
                
                new_booking = Booking(
                    order_item_id=order_item.id,
                    start_time=start_time,
                    end_time=end_time
                )
                db.session.add(new_booking)

        # Update the final order total
        new_order.total_amount = calculated_total

        try:
            db.session.commit()
            return {
                "message": "Order created, pending payment", 
                "order_id": new_order.id,
                "total_amount": calculated_total
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {"message": "Order processing failed", "error": str(e)}, 500

api.add_resource(CheckoutResource, '/api/checkout')



if __name__ == '__main__':
    app.run(debug=True, port=5000)