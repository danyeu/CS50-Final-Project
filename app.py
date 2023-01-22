import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from flask import redirect, render_template, request, session
from functools import wraps
from datetime import datetime

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///data.db")


# Global dictionary of 50 stocks' data
db_names_raw = db.execute("SELECT * FROM names")
db_names={}
for i in db_names_raw:
    db_names[i["symbol"]] = {"symbol": i["symbol"], "name": i["name"], "return": i["return"]}


# Decorate routes to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Format number as %
def pct(value):
    return f"{100 * value:,.2f}%"


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Index
@app.route("/")
def index():
    return render_template("welcome.html")


# Register user
@app.route("/register", methods=["GET", "POST"])
def register():
    # Force logout
    session.clear()

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("register.html", alert_text = "Invalid username!")
        # Ensure both passwords were submitted
        if (not request.form.get("password") or (not request.form.get("confirmation"))):
            return render_template("register.html", alert_text = "Invalid password(s)!")
        # Ensure passwords match
        if request.form.get("confirmation") != request.form.get("password"):
            return render_template("register.html", alert_text = "Passwords do not match!")

        # Ensure username is free
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 0:
            return render_template("register.html", alert_text = "Username already taken!")

        # Add to database
        db.execute("INSERT INTO users (username, hash, creation_date) VALUES (?,?,?)", request.form.get("username"), generate_password_hash(request.form.get("password")), datetime.today().strftime('%Y-%m-%d'))

        # Query database for username to get ID
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Initialise portfolio
        for symbol in db_names.keys():
            db.execute("INSERT INTO portfolios(id, symbol, name, weight) VALUES (?, ?, ?, 0)", session["user_id"], symbol, db_names[symbol]["name"])

        return redirect("/")

    else:
        return render_template("register.html", alert_text = "NONE")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    # Force logout
    session.clear()

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", alert_text = "Invalid username!")

        # Ensure password was submitted
        if not request.form.get("password"):
            return render_template("login.html", alert_text = "Invalid password!")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", alert_text = "Wrong username or password!")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html", alert_text = "NONE")


# Logout
@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()

    return redirect("/")


# Account details / change password
@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]["username"]
    creation_date = db.execute("SELECT creation_date FROM users WHERE id = ?", session["user_id"])[0]["creation_date"]

    if request.method == "POST":
        # Ensure both passwords were submitted
        if (not request.form.get("password")) or (not request.form.get("confirmation")):
            return render_template("account.html", username = username, creation_date = creation_date, alert_text = "Invalid password(s)!")

        # Ensure passwords match
        if request.form.get("confirmation") != request.form.get("password"):
            return render_template("account.html", username = username, creation_date = creation_date, alert_text = "Passwords do not match!")

        # Update database
        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(request.form.get("password")), session["user_id"])

        # Success message
        return render_template("account.html", username = username, creation_date = creation_date, alert_text = "Success")

    else:
        return render_template("account.html", username = username, creation_date = creation_date, alert_text = "NONE")


