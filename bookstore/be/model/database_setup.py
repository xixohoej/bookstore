import re
from sqlalchemy import create_engine, text, Column, String, Integer, ForeignKey, Text, DateTime, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List, Optional, Union
from datetime import datetime
import jieba.analyse
import sqlite3 as sqlite

Base = declarative_base()
DATABASE_URL = "postgresql://postgres:makimanoinu@localhost:5432/bookstore"
engine = create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)
session = DBSession()

class User(Base):
    __tablename__ = 'user'
    user_id: str = Column(String(128), primary_key=True)
    password: str = Column(String(128), nullable=False)
    balance: int = Column(Integer, nullable=False)
    token: str = Column(String(4000), nullable=False)
    terminal: str = Column(String(256), nullable=False)

class Store(Base):
    __tablename__ = 'store'
    store_id: str = Column(String(128), primary_key=True)
    user_id: str = Column(String(128), ForeignKey('user.user_id'), nullable=False)

class StoreDetail(Base):
    __tablename__ = 'StoreDetail'
    store_id: str = Column(String(128), ForeignKey('store.store_id'), primary_key=True)
    book_id: str = Column(String(128), ForeignKey('book.book_id'), primary_key=True)
    stock_level: int = Column(Integer, nullable=False)
    price: int = Column(Integer, nullable=False)

class Book(Base):
    __tablename__ = 'book'
    book_id: str = Column(String(128), primary_key=True)
    title: str = Column(String, nullable=False)
    author: str = Column(String)
    publisher: str = Column(String)
    original_title: Optional[Union[Text, None]] = Column(Text)
    translator: Optional[Union[Text, None]] = Column(Text)
    pub_year: Optional[Union[Text, None]] = Column(Text)
    pages: int = Column(Integer)
    original_price: Optional[Union[int, None]] = Column(Integer)
    currency_unit: Optional[Union[Text, None]] = Column(Text)
    binding: Optional[Union[Text, None]] = Column(Text)
    isbn: Optional[Union[Text, None]] = Column(Text)
    author_intro: Optional[Union[Text, None]] = Column(Text)
    book_intro: str = Column(String)
    content: Optional[Union[Text, None]] = Column(Text)
    tags: Optional[Union[str, None]] = Column(String)
    picture: Optional[LargeBinary] = Column(LargeBinary)

class Order(Base):
    __tablename__ = 'order'
    order_id: str = Column(String(1280), primary_key=True)
    user_id: str = Column(String(128), ForeignKey('user.user_id'), nullable=False)
    store_id: str = Column(String(128), ForeignKey('store.store_id'), nullable=False)
    paytime: Optional[datetime] = Column(DateTime, nullable=True)
    status: Optional[int] = Column(Integer, nullable=True)

class OrderToPay(Base):
    __tablename__ = 'OrderToPay'
    order_id: str = Column(String(1280), primary_key=True)
    user_id: str = Column(String(128), ForeignKey('user.user_id'), nullable=False)
    store_id: str = Column(String(128), ForeignKey('store.store_id'), nullable=False)
    paytime: Optional[datetime] = Column(DateTime, nullable=True)

class OrderDetail(Base):
    __tablename__ = 'OrderDetail'
    order_id: str = Column(String(1280), primary_key=True, nullable=False)
    book_id: str = Column(String(128), ForeignKey('book.book_id'), primary_key=True, nullable=False)
    count: int = Column(Integer, nullable=False)

class SearchTitle(Base):
    __tablename__ = 'SearchTitle'
    search_id: int = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    title: str = Column(String, primary_key=True, nullable=False)
    book_id: str = Column(String(128), ForeignKey('book.book_id'), nullable=False)


class SearchTags(Base):
    __tablename__ = 'SearchTags'
    search_id: int = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    tags: str = Column(String, primary_key=True, nullable=False)
    book_id: str = Column(String(128), ForeignKey('book.book_id'), nullable=False)

class SearchAuthor(Base):
    __tablename__ = 'SearchAuthor'
    search_id: int = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    author: str = Column(String, primary_key=True, nullable=False)
    book_id: str = Column(String(128), ForeignKey('book.book_id'), nullable=False)

