from sqlalchemy import Column, Integer, String, create_engine, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker
import json
import os
from dotenv import load_dotenv 

Base = declarative_base()

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    correctAnswer = Column(ARRAY(Text))
    points = Column(Integer)
    answers = Column(ARRAY(Text))
    setNumber = Column(Integer, index=True)
    questionNumber = Column(Integer)
    imageURL = Column(String)

load_dotenv()

username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

engine = create_engine(f"postgresql+psycopg2://{username}:{password}@localhost:5432/questions")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
