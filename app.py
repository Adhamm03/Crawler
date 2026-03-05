from flask import Flask, request, jsonify, send_from_directory
from fetchSite import get_company_info
import os

app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/company", methods=["POST"])
def company():
    body = request.get_json()
    company_name = body.get("company_name", "").strip()
    country = body.get("country", "").strip()
    if not company_name or not country:
        return jsonify({"error": "company_name and country are required"}), 400
    result = get_company_info(company_name, country)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
