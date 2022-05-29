import tokenize
import typing
import datetime
import random
import json
import requests
import sqlalchemy
from sqlalchemy.orm import Session
from transformers import AutoTokenizer
from db import models
from db.database import engine
from schemas import models as schemas
import logging
import id_gen
from fastapi_jwt_auth import AuthJWT
from chat_bot_gpt3 import PromptEngine

models.Base.metadata.create_all(bind=engine)

user_idgen = id_gen.generator(1, 1)

tokenizer = AutoTokenizer.from_pretrained('EleutherAI/gpt-j-6B')

def _get_user(db: Session, userid: str):
    uid = id_gen.text2uid(userid)
    db_user = db.query(models.User).filter(models.User.id == uid).first()
    return db_user

def get_user(db: Session, userid: str, operator=None):
    uid = id_gen.text2uid(userid)
    db_user = db.query(models.User).filter(models.User.id == uid).first()
    if not db_user:
        return
    db_oauth = db.query(models.OAuthItem).filter(models.OAuthItem.ownerid == uid).first()
    db_login = db.query(models.LoginLog).filter(models.LoginLog.userid == uid).order_by(models.LoginLog.id.desc()).first()
    db_bot = db.query(models.Bot).filter(models.Bot.id == db_user.default_botid).first()
    external_data = dict(
            id          = userid,
            name        = db_user.name,
            email       = db_user.email,
            avatar      = db_user.avatar,
            gender      = db_user.gender,
            birthday    = db_user.birthday,
            interest    = db_user.interest,
            bio         = db_user.bio,
            login_type  = db_oauth.login_type,
            login_id    = db_oauth.login_id,
            default_botid = id_gen.uid2text(db_user.default_botid),
            default_botname = db_bot.name,
            reg_device_id = db_user.reg_device_id,
            last_device_id = db_login.device_id if db_login else None,
            last_login_time = db_login.create_time if db_login else None,
    )
    if operator and operator.is_admin:
        external_data['is_active'] = db_user.is_active
        external_data['is_admin'] = db_user.is_admin
        return schemas.User4Admin(**external_data)
    else:
        return schemas.User(**external_data)

def get_user_list(db: Session, operator=None):
    # for easy implenment
    uids = db.query(models.User.id).all()
    uids = [i[0] for i in uids]
    rst = []
    for uid in uids:
        db_user = db.query(models.User).filter(models.User.id == uid).first()
        if not db_user:
            continue
        db_oauth = db.query(models.OAuthItem).filter(models.OAuthItem.ownerid == uid).first()
        db_login = db.query(models.LoginLog).filter(models.LoginLog.userid == uid).order_by(models.LoginLog.id.desc()).first()
        db_bot = db.query(models.Bot).filter(models.Bot.id == db_user.default_botid).first()
        rst_user = schemas.User4Admin(
                id          = id_gen.uid2text(uid),
                name        = db_user.name,
                email       = db_user.email,
                avatar      = db_user.avatar,
                gender      = db_user.gender,
                birthday    = db_user.birthday,
                interest    = db_user.interest,
                bio         = db_user.bio,
                is_active   = db_user.is_active,
                is_admin    = db_user.is_admin,
                login_type  = db_oauth.login_type,
                login_id    = db_oauth.login_id,
                default_botid = id_gen.uid2text(db_user.default_botid),
                default_botname = db_bot.name,
                reg_device_id = db_user.reg_device_id,
                last_device_id = db_login.device_id if db_login else None,
        )
        rst.append(rst_user)
    return rst

def update_user(db: Session, userid: str, update_data: typing.Union[schemas.UserUpdate, schemas.User4AdminUpdate], operator=None):
    rst = schemas.ComRspModel(err_code=-1, err_msg='user does not exists')
    db_user = _get_user(db, userid)
    if not db_user:
        return rst

    for key, val in update_data.__dict__.items():
        if val is None:
            continue
        if not hasattr(db_user, key):
            continue
        setattr(db_user, key, val)
    try:
        db.add(db_user)
        db.commit()
    except Exception as err:
        logging.exception(err)
        rst.err_msg = 'db error'
        return rst

    return schemas.ComRspModel(err_code=0)

