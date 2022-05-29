# encoding:utf8

from flask import jsonify

def invalid(code=-1, msg='Invalid Params'):
    return jsonify(dict(
            code    = code,
            message = msg
        ))


def success(msg='success', data=None):
    rsp = dict(
        code    = 0,
        message = msg,
    )

    if data is not None:
        rsp['data'] = data

    return jsonify(rsp)


def error(code=-1, msg='error'):
    
    return jsonify(dict(
        code    = code,
        message = msg
    ))


