import uuid

import jwt
import logging
import time
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from be.model import error
from be.db_conn import User as aUser
from be.db_conn import *
import warnings
warnings.filterwarnings("ignore")

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


class User(): # 防止类名相同
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
            row = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            if row is None:
                return error.error_authorization_fail()
            db_token = cursor.token
            hex_str = r"\x" + bytes(token, encoding='utf-8').hex()
            if db_token != token and db_token != hex_str:
                return error.error_authorization_fail()
        except SQLAlchemyError:
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        user_one = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
        if user_one is None:
            return error.error_authorization_fail()

        if password != user_one.password:
            return error.error_authorization_fail()
        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        try:
            token = ""
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""
            token = jwt_encode(user_id, terminal)
            cursor = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            cursor.token = token
            cursor.terminal = terminal
            self.cur.commit()
        except SQLAlchemyError:
            return error.error_exist_user_id(user_id)
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = f"terminal_{str(uuid.uuid1())}"
            dummy_token = jwt_encode(user_id, terminal)
            cursor = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            cursor.token = dummy_token
            cursor.terminal = terminal
            self.cur.commit()
        except SQLAlchemyError:
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message
            cursor = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            self.cur.delete(cursor)
            self.cur.commit()
        except SQLAlchemyError:
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = f"terminal_{str(uuid.uuid1())}"
            token = jwt_encode(user_id, terminal)
            cursor = self.cur.query(aUser).filter(aUser.user_id == user_id).first()
            cursor.password = new_password
            cursor.token = token
            cursor.terminal = terminal
            self.cur.commit()
        except SQLAlchemyError:
            return error.error_exist_user_id(user_id)
        return 200, "ok"