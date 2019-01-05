# coding=utf-8
from urllib.parse import urljoin
import asyncio
import aiohttp
import aiofiles
import os
import subprocess

headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36"}
headers_x_flash = {"X-Requested-With":"ShockwaveFlash/29.0.0.171","user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36"}

async def down_videos_for_concat(urls,name,requests_session):
    async def download_one(semaphore, session,url,name):
        if os.path.exists(name):
            return True
        try:
            if("vali-dns.cp31.ott.cibntv.net" in url):
                response = requests_session.get(url, headers=headers)
                response.raise_for_status()
                video_content = response.content
            else:
                async with semaphore:
                    async with session.get(url,headers=headers,timeout=(50 if ".ts" in url else 60*4)) as response:
                        if response.status == 200:
                            video_content = await response.read()  # Binary Response Content: access the response body as bytes, for non-text requests
                        else:
                            print("no 200"+"-"+url)
                            response = requests_session.get(url, headers=headers,timeout=(0.04 if ".ts" in url else 3))
                            response.raise_for_status()
                            video_content = response.content
        except Exception as e:
            print(e)
            return await download_one(semaphore, session,url,name)
        async with aiofiles.open(name, 'wb') as f:
            await f.write(video_content)
        return True

    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(30)  # 用于限制并发请求数量
        todo = [download_one(semaphore,session,url,"{}_{}".format(name,i)) for i,url in enumerate(urls,start=100)]
        results = await asyncio.gather(*todo)
        return len(results)

def down_video_hls(requests_session,url,name,path="./"):
    response = requests_session.get(url,headers=headers)
    lines = [line.strip() for line in response.text.split("\n") if line.strip() != ""]
    if lines[-1].endswith("m3u8"):
        url = urljoin(url, lines[-1])
        response = requests_session.get(url,headers=headers)
        lines = [line.strip() for line in response.text.split("\n") if line.strip() != ""]
    urls = [urljoin(url, line) for line in lines if '.ts' in line]

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(down_videos_for_concat(urls,name,requests_session))
    loop.close()

    cache_files = ["{}_{}".format(name,i) for i,url in enumerate(urls,start=100)]
    with open("{}_list".format(name),"w",encoding="utf-8") as fp:
        for cache_file in cache_files:
            fp.write("file '{}'\n".format(cache_file))
    subprocess.call(
        ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', "{}_list".format(name), '-c', 'copy', name+".ts"]
    )
    for cache_file in cache_files:
        os.remove(cache_file)
    os.remove("{}_list".format(name))

def down_m3u8(requests_session,text,name,path="./"):
    urls = [line.strip() for line in text.split("\n") if '.ts' in line]
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(down_videos_for_concat(urls,name,requests_session))
    loop.close()

    cache_files = ["{}_{}".format(name, i) for i, url in enumerate(urls, start=100)]
    with open("{}_list".format(name), "w", encoding="utf-8") as fp:
        for cache_file in cache_files:
            fp.write("file '{}'\n".format(cache_file))
    subprocess.call(
        ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', "{}_list".format(name), '-c', 'copy', name + ".ts"]
    )
    for cache_file in cache_files:
        os.remove(cache_file)
    os.remove("{}_list".format(name))

def down_video_mp4list(requests_session,urls,name,path="./"):
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(down_videos_for_concat(urls,name,requests_session))
    loop.close()

    cache_files = ["{}_{}".format(name, i) for i, url in enumerate(urls, start=100)]
    with open("{}_list".format(name), "w", encoding="utf-8") as fp:
        for cache_file in cache_files:
            fp.write("file '{}'\n".format(cache_file))
    subprocess.call(
        ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', "{}_list".format(name), '-c', 'copy', name + ".mp4"]
    )
    for cache_file in cache_files:
        os.remove(cache_file)
    os.remove("{}_list".format(name))

def down_video_mp4(session,url,name,path="./"):
    with session.get(url,stream=True) as response:
        with open(name + ".mp4", "wb") as fp:
            for chunk in response.iter_content(chunk_size=10*1024*1024):
                fp.write(chunk)