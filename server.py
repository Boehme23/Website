import os
import sqlite3

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, session, request, redirect, url_for, send_file, \
    jsonify  # <-- Ensure 'session' is imported
from flask_bootstrap5 import Bootstrap
from spotipy import Spotify
from spotipy.cache_handler import FlaskSessionCacheHandler  # Keep this import
from spotipy.oauth2 import SpotifyOAuth

from morse_code_converter import converter
from watermark import add_watermark

dotenv_path = os.path.join(
    os.path.dirname(__file__), ".env"
)
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"Warning: Environment file not found at {dotenv_path}")

# Initialize app first
app = Flask(__name__)

# Set secret key BEFORE you try to use session
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "a_sensible_default_secret_key_for_development"
)

# *** REMOVE THIS LINE IF IT'S STILL THERE: ***
# cache_handler = FlaskSessionCacheHandler(session) # DELETE THIS LINE

app.config["BEARER_TOKEN_MOVIE"] = os.environ.get("TMDB_BEARER_TOKEN")
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
BEARER_TOKEN_MOVIE = app.config.get("BEARER_TOKEN_MOVIE")
Bootstrap(app)


@app.route("/")
def home():
    return render_template("Matrix.html")
@app.route("/index")
def index():
    return render_template("index.html")



@app.route("/morse", methods=["GET", "POST"])
# simple texto to morse converter using user input.
def morse():
    texting = "Codigo"
    text2 = converter(texting)
    if request.method == "POST":
        texting = request.form["convert"]
        text2 = converter(texting)
    return render_template("morse.html", text=texting, coded=text2)


@app.route("/movies", methods=["GET"])  # Assuming POST is not used here
def movies():
    movies_list = []
    duplicated = False
    try:
        with sqlite3.connect("movies.db") as db:  # Use a context manager
            # Optional: db.row_factory = sqlite3.Row to access columns by name
            cursor = db.cursor()
            cursor.execute("SELECT * FROM movie")  # Consider selecting specific columns
            result = cursor.fetchall()
            # Process result into movies_list
            for row_data in result:
                movies_list.append(
                    list(row_data)
                )  # Or dict(row_data) if using row_factory
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        # Handle the error appropriately, e.g., flash a message or render an error page
        pass

    show_duplicate_error = request.args.get("error") == "True"
    return render_template("movies.html", movie=movies_list, error=show_duplicate_error)


@app.route("/selected", methods=["GET", "POST"])
def selected():
    # Conects to DB and save the new movie chosen by the user into it, if title already
    # in the list sends a querry string in the html and redirect to movies.
    if request.method == "POST":
        duplicated = False
        db = sqlite3.connect("movies.db")
        cursor = db.cursor()

        img = request.form.get("image")
        title = request.form.get("title")
        desc = request.form.get("overview")
        year = request.form.get("year")
        rating = request.form.get("rating")
        review = request.form.get("review")
        try:
            cursor.execute(
                f"INSERT INTO Movie VALUES(?,?,?,?,?,?)",
                (title, year, desc, rating, review, img),
            )
            db.commit()
            db.close()
        except sqlite3.IntegrityError:
            print(f"Movie Already Exists in Database")
            duplicated = True

        return redirect(url_for("movies", dup=duplicated))


# searching for movie
@app.route("/add", methods=["GET", "POST"])
# searchs for the movie input by the user in the MDB DB throught their API and displays
# the movie found, if the user wishes he can leave a comment about the movie and add it.
def add():
    title = ""
    overview = ""
    rating = ""
    year = ""
    img = ""
    ans = ""
    if request.method == "POST":
        # ... (variable initializations: title, overview, etc.)
        movie_searched = request.form.get("movie_searched")  # Use .get for safety

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
                "page": "1",
            }
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {BEARER_TOKEN_MOVIE}",
            }

            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)

                filme = response.json()
                if filme.get(
                        "results"
                ):  # Check if 'results' key exists and is not empty
                    first_result = filme["results"][0]
                    ans = "Is this the movie you were thinking about?"
                    title = first_result.get("original_title")
                    overview = first_result.get("overview")
                    rating = first_result.get("vote_average")
                    year = first_result.get("release_date")
                    img = first_result.get("poster_path")
                else:
                    ans = "No movies were found matching your search."
            except requests.exceptions.RequestException as e:
                ans = f"Unable to search due to an API error: {e}"
                print(f"API request failed: {e}")
            except ValueError:  # Catches JSON decoding errors
                ans = "Error processing API response."
                print("Failed to decode JSON from API response")

    return render_template(
        "add.html",
        ans=ans,
        title=title,
        overview=overview,
        rating=rating,
        year=year,
        img=img,
    )


