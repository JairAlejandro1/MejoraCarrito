from flask import Flask, current_app, g, request, session, render_template
import traceback
import logging
import os
import sys


def setup_debugging(app):
    """
    Configure debugging tools for Flask application

    Args:
        app: Flask application instance
    """
    # Set up logging
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Configure file handler
    file_handler = logging.FileHandler('logs/app.log')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    # Add request logger
    @app.before_request
    def log_request():
        app.logger.debug(f"Request: {request.method} {request.path}")
        app.logger.debug(f"Request args: {request.args}")
        if 'usuario_id' in session:
            app.logger.debug(f"User in session: {session.get('usuario_id')}")

    # Add response logger
    @app.after_request
    def log_response(response):
        app.logger.debug(f"Response status: {response.status_code}")
        return response

    # Add error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Unhandled exception: {str(e)}")
        app.logger.error(traceback.format_exc())

        # Custom error page with debug info in development
        if app.debug:
            error_details = {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc(),
                'session': {k: v for k, v in session.items()},
                'request': {
                    'path': request.path,
                    'method': request.method,
                    'args': request.args,
                    'form': request.form,
                }
            }
            return render_template('error_debug.html', error=error_details), 500

        # Standard error page in production
        return render_template('error.html',
                               error="An unexpected error occurred",
                               title="Error",
                               message="Our team has been notified of this issue."), 500


def debug_usuario(usuario_id):
    """
    Debug helper function to check a user by ID

    Args:
        usuario_id: User ID to check
    """
    from app.models.usuario import Usuario
    from bson.objectid import ObjectId

    try:
        # Try to convert to ObjectId
        oid = ObjectId(usuario_id)
        current_app.logger.debug(f"Valid ObjectId: {oid}")

        # Try to fetch user
        usuario = Usuario.obtener_por_id(oid)

        if usuario:
            current_app.logger.debug(f"User found: {usuario.get('nombre')} / {usuario.get('email')}")
            current_app.logger.debug(f"User role: {usuario.get('rol')}")
            return {
                'success': True,
                'usuario': {
                    'id': str(usuario.get('_id')),
                    'nombre': usuario.get('nombre'),
                    'email': usuario.get('email'),
                    'rol': usuario.get('rol')
                }
            }
        else:
            current_app.logger.debug(f"No user found with id {usuario_id}")
            return {
                'success': False,
                'error': 'User not found'
            }
    except Exception as e:
        current_app.logger.error(f"Error checking user {usuario_id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }