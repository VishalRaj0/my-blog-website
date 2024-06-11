from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey, Column
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm



app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog_database.db'
# app.config['SQLALCHEMY_BINDS'] = SQLALCHEMY_BINDS = {
#     "users_db": "sqlite:///users.db",
#     "posts_db": "sqlite:///posts.db"
# }

db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
# TODO: Create a User table for all your registered users.
class User(UserMixin, db.Model):
    __tablename__ = "user_table"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author = relationship("User", back_populates="posts")
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_table.id"))

    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("user_table.id"))
    author = relationship("User", back_populates="comments")

    parent_blog_id = Column(Integer, ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    comment = Column(String(500))
    date = Column(String(250))


with app.app_context():
    db.create_all()




# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if db.session.execute(db.select(User).where(User.email == request.form.get('email'))).scalar():
            flash("User already registered! Please login.")
            return redirect(url_for('login'))
        else:
            new_user = User(
                name=request.form.get('name'),
                email=request.form.get('email'),
                password=generate_password_hash(request.form.get('password'))
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template("register.html", form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == request.form.get('email'))).scalar()
        if user is not None:
            if check_password_hash(user.password, request.form.get('password')):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Password is wrong!")
        else:
            flash("User not registered!")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)
    comments = db.session.execute(db.select(Comment).where(Comment.parent_blog_id == requested_post.id).order_by(Comment.id.desc())).scalars().all()

    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                author=current_user,
                date=date.today().strftime("%B %d, %Y"),
                parent_post=requested_post,
                comment=request.form.get("comment")
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(request.url)

        else:
            flash('Please login to comment!')
            return redirect(url_for('login'))

    return render_template("post.html", post=requested_post, comment_form=form, comments=comments)

# TODO: Use a decorator so only an admin user can create a new post
def admin_only(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return function(*args, **kwargs)
        else:
            return abort(403)
    return wrapper

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")




if __name__ == "__main__":
    app.run(debug=True, port=5002)
