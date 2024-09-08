from flask import Flask, render_template, send_from_directory, redirect, request, url_for, abort
from flask_migrate import Migrate
from sqlalchemy import distinct, desc
from sqlalchemy.exc import SQLAlchemyError
from models import db, Genre, Cover, Review, Books_has_Genres, Book
from auth import bp as auth_bp, init_login_manager, check_rights
from book import bp as book_bp, search_params
from tools import  BookFilter
from flask_login import login_required, current_user
import markdown
import math


app = Flask(__name__)
application = app
app.config.from_pyfile('config.py')

db.init_app(app)
migrate = Migrate(app, db)

init_login_manager(app)


@app.errorhandler(SQLAlchemyError)
def handle_sqlalchemy_error(err):
    error_msg = ('Возникла ошибка при подключении к базе данных. '
                 'Повторите попытку позже.')
    return f'{error_msg} (Подробнее: {err})', 500


app.register_blueprint(auth_bp)
app.register_blueprint(book_bp)
PER_PAGE = 5


@app.route('/')
def index():
    genres = Genre.query.all()
    book_genre = Books_has_Genres.query.all()
    years = db.session.query(distinct(Book.year)).order_by(desc(Book.year)).all()
    years = [str(i[0]) for i in years]
    page = request.args.get('page', 1, type=int)
    name = request.args.get('name', '')
    genres_list = request.args.getlist('genre_id')
    years_list = request.args.getlist('year')
    amount_from = request.args.get('amount_from', '')
    amount_to = request.args.get('amount_to', '')
    author = request.args.get('author', '')
    books = BookFilter().perform(name, genres_list, years_list, amount_from, amount_to, author)
    pagination = books.paginate(page=page, per_page=5)
    books = pagination.items
    rating = Book.rating
    flag = True
    if not books:
        flag = False
    return render_template('index.html', books=books, genres=genres, years=years, book_genre=book_genre,
                           pagination=pagination, rating=rating,
                           search_params=search_params(name, genres_list, years_list, amount_from, amount_to, author),
                           name=name, genres_list=[int(x) for x in genres_list], years_list=years_list,
                           amount_from=amount_from, amount_to=amount_to, author=author, flag=flag)

@app.route('/media/images/<cover_id>')
def image(cover_id):
    cover = db.get_or_404(Cover, cover_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], cover.storage_filename)

@app.route('/reviews')
@login_required
def reviews():
    reviews = Review.query.filter_by(user_id=current_user.id).all()
    comments = []

    if reviews:
        for comment in reviews:
            comments.append({
                'get_full_user_name': comment.get_full_user_name,
                'rating': comment.rating,
                'text': markdown.markdown(comment.text),
                'status': comment.status_id
            })

    return render_template('review/reviews.html', reviews=comments)


@app.route('/reviewmoderation')
@check_rights('reviews_moderation')
@login_required
def reviews_moderation():
    reviews_counter = Review.query.filter_by(status_id=1).count()
    page = request.args.get('page', 1, type=int)
    reviews = Review.query.filter_by(status_id=1).limit(PER_PAGE).offset(PER_PAGE * (page - 1)).all()
    page_count = math.ceil(reviews_counter / PER_PAGE)
    comments = []

    if reviews:
        for comment in reviews:
            comments.append({
                'id': comment.id,
                'get_full_user_name': comment.get_full_user_name,
                'rating': comment.rating,
                'text': markdown.markdown(comment.text),
                'status': comment.status_id
            })

    return render_template("review/moderation.html", reviews=comments, page=page, page_count=page_count)


@app.route('/checkreview/<review_id>')
@check_rights('reviews_moderation')
@login_required
def check_review(review_id):
    review = Review.query.get(review_id)
    get_full_user_name = review.get_full_user_name
    rating = review.rating
    text = markdown.markdown(review.text)
    status = review.status_id

    return render_template("review/edit.html", review_id=review_id, user=get_full_user_name(), rating=rating,
                           text=text, status=status)


@app.route('/checkreview/aprove/<review_id>', methods=['GET', 'POST'])
@login_required
def aprove(review_id):
    db.session.query(Review).filter(Review.id == review_id).update({'status_id': 2})
    db.session.commit()
    return redirect(url_for('reviews_moderation'))


@app.route('/checkreview/reject/<review_id>', methods=['GET', 'POST'])
@login_required
def reject(review_id):
    db.session.query(Review).filter(Review.id == review_id).update({'status_id': 3})
    db.session.commit()
    return redirect(url_for('reviews_moderation'))


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000)
