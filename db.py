from sqlalchemy import Integer, Column, String, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Article(Base):
  __tablename__ = 'articles'

  id = Column(Integer, primary_key=True)
  slug = Column(String)
  title = Column(String)
  markdown = Column(Text)
  published = Column(Boolean)
  views = Column(Integer, default=0)

class Referrer(Base):
  __tablename__ = 'referrers'

  hostname = Column(String, primary_key=True)
  count = Column(Integer)
