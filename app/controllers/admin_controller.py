from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.models.producto import Producto
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario
from app.models.pedido import Pedido
from app.auth.auth import role_required
from bson.objectid import ObjectId
import os
from werkzeug.utils import secure_filename
import uuid

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Definir constantes para la subida de archivos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@admin_bp.route('/dashboard')
@role_required(['admin'])
def dashboard():
    total_productos = len(Producto.obtener_todos())
    total_clientes = len(list(Usuario.obtener_todos_por_rol('cliente')))
    total_pedidos = len(list(Pedido.obtener_todos()))

    # Obtener productos con bajo inventario para mostrar en el dashboard
    productos_bajo_inventario = []
    for producto in Producto.obtener_todos():
        if producto['existencias'] <= 5:
            productos_bajo_inventario.append(producto)

    # Obtener últimos pedidos
    ultimos_pedidos = Pedido.obtener_todos()[:5]

    # Para cada pedido, obtener información del cliente
    for pedido in ultimos_pedidos:
        cliente = Usuario.obtener_por_id(pedido['cliente_id'])
        if cliente:
            pedido['cliente_nombre'] = cliente['nombre']
        else:
            pedido['cliente_nombre'] = "Cliente desconocido"

    return render_template('admin/dashboard.html',
                           total_productos=total_productos,
                           total_clientes=total_clientes,
                           total_pedidos=total_pedidos,
                           productos_bajo_inventario=productos_bajo_inventario[:5],
                           ultimos_pedidos=ultimos_pedidos)


@admin_bp.route('/productos')
@role_required(['admin'])
def productos():
    productos = Producto.obtener_todos()
    return render_template('admin/productos.html', productos=productos)


@admin_bp.route('/producto/nuevo', methods=['GET', 'POST'])
@role_required(['admin'])
def nuevo_producto():
    if request.method == 'POST':
        # Procesar formulario
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        existencias = int(request.form['existencias'])
        categoria = request.form['categoria']
        proveedor_id = request.form['proveedor_id']

        # Manejar la subida de archivos
        imagen_url = None
        if 'imagen' in request.files:
            archivo = request.files['imagen']
            if archivo.filename != '' and allowed_file(archivo.filename):
                # Asegurar que el nombre del archivo sea seguro
                filename = secure_filename(archivo.filename)
                # Generar un nombre único para evitar colisiones
                filename = f"{str(uuid.uuid4())}_{filename}"
                # Guardar el archivo
                upload_folder = os.path.join('static', 'uploads', 'productos')
                os.makedirs(upload_folder, exist_ok=True)
                archivo.save(os.path.join(upload_folder, filename))
                # Construir la URL para acceder a la imagen
                imagen_url = f"/static/uploads/productos/{filename}"

        producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            existencias=existencias,
            categoria=categoria,
            proveedor_id=ObjectId(proveedor_id),
            imagen_url=imagen_url
        )

        producto.guardar()
        flash('Producto agregado correctamente', 'success')
        return redirect(url_for('admin.productos'))

    proveedores = Proveedor.obtener_todos()
    return render_template('admin/nuevo_producto.html', proveedores=proveedores)


@admin_bp.route('/producto/editar/<producto_id>', methods=['GET', 'POST'])
@role_required(['admin'])
def editar_producto(producto_id):
    producto = Producto.obtener_por_id(ObjectId(producto_id))

    if request.method == 'POST':
        # Actualizar producto
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        existencias = int(request.form['existencias'])
        categoria = request.form['categoria']
        proveedor_id = request.form['proveedor_id']

        # Manejar la imagen
        imagen_url = producto['imagen_url']  # Mantener la imagen actual por defecto
        if 'imagen' in request.files:
            archivo = request.files['imagen']
            if archivo.filename != '' and allowed_file(archivo.filename):
                # Asegurar que el nombre del archivo sea seguro
                filename = secure_filename(archivo.filename)
                # Generar un nombre único para evitar colisiones
                filename = f"{str(uuid.uuid4())}_{filename}"
                # Guardar el archivo
                upload_folder = os.path.join('static', 'uploads', 'productos')
                os.makedirs(upload_folder, exist_ok=True)
                archivo.save(os.path.join(upload_folder, filename))
                # Construir la URL para acceder a la imagen
                imagen_url = f"/static/uploads/productos/{filename}"

        producto_actualizado = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            existencias=existencias,
            categoria=categoria,
            proveedor_id=ObjectId(proveedor_id),
            imagen_url=imagen_url,
            _id=ObjectId(producto_id)
        )

        producto_actualizado.guardar()
        flash('Producto actualizado correctamente', 'success')
        return redirect(url_for('admin.productos'))

    proveedores = Proveedor.obtener_todos()
    return render_template('admin/editar_producto.html',
                           producto=producto,
                           proveedores=proveedores)


@admin_bp.route('/producto/eliminar', methods=['POST'])
@role_required(['admin'])
def eliminar_producto():
    producto_id = request.form['producto_id']
    # Implementar eliminación lógica
    Producto.eliminar(ObjectId(producto_id))
    flash('Producto eliminado correctamente', 'success')
    return redirect(url_for('admin.productos'))


@admin_bp.route('/pedidos')
@role_required(['admin'])
def pedidos():
    pedidos = []
    try:
        pedidos = Pedido.obtener_todos()

        # Para cada pedido, obtener información del cliente
        for pedido in pedidos:
            cliente = Usuario.obtener_por_id(pedido['cliente_id'])
            if cliente:
                pedido['cliente_nombre'] = cliente['nombre']
            else:
                pedido['cliente_nombre'] = "Cliente desconocido"
    except Exception as e:
        flash(f'Error al obtener pedidos: {str(e)}', 'danger')

    return render_template('admin/pedidos.html', pedidos=pedidos)


