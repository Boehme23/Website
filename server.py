from flask import Flask, render_template, request, redirect, url_for, send_file
from morse_code_converter import converter
import sqlite3
from flask_bootstrap5 import Bootstrap
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import os

dotenv_path = os.path.join(os.path.dirname(__file__), '.env') # Assumes keys.env is in the same directory as server.py
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"Warning: Environment file not found at {dotenv_path}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_sensible_default_secret_key_for_development')
app.config['BEARER_TOKEN_MOVIE'] = os.environ.get('TMDB_BEARER_TOKEN')
app.config['UPLOAD_FOLDER'] = 'uploads'  # Define the upload folder
# Create the upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
BEARER_TOKEN_MOVIE = app.config.get('BEARER_TOKEN_MOVIE')

Bootstrap(app)




def add_watermark(image_path, watermark_text, output_path):
    """
    Opens an image, adds a text watermark, and saves it to the output_path.
    Returns the output_path if successful, None otherwise.
    """
    try:
        img = Image.open(image_path).convert("RGBA")  # Open and ensure RGBA for transparency
        width, height = img.size

        # Make a new image for the watermark text that's the same size as the original
        txt_img = Image.new('RGBA', (width, height), (255, 255, 255, 0))  # Transparent layer
        draw = ImageDraw.Draw(txt_img)  # Draw on the transparent layer

        # Font
        try:
            font_path = "arial.ttf"
            font_size = int(height / 5)
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"Warning: Font '{font_path}' not found. Using default PIL font.")
            font_size = 70
            font = ImageFont.load_default()

        # Calculate text size and position
        try:

            bbox = font.getbbox(watermark_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            text_width, text_height = draw.textsize(watermark_text, font=font)

        padding = 10
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        # Add text watermark
        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 128))

        # Composite the text layer onto the original image
        img_with_watermark = Image.alpha_composite(img, txt_img)

        # If the output is JPEG, convert the RGBA image to RGB as JPEG doesn't support alpha
        if output_path.lower().endswith(('.jpg', '.jpeg')):
            img_with_watermark = img_with_watermark.convert('RGB')

        img_with_watermark.save(output_path)
        return output_path

    except FileNotFoundError:
        print(f"Error: Input image file not found at {image_path}")
        return None
    except Exception as e:
        print(f"Error adding watermark: {e}") # This will now correctly show other errors if they occur
        return None

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
        duplicated=False
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


@app.route('/watermark', methods=['GET', 'POST'])  # Corrected: Added POST method
def watermark():

    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('watermark.html', error="No file part")

        file = request.files['file']
        watermark_text_input = request.form.get('watermark_text', '').strip()  # Get from form

        if not watermark_text_input:  # Use default if empty
            watermark_text = '@Boehme'
        else:
            watermark_text = watermark_text_input

        if file.filename == '':
            return render_template('watermark.html', error="No selected file")

        if file:  # and file.filename: # Redundant check, already handled by above
            # Consider adding file type/extension validation here
            # e.g., allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}

            # Sanitize filename to prevent directory traversal or other issues
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            if not filename:  # If secure_filename returns empty (e.g., just "..")
                return render_template('watermark.html', error="Invalid filename.")

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            print(f"Saved uploaded file to: {filepath}")

            # Generate a unique name for the output file to avoid overwrites if multiple users upload same filename
            base, ext = os.path.splitext(filename)
            # Could add a timestamp or UUID for more uniqueness
            output_filename = f"watermarked_{base}{ext}"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

            watermarked_file_path = add_watermark(filepath, watermark_text, output_path)

            if watermarked_file_path:
                try:
                    return send_file(
                        watermarked_file_path,
                        as_attachment=True,
                        download_name=output_filename,  # Use the generated output filename
                        mimetype='image/png'  # Or dynamically determine based on output_path extension
                    )
                except Exception as e:
                    print(f"Error sending file: {e}")
                    # Clean up the generated watermarked file if sending fails?
                    # if os.path.exists(watermarked_file_path):
                    #     os.remove(watermarked_file_path)
                    return render_template('watermark.html', error=f"Error preparing file for download: {e}")
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
                return render_template('watermark.html', error="Error applying watermark to the image.")

    return render_template('watermark.html')


if __name__ == '__main__':
    app.run(debug=True)

    ##venv\Scripts\activate
