from flask import Flask, render_template, request, redirect, url_for
from morse_code_converter import converter
import sqlite3
from flask_bootstrap5 import Bootstrap
import requests
from dotenv import load_dotenv
import os

dotenv_path = os.path.join(os.path.dirname(__file__), 'keys.env') # Assumes keys.env is in the same directory as server.py
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"Warning: Environment file not found at {dotenv_path}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_sensible_default_secret_key_for_development')

Bootstrap(app)

BEARER_TOKEN_MOVIE = os.environ.get('TMDB_BEARER_TOKEN')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/morse' ,methods=['GET', 'POST'])
#simple texto to morse converter using user input.
def morse():
    texting = 'Codigo'
    text2 = converter(texting)
    if request.method == 'POST':
        texting=request.form['convert']
        text2=converter(texting)
    return render_template('morse.html',text=texting,coded=text2)

@app.route("/movies", methods=['GET'])  # Assuming POST is not used here
def movies():
    movies_list = []
    duplicated = False
    try:
        with sqlite3.connect('movies.db') as db:  # Use a context manager
            # Optional: db.row_factory = sqlite3.Row to access columns by name
            cursor = db.cursor()
            cursor.execute("SELECT * FROM movie")  # Consider selecting specific columns
            result = cursor.fetchall()
            # Process result into movies_list
            for row_data in result:
                movies_list.append(list(row_data))  # Or dict(row_data) if using row_factory
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        # Handle the error appropriately, e.g., flash a message or render an error page
        pass

    show_duplicate_error = request.args.get('error') == 'True'
    return render_template("movies.html", movie=movies_list, error=show_duplicate_error)
@app.route("/selected",methods=['GET', 'POST'])
def selected():
    # Conects to DB and save the new movie chosen by the user into it, if title already
    #in the list sends a querry string in the html and redirect to movies.
    if request.method == 'POST':
        db = sqlite3.connect('movies.db')
        cursor=db.cursor()
        print(request.form)

        img=request.form.get('image')
        title=request.form.get('title')
        desc=request.form.get('overview')
        year=request.form.get('year')
        rating=request.form.get('rating')
        review=request.form.get('review')
        try:
            cursor.execute(f'INSERT INTO Movie VALUES(?,?,?,?,?,?)', (title,year,desc,rating,review,img))
            db.commit()
            db.close()
        except sqlite3.IntegrityError:
            print(f'Movie Already Exists in Database')
            duplicated=True



        return redirect(url_for('movies',dup=duplicated))

#searching for movie
@app.route("/add",methods=['GET', 'POST'])
#searchs for the movie input by the user in the MDB DB throught their API and displays
#the movie found, if the user wishes he can leave a comment about the movie and add it.
def add():
    title=''
    overview=''
    rating=''
    year=''
    img=''
    ans=''
    if request.method == 'POST':
        # ... (variable initializations: title, overview, etc.)
        movie_searched = request.form.get('movie_searched')  # Use .get for safety

        if not movie_searched:
            ans = "Please enter a movie title to search."
        elif not BEARER_TOKEN_MOVIE:
            ans = "API token is not configured. Cannot search for movies."
            print("Error: TMDB_BEARER_TOKEN is not set.")
        else:
            url = "https://api.themoviedb.org/3/search/movie"  # Base URL
            params = {
                "query": movie_searched,
                "include_adult": "false",
                "language": "en-US",
                "page": "1"
            }
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {BEARER_TOKEN_MOVIE}"
            }

            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)

                filme = response.json()
                if filme.get('results'):  # Check if 'results' key exists and is not empty
                    first_result = filme['results'][0]
                    ans = 'Is this the movie you were thinking about?'
                    title = first_result.get('original_title')
                    overview = first_result.get('overview')
                    rating = first_result.get('vote_average')
                    year = first_result.get('release_date')
                    img = first_result.get('poster_path')
                else:
                    ans = 'No movies were found matching your search.'
            except requests.exceptions.RequestException as e:
                ans = f'Unable to search due to an API error: {e}'
                print(f"API request failed: {e}")
            except ValueError:  # Catches JSON decoding errors
                ans = 'Error processing API response.'
                print("Failed to decode JSON from API response")

    return render_template("add.html", ans=ans, title=title, overview=overview, rating=rating, year=year, img=img)

@app.route('/test-bootstrap')
def test_bootstrap_route():
    from flask import render_template_string

    # ---- START DIAGNOSTIC ----
    print("--- Checking Jinja Environment Globals ---")
    if 'bootstrap' in app.jinja_env.globals:
        print("'bootstrap' IS IN app.jinja_env.globals.")
        # You could even try to inspect it:
        # print(type(app.jinja_env.globals['bootstrap']))
    else:
        print("'bootstrap' IS NOT IN app.jinja_env.globals.")
    print("--- End Checking Jinja Environment Globals ---")
    # ---- END DIAGNOSTIC ----

    minimal_html = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Bootstrap Minimal Test</title>
        {% if bootstrap %}
            {{ bootstrap.load_css() }}
            <style> body { padding: 20px; } </style>
        {% else %}
            <!-- Bootstrap object not found! -->
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            <style> body { background-color: #ffdddd !important; padding: 20px; } </style>
        {% endif %}
      </head>
      <body>
        <div class="container">
          <h1>Minimal Bootstrap Test</h1>
          {% if bootstrap %}
            <p class="text-success">Bootstrap object seems to be available!</p>
          {% else %}
            <p class="text-danger"><strong>Error: 'bootstrap' is undefined in this minimal template.</strong></p>
          {% endif %}
          <button class="btn btn-primary">Test Button</button>
        </div>
        {% if bootstrap %}
            {{ bootstrap.load_js() }}
        {% endif %}
      </body>
    </html>
    """
    try:
        print("Attempting to render minimal_html...")
        return render_template_string(minimal_html)
    except Exception as e:
        print(f"Error in test_bootstrap_route: {e}")
        return f"Error in test_bootstrap_route: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)

    ##venv\Scripts\activate