def update_bot(db: Session, userid: str, update_data: typing.Union[schemas.BotUpdate, schemas.Bot4AdminUpdate], botid: str=None, operator=None):
    rst = schemas.ComRspModel(err_code=-1, err_msg='bot does not exists')
    db_bot = _get_bot(db, userid, botid)
    if not db_bot:
        return rst

    for key, val in update_data.__dict__.items():
        if val is None:
            continue
        if not hasattr(db_bot, key):
            continue
        setattr(db_bot, key, val)
    try:
        db.add(db_bot)
        db.commit()
    except Exception as err:
        logging.exception(err)
        rst.err_msg = 'db error'
        return rst

    return schemas.ComRspModel(err_code=0)

def delete_user(db: Session, userid: str):
    rst = schemas.ComRspModel(err_code=-1, err_msg='user does not exists')
    db_user = _get_user(db, userid)
    if not db_user:
        return rst

    db_user.is_active = False
    try:
        db.add(db_user)
        db.commit()
    except Exception as err:
        logging.exception(err)
        rst.err_msg = 'db error'
        return rst

    return schemas.ComRspModel(err_code=0)

def _get_bot(db: Session, userid: str=None, botid: str=None):
    if not userid and not botid:
        return
    if botid:
        db_botid = id_gen.text2uid(botid)
        db_bot = db.query(models.Bot).filter(models.Bot.id == db_botid).first()
        if not db_bot:
            return
        if userid:
            db_userid = id_gen.text2uid(userid)
            db_user = db_bot.owner
            if db_user.id != userid and not db_user.is_admin:
                # auth error
                return
    else:
        db_userid = id_gen.text2uid(userid)
        db_user = db.query(models.User).filter(models.User.id == db_userid).first()
        if not db_user:
            return
        db_botid = db_user.default_botid
        db_bot = db.query(models.Bot).filter(models.Bot.id == db_botid).first()
        if not db_bot:
            return
    return db_bot

def _check_persona(persona):
    if not persona:
        return False
    try:
        p = json.loads(persona)
        if not p:
            return False
    except:
            return False

    return True

def get_bot_persona(db: Session, botid: str):
    uid = id_gen.text2uid(botid)
    persona = db.query(models.Bot.persona).filter(models.Bot.id == uid).first()
    persona = persona[0] if persona else None
    if _check_persona(persona):
        return persona

    return get_persona_settings(db).persona

def get_bot(db: Session, userid: str=None, botid: str=None, operator=None):
    db_bot = _get_bot(db, userid, botid)
    if not db_bot:
        return
    if operator and operator.is_admin:
        rst = schemas.Bot4Admin.from_orm(db_bot)
        if not _check_persona(rst.persona):
            rst.persona = get_persona_settings(db).persona
    else:
        rst = schemas.Bot.from_orm(db_bot)
    rst.id = id_gen.uid2text(db_bot.id)
    return rst

def login_user(db: Session, oauth: schemas.OAuthLogin, Authorize: AuthJWT):
    db_oauth = db.query(models.OAuthItem).filter(models.OAuthItem.login_type == oauth.login_type, models.OAuthItem.login_id == oauth.login_id).first()
    if not db_oauth:
        return

    db_user = db_oauth.owner
    if not db_user.is_active:
        return

    userid = id_gen.uid2text(db_user.id)
    access_token = Authorize.create_access_token(subject=userid)
    refresh_token = Authorize.create_refresh_token(subject=userid)
    # write login log
    db_login_log = models.LoginLog(
            userid      = db_user.id,
            device_id   = oauth.device_id,
            access_token = access_token,
            refresh_token = refresh_token,
            data        = oauth.data,
    )
    try:
        db.add(db_login_log)
        db.commit()
    except Exception as err:
        db.rollback()
        logging.exception(err)
        return

    rst = schemas.OAuthOut(
            access_token=access_token,
            refresh_token=refresh_token,
    )
    return rst

def logout_user(db: Session, userid: str):
    uid = id_gen.text2uid(userid)
    db_user = db.query(models.User).filter(models.User.id == uid).first()
    if not db_user:
        return

    # write login log
    db_login_log = models.LoginLog(
            userid      = db_user.id,
            is_logout   = True,
    )
    try:
        db.add(db_login_log)
        db.commit()
    except Exception as err:
        db.rollback()
        logging.exception(err)
        return

    rst = schemas.ComRspModel(
            err_code = 0,
    )
    return rst

