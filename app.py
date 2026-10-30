from flask import Flask, request, jsonify

app = Flask(__name__)

data = []


@app.route("/")
def index():
	return """
	  <title>Hello World</title>
	  <h2>Links:</h2>
	  <a href="/data.get">Get data</a>
	"""

@app.route("/data.get")
def get_data():
	return jsonify(data)

@app.route("/data.post", methods=["POST"])
def post_data():
	if not request.is_json: return jsonify({"error": "Invalid JSON"}), 400
	data.append(request.get_json())
	return jsonify({"message": "Data added"})

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8080, debug=False)