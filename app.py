import numpy as np
import flask
from flask import Flask, render_template, request

app=Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/result", methods=['POST'])
def result():
    # TODO: add calls to the backend
    return render_template('result.html')

if __name__ == "__main__":
	app.run(debug=True)