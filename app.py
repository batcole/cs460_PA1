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
    u = flask_login.current_user.id
    return render_template('profile.html', name=getUserName(), message="Here's your profile",
                           friends = getFriends(u), r_friends = getFriendOfFriends(u), albums = getAlbums(), photoRecs=photoRecommendations())

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


@app.route('/c_search', methods=['GET', 'POST'])
def c_search():
    if request.method == 'POST':
        txt = request.form.get("search")
        ans = getCommentsFromText(txt)
        return render_template('c_search.html', comments = ans)
    else:
        return render_template('c_search.html')




# start friends code

@app.route('/addFriends', methods=['GET','POST'])
@flask_login.login_required
def addFriend():
    if request.method == 'POST':
        email = request.form.get('addFriend')
        u = flask_login.current_user.id
        print ('current = ', u, 'email = ', email)
        if (isFriend(email)):
            return render_template('profile.html', message = 'You are already Friends',
                                   friends = getFriends(u), name=getUserName(), albums = getAlbums())
        elif (u == email):
            print (getFriends(u))
            return render_template('profile.html', message='You cannot Friend yourself', friends=getFriends(u),
                                   albums=getAlbums(), name=getUserName())
        else:
            addFriendByEmail(email)
            return render_template('profile.html', message = 'Friend Added!', friends = getFriends(u),
                                   name=getUserName(), albums=getAlbums())
    else:
        return render_template('results.html')

@app.route('/profile', methods = ['GET', 'POST'])
@flask_login.login_required
def addRecFriend():
    if request.method == 'POST':
        email = request.form.get('addRecFriend')
        addFriendByEmail(email)
        u = flask_login.current_user.id
        return render_template('profile.html', message = 'Friend Added!', friends = getFriends(u), photoRecs=photoRecommendations())
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
        cursor.execute("INSERT INTO Contain (album_id, photo_id) VALUES  ({0}, {1})".format(getAlbumIdFromName(album),
                                                                                             photoid))
        conn.commit()
        #return render_template('upload.html')
        return render_template('profile.html', message='Photo uploaded!', photos=getUsersPhotos(uid), name=getUserName())
    # The method is GET so we return a  HTML form to upload the a photo.
    elif (whichSubmit == "createAlbum"):
        print("whichSubmit running")
        #do the album making here
        return createAlbum(request.form.get('albumName'))
    else:
        return render_template('upload.html', Albums=getAlbums())

# end photo uploading code

# album mgmt

@app.route('/manageAlbums', methods=['GET', 'POST'])
@flask_login.login_required
def manageAlbums():
    print("manage albums running")
    try:
        album = request.form.get("album")
        selection = request.form.get("submit")
    except:
        print ("dunno what happened")
        return render_template('manageAlbums.html', albums=getAlbums())
    print("album:", album)
    if (selection == "search") and (album is not None):
  #      print("inside search")
        photos = picsInAlbum(album)
  #      print("photos: ", photos)
        if photos is None:
            photos = []
        return render_template('manageAlbums.html', albums=getAlbums(), photos=photos, album=album)
    elif (selection == "delete"):
        deleteAlbum(album)
        return render_template('manageAlbums.html', albums=getAlbums())
    elif selection is not None:
        deletePhoto(selection)
        return render_template('manageAlbums.html', albums=getAlbums())
        #super sexy code, this makes selection into the value we need to delete ;)
    return render_template('manageAlbums.html', albums=getAlbums())

# end album mgmt

# Start tag mgmt

@app.route('/photoViewing', methods=['GET', 'POST'])
def photo_stream():
 #   print("called photoviewing")
    tagList = getAllTags()
 #   print("taglist in photo_stream:", tagList)
    addTags = str(request.form.get("tags"))
    userFilter = request.form.get("filter")
    like = request.form.get("like")

    if (like is not None):
        print("like: ", like)
        likePhoto(like)
    tagForSearch1 = request.form.get("existing_tags")
    lenGet = []
    print("tfs1: ", tagForSearch1)

    if tagForSearch1 is not None:
        if ("," in tagForSearch1):
            lenGet = tagForSearch1.split(",")
        else:
            lenGet.append(tagForSearch1)
    viewId = request.form.get("view")
    if (viewId is not None):
        print("viewId called")
        (users, likes, comments) = getInteractions(viewId)
        return render_template('photoViewing.html', photos=allPhotos(), tagList=tagList,
                               tagForSearch=tagForSearch1, topTags=topTags(), likesVisible=True, likes=likes, users=users, comments=showComment(viewId))

    print(lenGet)
    print("tagList: ", tagList)
    print("userFilter: ", userFilter)
    print("new tags: ", addTags)
    print("lenGet length: ", len(lenGet))
    if (addTags is not None) and (addTags != ""):
        tagList.append(addTags)

    elif (userFilter == "all") and (len(lenGet) == 1):
        return render_template('photoViewing.html', photos=photosWithTag(tagForSearch1), tagList=tagList, tagForSearch=tagForSearch1, topTags=topTags())

    elif (userFilter == "me") and (len(lenGet) == 1) and (flask_login.current_user.is_authenticated):
        return render_template('photoViewing.html', photos=myTagPhotos(tagForSearch1), tagList=tagList, tagForSearch=tagForSearch1, topTags=topTags())

    elif (userFilter == "me") and (len(lenGet) > 1) and (flask_login.current_user.is_authenticated):
        return render_template('photoViewing.html', multPhotos=myMultipleTags(lenGet), tagList=tagList, tagForSearch=tagForSearch1, topTags=topTags())

    elif (userFilter=="all") and (len(lenGet) > 1):
        print("multTags(lenGet: ", multipleTags(lenGet))
        return render_template('photoViewing.html', multPhotos=multipleTags(lenGet), tagList=tagList, tagForSearch=tagForSearch1, topTags=topTags())

    elif (userFilter=="me") and (not flask_login.current_user.is_authenticated):
        return render_template('photoViewing.html', tagList=tagList, topTags=topTags(), photos=allPhotos(), message="You need an account to have photos!")

    #print("calling last line")

    return render_template('photoViewing.html',  tagList=tagList, topTags=topTags(), photos=allPhotos())




