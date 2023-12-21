from bookstore.be.model import error
from bookstore.be.model.db_conn import *
import json
from sqlalchemy import and_


class Seller():
    def __init__(self):
        self.cur = session

    def add_book(self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int):
        try:
            book_json = json.loads(book_json_str)
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)
            tmp = StoreDetail(
                store_id=store_id,
                book_id=book_id,
                stock_level=stock_level,
                price=book_json.get("price")
            )
            self.cur.add(tmp)
            self.cur.commit()
        except BaseException as e:
            return 530, f"{e}"
        return 200, "ok"

    def add_stock_level(self, user_id: str, store_id: str, book_id: str, add_stock_level: int):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            cur = self.cur.query(StoreDetail).filter(
                and_(StoreDetail.store_id == store_id, StoreDetail.book_id == book_id)).first()
            cur.stock_level = cur.stock_level + add_stock_level
            self.cur.commit()
        except BaseException as e:
            return 530, f"{e}"
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            tmp = Store(user_id=user_id, store_id=store_id)
            self.cur.add(tmp)
            self.cur.commit()
        except BaseException as e:
            return 530, f"{e}"
        return 200, "ok"

    def user_id_exist(self, user_id):
        return user_id_exist(user_id)
    def store_id_exist(self, store_id):
        return store_id_exist(store_id)

    def book_id_exist(self, store_id, book_id):
        return book_id_exist(store_id, book_id)
