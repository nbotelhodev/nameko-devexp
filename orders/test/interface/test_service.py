import pytest

from mock import call
from nameko.exceptions import RemoteError
from marshmallow.exceptions import ValidationError

from orders.models import Order, OrderDetail
from orders.schemas import OrderSchema, OrderDetailSchema


@pytest.fixture
def order(db_session):
    order = Order()
    db_session.add(order)
    db_session.commit()
    return order

@pytest.fixture
def order_details(db_session, order):
    db_session.add_all([
        OrderDetail(
            order=order, product_id="the_odyssey", price=99.51, quantity=1
        ),
        OrderDetail(
            order=order, product_id="the_enigma", price=30.99, quantity=8
        )
    ])
    db_session.commit()
    return order_details


def test_get_order(orders_rpc, order):
    response = orders_rpc.get_order(1)
    assert response['id'] == order.id

@pytest.mark.usefixtures('db_session')
def test_will_raise_when_order_not_found(orders_rpc):
    with pytest.raises(RemoteError) as err:
        orders_rpc.get_order(1)
    assert err.value.value == 'Order with id 1 not found'


@pytest.mark.usefixtures('db_session')
def test_can_create_order(orders_service, orders_rpc):
    order_details = [
        {
            'product_id': "the_odyssey",
            'price': 99.99,
            'quantity': 1
        },
        {
            'product_id': "the_enigma",
            'price': 5.99,
            'quantity': 8
        }
    ]
    new_order = orders_rpc.create_order(
        OrderDetailSchema(many=True).dump(order_details).data
    )
    assert new_order['id'] > 0
    assert len(new_order['order_details']) == len(order_details)
    assert [call(
        'order_created', {'order': {
            'id': 1,
            'order_details': [
                {
                    'price': '99.99',
                    'product_id': "the_odyssey",
                    'id': 1,
                    'quantity': 1
                },
                {
                    'price': '5.99',
                    'product_id': "the_enigma",
                    'id': 2,
                    'quantity': 8
                }
            ]}}
    )] == orders_service.event_dispatcher.call_args_list


@pytest.mark.usefixtures('db_session', 'order_details')
def test_can_update_order(orders_rpc, order):
    order_payload = OrderSchema().dump(order).data
    for order_detail in order_payload['order_details']:
        order_detail['quantity'] += 1

    updated_order = orders_rpc.update_order(order_payload)

    assert updated_order['order_details'] == order_payload['order_details']


def test_can_delete_order(orders_rpc, order, db_session):
    orders_rpc.delete_order(order.id)
    assert not db_session.query(Order).filter_by(id=order.id).count()


@pytest.fixture
def orders(db_session):
    for i in range(0, 10):
        db_session.add(Order(id=i))
        db_session.commit()
    return orders

def test_list_order(orders_rpc, orders):
    page=1
    page_size=10
    response = orders_rpc.list(page, page_size)
    assert response['page'] == 1
    assert response['page_size'] == 10
    assert response['total_pages'] == 1
    assert response['total_items'] == 10
    assert len(response['items']) == 10

    page=1
    page_size=5
    response = orders_rpc.list(page, page_size)
    assert response['page'] == 1
    assert response['page_size'] == 5
    assert response['total_pages'] == 2
    assert response['total_items'] == 10
    assert len(response['items']) == 5

    page=2
    page_size=5
    response = orders_rpc.list(page, page_size)
    assert response['page'] == 2
    assert response['page_size'] == 5
    assert response['total_pages'] == 2
    assert response['total_items'] == 10
    assert len(response['items']) == 5

    page=4
    page_size=3
    response = orders_rpc.list(page, page_size)
    assert response['page'] == 4
    assert response['page_size'] == 3
    assert response['total_pages'] == 4
    assert response['total_items'] == 10
    assert len(response['items']) == 1

    # no exists page
    page=1000
    page_size=3
    response = orders_rpc.list(page, page_size)
    assert response['page'] == 1000
    assert response['page_size'] == 3
    assert response['total_pages'] == 4
    assert response['total_items'] == 10
    assert len(response['items']) == 0

def test_list_order_no_orders(orders_rpc):
    page=1
    page_size=10
    response = orders_rpc.list(page, page_size)
    print(response)
    assert response['page'] == 1
    assert response['page_size'] == 10
    assert response['total_pages'] == 1
    assert response['total_items'] == 0
    assert len(response['items']) == 0
