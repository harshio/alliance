from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel
from typing import List, Literal, Dict, Any, Optional
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from models import Question as DBQuestion, SessionLocal
from multiplayer import WebSocketManager
import json
import re

app = FastAPI()
manager = WebSocketManager()

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

#from the perspective of 'our' client
@app.websocket('/ws')
#FasAPI attaches IP metadata to websocket object automatically
async def websocket_endpoint(websocket: WebSocket):
    client_id = websocket.query_params.get("client_id")
    setNumber = websocket.query_params.get("setNumber")
    #connects client to server
    #if client_id == "host", then we will connect without needing a key
    #otherwise, we're forced to use player_connect
    if setNumber is None:
        await manager.host_connect(websocket, client_id)
    else:
        print("HI MOM")
        print("Player Number: " + str(setNumber))
        print("Actual Number: " + str(manager.activeSet))
        thing = await manager.player_connect(websocket, client_id, int(setNumber), manager.activeSet)
        if thing == False:
            return
    #the Room component will be something visible to player clients
    #so we need to send a message to all player clients connected to the server
    #whenever each player (except for the host client) joins the server
    for client_identification in manager.connected_clients:
        await manager.send_message_to(client_identification, {
            "type": "playerNames",
            "content": list(manager.connected_clients.keys())
        })
    print(len(manager.connected_clients))
    
    try:
        while True:
            #turns message sent by 'our' client to server via ws.send(JSON.stringify(message)) into json object
            message = await websocket.receive_json()
            if message.get("type") == "sessionID": #this is getting replaced by the sessionID message
                manager.activeSet = message.get("content")
                print(manager.activeSet)
            elif message.get("type") == "startGame":
               for client_identification in manager.connected_clients:
                   await manager.send_message_to(client_identification, {
                        "type": "startGame"
                    })
            elif message.get("type") == "playerDone":
                finished_question = manager.increment()
                if finished_question:
                    for client_identification in manager.connected_clients:
                        await manager.send_message_to(client_identification, {
                                "type": "questionDone"
                            })
    #disconnection case
    except WebSocketDisconnect:
        await manager.disconnect(client_id)