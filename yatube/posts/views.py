from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from yatube.settings import PAGE_COEF

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


# Вынес paginator  в отдельную функцию
def pagination(request, object, coef):
    paginator = Paginator(object, coef)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


# Главная страница

def index(request):
    template = 'posts/index.html'
    post_list = Post.objects.all()
    page_obj = pagination(request, post_list, PAGE_COEF)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


# Посты по группам

def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = pagination(request, posts, PAGE_COEF)
    context = {
        'page_obj': page_obj,
        'group': group
    }
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    post_count = post_list.count()
    user = request.user
    page_obj = pagination(request, post_list, PAGE_COEF)
    if user.is_authenticated:
        follows_list = user.follower.all().values_list('author', flat=True)
        if author.id in follows_list:
            following = True
        else:
            following = False
    else:
        following = None
    followers_count = author.following.count()
    context = {
        'post_count': post_count,
        'author': author,
        'page_obj': page_obj,
        'following': following,
        'followers_count': followers_count

    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    author = post.author
    post_list = author.posts
    post_count = post_list.count()
    self_comments = post.comments.all()
    comment_form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'post_count': post_count,
        'post_list': post_list,
        'author': author,
        'form': comment_form,
        'comments': self_comments

    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        request.FILES or None
    )
    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect('posts:profile', request.user.username)

    context = {
        'form': form
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    edit_post = get_object_or_404(Post, id=post_id)
    if request.user != edit_post.author:
        return redirect('posts:post_detail', post_id=edit_post.id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=edit_post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', edit_post.id)
    context = {
        'form': form,
        'is_edit': True
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    authors = request.user.follower.all().values('author')
    following_posts = Post.objects.all().filter(author__in=authors)
    template = 'posts/follow.html'
    page_obj = pagination(request, following_posts, PAGE_COEF)
    context = {
        'page_obj': page_obj
    }

    return render(request, template, context)


@login_required
def profile_follow(request, username):
    # Подписаться на автора
    template = reverse('posts:profile', args=((username,)))
    user = request.user
    author = get_object_or_404(User, username=username)
    follows_list = user.follower.all().values_list('author', flat=True)
    if user != author and author.id not in follows_list:
        Follow.objects.create(user=user, author=author)
    return redirect(template)


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    template = reverse('posts:profile', args=((username,)))
    user = request.user
    author = get_object_or_404(User, username=username)
    follow_obj = Follow.objects.filter(user=user, author=author)
    follow_obj.delete()
    return redirect(template)
