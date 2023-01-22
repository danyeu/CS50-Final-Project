# Beat the Market: 2022

## Overview
* "Beat the Market: 2022" is a web application in which users can build their own portfolio of stocks and see how it performed over 2022 versus the performance of the S&P 500 ("the market").

## Tech Stack
* There are a number of interconnecting technologies used for this app.

### Front End
* JavaScript, HTML, and CSS are used for the webpages and their interactive elements.
    * Bootstrap 5.1 is used to create familiar, appealing, and user-friendly website layout and interactive elements.
    * Chart.js is used similarly to handle the displaying of graphs used throughout the website.
    * JavaScript is used for the more dynamic webpage elements (disappearing error/success messages, client-side input validation).

### Back End
* Python, Flask, and SQLite are used to handle the behind the scenes data processing.
    * Python and Flask handle the interactions between front end and back end (partially via Jinja), reading and writing of data from the database, calculation of portfolio details, and webpage routing.
    * SQLite is used to manage the database of user account details, user portfolio details, and static stock and index details.

## Webpage Breakdown

### Welcome
* The welcome page (the site's index) provides a simple description of the web app.
    * (Note the S&P 500 return of -19.44% are official S&P 500 numbers, assuming a stock is held at the end of the last trading day of 2021. A -19.95% return is observed in the S&P 500 graph later on, and this is the return obtained if the first trade was placed at the end of the first trading day of 2022.)
* The web app features a consistent "dark-mode" themed colour scheme with light grey text and neon green and neon red accents.
    * Consistency is ensured via the use of a layout html page with Jinja, and styling in CSS.

### Register
* Most of the web app is locked behind a login (enforced by Flask).
* To register, a unique username and two matching passwords are needed.
* All validation is done server side, which includes any empty details, non-matching passwords, and taken usernames.
* For invalid inputs, a disappearing error message floats at the bottom of the screen (via JS).
* On successful registration, the username, hashed password, and the account creation date are added to the SQL database, which autoincrements a unique user ID that is stored in the session and used thereafter to validate which user is logged in.
* The user is automatically logged in after successful registration.

### Login
* Similar to registration, all validation is done server-side.
* If matching login details are found, the user is logged in and their user id stored as a cookie.
    * Else, an error message is displayed.

### Logout
* The user is logged out by clearing the session in Flask, and is redirected to the index.

### Account
* Displays the user's username, account creation date, and the option to change the user's password.
* Validation happens server-side, with a success message for matching valid passwords (hashed password updated in the database), and an error message otherwise.

### Stocks
* To help with portfolio building, the user can view data for each of the 50 stocks available.
    * These are the largest 50 companies in the S&P 500 as of the end of 2022.
* The stock is validated server-side, and upon selecting and submitting a valid stock, the annual return and price timeseries for that stock for 2022 is requested from the database.
* The data is displayed on a graph with consistent theming via Chart.js and a Jinja loop.

### Portfolio
* The user's portfolio is displayed in a table, with one row for each of the 50 stocks, and one row for cash.
* In each row, the stock has its own weight, which defaults to 0 on user creation.
    * The weights are integers representing the percentage of the portfolio held in each stock.
    * These weights are requested from the database when the page is visited.
* The amount of the portfolio held in cash is simply 100 - the sum of all stock weights.
* The user can edit the weights of each stock, and the cash will adjust itself via a JS script.
* Client-side validation is in place via number forms and a JS script disabling the "Update" button.
* Server-side validation handles all individual weight being integers between 0 and 100 inclusive, and weights summing to 100 at most.
    * Failing any of these returns an error message (via url) that is displayed for user feedback.
* Upon pressing the "Update" button with valid weights, the database is updated with only the weights that have changed (all new weights are checked against the weights that the page loaded with to save SQL queries), and a success message is displayed (via url) for user feedback.
* Upon pressing "Reset", all weights are reset to 0, and a success message is displayed (via url) for user feedback.

### Results
* The return for the user's portfolio and S&P 500 are displayed at the top of the page, so the user immediately sees how their portfolio performed.
* The price timeseries for the user's portfolio, the S&P 500, and cash are displayed on the same graph below.
* The weights for each stock are requested from the database.
    * From this, the starting number of stocks for each stock are calculated.
* To calculate the price timeseries for the portfolio, these number of stocks owned are multiplied by the price for each stock at each point in time (~250 trading days).
    * Any weight unallocated is treated as cash (remains at 100% value).
    * The result is a timeseries of indexed prices (indexed to 100 at the first date).
* The graph for the S&P 500 is simply requested from the database, and the graph for "Cash" simply remains at 100.
* All three timeseries are displayed on the same graph in different colours with consistent theming via Chart.js and Jinja loops.