@admin_bp.route('/pedido/<pedido_id>')
@role_required(['admin'])
def detalle_pedido(pedido_id):
    try:
        pedido = Pedido.obtener_por_id(ObjectId(pedido_id))

        # Obtener información del cliente
        cliente = Usuario.obtener_por_id(pedido['cliente_id'])

        return render_template('admin/detalle_pedido.html',
                               pedido=pedido,
                               cliente=cliente)
    except Exception as e:
        flash(f'Error al obtener detalle del pedido: {str(e)}', 'danger')
        return redirect(url_for('admin.pedidos'))


@admin_bp.route('/pedido/actualizar_estado/<pedido_id>', methods=['POST'])
@role_required(['admin'])
def actualizar_estado_pedido(pedido_id):
    try:
        nuevo_estado = request.form['estado']
        Pedido.actualizar_estado(ObjectId(pedido_id), nuevo_estado)
        flash('Estado del pedido actualizado correctamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar estado: {str(e)}', 'danger')

    return redirect(url_for('admin.pedidos'))


@admin_bp.route('/proveedores')
@role_required(['admin'])
def proveedores():
    proveedores = []
    try:
        proveedores = Proveedor.obtener_todos()

        # Contar productos de cada proveedor
        for proveedor in proveedores:
            productos = Producto.obtener_por_proveedor(proveedor['_id'])
            proveedor['total_productos'] = len(productos)

    except Exception as e:
        flash(f'Error al obtener proveedores: {str(e)}', 'danger')

    return render_template('admin/proveedores.html', proveedores=proveedores)


@admin_bp.route('/proveedor/nuevo', methods=['GET', 'POST'])
@role_required(['admin'])
def nuevo_proveedor():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            email = request.form['email']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            categoria_productos = request.form['categoria_productos']

            proveedor = Proveedor(
                nombre=nombre,
                email=email,
                telefono=telefono,
                direccion=direccion,
                categoria_productos=categoria_productos
            )

            proveedor.guardar()
            flash('Proveedor agregado correctamente', 'success')
            return redirect(url_for('admin.proveedores'))
        except Exception as e:
            flash(f'Error al agregar proveedor: {str(e)}', 'danger')

    return render_template('admin/nuevo_proveedor.html')


@admin_bp.route('/proveedor/editar/<proveedor_id>', methods=['GET', 'POST'])
@role_required(['admin'])
def editar_proveedor(proveedor_id):
    try:
        proveedor = Proveedor.obtener_por_id(ObjectId(proveedor_id))

        if request.method == 'POST':
            nombre = request.form['nombre']
            email = request.form['email']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            categoria_productos = request.form['categoria_productos']

            proveedor_actualizado = Proveedor(
                nombre=nombre,
                email=email,
                telefono=telefono,
                direccion=direccion,
                categoria_productos=categoria_productos,
                _id=ObjectId(proveedor_id)
            )

            proveedor_actualizado.guardar()
            flash('Proveedor actualizado correctamente', 'success')
            return redirect(url_for('admin.proveedores'))

        return render_template('admin/editar_proveedor.html', proveedor=proveedor)

    except Exception as e:
        flash(f'Error al cargar proveedor: {str(e)}', 'danger')
        return redirect(url_for('admin.proveedores'))


@admin_bp.route('/proveedor/eliminar', methods=['POST'])
@role_required(['admin'])
def eliminar_proveedor():
    try:
        proveedor_id = request.form['proveedor_id']
        # Implementar eliminación lógica
        # Proveedor.eliminar(ObjectId(proveedor_id))
        flash('Proveedor eliminado correctamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar proveedor: {str(e)}', 'danger')

    return redirect(url_for('admin.proveedores'))


@admin_bp.route('/proveedor/productos/<proveedor_id>')
@role_required(['admin'])
def productos_proveedor(proveedor_id):
    try:
        proveedor = Proveedor.obtener_por_id(ObjectId(proveedor_id))
        productos = Producto.obtener_por_proveedor(ObjectId(proveedor_id))
        return render_template('admin/productos_proveedor.html',
                               proveedor=proveedor,
                               productos=productos)
    except Exception as e:
        flash(f'Error al obtener productos del proveedor: {str(e)}', 'danger')
        return redirect(url_for('admin.proveedores'))


@admin_bp.route('/clientes')
@role_required(['admin'])
def clientes():
    try:
        clientes = list(Usuario.obtener_todos_por_rol('cliente'))
        return render_template('admin/clientes.html', clientes=clientes)
    except Exception as e:
        flash(f'Error al obtener clientes: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/cliente/pedidos/<cliente_id>')
@role_required(['admin'])
def ver_pedidos_cliente(cliente_id):
    try:
        cliente = Usuario.obtener_por_id(ObjectId(cliente_id))
        if not cliente or cliente['rol'] != 'cliente':
            flash('Cliente no encontrado', 'danger')
            return redirect(url_for('admin.clientes'))

        pedidos = Pedido.obtener_por_cliente(ObjectId(cliente_id))

        return render_template('admin/pedidos_cliente.html',
                               cliente=cliente,
                               pedidos=pedidos)
    except Exception as e:
        flash(f'Error al obtener pedidos del cliente: {str(e)}', 'danger')
        return redirect(url_for('admin.clientes'))