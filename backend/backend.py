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
    correctAnswer: List[str]
    points: int
    answers: List[str]
    setNumber: int
    questionNumber: int
    imageURL: str

class QuestionOut(BaseModel): #purpose of this is to define the shape of POST requests from the frontend
    text: str
    correctAnswer: List[str]
    points: int
    answers: List[str]
    setNumber: int
    questionNumber: int
    imageURL: str

    model_config = {"from_attributes": True}

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

@app.delete("/api/old/{setNumber}")
def delete_set(setNumber: int, db: Session = Depends(get_db)):
    db.query(DBQuestion).filter(
        DBQuestion.setNumber == setNumber
    ).delete(synchronize_session=False)

    db.commit()
    return{"message": f"Deleted set {setNumber}"}

@app.get("/api/question/{setNumber}/{questionNumber}")
def get_question(setNumber: int, questionNumber: int, db: Session = Depends(get_db)):
    question = db.query(DBQuestion).filter(
        DBQuestion.setNumber == setNumber,
        DBQuestion.questionNumber == questionNumber
    ).first()

    if not question:
        print(f"❌ No question found for setNumber={setNumber}, questionNumber={questionNumber}")
        raise HTTPException(status_code=404, detail="Question not found")
    
    return {"text": question.text, "correctAnswer": question.correctAnswer, "points": question.points, "answers": question.answers, "imageURL": question.imageURL}

@app.post("/api/new", response_model=QuestionOut)
def save_question(question: QuestionIn, db: Session = Depends(get_db)):
    new_question = DBQuestion(
        text=question.text,
        correctAnswer=question.correctAnswer,
        points=question.points,
        answers=question.answers,
        setNumber=question.setNumber,
        questionNumber=question.questionNumber,
        imageURL=question.imageURL
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    print(type(new_question.answers))
    print(type(new_question.correctAnswer))
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
        print("A player is connecting")
        print("Player Number: " + str(setNumber))
        print("Actual Number: " + str(manager.activeSetID))
        thing = await manager.player_connect(websocket, client_id, int(setNumber), manager.activeSetID)
        if thing == False:
            return
        await manager.send_message_to(client_id, {
            "type": "activeSet",
            "content": manager.activeSetNumber
        })
        print(f"The set number is {manager.activeSetNumber}")
    #the Room component will be something visible to player clients
    #so we need to send a message to all player clients connected to the server
    #whenever each player (except for the host client) joins the server
    for client_identification in manager.connected_clients:
        await manager.send_message_to(client_identification, {
            "type": "playerNames",
            "content": list(manager.connected_clients.keys())
        })
    
    try:
        while True:
            #turns message sent by 'our' client to server via ws.send(JSON.stringify(message)) into json object
            message = await websocket.receive_json()
            if message.get("type") == "sessionID": #this is getting replaced by the sessionID message
                manager.activeSetID = message.get("content").get("id")
                manager.activeSetNumber = message.get("content").get("set")
                print(manager.activeSetID)
            elif message.get("type") == "startGame":
               for client_identification in manager.connected_clients:
                   await manager.send_message_to(client_identification, {
                        "type": "startGame"
                    })
            elif message.get("type") == "playerDone":
                finished_question = manager.increment()
                print(finished_question)
                if finished_question:
                    for client_identification in manager.connected_clients:
                        await manager.send_message_to(client_identification, {
                                "type": "questionDone"
                            })
                    await manager.host_send_message("host", {
                                "type": "questionDone"
                            })
            elif message.get("type") == "timeOut":
                manager.playersDone = 0
                for client_identification in manager.connected_clients:
                        await manager.send_message_to(client_identification, {
                                "type": "questionDone"
                            })
            elif message.get("type") == "setSize":
                await manager.host_send_message("host", {
                                "type": "setSize",
                                "content": message.get("content")
                            })
                print("THIS SET HAS THIS MANY QUESTIONS:")
                print(message.get("content"))
    #disconnection case
    except WebSocketDisconnect:
        await manager.disconnect(client_id)