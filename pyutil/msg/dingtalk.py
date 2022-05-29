import os
import json
import requests

Token = 'b76ec3e18bde76f86cbc7bb6efaaf29cb835a51e51d7e77a00c28cabe66efcbc'

def send(content, token=Token):

    url = "https://oapi.dingtalk.com/robot/send?access_token=%s" % token

    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }

    rsp = requests.post(url, json=data, headers=headers)
    print(json.loads(rsp.content))



def send_download_giphy_log():
    pass

def send_reface_task_log():
    pass

def send_upload_log():
    pass

def send_sys_monitor():
    pass


if __name__ == '__main__':
    # send('test', 'test')
    # text = get_process()
    # text = get_mem()
    # get_nvi()
    text = get_top()
    send(text)



