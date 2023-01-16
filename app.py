from flask import Flask, request, redirect, abort
from csrf import csrf
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from config import DATABASE, API_KEY, OPENAI_API_KEY
from db import Article
from threading import Thread
import mistune
import openai

app = Flask(__name__)
engine = create_engine(DATABASE)
openai.api_key = OPENAI_API_KEY
get, post = csrf(app)

@get('/')
def index(render_template, logged_in):
  with Session(engine) as session:
    return render_template('index.html', articles=session.query(Article).all())

@get('/sitemap.xml')
def sitemap(render_template, logged_in):
  with Session(engine) as session:
    response = render_template('sitemap.xml', articles=session.query(Article).where(Article.published == True))
    response.headers['Content-Type'] = 'text/xml'
    return response

@get('/login')
def login(render_template, logged_in):
  return render_template('login.html')

@post('/login')
def login(redirect, logged_in):
  if request.form['api_key'] == API_KEY:
    response = redirect('/')
    response.set_cookie('api_key', API_KEY)
    return response
  return redirect('/login', 'Incorrect API Key.')

@get('/new_article')
def new_article(render_template, logged_in):
  if not logged_in: return redirect('/')
  return render_template('new_article.html')

@post('/new_article')
def new_article(redirect, logged_in):
  if not logged_in: return redirect('/')
  with Session(engine) as session:
    try:
      [article] = session.query(Article).where(Article.slug == request.form['slug'])
      return redirect('/new_article', 'An article with that slug already exists.')
    except:
      pass
    article = Article(title=request.form['title'], slug=request.form['slug'], markdown=None, published=False)
    session.add(article)
    session.commit()
  def target(title, slug):
    with Session(engine) as session:
      try:
        [article] = session.query(Article).where(Article.slug == slug)
      except:
        return
      article.markdown = openai.Completion.create(model="text-davinci-003", prompt='Write a blog post answering the following question: ' + title, max_tokens=1024, temperature=0)["choices"][0]["text"]
      session.commit()
  Thread(target=target, args=(request.form['title'], request.form['slug'])).start()
  return redirect(f"/article/{request.form['slug']}")

@get('/article/<slug>')
def article(render_template, logged_in, slug):
  with Session(engine) as session:
    try:
      [article] = session.query(Article).where(Article.slug == slug)
    except:
      abort(404)
    if not logged_in and not article.published:
      abort(404)
    html = mistune.html(article.markdown)
    return render_template('article.html', article=article, html=html)

@get('/article/<slug>/ready')
def article_ready(render_template, logged_in, slug):
  with Session(engine) as session:
    try:
      [article] = session.query(Article).where(Article.slug == slug)
    except:
      abort(404)
    if not logged_in and not article.published:
      abort(404)
    return {'ready': article.markdown is not None}

@post('/article/<slug>')
def article(redirect, logged_in, slug):
  if not logged_in: return redirect('/')
  with Session(engine) as session:
    try:
      [article] = session.query(Article).where(Article.slug == slug)
    except:
      abort(404)
    try:
      [new_article] = session.query(Article).where(Article.slug == request.form['slug'])
      if new_article.id != article.id:
        return redirect(f'/article/{slug}', "Another article with that slug already exists.")
    except:
      pass
    article.title = request.form['title']
    article.slug = request.form['slug']
    article.markdown = request.form['markdown']
    article.published = bool(request.form.get('published'))
    session.commit()
    return redirect(f"/article/{request.form['slug']}", "Your edits were saved.")

@post('/article/<slug>/delete')
def article_delete(redirect, logged_in, slug):
  if not logged_in: return redirect('/')
  with Session(engine) as session:
    try:
      [article] = session.query(Article).where(Article.slug == slug)
    except:
      abort(404)
    session.delete(article)
    session.commit()
    return redirect('/', 'The article was deleted.')
