from flask import Blueprint, request, session, redirect, url_for, render_template, flash, current_app as app
from app.models.usuario import Usuario
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                flash('Por favor inicia sesión para acceder a esta página', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            if 'rol' not in session or session['rol'] not in roles:
                flash('No tienes permiso para acceder a esta página', 'danger')
                return redirect(url_for('main.index'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_data = Usuario.obtener_por_email(email)

        if user_data:
            usuario = Usuario(
                nombre=user_data['nombre'],
                email=user_data['email'],
                password=None,
                rol=user_data['rol'],
                _id=user_data['_id']
            )
            usuario.password = user_data['password']

            if usuario.verificar_password(password):
                session['usuario_id'] = str(usuario._id)
                session['nombre'] = usuario.nombre
                session['email'] = usuario.email
                session['rol'] = usuario.rol

                if usuario.rol == 'proveedor':
                    session['proveedor_id'] = str(user_data.get('proveedor_id', ''))

                flash(f'Bienvenido de nuevo, {usuario.nombre}!', 'success')

                # Redirigir según el rol
                if usuario.rol == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif usuario.rol == 'cliente':
                    return redirect(url_for('cliente.perfil'))
                elif usuario.rol == 'proveedor':
                    return redirect(url_for('proveedor.dashboard'))
                else:
                    return redirect(url_for('main.index'))

        flash('Credenciales incorrectas. Por favor intenta de nuevo.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        direccion = request.form['direccion']
        telefono = request.form['telefono']

        # Verificar si el email ya está registrado
        if Usuario.obtener_por_email(email):
            flash('Este email ya está registrado. Por favor usa otro.', 'danger')
            return render_template('auth/registro.html')

        # Crear nuevo usuario (cliente)
        usuario = Usuario(
            nombre=nombre,
            email=email,
            password=password,
            rol='cliente',
            direccion=direccion,
            telefono=telefono
        )

        usuario.guardar()
        flash('Registro exitoso! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html')


@auth_bp.route('/setup-admin', methods=['GET', 'POST'])
def setup_admin():
    # Verificar si ya existe un administrador
    admin_exists = Usuario.obtener_por_rol('admin')

    if admin_exists and len(list(admin_exists)) > 0:
        flash('Ya existe un administrador en el sistema', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        telefono = request.form['telefono']
        direccion = request.form.get('direccion', 'Administración Central')

        # Verificar si el email ya está registrado
        if Usuario.obtener_por_email(email):
            flash('Este email ya está registrado. Por favor usa otro.', 'danger')
            return render_template('auth/setup_admin.html')

        # Crear el usuario administrador
        usuario = Usuario(
            nombre=nombre,
            email=email,
            password=password,
            rol='admin',  # Asignar rol de administrador
            direccion=direccion,
            telefono=telefono
        )

        usuario.guardar()
        flash('¡Administrador creado con éxito! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/setup_admin.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('main.index'))