@app.route("/watermark", methods=["GET", "POST"])
def watermark():
    if request.method == "POST":
        if "file" not in request.files:
            return render_template("watermark.html", error="No file part")
        file = request.files["file"]
        watermark_text_input = request.form.get(
            "watermark_text", ""
        ).strip()  # Get from form
        if not watermark_text_input:  # Use default if empty
            watermark_text = "@Boehme"
        else:
            watermark_text = watermark_text_input
        if file.filename == "":
            return render_template("watermark.html", error="No selected file")
        if file:
            # e.g., allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            # Sanitize filename to prevent directory traversal or other issues
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            if not filename:  # If secure_filename returns empty (e.g., just "..")
                return render_template("watermark.html", error="Invalid filename.")
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            print(f"Saved uploaded file to: {filepath}")
            # Generate a unique name for the output file to avoid overwrites if multiple users upload same filename
            base, ext = os.path.splitext(filename)
            output_filename = f"watermarked_{base}{ext}"
            output_path = os.path.join(app.config["UPLOAD_FOLDER"], output_filename)
            watermarked_file_path = add_watermark(filepath, watermark_text, output_path)
            if watermarked_file_path:
                try:
                    return send_file(
                        watermarked_file_path,
                        as_attachment=True,
                        download_name=output_filename,  # Use the generated output filename
                        mimetype="image/png",  # Or dynamically determine based on output_path extension
                    )
                except Exception as e:
                    print(f"Error sending file: {e}")
                    # Clean up the generated watermarked file if sending fails?
                    # if os.path.exists(watermarked_file_path):
                    #     os.remove(watermarked_file_path)
                    return render_template(
                        "watermark.html",
                        error=f"Error preparing file for download: {e}",
                    )
                # finally:
                # Clean up uploaded and watermarked files after sending or on error
                # This is important for server storage management.
                # Be careful with timing if send_file is asynchronous in some setups.
                # if os.path.exists(filepath):
                #     os.remove(filepath)
                # if os.path.exists(watermarked_file_path): # This might be premature if send_file is async
                #     os.remove(watermarked_file_path)
            else:
                # if os.path.exists(filepath): # Clean up original upload if watermarking failed
                #     os.remove(filepath)
                return render_template(
                    "watermark.html", error="Error applying watermark to the image."
                )

    return render_template("watermark.html")


@app.route("/textspeed", methods=["GET", "POST"])
def textspeed():
    return render_template("textspeed.html")


@app.route('/disney', methods=['GET', 'POST'])
def disney():
    return render_template("disney.html")


@app.route('/disney/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/disney/callback')
def callback():
    code = request.args.get('code')
    if code:
        token_info = sp_oauth.get_access_token(code)
        # You just need to return to the client with the access token
        return redirect(url_for('disney', access_token=token_info['access_token']))
    return "Error: No code received.", 400


@app.route('/disney/user_profile')
def user_profile():
    # Get Spotify object for the current user's session
    sp, access_token = get_spotify_for_user_()
    if not sp:
        return jsonify({"error": "Unauthorized"}), 401  # No token found for user session

    try:
        user = sp.current_user()
        return jsonify(user)  # Always jsonify dictionary responses
    except Exception as e:
        print(f"Error fetching user profile: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/disney/search_disney_music')
def search_disney_music():
    # Get Spotify object for the current user's session
    sp, access_token = get_spotify_for_user_()
    if not sp:
        return jsonify({"error": "Unauthorized"}), 401  # No token found for user session

    playlist_id = '4whT9DAdY6CeMcdvps3X8D'
    try:
        results = sp.playlist_tracks(playlist_id)
        tracks = [item['track'] for item in results['items']]
        return jsonify({"tracks": tracks})
    except Exception as e:
        print(f"Error searching Disney music: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/disney/play_track', methods=['POST'])
def play_track():
    # Get Spotify object for the current user's session
    sp, access_token = get_spotify_for_user_()
    if not sp:
        return jsonify({"error": "Unauthorized"}), 401  # No token found for user session

    data = request.get_json()

    device_id = data.get('device_id')
    uris = data.get('uris')
    offset = data.get('offset')
    position_ms = data.get('position_ms')

    # Use Spotipy's own player control methods instead of direct requests.put
    # This leverages Spotipy's error handling and token management
    try:
        sp.start_playback(
            device_id=device_id,
            uris=uris,
            offset=offset,
            position_ms=position_ms
        )
        return jsonify({"message": "Playback initiated"}), 200
    except Exception as e:
        print(f"Error starting playback via Spotipy: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/disney/transfer_playback', methods=['PUT'])
def transfer_playback():
    # Get Spotify object for the current user's session
    sp, access_token = get_spotify_for_user_()
    if not sp:
        return jsonify({"error": "Unauthorized"}), 401  # No token found for user session

    data = request.get_json()
    device_ids = data.get('device_ids')
    play_status = data.get('play', False)
    device_id = device_ids[0] if isinstance(device_ids, list) and device_ids else None

    if not all([access_token, device_id]):
        return jsonify({"error": "Missing required parameters"}), 400  # Return jsonify here too

    try:
        sp.transfer_playback(device_id=device_id, force_play=play_status)
        return jsonify({"status": "success"}), 200  # Always jsonify dictionary responses
    except Exception as e:
        print(f"Error transferring playback: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/inflation', methods=['GET', 'POST'])
def inflation():
    return render_template("inflation.html")


if __name__ == "__main__":
    if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI]):
        print(
            "ERROR: Please set SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI environment variables or in a .env file."
        )
        exit(1)
    app.run(debug=True)