@app.route('/activity', methods = ['GET', 'POST'])
def getActivityCount():
    cursor = conn.cursor()
    query = "SELECT Users.email, COUNT(*) FROM Users JOIN Owns ON Users.user_id = Owns.user_id JOIN Contain" \
            " ON Owns.album_id = Contain.album_id GROUP BY Users.user_id ORDER BY Count(*) DESC LIMIT 10"
    cursor.execute(query)
    count = cursor.fetchall()

    return render_template('activity.html', count = count )

# Start comments code



@app.route('/photoViewing.html', methods = ['GET','POST'])
def postComment():
    print('postComment called')
    if (request.method == 'POST'):
        comment = request.form.get("comment")     #Receives text data from comment box
       # print(comment)                            #Still need to connect pic information
        pid = request.form.get("pid")
        print('int(pid) is: ', int(pid))
        cursor = conn.cursor()

        #Block users from commenting on own photos
        cheq = "SELECT Photos.photo_id FROM Users JOIN Photos ON Users.user_id = Photos.user_id"
        cursor.execute(cheq)
        check = cursor.fetchall()
        for i in check:
            if (int(pid) == i[0]):          #int(check[i][0])
                return render_template('/photoViewing.html', message = 'Sorry, you cannot comment on your own photos',
                                   tagList = getAllTags(), topTags = topTags(), photos = allPhotos())
            else:
                pass
        else:
            u = getUserIdFromEmail(flask_login.current_user.id)
            query = "INSERT INTO Comments(user_id, content, photo_id) VALUES ('{0}', '{1}', '{2}')".format(u, comment, pid)
            cursor.execute(query)
            conn.commit()
            return photo_stream()
    else:
        print('method!=POST')
        pass


def showComment(pid):
    u = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    query = "SELECT Users.email, Comments.content, Comments.date FROM Users JOIN Comments ON " \
            "Users.user_id = Comments.user_id WHERE Comments.photo_id = '{0}' ORDER BY Comments.date ASC".format(pid)
    cursor.execute(query)
    tup = cursor.fetchall()
    return tup

# end comments code


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


def getFriends(id):
    cursor = conn.cursor()

    query = "SELECT email FROM Friends JOIN Users ON uid2 = user_id WHERE uid1 = '{0}'" \
            " UNION SELECT email FROM Friends JOIN Users ON uid1 = user_id WHERE uid2 = '{0}'".format(id)

    cursor.execute(query)
    ans = [spot[0] for spot in [[str(spot) for spot in results] for results in cursor.fetchall()]]
    return ans

def isFriend(uid):
    cursor = conn.cursor()
    u1 = getUserIdFromEmail(flask_login.current_user.id)
    u2 = getUserIdFromEmail(uid)
    print('cursor...')
    query = "SELECT * FROM Friends WHERE (uid1 = '{0}' AND uid2 = '{1}') OR (uid1 = '{1}' AND uid2 = '{0}')".format(u1, u2)

    cursor.execute(query)
    print('cursor executed')
    f = cursor.fetchall()
    print(f)
    if (len(f) == 0):
        return False
    else:
        return True

def addFriendByEmail(email):
    cursor = conn.cursor()
    u1 = getUserIdFromEmail(flask_login.current_user.id)
    u2 = getUserIdFromEmail(email)


    print(u1, u2, 'done')
    query = "INSERT INTO Friends(uid1, uid2) VALUES ('{0}', '{1}')".format(u1, u2)
    cursor.execute(query)
    conn.commit()

def getCommentsFromText(string):
    cursor = conn.cursor()
    query = "SELECT Users.email, COUNT(*) FROM Users JOIN Comments ON Users.user_id = Comments.user_id " \
            "WHERE content LIKE '%{0}%' GROUP BY Users.email ORDER BY COUNT(*) DESC;".format(string)
    cursor.execute(query)
    return cursor.fetchall()



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

def picsInAlbum(album):
    cursor = conn.cursor()
    print("pics in album called")
    print("album :", album)
    if cursor.execute("SELECT imgdata, photo_id FROM Photos WHERE photo_id IN (SELECT photo_id FROM Contain WHERE album_id = '{0}')".format(getAlbumIdFromName(album))):
        print("picsInAlbum query ran with something in it")
        return cursor.fetchall()

