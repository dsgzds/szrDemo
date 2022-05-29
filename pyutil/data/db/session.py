# encoding: utf8

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import config


def _create_mysql_engine():
    engine = create_engine(
            'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4'.format(
                 config.db.username,
                 config.db.password,
                 config.db.host,
                 config.db.port,
                 config.db.db_name, 
                 ),
            pool_recycle = 3600,
            pool_pre_ping = True
        )

    return engine


engine = _create_mysql_engine()

SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)


@contextmanager
def open_session(session_cls=Session, commit=False):

    session = session_cls()

    try:
        yield session

        if commit:
            session.commit()

    except:

        session.rollback()
        raise

    finally:

        session.close()



