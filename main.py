# main.py
import os
from flask import Flask, render_template

app = Flask(__name__)

@app.get("/")
def home():
    return "<h1>STEGIE Hub Têxtil no ar ✅</h1>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
