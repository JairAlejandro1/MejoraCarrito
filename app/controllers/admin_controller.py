from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.producto import Producto
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario
from app.models.pedido import Pedido
from app.auth.auth import role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@role_required(['admin'])
def dashboard():
    total_productos = len(Producto.obtener_todos())
    total_clientes = len(list(Usuario.obtener_todos_por_rol('cliente')))
    total_pedidos = len(list(Pedido.obtener_todos()))

    return render_template('admin/dashboard.html',
                           total_productos=total_productos,
                           total_clientes=total_clientes,
                           total_pedidos=total_pedidos)


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
        imagen_url = request.form['imagen_url']

        producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            existencias=existencias,
            categoria=categoria,
            proveedor_id=proveedor_id,
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
    producto = Producto.obtener_por_id(producto_id)

    if request.method == 'POST':
        # Actualizar producto
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        existencias = int(request.form['existencias'])
        categoria = request.form['categoria']
        proveedor_id = request.form['proveedor_id']
        imagen_url = request.form['imagen_url']

        producto_actualizado = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            existencias=existencias,
            categoria=categoria,
            proveedor_id=proveedor_id,
            imagen_url=imagen_url,
            _id=producto_id
        )

        producto_actualizado.guardar()
        flash('Producto actualizado correctamente', 'success')
        return redirect(url_for('admin.productos'))

    proveedores = Proveedor.obtener_todos()
    return render_template('admin/editar_producto.html',
                           producto=producto,
                           proveedores=proveedores)


@admin_bp.route('/pedidos')
@role_required(['admin'])
def pedidos():
    pedidos = Pedido.obtener_todos()
    return render_template('admin/pedidos.html', pedidos=pedidos)


@admin_bp.route('/pedido/<pedido_id>')
@role_required(['admin'])
def detalle_pedido(pedido_id):
    pedido = Pedido.obtener_por_id(pedido_id)
    return render_template('admin/detalle_pedido.html', pedido=pedido)


@admin_bp.route('/pedido/actualizar/<pedido_id>', methods=['POST'])
@role_required(['admin'])
def actualizar_estado_pedido(pedido_id):
    nuevo_estado = request.form['estado']
    Pedido.actualizar_estado(pedido_id, nuevo_estado)
    flash('Estado del pedido actualizado correctamente', 'success')
    return redirect(url_for('admin.pedidos'))


@admin_bp.route('/proveedores')
@role_required(['admin'])
def proveedores():
    proveedores = Proveedor.obtener_todos()
    return render_template('admin/proveedores.html', proveedores=proveedores)


@admin_bp.route('/proveedor/nuevo', methods=['GET', 'POST'])
@role_required(['admin'])
def nuevo_proveedor():
    if request.method == 'POST':
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

    return render_template('admin/nuevo_proveedor.html')