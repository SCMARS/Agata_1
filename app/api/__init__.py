# API endpoints package

from flask import Flask
from app.api.main import create_app

__all__ = ['create_app']

def get_app():

    return create_app() 