class SearchBookIntro(Base):
    __tablename__ = 'SearchBookIntro'
    search_id: int = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    book_intro: str = Column(String, primary_key=True, nullable=False)
    book_id: str = Column(String(128), ForeignKey('book.book_id'), nullable=False)

class BookInit:
    id: str
    title: str
    author: str
    publisher: str
    original_title: str
    translator: str
    pub_year: str
    pages: int
    price: int
    binding: str
    isbn: str
    author_intro: str
    book_intro: str
    content: str
    tags: List[str]
    pictures: List[bytes]

    def __init__(self):
        self.tags = []
        self.pictures = []

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

# 插入 book 表的数据
conn = sqlite.connect("bookstore/fe/data/book.db")
cursor = conn.execute("SELECT id, title, author, publisher, original_title, "
                      "translator, pub_year, pages, price, currency_unit, "
                      "binding, isbn, author_intro, book_intro, content, tags, picture FROM book ORDER BY id")
rows = cursor.fetchall()

book_objects = []
for row in rows:
    book_data = dict(zip(Book.__table__.columns.keys(), row))
    book_data['tags'] = [tag.strip() for tag in book_data['tags'].split("\n") if tag.strip()]
    book_objects.append(book_data)

session.bulk_insert_mappings(Book, book_objects)
session.commit()

# 插入 SearchTags 表的数据
rows = session.execute(text("SELECT book_id, tags FROM book;")).fetchall()
for row in rows[1:]:
    tags = [tag.strip() for tag in row.tags.replace("'", "").replace("[", "").replace("]", "").split(", ") if tag.strip()]
    for tag in tags:
        try:
            session.execute(
                text(f"INSERT into \"SearchTags\"(tags, book_id) VALUES (:tags, :book_id)"),
                {'tags': tag, 'book_id': int(row.book_id)}
            )
        except Exception as e:
            print(f"Error inserting into SearchTags: {e}")

# 插入 SearchAuthor 表的数据
rows = session.execute(text("SELECT book_id, author FROM book;")).fetchall()
for i in rows:
    tmp = i.author
    if tmp is None:
        authors = ['Unknown']
    else:
        tmp = re.sub(r'[\(\[\{（【][^)）】]*[\)\]\{\】\）]\s?', '', tmp)
        tmp = re.sub(r'[^\w\s]', '', tmp)
        authors = [tmp[:k] for k in range(1, len(tmp) + 1) if tmp[k - 1] != '']

    for author in authors:
        try:
            session.execute(
                text(f"INSERT into \"SearchAuthor\"(author, book_id) VALUES (:author, :book_id)"),
                {'author': author, 'book_id': int(i.book_id)}
            )
        except Exception as e:
            print(f"Error inserting into SearchAuthor: {e}")

# 插入 SearchTitle 表的数据
rows = session.execute(text("SELECT book_id, title FROM book;")).fetchall()
for i in rows:
    tmp = i.title
    tmp = re.sub(r'[\(\[\{（【][^)）】]*[\)\]\{\】\）]\s?', '', tmp)
    tmp = re.sub(r'[^\w\s]', '', tmp)

    seg_list = [k for k in jieba.cut_for_search(tmp) if k != ''] + [tmp]

    for j in seg_list:
        if j and j.strip():
            try:
                session.execute(
                    text(f"INSERT into \"SearchTitle\"(title, book_id) VALUES (:title, :book_id)"),
                    {'title': j, 'book_id': int(i.book_id)}
                )
            except Exception as e:
                print(f"Error inserting into SearchTitle: {e}")

# 插入 SearchBookIntro 表的数据
rows = session.execute(text("SELECT book_id, book_intro FROM book;")).fetchall()
for i in rows:
    tmp = i.book_intro
    if tmp is not None:
        keywords_textrank = jieba.analyse.textrank(tmp)
        for j in keywords_textrank:
            try:
                session.execute(
                    text(f"INSERT into \"SearchBookIntro\"(book_intro, book_id) VALUES (:book_intro, :book_id)"),
                    {'book_intro': j, 'book_id': int(i.book_id)}
                )
            except Exception as e:
                print(f"Error inserting into SearchBookIntro: {e}")

session.commit()
session.close()