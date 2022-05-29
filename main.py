from csv import Dialect
import httptools
from typing import List, Optional
import datetime
import json
import numpy as np
from pydantic import BaseModel
import logging
import requests
from sqlalchemy import Column, Integer, false, func, or_
from torch import from_numpy
from zmq import Message
import id_gen
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from fastapi import Depends, FastAPI, HTTPException, Request, Response, APIRouter
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session

from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException

from schemas import models as schemas
from db import models
from db.database import SessionLocal
import dal
from chat_bot_gpt3 import chat_api, PromptEngine, gpt3_api
from config import config
from pyutil.log.log import init as init_log

import uvicorn

init_log(config.log)
token_auth_scheme = HTTPBearer()
templates = Jinja2Templates(directory="templates")
app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    try:
        request.state.db = SessionLocal()
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response


class Settings(BaseModel):
    authjwt_secret_key: str = "gogogo2089@light"
    authjwt_access_token_expires = datetime.timedelta(hours=2)

@AuthJWT.load_config
def get_config():
    return Settings()

@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

#@app.exception_handler(RequestValidationError)
#async def validation_exception_handler(request: Request, exc: RequestValidationError):
#
#    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
#    # or logger.error(f'{exc}')
#    logging.error(request, exc_str)
#    content = {'status_code': 10422, 'message': exc_str, 'data': None}
#    return JSONResponse(content=content, status_code=422)


# Dependency
def get_db(request: Request):
    return request.state.db

class AdminAuthorizeError(AuthJWTException):
    """
        admin user is required
    """
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

# Dependency
def admin_authorize(request: Request):
    Authorize = AuthJWT(request)
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    user = dal._get_user(request.state.db, current_userid)
    if not user.is_admin:
        raise AdminAuthorizeError(401, 'admin user is required')
    return user


usr_router = APIRouter()


