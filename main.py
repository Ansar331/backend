from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
import sqlite3, os
from dotenv import dotenv_values
import openai

app = FastAPI()
security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
config = dotenv_values(".env")
openai.api_key = config["OPEN_API_KEY"]
messages = []

origins = [
    "http://localhost:3000",  # Замените на URL вашего Next.js-сервера
    "http://localhost:8000",  # Замените на URL вашего FastAPI-сервера
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
    data: str

class QueryRequest(BaseModel):
    user_id: str
    query: str

@app.post("/imp")
def imp_resume_handler(imp_data: ImproveRequest):
    pdf_text = imp_data.file
    message = imp_data.data  
    messages.append({"role": "user", "content": f'Перепиши и улучши это резюме "{pdf_text}" под должность {message}'})
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages = messages)
    reply = chat.choices[0].message.content
    messages.append({"role":"assistant", "content": reply})
    save_query(QueryRequest(user_id=imp_data.user_id, query=reply))  # Используем query=reply

    # Return the processed data
    return {"message": reply}

@app.post("/prof")
def profession_resume_handler(profession_data: Prof_AnalyzeRequest):
    # Process the resume data
    # Example processing, you can replace it with your own logic
    message = profession_data.data  
    messages.append({"role": "user", "content": "Какие професси подходят под данное резюме: " + message})
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages = messages)
    reply = chat.choices[0].message.content
    messages.append({"role":"assistant", "content": reply})
    save_query(QueryRequest(user_id=profession_data.user_id, query=reply))  # Используем query=reply
    return {"message": reply}

@app.post("/queries")
def save_query(query_request: QueryRequest):
    # Сохраняем запрос в базе данных
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS queries (user_id TEXT, reply TEXT)")  # Изменяем схему таблицы, чтобы использовать столбец 'reply'
    c.execute("INSERT INTO queries (user_id, reply) VALUES (?, ?)", (query_request.user_id, query_request.query))  # Используем query_request.query
    conn.commit()
    conn.close()
    return {"message": "Query saved successfully"}

@app.post("/analyze")
def analyze_resume_handler(analyze_data: Prof_AnalyzeRequest):
    # Process the resume data
    # Example processing, you can replace it with your own logic
    message = analyze_data.data
    messages.append({"role": "user", "content": "Сделай объективный анализ данного резюме: " + message})
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    reply = chat.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    # Сохраняем reply вместо query_request.query
    save_query(QueryRequest(user_id=analyze_data.user_id, query=reply))  # Используем query=reply
    # Return the processed data
    return {"message": reply}

@app.get("/queries/{user_id}")
def get_queries(user_id: str):
    # Получаем все запросы для определенного пользователя из базы данных
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute("SELECT reply FROM queries WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    queries = [row[0] for row in rows]
    conn.close()
    return {"queries": queries}
