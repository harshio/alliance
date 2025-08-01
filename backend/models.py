from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import TypeDecorator, Text
import json

Base = declarative_base()

class StringList(TypeDecorator):
    impl = Text
    
    def process_bind_param(self, value, dialect):
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        return json.loads(value)

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    correctAnswer = Column(StringList)
    points = Column(Integer)
    answers = Column(StringList)
    setNumber = Column(Integer, index=True)
    questionNumber = Column(Integer)

engine = create_engine("sqlite:///./questions.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
