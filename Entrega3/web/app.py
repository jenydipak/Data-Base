#!/usr/bin/python3
from logging.config import dictConfig

import psycopg
from flask import flash
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool


# postgres://{user}:{password}@{hostname}:{port}/{database-name}
DATABASE_URL = "postgres://db:db@postgres/db"


pool = ConnectionPool(conninfo=DATABASE_URL)
# the pool starts connecting immediately.

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

app = Flask(__name__)
log = app.logger

@app.route('/')
def index():
  try:
    return render_template("index.html", params=request.args)
  except Exception as e:
    return str(e)


@app.route("/products", methods=("GET",))
def product_index():
    """Show all the products, cheapest first."""

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            products = cur.execute(
                """
                SELECT name, SKU, description, price, ean
                FROM product
                ORDER BY price ASC;
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    # API-like response is returned to clients that request JSON explicitly (e.g., fetch)
    if (
        request.accept_mimetypes["application/json"]
        and not request.accept_mimetypes["text/html"]
    ):
        return jsonify(products)

    return render_template("product.html", products=products)

@app.route("/suppliers", methods=("GET",))
def supplier_index():
    """Show all the suppliers, first the most recents."""

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            suppliers = cur.execute(
                """
                SELECT TIN, supplier.name, supplier.address, SKU, date
                FROM supplier
                ORDER BY date DESC;
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    # API-like response is returned to clients that request JSON explicitly (e.g., fetch)
    if (
        request.accept_mimetypes["application/json"]
        and not request.accept_mimetypes["text/html"]
    ):
        return jsonify(suppliers)

    return render_template("supplier.html", suppliers=suppliers)

@app.route("/clients", methods=("GET",))
def client_index():
    """Show all the clients, first the most recents."""

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            clients = cur.execute(
                """
                SELECT cust_no, customer.name, email, phone, customer.address
                FROM customer
                ORDER BY cust_no DESC;
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    # API-like response is returned to clients that request JSON explicitly (e.g., fetch)
    if (
        request.accept_mimetypes["application/json"]
        and not request.accept_mimetypes["text/html"]
    ):
        return jsonify(clients)

    return render_template("client.html", clients=clients)

@app.route("/orders/<order_no>/<cust_no>/insert_pay")
def insert_pay(order_no, cust_no):
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                INSERT INTO pay VALUES(%(order_no)s, %(cust_no)s);
                """,
                {"order_no": order_no, "cust_no": cust_no}
            )
        conn.commit()
        return redirect(url_for("index"))

@app.route("/list_products", methods=("POST","GET"))
def insert_order():
    """Insert a order."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cust_no = request.args.get('cust_no')
            order_no = request.args.get('order_no')
            date = request.args.get('date')
            cur.execute(
                """
                INSERT INTO orders VALUES(%(order_no)s, %(cust_no)s, %(date)s);
                """,
                {"order_no": order_no, "cust_no": cust_no, "date": date}
            )
        conn.commit()
        return redirect(url_for("order_index", order_no = order_no, cust_no = cust_no, date = date))

@app.route("/list_products/<order_no>/<cust_no>/<date>", methods=("POST","GET"))
def order_index(order_no, cust_no, date):
    """Show all the products available to order."""

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            orders = cur.execute(
                """
                SELECT name, SKU, description, price, ean
                FROM product
                ORDER BY price ASC;
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")
    # API-like response is returned to clients that request JSON explicitly (e.g., fetch)
    if (
        request.accept_mimetypes["application/json"]
        and not request.accept_mimetypes["text/html"]
    ):
        return jsonify(orders)

    return render_template("make_order.html", orders=orders, order_no=order_no, cust_no = cust_no, date = date)

@app.route("/client/execute_insert", methods=("POST",))
def insert_client_into_db():
    """Insert the client."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cust_no = request.form['cust_no']
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            address = request.form['address']
            cur.execute(
                """
                INSERT INTO customer VALUES(%(cust_no)s, %(name)s, %(email)s, %(phone)s, %(address)s);
                """,
                {"cust_no": cust_no, "name": name, "email": email, "phone": phone, "address": address}
            )
        conn.commit()
    return redirect(url_for("client_index"))

@app.route('/client/insert_client')
def insert_client():
  try:
    return render_template("insert_client.html", params=request.args)
  except Exception as e:
    return str(e)
    
@app.route("/supplier/execute_insert", methods=("POST",))
def insert_supplier_into_db():
    """Insert the supplier."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            TIN = request.form['TIN']
            name = request.form['name']
            address = request.form['address']
            SKU = request.form['SKU']
            date = request.form['date']
            cur.execute(
                """
                INSERT INTO supplier VALUES(%(TIN)s, %(name)s, %(address)s, %(SKU)s, %(date)s);
                """,
                {"TIN": TIN, "name": name, "address": address, "SKU": SKU, "date": date}
            )
        conn.commit()
    return redirect(url_for("supplier_index"))

@app.route('/supplier/insert_supplier')
def insert_supplier():
  try:
    return render_template("insert_supplier.html", params=request.args)
  except Exception as e:
    return str(e)

@app.route("/product/execute_insert", methods=("POST",))
def insert_product_into_db():
    """Insert the product."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            SKU = request.form['SKU']
            name = request.form['name']
            description = request.form['description']
            price = request.form['price']
            ean = request.form['ean']
            cur.execute(
                """
                INSERT INTO product VALUES(%(SKU)s, %(name)s, %(description)s, %(price)s, %(ean)s);
                """,
                {"SKU": SKU, "name": name, "description": description, "price": price, "ean": ean}
            )
        conn.commit()
    return redirect(url_for("product_index"))

@app.route('/product/insert_product')
def insert_product():
  try:
    return render_template("insert_product.html", params=request.args)
  except Exception as e:
    return str(e)

@app.route("/remove_product/<SKU>")
def product_delete(SKU):
    """Delete the product."""
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE 
                FROM contains 
                WHERE sku=%(SKU)s;
                """,
                {"SKU": SKU},
                )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM process 
                WHERE order_no NOT IN 
                ( SELECT order_no FROM orders JOIN contains USING (order_no));
                """
                )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM pay  
                WHERE order_no NOT IN 
                ( SELECT order_no FROM orders JOIN contains USING (order_no));
                """
                )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM orders
                WHERE order_no NOT IN 
                ( SELECT order_no FROM orders JOIN contains USING (order_no));
                """
                )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE 
                FROM delivery d USING supplier
                WHERE d.tin IN
                (SELECT tin FROM supplier WHERE SKU=%(SKU)s); 
                """,
                {"SKU": SKU},
                )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM supplier
                WHERE SKU=%(SKU)s;
                """,
                {"SKU": SKU},
                )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE  FROM product
                WHERE SKU=%(SKU)s;
                """,
                {"SKU": SKU},
            )
        conn.commit()
    return redirect(url_for("product_index"))

