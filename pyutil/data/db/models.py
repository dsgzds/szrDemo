# encoding: utf8

import copy
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, SmallInteger, DateTime, String, inspect, Float, Text, JSON, Date
from sqlalchemy.sql import func

from .session import Session
from .mysql import BaseModel, ModelManager as Manager

Base = declarative_base()
SECRET_KEY = 'light-do'


class UserModel(Base, BaseModel):

    __tablename__ = 'user'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String)
    platform    = Column(String)
    is_vip      = Column(SmallInteger)
    count       = Column(Integer)

    modified_column = ['is_vip', 'count', 'is_del']


class ImageModel(Base, BaseModel):

    __tablename__ = 'image'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String)
    space_name  = Column(String)
    image_id    = Column(String)
    data        = Column(JSON)
    is_del      = Column(SmallInteger, default=0)

    modified_column = ['is_del']


class ImageFeatureModel(Base, BaseModel):

    __tablename__ = 'image_feature'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String)
    image_id    = Column(String)
    feature_id  = Column(String)
    ext_version = Column(String)
    uri         = Column(String)
    data        = Column(JSON)
    is_del      = Column(SmallInteger, default=0)

    modified_column = ['is_del']


class WorkspaceModel(Base, BaseModel):

    __tablename__ = 'workspace'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String)
    name        = Column(String)
    data        = Column(JSON)
    is_del      = Column(SmallInteger, default=0)

    modified_column = ['is_del']


class VideoModel(Base, BaseModel):

    __tablename__ = 'video'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String)
    name        = Column(String)
    space_name  = Column(String)
    type        = Column(String)
    origin_id   = Column(String)
    video_id    = Column(String)
    uri         = Column(String)
    data        = Column(JSON)
    is_del      = Column(SmallInteger, default=0)

    modified_column = ['is_del']


class VideoFeatureModel(Base, BaseModel):
    
    __tablename__ = 'video_feature'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String)
    video_id    = Column(String)
    ext_version = Column(String)
    feature_id  = Column(String)
    uri         = Column(String)
    task_id     = Column(String)
    faces       = Column(JSON)
    data        = Column(JSON)
    is_del      = Column(SmallInteger, default=0)

    modified_column = ['is_del', 'uri']


class RefaceRecordModel(Base, BaseModel):

    __tablename__ = 'reface_record'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(String)
    video_id        = Column(String)
    video_feature   = Column(String)
    swap_version    = Column(String)
    task_id         = Column(String)
    params          = Column(JSON)
    status          = Column(SmallInteger)
    err_msg         = Column(String)
    result_uri      = Column(String)
    data            = Column(JSON)
    is_del          = Column(SmallInteger, default=0)
    create_time     = Column(DateTime, default=func.now())

    modified_column = ['is_del', 'status', 'err_msg', 'result_uri']


class MotionRecordModel(Base, BaseModel):

    __tablename__ = 'motion_record'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(String)
    video_id        = Column(String)
    video_feature   = Column(String)
    image_feature   = Column(String)
    face_ids        = Column(String)
    motion_version  = Column(String)
    task_id         = Column(String)
    params          = Column(JSON)
    status          = Column(SmallInteger)
    err_msg         = Column(String)
    result_uri      = Column(String)
    data            = Column(JSON)
    is_del          = Column(SmallInteger, default=0)
    create_time     = Column(DateTime, default=func.now())

    modified_column = ['is_del', 'status', 'err_msg', 'result_uri']


class BabyRecordModel(Base, BaseModel):

    __tablename__ = 'baby_record'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(String)
    video_id        = Column(String)
    video_feature   = Column(String)
    swap_version    = Column(String)
    task_id         = Column(String)
    params          = Column(JSON)
    status          = Column(SmallInteger)
    err_msg         = Column(String)
    result_uri      = Column(String)
    data            = Column(JSON)
    is_del          = Column(SmallInteger, default=0)
    create_time     = Column(DateTime, default=func.now())

    modified_column = ['is_del', 'status', 'err_msg', 'result_uri']


User            = Manager(UserModel)
Image           = Manager(ImageModel)
Video           = Manager(VideoModel)
Workspace       = Manager(WorkspaceModel)
ImageFeature    = Manager(ImageFeatureModel)
VideoFeature    = Manager(VideoFeatureModel)
RefaceRecord    = Manager(RefaceRecordModel)
MotionRecord    = Manager(MotionRecordModel)
BabyRecord      = Manager(BabyRecordModel)

