from datetime import datetime
from app.services.database import get_db


class Pedido:
    def __init__(self, cliente_id, productos, estado="pendiente",
                 direccion_entrega=None, metodo_pago=None, _id=None):
        self.cliente_id = cliente_id
        self.productos = productos  # Lista de {producto_id, cantidad, precio_unitario}
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

        if self._id:
            db.pedidos.update_one(
                {"_id": self._id},
                {"$set": self.to_dict()}
            )
        else:
            self._id = db.pedidos.insert_one(self.to_dict()).inserted_id

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

    @classmethod
    def obtener_por_cliente(cls, cliente_id):
        return list(get_db().pedidos.find({"cliente_id": cliente_id}))

    @classmethod
    def obtener_por_id(cls, pedido_id):
        return get_db().pedidos.find_one({"_id": pedido_id})

    @classmethod
    def actualizar_estado(cls, pedido_id, nuevo_estado):
        get_db().pedidos.update_one(
            {"_id": pedido_id},
            {
                "$set": {
                    "estado": nuevo_estado,
                    "fecha_actualizacion": datetime.now()
                }
            }
        )