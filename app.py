from flask import Flask, render_template, request
from scraper import scrape_google_places

app = Flask(__name__)

category_type = [
    "Saree shop", "Indian cloth wears", "Lehenga shop", "Shalwar suit shop",
    "Indian Ethnic Wears", "Indian Wears Dress", "Indian shop for Western Wears"
]

countries = [
    "UK", "USA", "AUSTRALIA", "NEW ZEALAND", "France", "Germany", "Sri Lanka", "Nepal",
    "Mauritius", "Fiji Island", "Reunion Island", "Singapore", "Malaysia", "South Africa",
    "UAE", "Canada", "Oman", "Bahrain", "Qatar", "Kuwait", "Switzerland"
]

@app.route("/", methods=["GET", "POST"])
def index():
    result = []
    search_term = ""
    if request.method == "POST":
        category = request.form.get("category")
        country = request.form.get("country")
        search_term = f"{category} in {country}"
        result = scrape_google_places(search_term)
    return render_template("index.html", categories=category_type, countries=countries, result=result, search=search_term)

if __name__ == "__main__":
    app.run(debug=True)
