import json
import requests

BASE_URL = 'https://api.themoviedb.org/3'
API_KEY = '06b0ce27243d1f04de9675dc822f928a'

data_lsit = []
GENRE_URL = f'{BASE_URL}/genre/movie/list?api_key={API_KEY}&language=ko-KR'
genre_data = requests.get(GENRE_URL).json()
genres = genre_data.get('genres')
for genre in genres:
    genre_dict = {
        "model" : "movies.Genre",
        "pk" : genre.get("id"),
        "fields" : {
            "name" : genre.get("name"),
        }
    }
    data_lsit.append(genre_dict)

for page in range(1, 501):
    MOIVE_URL = f'{BASE_URL}/movie/popular?api_key={API_KEY}&language=ko-KR&page={page}'
    movie_data = requests.get(MOIVE_URL).json()
    movies = movie_data.get('results')
    for movie in movies:
        if not movie.get("release_date") or not movie.get("poster_path"):
            continue
        movie_dict = {
            "model" : "movies.Movie",
            "pk" : movie.get("id"),
            "fields" : {
                "title" : movie.get("title"),
                "release_date" : movie.get("release_date"),
                "popularity" : movie.get("popularity"),
                "vote_count" : movie.get("vote_count"),
                "vote_average" : movie.get("vote_average"),
                "overview" : movie.get("overview"),
                "poster_path" : movie.get("poster_path"),
                "genres" : movie.get("genre_ids"),
            }
        }
        data_lsit.append(movie_dict)

with open('movies/fixtures/movies.json', 'w', encoding='UTF-8') as file:
    file.write(json.dumps(data_lsit, ensure_ascii=False))