def deletePhoto(photo_id):
    print("delete photo called: ", photo_id)
    cursor = conn.cursor()
   # cursor.execute("DELETE FROM Contains")
    cursor.execute("DELETE FROM Photos WHERE photo_id = {0}".format(photo_id))
    conn.commit()

def deleteAlbum(album):
    cursor = conn.cursor()
    albumID = getAlbumIdFromName(album)
    cursor.execute("DELETE FROM Photos WHERE photo_id in (SELECT photo_id FROM Contain WHERE album_id = {0})".format(albumID))
    cursor.execute("DELETE FROM Albums WHERE album_id = {0}".format(albumID))
    conn.commit()

def allPhotos():
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, photo_id, caption FROM Photos")
    return cursor.fetchall()

def getAllTags():
    cursor = conn.cursor()
    cursor.execute("SELECT tag_name, count(*) AS frequency FROM Tags GROUP BY tag_name ORDER BY count(*) DESC;")
    list = [item[0] for item in [[str(item) for item in results] for results in cursor.fetchall()]]
    tagHolder = []
    tagHolder.extend(list)
    return tagHolder

def photosWithTag(tags):
    print("calling photosWithTag")
    print("tags: ",tags)
    cursor = conn.cursor()
    cursor.execute("SELECT p.imgdata, p.photo_id, p.caption FROM Photos AS P WHERE p.photo_id IN (SELECT DISTINCT photo_id FROM Tag_in WHERE tag_name = '{0}')".format(tags))
    return cursor.fetchall()

def multipleTags(tags):
    print("calling multipleTags")
    print("tags: ", tags)
    tagHolder = []
    for i in tags:
        temp = photosWithTag(i)
        print("temp: ", temp)
        if temp not in tagHolder:
            tagHolder.append(temp)
    return tagHolder

def topTags():
    print("topTags called")
    cursor = conn.cursor()
    cursor.execute("SELECT tag_name FROM Tag_in GROUP BY tag_name ORDER BY count(*) DESC")
    return cursor.fetchall()

def likePhoto(photo_id):
    print("likePhoto called")
    if (dupeLike(photo_id)):
        return
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Likes (photo_id, user_id) VALUES ('{0}', '{1}')".format(photo_id, Id()))
    conn.commit()

def dupeLike(photo_id):
    cursor = conn.cursor()
    if cursor.execute(
            "SELECT photo_id FROM likes WHERE user_id = {0} AND photo_id = {1}".format(Id(), photo_id)):
        return True
    else:
        return False

def getInteractions(viewId):
    print("getInteractions called")
    print("viewId: ", viewId)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(L.photo_id) FROM Likes L, Photos P WHERE L.photo_id = P.photo_id AND P.photo_id = {0}".format(viewId))
    print("ran likes")
    holder = cursor.fetchall()
    likes = holder[0][0]

    cursor.execute("SELECT group_concat(u.email SEPARATOR ', ') FROM Users U, Likes L WHERE U.user_id = L.user_id AND L.photo_id={0};".format(
        viewId))
    holder = cursor.fetchall()
    usersLike = holder[0][0]

    cursor.execute(str(
        "SELECT group_concat(content separator '$') FROM Photos P, Comments C WHERE P.photo_id = C.photo_id AND P.photo_id = {0};".format(
            viewId)))
    holder = cursor.fetchall()
    comments = holder[0][0]
    if comments is None:
        comments = []
    else:
        comments = comments.split("$")
    newList = (usersLike, likes, comments)
    print("newlist: ", newList)
    return newList

def getUserName():
    cursor = conn.cursor()
    cursor.execute("SELECT f_name FROM Users WHERE user_id = '{0}'".format(Id()))
    return cursor.fetchone()

def myTagPhotos(tags):
    print("myTagPhotos called")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT P.imgdata, P.photo_id, P.caption FROM Photos AS P, Tag_in AS T WHERE P.photo_id = T.photo_id AND P.photo_id IN (SELECT DISTINCT photo_id FROM Tag_in WHERE user_id = '{0}' AND  tag_name = '{1}')".format(
            Id(), tags))
    return cursor.fetchall()

def myMultipleTags(tags):
    print("calling myMultipleTags")
    print("tags: ", tags)
    tagHolder = []
    for i in tags:
        temp = myTagPhotos(i)
        print("temp: ", temp)
        if temp not in tagHolder:
            tagHolder.append(temp)
    return tagHolder

def photoRecommendations():
    print("getRecommendations called")
    cursor.execute(
        "SELECT DISTINCT P.imgdata, P.photo_id FROM Photos P, Tag_in T WHERE P.photo_id = T.photo_id AND P.user_id != {0} AND T.tag_name IN (SELECT tag_name FROM Tag_in GROUP BY tag_name ORDER BY count(tag_name)) LIMIT 5;".format(
            Id()))
    return cursor.fetchall()



# default page
@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html', message='Welcome to BS - A Photo Sharing Site!')


if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)
