import http3, json, asyncio
from bs4 import BeautifulSoup
from marshmallow import ValidationError

from api.steamscraper.parser import parse_tree
from api.db import db, model

async def run_requests():
    client = http3.AsyncClient()
    steam_api_result = await client.get('https://api.steampowered.com/ISteamApps/GetAppList/v2/')
    steam_api_result_list = json.loads(steam_api_result.text)['applist']['apps']
    ids = list(map(lambda obj: obj['appid'], steam_api_result_list))

    len_ids = len(ids)
    end_index_task2 = len_ids // 2
    end_index_task1 = end_index_task2 // 2
    end_index_task3 = end_index_task2 + end_index_task1

    task1 = asyncio.create_task(wrap_generator(steamstore_request(0,end_index_task1+1,ids), 1))
    task2 = asyncio.create_task(wrap_generator(steamstore_request(end_index_task1+1,end_index_task2+1,ids), 2))
    task3 = asyncio.create_task(wrap_generator(steamstore_request(end_index_task2+1, end_index_task3+1, ids), 3))
    task4 = asyncio.create_task(wrap_generator(steamstore_request(end_index_task3+1, len_ids, ids), 4))

    await asyncio.gather(task1, task2, task3, task4)


async def wrap_generator(generator, task_number):

    async for game in generator:
        print(f'Task{task_number}')
        if 'name' in game and game['name']:
            try:
                game_schema = model.GameSchema()
                game_obj = game_schema.load(game)
                db.insert(game_obj)
            except ValidationError as err:
                print(err.messages)
                print(err.valid_data)



async def steamstore_request(begin, end, ids):
    client = http3.AsyncClient()

    for game_id in ids[begin:end]:
        game = {}
        page = await client.get(f'https://store.steampowered.com/app/{game_id}')
        soup = BeautifulSoup(page.text, 'html.parser')
        parse_tree(soup, game)
        yield game
