from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.producto import Producto
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.auth.auth import login_required, role_required
from bson.objectid import ObjectId

cliente_bp = Blueprint('cliente', __name__, url_prefix='/cliente')


@cliente_bp.route('/perfil')
@role_required(['cliente'])
def perfil():
    usuario_id = session.get('usuario_id')
    usuario = Usuario.obtener_por_id(ObjectId(usuario_id))
    return render_template('cliente/perfil.html', usuario=usuario)


@cliente_bp.route('/editar_perfil', methods=['GET', 'POST'])
@role_required(['cliente'])
def editar_perfil():
    usuario_id = session.get('usuario_id')
    usuario = Usuario.obtener_por_id(ObjectId(usuario_id))

    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        direccion = request.form['direccion']

        usuario_actualizado = Usuario(
            nombre=nombre,
            email=usuario['email'],
            password=None,
            telefono=telefono,
            direccion=direccion,
            rol='cliente',
            _id=ObjectId(usuario_id)
        )

        usuario_actualizado.guardar()
        session['nombre'] = nombre
        flash('Perfil actualizado correctamente', 'success')
        return redirect(url_for('cliente.perfil'))

    return render_template('cliente/editar_perfil.html', usuario=usuario)


@cliente_bp.route('/carrito')
@role_required(['cliente'])
def carrito():
    if 'carrito' not in session:
        session['carrito'] = []

    # Obtener detalles completos de los productos en el carrito
    items_carrito = []
    total = 0

    for item in session['carrito']:
        producto = Producto.obtener_por_id(ObjectId(item['producto_id']))
        if producto:
            subtotal = producto['precio'] * item['cantidad']
            items_carrito.append({
                'producto': producto,
                'cantidad': item['cantidad'],
                'subtotal': subtotal
            })
            total += subtotal

    return render_template('cliente/carrito.html',
                           items=items_carrito,
                           total=total)


@cliente_bp.route('/agregar_al_carrito/<producto_id>', methods=['POST'])
@role_required(['cliente'])
def agregar_al_carrito(producto_id):
    producto = Producto.obtener_por_id(ObjectId(producto_id))
    if not producto:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('main.productos'))

    cantidad = int(request.form.get('cantidad', 1))

    if cantidad <= 0:
        flash('La cantidad debe ser mayor a 0', 'warning')
        return redirect(url_for('main.detalle_producto', producto_id=producto_id))

    if cantidad > producto['existencias']:
        flash(f'Solo hay {producto["existencias"]} unidades disponibles', 'warning')
        return redirect(url_for('main.detalle_producto', producto_id=producto_id))

    # Inicializar carrito si no existe
    if 'carrito' not in session:
        session['carrito'] = []

    # Verificar si el producto ya está en el carrito
    encontrado = False
    for item in session['carrito']:
        if item['producto_id'] == producto_id:
            item['cantidad'] += cantidad
            encontrado = True
            break

    if not encontrado:
        session['carrito'].append({
            'producto_id': producto_id,
            'cantidad': cantidad
        })

    session.modified = True
    flash(f'Se agregó {cantidad} {producto["nombre"]} al carrito', 'success')
    return redirect(url_for('cliente.carrito'))


@cliente_bp.route('/eliminar_del_carrito/<producto_id>')
@role_required(['cliente'])
def eliminar_del_carrito(producto_id):
    if 'carrito' in session:
        session['carrito'] = [item for item in session['carrito']
                              if item['producto_id'] != producto_id]
        session.modified = True
        flash('Producto eliminado del carrito', 'success')

    return redirect(url_for('cliente.carrito'))


@cliente_bp.route('/actualizar_carrito', methods=['POST'])
@role_required(['cliente'])
def actualizar_carrito():
    producto_id = request.form['producto_id']
    cantidad = int(request.form['cantidad'])

    if 'carrito' in session:
        for item in session['carrito']:
            if item['producto_id'] == producto_id:
                producto = Producto.obtener_por_id(ObjectId(producto_id))
                if cantidad > producto['existencias']:
                    flash(f'Solo hay {producto["existencias"]} unidades disponibles', 'warning')
                    cantidad = producto['existencias']

                item['cantidad'] = cantidad
                break

        session.modified = True
        flash('Carrito actualizado', 'success')

    return redirect(url_for('cliente.carrito'))


@cliente_bp.route('/checkout', methods=['GET', 'POST'])
@role_required(['cliente'])
def checkout():
    if 'carrito' not in session or len(session['carrito']) == 0:
        flash('Tu carrito está vacío', 'warning')
        return redirect(url_for('cliente.carrito'))

    if request.method == 'POST':
        usuario_id = session.get('usuario_id')
        direccion_entrega = request.form['direccion_entrega']
        metodo_pago = request.form['metodo_pago']

        # Preparar productos para el pedido
        productos_pedido = []
        for item in session['carrito']:
            producto = Producto.obtener_por_id(ObjectId(item['producto_id']))
            if producto:
                # Verificar existencias
                if not Producto.verificar_existencias(ObjectId(item['producto_id']), item['cantidad']):
                    flash(f'No hay suficientes existencias de {producto["nombre"]}', 'danger')
                    return redirect(url_for('cliente.carrito'))

                productos_pedido.append({
                    'producto_id': item['producto_id'],
                    'nombre': producto['nombre'],
                    'cantidad': item['cantidad'],
                    'precio_unitario': producto['precio']
                })

                # Actualizar existencias
                Producto.actualizar_existencias(ObjectId(item['producto_id']), item['cantidad'])

        # Crear pedido
        pedido = Pedido(
            cliente_id=ObjectId(usuario_id),
            productos=productos_pedido,
            estado='pendiente',
            direccion_entrega=direccion_entrega,
            metodo_pago=metodo_pago
        )

        # Crear pedido
        pedido_id = pedido.guardar()

        # Vaciar el carrito
        session['carrito'] = []
        session.modified = True

        flash('¡Pedido realizado con éxito!', 'success')
        return redirect(url_for('cliente.mis_pedidos'))

        # Si es GET, mostrar página de checkout
    items_carrito = []
    total = 0

    for item in session['carrito']:
        producto = Producto.obtener_por_id(ObjectId(item['producto_id']))
        if producto:
            subtotal = producto['precio'] * item['cantidad']
            items_carrito.append({
                'producto': producto,
                'cantidad': item['cantidad'],
                'subtotal': subtotal
            })
            total += subtotal

    usuario_id = session.get('usuario_id')
    usuario = Usuario.obtener_por_id(ObjectId(usuario_id))

    return render_template('cliente/checkout.html',
                           items=items_carrito,
                           total=total,
                           usuario=usuario)


@cliente_bp.route('/mis_pedidos')
@role_required(['cliente'])
def mis_pedidos():
    usuario_id = session.get('usuario_id')
    pedidos = Pedido.obtener_por_cliente(ObjectId(usuario_id))
    return render_template('cliente/mis_pedidos.html', pedidos=pedidos)


@cliente_bp.route('/pedido/<pedido_id>')
@role_required(['cliente'])
def detalle_pedido(pedido_id):
    pedido = Pedido.obtener_por_id(ObjectId(pedido_id))

    if not pedido or str(pedido['cliente_id']) != session.get('usuario_id'):
        flash('Pedido no encontrado', 'danger')
        return redirect(url_for('cliente.mis_pedidos'))

    return render_template('cliente/detalle_pedido.html', pedido=pedido)