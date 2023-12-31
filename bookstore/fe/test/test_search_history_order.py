import pytest
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
from fe.access.book import Book
import uuid
import random


class TestSearchOrder:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.buyer_id = f"test_search_order_buyer_id_{uuid.uuid1()}"
        self.password = self.buyer_id
        b = register_new_buyer(self.buyer_id, self.password)
        self.buyer = b

        self.buyer2_id = f"test_close_order_buyer2_id_{uuid.uuid1()}"
        self.password2 = self.buyer2_id
        b2 = register_new_buyer(self.buyer2_id, self.password2)
        self.buyer2 = b2
        yield

    def test_ok(self):
        order_num = random.randint(10, 20)
        for i in range(order_num):
            self.seller_id = f"test_search_order_seller_id_{uuid.uuid1()}"
            self.store_id = f"test_search_order_store_id_{uuid.uuid1()}"
            self.gen_book = GenBook(self.seller_id, self.store_id)
            self.seller = self.gen_book.seller
            ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False, max_book_count=5)
            self.buy_book_info_list = self.gen_book.buy_book_info_list
            assert ok

            self.total_price = 0
            for item in self.buy_book_info_list:
                book: Book = item[0]
                num = item[1]
                self.total_price = self.total_price + book.price * num
            code = self.buyer.add_funds(self.total_price + 99999)
            assert code == 200
            code, self.order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
            assert code == 200

            paystatus = random.randint(0, 3)
            if paystatus != 3:
                code = self.buyer.payment(self.order_id)
                assert code == 200
                if paystatus != 0:
                    code = self.seller.send_books(self.seller_id, self.order_id)
                    assert code == 200
                    if paystatus == 2:
                        code = self.buyer.receive_books(self.buyer_id, self.order_id)
                        assert code == 200
        code = self.buyer.search_order()
        assert code == 200

    def test_authorization_error(self):
        self.buyer.password = f"{self.buyer.password}_x"
        code = self.buyer.search_order()
        assert code != 200

        self.buyer_id = f"{self.buyer_id}_x"
        code = self.buyer.search_order()
        assert code != 200

    def test_no_history(self):
        code = self.buyer2.search_order()
        assert code == 200
