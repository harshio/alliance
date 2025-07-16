from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter, Body
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel
from typing import List, Literal, Dict, Any, Optional
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from models import Question as DBQuestion, SessionLocal
import json
import re

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class QuestionIn(BaseModel): #purpose of this is to define the shape of POST requests from the frontend
    text: str
    correctAnswer: str
    points: int
    answers: List[str]
    setNumber: int
    questionNumber: int

class Config:
    orm_mode = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials = True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#We will define three routes
#The first route will return the highest
#setNumber
#The second route will retrieve the
#specified question
#The third route will post a question into
#the database
#Thus, the first two routes will map to
#a GET request, while the final route will
#map to a POST request

@app.get("/api/max")
def get_max_set_number(db: Session = Depends(get_db)) -> int:
    result = db.query(func.max(DBQuestion.setNumber)).scalar()
    return result if result is not None else -1

@app.get("/api/size/{setNumber}")
def get_size(setNumber: int, db: Session = Depends(get_db)):
    size = db.query(DBQuestion).filter(
        DBQuestion.setNumber == setNumber
    ).count()
    
    return size

@app.get("/api/question/{setNumber}/{questionNumber}")
def get_question(setNumber: int, questionNumber: int, db: Session = Depends(get_db)):
    question = db.query(DBQuestion).filter(
        DBQuestion.setNumber == setNumber,
        DBQuestion.questionNumber == questionNumber
    ).first()

    if not question:
        print(f"❌ No question found for setNumber={setNumber}, questionNumber={questionNumber}")
        raise HTTPException(status_code=404, detail="Question not found")
    
    return {"text": question.text, "correctAnswer": question.correctAnswer, "points": question.points, "answers": question.answers}

@app.post("/api/new")
def save_question(question: QuestionIn, db: Session = Depends(get_db)):
    new_question = DBQuestion(
        text=question.text,
        correctAnswer=question.correctAnswer,
        points=question.points,
        answers=question.answers,
        setNumber=question.setNumber,
        questionNumber=question.questionNumber,
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return new_question

@app.get("/api/setNumbers", response_model = List[int])
def get_unique_set_number(db: Session = Depends(get_db)):
    results = db.query(distinct(DBQuestion.setNumber)).all()
    return [row[0] for row in results]