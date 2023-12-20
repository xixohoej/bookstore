from be.model import error
from be.db_conn import *
import json
from sqlalchemy import and_


class Seller():

    def add_book(self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int):
        try:
            book_json = json.loads(book_json_str)
            if not user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)
            tmp = StoreDetail(
                store_id=store_id,
                book_id=book_id,
                stock_level=stock_level,
                price=book_json.get("price")
            )
            session.add(tmp)
            session.commit()
        except BaseException as e:
            return 530, f"{e}"
        return 200, "ok"

    def add_stock_level(self, user_id: str, store_id: str, book_id: str, add_stock_level: int):
        try:
            if not user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            cur = session.query(StoreDetail).filter(
                and_(StoreDetail.store_id == store_id, StoreDetail.book_id == book_id)).first()
            cur.stock_level = cur.stock_level + add_stock_level
            session.commit()
        except BaseException as e:
            return 530, f"{e}"
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            tmp = Store(user_id=user_id, store_id=store_id)
            session.add(tmp)
            session.commit()
        except BaseException as e:
            return 530, f"{e}"
        return 200, "ok"