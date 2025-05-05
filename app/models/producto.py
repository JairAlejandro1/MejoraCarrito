from datetime import datetime
from app.services.database import get_db
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError


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
    def verificar_y_reservar(cls, producto_id, cantidad):
        """
        Verifica y actualiza el inventario atómicamente.
        Retorna True si se actualizó con éxito, False si no hay suficientes existencias.
        """
        try:
            db = get_db()
            # Operación atómica: busca y actualiza en un solo paso
            result = db.productos.find_one_and_update(
                {
                    "_id": producto_id,
                    "existencias": {"$gte": cantidad},  # Verifica si hay suficientes existencias
                    "activo": True
                },
                {"$inc": {"existencias": -cantidad}},  # Reduce las existencias
                return_document=True  # Retorna el documento después de la actualización
            )

            # Si result es None, significa que no se encontró un producto con suficientes existencias
            return result is not None

        except PyMongoError as e:
            print(f"Error al actualizar inventario: {str(e)}")
            return False

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
    def restituir_existencias(cls, producto_id, cantidad):
        """
        Devuelve productos al inventario (por ejemplo, cuando se cancela un pedido)
        """
        get_db().productos.update_one(
            {"_id": producto_id},
            {"$inc": {"existencias": cantidad}}
        )

    @classmethod
    def eliminar(cls, producto_id):
        """
        Eliminación lógica de un producto
        """
        get_db().productos.update_one(
            {"_id": producto_id},
            {"$set": {"activo": False}}
        )