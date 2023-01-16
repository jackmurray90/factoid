from flask import request, abort, make_response, render_template, redirect
from util import random_128_bit_string
from config import API_KEY

def csrf(app):
  def get(path):
    def decorator(f):
      @app.route(path, endpoint=random_128_bit_string())
      def wrapper(*args, **kwargs):
        logged_in = request.cookies.get('api_key') == API_KEY
        api_key = API_KEY if logged_in else ''
        csrf = f'<input type="hidden" name="csrf" value="{api_key}"/>'
        def rt(path, **kwargs):
          if 'message' not in kwargs:
            kwargs['message'] = request.cookies.get('message')
          response = make_response(render_template(path, csrf=csrf, logged_in=logged_in, **kwargs))
          response.set_cookie('message', '', expires=0)
          return response
        return f(rt, logged_in, *args, **kwargs)
      return wrapper
    return decorator

  def post(path):
    def decorator(f):
      @app.post(path, endpoint=random_128_bit_string())
      def wrapper(*args, **kwargs):
        logged_in = request.cookies.get('api_key') == API_KEY
        if logged_in and request.form['csrf'] != API_KEY:
          abort(403)
        def r(path, message=''):
          response = make_response(redirect(path))
          response.set_cookie('message', message)
          return response
        return f(r, logged_in, *args, **kwargs)
      return wrapper
    return decorator

  return get, post
