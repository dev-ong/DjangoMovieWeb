from django.db.models import Q, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_safe
from django.contrib.auth.decorators import login_required
from .models import Movie, Rank, Movie
from .forms import RankForm
from datetime import datetime

import requests
import pandas
import numpy
from django.db.models import Q

# 유저간 유사도 구하기 : 피어슨 상관계수
def pearson(s1, s2):
    s1_c = s1 - s1.mean()
    s2_c = s2 - s2.mean()
    return numpy.sum(s1_c * s2_c) / (numpy.sqrt(numpy.sum(s1_c ** 2) * numpy.sum(s2_c ** 2)))

def recommended(request):

    # 유저가 등록한 평점과 다른 유저가 등록한 평점이 존재한다면
    if Rank.objects.filter(user_id=request.user) and Rank.objects.filter(~Q(user_id=request.user)):

        # 유저의 평점 데이터 불러오기
        ranks = pandas.DataFrame(data=Rank.objects.all().values('user', 'movie', 'rank'))
        ranks = ranks.rename(columns={'user':"userId", 'movie':"movieId"})

        # 영화 데이터에서 id값 가져오기
        movie = pandas.DataFrame(data=Movie.objects.all().values('id'))
        movie = movie.rename(columns={'id':'movieId'})

        # 평가하지 않은 데이터는 NaN값으로
        movie.movieId = pandas.to_numeric(movie.movieId, errors='coerce')
        ranks.movieId = pandas.to_numeric(ranks.movieId, errors='coerce')

        # 데이터 통합 후 피벗 테이블 생성
        data = pandas.merge(ranks, movie, on='movieId', how='inner')
        matrix = data.pivot_table(index='movieId', columns='userId', values='rank')
        result = []

        # 다른 유저들과 유사도 검사
        for side_id in matrix.columns:
            
            if side_id == request.user.id:
                continue
            
            # 유저간 유사도 검사
            cor = pearson(matrix[request.user.id], matrix[side_id])

            # 평점이 NaN 값이면 0으로 입력
            if numpy.isnan(cor):
                result.append((side_id, 0))
            else:
                result.append((side_id, cor))

        # 가장 유사한 유저 값 생성
        result = max(result, key=lambda r: r[1])[0]

        # 자신이 평가한 영화 id값
        movies = Rank.objects.filter(user_id=request.user.id).values('movie_id')
        movies = [value['movie_id'] for value in movies]

        # 유사 유저가 평가한 영화 id값
        sim_movie = Rank.objects.filter(user_id=result).values('movie_id')
        
        # 내가 보지 않은 영화 id 후보 결정
        id_list = [value['movie_id'] for value in sim_movie if value['movie_id'] not in movies]
        recommends = Movie.objects.filter(id__in=id_list).order_by('-popularity')
        recommends_count = recommends.count()

        # 추천 영화가 충분하지 않으면
        if recommends_count < 4:
            return None

        return recommends[:4]

    return None

@require_safe
def index(request):
    movies_popular = Movie.objects.order_by('-popularity')[:12]
    movies_release = Movie.objects.filter(release_date__lte=datetime.now()).order_by('-release_date')[:8]
    movies_comeout = Movie.objects.filter(release_date__gt=datetime.now()).order_by('release_date')[:4]
    movies_recommend = None
    if request.user.is_authenticated:
        movies_recommend = recommended(request)
    movies_random = Movie.objects.order_by('?')[:4]

    context = {
        'movies_popular': movies_popular,
        'movies_release': movies_release,
        'movies_comeout': movies_comeout,
        'movies_recommend': movies_recommend,
        'movies_random': movies_random,

    }
    return render(request, 'movies/index.html', context)


@login_required
@require_safe
def detail(request, movie_pk):
    movie = get_object_or_404(Movie, pk=movie_pk)
    ranks = movie.rank_set.all()
    averatge_ranks = ranks.aggregate(Avg('rank'))['rank__avg']
    user_rank = ranks.filter(user_id=request.user, movie_id=movie_pk)
    rank_form = RankForm()

    BASE_URL = 'https://api.themoviedb.org/3'
    API_KEY = '06b0ce27243d1f04de9675dc822f928a'
    VIDEOS_URL = f'{BASE_URL}/movie/{movie_pk}/videos?api_key={API_KEY}&language=ko-KR'
    videos_data = requests.get(VIDEOS_URL).json()
    video_path = None
    videos = videos_data.get('results')
    if videos:
        video = videos[0]
        video_path = video['key']
    context = {
        'movie': movie,
        'ranks': ranks,
        'rank_form': rank_form,
        'user_rank': user_rank,
        'averatge_ranks': averatge_ranks,
        'video_path': video_path,
    }
    return render(request, 'movies/detail.html', context)

@login_required
@require_POST
def create_rank(request, movie_pk):
    movie = get_object_or_404(Movie, pk=movie_pk)
    rank_form = RankForm(request.POST)
    if rank_form.is_valid():
        rank = rank_form.save(commit=False)
        rank.movie = movie
        rank.user = request.user
        rank.save()
        return redirect('movies:detail', movie.pk)
    context = {
        'rank_form': rank_form,
        'movie': movie,
        'ranks': movie.rank_set.all(),
    }
    return render(request, 'movies/detail.html', context)


@require_POST
def delete_rank(request, movie_pk, rank_pk):
    if request.user.is_authenticated:
        rank = get_object_or_404(Rank, pk=rank_pk)
        if request.user == rank.user:
            rank.delete()
    return redirect('movies:detail', movie_pk)



# 검색 기능
def search(request):
    q = request.POST.get('q', "") 

    if q:
        movies = Movie.objects.all().filter(title__icontains=q).order_by('release_date')

        context = {
            'movies' : movies,
            'q' : q,
        }
        return render(request, 'movies/search.html', context)
    
    return render(request, 'movies/search.html')
