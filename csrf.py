from flask import request, abort, make_response, render_template, redirect
from util import random_128_bit_string
from sqlalchemy.orm import Session
from db import User
from translations import tr, accepted_languages, default_language

def csrf(app, engine):
  def get(path):
    def decorator(f):
      @app.get(path, endpoint=random_128_bit_string())
      def get(*args, **kwargs):
        try:
          with Session(engine) as session:
            [user] = session.query(User).where(User.api_key == request.cookies.get('api_key'))
            api_key = user.api_key
        except:
          api_key = ''
          user = None
        csrf = f'<input type="hidden" name="csrf" value="{api_key}"/>'
        language = request.cookies.get('language')
        if language not in accepted_languages:
          language = request.accept_languages.best_match(accepted_languages) or default_language
        def rt(p, **kwargs):
          if 'message' not in kwargs:
            kwargs['message'] = request.cookies.get('message')
          response = make_response(render_template(p, tr=tr[language], csrf=csrf, user=user, **kwargs))
          response.set_cookie('message', '', expires=0)
          return response
        return f(rt, user, tr[language], *args, **kwargs)
    return decorator

  def post(path):
    def decorator(f):
      @app.post(path, endpoint=random_128_bit_string())
      def post(*args, **kwargs):
        try:
          with Session(engine) as session:
            [user] = session.query(User).where(User.api_key == request.cookies.get('api_key'))
            api_key = user.api_key
        except:
          api_key = ''
          user = None
        language = request.cookies.get('language')
        if language not in accepted_languages:
          language = request.accept_languages.best_match(accepted_languages) or default_language
        if user and request.form['csrf'] != api_key:
          abort(403)
        def r(p, message=''):
          response = make_response(redirect(p))
          response.set_cookie('message', message)
          return response
        return f(r, user, tr[language], *args, **kwargs)
    return decorator

  return get, post
