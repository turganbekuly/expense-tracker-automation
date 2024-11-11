# app/models/activation_code.py

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ActivationCode(Base):
    __tablename__ = "activation_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    phone_number = Column(String, nullable=True)
    device = Column(String, nullable=True)
    receipt_number = Column(String, unique=True, nullable=True)  # Ensure unique constraint is set

