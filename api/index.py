from flask import Flask, jsonify, request
import psycopg2
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Railway uses a single DATABASE_URL variable ---
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        raise e


@app.route("/")
def home():
    return jsonify({"message": "Backend funcionando correctamente"})


# ------------------ USUARIOS ------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id_usuario, nombre FROM usuarios WHERE correo = %s AND password = %s",
        (email, password),
    )
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return jsonify({"status": "success", "user_id": user[0], "nombre": user[1]})
    else:
        return jsonify({"status": "error", "message": "Credenciales incorrectas"}), 401


# ------------------ TENIS ------------------
@app.route("/tenis", methods=["GET"])
def obtener_tenis():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id_tenis, nombre, precio, stock, descripcion FROM tenis")
    tenis = cursor.fetchall()

    cursor.close()
    conn.close()

    lista = []
    for t in tenis:
        lista.append({
            "id": t[0],
            "nombre": t[1],
            "precio": t[2],
            "stock": t[3],
            "descripcion": t[4]
        })

    return jsonify(lista)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
