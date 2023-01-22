from flask import Flask, request, redirect, abort, render_template, make_response
from csrf import csrf
from util import random_128_bit_string
from hashlib import sha256
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from config import DATABASE, OPENAI_API_KEY
from db import Question, Referrer, User, LoginCode
from threading import Thread
from mistune import create_markdown
from time import time, sleep
from mail import send_email
import re
import openai

app = Flask(__name__)
engine = create_engine(DATABASE)
openai.api_key = OPENAI_API_KEY
markdown = create_markdown()
get, post = csrf(app, engine)

slug_special_chars = '?.,/&!?\'"<>'

def is_valid_slug(slug):
  return len(slug) >= 1 and len(slug) <= 300 and not re.search(f'[{slug_special_chars}]', slug)

def make_slug(question):
  return re.sub('\s+', '-', re.sub(f'[{slug_special_chars}]', '', question)).lower()

def hash(salt, s):
  return sha256((salt + s).encode('utf-8')).hexdigest()

@get('/')
def new_question(render_template, user, tr):
  log_referrer()
  return render_template('new_question.html')

@get('/about')
def about(render_template, user, tr):
  log_referrer()
  return render_template('about.html')

@get('/sitemap.xml')
def sitemap(render_template, user, tr):
  with Session(engine) as session:
    response = render_template('sitemap.xml', articles=session.query(Question).all())
    response.headers['Content-Type'] = 'text/xml'
    return response

@get('/referrers')
def referrers(render_template, user, tr):
  if not user or not user.admin: return redirect('/')
  with Session(engine) as session:
    return render_template('referrers.html', referrers=session.query(Referrer).order_by(Referrer.count.desc()).all())

@get('/register')
def register(render_template, user, tr):
  if user: return redirect('/')
  return render_template('login.html', register=True)

@post('/register')
def register(redirect, user, tr):
  if user: return redirect('/')
  with Session(engine) as session:
    try:
      [user] = session.query(User).where(User.email == request.form['email'])
      if user.email_verified:
        return redirect('/register', tr['account_already_exists'])
    except:
      user = User(email=request.form['email'], api_key=random_128_bit_string())
      session.add(user)
      session.commit()
    login_code = LoginCode(user_id=user.id, code=random_128_bit_string(), expiry=int(time()+60*60*2))
    session.add(login_code)
    session.commit()
    send_email(request.form['email'], tr['verification_email_subject'], render_template('emails/verification.html', tr=tr, code=login_code.code))
    return redirect('/register', tr['verify_your_email'] % request.form['email'])

@get('/login/<code>')
def login(render_template, user, tr, code):
  with Session(engine) as session:
    try:
      [login_code] = session.query(LoginCode).where(LoginCode.code == code)
    except:
      abort(404)
    if login_code.expiry < time():
      return render_template('login.html', message=tr['login_code_expired'])
    [user] = session.query(User).where(User.id == login_code.user_id)
    user.email_verified = True
    session.delete(login_code)
    session.commit()
    response = make_response(redirect(f'/{tr["language"]}/'))
    response.set_cookie('api_key', user.api_key)
    return response

@get('/login')
def login(render_template, user, tr):
  if user: return redirect('/')
  return render_template('login.html')

@post('/login')
def login(redirect, user, tr):
  if user: return redirect('/')
  with Session(engine) as session:
    try:
      [user] = session.query(User).where(User.email == request.form['email'])
    except:
      return redirect('/login', tr['email_not_found'])
    login_code = LoginCode(user_id=user.id, code=random_128_bit_string(), expiry=int(time()+60*60*2))
    session.add(login_code)
    session.commit()
    if user.email_verified:
      send_email(request.form['email'], tr['login_email_subject'], render_template('emails/login.html', tr=tr, code=login_code.code))
      return redirect('/login', tr['login_email_sent'])
    else:
      send_email(request.form['email'], tr['verification_email_subject'], render_template('emails/verification.html', tr=tr, code=login_code.code))
      return redirect('/register', tr['verify_your_email'] % request.form['email'])

@post('/logout')
def logout(redirect, user, tr):
  if not user: return redirect('/')
  response = redirect('/')
  response.set_cookie('api_key', '', expires=0)
  return response

