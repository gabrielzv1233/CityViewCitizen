from flask import Flask, render_template, request, make_response, redirect
from markupsafe import escape
import shelve
import re
import datetime
import uuid
import os
from PIL import Image
from werkzeug.utils import secure_filename

db = shelve.open("databases/users/userdata")
if not "Admin" in db.keys():
    db["Admin"] = ["CHANGE-ME", str(uuid.uuid4()), True]
    print("Admin account dose not exist, creating\n")
    db.close()

app = Flask(__name__)

def format(contents):
    contents = escape(contents)
    contents = contents.rstrip()
    contents = re.sub(r'  ', '&nbsp;&nbsp;', contents)
    contents = re.sub(r'^- \|(.*)$', r'<li>\1</li>', contents)
    contents = re.sub(r'\((.*?)\)\[(.*?)\]', lambda m: f'<a href="{m.group(2)}">{m.group(1) if m.group(1) else m.group(2)}</a>', contents)
    contents = re.sub(r'&lt;yt&gt;(.*?)&lt;/yt&gt;', r'<iframe width="426.6666667" height="240" src="https://www.youtube.com/embed/\1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen=""></iframe>', contents.replace("https://www.youtube.com/watch?v=",""))
    contents = re.sub(r"&lt;u&gt;(.*?)&lt;/u&gt;", r'<u>\1</u>', contents)
    contents = re.sub(r'&lt;c=&#34;([^"]+)&#34;&gt;([^<]+)&lt;/c&gt;', r'<span style="color:\1">\2</span>', contents)
    contents = re.sub(r"&lt;left&gt;(.*?)&lt;/left&gt;", r'<div class="left">\1</div>', contents)
    contents = re.sub(r"&lt;center&gt;(.*?)&lt;/center&gt;", r'<div class="center">\1</div>', contents)
    contents = re.sub(r"&lt;right&gt;(.*?)&lt;/right&gt;", r'<div class="right">\1</div>', contents)
    contents = re.sub(r"--(.*?)--", r'<s>\1</s>', contents)

    # Fix escaping for bold, italic, and header formatting
    contents = re.sub(r"(?<!\\)(?<!\\\\)\*\*(?<!\\)(.*?)(?<!\\)(?<!\\\\)\*\*", r'<b>\1</b>', contents)
    contents = re.sub(r"(?<!\\)(?<!\\\\)\*(?<!\\)(.*?)(?<!\\)(?<!\\\\)\*", r'<i>\1</i>', contents)
    
    contents = re.sub(r"(?<!\\)(?<!\\\\)#(?!#)(.*?)(?<!\\)(?<!\\\\)#", r'<h1>\1</h1>', contents)
    contents = re.sub(r"(?<!\\)(?<!\\\\)##(?!#)(.*?)(?<!\\)(?<!\\\\)##", r'<h2>\1</h2>', contents)
    contents = re.sub(r"(?<!\\)(?<!\\\\)###(?!#)(.*?)(?<!\\)(?<!\\\\)###", r'<h3>\1</h3>', contents)
    
    contents = contents.replace("\n", "<br>")
    
    # Remove the backslash if it's followed by a formatting character
    contents = re.sub(r"\\(\*\*|\*|#)", r'\1', contents)
    
    return contents

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', e="404 Page Not Found"), 404

IMAGE_DIR = "static/images/"

@app.route("/upload_image", methods=["POST"])
def upload_image():
    if "image" in request.files:
        image = request.files["image"]
        if image.filename != "":
            # Secure the original filename
            original_filename = secure_filename(image.filename)

            # Generate a unique filename with UUID
            filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1]
            filepath = os.path.join(IMAGE_DIR, filename)
            image.save(filepath)

            # Create the image URL
            image_url = f"/{IMAGE_DIR}{filename}"

            # Get image width and height
            with Image.open(filepath) as img:
                width, height = img.size

            # Store image data using shelve
            with shelve.open("static/images/imagedata") as db:
                db[filename] = {
                    "filename": original_filename,
                    "url": image_url,
                    "width": width,
                    "height": height,
                }

            # Redirect back to the /upload page
            return redirect("/dashboard/upload")

    return redirect("/dashboard/upload")