@app.route("/remove_supplier/<TIN>")
def supplier_delete(TIN):
    """Delete the supplier."""

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM delivery
                WHERE tin=%(TIN)s;
                """,
                {"TIN": TIN},
            )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM supplier
                WHERE tin=%(TIN)s;
                """,
                {"TIN": TIN},
            )
        conn.commit()
    return redirect(url_for("supplier_index"))

@app.route("/remove_client/<cust_no>")
def client_delete(cust_no):
    """Delete the client."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE  
                FROM contains c USING orders 
                WHERE c.order_no IN (SELECT order_no FROM orders WHERE cust_no=%(cust_no)s);
                """,
                {"cust_no": cust_no},
            )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE
                FROM process p USING orders
                WHERE p.order_no IN (SELECT order_no FROM orders WHERE cust_no=%(cust_no)s);
                """,
                {"cust_no": cust_no},
            )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM pay
                WHERE cust_no=%(cust_no)s;

                """,
                {"cust_no": cust_no},
            )
        conn.commit()
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM orders  
                WHERE cust_no=%(cust_no)s;
                """,
                {"cust_no": cust_no},
            )
        conn.commit()    
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM customer 
                WHERE cust_no=%(cust_no)s;
                """,
                {"cust_no": cust_no},
            )
        conn.commit()    
    return redirect(url_for("client_index"))
 
@app.route('/orders/<order_no>/<cust_no>/payment_method')
def payment_method(order_no, cust_no):
  try:
    return render_template("payment_method.html", params=request.args, order_no = order_no, cust_no= cust_no)
  except Exception as e:
    return str(e)