@usr_router.post("/user/register", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user_out = dal.create_user(db, user)
    return user_out


@usr_router.put("/user", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
def update_me(update_data: schemas.UserUpdate, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    return dal.update_user(db, current_userid, update_data)


@usr_router.put("/bot", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
def update_mybot(update_data: schemas.BotUpdate, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    return dal.update_bot(db, current_userid, update_data)

@usr_router.delete("/user", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
def destroy_me(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    return dal.delete_user(db, current_userid)

@usr_router.post("/auth/login", response_model=schemas.OAuthOut)
def login_user(auth_info: schemas.OAuthLogin, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    return dal.login_user(db, auth_info, Authorize)

@usr_router.post("/auth/refresh", response_model=schemas.OAuthOut, dependencies=[Depends(token_auth_scheme)])
def refresh_access_token(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_refresh_token_required()
    current_user = Authorize.get_jwt_subject()
    new_access_token = Authorize.create_access_token(subject=current_user)
    return schemas.OAuthOut(access_token=new_access_token)

@usr_router.post("/auth/logout", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
def logout_user(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    return dal.logout_user(db, current_userid)

@usr_router.get("/user", response_model=schemas.User, dependencies=[Depends(token_auth_scheme)])
def read_me(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    return dal.get_user(db, current_userid)

@usr_router.get("/bot", response_model=schemas.Bot, dependencies=[Depends(token_auth_scheme)])
def read_mybot(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    return dal.get_bot(db, current_userid, botid=None)

@usr_router.get("/msgs/hist", response_model=List[schemas.MessageOut], dependencies=[Depends(token_auth_scheme)])
def hist_message(start_id: Optional[int]=0, limit: Optional[int]=50, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    return dal.get_hist_message(db, current_user, start_id, limit)

@usr_router.post("/msgs/send", response_model=schemas.ConversationOut, dependencies=[Depends(token_auth_scheme)])
async def send_message(message: schemas.MessageCreate, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    src_msg_time = datetime.datetime.now()
    code, resp_msg = await chat_api(message.msg, current_userid, db)
    if code != 200 or not resp_msg:
        resp_msg = ["sorry, I can't catch you"]
    msg1, msg2 = dal.add_conversation_log(db, current_userid, message.msg, resp_msg, src_msg_time)
    if None in (msg1, msg2):
        return

    return schemas.ConversationOut(
            src = schemas.ConversationMessage(
                msgid       = msg1.id,
                content         = msg1.msg,
                msg_time    = msg1.create_time
            ),
            reply = [schemas.ConversationMessage(
                msgid       = msg.id,
                content         = msg.msg,
                msg_time    = msg.create_time
            ) for msg in msg2 ],
    )

@usr_router.get("/msgs/pop", response_model=List[schemas.MessageOut], dependencies=[Depends(token_auth_scheme)])
async def pop_message(start_id: Optional[int]=-1, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    Authorize.jwt_required()
    current_userid = Authorize.get_jwt_subject()
    rst = await dal.pop_user_message(db, current_userid, start_id)
    return rst

@usr_router.put("/users/{userid}", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
def update_user(userid: str, update_data: schemas.User4AdminUpdate, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid admin access token is required to access this route"""
    return dal.update_user(db, userid, update_data, operator=user)

@usr_router.delete("/users/{userid}", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
def destroy_user(user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    return dal.delete_user(db, user.id, operator=user)

@usr_router.put("/bots/{botid}", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
def update_bot(botid: str, update_data: schemas.Bot4AdminUpdate, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid admin access token is required to access this route"""
    return dal.update_bot(db, None, update_data, botid=botid, operator=user)

@usr_router.get("/users", response_model=List[schemas.User4Admin], dependencies=[Depends(token_auth_scheme)])
def read_user_list(user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid admin access token is required to access this route"""
    return dal.get_user_list(db, operator=user)


@usr_router.get("/users/{userid}", response_model=schemas.User4Admin, dependencies=[Depends(token_auth_scheme)])
def read_user(userid: str, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid admin access token is required to access this route"""
    return dal.get_user(db, userid, operator=user)

@usr_router.get("/bots/{botid}", response_model=schemas.Bot4Admin, dependencies=[Depends(token_auth_scheme)])
def read_bot(botid: str, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid admin access token is required to access this route"""
    return dal.get_bot(db, userid=None, botid=botid, operator=user)

@usr_router.get("/settings/persona", response_model=schemas.PersonaSettings, dependencies=[Depends(token_auth_scheme)])
def get_persona_settings(user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid admin access token is required to access this route"""
    return dal.get_persona_settings(db, operator=user)

@usr_router.put("/settings/persona", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
def update_persona_settings(update_data: schemas.PersonaSettingsUpdate, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid admin access token is required to access this route"""
    return dal.update_persona_settings(db, update_data, operator=user)

@usr_router.get("/msgs/hist/{userid}", response_model=List[schemas.MessageOut], dependencies=[Depends(token_auth_scheme)])
def hist_message(userid: str, start_id: Optional[int]=-1, limit: Optional[int]=50, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    return dal.get_hist_message(db, userid, start_id, limit)

@usr_router.post("/msgs/send/{userid}", response_model=schemas.ConversationOut, dependencies=[Depends(token_auth_scheme)])
async def send_message(userid: str, message: schemas.MessageCreate, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    src_msg_time = datetime.datetime.now()
    code, resp_msg = await chat_api(message.msg, userid, db)
    if code != 200:
        resp_msg = ["sorry, I can't catch you"]
    msg1, msg2 = dal.add_conversation_log(db, userid, message.msg, resp_msg, src_msg_time)
    if None in (msg1, msg2):
        return

    return schemas.ConversationOut(
            src = schemas.ConversationMessage(
                msgid       = msg1.id,
                msg         = msg1.msg,
                msg_time    = msg1.create_time
            ),
            reply = [schemas.ConversationMessage(
                msgid       = msg.id,
                msg         = msg.msg,
                msg_time    = msg.create_time
            ) for msg in msg2],
    )

@usr_router.get("/msgs/pop/{userid}", response_model=List[schemas.MessageOut], dependencies=[Depends(token_auth_scheme)])
async def pop_message(userid: str, start_id: Optional[int] = -1, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid access token is required to access this route"""
    rst = await dal.pop_user_message(db, userid, start_id)
    return rst

@usr_router.get("/msgs/prompt/{userid}/", response_model=schemas.DebugPromptInfo, dependencies=[Depends(token_auth_scheme)])
def get_user_prompt(userid: str, msg: str, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid access token is required to access this route, for debug"""
    engine = PromptEngine(msg, userid, db)
    prompt = engine.gen_prompt()
    return schemas.DebugPromptInfo(prompt=prompt, api_params=json.dumps(engine.api_params))




@usr_router.post("/msgs/prompt/debug", response_model=schemas.ComRspModel, dependencies=[Depends(token_auth_scheme)])
async def debug_user_prompt(prompt_params: schemas.DebugPromptInfo, user: models.User = Depends(admin_authorize), db: Session = Depends(get_db)):
    """A valid access token is required to access this route, for debug"""
    try:
        api_params = json.loads(prompt_params.api_params)
    except:
        api_params = {}
    rsp = await gpt3_api(prompt_params.prompt, api_params)
    if not rsp or rsp.status_code != 200:
        return schemas.ComRspModel(err_code=-1, err_msg='api failed')
    else:
        rsp = json.loads(rsp.text)
        return schemas.ComRspModel(err_code=0, err_msg=rsp['choices'][0]['text'])

@usr_router.post("/msgs/evaluate")
def evalutate_massage(msg: schemas.MessageEvaluation, db: Session = Depends(get_db)):
    msg_info = db.query(models.Message).filter(models.Message.id == msg.msgid).first()
    if msg_info.selfuser:
        msg_info = db.query(models.Message).filter(models.Message.id == msg.msgid+'_r').first()
    msg_info.evaluation = msg.evaluate
    db.commit()
    return {'msgid': msg.msgid,
    'content': msg_info.content,
    'evaluation':msg.evaluate}


@usr_router.post("/user/create_user_demo1", response_model=schemas.UserDemo)
def create_user_demo1(user: schemas.UserCreateDemo, db: Session = Depends(get_db)):
    user_out = dal.create_user_demo1(db, user)
    return user_out

@usr_router.get("/msg/history_msg_bydate", response_model=List[schemas.SendMessageRes])
def get_history_msg_bydate(userid: str, db: Session = Depends(get_db)):
    uid = id_gen.text2uid(userid)
    db_msgs = db.query(models.Message.create_time, func.group_concat(models.Message).label('msgs')).filter(or_(models.Message.fromUserId == uid, models.Message.toUserId == uid)).group_by(models.Message.create_time).all()
    history_msg = []
    for db_msg in db_msgs:
        history_msg_day = []
        for db_msg_day in db_msg['msgs'].split(','):
            msg = schemas.SendMessageRes.from_orm(db_msg_day)
            if msg['fromUserId'] == uid:
                msg_out = schemas.SendMessageRes(
                fromUserId=userid,
                toUserId=msg['toUserId'],
                content=msg['content'],
                msgid=msg['id'],
                type=1,
                selfuser=msg['selfuser'],
                reply_time=msg['create_time'],
                evaluation=msg['evaluation']
            )
            else:
                 msg_day_out = schemas.SendMessageRes(
                    fromUserId=msg['fromUserId'],
                    toUserId=userid,
                    content=msg['content'],
                    msgid=msg['id'],
                    type=1,
                    selfuser=msg['selfuser'],
                    reply_time=msg['create_time'],
                    evaluation=msg['evaluation']
                    )

            history_msg_day.append(msg_day_out)
            
        msg_out = schemas.MessageByDate(
            day = db_msg['create_time'].day,
            content = history_msg_day
        )

        history_msg.append(msg_out)

        
    return history_msg

@usr_router.get("/msg/history_msg", response_model=List[schemas.SendMessageRes])
def get_history_msg(userid: str, db: Session = Depends(get_db)):
    uid = id_gen.text2uid(userid)
    db_msg = db.query(models.Message).filter(or_(models.Message.fromUserId == uid, models.Message.toUserId == uid)).all()
    history_msg = []
    for msg in db_msg:
        msg = msg.to_json()
        if msg['fromUserId'] == uid:
            msg_out = schemas.SendMessageRes(
            fromUserId=userid,
            toUserId=msg['toUserId'],
            # fromUserId=msg['fromUserId'],
            # toUserId=msg['toUserId'],
            content=msg['content'],
            msgid=msg['id'],
            type=1,
            selfuser=msg['selfuser'],
            reply_time=msg['create_time'],
            evaluation=msg['evaluation']
        )
        else:
            msg_out = schemas.SendMessageRes(
            fromUserId=msg['fromUserId'],
            toUserId=userid,
            # fromUserId=msg['fromUserId'],
            # toUserId=msg['toUserId'],
            content=msg['content'],
            msgid=msg['id'],
            type=1,
            selfuser=msg['selfuser'],
            reply_time=msg['create_time'],
            evaluation=msg['evaluation']
        )
        history_msg.append(msg_out)
    return history_msg


@usr_router.post('/msg/send_msg_demo1', response_model=schemas.SendMessageRes)
async def send_message_demo1(content: str, fromUserId: str, toUserId: str, db: Session = Depends(get_db)):
    message_out = dal.gpt_j_api(content, fromUserId, toUserId, db)
    return message_out

@usr_router.get('/admin/change_db')
def add_column(db: Session = Depends(get_db)):
    db.execute("ALTER TABLE history_msgs ADD COLUMN evaluation Integer")


@usr_router.post('/admin/add_robot_info')
def add_robot_info(db: Session = Depends(get_db)):
    robot_id = 1
    SPEAKER1 = ' [Human]:'
    SPEAKER2 = ' [Robot]:'
    Intruction = "This is a discussion between a [Human] and a [Robot]. The [Robot] is very kind, empathtic and humous."
    Sample = SPEAKER1 + "How do we learn?\n"+SPEAKER2 + "Through examining our mistakes.\n"+SPEAKER1 + "How do we get into the flow?\n"+ SPEAKER2  + "By letting go of our ego and self absorption.\n"+SPEAKER1 + "How do we grow?\n"+SPEAKER2 + "Through connection and diversity.\n"+SPEAKER1 + "What is the purpose of suffering?\n"+SPEAKER2 + "To learn and grow.\n"
    db_robot = models.Robot(
        robot_id = robot_id,
        intruction = Intruction,
        sample = Sample
    )
    try: 
        db.add(db_robot)
        db.commit
    except Exception as err:
        db.rollback()
        logging.exception(err)
        return

    result = db.query(models.Robot).filter(models.Robot.robot_id == robot_id).first()
    return result


@usr_router.post('/robot/get_robot_info')
def get_robot_info(robot_id: int, db: Session = Depends(get_db)):
    # robot_db = db.query(models.Robot).filter(models.Robot.robot_id == robot_id).first()
    robot_db = db.query(models.Robot).all()
    if robot_db:
        # robot = robot_db.to_json()
        pass
        #  return robot_db
    else: 
        return 'cannot find'
    robot_info = schemas.RobotInfo(
        robot_id=robot_db.robot_id,
        intruction=robot_db.intruction,
        sample=robot_db.sample)
    return robot_info


app.include_router(usr_router, prefix='/api/v0')


@app.get('/')
async def root(request: Request):
    return templates.TemplateResponse("chat.html", dict(request=request))


if __name__ == '__main__':
    uvicorn.run(app='main:app', host="0.0.0.0", port=9090, reload=True, debug=True)