@app.route("/dashboard/upload", methods=["GET", "POST"])
def upload():
    domain = request.headers.get('Host')
    if request.method == "POST" and "image" in request.files:
        return redirect("/upload_image")

    # Get the list of uploaded images
    image_files = os.listdir(IMAGE_DIR)
    image_urls = [f"http://{domain}/{IMAGE_DIR}{filename}" for filename in image_files]

    return render_template("upload.html", image_urls=image_urls)

@app.route("/dashboard", strict_slashes=False)
def dashboard():
    token = request.cookies.get('CV_LOGIN_TOKEN')
    username = request.cookies.get('CV_un')
    perm = perms(username, token)
    if perm == "admin":
        return "user is admin"
    elif perm == "editor":
        return "user is editor"
    elif perm == False:
        return "not logged in"
    else:
        return "invalid"

def perms(username, token):
    db = shelve.open('databases/users/userdata')
    if username in db.keys():
        if token == db[username][1]:
            if db[username][2] == True:
                db.close()
                return "admin"
            else:
                db.close()
                return "editor"
    db.close()
    return False
        

@app.route("/")
def home():
    return "home"

@app.route("/dashboard/users", strict_slashes=False)
def users():
    db = shelve.open('databases/users/userdata')
    token = request.cookies.get('CV_LOGIN_TOKEN')
    username = request.cookies.get('CV_un')
    if username in db.keys():
        if db[username][2] == True:
            if token == db[username][1]:
                keys = list(db.keys())
                data = []
                for key in keys:
                    data.append(f"<p>{key}: {db[key]}</p>")
                db.close()
                response = """<button onclick="window.location.href='../dashboard/account'">Account</button> <button onclick="window.location.href='../dashboard/new_user'">New user</button>""" + ''.join(data)
                return response
    return "<script>alert('Invalid permissions');history.go(-1);</script>"
    
@app.route("/dashboard/account", strict_slashes=False)
def account():
    db = shelve.open('databases/users/userdata')
    username = request.cookies.get('CV_un')
    token = request.cookies.get('CV_LOGIN_TOKEN')
    if username in db.keys():
        if token == db[username][1]:
            return f"""logged in as {username} <button onclick="window.location.href='/dashboard/logout'">Logout</button><br>
        Is Admin: {db[username][2]}<br>
        Change password:<br>
        <form method="POST" action="/change_password">
    old password: <input type="text" name="old_password" required><br>
    new password: <input type="text" name="new_password" required><br>
    confirm password: <input type="text" name="confirm_password" required><br>
    <input type="submit" value="change password">"""
    response = make_response("Not logged in")
    response.delete_cookie("CV_LOGIN_TOKEN")
    response.delete_cookie("CV_un")
    response.headers["Location"] = "/dashboard/login"
    return response, 302
    
@app.route("/change_password", methods=['POST'], strict_slashes=False)
def change_password():
    username = request.cookies.get('CV_un')
    CV_LOGIN_TOKEN = request.cookies.get('CV_LOGIN_TOKEN')
    old_password = request.form.get("old_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")
    db = shelve.open('databases/users/userdata')
    if username in db.keys():
        if CV_LOGIN_TOKEN == db[username][1]:
            if old_password == db[username][0]:
                if new_password == confirm_password:
                    db[username] = [new_password, db[username][1], db[username][2], db[username][3]]
                    return "<script>alert('Password changed');history.go(-1);</script>"
    return "<script>alert('Invalid information');history.go(-1);</script>"
    
@app.route("/posts/new", strict_slashes=False)
def new():
    db = shelve.open('databases/users/userdata')
    username = request.cookies.get('CV_un')
    CV_LOGIN_TOKEN = request.cookies.get('CV_LOGIN_TOKEN')
    if not username or not CV_LOGIN_TOKEN:
        response = make_response("not logged in")
        response.delete_cookie("CV_LOGIN_TOKEN")
        response.delete_cookie("CV_un")
        return response
    else: 
        if username in db:
            data = db[username]
            if CV_LOGIN_TOKEN == data[1]:
                db.close()
                if data[2] == True:
                    return render_template("makearticle.html", title="", contents="", og_title="", post_route="/_post")
                else:
                    response = make_response("Invalid permissions")
                    response.delete_cookie("CV_LOGIN_TOKEN")
                    response.delete_cookie("CV_un")
                    response.headers["Location"] = "/dashboard/login"
                    return response, 302
            else:
                db.close()
                response = make_response("not logged in")
                response.delete_cookie("CV_LOGIN_TOKEN")
                response.delete_cookie("CV_un")
                response.headers["Location"] = "/dashboard/login"
                return response, 302
    response = make_response("invalid response")
    return response, 500
    
