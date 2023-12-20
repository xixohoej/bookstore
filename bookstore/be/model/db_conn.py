from bookstore.database_setup import *

def user_id_exist(user_id):
    cursor = session.query(User).filter(User.user_id == user_id).first()
    if cursor is None:
        return False
    else:
        return True

def book_id_exist(store_id, book_id):
    cursor = session.query(StoreDetail).filter(StoreDetail.store_id == store_id,
                                                StoreDetail.book_id == book_id).first()
    if cursor is None:
        return False
    else:
        return True

def store_id_exist(store_id):
    cursor = session.query(Store).filter(Store.store_id == store_id).first()
    if cursor is None:
        return False
    else:
        return True
