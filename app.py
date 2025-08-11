from flask import Flask, request, render_template_string, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
import os
import tempfile
import requests
import io
import base64
from PyPDF2 import PdfMerger
import uuid
import time

app = Flask(__name__)
app.secret_key = 'zpl-generator-manus-2025'
CORS(app)
