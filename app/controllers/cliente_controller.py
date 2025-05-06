from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.producto import Producto
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.auth.auth import login_required, role_required
from app.services.database import get_db
from bson.objectid import ObjectId

cliente_bp = Blueprint('cliente', __name__, url_prefix='/cliente')


@cliente_bp.route('/perfil')
@role_required(['cliente'])
def perfil():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        flash('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning')
        return redirect(url_for('auth.login'))

    # Obtener información del usuario
    usuario = Usuario.obtener_por_id(ObjectId(usuario_id))
    if not usuario:
        flash('Usuario no encontrado. Por favor inicia sesión nuevamente.', 'warning')
        return redirect(url_for('auth.login'))

    # Obtener pedidos recientes
    pedidos_recientes = []
    try:
        pedidos = Pedido.obtener_por_cliente(ObjectId(usuario_id))
        if pedidos and isinstance(pedidos, list):
            # Añadir _id_str para cada pedido
            for pedido in pedidos:
                pedido['_id_str'] = str(pedido['_id'])
            pedidos_recientes = pedidos[:3]  # Limitar a los 3 más recientes
    except Exception as e:
        print(f"Error al obtener pedidos: {str(e)}")
        # No se muestra error al usuario, simplemente se muestra una lista vacía

    return render_template('cliente/perfil.html',
                           usuario=usuario,
                           pedidos_recientes=pedidos_recientes)


