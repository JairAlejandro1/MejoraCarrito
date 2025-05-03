from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.producto import Producto
from app.models.pedido import Pedido
from app.models.proveedor import Proveedor
from app.auth.auth import role_required
from bson.objectid import ObjectId

proveedor_bp = Blueprint('proveedor', __name__, url_prefix='/proveedor')


@proveedor_bp.route('/dashboard')
@role_required(['proveedor'])
def dashboard():
    proveedor_id = session.get('proveedor_id')
    productos = Producto.obtener_por_proveedor(ObjectId(proveedor_id))

    # Contar productos agotados o con inventario bajo
    productos_agotados = 0
    productos_bajo_inventario = 0

    for producto in productos:
        if producto['existencias'] == 0:
            productos_agotados += 1
        elif producto['existencias'] < 10:  # Umbral de inventario bajo
            productos_bajo_inventario += 1

    return render_template('proveedor/dashboard.html',
                           total_productos=len(productos),
                           productos_agotados=productos_agotados,
                           productos_bajo_inventario=productos_bajo_inventario)


@proveedor_bp.route('/productos')
@role_required(['proveedor'])
def productos():
    proveedor_id = session.get('proveedor_id')
    productos = Producto.obtener_por_proveedor(ObjectId(proveedor_id))
    return render_template('proveedor/productos.html', productos=productos)


@proveedor_bp.route('/producto/nuevo', methods=['GET', 'POST'])
@role_required(['proveedor'])
def nuevo_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        existencias = int(request.form['existencias'])
        categoria = request.form['categoria']
        imagen_url = request.form['imagen_url']

        producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            existencias=existencias,
            categoria=categoria,
            proveedor_id=ObjectId(session.get('proveedor_id')),
            imagen_url=imagen_url
        )

        producto.guardar()
        flash('Producto agregado correctamente', 'success')
        return redirect(url_for('proveedor.productos'))

    return render_template('proveedor/nuevo_producto.html')


@proveedor_bp.route('/producto/editar/<producto_id>', methods=['GET', 'POST'])
@role_required(['proveedor'])
def editar_producto(producto_id):
    producto = Producto.obtener_por_id(ObjectId(producto_id))

    # Verificar que el producto pertenezca al proveedor
    if str(producto['proveedor_id']) != session.get('proveedor_id'):
        flash('No tienes permiso para editar este producto', 'danger')
        return redirect(url_for('proveedor.productos'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        existencias = int(request.form['existencias'])
        categoria = request.form['categoria']
        imagen_url = request.form['imagen_url']

        producto_actualizado = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            existencias=existencias,
            categoria=categoria,
            proveedor_id=ObjectId(session.get('proveedor_id')),
            imagen_url=imagen_url,
            _id=ObjectId(producto_id)
        )

        producto_actualizado.guardar()
        flash('Producto actualizado correctamente', 'success')
        return redirect(url_for('proveedor.productos'))

    return render_template('proveedor/editar_producto.html', producto=producto)


@proveedor_bp.route('/pedidos')
@role_required(['proveedor'])
def pedidos():
    proveedor_id = session.get('proveedor_id')
    # Obtener pedidos que contengan productos del proveedor
    pedidos = Pedido.obtener_por_proveedor(ObjectId(proveedor_id))
    return render_template('proveedor/pedidos.html', pedidos=pedidos)


@proveedor_bp.route('/pedido/<pedido_id>')
@role_required(['proveedor'])
def detalle_pedido(pedido_id):
    pedido = Pedido.obtener_por_id(ObjectId(pedido_id))

    # Filtrar solo los productos que pertenecen a este proveedor
    proveedor_id = session.get('proveedor_id')
    productos_proveedor = []

    for item in pedido['productos']:
        producto = Producto.obtener_por_id(ObjectId(item['producto_id']))
        if str(producto['proveedor_id']) == proveedor_id:
            productos_proveedor.append({
                'producto': producto,
                'cantidad': item['cantidad'],
                'precio_unitario': item['precio_unitario'],
                'subtotal': item['cantidad'] * item['precio_unitario']
            })

    return render_template('proveedor/detalle_pedido.html',
                           pedido=pedido,
                           productos=productos_proveedor)


@proveedor_bp.route('/inventario')
@role_required(['proveedor'])
def inventario():
    proveedor_id = session.get('proveedor_id')
    productos = Producto.obtener_por_proveedor(ObjectId(proveedor_id))

    # Clasificar productos por nivel de inventario
    productos_agotados = []
    productos_bajo_inventario = []
    productos_normal = []

    for producto in productos:
        if producto['existencias'] == 0:
            productos_agotados.append(producto)
        elif producto['existencias'] < 10:
            productos_bajo_inventario.append(producto)
        else:
            productos_normal.append(producto)

    return render_template('proveedor/inventario.html',
                           productos_agotados=productos_agotados,
                           productos_bajo_inventario=productos_bajo_inventario,
                           productos_normal=productos_normal)


@proveedor_bp.route('/actualizar_inventario/<producto_id>', methods=['POST'])
@role_required(['proveedor'])
def actualizar_inventario(producto_id):
    nueva_cantidad = int(request.form['existencias'])
    producto = Producto.obtener_por_id(ObjectId(producto_id))

    # Verificar que el producto pertenezca al proveedor
    if str(producto['proveedor_id']) != session.get('proveedor_id'):
        flash('No tienes permiso para actualizar este producto', 'danger')
        return redirect(url_for('proveedor.inventario'))

    Producto.actualizar_inventario(ObjectId(producto_id), nueva_cantidad)
    flash('Inventario actualizado correctamente', 'success')
    return redirect(url_for('proveedor.inventario'))