@app.route("/posts/edit/<string:article>", strict_slashes=False)
def edit(article):
    if not article:
        return render_template('404.html', e="404 Article Not Found"), 404 
    db = shelve.open('databases/articles/articles')
    if article in db:
        contents = db[article]
        db.close()
        db = shelve.open('databases/users/userdata')
        username = request.cookies.get('CV_un')
        CV_LOGIN_TOKEN = request.cookies.get('CV_LOGIN_TOKEN')
        if not username or not CV_LOGIN_TOKEN:
            response = make_response("not logged in")
            response.delete_cookie("CV_LOGIN_TOKEN")
            response.delete_cookie("CV_un")
            return response
        else: 
            if username in db:
                data = db[username]
                if CV_LOGIN_TOKEN == data[1]:
                    if data[2] == True:
                        return render_template("makearticle.html", title=article, contents=contents, og_title=article, post_route="/_edit")
                    else:
                        response = make_response("Invalid permissions")
                        response.delete_cookie("CV_LOGIN_TOKEN")
                        response.delete_cookie("CV_un")
                        response.headers["Location"] = "/dashboard/login"
                        return response, 302
                else:
                    db.close()
                    response = make_response("not logged in")
                    response.delete_cookie("CV_LOGIN_TOKEN")
                    response.delete_cookie("CV_un")
                    response.headers["Location"] = "/dashboard/login"
                    return response, 302
        response = make_response("Invalid response")
        return response, 500
    else:
        return render_template('404.html', e="404 Article Not Found"), 404
    
@app.route('/dashboard/logout', strict_slashes=False)
def logout():
    response = make_response("Logged out")
    response.delete_cookie("CV_LOGIN_TOKEN")
    response.delete_cookie("CV_un")
    response.headers["Location"] = "/dashboard/login"
    return response, 302

@app.route('/li', methods=['POST'], strict_slashes=False)
def li():
    db = shelve.open('databases/users/userdata')
    username = str(request.form.get('username'))
    password = str(request.form.get('password'))
    if username in db:
        data = db[username]
        userpass = data[0]
        if password == userpass:
            db.close()
            response = make_response("logged in")
            expiration = datetime.datetime.now() + datetime.timedelta(days=365 * 10)
            response.set_cookie('CV_LOGIN_TOKEN', data[1], expires=expiration)
            response.set_cookie('CV_un', username, expires=expiration)
            response.headers["Location"] = "/posts"
            return response, 302
        else:
            db.close()
            return "login info incorrect"
    else:
        db.close()
        return "login info incorrect"

@app.route('/si', methods=['POST'], strict_slashes=False)
def si():
    db = shelve.open('databases/users/userdata')
    token = request.cookies.get('CV_LOGIN_TOKEN')
    username = request.cookies.get('CV_un')
    if username in db.keys():
        if db[username][2] == True:
            if db[username][1] == token:    
                username = str(escape(request.form.get('username')[:22]))
                print(request.form.get('admin'))
                if request.form.get('admin') == "on":
                    make_admin = True
                else:
                    make_admin = False
                data = [str(request.form.get('password')), str(uuid.uuid4()), make_admin]
                if username.lower() in [key.lower() for key in db.keys()]:
                    db.close()
                    return "<script>alert('Account already exists');history.go(-1);</script>", 200
                else:
                    db[username] = data
                    db.close()
                    response = make_response(f"Created account<br>{username}<br>{str(data)}")
                    response.headers["Location"] = "/dashboard/users"
                    return response, 302
    return "<script>alert('Invalid permissions');history.go(-1);</script>"
        
@app.route("/dashboard/login", strict_slashes=False)
def login():
    return """<meta name='viewport' content='width=device-width, initial-scale=1'><form method="POST" action="/li">
    username: <input type="text" name="username" required maxlength="22"><br>
    password: <input type="password" name="password" required><br>
    <input type="submit" value="login">
</form>"""

