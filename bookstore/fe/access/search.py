import requests
from urllib.parse import urljoin

class Search:
    def __init__(self, url_prefix):
        self.url_prefix = urljoin(url_prefix, "auth/")

    def search(self, endpoint, **kwargs) -> int:
        url = urljoin(self.url_prefix, endpoint)
        json_data = kwargs
        r = requests.post(url, json=json_data)
        return r.status_code

    def search_author(self, author: str, page: int) -> int:
        return self.search("search_author", author=author, page=page)

    def search_book_intro(self, book_intro: str, page: int) -> int:
        return self.search("search_book_intro", book_intro=book_intro, page=page)

    def search_tags(self, tags: str, page: int) -> int:
        return self.search("search_tags", tags=tags, page=page)

    def search_title(self, title: str, page: int) -> int:
        return self.search("search_title", title=title, page=page)

    def search_author_in_store(self, author: str, store_id: str, page: int) -> int:
        return self.search("search_author_in_store", author=author, store_id=store_id, page=page)

    def search_book_intro_in_store(self, book_intro: str, store_id: str, page: int) -> int:
        return self.search("search_book_intro_in_store", book_intro=book_intro, store_id=store_id, page=page)

    def search_tags_in_store(self, tags: str, store_id: str, page: int) -> int:
        return self.search("search_tags_in_store", tags=tags, store_id=store_id, page=page)

    def search_title_in_store(self, title: str, store_id: str, page: int) -> int:
        return self.search("search_title_in_store", title=title, store_id=store_id, page=page)
