# encoding:utf8

import copy
import json
import time
import asyncio
import logging
import functools
import aiohttp
from aiohttp import ClientSession

from config import fbconfig

def retry(retries=3, cooldown=1, verbose=True):

    def wrap(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            retries_count = 0

            while True:
                code, result = await func(*args, **kwargs)
                retries_count += 1

                if code == 200:
                    break

                else:
                    try:
                        params = json.dumps(args)
                    except:
                        params = ''

                    message = "Got response ({}, {}), request params: {} " \
                              "{} of {} retries attempted".format(code, result, params, retries_count, retries)
                    verbose and logging.warning(message)

                if retries_count < retries:

                    if cooldown:
                        await asyncio.sleep(cooldown)

                else:
                    raise RuntimeError(result)

            return result
        return inner
    return wrap


@retry()
async def gen_async_task(options):

    try:
        ops = copy.deepcopy(options)
    except:
        ops = options

    method  = ops.pop('method', 'GET')
    url     = ops.pop('url')

    conn = aiohttp.TCPConnector(ssl=False)
    if fbconfig.api.proxy:
        ops['proxy'] = fbconfig.api.proxy

    async with ClientSession(connector=conn) as session:
        async with session.request(method, url, **ops) as response:
            return response.status, await response.read()


async def request_all(options_list):

    tasks = [gen_async_task(options) for options in options_list]

    return await asyncio.gather(*tasks)


async def request(options):

    task = gen_async_task(options)
    result = await asyncio.gather(task)

    return result[0]

