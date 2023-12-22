import uuid
import logging
from be.model.db_conn import *
from be.model import error
from sqlalchemy.orm import joinedload


class Buyer():

    def __init__(self):
        self.cur = session

    def new_order(self, user_id: str, store_id: str, book_id_and_count: [(str, int)]) -> (int, str, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + ("",)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + ("")

            order_uid = f"{user_id}_{store_id}_{uuid.uuid1()}"

            for book_id, count in book_id_and_count:
                store_detail = self.cur.query(StoreDetail).filter(
                    StoreDetail.store_id == store_id, StoreDetail.book_id == book_id
                ).first()

                if not store_detail:
                    return error.error_non_exist_book_id(book_id) + (order_uid,)

                stock_level = store_detail.stock_level

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_uid,)

                store_detail.stock_level -= count
                self.cur.add(OrderDetail(order_id=order_uid, book_id=book_id, count=count))

            self.cur.add(OrderToPay(order_id=order_uid, user_id=user_id, store_id=store_id, paytime=datetime.now()))
            self.cur.commit()

        except BaseException as e:
            logging.info(f"530, {e}")
            return 530, f"{e}", ""

        return 200, "ok", order_uid

    def payment(self, buyer_user_id: str, buyer_password: str, order_id: str) -> (int, str):
        try:
            order_to_pay = self.cur.query(OrderToPay).filter(OrderToPay.order_id == order_id).one_or_none()

            if not order_to_pay:
                return error.error_invalid_order_id(order_id)

            buyer_id, store_id = order_to_pay.user_id, order_to_pay.store_id

            if buyer_id != buyer_user_id:
                return error.error_authorization_fail()

            buyer = self.cur.query(User).filter(User.user_id == buyer_id).one_or_none()
            if not buyer:
                return error.error_non_exist_user_id(buyer_id)

            if buyer_password != buyer.password:
                return error.error_authorization_fail()

            store = self.cur.query(Store).filter(Store.store_id == store_id).one_or_none()
            if not store:
                return error.error_non_exist_store_id(store_id)

            seller_id = store.user_id
            if not user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            order_detail = self.cur.query(OrderDetail).filter(OrderDetail.order_id == order_id).all()
            total_price = sum(
                order_item.count * self.cur.query(StoreDetail).filter(
                    StoreDetail.store_id == store_id, StoreDetail.book_id == order_item.book_id
                ).first().price for order_item in order_detail
            )

            if buyer.balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            buyer.balance -= total_price
            seller = self.cur.query(User).filter(User.user_id == seller_id).one_or_none()
            if seller:
                seller.balance += total_price

            self.cur.add(
                Order(order_id=order_id, user_id=buyer_id, store_id=store_id, paytime=datetime.now(), status=0))
            self.cur.delete(order_to_pay)
            self.cur.commit()

        except BaseException as e:
            return 530, f"{e}"

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            user = self.cur.query(User).filter(User.user_id == user_id).first()

            if not user or user.password != password:
                return error.error_authorization_fail()

            user.balance += add_value
            self.cur.commit()

        except BaseException as e:
            return 530, f"{e}"

        return 200, "ok"

    def receive_books(self, buyer_id, order_id):
        try:
            order = self.cur.query(Order).filter(Order.order_id == order_id).first()

            if not order:
                return error.error_invalid_order_id(order_id)

            if order.status == 0:
                return error.error_order_unsent(order_id)
            elif order.status == 2:
                return error.error_order_received(order_id)

            if order.user_id != buyer_id:
                return error.error_authorization_fail()

            order.status = 2
            self.cur.commit()

        except BaseException as e:
            return 530, f"{e}"

        return 200, "ok"

    def check_order(self):
        orders_to_pay = self.cur.query(OrderToPay).options(joinedload(OrderToPay.order_details)).all()

        for order_to_pay in orders_to_pay:
            paytime = order_to_pay.paytime
            time_now = datetime.now()
            time_lag = (time_now - paytime).seconds

            if time_lag > 15 * 60:
                order_id, user_id, store_id = order_to_pay.order_id, order_to_pay.user_id, order_to_pay.store_id

                store = self.cur.query(Store).filter(Store.store_id == store_id).first()

                if not store:
                    return error.error_non_exist_store_id(store_id)

                for order_detail in order_to_pay.order_details:
                    book_id, count = order_detail.book_id, order_detail.count
                    book = self.cur.query(StoreDetail).filter(
                        StoreDetail.store_id == store_id, StoreDetail.book_id == book_id
                    ).first()

                    if book:
                        book.stock_level += count

                self.cur.add(Order(order_id=order_id, user_id=user_id, store_id=store_id, paytime=paytime, status=4))
                self.cur.delete(order_to_pay)
                self.cur.commit()
                return 200, "ok", "closed"

        return 200, "ok", None

    def close_order(self, user_id: str, password: str, order_id: str) -> (int, str):
        order = self.cur.query(Order).filter(Order.order_id == order_id).first()
        order_to_pay = self.cur.query(OrderToPay).filter(OrderToPay.order_id == order_id).first()

        if not order and not order_to_pay:
            return error.error_invalid_order_id(order_id)

        if order:
            status = order.status
            if status == 4:
                return error.error_order_closed(order_id)
            elif status == 1 or status == 2:
                return error.error_order_can_not_be_closed(order_id)

            buyer_id, store_id, flag = order.user_id, order.store_id, 0
        elif order_to_pay:
            buyer_id, store_id, flag = order_to_pay.user_id, order_to_pay.store_id, 3

        if buyer_id != user_id:
            return error.error_authorization_fail()

        buyer = self.cur.query(User).filter(User.user_id == buyer_id).first()
        if not buyer or password != buyer.password:
            return error.error_authorization_fail()

        store = self.cur.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            return error.error_non_exist_store_id(store_id)

        order_details = self.cur.query(OrderDetail).filter(OrderDetail.order_id == order_id).all()
        total_price = 0

        for order_detail in order_details:
            book_id, count = order_detail.book_id, order_detail.count
            book = self.cur.query(StoreDetail).filter(
                StoreDetail.store_id == store_id, StoreDetail.book_id == book_id
            ).first()

            if book:
                book.stock_level += count
                total_price += book.price * count

        if flag == 0:
            seller_id = store.user_id
            if not user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            seller = self.cur.query(User).filter(User.user_id == seller_id).first()
            if seller:
                seller.balance -= total_price
                buyer.balance += total_price
                order.status = 4
        elif flag == 3:
            paytime = order_to_pay.paytime
            self.cur.add(Order(order_id=order_id, user_id=buyer_id, store_id=store_id, paytime=paytime, status=4))
            self.cur.delete(order_to_pay)

        self.cur.commit()
        return 200, "ok"

    def search_order(self, user_id: str, password: str) -> (int, str, list):
        user = self.cur.query(User).filter(User.user_id == user_id).first()
        if not user or user.password != password:
            return 401, "authorization fail.", []

        historys = []

        for order_to_pay in self.cur.query(OrderToPay).all():
            order_id, status = order_to_pay.order_id, "未付款"
            details, total_price = [], 0

            for order_detail in self.cur.query(OrderDetail).filter(OrderDetail.order_id == order_id).all():
                book = self.cur.query(StoreDetail).filter(
                    StoreDetail.store_id == order_to_pay.store_id,
                    StoreDetail.book_id == order_detail.book_id
                ).first()

                price = book.price
                total_price += price * order_detail.count
                detail = {"book_id": order_detail.book_id, "count": order_detail.count, "single_price": price}
                details.append(detail)

            history = {"order_id": order_id, "user_id": order_to_pay.user_id, "store_id": order_to_pay.store_id,
                       "total_price": total_price, "order_detail": details, "paytime": order_to_pay.paytime,
                       "status": status}
            historys.append(history)

        for order in self.cur.query(Order).order_by(Order.paytime).all():
            order_id, status = order.order_id, order.status
            if status == 0:
                status = "paid, remain to be delivered"
            elif status == 1:
                status = "delivered"
            elif status == 2:
                status = "received"
            elif status == 4:
                status = "order closed"

            details, total_price = [], 0

            for order_detail in self.cur.query(OrderDetail).filter(OrderDetail.order_id == order_id).all():
                book = self.cur.query(StoreDetail).filter(
                    StoreDetail.store_id == order.store_id,
                    StoreDetail.book_id == order_detail.book_id
                ).first()

                price = book.price
                total_price += price * order_detail.count
                detail = {"book_id": order_detail.book_id, "count": order_detail.count, "single_price": price}
                details.append(detail)

            history = {"order_id": order_id, "user_id": order.user_id, "store_id": order.store_id,
                       "total_price": total_price, "order_detail": details, "paytime": order.paytime, "status": status}
            historys.append(history)

        return 200, "ok", historys

    def user_id_exist(self, user_id):
        return user_id_exist(user_id)

    def store_id_exist(self, store_id):
        return store_id_exist(store_id)
    