# Individual stock prices
@app.route("/stocks", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")

        # Ensure stock was submitted, and is in out list of stocks
        if (not symbol) or (symbol not in db_names.keys()):
            return render_template("stocks.html", db_names_raw = db_names_raw, alert_text = "Invalid stock!")

        # Lists for chartjs graph datasets
        dataset_dates = []
        dataset_prices = []
        ts = db.execute("SELECT date, price FROM stocks WHERE symbol = ?", symbol)
        for day in ts:
            dataset_dates.append(datetime.strptime(day["date"], "%Y-%m-%d").strftime("%d %b"))
            dataset_prices.append(float(day["price"]))

        return render_template("stock.html", name = db_names[symbol]["name"], symbol = symbol, r = pct(db_names[symbol]["return"]), dataset_dates = dataset_dates, dataset_prices = dataset_prices)

    else:
        return render_template("stocks.html", db_names_raw = db_names_raw, alert_text = "NONE")


# User's portfolio
@app.route("/portfolio/", methods=["GET", "POST"])
@login_required
def portfolio():
    db_portfolios_raw = db.execute("SELECT * FROM portfolios WHERE id = ?", session["user_id"])
    cash = int(db.execute("SELECT (100 - sum(weight)) AS cash FROM portfolios WHERE id = ?", session["user_id"])[0]["cash"])

    if request.method == "POST":
        # Grab old weights
        old_weights_raw = db.execute("SELECT symbol, weight FROM portfolios WHERE id = ?", session["user_id"])

        # For each symbol, check if the weight is valid (was submitted and in [0,100])
        # If so, add to the new weights list, else return an error message
        weights = []
        for symbol in db_names.keys():
            weight = request.form.get(symbol)
            if (not weight) or (not weight.isdigit()):
                return redirect("/portfolio/?msg=Invalid%20weights!")
            weight = int(weight)
            if (weight < 0) or (weight > 100):
                return redirect("/portfolio/?msg=Invalid%20weights!")
            weights.append(weight)

        # Ensure sum of weights is <= 100 (>0 handled above)
        if sum(weights) > 100:
            return redirect("/portfolio/?msg=Invalid%20weights!")

        # Update database (only weights that have changed)
        for i, symbol in enumerate(db_names.keys()):
            if old_weights_raw[i]["weight"] != weights[i]:
                db.execute("UPDATE portfolios SET weight = ? WHERE id = ? AND symbol = ?", weights[i], session["user_id"], symbol)

        return redirect("/portfolio/?msg=Success")

    else:
        # Alert text depends on url "msg="
        if request.args.get('msg'):
            alert_text = request.args.get('msg')
        else:
            alert_text = "NONE"

        return render_template("portfolio.html", db_portfolios_raw = db_portfolios_raw, cash = cash, alert_text = alert_text)


# Reset portfolio
@app.route("/resetportfolio", methods=["GET", "POST"])
@login_required
def resetportfolio():
    # Update database: set all weights to 0
    db.execute("UPDATE portfolios SET weight = 0 WHERE id = ?", session["user_id"])

    return redirect("/portfolio/?msg=Success")


# Show results
@app.route("/results")
@login_required
def results():
    db_portfolios_raw = db.execute("SELECT * FROM portfolios WHERE id = ?", session["user_id"])
    cash = int(db.execute("SELECT (100 - sum(weight)) AS cash FROM portfolios WHERE id = ?", session["user_id"])[0]["cash"])
    db_dates_raw = db.execute("SELECT distinct(date) AS date FROM stocks")

    # Calculate portfolio return using annual returns in database
    portfolio_return = 0
    for i, symbol in enumerate(db_names.keys()):
        portfolio_return += db_portfolios_raw[i]["weight"] * db_names[symbol]["return"]
    portfolio_return /= 100

    # Create dictionary of prices of all stocks
    # db_prices = outer: key: symbol, value: list[key: date, price]
    db_prices = {}
    for symbol in db_names.keys():
        db_prices[symbol] = db.execute("SELECT date, price FROM stocks WHERE symbol = ?", symbol)

    # Dictionary of number of each stock owned at the start of the year
    stocks_owned = {}
    for i, symbol in enumerate(db_names.keys()):
        stocks_owned[symbol] = db_portfolios_raw[i]["weight"] / db_prices[symbol][0]["price"]

    # Dictionary of number of each stock owned at the start of the year
    # key:date, value:price
    portfolio_prices = {}
    for d, date in enumerate(db_dates_raw):
        portfolio_prices[date["date"]] = cash
        for symbol in db_names.keys():
            portfolio_prices[date["date"]] += stocks_owned[symbol] * db_prices[symbol][d]["price"]

    # Lists for chartjs graph datasets
    dataset_dates = []
    for date in portfolio_prices.keys():
        dataset_dates.append(datetime.strptime(date, "%Y-%m-%d").strftime("%d %b"))
    dataset_prices = []
    for price in portfolio_prices.values():
        dataset_prices.append(round(price,2))
    dataset_prices_sp = []
    for row in db.execute("SELECT price FROM sp"):
        dataset_prices_sp.append(round(float(row["price"]),2))

    return render_template("results.html", r = pct(portfolio_return), dataset_dates = dataset_dates, dataset_prices = dataset_prices, dataset_prices_sp = dataset_prices_sp)