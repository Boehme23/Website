from ensurepip import bootstrap
from xml.dom.expatbuilder import TEXT_NODE
from flask import Flask, render_template, request, redirect, url_for
from morse_code_converter import converter
import sqlite3
from flask_bootstrap import Bootstrap5
import requests
app = Flask(__name__)
Bootstrap5(app)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
api_key_movie='4673175d64a444553e6749d1d2f920ad'
bearer_token_movie='eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI0NjczMTc1ZDY0YTQ0NDU1M2U2NzQ5ZDFkMmY5MjBhZCIsIm5iZiI6MTc0NzA3MTE5NS4wMzUsInN1YiI6IjY4MjIzMGRiN2Q1YTZiZjY3ZDdlN2RiYyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.c1hk6YRfrd8yRtBW6lwY-udm-cc5QOx642CE3TGhnhI'

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
@app.route("/movies",methods=['GET', 'POST'])
def movies():
    #Connect to DB, Reads and save to a list 'movies'
    db = sqlite3.connect('movies.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM movie")
    result = cursor.fetchall()
    movies = []
    for rows in range(0, len(result)):
        new_column = [
            result[rows][0],
            result[rows][1],
            result[rows][2],
            result[rows][3],
            result[rows][4],
            result[rows][5]
        ]
        movies.append(new_column)

#gets querry string, if error is true then it will diplay a pop-up saying the movie is already on the list
    dup=''
    if request.args.get('error')=='True':
        dup='x'
    return render_template("movies.html", movie=movies, error=dup)

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
        print(request.form)
        movie_searched =request.form['movie_searched']
        url = "https://api.themoviedb.org/3/search/movie?query="+movie_searched+"&include_adult=false&language=en-US&page=1"

        headers = {
            "accept": "application/json",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI0NjczMTc1ZDY0YTQ0NDU1M2U2NzQ5ZDFkMmY5MjBhZCIsIm5iZiI6MTc0NzA3MTE5NS4wMzUsInN1YiI6IjY4MjIzMGRiN2Q1YTZiZjY3ZDdlN2RiYyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.c1hk6YRfrd8yRtBW6lwY-udm-cc5QOx642CE3TGhnhI"
        }

        response = requests.get(url, headers=headers)
        filme=response.json()
        if response.status_code == 200:
             if len(filme['results'])>0:
                print(filme['results'])
                ans='Is this the movie you were thinking about?'
                title=filme['results'][0]['original_title']
                overview=filme['results'][0]['overview']
                rating=filme['results'][0]['vote_average']
                year=filme['results'][0]['release_date']
                img=filme['results'][0]['poster_path']
             else:
                 ans='No movies were found'
        else:
            ans='Unable to search'
    return render_template("add.html",ans=ans, title= title,overview=overview,rating=rating,year=year,img=img)


if __name__ == '__main__':
    app.run(debug=True)
