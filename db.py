from sqlalchemy import Integer, Column, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Question(Base):
  __tablename__ = 'questions'
  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('users.id'))
  slug = Column(String)
  question = Column(String)
  answer = Column(Text)
  views = Column(Integer, default=0)
  user = relationship('User')

class User(Base):
  __tablename__ = 'users'
  id = Column(Integer, primary_key=True)
  api_key = Column(String)
  email = Column(String)
  email_verified = Column(Boolean, default=False)
  payout_address = Column(String)
  admin = Column(Boolean, default=False)
  questions = relationship('Question', back_populates='user')

class LoginCode(Base):
  __tablename__ = 'login_codes'
  code = Column(String, primary_key=True)
  user_id = Column(Integer, ForeignKey('users.id'))
  expiry = Column(Integer)
  user = relationship('User')

class Referrer(Base):
  __tablename__ = 'referrers'
  hostname = Column(String, primary_key=True)
  count = Column(Integer)
