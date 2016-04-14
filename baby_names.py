import flask
import random
from flask import Flask, url_for, render_template, request, jsonify, redirect
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.bcrypt import Bcrypt
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)

with app.test_request_context():
    url_for('static', filename='main.css')

## User Management ##

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(10))
    pwhash = db.Column(db.String(64))

    def __init__(self, username, pwhash):
        self.username = username
        self.pwhash = pwhash

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

class Rating(db.Model):
    name_id = db.Column(db.Integer, db.ForeignKey('name.id'), primary_key=True)
    name = db.relationship('Name', backref=db.backref('ratings', lazy='dynamic'))
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user = db.relationship('User', backref=db.backref('ratings', lazy='dynamic'))
    
    rating = db.Column(db.Integer)
    
    def __init__(self, name, rating, user):
        self.name = name
        self.rating = rating
        self.user = user

class Name(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)

    def __init__(self, name):
        self.name = name

@login_manager.user_loader
def load_user(username):
    return User.query.filter_by(username=username).first()

def get_next_name(user):
    unrated_names = Name.query.filter(~Name.ratings.any(Rating.user == user)).all()

    if len(unrated_names) > 0:
        return random.choice(unrated_names)
    else:
        return random.choice(Name.query.all())

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
 
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = load_user(username)
        if not user:
            error = 'Invalid username'
        elif not bcrypt.check_password_hash(user.pwhash, password):
            error = 'Invalid password'
        else:
            login_user(user)

            next_page = request.args.get('next')
            if not next_page:
                next_name = get_next_name(user)    
                next_page = '/rate/' + next_name.name

            return redirect(next_page)
    
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'Succesfully logged out'

@app.route('/next_name')
@login_required
def next_name():
    next_name = get_next_name(current_user)
    return jsonify(name=next_name.name)

@app.route("/rate/<name>")
@login_required
def rate_name(name):
    name_obj = Name.query.filter_by(name=name).first()
    rating_obj = Rating.query.filter_by(name=name_obj, user=current_user).first()
    if rating_obj is None:
        rating = 0
    else:
        rating = rating_obj.rating

    return render_template('rate.html', name=name, rating=rating)

@app.route('/change_rating/<name>', methods=['POST'])
@login_required
def change_rating(name):
    name = Name.query.filter_by(name=request.json['name']).first()
    rating_value = request.json['rating']

    rating = Rating.query.filter_by(name=name, user=current_user).first()
    if rating is None:
        rating = Rating(name, rating_value, current_user)
        db.session.add(rating)
    else:
        rating.rating = rating_value

    db.session.commit()

    return 'Rating for {} changed to {}'.format(request.json['name'], request.json['rating'])

if __name__ == "__main__":
    app.run()