@cliente_bp.route('/editar_perfil', methods=['GET', 'POST'])
@role_required(['cliente'])
def editar_perfil():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        flash('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning')
        return redirect(url_for('auth.login'))

    usuario = Usuario.obtener_por_id(ObjectId(usuario_id))
    if not usuario:
        flash('Usuario no encontrado. Por favor inicia sesión nuevamente.', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')

        # Actualizar usuario directamente en la base de datos
        db = get_db()
        db.usuarios.update_one(
            {"_id": ObjectId(usuario_id)},
            {"$set": {
                "nombre": nombre,
                "telefono": telefono,
                "direccion": direccion
            }}
        )

        # Actualizar sesión
        session['nombre'] = nombre

        flash('Perfil actualizado correctamente', 'success')
        return redirect(url_for('cliente.perfil'))

    return render_template('cliente/editar_perfil.html', usuario=usuario)


@cliente_bp.route('/cambiar_password', methods=['POST'])
@role_required(['cliente'])
def cambiar_password():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        flash('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning')
        return redirect(url_for('auth.login'))

    usuario = Usuario.obtener_por_id(ObjectId(usuario_id))
    if not usuario:
        flash('Usuario no encontrado. Por favor inicia sesión nuevamente.', 'warning')
        return redirect(url_for('auth.login'))

    password_actual = request.form.get('password_actual')
    password_nueva = request.form.get('password_nueva')
    password_confirmacion = request.form.get('password_confirmacion')

    if not password_actual or not password_nueva or not password_confirmacion:
        flash('Todos los campos son obligatorios', 'danger')
        return redirect(url_for('cliente.editar_perfil'))

    # Verificar la contraseña actual
    usuario_obj = Usuario(
        nombre=usuario['nombre'],
        email=usuario['email'],
        password=None,
        telefono=usuario['telefono'],
        direccion=usuario['direccion'],
        rol='cliente'
    )
    usuario_obj.password = usuario['password']

    if not usuario_obj.verificar_password(password_actual):
        flash('La contraseña actual es incorrecta', 'danger')
        return redirect(url_for('cliente.editar_perfil'))

    # Verificar que las contraseñas nuevas coincidan
    if password_nueva != password_confirmacion:
        flash('Las contraseñas nuevas no coinciden', 'danger')
        return redirect(url_for('cliente.editar_perfil'))

    # Crear un nuevo objeto Usuario
    usuario_nuevo = Usuario(
        nombre=usuario['nombre'],
        email=usuario['email'],
        password=password_nueva,
        telefono=usuario['telefono'],
        direccion=usuario['direccion'],
        rol='cliente'
    )

    # Guardar el hash de la nueva contraseña
    password_hash = usuario_nuevo.password

    # Actualizar directamente en la base de datos
    db = get_db()
    db.usuarios.update_one(
        {"_id": ObjectId(usuario_id)},
        {"$set": {"password": password_hash}}
    )

    flash('Contraseña actualizada correctamente', 'success')
    return redirect(url_for('cliente.perfil'))


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

    # Get and validate the quantity
    cantidad = request.form.get('cantidad', '1')

    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            flash('La cantidad debe ser un número positivo', 'warning')
            return redirect(url_for('main.detalle_producto', producto_id=producto_id))
    except ValueError:
        flash('La cantidad debe ser un número entero', 'warning')
        return redirect(url_for('main.detalle_producto', producto_id=producto_id))

    # Volver a verificar existencias en tiempo real
    producto_actualizado = Producto.obtener_por_id(ObjectId(producto_id))
    if cantidad > producto_actualizado['existencias']:
        flash(f'Solo hay {producto_actualizado["existencias"]} unidades disponibles', 'warning')
        return redirect(url_for('main.detalle_producto', producto_id=producto_id))

    # Inicializar carrito si no existe
    if 'carrito' not in session:
        session['carrito'] = []

    # Verificar si el producto ya está en el carrito
    encontrado = False
    for item in session['carrito']:
        if item['producto_id'] == producto_id:
            # Verificar que la suma no exceda el inventario disponible
            nueva_cantidad = item['cantidad'] + cantidad
            if nueva_cantidad > producto_actualizado['existencias']:
                flash(f'No se puede agregar más de {producto_actualizado["existencias"]} unidades de este producto',
                      'warning')
                return redirect(url_for('cliente.carrito'))

            item['cantidad'] = nueva_cantidad
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
    cantidad = request.form['cantidad']

    # Validar que la cantidad sea un número entero positivo
    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            flash('La cantidad debe ser un número positivo', 'warning')
            return redirect(url_for('cliente.carrito'))
    except ValueError:
        flash('La cantidad debe ser un número entero', 'warning')
        return redirect(url_for('cliente.carrito'))

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
        direccion_entrega = request.form.get('direccion_entrega')
        metodo_pago = request.form.get('metodo_pago')

        # Verificar campos requeridos
        if not direccion_entrega or not metodo_pago:
            flash('Por favor completa todos los campos requeridos', 'danger')
            return redirect(url_for('cliente.checkout'))

        # Verificar campos de tarjeta si el método es tarjeta
        if metodo_pago == 'tarjeta':
            card_number = request.form.get('card_number')
            card_expiry = request.form.get('card_expiry')
            card_cvv = request.form.get('card_cvv')

            if not card_number or not card_expiry or not card_cvv:
                flash('Por favor completa todos los campos de la tarjeta', 'danger')
                return redirect(url_for('cliente.checkout'))

        # Lista para productos que se procesaron correctamente
        productos_procesados = []
        # Lista para productos que fallaron (no había suficiente stock)
        productos_fallidos = []

        # Preparar productos para el pedido y verificar existencias atómicamente
        for item in session['carrito']:
            producto_id = ObjectId(item['producto_id'])
            cantidad = item['cantidad']

            # Obtener información del producto para mostrar mensaje de error si es necesario
            producto = Producto.obtener_por_id(producto_id)
            if not producto:
                productos_fallidos.append(f"Producto con ID {item['producto_id']}")
                continue

            # Verificar y actualizar existencias atómicamente en un solo paso
            if Producto.verificar_y_reservar(producto_id, cantidad):
                # Si se actualizó correctamente, añadir a productos procesados
                productos_procesados.append({
                    'producto_id': str(producto_id),  # Convertir a string
                    'nombre': producto['nombre'],
                    'cantidad': cantidad,
                    'precio_unitario': producto['precio']
                })
            else:
                # Si no se pudo actualizar (no hay suficientes existencias), añadir a productos fallidos
                productos_fallidos.append(producto['nombre'])

                # Restituir existencias de productos procesados anteriormente si hay algún fallo
                for prod in productos_procesados:
                    Producto.restituir_existencias(ObjectId(prod['producto_id']), prod['cantidad'])

                # Devolver al carrito y mostrar mensaje de error
                flash(
                    f'No hay suficientes existencias de {producto["nombre"]}. Otro usuario puede haberlo comprado mientras estabas en checkout.',
                    'danger')
                return redirect(url_for('cliente.carrito'))

        # Si llegamos aquí, todos los productos se procesaron correctamente
        if productos_procesados:
            # Crear pedido
            pedido = Pedido(
                cliente_id=ObjectId(usuario_id),
                productos=productos_procesados,
                estado='pendiente',
                direccion_entrega=direccion_entrega,
                metodo_pago=metodo_pago
            )

            # Guardar pedido
            pedido_id = pedido.guardar()

            # Vaciar el carrito solo después de que todo esté confirmado
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
    if not usuario_id:
        flash('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning')
        return redirect(url_for('auth.login'))

    pedidos = Pedido.obtener_por_cliente(ObjectId(usuario_id))
    if not pedidos:
        pedidos = []
    else:
        # Añadir _id_str para cada pedido
        for pedido in pedidos:
            pedido['_id_str'] = str(pedido['_id'])

    return render_template('cliente/mis_pedidos.html', pedidos=pedidos)


@cliente_bp.route('/pedido/<pedido_id>')
@role_required(['cliente'])
def detalle_pedido(pedido_id):
    try:
        pedido = Pedido.obtener_por_id(ObjectId(pedido_id))

        if not pedido:
            flash('Pedido no encontrado', 'danger')
            return redirect(url_for('cliente.mis_pedidos'))

        # Añadir _id_str para el template
        pedido['_id_str'] = str(pedido['_id'])

        # Convertir cliente_id a string si es ObjectId
        cliente_id_pedido = pedido['cliente_id']
        if isinstance(cliente_id_pedido, ObjectId):
            cliente_id_pedido = str(cliente_id_pedido)

        usuario_id = session.get('usuario_id')

        # Solo comparar IDs si ambos son del mismo tipo (string)
        if cliente_id_pedido != usuario_id:
            flash('No tienes permiso para ver este pedido', 'danger')
            return redirect(url_for('cliente.mis_pedidos'))

        return render_template('cliente/detalle_pedido.html', pedido=pedido)
    except Exception as e:
        print(f"Error en detalle_pedido: {str(e)}")
        flash(f'Error al cargar el detalle del pedido: {str(e)}', 'danger')
        return redirect(url_for('cliente.mis_pedidos'))


@cliente_bp.route('/pedido/cancelar/<pedido_id>', methods=['POST'])
@role_required(['cliente'])
def cancelar_pedido(pedido_id):
    try:
        # Verificar si el pedido existe
        pedido = Pedido.obtener_por_id(ObjectId(pedido_id))

        if not pedido:
            flash('Pedido no encontrado', 'danger')
            return redirect(url_for('cliente.mis_pedidos'))

        # Verificar que el pedido pertenece al cliente actual
        cliente_id_pedido = pedido['cliente_id']
        if isinstance(cliente_id_pedido, ObjectId):
            cliente_id_pedido = str(cliente_id_pedido)

        usuario_id = session.get('usuario_id')

        if cliente_id_pedido != usuario_id:
            flash('No tienes permiso para cancelar este pedido', 'danger')
            return redirect(url_for('cliente.mis_pedidos'))

        # Verificar que el pedido esté en estado pendiente
        if pedido['estado'] != 'pendiente':
            flash('Solo se pueden cancelar pedidos en estado pendiente', 'danger')
            return redirect(url_for('cliente.detalle_pedido', pedido_id=pedido_id))

        # Actualizar el estado del pedido a "cancelado"
        Pedido.actualizar_estado(ObjectId(pedido_id), 'cancelado')

        flash('Pedido cancelado correctamente', 'success')
        return redirect(url_for('cliente.mis_pedidos'))

    except Exception as e:
        print(f"Error en cancelar_pedido: {str(e)}")
        flash(f'Error al cancelar el pedido: {str(e)}', 'danger')
        return redirect(url_for('cliente.mis_pedidos'))