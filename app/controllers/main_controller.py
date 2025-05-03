from flask import Blueprint, render_template, session
from app.models.producto import Producto

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    productos_destacados = Producto.obtener_todos()[:6]  # Limitar a 6 para mostrar en la página principal
    return render_template('main/index.html',
                          productos=productos_destacados,
                          is_authenticated='usuario_id' in session)

@main_bp.route('/productos')
def productos():
    productos = Producto.obtener_todos()
    return render_template('main/productos.html',
                          productos=productos,
                          is_authenticated='usuario_id' in session)

@main_bp.route('/producto/<producto_id>')
def detalle_producto(producto_id):
    producto = Producto.obtener_por_id(producto_id)
    return render_template('main/detalle_producto.html',
                          producto=producto,
                          is_authenticated='usuario_id' in session)