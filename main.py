from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Request, Form
from typing_extensions import Annotated
import io
import PyPDF2
import random
import psycopg2
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
import sqlite3, os
from dotenv import dotenv_values
import requests
import openai

app = FastAPI()
security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DATABASE_URL = "postgres://history_6l1z_user:3aKwLmkc4P4mghSZBnTPWc8qa9wSiMZl@dpg-civ2765iuiedpv4ukhcg-a.frankfurt-postgres.render.com/history_6l1z"
config = dotenv_values(".env")
openai.api_key = config["OPEN_API_KEY"]
messages2 = []

origins = [
    "https://resume-frontend-five.vercel.app",  # Замените на URL вашего Next.js-сервера
    "https://resume-corrector.onrender.com",  # Замените на URL вашего FastAPI-сервера
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Prof_AnalyzeRequest(BaseModel):
    user_id: str
    data: str

class ImproveRequest(BaseModel):
    user_id: str
    file: str

class QueryRequest(BaseModel):
    user_id: str
    query: str

@app.post("/imp")
def imp_resume_handler(imp_data: ImproveRequest):
    messages = []
    pdf_text = imp_data.file
    messages.append({"role": "user", "content": f'Создай простой шаблон для резюме и заполни его этими данными "{pdf_text}"'})
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages = messages)
    reply = chat.choices[0].message.content
    messages.append({"role":"assistant", "content": reply})
    save_query(QueryRequest(user_id=imp_data.user_id, query=reply))  # Используем query=reply

    # Return the processed data
    return {"message": reply}

@app.post("/prof")
async def profession_resume_handler(
        file: Annotated[UploadFile, File()],
        user_id: Annotated[str, Form()]
):
    # Process the resume data
    # Example processing, you can replace it with your own logic
    messages = []
    pdf_file_bytes = await file.read()
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file_bytes))

    # Инициализируем переменную для хранения текста из всех страниц
    all_text = ""

    # Получаем количество страниц в документе
    num_pages = len(pdf_reader.pages)

    # Читаем содержимое каждой страницы и добавляем в переменную all_text
    for page_num in range(num_pages):
        page = pdf_reader.pages[page_num]
        all_text += page.extract_text()
    message = all_text
    messages.append({"role": "user", "content": "Какие професси подходят под данное резюме: " + message})
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages = messages)
    reply = chat.choices[0].message.content
    messages.append({"role":"assistant", "content": reply})
    save_query(QueryRequest(user_id=user_id, query=reply))  # Используем query=reply
    messages2.append({"role": "user", "content": f'напиши мне из данного текста ТОЛЬКО ЛИШЬ все профессии, должности и работы без нумераций и объяснений, только через проблема {reply}'})
    chat2 = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages = messages2)
    reply2 = chat2.choices[0].message.content
    words = reply2
    word_list = [word.strip() for word in words.split(",")]
    count = len(word_list)
    url = 'https://api.hh.ru/vacancies'
    params = {
        'text': word_list[0],
        'per_page': 5  # Количество вакансий, которые вы хотите получить
    }
    spisok_rabot = []
    response = requests.get(url, params=params)
    data = response.json()
    vacancies = data['items']
    for vacancy in vacancies:
        vacancy_id = vacancy['id']
        vacancy_link = f'https://hh.ru/vacancy/{vacancy_id}'
        spisok_rabot.append(vacancy_link)
    output = '<br>'.join([f'<a href="{link}">{link}</a>' for link in spisok_rabot])
    output2 = ', '.join(spisok_rabot)
    if output2 == '':
        output = 'Ничего не удалось найти'
    return {"message": f'{reply}   Вот ваш список вакансий: <br>{output}'} 

def get_db_conn():
    return psycopg2.connect(DATABASE_URL)

def execute_query(query, args=None, fetchall=False):
    conn = get_db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(query, args)
            if fetchall:
                return cur.fetchall()
    conn.close()

@app.post("/queries")
def save_query(query_request: QueryRequest):
    # Save the query in the PostgreSQL database
    query = "CREATE TABLE IF NOT EXISTS queries (user_id TEXT, reply TEXT)"
    execute_query(query)

    query = "INSERT INTO queries (user_id, reply) VALUES (%s, %s)"
    execute_query(query, (query_request.user_id, query_request.query))

    return {"message": "Query saved successfully"}
    
@app.post("/analyze")
async def analyze_resume_handler(
        file: Annotated[UploadFile, File()],
        user_id: Annotated[str, Form()]
):
    # Process the resume data
    # Example processing, you can replace it with your own logic
    messages = []
    pdf_file_bytes = await file.read()
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file_bytes))

    # Инициализируем переменную для хранения текста из всех страниц
    all_text = ""

    # Получаем количество страниц в документе
    num_pages = len(pdf_reader.pages)

    # Читаем содержимое каждой страницы и добавляем в переменную all_text
    for page_num in range(num_pages):
        page = pdf_reader.pages[page_num]
        all_text += page.extract_text()
    message = all_text
    # message = analyze_data.data
    messages.append({"role": "user", "content": "Сделай объективный анализ данного резюме и напиши мне только лишь качественные советы, что убрать и что добавить: " + message})
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    reply = chat.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    # Сохраняем reply вместо query_request.query
    save_query(QueryRequest(user_id=user_id, query=reply))  # Используем query=reply
    # Return the processed data
    return {"message": reply}
    
@app.get("/queries/{user_id}")
def get_queries(user_id: str):
    conn = get_db_conn()
    with conn:
        # Получаем все запросы для определенного пользователя из базы данных
        query = "SELECT reply FROM queries WHERE user_id = %s ORDER BY user_id DESC"
        cur = conn.cursor()
        cur.execute(query, (user_id,))
        rows = cur.fetchall()
        queries = [row[0] for row in rows]

    return {"queries": queries}

@app.delete("/queries")
def delete_query(query_request: QueryRequest):
    # Delete the specific query from the PostgreSQL database
    query = "DELETE FROM queries WHERE user_id = %s AND reply = %s"
    execute_query(query, (query_request.user_id, query_request.query))

    return {"message": "Query deleted successfully"}