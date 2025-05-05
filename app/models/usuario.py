from datetime import datetime
import bcrypt
from app.services.database import get_db


class Usuario:
    def __init__(self, nombre, email, password, rol="cliente",
                 direccion=None, telefono=None, _id=None):
        self.nombre = nombre
        self.email = email
        self.password = self._hash_password(password) if password else None
        self.rol = rol
        self.direccion = direccion
        self.telefono = telefono
        self._id = _id
        self.fecha_registro = datetime.now()
        self.activo = True

    def _hash_password(self, password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    def verificar_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password)

    def guardar(self):
        db = get_db()
        usuario_dict = self.to_dict()

        if self._id:
            db.usuarios.update_one(
                {"_id": self._id},
                {"$set": usuario_dict}
            )
        else:
            self._id = db.usuarios.insert_one(usuario_dict).inserted_id

        return self._id

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "email": self.email,
            "password": self.password,
            "rol": self.rol,
            "direccion": self.direccion,
            "telefono": self.telefono,
            "fecha_registro": self.fecha_registro,
            "activo": self.activo
        }

    @classmethod
    def obtener_por_email(cls, email):
        return get_db().usuarios.find_one({"email": email, "activo": True})

    @classmethod
    def obtener_por_id(cls, usuario_id):
        return get_db().usuarios.find_one({"_id": usuario_id, "activo": True})

    @classmethod
    def obtener_todos(cls):
        return list(get_db().usuarios.find({"activo": True}))

    @classmethod
    def obtener_todos_por_rol(cls, rol):
        return get_db().usuarios.find({"rol": rol, "activo": True})

    @classmethod
    def eliminar(cls, usuario_id):
        """
        Eliminación lógica de un usuario
        """
        get_db().usuarios.update_one(
            {"_id": usuario_id},
            {"$set": {"activo": False}}
        )