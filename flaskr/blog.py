from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('blog', __name__)


@bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, username'
        '       ,(SELECT COUNT(*) FROM user_like'
        '         WHERE post_id = p.id) as like_count'
        '       ,? in (SELECT user_id FROM user_like'
        '         WHERE post_id = p.id) as i_like'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC',
        (0 if g.user is None else g.user['id'],)
    ).fetchall()

    return render_template('blog/index.html', posts=posts)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is None:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('index'))

        flash(error)

    return render_template('blog/create.html')


def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is None:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

        flash(error)

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))


@bp.route('/<int:id>/details')
def details(id):
    post = get_post(id, check_author=False)
    return render_template('blog/details.html', post=post)


@bp.route('/<int:id>/like')
@login_required
def like_post(id):
    post = get_post(id, check_author=False)
    db = get_db()
    if db.execute(
        'SELECT * FROM user_like'
        ' WHERE post_id = ? AND user_id = ?',
        (post['id'], g.user['id'])
    ).fetchone() is None:
        db.execute(
            'INSERT INTO user_like (user_id, post_id)'
            ' VALUES (?, ?)',
            (g.user['id'], post['id'])
        )
    else:
        db.execute(
            'DELETE FROM user_like'
            ' WHERE post_id = ? AND user_id = ?',
            (post['id'], g.user['id'])
        )
    db.commit()
    return redirect(url_for('blog.index'))
