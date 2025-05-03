from flask import Flask, session, redirect, url_for, render_template
from app.services.database import get_db
from config.config import Config
from bson.objectid import ObjectId
import datetime

# Importar Blueprints
from app.auth.auth import auth_bp
from app.controllers.main_controller import main_bp
from app.controllers.admin_controller import admin_bp
from app.controllers.cliente_controller import cliente_bp
from app.controllers.proveedor_controller import proveedor_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cliente_bp)
    app.register_blueprint(proveedor_bp)

    # Inicializar la base de datos
    with app.app_context():
        db = get_db()
        # Crear índices si es necesario
        db.usuarios.create_index('email', unique=True)
        db.productos.create_index([('nombre', 'text'), ('descripcion', 'text')])

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

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.route('/')
    def index():
        return redirect(url_for('main.index'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)