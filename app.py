from flask         import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms       import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash  import sha256_crypt
from functools     import wraps


# Kullanici Giris Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "loggedIn" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapınız...", "danger")
            return redirect(url_for("login"))
    return decorated_function

# Kullanici Kayit Formu
class RegisterForm(Form):
    name     = StringField("İsim Soyisim",  validators=[validators.DataRequired(), validators.Length(min=4, max=25)])
    username = StringField("Kullanıcı Adı", validators=[validators.DataRequired(), validators.Length(min=5, max=35)])
    email    = StringField("E-mail",        validators=[validators.DataRequired(), validators.Email("Lütfen geçerli bir e-mail adresi giriniz")])
    password = PasswordField("Parola",      validators=[validators.DataRequired(message="Lütfen bir parola giriniz"),validators.EqualTo(fieldname="confirm", message="Parolanız uyuşmuyor")])
    confirm  = PasswordField("Parolanızı Doğrulayınız")

# Login Kayit Formu
class LoginForm(Form):
    username = StringField("Kullanıcı adı")
    password = StringField("Parola")

# Makale Form
class ArticleForm(Form):
    title   = StringField("Makale Başlığı",  validators=[validators.Length(min=5, max=100)])
    content = TextAreaField("Makale İçeriği", validators=[validators.Length(min=10)])
    

app            = Flask(__name__)
app.secret_key = "blog"

app.config["MYSQL_HOST"]         = "localhost"
app.config["MYSQL_USER"]         = "root"
app.config["MYSQL_PASSWORD"]     = ""
app.config["MYSQL_DB"]           = "blog"
app.config["MYSQL_CURSORCLASS"]  = "DictCursor"
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/articles')
def articles():
    cursor = mysql.connection.cursor()
    query  = "SELECT * FROM articles"
    result = cursor.execute(query)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles)
    else:
        return render_template("articles.html")


@app.route('/article/<string:id>')
def article(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(query, (id, ))

    if result > 0:
        article = cursor.fetchone()
        cursor.close()
        return render_template("article.html", article=article)
    else:
        return render_template("article.html")


@app.route('/dashboard')
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query  = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(query, (session["name"], ))

    if result > 0:
        articles = cursor.fetchall()
        cursor.close()
        return render_template("dashboard.html", articles=articles)
    else:
        return render_template("dashboard.html")


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name     = form.name.data
        username = form.username.data
        email    = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        query = "INSERT INTO users(name, username, email, password) VALUES (%s,%s,%s,%s)"
        cursor.execute(query, (name, username, email, password))
        mysql.connection.commit()
        cursor.close()
        
        flash("Başarıyla kayıt oldunuz...", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username        = form.username.data
        passwordEntered = form.password.data

        cursor = mysql.connection.cursor()
        query  = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(query, (username,))
        
        if result > 0:
            data = cursor.fetchone()
            realPassword = data["password"]
            if sha256_crypt.verify(passwordEntered, realPassword):
                flash("Başarıyla giriş yaptınız", "success")
                session["loggedIn"] = True
                session["username"] = username
                session["name"]     = data["name"]
                return redirect(url_for("index"))
            else:
                flash("Parolayı yanlış girdiniz", "danger")
                return redirect(url_for("login"))
        else:
            flash("Kullanıcı bulunamadı...","danger")
            return redirect(url_for("login"))

        cursor.close()
    return render_template("login.html", form=form,)


@app.route('/logout')
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız", "success")
    return redirect(url_for("index"))


@app.route('/addarticle', methods=["GET", "POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title   = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        query = "INSERT INTO articles(title, author, content) VALUES (%s,%s,%s)"
        cursor.execute(query, (title, session["name"], content))
        mysql.connection.commit()
        cursor.close()
        
        flash("Makale başarıyla eklendi!", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("addarticle.html", form=form)


@app.route('/edit/<string:id>', methods=["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query  = "SELECT * FROM articles WHERE id = %s and author = %s"
        result = cursor.execute(query, (id, session["name"]))


        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok", "danger")
            return redirect(url_for("index"))
        else:
            article           = cursor.fetchone()
            form              = ArticleForm()
            form.title.data   = article["title"]
            form.content.data = article["content"]
            cursor.close()
            return render_template("update.html", form=form)
    else:
        form       = ArticleForm(request.form)
        newTitle   = form.title.data
        newContent = form.content.data
        query2     = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(query2, (newTitle, newContent, id))
        mysql.connection.commit()
        cursor.close()
        
        flash("Makale başarıyla güncellendi...", "success")
        return redirect(url_for("dashboard"))


@app.route('/delete/<string:id>')
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query  = "SELECT * FROM articles " \
             "WHERE author = %s "      \
             "AND   id     = %s"
    result = cursor.execute(query, (session["name"], id))

    if result > 0:
        deleteQurey = "DELETE FROM articles " \
                      "WHERE id = %s"
        cursor.execute(deleteQurey, (id, ))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya silme yetkiniz yok!", "danger")
        return redirect(url_for("index"))


    return render_template("delete.html")


@app.route('/search', methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor  = mysql.connection.cursor()
        query   = "SELECT * FROM articles "               \
                "WHERE title   LIKE '%" + keyword + "%' " \
                "OR    author  LIKE '%" + keyword + "%' " \
                "OR    content LIKE '%" + keyword + "%'"
        result  = cursor.execute(query)

        if result == 0:
            flash("Aradığınız sonuç bulunamadı...", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles=articles)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True)
