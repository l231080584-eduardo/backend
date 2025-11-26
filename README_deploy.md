
# BD_tenis - Deployment guide (Railway backend + Vercel frontend)

Este paquete contiene los ajustes mínimos para desplegar tu backend Flask en **Railway** y tu frontend estático en **Vercel**.

## Archivos incluidos
- `app.py` - Flask app preparada para producción (usa DATABASE_URL si está definida).
- `requirements.txt` - Dependencias.
- `Procfile` - Para que Railway use gunicorn.
- `vercel.json` - Indica a Vercel que sirva la carpeta `public`.
- `.env.example` - Variables de entorno de ejemplo.

---
## Paso A: Preparar el backend en Railway (rápido)
1. Crea un repositorio en GitHub con la carpeta `backend` (o usa tu repo actual).
2. Sube `app.py`, `requirements.txt`, `Procfile`, y tus templates estáticos (carpeta `templates/`) y `static/` si aplican.
3. En Railway, crea un nuevo **"Deploy from GitHub"** y conecta el repo y branch.
4. En Railway, agrega el plugin **Postgres** (Create plugin -> PostgreSQL). Esto te dará una variable de entorno `DATABASE_URL` automáticamente.
   - Si prefieres usar variables separadas, define `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS` en Settings -> Environment.
5. En Settings -> Variables del servicio en Railway, añade `FLASK_SECRET_KEY` (valor largo) y, si estás en desarrollo, `FLASK_ENV=development` para cargar `.env` local.
6. Deploy: Railway instalará las dependencias y lanzará gunicorn usando el `Procfile`.

## Paso B: Preparar el frontend en Vercel
1. Asegúrate que tu carpeta `public/` contiene `index.html`.
2. En la configuración del repo en Vercel, en General -> Build & Output Settings, configura **Output Directory** como `public` o sube `vercel.json` con `{"outputDirectory":"public"}`.
3. Ajusta llamadas del frontend a la URL de tu API en Railway. Por ejemplo, si Railway te da `https://bd-tenis-xyz.up.railway.app`, usa esa base en las peticiones fetch/axios.
4. Despliega en Vercel normalmente.

---
## Nota sobre CORS y llamadas AJAX
- Si tu frontend y backend quedan en dominios distintos, asegúrate de habilitar CORS en Flask (pip install flask-cors) o configurar encabezados apropiados para permitir peticiones desde tu dominio Vercel.

---
## Variables de entorno recomendadas
- `DATABASE_URL` (proporcionada por Railway Postgres plugin)
- `FLASK_SECRET_KEY` (string aleatorio)
- Opcional: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`

---
Si quieres, puedo:
- Generar la estructura de carpetas `templates/` y `static/` con tus archivos actuales.
- Crear un pequeño script para reemplazar las URLs del frontend por la URL final de Railway.
- Guiarte en cada click dentro de Railway y Vercel.
