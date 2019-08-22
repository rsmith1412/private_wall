from flask import Flask, render_template, request, redirect, session, flash
from flask_bcrypt import Bcrypt
from mysql_connection import connectToMySQL
import re 

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
FORM_NAME_REGEX = re.compile(r'^[a-zA-Z- ]+$')
app = Flask(__name__)
app.secret_key = "the biggest secret"
bcrypt = Bcrypt(app)

# First route to login or register
@app.route('/')
def login_and_reg():
    return render_template("index.html")

# POST route for first time users to create an account. If successful, redirects to 'success' page. Otherwise redirects to /
@app.route('/register', methods=['POST'])
def create():
    print("Got post info")
    print(request.form)
    # include some logic to validate user input before adding them to the database!
    # Going to use this data twice, so putting it into a variable
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    form_email = request.form["email"]
    pass_word = request.form["password"]
    print(form_email, "LOOK HERE")
    #Setting up a query to retrieve all the email addresses so we can verify the new one doesn't already exist in the DB
    is_valid = True
    if len(first_name) < 2 or not FORM_NAME_REGEX.match(first_name):
        is_valid = False
        flash(u"First name must contain at least two letters and only contain letters.", 'register')
    if len(last_name) < 2 or not FORM_NAME_REGEX.match(last_name):
        is_valid = False
        flash(u"Last name must contain at least two letters and only contain letters.", 'register')
    if not EMAIL_REGEX.match(form_email):
        is_valid = False
        flash(u"Invalid email address!", 'register')
    if len(pass_word) < 8:
        is_valid = False
        flash(u"Password must be at least 8 characters", 'register')
    if not pass_word == request.form["confirm_password"]:
        is_valid = False
        flash(u"Passwords did not match!", 'register')
    mysql = connectToMySQL("private_wall")
    query = "SELECT * FROM users;"
    results = mysql.query_db(query)
    print(results[0])
    for result in results:
        if form_email == result["email"]:
            print("------------------------")
            is_valid = False
            flash(u"Email address already exists!", "register")
        
    # create the hash
    pw_hash = bcrypt.generate_password_hash(pass_word)  
    print(pw_hash)  
    # prints something like b'$2b$12$sqjyok5RQccl9S6eFLhEPuaRaJCcH3Esl2RWLm/cimMIEnhnLb7iC'
    # be sure you set up your database so it can store password hashes this long (60 characters)copy
    if is_valid:
        mysql = connectToMySQL("private_wall")
        query = "INSERT INTO users (first_name, last_name, email, pass_word) VALUES (%(fname)s, %(lname)s, %(email)s, %(password_hash)s);"
        # put the pw_hash in our data dictionary, NOT the password the user provided
        data = { 
            "fname" : first_name,
            "lname" : last_name,
            "email" : form_email,
            "password_hash" : pw_hash 
        }
        results = mysql.query_db(query, data)
        print(results, "//////////////")
        session['id'] = results
        print(session['id'])
        session['first_name'] = first_name
        # session["first_name"] = first_name
        print(session["first_name"], "---------------------")
        # never render on a post, always redirect!
        print(is_valid)
        return redirect("/wall")
    return redirect('/')

# POST route to login with an existing account. Success redirects to wall page, other wise redirects to login page
@app.route('/login', methods=['POST'])
def login():
    # see if the username provided exists in the database
    mysql = connectToMySQL("private_wall")
    query = "SELECT * FROM users WHERE email = %(email)s;"
    data = { "email" : request.form["email"] }
    result = mysql.query_db(query, data)
    print(result, "!!!!!!!!!!!!!!!!!!!!!!!!!")
    if len(result) > 0:
        # use bcrypt's check_password_hash method, passing the hash from our database and the password from the form
        if bcrypt.check_password_hash(result[0]['pass_word'], request.form["password_login"]):
            # if we get True after checking the password, we may put the user id in session
            session['first_name'] = result[0]['first_name']
            session['id'] = result[0]['id']
            print(session['first_name'], session['id'], "?????????????????????????????")
            # never render on a post, always redirect!
            return redirect('/wall')
    # if we didn't find anything in the database by searching by username or if the passwords don't match,
    # flash an error message and redirect back to a safe route
    flash(u"You could not be logged in.", 'login')
    return redirect("/")

# Upon successful login/registration, displays welcome message with session["first_name"]
@app.route('/wall')
def display_wall():
    if 'first_name' not in session:
        print("IS THIS IT")
        return redirect('/')
    else:
        # MySQL query to retrieve all messages where session["id"] = receiver["id"]
        # user_first_name = session['first_name']
        print("WHATS GOOD")
        print(session["id"])
        session_id = session["id"]
        print(session_id)
        mysql = connectToMySQL("private_wall")
        query = "SELECT id, first_name FROM users;"
        friends = mysql.query_db(query)
        print(friends, "!!!!!!!!!!!!!!!!!!!!!!!!!")
        mysql = connectToMySQL("private_wall")
        query = "SELECT messages.id AS msgid, messages.content AS msgcnt, sender.first_name AS sender_first FROM messages JOIN users AS sender ON sender.id = messages.sender_id WHERE messages.receiver_id = %(r_id)s;"
        data = {
            "r_id" : session_id
        }
        messages = mysql.query_db(query, data)
        mysql = connectToMySQL("private_wall")
        query = "SELECT id FROM messages WHERE sender_id = %(r_id)s;"
        num_msgs_sent = mysql.query_db(query, data)
        mysql = connectToMySQL("private_wall")
        query = "SELECT id FROM messages WHERE receiver_id = %(r_id)s;"
        num_msgs_rec = mysql.query_db(query, data)
        return render_template("wall.html", friends = friends, messages = messages, num_messages_sent = len(num_msgs_sent), your_messages = len(num_msgs_rec))

@app.route('/send_message/<receiver_id>', methods=["POST"])
def send_message(receiver_id):
    print("IN THE SEND MESSAGE FUNCTION")
    receiver_id = request.form["hidden_receiver"]
    print(receiver_id)
    
    mysql = connectToMySQL("private_wall")
    query = "INSERT INTO messages (sender_id, receiver_id, content) VALUES (%(s_id)s, %(r_id)s, %(con)s);"
    data = {
        "s_id" : session["id"],
        "r_id" : receiver_id,
        "con" : request.form["text_area"]
    }
    new_message = mysql.query_db(query, data)
    print(new_message, "+++++++++++++++++++++++++")
    return redirect('/wall')

@app.route('/delete_message', methods=["POST"])
def del_message():
    print("In the delete message function")
    mysql = connectToMySQL("private_wall")
    query = "DELETE FROM messages WHERE id = %(id)s;"
    data = {
        "id" : request.form["hidden_message"]
    }
    del_message = mysql.query_db(query, data)
    print(del_message)
    return redirect('/wall')

# Logout route will clear the session and redirect to root 
@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)