@app.route("/dashboard/new_user", strict_slashes=False)
def signup():
    return """<style>.admin-tooltip {
  position: relative;
  border-radius: 25px;
}

.admin-tooltip::after {
  content: "Allows the user to create new accounts";
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  background-color: #000;
  color: #fff;
  padding: 5px;
  border-radius: 5px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
}

.admin-tooltip:hover::after {
  opacity: 1;
}</style><meta name='viewport' content='width=device-width, initial-scale=1'><form method="POST" action="/si" autocomplete="off">
    username: <input type="text" name="username" required maxlength="22"><br>
    passsword: <input type="text" name="password" required><br>
    admin access <button class="admin-tooltip">?</button>: <input type="checkbox" name="admin"><br>
    <input type="submit" value="Create account">
</form>"""

@app.route("/posts", strict_slashes=False)
def posts():
    username = request.cookies.get('CV_un')
    if not username:
        editor = False
    else:
        db = shelve.open("databases/users/userdata")
        if username in list(db.keys()):
            editor = True
            if db[username][2] == True:
                admin_buttons = f"""<button onclick="window.location.href='./dashboard/new_user'">New user</button>"""
            else:
                admin_buttons = ""
        else:
            editor = False
    db = shelve.open('databases/articles/articles')

    # Get all keys from the database
    keys = list(db.keys())

    # Check if the editor variable is True
    if editor:
        # Create a list of buttons
        buttons = []
        for key in keys:
            # Create the URL for the edit button
            edit_url = f"/posts/edit/{key}"
            # Create the URL for the view button
            post_url = f"/post{key}"
            # Create the button element
            button = f'{key} <button onclick="window.location.href=\'{post_url}\'">View post</button> <button onclick="window.location.href=\'{edit_url}\'">Edit post</button>'
            # Add the button to the list
            buttons.append(button)
        
        # Join the buttons with new lines
        buttons_html = '<br>'.join(buttons)
        html = f"""<button onclick="window.location.href='./dashboard/account'">Account</button> <button onclick="window.location.href='./posts/new'">New post</button> {admin_buttons}<br><br>""" + buttons_html
    else:
        # Create a list of buttons
        buttons = []
        for key in keys:
            # Create the URL for the veiw button
            post_url = f"/post/{key}"
            # Create the button element
            button = f'{key} <button onclick="window.location.href=\'{post_url}\'">View post</button>'
            # Add the button to the list
            buttons.append(button)
        
        # Join the buttons with new lines
        buttons_html = '<br>'.join(buttons)
        html = buttons_html

    db.close()
    return html

@app.route("/_edit", methods=["POST"], strict_slashes=False)
def make_edit():
    og_title = request.form["og-title"]
    title = request.form["title"]
    contents = request.form["contents"]
    db = shelve.open('databases/articles/articles')
    if title not in db:
        return "<script>alert('Article not found');history.go(-1);</script>"
    if title == "":
        return "<script>alert('Title cannot be blank');history.go(-1);</script>"
    if og_title != title:
        del db[og_title]
    db[title] = contents
    response = make_response("Article edited")
    response.headers["Location"] = f"/post/{title}"
    return response, 302

@app.route("/_post", methods=["POST"], strict_slashes=False)
def make_post():
    title = request.form["title"]
    contents = request.form["contents"]
    db = shelve.open('databases/articles/articles')
    if title in db:
        return "<script>alert('Article already exists');history.go(-1);</script>"
    if title == "":
        return "<script>alert('Title cannot be blank');history.go(-1);</script>"
    db[title] = contents
    response = make_response("Article created")
    response.headers["Location"] = f"/article/{title}"
    return response, 302

@app.route("/preview", methods=["POST"], strict_slashes=False)
def preview():
    title = request.form["title"]
    contents = request.form["contents"]
    contents = format(contents)
    return render_template("article.html", article=title, contents=contents)

@app.route("/post/<string:article>", strict_slashes=False)
def post(article):
    if not article:
        return render_template('404.html', e="404 Article Not Found"), 404 
    db = shelve.open('databases/articles/articles')
    if article in db:
        contents = db[article]
        contents = format(contents)
        db.close()
        return render_template("article.html", article=article, contents=contents)
    else:
        return render_template('404.html', e="404 Article Not Found"), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)