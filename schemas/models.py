from typing import List, Optional
from enum import Enum, IntEnum

import datetime
from pydantic import BaseModel

class ComRspModel(BaseModel):
    err_code: int = 0
    err_msg: Optional[str] = None

class Gender(str, Enum):
    male = 'Male'
    female = 'Female'
    unknow = 'Non-Binary'

class UserBase(BaseModel):
    name: str
    email: Optional[str]
    bio: Optional[str]
    interest: Optional[int]
    birthday: Optional[datetime.date]
    avatar: Optional[str]
    gender: Optional[Gender] = Gender.unknow
    default_botid: Optional[str]

    login_type: str
    login_id: str

class UserCreate(UserBase):
    password: Optional[str]
    device_id: Optional[str]
    default_botname: Optional[str]
    default_botavatar: Optional[str]

class UserCreateDemo(BaseModel):
    username: str
    # id: Optional[str]

class UserUpdate(BaseModel):
    name: Optional[str]
    email: Optional[str]
    bio: Optional[str]
    interest: Optional[int]
    birthday: Optional[datetime.date]
    avatar: Optional[str]
    gender: Optional[Gender]

class User4AdminUpdate(UserUpdate):
    is_active: Optional[bool]
    is_admin: Optional[bool]
    password: Optional[bool]

class User(UserBase):
    id: str
    reg_device_id: Optional[str]
    last_device_id: Optional[str]
    default_botname: Optional[str]
    last_login_time: Optional[datetime.datetime]

    class Config:
        orm_mode = True

class User4Admin(User):
    is_active: Optional[bool]
    is_admin: Optional[bool] = False
    class Config:
        orm_mode = True

class BotBase(BaseModel):
    name: str
    avatar: Optional[str]

class BotCreate(BotBase):
    pass

class BotUpdate(BaseModel):
    name: Optional[str]
    avatar: Optional[str]

class Bot(BotBase):
    id: Optional[str]
    class Config:
        orm_mode = True

class Bot4AdminUpdate(BotUpdate):
    persona: Optional[str]

class Bot4Admin(Bot):
    persona: Optional[str]
    class Config:
        orm_mode = True

class OAuthLogin(BaseModel):
    login_type: str
    login_id: str
    device_id: str
    data: Optional[str]

class OAuthOut(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None

class MessageBase(BaseModel):
    topic: Optional[str] = None
    srcid: Optional[str] = None
    create_time: Optional[datetime.datetime] = None
    msg: str

class MessageBase1(BaseModel):
    topic: Optional[str] = None
    srcid: Optional[str] = None
    create_time: Optional[datetime.datetime] = None
    msg: str


class MessageBase(BaseModel):
    srcid: Optional[str] = None
    create_time: Optional[datetime.datetime] = None
    content: str
    class Config:
        orm_mode= True

class MessageCreate(MessageBase):
    pass

class ConversationMessage(BaseModel):
    msgid: str
    content: str
    msg_time: datetime.datetime

class MessageEvaluation(BaseModel):
    msgid: str
    evaluate: int

class MessageOut(MessageBase1):
    id: int
    visiable: Optional[bool] = None
    class Config:
        orm_mode = True

# class ConversationMessage(BaseModel):
#     msgid: int
#     msg: str
#     msg_time: datetime.datetime

class ConversationOut(BaseModel):
    srcid: Optional[str] = None
    src: ConversationMessage
    reply: ConversationMessage

class PersonaSettings(BaseModel):
    persona: str
    born_msg: str
    create_time: datetime.datetime

    class Config:
        orm_mode = True

class PersonaSettingsUpdate(BaseModel):
    persona: Optional[str]
    born_msg: Optional[str]

class DebugPromptInfo(BaseModel):
    prompt: str
    api_params: str

class UserDemo(BaseModel):
    id: str
    username: str

class SendMessageRes(BaseModel):
    # day: Optional[str]
    fromUserId: str
    toUserId: str
    content: str
    msgid: str
    type: int
    selfuser: bool
    reply_time: datetime.datetime
    evaluation: Optional[int]
    class Config:
	    orm_mode=True

class MessageByDate(BaseModel):
    day: str
    content: List[SendMessageRes]

class RobotInfo(BaseModel):
    robot_id: int
    intruction: str
    sample: str


if __name__ == '__main__':
    external_data = dict(id=1, login_type='test_login_type', login_id='test_login_id', password='testpwd', name='testname')
    user = User(**external_data)
    import pdb; pdb.set_trace()
    print(user)
    user = UserCreate(**external_data)
    print(user)
    print(user.dict())
