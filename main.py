from flask import Flask, render_template, request, make_response, abort
from markupsafe import escape
import shelve
import re

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

@app.route("/")
def home():
    return render_template("makearticle.html")
    
@app.route("/post", methods=["POST"], strict_slashes=False)
def post():
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

@app.route("/article/<string:article>", strict_slashes=False)
def articles(article):
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