def get_user_by_profileid(db: Session, profile_id: str):
    return db.query(models.User).filter(models.User.profileid == profile_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


#def get_users(db: Session, skip: int = 0, limit: int = 100):
#    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    fake_hashed_password = user.password or '' + "notreallyhashed"
    user_id, bot_id, auth_id = [next(user_idgen) for _ in range(3)]
    db_user = models.User(
            id          = user_id,
            email       = user.email,
            name        = user.name,
            avatar      = user.avatar,
            gender      = user.gender,
            birthday    = user.birthday,
            bio         = user.bio,
            interest    = user.interest,
            default_botid   = bot_id,
            reg_device_id = user.device_id,
    )
    db_bot = models.Bot(
            id = bot_id,
            name        = user.default_botname or f"{user.name}'s friends",
            avatar      = user.default_botavatar or '',
            ownerid     = user_id,
    )
    db_oauth = models.OAuthItem(
            id          = auth_id,
            login_type  = user.login_type,
            login_id    = user.login_id,
            ownerid    = user_id,
    )
    db_topic = models.Topic(
            id = bot_id,
            ownerid = bot_id,
            name = id_gen.uid2text(bot_id),
    )

    try:
        db.add(db_user)
        db.add(db_bot)
        db.add(db_oauth)
        db.add(db_topic)
        db.commit()
        db.refresh(db_user)
    except Exception as err:
        db.rollback()
        logging.exception(err)
        return

    rst_user = schemas.User(
            id          = id_gen.uid2text(user_id),
            is_active   = db_user.is_active,
            **user.dict())

    return rst_user

def _get_hist_message_count(db: Session, userid: str, visiable=True):
    db_user = _get_user(db, userid)
    if not db_user:
        return 0
    topicid = db_user.default_botid
    query = db.query(sqlalchemy.func.count(models.Message1.id)).filter(models.Message1.topicid== topicid)
    if visiable is not None:
        query = query.filter(models.Message1.visiable == visiable)
    return query.first()[0]


def _get_last_hist_message_id(db: Session, userid: str, visiable=True):
    db_user = _get_user(db, userid)
    if not db_user:
        return 0
    topicid = db_user.default_botid
    query = db.query(sqlalchemy.func.max(models.Message1.id)).filter(models.Message1.topicid== topicid)
    if visiable is not None:
        query = query.filter(models.Message.visiable == visiable)
    return query.first()[0]

def _get_last_hist_messages(db: Session, userid: str, visiable=True, limit=3):
    db_user = _get_user(db, userid)
    if not db_user:
        return 0
    topicid = db_user.default_botid
    query = db.query(models.Message1).filter(models.Message1.topicid== topicid).order_by(models.Message1.id.desc())
    if visiable is not None:
        query = query.filter(models.Message1.visiable == visiable)
    return query.limit(limit)[::-1]

def get_hist_message(db: Session, userid: str, start_id: int=0, limit: int=50, visiable=True):
    uid = id_gen.text2uid(userid)
    db_user = db.query(models.User).filter(models.User.id == uid).first()
    if not db_user:
        return None, None
#    topic = db.query(models.Topic).filter(models.Topic.ownerid == db_user.default_botid).first()
#    if not topic:
#        raise
#    topicid = topic.id
    topicid = db_user.default_botid
    query = db.query(models.Message1).filter(models.Message1.topicid== topicid)
    if start_id > 0:
        query = query.filter(models.Message1.id < start_id)
    if visiable is not None:
        query = query.filter(models.Message1.visiable == visiable)
    if limit > 0:
        db_hists = query.order_by(models.Message1.id.desc()).limit(limit)
        db_hists = db_hists[::-1] # reverse
    else:
        db_hists = query.all()

    hists = []
    for db_hist in db_hists:
        hist = schemas.MessageOut.from_orm(db_hist)
        hist.topic=id_gen.uid2text(db_hist.topicid)
        hist.srcid=id_gen.uid2text(db_hist.srcid)
        hists.append(hist)

    return hists

def _pop_user_message(db: Session, db_user: models.User, start_id: int, visiable=True):
    if not db_user:
        return None, None
    topicid = db_user.default_botid
    query = db.query(models.Message1).filter(models.Message1.topicid== topicid)
    if start_id > 0:
        query = query.filter(models.Message1.id > start_id)
    if visiable is not None:
        query = query.filter(models.Message1.visiable == visiable)
    db_hists = query.all()

    hists = []
    for db_hist in db_hists:
        hist = schemas.MessageOut.from_orm(db_hist)
        hist.topic=id_gen.uid2text(db_hist.topicid)
        hist.srcid=id_gen.uid2text(db_hist.srcid)
        hists.append(hist)

    return hists


async def pop_user_message(db: Session, userid: str, start_id: int, visiable=True):
    start = datetime.datetime.now()
    db_bot = _get_bot(db, userid)
    if not db_bot:
        return []
    db_user = db_bot.owner
    msg_cnt = _get_hist_message_count(db, userid, visiable)
    db_msgs = []
    topicid = db_bot.id
    if not msg_cnt:
        start_id = -1
        # write msg
        db_persona = _get_persona_settings(db)
        born_msg = json.loads(db_persona.born_msg)
        for msg in born_msg:
            msg = msg.format(user_name=db_user.name, bot_name=db_bot.name)
            delta = datetime.timedelta(microseconds=random.randint(20, 80) * 10)
            start += delta
            db_msg = models.Message1(
                    topicid=topicid,
                    srcid=db_bot.id,
                    msg=msg,
                    create_time = start
            )
            db_msgs.append(db_msg)

        try:
            for msg in db_msgs:
                db.add(msg)
            db.commit()
        except Exception as err:
            db.rollback()
            logging.exception(err)
            return []
    else:
        last_msgs = _get_last_hist_messages(db, userid)
        if not _check_pop_msg(db_user, last_msgs):
            return []

        start_id = last_msgs[-1].id
        engine = PromptEngine('', userid, db)
        prompt = engine.gen_prompt()
        code, reply = await engine.gen_replay(prompt)
        if code == 200:
            db_msgs = [models.Message1(
                    topicid=topicid,
                    srcid=db_bot.id,
                    msg=msg,
            ) for msg in reply]
            try:
                for db_msg in db_msgs:
                    db.add(db_msg)
                db.commit()
            except Exception as err:
                db.rollback()
                logging.exception(err)
                return []

    return _pop_user_message(db, db_user, start_id, visiable)
            
def _check_pop_msg(db_user, last_msgs):
    now = datetime.datetime.now()
    if not last_msgs:
        return True

    if last_msgs[-2].srcid == db_user.id:
        return True

    if last_msgs[-1].create_time + datetime.timedelta(hours=2) < now:
        return True

    return False
        

def add_conversation_log(db: Session, userid: str, msg_send: str, msg_id: str, msg_reply: str, src_msg_time: datetime.datetime): 
    uid = id_gen.text2uid(userid)
    # db_user = db.query(models.UserDemo).filter(models.UserDemo.id == uid).first()
    # if not db_user:
    #     return None, None

    # botid = db_user.default_botid
    msg1 = models.Message(
            fromUserId=uid,
            toUserId=1,
            id=msg_id,
            content=msg_send,
            create_time=src_msg_time,
            selfuser=True,
    )
    msg2 = models.Message(
            fromUserId=1,
            toUserId=uid,
            id=msg_id+'_r',
            content=msg_reply,
            create_time=datetime.datetime.now(),
            selfuser=False,
    )

    try:
        db.add(msg1)
        db.add(msg2)
        db.commit()
        db.refresh(msg1)
        db.refresh(msg2)
    except Exception as err:
        db.rollback()
        logging.exception(err)
        return None, None

    return msg1, msg2

def create_user_demo1(db: Session, user: schemas.UserCreateDemo):
    Authorize = AuthJWT
    userid = 0
    isExist = db.query(models.UserDemo).filter(models.UserDemo.username == user.username).first()
    if not isExist:
        userid = [next(user_idgen) for _ in range(1)][0]
        db_user = models.UserDemo(
            id=userid,
            username=user.username,
        )
        try:
            db.add(db_user)
        except Exception as err:
            db.rollback()
            logging.exception(err)
            return
    else:
        userid = db.query(models.UserDemo).filter(models.UserDemo.username == user.username).first().id
        # print("userid: ", userid)

    access_token = Authorize().create_access_token(subject=userid)
    refresh_token = Authorize().create_refresh_token(subject=userid)

    # write login log
    db_login_log = models.LoginLog(
        userid=userid,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    try:
        db.add(db_login_log)
        db.commit()
    except Exception as err:
        db.rollback()
        logging.exception(err)
        return

    rst = schemas.UserDemo(
        id = id_gen.uid2text(userid),
        username = user.username
    )
    return rst

def _get_persona_settings(db: Session):
    db_persona = db.query(models.PersonaSettings).order_by(models.PersonaSettings.id.desc()).first()
    return db_persona

def get_persona_settings(db: Session, operator: schemas.User=None) -> schemas.PersonaSettings:
    db_persona = _get_persona_settings(db)
    if not db_persona:
        return schemas.PersonaSettings(persona='', born_msg='')
    return schemas.PersonaSettings.from_orm(db_persona)

def update_persona_settings(db: Session, update_data: schemas.PersonaSettingsUpdate, operator: schemas.User=None) -> schemas.ComRspModel:
    rst = schemas.ComRspModel(err_code=-1, err_msg='system error')
    cur_db_persona = db.query(models.PersonaSettings).order_by(models.PersonaSettings.id.desc()).first()
    if not cur_db_persona:
        db_persona = models.PersonaSettings(persona='{}', born_msg='[]')
    else:
        db_persona = models.PersonaSettings(
                persona=cur_db_persona.persona,
                born_msg=cur_db_persona.born_msg)
        
    for key, val in update_data.__dict__.items():
        if val is None:
            continue
        if not hasattr(db_persona, key):
            continue

        try:
            json.loads(val) 
        except Exception as err:
            logging.exception(err)
            return schemas.ComRspModel(err_code=-1, err_msg='invalid json params')
        setattr(db_persona, key, val)
        
    try:
        db.add(db_persona)
        db.commit()
    except Exception as err:
        logging.exception(err)
        rst.err_msg = 'db error'
        return rst

    return schemas.ComRspModel(err_code=0)

def get_result(input):
    url = 'http://127.0.0.1:8080/api/v0/generate'
    req_data = input
    rsp = requests.post(url, json=req_data)
    if rsp.status_code ==200:
        rsp_data = rsp.json()
        return rsp_data
    else:
        return rsp.status_codes

def get_robot_info(robot_id: int, db):
    robot_db = db.query(models.Robot).filter(models.Robot.robot_id == robot_id).first()
    if robot_db:
        # return robot_db
        pass
    else: 
        return 'cannot find'
    robot_info = schemas.RobotInfo(
        robot_id=robot_db.robot_id,
        intruction=robot_db.intruction,
        sample=robot_db.sample)
    return robot_info

def get_result(input):
    url = 'http://127.0.0.1:8080/api/v0/generate'
    req_data = input
    rsp = requests.post(url, json=req_data)
    if rsp.status_code ==200:
        rsp_data = rsp.json()
        # print(rsp_data)
    else:
        print(rsp.status_code)
    return rsp_data

def choose_res(response,info):
    if response['code'] != -1:
        for res in response['texts']:
            if len(tokenizer.encode(res)) < info['max_len']-1:
                return res
    else:
        return 'response code error'
    print('repost')
    return choose_res(get_result(info),info)

def gpt_j_api(content, fromUserId, toUserId, db):
    # Authorize.jwt_required()
    # current_userid = Authorize.get_jwt_subject()
    src_msg_time = datetime.datetime.now()

    SPEAKER1 = ' [Human]:'#家庭矛盾-指定用户性别
    SPEAKER2 = ' [Dianbot]:'

    Intruction = "This is a short conversation chat between a human and a robot about family conflict issues. The robot's name is Dianbot. The robot is an expert in dealing with family emotional issues and was created by Team Cao in September 2021. The team Cao consists of ten students from Huazhong University of Science and Technology. The Robot is very gentle, empathetic, humorous and considerate. The robot's job is to comfort human emotions and give humans an effective suggestion."

    Sample = SPEAKER1 + "What's your name?\n"+SPEAKER2 + "My name is Dianbot, and you can call me Dian.\n\n"+SPEAKER1 + "How old are you?\n"+ SPEAKER2  + "I was created by Team Cao of Huazhong University of Science and Technology(HUST) in September 2021.\n\n"+SPEAKER1 + "So where do you work?\n"+SPEAKER2 + "I am a robot major in dealing with family emotional issues and was created by Team Cao of HUST in Wuhan.\n\n"+SPEAKER1 + " Do you have colleagues?\n"+SPEAKER2 + "Our team has ten members in total, all of whom are students from HUST.\n\n"+SPEAKER1 + "Where is your hometown? Which cuisine do you like?\n"+SPEAKER2 + "I was born in Wuhan, my favorite food is of course Hubei cuisine.\n\n"

    prompt = Intruction + "\n"*5 + Sample
    intro_dialogue = f"{SPEAKER1}" + '\n'

    max_number_turns = 10
    config = {"info":{},"dialogue":[],"meta":[],"user":[],"assistant":[],"user_memory":[]}
    info = {"prompt":prompt,
                "max_len":40,
                'do_sample':True,
                "top_p":0.7,
                "top_k":10,
                "temperature":0.9,
                "stop_words":['\n','<|endoftext|>','['],
                "min_len":5,
                "length_penalty":0.9,
                "repetition_penalty":1.3,
                "num_return_sequences":1
    }

    config["info"] = info
    dialogue = []
    user = []
    meta = []
    with_knowledge = 3 #先验知识
    user_utt = ''
    initial_situation = config["info"]["prompt"]
    topic_list = ["navigate","schedule","weather"]
    topic_sign = False
    emotion_list = ["afraid","angry","annoyed","anticipating","anxious","apprehensive","ashamed","caring","confident","content","devastated","disappointed","disgusted","embarrassed","excited","faithful","furious","grateful","guilty","hopeful","impressed","jealous","joyful","lonely","nostalgic","prepared","proud","sad","sentimental","surprised","terrified","trusting"]
    emotion_sign = False
    intro_list = ["I AM","I am","i am"]
    intro_sign = False

    #emotion数据集中meta I是用户

    #2
    history_dialog = "History Dialogue:\n"

    dialog_pairs = []
    user_utt = content
    for intronum,intro in enumerate(intro_list):
        if intro in user_utt:
            intro_sign = True
            intro_dialogue = intro_dialogue + user_utt + '\n'


    # dialogue["dialogue"].append([user_utt,""]) #append整个[user_utt,""]
    history_dialog = "History Dialogue:\n"
    for turn in config["dialogue"]:
        history_dialog += f"{turn[0]}" +"\n"
        if turn[1] == "":
            ## NO GENERATION REQUIRED
            pass
        else:
            history_dialog += f"{turn[1]}" +"\n\n"
    # print("history:"+'\n'+history_dialog)
    if topic_sign == True or emotion_sign == True:
        prefix = info['prompt'] + SPEAKER1 + user_utt + '\n' + SPEAKER2
    elif intro_sign == True:
        prefix = Intruction + intro_dialogue + Sample + history_dialog + SPEAKER1 + user_utt + '\n' + SPEAKER2
    else:
        prefix = Intruction + Sample + history_dialog + SPEAKER1 + user_utt + '\n' + SPEAKER2 # prompt = prompt + Human+'\n'
    print('='*72)
    print(prefix)
    print('='*72)
    dialog_pairs.append(SPEAKER1 + user_utt)
    info['prompt'] = prefix

    #更新
    config["dialogue"] = dialogue


    url = 'http://127.0.0.1:8080/api/v0/generate'
    rsp = requests.post(url, json=info)

    if rsp.status_code ==200:
        rsp = json.loads(rsp.text)
        response_all = rsp
        response = choose_res(response_all, info)
        prefix += (response.strip('\n') + '\n')
        info['prompt'] = prefix
        dialogue.append(dialog_pairs)
        dialog_pairs.append(SPEAKER2 + response.strip('\\n'))

        if response != '':
            response_out = response.strip('\\n')
            msg1, msg2 = add_conversation_log(db, fromUserId, content, rsp['log_id'], response_out, src_msg_time)
        else: 
            response_out = 'error, null'
            msg2 = models.Message()
            msg2.create_time='12345'
          

        dialogue.append(dialog_pairs)
        config["dialogue"] = dialogue

        return schemas.SendMessageRes(
            fromUserId=toUserId,
            toUserId=fromUserId,
            content=response_out,
            msgid=rsp['log_id'],
            type=1,
            selfuser=False,
            reply_time=msg2.create_time
            )

    else:
        return rsp.status_code
