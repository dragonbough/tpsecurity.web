from flask import *   
import mysql.connector
import bcrypt
from datetime import timedelta
from PIL import Image
import io
import base64
from dotenv import load_dotenv
import os

#access .env file which stores sensitive information
load_dotenv()

database = mysql.connector.connect(
  host=os.getenv("DATABASE_HOST"),
  user=os.getenv("DATABASE_USER"),
  password=os.getenv("DATABASE_PASSWORD"),
  database = os.getenv("DATABASE")
)

dbcursor = database.cursor()
    
app = Flask(__name__)   # Flask constructor 

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=31)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 3

def hash(data):
    encoded = data.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(encoded, salt)

def compressed_image(image_bytes, filename):
    image = Image.open(io.BytesIO(image_bytes))
    buffered = io.BytesIO()
    file_type = filename[filename.index(".")+1:]
    if file_type.lower() == "jpg" or file_type.lower() == "jpeg":
        file_type = "jpeg"
        image.save(buffered, format=file_type, optimize=True, quality=70)
    else:
        image.save(buffered, format=file_type, optimize=True)
    print(f"Original length: {len(image_bytes)}")
    print(f"Compressed length: {len(buffered.getvalue())}")
    return buffered.getvalue()

@app.route('/')
def init():
    return redirect(url_for("home"))
 
@app.route('/home')
def home():
    return render_template("index.html")

@app.route('/vision')
def vision():
    return render_template("vision.html")

@app.route('/login', methods=['POST', 'GET'])
def login():
    error = None
    
    if session.get("username"):
            return redirect(url_for("tportal"))
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        remember = request.form.get("remember")
        dbcursor.execute("SELECT * FROM users WHERE username = %s", [username])
        users = dbcursor.fetchall()
        if users:
            if username in users[0]:
                hashed_pass = bytes(users[0][2], "utf-8")
                if bcrypt.checkpw(password.encode("utf-8"), hashed_pass) == True:
                    session["username"] = username
                    if remember == "on":
                        session.permanent = True
                    elif remember == "off":
                        session.permanent = False
                    return redirect(url_for("tportal"))
                else:
                    error = "Incorrect username or password"
        else:
            error = "Incorrect username or password"
        flash(error, "error")
    return render_template("tportal/index.html")

@app.route('/register', methods =["POST", "GET"])
def register():
    
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password2 = request.form["password2"]
        if password != password2:
            error = "Passwords do not match"
            
        dbcursor.execute("SELECT * FROM users WHERE username = %s", [username])
        users = dbcursor.fetchall()
        if users:
            error = "Username already exists"

        if error == None:
            dbcursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hash(password)))
            database.commit()
            return redirect(url_for("login"), code="307")       
         
        if error:
            flash(error, "error")
    return render_template("tportal/register.html") 

@app.route("/tportal", methods=["POST", "GET"])
def tportal():
    
    if session.get("username"):
        
        dbcursor.execute("SELECT id FROM users WHERE username = %s", [session["username"]])
        user_id = dbcursor.fetchall()[0][0]
        
        error = None
        if request.method == "POST":
            if "logout" in request.form:
                session.pop("username", default=None)
                return redirect(url_for("login"))
            elif "submit" in request.form:
                post_file = request.files.get("user_file")
                print(post_file)
                post_text = request.form.get("user_text")
                if not post_file.filename and not post_text:
                    error = "No file or text inputted"
                else:
                    if post_file:
                        stream = compressed_image(post_file.stream.read(), post_file.filename)
                    else:
                        stream = "n/a"
                    if not post_text:
                        post_text = "n/a"
                    dbcursor.execute("INSERT INTO posts (post_image, post_text) VALUES (%s, %s)", (stream, post_text))
                    post_id = dbcursor.lastrowid
                    print(f"postid: {post_id}")
                    print(f"userid: {user_id}")
                    dbcursor.execute("INSERT INTO users_to_posts (postid, userid) VALUES (%s, %s)", (post_id, user_id))
                    database.commit()
            elif "delete" in request.form:
                print("DELETING")
                post_to_delete = request.form["delete"]
                print (post_to_delete)
                dbcursor.execute("DELETE FROM posts WHERE postid = %s", [post_to_delete])
                dbcursor.execute("DELETE FROM users_to_posts WHERE postid = %s", [post_to_delete])
                database.commit()
            if error:
                flash(error, "error")
                
        error = None
        posts = []
        sql = "SELECT posts.postid, posts.post_image, posts.post_text FROM posts JOIN users_to_posts ON posts.postid = users_to_posts.postid WHERE users_to_posts.userid = %s;"
        dbcursor.execute(sql, [user_id])
        results = dbcursor.fetchall()
        if results:
            for result in results:
                post_id = result[0]
                if result[1] != "n/a":
                    post_image_base64 = base64.b64encode(result[1])
                    post_image = Image.open(io.BytesIO(result[1]))
                    post_dimensions = post_image.size
                    posts.append(["", post_image_base64.decode('utf-8'), post_image.format.lower(), post_dimensions, post_id])
                else:
                    post_text = result[2]
                    posts.append([post_text, "n/a", "n/a", "n/a", post_id])
                
        if error:
            flash(error, "error")
        return render_template("tportal/main.html", postlist=posts) 
    else:
        return redirect(url_for("login"))
    
@app.errorhandler(413)
def large_error(error):
    if request.path == url_for("tportal"):
        flash("File too large (max is 3MB)", "error")
        return redirect(url_for("tportal"))
   
@app.route("/contact", methods=["POST", "GET"])
def contact():
    if request.method == "GET":
        return render_template("contact.html")
    elif request.method == "POST":
        return ("IT WORKS")
    
if __name__=='__main__': 
   app.run() 