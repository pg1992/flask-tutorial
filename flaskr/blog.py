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


def get_comments(post_id):
    comments = get_db().execute(
        'SELECT pc.id, title, body, created, user_id, username'
        ' FROM post_comment as pc JOIN user as u ON u.id = pc.user_id'
        ' WHERE post_id = ?'
        ' ORDER BY created DESC',
        (post_id,)
    ).fetchall()

    return comments


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


@bp.route('/<int:id>/details', methods=('GET', 'POST'))
def details(id):
    post = get_post(id, check_author=False)
    comments = get_comments(id)

    if request.method == 'POST':
        if g.user is None:
            abort(403)

        comment_title = request.form['comment_title']
        comment_body = request.form['comment_body']
        error = None

        if comment_title is None:
            error = 'Comment title is required.'

        if comment_body is None:
            error = 'Comment body is required.'

        if error is None:
            db = get_db()
            db.execute(
                'INSERT INTO post_comment (title, body, user_id, post_id)'
                ' VALUES (?, ?, ?, ?)',
                (comment_title, comment_body, g.user['id'], id)
            )
            db.commit()
            return redirect(url_for('blog.details', id=post['id']))

        flash(error)

    return render_template('blog/details.html', post=post, comments=comments)


@bp.route('/<int:id>/like', methods=('POST',))
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
