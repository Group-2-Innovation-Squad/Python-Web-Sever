from flask import Flask, request, jsonify
from openai import OpenAI
import requests

from dotenv import load_dotenv
import os
 
load_dotenv()

app = Flask(__name__)

PLANT_API_KEY = os.getenv("PLANT_API_KEY") # 500 a day
API_ENDPOINT = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANT_API_KEY}"
OPEN_API_KEY= os.getenv("OPEN_AI_KEY")

client = OpenAI(api_key=OPEN_API_KEY)

# this is how the OPEN AI model response will be structured
structure = """{
  "plant": {
    "common_name": "string",
    "scientific_name": "string",
    "watering": {
      "frequency": "string",
      "tips": ["string"]
    },
    "care_tips": ["string"],
    "humidity_level": {
      "preferred": "string",
      "tolerance": "string"
    },
    "light_requirements": {
      "type": "string",
      "ideal_conditions": "string"
    },
    "potting": {
      "container_type": "string",
      "drainage": "string"
    },
    "repotting": {
      "frequency": "string",
      "when_to_repote": "string"
    },
    "pests_diseases": {
      "common_pests": ["string"],
      "prevention_tips": ["string"]
    }
  }
}"""


@app.route('/identify', methods=['POST'])
def identify():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image = request.files['image']
    if image.filename == '':
        return jsonify({"error": "Empty filename provided"}), 400

    files = {
        'images': (image.filename, image.stream, image.content_type)
    }
    data = {'organs': []}

    try:
        response = requests.post(API_ENDPOINT, files=files, data=data)
        response.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": "Error calling PlantNet API", "details": str(e)}), 500

    json_result = response.json()

    # Ensure that we got valid results
    if "results" not in json_result or len(json_result["results"]) == 0:
        return jsonify({"error": "No results returned by PlantNet API"}), 500

    species_info = json_result["results"][0]["species"]
    family = species_info["family"]["scientificName"]
    common_name = species_info["commonNames"][0] if species_info.get("commonNames") else None
    scientific_name = species_info["scientificName"]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Give me data in JSON format (only output json as a result, nothing else) for the plant type: " + common_name + " using this json structure: " + structure}]
    )

    return jsonify(response.choices[0].message.content)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)

