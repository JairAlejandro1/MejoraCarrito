from datetime import datetime
from app.services.database import get_db


class Producto:
    def __init__(self, nombre, descripcion, precio, existencias,
                 categoria, proveedor_id, imagen_url=None, _id=None):
        self.nombre = nombre
        self.descripcion = descripcion
        self.precio = precio
        self.existencias = existencias
        self.categoria = categoria
        self.proveedor_id = proveedor_id
        self.imagen_url = imagen_url
        self._id = _id
        self.fecha_creacion = datetime.now()
        self.activo = True

    def guardar(self):
        db = get_db()
        if self._id:
            db.productos.update_one(
                {"_id": self._id},
                {"$set": self.to_dict()}
            )
        else:
            self._id = db.productos.insert_one(self.to_dict()).inserted_id
        return self._id

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "precio": self.precio,
            "existencias": self.existencias,
            "categoria": self.categoria,
            "proveedor_id": self.proveedor_id,
            "imagen_url": self.imagen_url,
            "fecha_creacion": self.fecha_creacion,
            "activo": self.activo
        }

    @classmethod
    def obtener_todos(cls):
        return list(get_db().productos.find({"activo": True}))

    @classmethod
    def obtener_por_id(cls, producto_id):
        return get_db().productos.find_one({"_id": producto_id, "activo": True})

    @classmethod
    def obtener_por_categoria(cls, categoria):
        return list(get_db().productos.find({"categoria": categoria, "activo": True}))

    @classmethod
    def actualizar_existencias(cls, producto_id, cantidad):
        get_db().productos.update_one(
            {"_id": producto_id},
            {"$inc": {"existencias": -cantidad}}
        )

    @classmethod
    def verificar_existencias(cls, producto_id, cantidad):
        producto = cls.obtener_por_id(producto_id)
        return producto and producto["existencias"] >= cantidad