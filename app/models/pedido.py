from datetime import datetime
from app.services.database import get_db
from bson.objectid import ObjectId
from app.models.producto import Producto


class Pedido:
    def __init__(self, cliente_id, productos, estado="pendiente",
                 direccion_entrega=None, metodo_pago=None, _id=None):
        self.cliente_id = cliente_id

        # Asegurar que los IDs de producto sean string para evitar el error de len()
        for producto in productos:
            if 'producto_id' in producto and isinstance(producto['producto_id'], ObjectId):
                producto['producto_id'] = str(producto['producto_id'])

        self.productos = productos  # Lista de {producto_id, nombre, cantidad, precio_unitario}
        self.estado = estado  # pendiente, pagado, enviado, entregado, cancelado
        self.direccion_entrega = direccion_entrega
        self.metodo_pago = metodo_pago
        self._id = _id
        self.fecha_creacion = datetime.now()
        self.fecha_actualizacion = self.fecha_creacion

    def calcular_total(self):
        return sum(item["precio_unitario"] * item["cantidad"] for item in self.productos)

    def guardar(self):
        db = get_db()
        self.fecha_actualizacion = datetime.now()
        pedido_dict = self.to_dict()

        if self._id:
            db.pedidos.update_one(
                {"_id": self._id},
                {"$set": pedido_dict}
            )
        else:
            self._id = db.pedidos.insert_one(pedido_dict).inserted_id

        return self._id

    def to_dict(self):
        return {
            "cliente_id": self.cliente_id,
            "productos": self.productos,
            "estado": self.estado,
            "direccion_entrega": self.direccion_entrega,
            "metodo_pago": self.metodo_pago,
            "fecha_creacion": self.fecha_creacion,
            "fecha_actualizacion": self.fecha_actualizacion,
            "total": self.calcular_total()
        }

    @staticmethod
    def _stringify_object_ids(data):
        """
        Recursively convert all ObjectId instances to strings in a dictionary or list
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, ObjectId):
                    data[key] = str(value)
                elif isinstance(value, (dict, list)):
                    Pedido._stringify_object_ids(value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, ObjectId):
                    data[i] = str(item)
                elif isinstance(item, (dict, list)):
                    Pedido._stringify_object_ids(item)
        return data

    @classmethod
    def obtener_por_cliente(cls, cliente_id):
        return list(get_db().pedidos.find({"cliente_id": cliente_id}).sort("fecha_creacion", -1))

    @classmethod
    def obtener_por_id(cls, pedido_id):
        """
        Obtener un pedido por su ID asegurando que los ObjectIds son manejados correctamente
        """
        pedido = get_db().pedidos.find_one({"_id": pedido_id})

        if pedido:
            # Convert all ObjectIds to strings for safe handling
            cls._stringify_object_ids(pedido)

        return pedido

    @classmethod
    def obtener_todos(cls):
        return list(get_db().pedidos.find().sort("fecha_creacion", -1))

    @classmethod
    def obtener_por_proveedor(cls, proveedor_id):
        """
        Encuentra pedidos que contienen productos del proveedor especificado
        """
        # Primero, encontrar todos los productos de este proveedor
        productos_proveedor = list(Producto.obtener_por_proveedor(proveedor_id))
        ids_productos = [str(p["_id"]) for p in productos_proveedor]

        # Buscar todos los pedidos que contengan productos de este proveedor
        pedidos = []
        for pedido in get_db().pedidos.find():
            # Contar productos de este proveedor en el pedido
            productos_proveedor_en_pedido = 0
            total_proveedor = 0

            for item in pedido.get("productos", []):
                # Obtener producto_id y convertir a string si es necesario
                item_producto_id = item.get("producto_id")
                if isinstance(item_producto_id, ObjectId):
                    item_producto_id = str(item_producto_id)

                if item_producto_id in ids_productos:
                    productos_proveedor_en_pedido += 1
                    total_proveedor += item.get("precio_unitario", 0) * item.get("cantidad", 0)

            # Si hay al menos un producto de este proveedor, incluir el pedido
            if productos_proveedor_en_pedido > 0:
                pedido["productos_proveedor"] = productos_proveedor_en_pedido
                pedido["total_proveedor"] = total_proveedor
                pedidos.append(pedido)

        return sorted(pedidos, key=lambda x: x["fecha_creacion"], reverse=True)

    @classmethod
    def actualizar_estado(cls, pedido_id, nuevo_estado):
        """
        Actualiza el estado de un pedido
        Si el estado es 'cancelado', revierte las existencias de los productos
        """
        pedido = cls.obtener_por_id(pedido_id)

        # Si el estado es cancelado y el pedido no estaba cancelado previamente
        if nuevo_estado == 'cancelado' and pedido['estado'] != 'cancelado':
            # Revertir las existencias (aumentarlas nuevamente)
            for item in pedido['productos']:
                try:
                    # Convierte producto_id a ObjectId si es string
                    producto_id = item['producto_id']
                    if isinstance(producto_id, str):
                        producto_id = ObjectId(producto_id)

                    cantidad = item['cantidad']
                    Producto.restituir_existencias(producto_id, cantidad)  # Aumenta las existencias
                except Exception as e:
                    print(f"Error al revertir existencias: {str(e)}")

        # Actualizar el estado
        get_db().pedidos.update_one(
            {"_id": pedido_id},
            {
                "$set": {
                    "estado": nuevo_estado,
                    "fecha_actualizacion": datetime.now()
                }
            }
        )
        return True