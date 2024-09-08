import os
from typing import Optional
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin, current_user
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Text, Integer, MetaData


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })


db = SQLAlchemy(model_class=Base)


class Genre(db.Model):
    __tablename__ = 'genres'

    id = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    books = relationship('Book', secondary='books_has_genres', back_populates='genres', overlaps='books_genres')

    def __repr__(self):
        return '<Genre %r>' % self.name


class Books_has_Genres(db.Model):
    __tablename__ = 'books_has_genres'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    books_id: Mapped[int] = mapped_column(Integer, ForeignKey('books.id', ondelete='CASCADE'))
    genres_id: Mapped[int] = mapped_column(Integer, ForeignKey('genres.id', ondelete='CASCADE'))

    book = relationship('Book', overlaps='books,genres')
    genre = relationship('Genre', overlaps='books')


class Status(db.Model):
    __tablename__ = 'statuses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status_name: Mapped[str] = mapped_column(String(50))

    def __repr__(self):
        return '<Review: %r>' % self.status_name


class Role(db.Model):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)

    def __repr__(self):
        return '<User: %r>' % self.role_name


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    login: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)

    role: Mapped["Role"] = relationship()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return ' '.join([self.last_name, self.first_name, self.middle_name or ''])

    def __repr__(self):
        return '<User %r>' % self.login

    @property
    def is_admin(self):
        return self.role_id == 1

    @property
    def is_moder(self):
        return self.role_id == 2

    def can(self, action):
        users_policy = UserPolicy()
        method = getattr(users_policy, action, None)
        if method is not None:
            return method()
        return False


class Book(db.Model):
    __tablename__ = 'books'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    rating_sum: Mapped[int] = mapped_column(default=0)
    rating_num: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    year: Mapped[int] = mapped_column(mysql.YEAR)
    publisher: Mapped[str] = mapped_column(String(100))
    amount: Mapped[int] = mapped_column(Integer)
    author: Mapped[str] = mapped_column(String(100))
    cover_id: Mapped[str] = mapped_column(String(100), ForeignKey("covers.id", ondelete='CASCADE'))

    reviews = relationship('Review', overlaps='book')
    genres = relationship('Genre', secondary='books_has_genres', back_populates='books', overlaps='books_genres')
    cover = relationship('Cover')

    def __repr__(self):
        return '<Book %r>' % self.name

    def get_img(self):
        img = Cover.query.filter_by(id=self.cover_id).first()
        if img:
            img = img.url
        return img

    @property
    def rating(self):
        if self.rating_num > 0:
            return self.rating_sum / self.rating_num
        return 0


class Cover(db.Model):
    __tablename__ = 'covers'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(100))
    mime_type: Mapped[str] = mapped_column(String(100))
    md5_hash: Mapped[str] = mapped_column(String(100), unique=True)
    object_id: Mapped[Optional[int]]
    object_type: Mapped[Optional[str]] = mapped_column(String(100))

    def __repr__(self):
        return '<Cover: %r>' % self.file_name

    @property
    def storage_filename(self):
        _, ext = os.path.splitext(self.file_name)
        return _ + ext

    @property
    def url(self):
        return url_for('image', cover_id=self.id)


class Review(db.Model):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rating: Mapped[str] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    book_id: Mapped[str] = mapped_column(Integer, ForeignKey('books.id'))
    user_id: Mapped[str] = mapped_column(Integer, ForeignKey('users.id'))
    status_id: Mapped[int] = mapped_column(Integer, ForeignKey('statuses.id', ondelete='CASCADE'))

    book = relationship('Book', overlaps='reviews')
    user: Mapped["User"] = relationship()
    status: Mapped["Status"] = relationship()

    def __repr__(self):
        return f'<Reviews: {self.user_id} {self.created_at}>'

    def get_full_user_name(self):
        user = db.session.execute(db.select(User).filter_by(id=self.user_id)).scalar()
        return f"{user.first_name} {user.middle_name or ''} {user.last_name}"

    @property
    def is_ok(self):
        return self.status_id == 2


class UserPolicy:

    def create(self):
        return current_user.is_admin

    def delete(self):
        return current_user.is_admin

    def edit(self):
        return current_user.is_admin or current_user.is_moder

    def reviews_moderation(self):
        return current_user.is_admin or current_user.is_moder

    def show(self):
        return current_user.is_authenticated