@app.route('/orders/<order_no>/<cust_no>/execute_payment')
def final_payment(order_no, cust_no):
    try:
        payment_method = request.args.get('payment')
        if payment_method=='card':
            return render_template("card_payment.html",params=request.args, order_no=order_no, cust_no=cust_no)
        elif payment_method=='paypal':
            return render_template("paypal_payment.html",params=request.args, order_no=order_no, cust_no=cust_no)
        elif payment_method=='mbway':
            return render_template("mbway_payment.html",params=request.args, order_no=order_no, cust_no=cust_no)
    except Exception as e:
        return str(e)
 
@app.route("/orders", methods=("GET",))  
def start_order():
    """Choose the order number and client number"""
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            orders = cur.execute(
                """
                SELECT order_no, cust_no, date
                FROM orders
                ORDER BY order_no ASC;
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")
    # API-like response is returned to clients that request JSON explicitly (e.g., fetch)
    if (
        request.accept_mimetypes["application/json"]
        and not request.accept_mimetypes["text/html"]
    ):
        return jsonify(orders)

    return render_template("start_order.html", orders=orders, params=request.args)
 
@app.route('/orders/<SKU>/<order_no>/<cust_no>/<date>')
def choose_quantity(SKU,order_no,cust_no,date):
    """Direct to page to choose product quantity"""
    try:
        return render_template("choose_quantity.html", params=request.args, order_no=order_no, SKU=SKU, cust_no = cust_no, date = date)
    except Exception as e:
        return str(e)

@app.route("/orders/<SKU>/<order_no>/<cust_no>/<date>/update_quantity", methods=("POST",))
def orders_update_quantity(SKU, order_no, cust_no, date):
    """Update the product quantity in order."""
    quantity = int(request.form.get('quantity'))
    error = None
    if not quantity:
        error = "Quantity is required."
        if not quantity.isnumeric():
            error = "Quantity is required to be numeric."

    if error is not None:
        flash(error)
    else:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    INSERT INTO contains VALUES(%(order_no)s,%(SKU)s,%(quantity)s);
                    """,
                    {"order_no": order_no, "SKU": SKU, "quantity": quantity},
                )
            conn.commit()
    return redirect(url_for("order_index", order_no = order_no, cust_no = cust_no, date =date))

@app.route("/products/<SKU>/update_product_price", methods=("GET", "POST"))
def product_price_update(SKU):
    """Update the product price."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            product = cur.execute(
                """
                SELECT name, SKU, description, price, ean
                FROM product
                WHERE SKU = %(SKU)s;
                """,
                {"SKU": SKU},
            ).fetchone()
            log.debug(f"Found {cur.rowcount} rows.")

    if request.method == "POST":
        price = request.form["price"]

        error = None

        if not price:
            error = "Price is required."
            if not price.isnumeric():
                error = "Price is required to be numeric."

        if error is not None:
            flash(error)
        else:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        UPDATE product
                        SET price = %(price)s
                        WHERE SKU = %(SKU)s;
                        """,
                        {"SKU": SKU, "price": price},
                    )
                conn.commit()
            return redirect(url_for("product_index"))

    return render_template("update_product_price.html", product=product)

@app.route("/products/<SKU>/update_product_description", methods=("GET", "POST"))
def product_description_update(SKU):
    """Update the product description."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            product = cur.execute(
                """
                SELECT name, SKU, description, price, ean
                FROM product
                WHERE SKU = %(SKU)s;
                """,
                {"SKU": SKU},
            ).fetchone()
            log.debug(f"Found {cur.rowcount} rows.")

    if request.method == "POST":
        description = request.form["description"]

        error = None

        if not description:
            error = "descrption is required."
            if not isinstance(description,str):
                error = "Description is required to be text."

        if error is not None:
            flash(error)
        else:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        UPDATE product
                        SET description = %(description)s
                        WHERE SKU = %(SKU)s;
                        """,
                        {"SKU": SKU, "description": description},
                    )
                conn.commit()
            return redirect(url_for("product_index"))

    return render_template("update_product_description.html", product=product)


@app.route("/ping", methods=("GET",))
def ping():
    log.debug("ping!")
    return jsonify({"message": "pong!", "status": "success"})

if __name__ == "__main__":
    app.run()
