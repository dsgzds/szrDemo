import firebase_admin
from firebase_admin.messaging import Message, Notification, AndroidConfig, APNSConfig

ios_cred        = firebase_admin.credentials.Certificate('./firebase/firebase-facee-ios.json')
ios_app         = firebase_admin.initialize_app(ios_cred, name='ios_app')

android_cred    = firebase_admin.credentials.Certificate('./firebase/firebase-facee-android.json')
android_app     = firebase_admin.initialize_app(android_cred, name='android_app')

test_cred       = firebase_admin.credentials.Certificate('./firebase/firebase-facee-test.json')
test_app        = firebase_admin.initialize_app(test_cred, name='test_app')


def send(title, message, data, token, platform='ios', env='prod'):

    notification    = Notification(title, message)
    android_config  = AndroidConfig(priority='high')
    apns_config     = APNSConfig(headers={"apns-priority": "10"})

    msg = Message(data, notification, android=android_config, apns=apns_config, token=token)

    app = test_app if env == 'dev' else (ios_app if platform == 'ios' else android_app)
    rsp = firebase_admin.messaging.send(msg, app=app)

    print(rsp)


def send_swap_finished_msg(platform, task_id, token, env='prod'):

    title   = "COOL🎉 Your face swapping has been completed!"
    message = "Click to see >>"

    data = {
        "event": "1",
        "taskId": task_id,
        "resultUrl": "xxx"
    }


    send(title, message, data, token)


if __name__ == '__main__':
    send_swap_finished_msg('ios', 'xxx', 'dQ3hZMQZ2UJ1gH_O6ePy5A:APA91bGRiLAyU-HhDiZFCmwAEgbvykcMjn4M-8-_lqICmCembzdlReoSPFU4FJgC4rrUeIPrjlz5Zj59OEu2nc4FJMG_HukHBiEGA3R81I9G3bMomVsG-h9U7UbRg2HBNqAB5NoEwVG8')