@post('/')
def new_question(redirect, user, tr):
  q = request.form['question'].strip()
  slug = make_slug(q)
  if not is_valid_slug(slug):
    return redirect('/', tr['invalid_question'])
  if len(q) > 300:
    return redirect('/', tr['question_too_long'])
  with Session(engine) as session:
    try:
      [question] = session.query(Question).where(Question.slug == slug)
      return redirect(f'/question/{slug}', tr['question_exists'])
    except:
      pass
    question = Question(user_id=None if not user else user.id, question=q, slug=slug, answer=None)
    session.add(question)
    session.commit()
  def target():
    with Session(engine) as session:
      try:
        [question] = session.query(Question).where(Question.slug == slug)
      except:
        return
      for i in range(5):
        try:
          question.answer = openai.Completion.create(model="text-davinci-003", prompt='Write a blog post answering the following question: ' + q, max_tokens=1024, temperature=0)["choices"][0]["text"]
          break
        except:
          sleep(5)
      if not question.answer:
        question.answer = tr['error_generating_answer']
      session.commit()
  Thread(target=target).start()
  return redirect(f"/question/{slug}")

@get('/browse')
def browse(render_template, user, tr):
  with Session(engine) as session:
    return render_template('browse.html', questions=session.query(Question).order_by(Question.id.desc()).all())

@get('/mine')
def mine(render_template, user, tr):
  if not user: return redirect('/')
  with Session(engine) as session:
    return render_template('browse.html', questions=session.query(Question).where(Question.user_id == user.id).order_by(Question.id.desc()).all())

@get('/article/<slug>')
def question(render_template, user, tr, slug):
  log_referrer()
  if not is_valid_slug(slug): abort(404)
  return redirect(f'/question/{slug}')

@get('/question/<slug>')
def question(render_template, user, tr, slug):
  log_referrer()
  if not is_valid_slug(slug): abort(404)
  with Session(engine) as session:
    try:
      [question] = session.query(Question).where(Question.slug == slug)
    except:
      abort(404)
    question.views += 1
    session.commit()
    html = markdown(question.answer)
    return render_template('question.html', question=question, html=html)

@get('/question/<slug>/ready')
def question_ready(render_template, user, tr, slug):
  if not is_valid_slug(slug): abort(404)
  with Session(engine) as session:
    try:
      [question] = session.query(Question).where(Question.slug == slug)
    except:
      abort(404)
    return {'ready': question.answer is not None}

@post('/question/<slug>')
def question(redirect, user, tr, slug):
  if not user or not user.admin: return redirect('/')
  if not is_valid_slug(slug): abort(404)
  with Session(engine) as session:
    try:
      [question] = session.query(Question).where(Question.slug == slug)
    except:
      abort(404)
    try:
      [new_question] = session.query(Question).where(Question.slug == request.form['slug'])
      if new_question.id != question.id:
        return redirect(f'/question/{slug}', tr['another_question_slug_exists'])
    except:
      pass
    if not is_valid_slug(request.form['slug']):
      return redirect(f'/question/{slug}', tr['invalid_slug'])
    question.question = request.form['question']
    question.slug = request.form['slug']
    question.answer = request.form['answer']
    session.commit()
    return redirect(f"/question/{request.form['slug']}", tr['edits_were_saved'])

@post('/question/<slug>/delete')
def question_delete(redirect, user, tr, slug):
  if not user or not user.admin: return redirect('/')
  if not is_valid_slug(slug): abort(404)
  with Session(engine) as session:
    try:
      [question] = session.query(Question).where(Question.slug == slug)
    except:
      abort(404)
    session.delete(question)
    session.commit()
    return redirect('/', tr['question_deleted'])

def log_referrer():
  try:
    referrer_hostname = re.match('https?://([^/]*)', request.referrer).group(1)
  except:
    referrer_hostname = 'unknown'
  with Session(engine) as session:
    try:
      [ref] = session.query(Referrer).where(Referrer.hostname == referrer_hostname)
      ref.count += 1
      session.commit()
    except:
      session.add(Referrer(hostname=referrer_hostname, count=1))
      session.commit()
