import json
import httpx
import asyncio
import urllib.parse
import dal
from sqlalchemy.orm import Session
import logging

from write_persona import persona

import requests

API_URL = 'https://api.openai.com/v1/engines/{engine}/completions'
OPENAI_API_KEY = "sjgsibgusigdgdfg"  # add config
API_ENGINS = {
    "davinci",
    "curie",
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {OPENAI_API_KEY}",
}

def_api_params = dict(
        stop="\n",
        temperature=0.9,
        top_p=0.9,
        max_tokens=150,
        frequency_penalty=0.0,
        presence_penalty=0.6,
)


def rsp_test():
    url = 'http://127.0.0.1:8080/api/v0/generate'
    req_data = dict(
        prompt='"hello, how are you',
        num_return_sequences=5,
        stop_words = ["I'm", "good"]
    )
    rsp = requests.post(url, json=req_data)
    if rsp.status_code == 200:
        rsp_data = rsp.json()
        print(rsp_data)
        return rsp_data
    else:
        print(rsp.status_code)
        return rsp.status_code


async def gpt3_api(prompt: str, api_params: dict, engine="davinci"):
    api_params = api_params or def_api_params
    if 'stop' not in api_params:
        api_params['stop'] = '\n'

    logging.info('for debug: %s\napi_params: %s', prompt, api_params)
    async with httpx.AsyncClient(timeout=8.0) as client:
        data = dict(
                prompt=prompt,
                **api_params,
        )
        retry = 2
        while retry > 0:
            try:
                # rsp = await client.post(API_URL.format(engine=engine), data=json.dumps(data), headers=headers)
                # TODO:
                rsp = rsp_test()
                break
            except httpx.ReadTimeout as err:
                retry -= 1
                logging.warn('gpt3 api timeout')
        if retry > 0: 
            logging.info('for debug: api result: %s', rsp.text)
            return rsp
        else:
            return None


class PromptEngine(object):
    def __init__(self, msg: str, userid: str, db: Session, hist_wind=10):
        user = dal.get_user(db, userid)
        self.user_name = user.name 
        self.bot_name = user.default_botname
        self.persona = json.loads(dal.get_bot_persona(db, user.default_botid))
        hist_wind = self.persona.get('hist_window', hist_wind)
        hist_msgs = dal.get_hist_message(db, userid, 0, hist_wind)
        hist = [(msg.msg, msg.srcid == userid) for msg in hist_msgs]
        if msg:
            hist.append((msg, True))
        """
            hist format: [("message", bool(is_human_send)), ...]
        """
        self.hist = hist
        api_params = self.persona.get('api_params', def_api_params)
        if 'stop' not in api_params:
            api_params['stop'] = '\n'
        api_params['stop'] = api_params['stop'].format(user_name=self.user_name)
        self.api_params = api_params

    def gen_prompt(self):
        prompt = self.persona['prefix'].format(user_name=self.user_name, bot_name=self.bot_name) + "\n\n"
        for send, recv in self.persona['samples']:
            send, recv = [i.format(user_name=self.user_name, bot_name=self.bot_name) for i in (send, recv)]
            prompt += f"{self.user_name}: {send}\n{self.bot_name}: {recv}\n"

        for msg, is_human_send in self.hist:
            sender = self.user_name if is_human_send else self.bot_name
            prompt += f"{sender}: {msg}\n"
        prompt += f"{self.bot_name}: "
        return prompt

    def parse_result(self, rsp_text):
        try:
            rsp = json.loads(rsp_text)
            rsp = rsp['choices'][0]['text']
        except:
            return []
        rst = []
        prefix = f'{self.bot_name}:'
        prefix_len = len(prefix)
        for line in rsp.split('\n'):
            if line.startswith(prefix):
                line = line[prefix_len:]
            rst.append(line.strip())
        return rst

    async def gen_replay(self, prompt):
        rsp = await gpt3_api(prompt, self.api_params)
        if not rsp or rsp.status_code != 200:
            return rsp.status_code, 'Failed'
        else:
            return 200, self.parse_result(rsp.text)


async def chat_api(msg: str, userid: str=None, db: Session=None):
    engine = PromptEngine(msg, userid, db)
    prompt = engine.gen_prompt()
    rsp = await engine.gen_replay(prompt)
    return rsp


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    name = input(">> name:")
    prompt_maker = PromptEngine(persona, name, db=d)
    hist = []
    bot_name = persona['name']
    while True:
        msg = input(f">> {name}:")
        hist.append((msg, True))
        prompt = prompt_maker.generator(hist)
        print(prompt)

        rsp = loop.run_until_complete(gpt3_api(prompt, persona['api_params']))
        print(rsp.status_code, json.loads(rsp.text))
        rsp = json.loads(rsp.text)
        rsp_msg = rsp['choices'][0]['text']
        print(f"<< {bot_name}: {rsp_msg}")
        hist.append((rsp_msg, False))