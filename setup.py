from sqlalchemy import create_engine
from db import Base
from config import DATABASE

if __name__ == '__main__':
  engine = create_engine(DATABASE)
  Base.metadata.create_all(engine)
