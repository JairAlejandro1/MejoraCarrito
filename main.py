from flask import Flask, session, redirect, url_for, render_template, flash, g, request, current_app
from app.services.database import get_db
from config.config import Config
from bson.objectid import ObjectId
import datetime
import os
from werkzeug.utils import secure_filename
from pyngrok import ngrok
# Importar función de debug
from app.debug_utils import setup_debugging

# Importar Blueprints
from app.auth.auth import auth_bp
from app.controllers.main_controller import main_bp
from app.controllers.admin_controller import admin_bp
from app.controllers.cliente_controller import cliente_bp
from app.controllers.proveedor_controller import proveedor_bp

# Definir constantes para la subida de archivos
UPLOAD_FOLDER = 'static/uploads/productos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configurar la carpeta de subida de archivos
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cliente_bp)
    app.register_blueprint(proveedor_bp)

    # Inicializar la base de datos
    with app.app_context():
        try:
            db = get_db()
            # Crear índices si es necesario
            db.usuarios.create_index('email', unique=True)
            db.productos.create_index([('nombre', 'text'), ('descripcion', 'text')])
        except Exception as e:
            print(f"Error al inicializar la base de datos: {str(e)}")

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Manejar excepciones genéricas
        app.logger.error(f"Uncaught exception: {str(e)}")
        return render_template('error.html',
                               error=str(e),
                               title="Error",
                               message="Ha ocurrido un error inesperado"), 500

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html', title="Página no encontrada"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('error.html',
                               title="Error interno del servidor",
                               message="Ha ocurrido un error en el servidor."), 500

    @app.context_processor
    def utility_processor():
        # Utilidades disponibles en todas las plantillas
        def es_admin():
            return session.get('rol') == 'admin'

        def es_cliente():
            return session.get('rol') == 'cliente'

        def es_proveedor():
            return session.get('rol') == 'proveedor'

        def items_carrito():
            return len(session.get('carrito', []))

        def formato_fecha(fecha):
            if isinstance(fecha, datetime.datetime):
                return fecha.strftime('%d/%m/%Y %H:%M')
            return ""

        def truncate_id(id_obj):
            if isinstance(id_obj, ObjectId):
                return str(id_obj)[:8]
            return str(id_obj)[:8]

        def calcular_subtotal(precio, cantidad):
            return round(precio * cantidad, 2)

        return dict(
            es_admin=es_admin,
            es_cliente=es_cliente,
            es_proveedor=es_proveedor,
            items_carrito=items_carrito,
            formato_fecha=formato_fecha,
            truncate_id=truncate_id,
            calcular_subtotal=calcular_subtotal,
            datetime=datetime
        )

    @app.route('/')
    def index():
        return redirect(url_for('main.index'))

    return app


if __name__ == '__main__':
    app = create_app()

    # Configurar herramientas de debugging
    setup_debugging(app)

    # Obtener número de administradores
    from app.models.usuario import Usuario
    from bson.objectid import ObjectId

    # Verificar si existen administradores
    with app.app_context():
        admin_count = len(list(Usuario.obtener_todos_por_rol('admin')))

    # Crear enlaces útiles
    local_url = "http://127.0.0.1:5000"

    print("\n" + "=" * 50)
    print("EcoShop - Sistema de Comercio Electrónico")
    print("=" * 50)

    # Solo mostrar los 3 enlaces solicitados
    if admin_count == 0:
        print(f"[1] Crear Administrador: {local_url}/registrar-admin")

    print(f"[2] Abrir localmente: {local_url}")

    # Configurar ngrok si está disponible
    try:
        public_url = ngrok.connect(5000)
        print(f"[3] Abrir globalmente con ngrok: {public_url}")
    except:
        print("[3] Abrir globalmente con ngrok: ngrok no está disponible")

    print("=" * 50 + "\n")

    # Configuración para evitar el error de socket en Windows
    if os.name == 'nt':  # Si es Windows
        app.config['WERKZEUG_RUN_MAIN'] = 'true'

    app.run(debug=True)