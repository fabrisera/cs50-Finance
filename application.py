import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# export API_KEY=pk_524638964d8845ffa4285652da9a0162
@app.route("/")
@login_required
def index():
    data = db.execute(
        "SELECT SUM(total), SUM(nshares), \
        symbol FROM transactions WHERE user_id = ? \
        GROUP BY symbol", session["user_id"])
    cash_d = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    cash = round(cash_d[0]['cash'], 2)
    i = 0
    c = 0
    lista = []
    for row in data:
        data[i]['current'] = lookup(row['symbol'])
        data[i]['tot'] = round((data[i]['current']['price']) * (data[i]['SUM(nshares)']), 2)
        c += (data[i]['current']['price']) * (data[i]['SUM(nshares)'])
        if data[i]['SUM(nshares)'] == 0:
            lista.append(i)
        i += 1
    lista.sort(reverse=True)
    for b in lista:
        del data[b]
    c = round(c, 2)
    return render_template('index.html', data=data, cash=cash, total=c, ass=cash + c)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == 'GET':
        return render_template('buy.html')
    else:
        buying = lookup(request.form.get("symbol"))
        if buying == None:
            return apology("invalid symbol", 7)
        if request.form.get("shares") == "":
            return apology('invalid number of shares')
        sharenum = int(request.form.get("shares"))
        if sharenum <= 0:
            return apology('invalid number of shares')
        sy = request.form.get("symbol")
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        result = cash[0]['cash'] - (buying["price"] * sharenum)
        cost = (buying["price"] * sharenum)
        if result < 0:
            return apology('Insufficient Cash')
        db.execute("UPDATE users SET cash = ? WHERE id = ?",
                   result, session["user_id"])
        db.execute("INSERT INTO transactions (user_id, symbol, date, total, nshares, type) \
        VALUES (?,?,?,?,?,?)", session["user_id"], sy,
                   datetime.datetime.now(), cost, sharenum, "BUY")
        return redirect("/")


@app.route("/history")
@login_required
def history():
    data = db.execute("SELECT * FROM transactions WHERE user_id = ?", session["user_id"])
    i = 0
    for row in data:
        if data[i]['total'] != None:
            data[i]['total'] = round(data[i]['total'], 2)
        i += 1
    return render_template("history.html", data=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == 'GET':
        return render_template("request.html")
    else:
        data = lookup(request.form.get("symbol"))
        if data == None:
            return apology('invalid symbol')
        logo = ""
    for i in range(len(data["name"])):
        if (data["name"][i]).isalpha() == True:
            logo += data["name"][i]
        else:
            break
    return render_template("requested.html", name=data["name"],
                           price=data["price"], sym=data["symbol"], logo=logo)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        username = request.form.get("username")
        users = db.execute("SELECT username FROM users")
        for row in users:
            if username == row["username"]:
                return apology('username already in use')
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if len(username) == 0 or username.isspace() == True or len(password) == 0\
                or password != confirmation:
            return apology('Invalid Password/Password Not Matching')
        else:
            db.execute("INSERT INTO users (username, hash) VALUES (?,?)", username,
                       generate_password_hash(password))
            return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == 'GET':
        drop = db.execute("SELECT (symbol), SUM(nshares) FROM transactions WHERE user_id = ? GROUP BY symbol", session['user_id'])
        lista = []
        i = 0
        for row in drop:
            if drop[i]['SUM(nshares)'] == 0:
                lista.append(i)
            i += 1
        lista.sort(reverse=True)
        for b in lista:
            del drop[b]
        return render_template('selling.html', drop=drop)
    else:
        if request.form.get("symbol") == None:
            return apology('Invalid Symbol')
        selling = lookup(request.form.get("symbol"))
        if selling == None:
            return apology('Invalid Symbol')
        if request.form.get("shares") == "":
            return apology('Invalid number of shares')
        sy = request.form.get("symbol")
        sharenum = int(request.form.get("shares"))
        p = db.execute("SELECT SUM(nshares) FROM transactions WHERE user_id = ? AND symbol = ?", session['user_id'], sy)
        if sharenum <= 0:
            return apology('invalid number of shares')
        if p[0]['SUM(nshares)'] < sharenum:
            return apology('not enough shares')
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        result = cash[0]['cash'] + (selling["price"] * sharenum)
        profit = (selling["price"] * sharenum)
        db.execute("UPDATE users SET cash = ? WHERE id = ?",
                   result, session["user_id"])
        db.execute("INSERT INTO transactions (user_id, symbol, date, total, nshares, type) \
        VALUES (?,?,?,?,?,?)", session["user_id"], sy, datetime.datetime.now(), -profit, -sharenum, "SELL")
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
