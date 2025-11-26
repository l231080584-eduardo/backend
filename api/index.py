from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
from dotenv import load_dotenv
import hashlib
from functools import wraps
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.secret_key = "110512"

# ================================
#   SOLO UNA VARIABLE PARA RAILWAY
# ================================
DATABASE_URL = os.getenv("DATABASE_URL")


# ----------------------------------------
#   Función de conexión
# ----------------------------------------
def get_conn():
    """Establece y devuelve una conexión a la base de datos PostgreSQL."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        raise e


def login_required(f):
    """Decorador para asegurar que una ruta solo sea accesible si el usuario ha iniciado sesión."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "loggedin" not in session:
            flash("Debes iniciar sesión primero.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# LOGIN (Ruta principal "/")
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"]
        password = request.form["contraseña"]

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT id_clientes, nombre FROM clientes WHERE correo = %s AND contraseña = %s",
                (correo, hashed_password)
            )
            cliente = cur.fetchone()
        finally:
            if cur: cur.close()
            if conn: conn.close()

        if cliente:
            session["loggedin"] = True
            session["id_cliente"] = cliente["id_clientes"]
            session["nombre_cliente"] = cliente["nombre"]
            flash(f"¡Bienvenido de nuevo, {cliente['nombre']}!", "success")
            return redirect(url_for("index"))

        flash("Correo o contraseña incorrectos.", "error")

    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        correo = request.form["correo"]
        password = request.form["contraseña"]
        telefono = request.form["telefono"]

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO clientes (nombre, apellido, correo, contraseña, telefono)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, apellido, correo, hashed_password, telefono))

            conn.commit()
            flash("¡Registro exitoso! Por favor, inicia sesión.", "success")
            return redirect(url_for("login"))

        except psycopg2.IntegrityError:
            conn.rollback()
            flash("El correo ya está registrado o hay un error de integridad de datos.", "error")

        except Exception as e:
            conn.rollback()
            flash(f"Ocurrió un error al registrar: {e}", "error")

        finally:
            if cur: cur.close()
            if conn: conn.close()

    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("login"))


# ======================================================
#                 CATÁLOGO PRINCIPAL
# ======================================================

@app.route("/index")
@login_required
def index():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("index.html", productos=productos)


# ======================================================
#                       CARRITO
# ======================================================

@app.route("/add_cart", methods=["POST"])
@login_required
def add_cart():
    try:
        product_id = request.form["id_producto"]
        cantidad = int(request.form["cantidad"])
    except (KeyError, ValueError):
        flash("Error al procesar la solicitud de agregar al carrito.", "error")
        return redirect(url_for("index"))

    if "cart" not in session:
        session["cart"] = {}

    carrito = session["cart"]
    carrito[product_id] = carrito.get(product_id, 0) + cantidad
    session.modified = True

    flash(f"Producto {product_id} agregado al carrito.", "success")
    return redirect(url_for("index"))


@app.route("/carrito")
@login_required
def carrito():
    if "cart" not in session or len(session["cart"]) == 0:
        return render_template("carrito.html", items=[], total=0)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    items = []
    total = 0

    for idp, qty in session["cart"].items():
        cur.execute("SELECT * FROM productos WHERE id_producto = %s", (idp,))
        p = cur.fetchone()

        if p:
            subtotal = p["precio"] * qty
            items.append({"producto": p, "cantidad": qty, "subtotal": subtotal})
            total += subtotal

    cur.close()
    conn.close()

    return render_template("carrito.html", items=items, total=total)


@app.route("/eliminar/<int:idp>")
@login_required
def eliminar(idp):
    idp_str = str(idp)

    if "cart" in session:
        if idp_str in session["cart"]:
            session["cart"].pop(idp_str)
            session.modified = True
            flash("Producto eliminado del carrito.", "info")
        else:
            flash("Ese producto no se encontró en tu carrito.", "error")
    else:
        flash("Tu carrito está vacío.", "warning")

    return redirect(url_for("carrito"))


# ======================================================
#                     COMPRAR
# ======================================================

