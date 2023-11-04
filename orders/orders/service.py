from nameko.events import EventDispatcher
from nameko.rpc import rpc
from nameko_sqlalchemy import DatabaseSession
from sqlalchemy import select, func
from math import ceil
from orders.exceptions import NotFound
from orders.models import DeclarativeBase, Order, OrderDetail
from orders.schemas import OrderSchema

class OrdersService:
    name = 'orders'

    db = DatabaseSession(DeclarativeBase)
    event_dispatcher = EventDispatcher()

    @rpc
    def list(self, page, page_size):
        limit = page_size * page
        offset = (page - 1) * page_size

        total_items = self.db.scalar(select(func.count()).select_from(Order))
        items = self.db.scalars(
            select(Order).limit(limit).offset(offset)).all()

        total_pages = (1 if total_items == 0 else ceil(total_items / page_size))

        return {'page': page,
                'page_size': page_size,
                'total_items': total_items,
                'total_pages': total_pages,
                'items': OrderSchema().dump(items, many=True).data}

    @rpc
    def get_order(self, order_id):
        order = self.db.query(Order).get(order_id)

        if not order:
            raise NotFound('Order with id {} not found'.format(order_id))

        return OrderSchema().dump(order).data

    @rpc
    def create_order(self, order_details):
        order = Order(
            order_details=[
                OrderDetail(
                    product_id=order_detail['product_id'],
                    price=order_detail['price'],
                    quantity=order_detail['quantity']
                )
                for order_detail in order_details
            ]
        )
        self.db.add(order)
        self.db.commit()

        order = OrderSchema().dump(order).data

        self.event_dispatcher('order_created', {
            'order': order,
        })

        return order

    @rpc
    def update_order(self, order):
        order_details = {
            order_details['id']: order_details
            for order_details in order['order_details']
        }

        order = self.db.query(Order).get(order['id'])

        for order_detail in order.order_details:
            order_detail.price = order_details[order_detail.id]['price']
            order_detail.quantity = order_details[order_detail.id]['quantity']

        self.db.commit()
        return OrderSchema().dump(order).data

    @rpc
    def delete_order(self, order_id):
        order = self.db.query(Order).get(order_id)
        self.db.delete(order)
        self.db.commit()

    @rpc 
    def get_order_by_product_id(self, _product_id):
        order = self.db.query(OrderDetail).filter_by(product_id=_product_id).first()
        return OrderSchema().dump(order).data
