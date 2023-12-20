import bookstore.database_setup as ds

def user_id_exist(user_id):
    cursor = ds.session.query(ds.User).filter(ds.User.user_id == user_id).first()
    if (cursor is None):
        return False
    else:
        return True

def book_id_exist(store_id, book_id):
    cursor = ds.session.query(ds.StoreDetail).filter(ds.StoreDetail.store_id == store_id,
                                                ds.StoreDetail.book_id == book_id).first()
    if (cursor is None):
        return False
    else:
        return True

def store_id_exist(store_id):
    cursor = ds.session.query(ds.Store).filter(ds.Store.store_id == store_id).first()
    if (cursor is None):
        return False
    else:
        return True
