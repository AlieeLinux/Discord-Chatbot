import aiohttp
from colorama import Fore as fr
import io
import re
import asyncio
import time
import random
import asyncio
from urllib.parse import quote
from bot_utilities.config_loader import load_current_language, config
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import asyncio
import sys
from duckduckgo_search import AsyncDDGS
import requests
from gradio_client import Client as Flux_Sch
from huggingface_hub import AsyncInferenceClient as huggingface
from huggingface_hub import login
load_dotenv()

hfkey = os.getenv("HF")
print(hfkey)

login(hfkey)
current_language = load_current_language()
internet_access = config['INTERNET_ACCESS']
results_limit = config['MAX_SEARCH_RESULTS']

dalle_3 = AsyncOpenAI(api_key = os.getenv('CHIMERA_GPT_KEY'), base_url = "http://127.0.0.1:1337/v1")
client = AsyncOpenAI(api_key = os.getenv('CHIMERA_GPT_KEY'), base_url = "https://api.naga.ac/v1")


async def anythingxl(prompts, negative):
    if negative == None:
        negative = "(low quality, worst quality:1.2), very displeasing, 3d, watermark, signature, ugly, poorly drawn"
        print(negative)
    client = Flux_Sch("votepurchase/votepurchase-AnythingXL_xl")
    result = client.submit(
	    prompt=prompts,
		negative_prompt=f"{negative}",
		seed=0,
		width=1024,
		height=1024,
		guidance_scale=7,
		num_inference_steps=20,
		api_name="/infer"
    )
    return result.result()

async def ai_hoshino(prompt):
    client = huggingface("Blane187/ai-hoshino-s1-ponyxl-lora-nochekaise", token=os.getenv("HF"))
    results = await client.text_to_image(prompt)
    buffer = random.randint(1, 1111)
    results.save(f"{buffer}.png")
    return f"{buffer}.png"


async def flux_sch(prompt):
    client = huggingface(model="black-forest-labs/FLUX.1-schnell", token=os.getenv("HF"))
    results = await client.text_to_image(prompt=f"{prompt}", width=1024, height=1024)
    buffer = random.randint(1, 1100)
    results.save(F"{buffer}.png")
    return f"{buffer}.png"



async def flux_gen(prompts):
    client = huggingface(model="stabilityai/stable-diffusion-3.5-large", token=os.getenv("HF"))
    image = await client.text_to_image(prompts)
    buffer = random.randint(1, 1000)
    image.save(f"{buffer}.png")
    return f"{buffer}.png"

def tenor(search, number):
    apikey = os.getenv("TENOR")
    ckey = "my_test_app"  # set the client_key for the integration
    lmt = number
    search_term = search

    r = requests.get(
    "https://tenor.googleapis.com/v2/search?q=%s&key=%s&client_key=%s&limit=%s" % (search_term, apikey, ckey,  lmt))

    if r.status_code != 200:
        return "error"

    return r.json()
    


def fetch_chat_models(key):
    models = ''
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }

    response = requests.get('https://api.naga.ac/v1/models', headers=headers)
    if response.status_code == 200:
        ModelsData = response.json()
        for model in ModelsData.get('data'):
            models += model['id'] + "\n"

    else:
        print(f"Failed to fetch chat models. Status code: {response.status_code}")

    return models


def g4f_fetch_chat_models(key):
    models = ''
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }

    response = requests.get('http://127.0.0.1:1337/v1/models', headers=headers)
    if response.status_code == 200:
        ModelsData = response.json()
        for model in ModelsData.get('data'):
            models += model['id'] + "\n"

    else:
        print(f"Failed to fetch chat models. Status code: {response.status_code}")

    return models


def sdxl(prompt):
    response = client.Image.create(
    model="kandinsky-2.2",
    prompt=prompt,
    n=1,  # images count
    size="1024x1024"
)
    return response['data'][0]["url"]

if sys.platform.lower().startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def search(prompt):
    if not internet_access or len(prompt) > 200 or "/ns" in prompt:
        return
    if url_match := re.search(r'(https?://\S+)', prompt):
        search_query = url_match.group(0)
    else:
        search_query = prompt
    blob = ""
    prompt = prompt.replace("Avernus", "").replace("@Avernus", "")
    async with AsyncDDGS() as ddgs:
        search = ddgs.text(search_query, max_results=results_limit)
        for result in enumerate(search):
            body_value = result.get("body", None)
            href_value = result.get("href", None)
            title_value = result.get("title", None)
            blob += f'Title: {title_value}\n\n{body_value}\n\nURL: {href_value}\n\n'
        blob += "\nSearch results allows you to have real-time information and the ability to browse the internet.\n As the links were generated by the system rather than the user, please send a response along with the link if necessary(disregard the search results if you already know the answer).\n"
    print(blob)
    return blob

'''
def fetch_models():
    openai.api_key = os.getenv('CHIMERA_GPT_KEY')
    modelget = openai.Model.list()
    for models in modelget['data']:
        print(models['id'], models['owner'], models['ready'])
    return models
'''

