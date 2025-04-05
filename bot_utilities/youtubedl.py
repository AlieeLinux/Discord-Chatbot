import os
import subprocess
import asyncio
import random

tempmusic = random.randint(1, 2999)
tempthumb = random.randint(1, 3999)
tempmusic2 = random.randint(1, 2999)
tempmusic3 = random.randint(1, 3999)

async def bash_command(cmd):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    #uncomment for debugging purposes
    if stdout:
        print(f"[stdout]\n{stdout.decode()}")
    if stderr:
        print(f"[stderr]\n{stderr.decode()}")


delfile = '/tmp/21.png'
delfile2 = "/tmp/imafile.webp"


#magic wahahahah
async def download_thumbnail(flink):
    await bash_command(f"/usr/bin/yt-dlp '{flink}' --embed-thumbnail --no-download  -o ./temp/{tempthumb}")

async def download_m4a(flink):
    print(f"/usr/bin/yt-dlp -f 140 '{flink}' --embed-metadata -o ./temp/{tempmusic}.m4a")

    await bash_command(f"/usr/bin/yt-dlp -f 140 '{flink}' --embed-metadata -o ./temp/{tempmusic}.m4a")

async def ffmpeg_function(namemusic):
    await bash_command(f'ffmpeg -i ./temp/{tempthumb}.webp -vf "crop=w=min(min(iw\,ih)\,720):h=min(min(iw\,ih)\,720),scale=720:720,setsar=1" -vframes 1 ./temp/{tempmusic2}.png')
    await bash_command(f"ffmpeg -i ./temp/{tempmusic}.m4a -c:a libmp3lame ./temp/{tempmusic3}.mp3")
    await bash_command(f"ffmpeg -i ./temp/{tempmusic3}.mp3 -i ./temp/{tempmusic2}.png -map 1:0 -map 0:0 -c copy './temp/{namemusic}.mp3'")

async def func(links):
    await asyncio.gather(download_thumbnail(links), download_m4a(links))

async def thefunc(link, music_name):
    await func(links=link)
    await ffmpeg_function(namemusic=music_name)
