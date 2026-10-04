from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import vision
import psycopg2
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = vision.ImageAnnotatorClient()

conn = psycopg2.connect(
    dbname="manpower",
    user="postgres",
    password="12345",
    host="db",
    port=5432
)
cur = conn.cursor()

JOB_CODES = [
    "EL.ES","EL.CT","EL.CD","EL.JB","EL.PL","EL.CO","EL.MA","EL.SE",
    "EL.LF","EL.LC","EL.ET","EL.CP",
    "IN.CT","IN.CD","IN.JB","IN.PL","IN.CO","IN.FO","IN.MA","IN.IN",
    "TF.TF"
]

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    text = response.full_text_annotation.text

    records = parse(text)

    for r in records:
        cur.execute(
            "INSERT INTO manpower (name, area, job_code, work_date) VALUES (%s, %s, %s, %s)",
            (r["name"], r["area"], r["job"], r["date"])
        )
    conn.commit()

    return {"ok": True, "count": len(records)}

@app.get("/report")
def report(date: str):
    cur.execute("""
        SELECT area, job_code, COUNT(*) 
        FROM manpower 
        WHERE work_date = %s
        GROUP BY area, job_code
    """, (date,))
    return cur.fetchall()

def parse(text):
    lines = text.splitlines()
    out = []
    for l in lines:
        parts = l.split()
        for code in JOB_CODES:
            if code in l:
                out.append({
                    "name": parts[0] + " " + parts[1],
                    "area": parts[2],
                    "job": code,
                    "date": datetime.date.today()
                })
    return out
