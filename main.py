from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze")
def analyze():
    coin = request.args.get("coin", "bitcoin")
    # test dữ liệu fake trước, chưa gọi API
    price = "$12,345"
    return render_template("index.html", coin=coin, price=price)

@app.route("/hello")
def hello():
    return "Hello from Flask - still working!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
