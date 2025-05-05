from datetime import datetime
from app.services.database import get_db
from bson.objectid import ObjectId


class Producto:
    def __init__(self, nombre, descripcion, precio, existencias,
                 categoria, proveedor_id, imagen_url=None, _id=None):
        self.nombre = nombre
        self.descripcion = descripcion
        self.precio = precio
        self.existencias = existencias
        self.categoria = categoria
        self.proveedor_id = proveedor_id  # ID del proveedor que suministra este producto
        self.imagen_url = imagen_url
        self._id = _id
        self.fecha_creacion = datetime.now()
        self.fecha_actualizacion = self.fecha_creacion
        self.activo = True

    def guardar(self):
        db = get_db()
        self.fecha_actualizacion = datetime.now()

        producto_dict = self.to_dict()

        if self._id:
            db.productos.update_one(
                {"_id": self._id},
                {"$set": producto_dict}
            )
        else:
            self._id = db.productos.insert_one(producto_dict).inserted_id
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
            "fecha_actualizacion": self.fecha_actualizacion,
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
    def obtener_por_proveedor(cls, proveedor_id):
        return list(get_db().productos.find({"proveedor_id": proveedor_id, "activo": True}))

    @classmethod
    def actualizar_existencias(cls, producto_id, cantidad_cambio):
        """
        Actualiza el inventario de un producto
        Si cantidad_cambio es negativo, reduce el inventario
        Si cantidad_cambio es positivo, aumenta el inventario
        """
        get_db().productos.update_one(
            {"_id": producto_id},
            {"$inc": {"existencias": cantidad_cambio}}
        )

    @classmethod
    def actualizar_inventario(cls, producto_id, nueva_cantidad):
        """
        Establece el inventario a un valor específico
        """
        get_db().productos.update_one(
            {"_id": producto_id},
            {"$set": {"existencias": nueva_cantidad}}
        )

    @classmethod
    def verificar_existencias(cls, producto_id, cantidad):
        """
        Verifica si hay suficientes existencias del producto
        """
        producto = cls.obtener_por_id(producto_id)
        return producto and producto["existencias"] >= cantidad

    @classmethod
    def eliminar(cls, producto_id):
        """
        Eliminación lógica de un producto
        """
        get_db().productos.update_one(
            {"_id": producto_id},
            {"$set": {"activo": False}}
        )