@app.route("/comprar", methods=["GET", "POST"])
@login_required
def comprar():
    id_cliente_existente = session.get("id_cliente")

    if not id_cliente_existente:
        flash("Tu sesión expiró. Por favor, vuelve a iniciar sesión.", "error")
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("comprar.html")

    codigo_postal = request.form.get("CP", "N/A")
    calle = request.form.get("calle", "N/A")
    num_ext = request.form.get("num_ext", "S/N")
    num_int = request.form.get("num_int", "")
    metodo_pago = request.form.get("metodo_pago", "N/A")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if "cart" in session and session["cart"]:
        try:
            for idp, qty in session["cart"].items():
                cur.execute("SELECT precio, stock FROM productos WHERE id_producto = %s", (idp,))
                result = cur.fetchone()

                if not result:
                    flash(f"Error: Producto con ID {idp} no encontrado.", "error")
                    conn.rollback()
                    return redirect(url_for("carrito"))

                if result["stock"] < qty:
                    flash(f"Error: Stock insuficiente para el producto {idp}.", "error")
                    conn.rollback()
                    return redirect(url_for("carrito"))

                precio = result["precio"]
                total_item = precio * qty

                cur.execute("""
                    INSERT INTO ventas (id_producto, id_clientes, cantidad, total, fecha_salida)
                    VALUES (%s, %s, %s, %s, CURRENT_DATE)
                """, (idp, id_cliente_existente, qty, total_item))

                cur.execute("""
                    UPDATE productos SET stock = stock - %s WHERE id_producto = %s
                """, (qty, idp))

            conn.commit()

        except Exception as e:
            conn.rollback()
            flash(f"Ocurrió un error al procesar la compra: {e}", "error")
            return redirect(url_for("carrito"))

        finally:
            if cur: cur.close()
            if conn: conn.close()

    else:
        flash("Tu carrito de compras está vacío.", "warning")
        return redirect(url_for("index"))

    session.pop("cart", None)

    flash("¡Compra realizada con éxito! Generando su ticket.", "success")

    return redirect(url_for("ticket",
                            id_cliente=id_cliente_existente,
                            cp=codigo_postal,
                            calle=calle,
                            num_ext=num_ext,
                            num_int=num_int,
                            metodo_pago=metodo_pago
                            ))


# ======================================================
#                   TICKET PDF
# ======================================================

@app.route("/ticket/<int:id_cliente>")
@login_required
def ticket(id_cliente):
    cp = request.args.get('cp', 'No Especificado')
    calle = request.args.get('calle', 'No Especificado')
    num_ext = request.args.get('num_ext', 'S/N')
    num_int = request.args.get('num_int', '')
    metodo_pago = request.args.get('metodo_pago', 'No Especificado')

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT c.nombre, c.apellido, v.id_producto, v.cantidad, v.total, v.fecha_salida,
        p.nombre AS nombre_producto, p.marca, p.talla
        FROM ventas v
        JOIN clientes c ON v.id_clientes = c.id_clientes
        JOIN productos p ON p.id_producto = v.id_producto
        WHERE v.id_clientes = %s
    """, (id_cliente,))

    ventas = cur.fetchall()
    cur.close()
    conn.close()

    if not ventas:
        flash("No se encontraron ventas para este cliente.", "error")
        return redirect(url_for("index"))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFillColorRGB(0.36, 0.25, 0.62)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, 750, "THE 4 FANTASTIC - Ticket de Compra")

    pdf.setFillColorRGB(0.1, 0.1, 0.1)
    pdf.setFont("Helvetica", 12)
    y = 720

    cliente = ventas[0]
    pdf.drawString(50, y, f"Cliente: {cliente['nombre']} {cliente['apellido']}")
    pdf.drawString(300, y, f"Fecha: {cliente['fecha_salida'].strftime('%d/%m/%Y')}")
    y -= 20

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Datos de Envío y Pago:")
    y -= 15
    pdf.setFont("Helvetica", 11)

    direccion_completa = f"Calle: {calle}"
    numeros = f"Ext: {num_ext}"
    if num_int:
        numeros += f" Int: {num_int}"

    pdf.drawString(50, y, direccion_completa)
    pdf.drawString(300, y, numeros)
    y -= 15
    pdf.drawString(50, y, f"Código Postal: {cp}")
    pdf.drawString(300, y, f"Método de Pago: {metodo_pago}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "PRODUCTO")
    pdf.drawString(125, y, "MARCA")
    pdf.drawString(210, y, "TALLA")
    pdf.drawString(300, y, "CANTIDAD")
    pdf.drawString(400, y, "TOTAL")
    y -= 15
    pdf.line(50, y, 550, y)
    y -= 15

    pdf.setFont("Helvetica", 11)
    subtotal_total = 0
    for v in ventas:
        total_str = "{:,.2f}".format(v['total'])
        pdf.drawString(50, y, f"{v['nombre_producto']}")
        pdf.drawString(125, y, f"{v['marca']}")
        pdf.drawString(210, y, f"{v['talla']}")
        pdf.drawString(300, y, f"{v['cantidad']}")
        pdf.drawString(400, y, f"${total_str}")
        subtotal_total += v["total"]
        y -= 20

        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = 750

    pdf.line(50, y - 10, 550, y - 10)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColorRGB(0.36, 0.25, 0.62)
    pdf.drawString(250, y - 30, "TOTAL PAGADO:")
    pdf.drawString(400, y - 30, f"${'{:,.2f}'.format(subtotal_total)}")

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="ticket.pdf", mimetype="application/pdf")


# ======================================================
#             EJECUCIÓN LOCAL
# ======================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
