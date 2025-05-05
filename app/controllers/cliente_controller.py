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
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            flash('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth.login'))

        # Obtener información del usuario
        usuario = Usuario.obtener_por_id(ObjectId(usuario_id))
        if not usuario:
            flash('Usuario no encontrado. Por favor inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth.login'))

        # Obtener pedidos recientes de forma segura
        pedidos_recientes = []
        try:
            pedidos = Pedido.obtener_por_cliente(ObjectId(usuario_id))
            if pedidos and isinstance(pedidos, list):
                pedidos_recientes = pedidos[:3]  # Limitar a los 3 más recientes
        except Exception as e:
            print(f"Error al obtener pedidos: {str(e)}")
            # No se muestra error al usuario, simplemente se muestra una lista vacía

        return render_template('cliente/perfil.html',
                               usuario=usuario,
                               pedidos_recientes=pedidos_recientes)
    except Exception as e:
        flash(f'Error al cargar el perfil: {str(e)}', 'danger')
        return redirect(url_for('main.index'))


@cliente_bp.route('/editar_perfil', methods=['GET', 'POST'])
@role_required(['cliente'])
def editar_perfil():
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            flash('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth.login'))

        usuario = Usuario.obtener_por_id(ObjectId(usuario_id))
        if not usuario:
            flash('Usuario no encontrado. Por favor inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth.login'))

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
    except Exception as e:
        flash(f'Error al cargar o actualizar el perfil: {str(e)}', 'danger')
        return redirect(url_for('main.index'))


@cliente_bp.route('/cambiar_password', methods=['POST'])
@role_required(['cliente'])
def cambiar_password():
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            flash('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth.login'))

        usuario = Usuario.obtener_por_id(ObjectId(usuario_id))
        if not usuario:
            flash('Usuario no encontrado. Por favor inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth.login'))

        password_actual = request.form['password_actual']
        password_nueva = request.form['password_nueva']
        password_confirmacion = request.form['password_confirmacion']

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

        # Actualizar la contraseña
        usuario_actualizado = Usuario(
            nombre=usuario['nombre'],
            email=usuario['email'],
            password=password_nueva,
            telefono=usuario['telefono'],
            direccion=usuario['direccion'],
            rol='cliente',
            _id=ObjectId(usuario_id)
        )

        usuario_actualizado.guardar()
        flash('Contraseña actualizada correctamente', 'success')
        return redirect(url_for('cliente.perfil'))
    except Exception as e:
        flash(f'Error al cambiar la contraseña: {str(e)}', 'danger')
        return redirect(url_for('cliente.editar_perfil'))


@cliente_bp.route('/carrito')
@role_required(['cliente'])
def carrito():
    try:
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
    except Exception as e:
        flash(f'Error al cargar el carrito: {str(e)}', 'danger')
        return redirect(url_for('main.index'))


@cliente_bp.route('/agregar_al_carrito/<producto_id>', methods=['POST'])
@role_required(['cliente'])
def agregar_al_carrito(producto_id):
    try:
        producto = Producto.obtener_por_id(ObjectId(producto_id))
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect(url_for('main.productos'))

        cantidad = int(request.form.get('cantidad', 1))

        if cantidad <= 0:
            flash('La cantidad debe ser mayor a 0', 'warning')
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
    except Exception as e:
        flash(f'Error al agregar producto al carrito: {str(e)}', 'danger')
        return redirect(url_for('main.productos'))


@cliente_bp.route('/eliminar_del_carrito/<producto_id>')
@role_required(['cliente'])
def eliminar_del_carrito(producto_id):
    try:
        if 'carrito' in session:
            session['carrito'] = [item for item in session['carrito']
                                  if item['producto_id'] != producto_id]
            session.modified = True
            flash('Producto eliminado del carrito', 'success')

        return redirect(url_for('cliente.carrito'))
    except Exception as e:
        flash(f'Error al eliminar producto del carrito: {str(e)}', 'danger')
        return redirect(url_for('cliente.carrito'))


@cliente_bp.route('/actualizar_carrito', methods=['POST'])
@role_required(['cliente'])
def actualizar_carrito():
    try:
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
    except Exception as e:
        flash(f'Error al actualizar carrito: {str(e)}', 'danger')
        return redirect(url_for('cliente.carrito'))


@cliente_bp.route('/checkout', methods=['GET', 'POST'])
@role_required(['cliente'])
def checkout():
    try:
        if 'carrito' not in session or len(session['carrito']) == 0:
            flash('Tu carrito está vacío', 'warning')
            return redirect(url_for('cliente.carrito'))

        if request.method == 'POST':
            usuario_id = session.get('usuario_id')
            direccion_entrega = request.form['direccion_entrega']
            metodo_pago = request.form['metodo_pago']

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
                        'producto_id': item['producto_id'],
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
    except Exception as e:
        flash(f'Error en el proceso de checkout: {str(e)}', 'danger')
        return redirect(url_for('cliente.carrito'))


@cliente_bp.route('/mis_pedidos')
@role_required(['cliente'])
def mis_pedidos():
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            flash('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth.login'))

        pedidos = Pedido.obtener_por_cliente(ObjectId(usuario_id))
        if not pedidos:
            pedidos = []

        return render_template('cliente/mis_pedidos.html', pedidos=pedidos)
    except Exception as e:
        flash(f'Error al cargar tus pedidos: {str(e)}', 'danger')
        return redirect(url_for('cliente.perfil'))


@cliente_bp.route('/pedido/<pedido_id>')
@role_required(['cliente'])
def detalle_pedido(pedido_id):
    try:
        pedido = Pedido.obtener_por_id(ObjectId(pedido_id))

        if not pedido or str(pedido['cliente_id']) != session.get('usuario_id'):
            flash('Pedido no encontrado', 'danger')
            return redirect(url_for('cliente.mis_pedidos'))

        return render_template('cliente/detalle_pedido.html', pedido=pedido)
    except Exception as e:
        flash(f'Error al cargar el detalle del pedido: {str(e)}', 'danger')
        return redirect(url_for('cliente.mis_pedidos'))