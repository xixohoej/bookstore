import uuid

import jwt
import logging
import time
from sqlalchemy.exc import SQLAlchemyError
from be.model import error
from be.model.db_conn import User as aUser
from be.model.db_conn import *

# encode a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }


def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal},
        key=user_id,
        algorithm="HS256",
    )
    return encoded


# decode a JWT to a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }
def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User():
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        self.cur = session

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    def register(self, user_id: str, password: str):
        try:
            terminal = f"terminal_{uuid.uuid1()}"
            token = jwt_encode(user_id, terminal)

            tmp = self.cur.query(aUser).get(user_id)
            if tmp:
                return error.error_exist_user_id(user_id)

            self.cur.add(aUser(user_id=user_id, password=password, balance=0, token=token, terminal=terminal))
            self.cur.commit()

        except SQLAlchemyError:
            return error.error_exist_user_id(user_id)

        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        try:
            cursor = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            if cursor is None:
                return error.error_authorization_fail()
            db_token = cursor.token

            hex_str = r"\x" + bytes(token, encoding='utf-8').hex()
            if db_token != token and db_token != hex_str:
                return error.error_authorization_fail()

        except SQLAlchemyError:
            return error.error_authorization_fail()

        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        try:
            tmp = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            if tmp is None:
                return error.error_authorization_fail()

            if password != tmp.password:
                return error.error_authorization_fail()

        except SQLAlchemyError:
            return error.error_authorization_fail()

        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        try:
            token = ""
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""
            token = jwt_encode(user_id, terminal)
            cnt = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            cnt.token = token
            cnt.terminal = terminal
            self.cur.commit()

        except BaseException as e:
            return 530, f"{e}"

        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = f"terminal_{str(uuid.uuid1())}"
            dummy_token = jwt_encode(user_id, terminal)
            cnt = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            cnt.token = dummy_token
            cnt.terminal = terminal
            self.cur.commit()

        except BaseException as e:
            return 530, f"{e}"

        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message
            cnt = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            self.cur.delete(cnt)
            self.cur.commit()

        except BaseException as e:
            return 530, f"{e}"

        return 200, "ok"

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = f"terminal_{str(uuid.uuid1())}"
            token = jwt_encode(user_id, terminal)
            cnt = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            cnt.password = new_password
            cnt.token = token
            cnt.terminal = terminal
            self.cur.commit()
        except BaseException as e:
            return 530, f"{e}"
        return 200, "ok"

    def search_author(self, author: str, page: int) -> (int, [dict]):  # 200,'ok',list[{str,str,str,str,list,bytes}]
        if page < 1:
            return 200, []
        records = self.cur.execute(
            text(f"SELECT title,author,publisher,book_intro,tags "
            f"FROM book WHERE book_id in "
            f"(select book_id from \"SearchAuthor\" where author='{author}') LIMIT 10 OFFSET {10 * page - 10}")).fetchall()
        if len(records) == 0:
            return 200, []
        return self.helper(records)

    def search_book_intro(self, book_intro: str, page: int) -> (int, [dict]):
        if page < 1:
            return 200, []
        records = self.cur.execute(
            text(f"SELECT title,author,publisher,book_intro,tags "
                 f"FROM book WHERE book_id in "
                 f"(select book_id from \"SearchBookIntro\" where book_intro='{book_intro}') LIMIT 10 OFFSET {10 * page - 10}")).fetchall()
        if len(records) == 0:
            return 200, []
        return self.helper(records)

    def search_tags(self, tags: str, page: int) -> (int, [dict]):
        if page < 1:
            return 200, []
        records = self.cur.execute(
            text(f"SELECT title,author,publisher,book_intro,tags "
                 f"FROM book WHERE book_id in "
                 f"(select book_id from \"SearchTags\" where tags='{tags}') LIMIT 10 OFFSET {10 * page - 10}")).fetchall()
        if len(records) == 0:
            return 200, []
        return self.helper(records)

    def search_title(self, title: str, page: int) -> (int, [dict]):
        if page < 1:
            return 200, []
        records = self.cur.execute(
            text(f"SELECT title,author,publisher,book_intro,tags "
                 f"FROM book WHERE book_id in "
                 f"(select book_id from \"SearchTitle\" where title='{title}') LIMIT 10 OFFSET {10 * page - 10}")).fetchall()
        if len(records) == 0:
            return 200, []
        return self.helper(records)

    def search_author_in_store(self, author: str, store_id: str, page: int) -> (int, [dict]):
        if page < 1:
            return 200, []
        records = self.cur.execute(
            text(f"SELECT title,author,publisher,book_intro,tags "
                 f"FROM book WHERE book_id in "
                 f"(select book_id from \"SearchAuthor\" where author='{author}') and "
                 f"book_id in (select book_id from \"StoreDetail\" where store_id='{store_id}') LIMIT 10 OFFSET {10 * page - 10}")).fetchall()
        if len(records) == 0:
            return 200, []
        return self.helper(records)

    def search_book_intro_in_store(self, book_intro: str, store_id: str, page: int) -> (int, [dict]):
        if page < 1:
            return 200, []
        records = self.cur.execute(
            text(f"SELECT title,author,publisher,book_intro,tags "
                 f"FROM book WHERE book_id in "
                 f"(select book_id from \"SearchBookIntro\" where book_intro='{book_intro}') and "
                 f"book_id in (select book_id from \"StoreDetail\" where store_id='{store_id}') LIMIT 10 OFFSET {10 * page - 10}")).fetchall()
        if len(records) == 0:
            return 200, []
        return self.helper(records)

    def search_tags_in_store(self, tags: str, store_id: str, page: int) -> (int, [dict]):
        if page < 1:
            return 200, []
        records = self.cur.execute(
            text(f"SELECT title,author,publisher,book_intro,tags "
                 f"FROM book WHERE book_id in "
                 f"(select book_id from \"SearchTags\" where tags='{tags}') and "
                 f"book_id in (select book_id from \"StoreDetail\" where store_id='{store_id}') LIMIT 10 OFFSET {10 * page - 10}")).fetchall()
        if len(records) == 0:
            return 200, []
        return self.helper(records)

    def search_title_in_store(self, title: str, store_id: str, page: int) -> (int, [dict]):
        if page < 1:
            return 200, []
        records = self.cur.execute(
            text(f"SELECT title,author,publisher,book_intro,tags "
                 f"FROM book WHERE book_id in "
                 f"(select book_id from \"SearchTitle\" where title='{title}') and "
                 f"book_id in (select book_id from \"StoreDetail\" where store_id='{store_id}') LIMIT 10 OFFSET {10 * page - 10}")).fetchall()
        if len(records) == 0:
            return 200, []
        return self.helper(records)

    def helper(self, records):
        ret = [
            {'title': title, 'author': author, 'publisher': publisher,
             'book_intro': book_intro, 'tags': tags}
            for title, author, publisher, book_intro, tags in records
        ]
        return 200, ret

