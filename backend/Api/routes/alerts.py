# -*- coding: utf-8 -*-
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os, threading, json
from dotenv import load_dotenv
load_dotenv(
