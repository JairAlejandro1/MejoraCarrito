from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.models.producto import Producto
from bson.objectid import ObjectId

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    productos_destacados = Producto.obtener_todos()[:6]
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
    try:
        producto = Producto.obtener_por_id(ObjectId(producto_id))
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect(url_for('main.productos'))
        return render_template('main/detalle_producto.html',
                              producto=producto,
                              is_authenticated='usuario_id' in session)
    except Exception as e:
        flash(f'Error al cargar el producto: {str(e)}', 'danger')
        return redirect(url_for('main.productos'))