from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import MySQLdb
import re

import pickle
import numpy as np
import pandas as pd
from preprocess import preprocess_apply
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import gensim
import tensorflow as tf

app = Flask(__name__,static_folder='/Users/bytedance/Documents/frontend/perfect stranger/static',)
app.debug = 1
# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'perfect'

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'zhfzuishuai'
app.config['MYSQL_DB'] = 'perfectlogin'

#socketio = SocketIO(app, cors_allowed_origins="*")
# Intialize MySQL
mysql = MySQL(app)

# fill null in table post.score
# connect to database
db = MySQLdb.connect('localhost', 'root', 'zhfzuishuai', 'perfectlogin', charset='utf8' )
cursor = db.cursor()
try:
    cursor.execute('SELECT * FROM post WHERE score is NULL')
    # Fetch all record and return result
    empty_score = cursor.fetchall()

    # load the sentiment analysis model
    word2vec_model = gensim.models.KeyedVectors.load_word2vec_format('Word2Vec-twitter-100-dims-trainable')
    # Loading the tokenizer
    with open('Tokenizer.pickle', 'rb') as file:
        tokenizer = pickle.load(file)
    # load the saved model
    training_model = tf.keras.models.load_model('Twitter-Sentiment-BiLSTM')

    # generate score and store it in table named post_with_score
    input_length = 60
    update_data = []
    for i in empty_score:
        myword = i[2]
        my = preprocess_apply(myword)
        my_test = pad_sequences(tokenizer.texts_to_sequences([my]), maxlen=input_length)
        content_score = training_model.predict(my_test)
        update_data.append((content_score[0][0], i[0], i[1], i[2], i[3]))

    sql = 'UPDATE post SET score=(%s) WHERE id=(%s) AND username=(%s) AND content=(%s) AND created_date=(%s)'
    try:
        cursor.executemany(sql, update_data)
        db.commit()
    except:
        db.rollback()
except:
    print("Error: unable to fetch data.")
# close the connection
db.close()

# http://localhost:5000/perfectlogin/ - this will be the login page, we need to use both GET and POST requests
@app.route('/perfectlogin/', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

# http://localhost:5000/perfectlogin/logout - this will be the logout page
@app.route('/perfectlogin/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

# http://localhost:5000/perfectlogin/register - this will be the registration page, we need to use both GET and POST requests
@app.route('/perfectlogin/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

# http://localhost:5000/perfectlogin/home - this will be the home page, only accessible for loggedin users
@app.route('/perfectlogin/home')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# http://localhost:5000/perfectlogin/profile - this will be the profile page, only accessible for loggedin users
@app.route('/perfectlogin/profile')
def profile():
    # Check if user is loggedinset FLASK_APP=main.pyset FLASK_APP=main.pyset FLASK_APP=main.py
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# http://localhost:5000/perfectlogin/predict
@app.route('/perfectlogin/score')
def score():
    # Check if user is loggedinset FLASK_APP=main.pyset FLASK_APP=main.pyset FLASK_APP=main.py
    if 'loggedin' in session:
        # We need to display the score of user's posts.
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM post WHERE id = %s', (session['id'],))
        post_info = cursor.fetchall()

        # input_length = 60
        # myword = post_info['content']
        # my = preprocess_apply(myword)
        # my_test = pad_sequences(tokenizer.texts_to_sequences([my]), maxlen=input_length)
        # text_score = training_model.predict(my_test)

        # Show the score info
        # return render_template('score.html', post_info=post_info, score=text_score)
        return render_template('score.html', post_info=post_info)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

app.run()