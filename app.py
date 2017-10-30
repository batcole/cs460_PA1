######################################
# author ben lawson <balawson@bu.edu> 
# Edited by: Baichuan Zhou (baichuan@bu.edu) and Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################
import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login as flask_login

# for image uploading
# from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

# These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'hello'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email FROM Users")
users = cursor.fetchall()


def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM Users")
    return cursor.fetchall()


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    query = "SELECT password FROM Users WHERE email = '%s'"% (email)
    cursor.execute(query)
    data = cursor.fetchall()
    pwd = str(data[0][0])
    user.is_authenticated = request.form['password'] == pwd
    return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return render_template('login.html')    #redirect to login page


    # The request method is POST (page is receiving data)
    email = flask.request.form['email']
    cursor = conn.cursor()
    # check if email is registered
    if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
        data = cursor.fetchall()
        pwd = str(data[0][0])
        if flask.request.form['password'] == pwd:
            user = User()
            user.id = email
            flask_login.login_user(user)  # okay login in user
            return flask.redirect(flask.url_for('protected'))  # protected is a function defined in this file

    # information did not match
    return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('logout.html', message='Logged out')


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')


# you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')


@app.route("/register", methods=['POST'])
def register_user():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        h_town = request.form.get('h_town')
        dob = request.form.get('dob')
    except:
        print(
            "couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test = isEmailUnique(email)
    if test:
        print(cursor.execute("INSERT INTO Users (email, password, f_name, l_name, h_town, dob) VALUES "
                             "('{0}', '{1}', '{2}', '{3}', '{4}', '{5}')".format(email, password, f_name, l_name, h_town, dob)))
        conn.commit()
        # log user in
        user = User()
        user.id = email

        username = email.split('@')[0] # splits email at '@', uses first part of email as username
        flask_login.login_user(user)
        return render_template('hello.html', name=username, message='Account Created!')
    else:
        print("couldn't find all tokens")
        return render_template('register.html', suppress ='False')


def getUsersPhotos(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, photo_id, caption FROM Photos WHERE user_id = '{0}'".format(uid))
    return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]


def getUserIdFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
    return cursor.fetchone()[0]


def isEmailUnique(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True


# end login code

@app.route('/profile')
@flask_login.login_required
def protected():
    dispName = flask_login.current_user.id.split('@')[0]
    u = flask_login.current_user.id
    return render_template('profile.html', name= u, message="Here's your profile",
                           friends = getFriends(u), r_friends = getFriendOfFriends(u))

# start search code
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        cursor = conn.cursor()
        email = request.form.get("search")
       # print(email, 'out')
        #if (cursor.execute("SELECT email FROM Users WHERE email LIKE '{0}'".format(uemail))):
        #print(getUsersFromEmail(email))
        if (getUsersFromEmail(email)!= []):
            records = getUsersFromEmail(email)
         #   print(records, type(records))
            return render_template('results.html', records=records)
    return render_template('search.html')




# start friends code

@app.route('/addFriends', methods=['GET','POST'])
@flask_login.login_required
def addFriend():
    if request.method == 'POST':
        email = request.form.get('addFriend')
        addFriendByEmail(email)
        u = flask_login.current_user.id
        return render_template('profile.html', message = 'Friend Added!', friends = getFriends(u))
    else:
        return render_template('results.html')

@app.route('/profile', methods = ['GET', 'POST'])
@flask_login.login_required
def addRecFriend():
    if request.method == 'POST':
        email = request.form.get('addRecFriend')
        print email
        addFriendByEmail(email)
        u = flask_login.current_user.id
        return render_template('profile.html', message = 'Friend Added!', friends = getFriends(u))
    else:
        return protected()

# begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
    print(request.form.get("Submit"))
    print(request.method)
    whichSubmit = request.form.get("Submit")
    print(whichSubmit)
    if (whichSubmit == 'Upload'):
        print("running upload")
        uid = getUserIdFromEmail(flask_login.current_user.id)
        imgfile = request.files['photo']
        print("before caption")
        caption = request.form.get('caption')
        print("after caption")
        album = request.form.get('album')
        tags = request.form.get('tags') #need to wire this
        tags = tags.split(",")
        photo_data = base64.standard_b64encode(imgfile.read())
        cursor = conn.cursor()
        '''
        cursor.execute(
            "INSERT INTO Photos (user_id, imgdata, caption) VALUES ('{0}', '{1}', '{2}' )".format(uid, photo_data,
                                                                                                    caption))
        '''
        cursor.execute("INSERT INTO Photos (user_id, imgdata, caption) VALUES ('{0}', '{1}', '{2}' )".format(uid, photo_data, caption))
        conn.commit()
        photoid = cursor.lastrowid
        for i in tags:
            if len(i) <= 40:
                if tagUnique(i):
                    cursor.execute("INSERT INTO Tags (tag_name) VALUES ('{0}')".format(i))
                    conn.commit()
                cursor.execute("INSERT INTO Tag_in (tag_name, photo_id) VALUES ('{0}','{1}')".format(i, photoid))
                conn.commit()
            else:
                i = i[:40]
                if tagUnique(i):
                    cursor.execute("INSERT INTO Tags (tag_name) VALUES ('{0}')".format(i))
                    conn.commit()
                cursor.execute("INSERT INTO Tag_in (tag_name, photo_id) VALUES ('{0}','{1}')".format(i, photoid))
                conn.commit()
        print("photoid: ", photoid)
        print("Albumid: ", getAlbumIdFromName(album))
        cursor.execute("INSERT INTO Contains (album_id, photo_id) VALUES  ({0}, {1})".format(getAlbumIdFromName(album),
                                                                                             photoid))
        conn.commit()
        #return render_template('upload.html')
        return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid))
    # The method is GET so we return a  HTML form to upload the a photo.
    elif (whichSubmit == "createAlbum"):
        print("whichSubmit running")
        #do the album making here
        return createAlbum(request.form.get('albumName'))
    else:
        return render_template('upload.html', Albums=getAlbums())




