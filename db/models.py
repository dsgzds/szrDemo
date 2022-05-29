from email.policy import default
from sqlalchemy import Boolean, Column, ForeignKey, Integer, BigInteger, Text, Date, DateTime, SmallInteger, String, \
    Numeric
from sqlalchemy.orm import relationship
import datetime

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(String(30))
    name = Column(String(20))
    hashed_password = Column(String)
    bio = Column(String(256))
    interest = Column(BigInteger)
    birthday = Column(DateTime)
    avatar = Column(String(256))
    gender = Column(String(10))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.datetime.now())
    update_time = Column(DateTime, default=datetime.datetime.now())
    default_botid = Column(Integer)
    reg_device_id = Column(String)

    oauth_items = relationship("OAuthItem", back_populates="owner")
    bots = relationship("Bot", back_populates="owner")


class UserDemo(Base):
    __tablename__ = 'users_demo1'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20))


class PersonaSettings(Base):
    __tablename__ = 'persona_sets'
    id = Column(Integer, primary_key=True, index=True)
    persona = Column(String)
    born_msg = Column(String)
    create_time = Column(DateTime, default=datetime.datetime.now())


class Bot(Base):
    __tablename__ = 'bots'
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String)
    avatar = Column(String)
    is_active = Column(Boolean, default=True)
    ownerid = Column(Integer, ForeignKey('users.id'))
    persona = Column(String, default=None)

    owner = relationship("User", back_populates="bots")
    create_time = Column(DateTime, default=datetime.datetime.now())
    update_time = Column(DateTime, default=datetime.datetime.now())


class OAuthItem(Base):
    # for firebase login
    __tablename__ = "oauth_items"

    id = Column(Integer, primary_key=True, index=True)
    login_type = Column(String)
    login_id = Column(String)

    ownerid = Column(BigInteger, ForeignKey("users.id"), index=True)

    owner = relationship("User", back_populates="oauth_items")
    create_time = Column(DateTime, default=datetime.datetime.now())


class Topic(Base):
    __tablename__ = 'topics'
    id = Column(BigInteger, primary_key=True, index=True)  # for bot topic current equal to ownerid
    ownerid = Column(BigInteger, index=True)  # for botid
    name = Column(String, index=True)
    create_time = Column(DateTime, default=datetime.datetime.now())


class LoginLog(Base):
    __tablename__ = 'loginlogs'
    id = Column(Integer, primary_key=True, index=True)
    userid = Column(Integer, index=True)
    access_token = Column(String)
    refresh_token = Column(String)
    device_id = Column(String)
    data = Column(String)
    is_logout = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.datetime.now(), index=True)


class Message(Base):
    __tablename__ = 'history_msgs'
    id = Column(String, primary_key=True, index=True)
    content = Column(String)
    fromUserId = Column(BigInteger)
    toUserId = Column(BigInteger)
    create_time = Column(DateTime, default=datetime.datetime.now(), index=True)
    visiable = Column(Boolean, default=True)
    selfuser = Column(Boolean)
    evaluation = Column(Integer, default=0)
    class Config: 
        orm_mode = True
    def to_json(self):
        return self.__dict__


class MessageEvaluation(Base):
    __tablename__ = 'evaluation'
    userid = Column(Integer)
    msgid = Column(Integer, primary_key=True, index=True)
    msg = Column(String)
    msg_time = Column(DateTime, default=datetime.datetime.now())
    evaluation = Column(Integer)

class Robot(Base):
    __tablename__ = 'robot_infos'
    robot_id = Column(Integer, primary_key=True, index=True)
    intruction = Column(String)
    sample = Column(String)

class Message1(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, index=True)
    topicid = Column(BigInteger, index=True)
    msg = Column(String)
    srcid = Column(BigInteger)
    create_time = Column(DateTime, default=datetime.datetime.now(), index=True)
    visiable = Column(Boolean, default=True)
    class Config: 
        orm_mode: True
    def to_json(self):
        return {
            'id': self.id,
            'content': self.content,
            'fromUserId': self.fromUserId,
            'toUserId': self.toUserId,
            'create_time': self.create_time,
            'visiable' : self.visiable,
            'selfuser': self.selfuser,
            'evaluation': self.evaluation
            }
