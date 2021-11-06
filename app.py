from flask import Flask, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_uploads import UploadSet, configure_uploads, IMAGES
import random

app = Flask(__name__)

photos = UploadSet('photos', IMAGES)

app.config['UPLOADED_PHOTOS_DEST'] = 'images'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Number39:Utopia@localhost/backpack'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'supernicebackpacks'

configure_uploads(app, photos)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

from forms import AddBackpack, AddToCart, Checkout
from models.product import Product, Order, OrderItems

def handle_cart():
    products = []
    grand_total = 0
    quantity_total = 0
    if 'cart' not in session:
        session['cart'] = []

    for index, item in enumerate(session['cart']):
        product = Product.query.filter_by(id=item['id']).first()
        quantity = item['quantity']
        total = quantity * product.price
        grand_total += total
        quantity_total += quantity
        products.append({'id': product.id, 'name': product.name, 'price': product.price, 'image':product.image, 'quantity': quantity, 'total': total, 'index': index})
    
    grand_total_plus_shipping = grand_total + 10
    return products, grand_total, grand_total_plus_shipping, quantity_total

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/product/<id>')
def product(id):
    product = Product.query.filter_by(id=id).first()
    form = AddToCart()
    return render_template('view-product.html', product=product, form=form)

@app.route('/quick-add/<id>', methods=['GET', 'POST'])
def quick_add(id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append({'id': id, 'quantity': 1})
    session.modified = True
    return redirect(url_for('index'))

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'cart' not in session:
        session['cart'] = []

    form = AddToCart()
    if form.validate_on_submit():

        session['cart'].append({'id': form.id.data, 'quantity': form.quantity.data})
        session.modified = True

    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    products, grand_total, grand_total_plus_shipping, quantity_total = handle_cart()

    return render_template('cart.html', products=products, grand_total=grand_total, grand_total_plus_shipping=grand_total_plus_shipping)

@app.route('/remove-from-cart/<index>', methods=['GET','POST'])
def remove_from_cart(index):
    del session['cart'][int(index)]
    session.modified = True
    print(session)
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    form = Checkout()
    products, grand_total, grand_total_plus_shipping, quantity_total = handle_cart()
    if form.validate_on_submit():
        order = Order(
            reference = ''.join([random.choice('ABCDE') for a in  range(5)]),
            status = 'PENDING',
            first_name = form.first_name.data,
            last_name = form.last_name.data,
            phone_number = form.phone_number.data,
            email = form.email.data,
            address = form.address.data,
            city = form.city.data,
            state = form.state.data,
            country = form.country.data,
            payment_type = form.payment_type.data,
            order_total = grand_total_plus_shipping
        )
        for product in products:
            order_item = OrderItems(quantity=product['quantity'], product_id=product['id'])
            order.items.append(order_item)
            product = Product.query.filter_by(id=product['id']).update({'stock' : Product.stock - product['quantity']})

        db.session.add(order)
        db.session.commit()
        session['cart'] = []
        session.modified = True

        return redirect(url_for('index'))

    return render_template('checkout.html', form=form)

@app.route('/admin')
def admin():
    products = Product.query.all()
    products_in_stock = Product.query.filter(Product.stock > 0).count()
    orders = Order.query.all()
    return render_template('admin/index.html', admin=True, products=products, products_in_stock=products_in_stock, orders=orders)

@app.route('/admin/add', methods=['GET', 'POST'])
def add():
    form = AddBackpack()
    if form.validate_on_submit():
        image_url = photos.url(photos.save(form.image.data))
        new_backpack = Product(name=form.name.data, price=form.price.data, stock=form.stock.data, description=form.description.data, image=image_url)
        new_backpack.save_to_db()
        return redirect(url_for('admin'))
    return render_template('admin/add-product.html', admin=True, form=form)

@app.route('/admin/order/<id>')
def order(id):
    order = Order.query.filter_by(id=int(id)).first()

    return render_template('admin/view-order.html', admin=True, order=order)

if __name__ == '__main__':
    manager.run()