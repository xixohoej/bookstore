import uuid
import logging
from bookstore.be.model.db_conn import *
from bookstore.be.model import error


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
            return 530, f"{3}", ""

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
