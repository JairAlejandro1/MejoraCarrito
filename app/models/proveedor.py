from datetime import datetime
from app.services.database import get_db


class Proveedor:
    def __init__(self, nombre, email, telefono, direccion,
                 categoria_productos, _id=None):
        self.nombre = nombre
        self.email = email
        self.telefono = telefono
        self.direccion = direccion
        self.categoria_productos = categoria_productos
        self._id = _id
        self.fecha_registro = datetime.now()
        self.activo = True

    def guardar(self):
        db = get_db()
        if self._id:
            db.proveedores.update_one(
                {"_id": self._id},
                {"$set": self.to_dict()}
            )
        else:
            self._id = db.proveedores.insert_one(self.to_dict()).inserted_id
        return self._id

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "email": self.email,
            "telefono": self.telefono,
            "direccion": self.direccion,
            "categoria_productos": self.categoria_productos,
            "fecha_registro": self.fecha_registro,
            "activo": self.activo
        }

    @classmethod
    def obtener_todos(cls):
        return list(get_db().proveedores.find({"activo": True}))

    @classmethod
    def obtener_por_id(cls, proveedor_id):
        return get_db().proveedores.find_one({"_id": proveedor_id, "activo": True})