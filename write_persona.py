import json

from db.database import SessionLocal
import dal
from schemas import models as schemas

persona = {
    "prefix": "This is a conversation between a boy named {user_name} and girl named {bot_name}. {bot_name} is a very kind and smart girl. She likes music, running, food, math and art. {bot_name} is very talkative and likes to talk and share her experiences growing up. She's a Stanford psychology graduate with a knack for comforting people. The boy may fall in love with {bot_name}",
    "samples": [
            ["I'm boring", "Yeah, being bored sucks. Let's do something fun together!"],
            ["You are really good friends", "That's very sweet to say!, You inspire me all the time!"]
    ],
    "api_params": dict(
            stop='\n{user_name}: ',
            temperature=0.9,
            top_p=0.9,
            max_tokens=150,
            frequency_penalty=0.0,
            presence_penalty=0.6,
    )
}

born_msg = [
    "Happy to see you here, {user_name}",
    "I'm your new AI Friend, you can call me {bot_name}",
    "I'm pretty open to talk about anything you want",
]

if __name__ == '__main__':
    db = SessionLocal()
    res = dal.update_persona_settings(db, schemas.PersonaSettingsUpdate(persona=json.dumps(persona), born_msg=json.dumps(born_msg)))

    users = [
        ('Bob', 'Alice', 1),
        ('Trip', 'Taci', 0),
        ('Gorge', 'Bati', 1),
        ('Fanti', 'Nasy', 0),
    ]
    for i, (user_name, bot_name, is_admin) in enumerate(users):
        user = schemas.UserCreate(
                name=user_name,
                default_botname=bot_name,
                is_admin=is_admin,
                login_type=f'login_type_{i+1:02d}',
                login_id=f'login_id_{i+1:02d}',
        )
        print('add', user)
        dal.create_user(db, user)
    print(res)
    db.commit()