# end photo uploading code


#helper functions
def getFriendOfFriends(user):
    friends = getFriends(user)
    rec_list = []
    for friend in friends:
        # find list of B's friends, for each friend, if not friends with A, add to rec_list
        temp = getFriends(friend)
        print temp, friend, 'outside'
        for i in temp:
            if (i not in rec_list and i not in friends and i != flask_login.current_user.id):
                print rec_list, 'inside'
                rec_list.append(i)
            else:
                continue
   # print rec_list
    return rec_list


def getFriends(user):
    cursor = conn.cursor()
    uid = getUserIdFromEmail(user)
    query = "SELECT email FROM Friends JOIN Users ON uid2 = user_id WHERE uid1 = '{0}'" \
            " UNION SELECT email FROM Friends JOIN Users ON uid1 = user_id WHERE uid2 = '{0}'".format(uid)

    cursor.execute(query)
    ans = [spot[0] for spot in [[str(spot) for spot in results] for results in cursor.fetchall()]]
    return ans


def addFriendByEmail(email):
    cursor = conn.cursor()
    u1 = getUserIdFromEmail(flask_login.current_user.id)
    u2 = getUserIdFromEmail(email)
    print(u1, u2, 'done')
    query = "INSERT INTO Friends(uid1, uid2) VALUES ('{0}', '{1}')".format(u1, u2)
    cursor.execute(query)
    conn.commit()

def getUsersFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM Users WHERE email LIKE '{0}%'".format(email))
    ans = [spot[0] for spot in [[str(spot) for spot in results] for results in cursor.fetchall()]]
    return ans

def getAlbumIdFromName(name):
    cursor = conn.cursor()
    print("get albumid from nbame called")
    print(name)
    if (cursor.execute("SELECT album_id  FROM Albums WHERE name = '{0}'".format(name))):
        print("query ran albumid")
        return cursor.fetchone()[0]
    return cursor.fetchone()[0]

def createAlbum(album_name):
    print("createAlbum running")
    unique = albumUniqueTest(album_name)
    if unique:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Albums (name) VALUES ('{0}' )".format(album_name))
        conn.commit()
        cursor.execute("INSERT INTO Owns (user_id, album_id) VALUES ({0},{1})".format(Id(), cursor.lastrowid))
        conn.commit()
        return render_template('upload.html', Albums=getAlbums())
    else:
        print("duplicate")
        return render_template('upload.html', Albums=getAlbums())

def albumUniqueTest(album):
    cursor = conn.cursor()
    if cursor.execute("SELECT name FROM Albums  WHERE name = '{0}'".format(album)):
        return False
    else:
        return True

def Id():
    if (flask_login.current_user.is_authenticated):
        return getUserIdFromEmail(flask_login.current_user.id)
    else:
        return "not authenticated"

def getAlbums():
    print("get albums running")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT A.name FROM Albums AS A WHERE album_id IN (SELECT album_id FROM Owns WHERE user_id={0});".format(
            Id()))
    print("get albums cursor ran")
    return [spot[0] for spot in [[str(spot) for spot in results] for results in cursor.fetchall()]]

def getUserIdFromEmail(email):
    cursor = conn.cursor()
   # print('getting userID')
    cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
    ans = cursor.fetchone()[0]
   # print(ans, type(ans))
   # print(cursor.fetchone()[0], 'did I get it?')
    return int(str(ans).split('L')[0])

def tagUnique(tag):
    cursor = conn.cursor()
    if cursor.execute("SELECT tag_name FROM Tags WHERE tag_name = '{0}'".format(tag)):
        return False
    else:
        return True





# default page
@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html', message='Welcome to Photoshare')


if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)