async def dall_e_3(model, prompt):
    response = await client.images.generate(
        model=model,
        prompt=prompt,
    )
    imagefileobjs = []
    for image in response.data:
        image_url = image.url
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                content = await response.content.read()
                img_file_obj = io.BytesIO(content)
                imagefileobjs.append(img_file_obj)
    return imagefileobjs


async def dalle3(model, prompt):
    response = await dalle_3.images.generate(
        model=model,
        prompt=prompt,
    )
    imagefileobjs = []
    for image in response.data:
        image_url = image.url
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                content = await response.content.read()
                img_file_obj = io.BytesIO(content)
                imagefileobjs.append(img_file_obj)
    return imagefileobjs


'''
async def dalle3(model, prompt):
    response = await dalle_3.images.generate(
        model=model,
        prompt=prompt,
    )
    imagefileobjs = []
    for image in response.data:
        image_url = image.url
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                content = await response.content.read()
                img_file_obj = io.BytesIO(content)
                imagefileobjs.append(img_file_obj)
    return imagefileobjs
'''

'''
async def tts(zmessage, zmodel):
    voicez = await client.audio.speech.create(
        model="text-moderation-latest",
        voice="text-moderation-latest",
        input="text-moderation-latest"
    )
    with open("zaudio.wav", "wb") as source:
        source.write(voicez["data"])
'''


async def generate_response(instructions, search, history):
    search_results = search if search is not None else "Search feature is disabled"
    messages = [
            {"role": "system", "name": "instructions", "content": instructions},
            *history,
            {"role": "system", "name": "search_results", "content": search_results}
        ]
    response = await client.chat.completions.create(
        model=config['GPT_MODEL'],
        messages=messages,
    )
    message = response.choices[0].message.content
    return message

async def poly_image_gen(session, prompt):
    seed = random.randint(1, 100000)
    image_url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}"
    async with session.get(image_url) as response:
        image_data = await response.read()
        return io.BytesIO(image_data)

async def dall_e_gen(model, prompt, num_images, width, height):
    response = await client.images.generate(
        model=model,
        prompt=prompt,
        n=num_images,
    )
    imagefileobjs = []
    for image in response.data:
        image_url = image.url
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                content = await response.content.read()
                img_file_obj = io.BytesIO(content)
                imagefileobjs.append(img_file_obj)
    return imagefileobjs

async def generate_image_prodia(prompt, model, sampler, seed, neg):
    print("\033[1;32m(Avernus) Creating image for :\033[0m", prompt)
    start_time = time.time()
    async def create_job(prompt, model, sampler, seed, neg):
        if neg is None:
            negative = "painting, extra fingers, missing fingers,  mutated hands, poorly drawn hands, poorly drawn face, deformed, ugly, blurry, bad anatomy, bad proportions, extra limbs, cloned face, skinny, glitchy, double torso, extra arms, extra hands, mangled fingers, missing lips, ugly face, distorted face, extra legs, low quality, medium quality"
            print("")
        else:
            negative = f'painting, extra fingers, missing fingers,  mutated hands, poorly drawn hands, poorly drawn face, deformed, ugly, blurry, bad anatomy, bad proportions, extra limbs, cloned face, skinny, glitchy, double torso, extra arms, extra hands, mangled fingers, missing lips, ugly face, distorted face, extra legs, low quality, medium quality, {neg}'
        url = 'https://api.prodia.com/generate'
        params = {
            'new': 'true',
            'prompt': f'{quote(prompt)}',
            'model': model,
            'negative_prompt': f"{negative}",
            'steps': '25',
            'cfg': '7',
            'seed': f'{seed}',
            'sampler': sampler,
            'upscale': 'True',
            'width': '512',
            'height': '768'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                return data['job']
            
    job_id = await create_job(prompt, model, sampler, seed, neg)
    url = f'https://api.prodia.com/job/{job_id}'
    headers = {
        'authority': 'api.prodia.com',
        'accept': '*/*',
    }

    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(url, headers=headers) as response:
                json = await response.json()
                if json['status'] == 'succeeded':
                    async with session.get(f'https://images.prodia.xyz/{job_id}.png?download=1', headers=headers) as response:
                        content = await response.content.read()
                        img_file_obj = io.BytesIO(content)
                        #heyy = random.randint(1 , 6969696969)
                        duration = time.time() - start_time
                        print(f"\033[1;34m(Avernus) Finished image creation\n\033[0mJob id : {job_id}  Prompt : ", prompt, "in", duration, "seconds.")
                        return img_file_obj

async def gpt4(prompt, image, history, instructions):
    """gpt4 visionary"""
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "name": "instructions", "content": instructions},
            *history,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image}",
                        }
                    },
                ],
            }
        ],
    )

    message = response.choices[0].message.content
    return message



async def llama_vision(prompt, image):
    response = await client.chat.completions.create(
        model="llama-3.2-11b-vision-instruct",
        messages=[
#            *history,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image}",
                        }
                    },
                ],
            }
        ],
    )

    message = response.choices[0].message.content
    return message


print(fr.BLUE, "ai_utils is working properly :)")
