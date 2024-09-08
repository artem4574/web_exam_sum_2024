from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import Book, Genre, User, Books_has_Genres, Review, Cover
from tools import ImageSaver
import markdown
import bleach
import os
from auth import check_rights
from models import db
bp = Blueprint('book', __name__, url_prefix='/book')

BOOK_PARAMS = [
    'author', 'name', 'amount', 'description', 'publisher', 'year'
]


def params():
    return {p: request.form.get(p) or None for p in BOOK_PARAMS}


def search_params(name, genres_list, years_list, amount_from, amount_to, author):
    return {
        'name': name,
        'genre_id': genres_list,
        'year': years_list,
        'amount_from': amount_from,
        'amount_to': amount_to,
        'author': author
    }


@bp.route('/new')
@check_rights('create')
@login_required
def new():
    book = Book()
    genres = db.session.execute(db.select(Genre)).scalars()
    users = db.session.execute(db.select(User)).scalars()
    return render_template('book/create.html',
                           genres=genres,
                           users=users,
                           book=book)

@bp.route('/create', methods=['POST'])
@check_rights('create')
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    book = Book()
    try:
        if f and f.filename:
            img = ImageSaver(f).save()

        cover_id = img.id if img else None
        year = int(request.form['year'])
        description = bleach.clean(request.form['description'], tags=['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul'], strip=True)
        book_params = params()
        book_params['year'] = year
        book_params['description'] = description
        book = Book(**params(), cover_id=cover_id)
        db.session.add(book)
        db.session.commit()
        genres = request.form.getlist('genre_id')
        for i in genres:
            genre_in_db = Books_has_Genres(books_id=book.id, genres_id=i)
            db.session.add(genre_in_db)
            db.session.commit()
    except IntegrityError:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных.', 'danger')
        db.session.rollback()
        genres = db.session.execute(db.select(Genre)).scalars()
        users = db.session.execute(db.select(User)).scalars()
        return render_template('book/create.html',
                            genres=genres,
                            users=users,
                            book=book)

    flash(f'Книга {book.name} была успешно добавлен!', 'success')

    return redirect(url_for('index'))



@bp.route('/<int:book_id>')
def show(book_id):
    book = db.get_or_404(Book, book_id)
    book_genres = Books_has_Genres.query.all()
    book.description = markdown.markdown(book.description)
    if current_user.is_authenticated:
        review = Review.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        if review:
            review = markdown.markdown(review.text)
    else:
        review = False

    reviews = Review.query.filter_by(book_id=book_id).all()
    comments = []
    if reviews:
        for comment in reviews:
            comments.append({
                'get_full_user_name': comment.get_full_user_name,
                'rating': comment.rating,
                'text': markdown.markdown(comment.text),
                'status': comment.is_ok
            })
    return render_template('book/show.html', book=book, book_genres=book_genres, review=review, reviews=comments)

@bp.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit(book_id):
    book = Book.query.get(book_id)
    genres = Genre.query.all()

    if request.method == 'GET':
        chosen_genres = Books_has_Genres.query.filter_by(books_id=book_id).all()
        chosen_genres_list = [genre.genres_id for genre in chosen_genres]
        return render_template('book/edit.html', book=book, genres=genres, chosen_genres_list=chosen_genres_list)

    if request.method == 'POST':
        try:
            for param in BOOK_PARAMS:
                if param == 'description':
                    sanitized_description = bleach.clean(request.form.get(param),
                                                        tags=['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em',
                                                              'i', 'li', 'ol', 'strong', 'ul'], strip=True)
                    setattr(book, param, sanitized_description)
                else:
                    setattr(book, param, request.form.get(param))
            db.session.commit()

            # Удаление существующих связей
            Books_has_Genres.query.filter_by(books_id=book_id).delete()
            db.session.commit()

            # Добавление новых связей
            genres = request.form.getlist('genre_id')
            for genre_id in genres:
                if genre_id:
                    genre_in_db = Books_has_Genres(books_id=book.id, genres_id=int(genre_id))
                    db.session.add(genre_in_db)
            db.session.commit()
            flash(f'Книга "{book.name}" успешно изменена!', 'success')

        except IntegrityError:
            flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных.', 'danger')
            db.session.rollback()

    return redirect(url_for('index'))


@bp.route('/review/<int:book_id>', methods=['GET', 'POST'])
@login_required
def review(book_id):
    book = Book.query.get(book_id)
    if request.method == 'POST':
        text = request.form.get('review')
        mark = int(request.form.get('mark'))
        review = Review(rating=mark, text=text, book_id=book_id, user_id=current_user.get_id(), status_id=1)
        is_review = db.session.query(Review).filter(Review.user_id == current_user.id,
                                                    Review.book_id == book_id).all()  # Corrected query
        book.rating_num += 1
        book.rating_sum += int(review.rating)

        if is_review:
            error = "Вы уже оставили отзыв на этот курс"
            flash("Вы уже оставили отзыв на этот курс.", "danger")
            return redirect(url_for('book.show', book_id=book.id, error=error))

        db.session.add(review)
        db.session.commit()
        flash(f'Отзыв был успешно добавлен на модерацию!', 'success')
        return redirect(url_for('book.show', book_id=book.id))
    if request.method == 'GET':
        return render_template('book/review.html', book=book)


@bp.route('/delete/<int:book_id>', methods=['POST', 'GET'])
@check_rights('delete')
def delete(book_id):
    if request.method == 'POST':
        book_genres = Books_has_Genres.query.filter_by(books_id=book_id).all()
        for book_genre in book_genres:
            db.session.delete(book_genre)
        book_reviews = Review.query.filter_by(book_id=book_id).all()
        for review in book_reviews:
            db.session.delete(review)
        book = Book.query.filter_by(id=book_id).first()
        try:
            img = Cover.query.filter_by(id=book.cover_id).first()
            if len(Book.query.filter_by(cover_id=book.cover_id).all()) == 1:
                img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'images', img.file_name)
                os.remove(img_path)
            else:
                db.session.delete(book)
                db.session.delete(img)
                db.session.commit()
        except:
            pass
        db.session.commit()
        db.session.delete(book)
        db.session.delete(img)
        db.session.commit()
        flash(f'Книга успешно удалена!', 'success')
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))