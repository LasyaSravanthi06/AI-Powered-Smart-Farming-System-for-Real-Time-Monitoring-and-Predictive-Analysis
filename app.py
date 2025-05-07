from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
from dotenv import load_dotenv
from data_collection import get_weather_data, get_soil_data, download_satellite_data
from recommendations import get_recommendations

# Initialize the Flask application
app = Flask(_name_)

# Load environment variables from a .env file
load_dotenv()

# Get API key from environment variables
API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Setup CORS for multiple origins
CORS(app, origins=["http://localhost:3000", "http://localhost:3001"])

# Initialize Limiter for rate-limiting
limiter = Limiter(get_remote_address, app=app)  
limiter.init_app(app)

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the SpectraCrop Management API"})

@app.route('/api/weather', methods=['GET'])
@limiter.limit("10 per minute")
def weather():
    location = request.args.get('location', 'India')  # Default to 'India' if no location is provided
    logging.info(f"Received request for weather data for location: {location}")
    try:
        data = get_weather_data(API_KEY, location)
        logging.info("Weather data retrieved successfully.")
        return jsonify(data), 200
    except Exception as e:
        logging.error(f"Error fetching weather data for {location}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recommendations', methods=['POST'])
def recommendations():
    data = request.get_json()
    if not data:
        logging.warning("Request body is empty or not in JSON format.")
        abort(400, "Request body must be JSON.")
required_fields = ['crop_type', 'ndvi_value', 'soil_moisture', 'temperature', 'humidity']
    for field in required_fields:
        if field not in data:
            logging.warning(f"Missing field in request data: {field}")
            abort(400, f"Missing field: {field}")

    try:
        recommendations = get_recommendations(
            data['crop_type'], 
            data['ndvi_value'], 
            data['soil_moisture'], 
            data['temperature'], 
            data['humidity']
        )
        logging.info("Recommendations generated successfully.")
        return jsonify(recommendations), 200
    except Exception as e:
        logging.error(f"Error generating recommendations: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Run the Flask application only if this script is executed directly
if _name_ == '_main_':
    app.run(debug=True)
import pandas as pd
import requests
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
import os


# Add your Sentinel credentials and GeoJSON path
SATELLITE_USER = "sravanthi"
SATELLITE_PASS = "Sravanthi@06"
GEOJSON_PATH = "C:/Users/mvlsravanthi/Documents/spectral-crop-management/your_geojson_file.geojson"  # Update this to your actual geojson file path


# Download satellite data using Sentinel API
def download_satellite_data(username, password, geojson_path):
    # Connect to Sentinel API
    api = SentinelAPI(username, password, 'https://scihub.copernicus.eu/dhus')


    # Read and convert GeoJSON to WKT format (for querying)
    footprint = geojson_to_wkt(read_geojson(geojson_path))


    # Query for products (Sentinel-2, cloud cover percentage < 30)
    products = api.query(footprint,
                         date=('20200101', '20200131'),
                         platformname='Sentinel-2',
cloudcoverpercentage=(0, 30))


    # Download the products found by the query
    for product_id in products.keys():
        api.download(product_id)


# Function to get weather data using OpenWeather API
def get_weather_data(api_key, location):
    # OpenWeatherMap API call to get weather data for India
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}"
    response = requests.get(url)
   
    # Check if the response is valid (status code 200)
    if response.status_code == 200:
        return response.json()
    else:
raise Exception("Error fetching weather data")


# Function to get soil data using SoilGrids API
def get_soil_data(latitude, longitude):
    # Request to SoilGrids API to fetch soil data for given coordinates
    url = f"http://soilgrids.org/api/v1.0/properties?lon={longitude}&lat={latitude}"
    response = requests.get(url)
   
    # Check if the response is valid (status code 200)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Error fetching soil data")


# Function to get historical crop data (FAO)
def get_historical_crop_data():
    # Fetch historical crop data from FAO
    url = 'http://faostat3.fao.org/browse/Q/QC/E'
    df = pd.read_html(url)[0]  # Read the first table from the FAO page
    return df
def get_recommendations(crop_type, ndvi_value, soil_moisture, temperature, humidity):
    recommendations = {}

    if ndvi_value > 0.7:
        recommendations["crop_recommendation"] = (
            f"The NDVI value is high ({ndvi_value}). {crop_type} is growing well! Maintain current irrigation and fertilization practices."
        )
    elif 0.4 <= ndvi_value <= 0.7:
        recommendations["crop_recommendation"] = (
            f"The NDVI value ({ndvi_value}) is moderate. Consider applying organic fertilizers or adjusting irrigation to improve crop health."
        )
    else:
        recommendations["crop_recommendation"] = (
            f"Low NDVI detected ({ndvi_value}). Possible crop stress in {crop_type}. Check for diseases, nutrient deficiencies, or water shortages."
        )

    if soil_moisture < 20:
        if temperature > 30:
            recommendations["irrigation_recommendation"] = (
                "Soil moisture is low and high temperature detected. Increase irrigation frequency to prevent crop wilting."
            )
        else:
            recommendations["irrigation_recommendation"] = (
"Soil moisture is below optimal levels. Consider light irrigation to maintain crop health."
            )
    elif 20 <= soil_moisture <= 50:
        recommendations["irrigation_recommendation"] = (
            "Soil moisture is at an optimal level. Maintain current irrigation schedule."
        )
    else:
        recommendations["irrigation_recommendation"] = (
            "Soil moisture is high. Reduce watering to avoid waterlogging and root diseases."
        )

    if temperature > 30 and humidity > 70:
        recommendations["pesticide_recommendation"] = (
            "High temperature and humidity increase fungal and insect pest risks. Apply a bio-pesticide or Neem-based spray to control infestations."
        )
    elif temperature < 20 and humidity < 50:
        recommendations["pesticide_recommendation"] = (
            "Pest risk is low due to cooler, drier conditions. Reduce pesticide use but continue monitoring for potential outbreaks."
        )
    else:
        recommendations["pesticide_recommendation"] = (
            "Moderate weather conditions detected. Continue regular pest monitoring and apply pesticide only if infestation is noticed."
        )
if ndvi_value < 0.4 and soil_moisture < 20:
        recommendations["additional_advice"] = (
            "Crop health is poor, and soil moisture is low. Consider drought-resistant crop varieties or mulching to retain moisture."
        )
    elif ndvi_value > 0.7 and temperature > 35:
        recommendations["additional_advice"] = (
            "High NDVI and extreme temperature detected. Increase shade nets or micro-irrigation to prevent heat stress in crops."
        )
    elif humidity > 80 and temperature > 28:
        recommendations["additional_advice"] = (
            "High humidity and warm temperature detected. Risk of fungal diseases like powdery mildew is high. Use appropriate fungicides."
        )

    return recommendations
import pandas as pd
import numpy as np

def validate_input_data(data):
    
    required_fields = ['crop_type', 'ndvi_value', 'soil_moisture', 'temperature', 'humidity']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Validate data types
    if not isinstance(data['ndvi_value'], (int, float)):
        raise TypeError("NDVI value must be a number.")
    if not isinstance(data['soil_moisture'], (int, float)):
        raise TypeError("Soil moisture must be a number.")
    if not isinstance(data['temperature'], (int, float)):
        raise TypeError("Temperature must be a number.")
    if not isinstance(data['humidity'], (int, float)):
        raise TypeError("Humidity must be a number.")

def calculate_average(values):
   
    if not values:
        return 0
    return sum(values) / len(values)

def load_crop_data(file_path):
try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        raise FileNotFoundError(f"Error loading data from {file_path}: {e}")

def convert_ndvi_to_health(ndvi):
    
    if ndvi < 0.2:
        return "Poor"
    elif 0.2 <= ndvi < 0.5:
        return "Moderate"
    elif 0.5 <= ndvi < 0.8:
        return "Good"
    else:
        return "Excellent"

def format_recommendations(recommendations):
   
    formatted = []
    for key, value in recommendations.items():
        formatted.append(f"{key.replace('_', ' ').capitalize()}: {value}")
    return "\n".join(formatted)
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Smart Farming System</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { padding: 20px; }
    h2 { text-align: center; margin-bottom: 30px; }
    .result { margin-top: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>AI-Powered Smart Farming System</h2>

    <form id="predictionForm">
      <div class="mb-3">
        <label for="cropType" class="form-label">Crop Type</label>
        <input type="text" class="form-control" id="cropType" required>
      </div>
      <div class="mb-3">
        <label for="ndvi" class="form-label">NDVI Value</label>
<input type="number" step="0.01" class="form-control" id="ndvi" required>
      </div>
      <div class="mb-3">
        <label for="soilMoisture" class="form-label">Soil Moisture (%)</label>
        <input type="number" class="form-control" id="soilMoisture" required>
      </div>
      <div class="mb-3">
        <label for="temperature" class="form-label">Temperature (°C)</label>
        <input type="number" class="form-control" id="temperature" required>
      </div>
      <div class="mb-3">
        <label for="humidity" class="form-label">Humidity (%)</label>
        <input type="number" class="form-control" id="humidity" required>
      </div>
      <button type="submit" class="btn btn-primary">Get Recommendations</button>
    </form>

    <div class="result" id="results" style="display: none;">
      <h4 class="mt-4">Recommendations:</h4>
      <p><strong>Crop Health:</strong> <span id="cropHealth"></span></p>
      <p><strong>Water Usage:</strong> <span id="waterUsage"></span></p>
      <p><strong>Pesticide Recommendation:</strong> <span id="pesticideRec"></span></p>
    </div>
  </div>

  <script>
document.getElementById('predictionForm').addEventListener('submit', async function(e) {
      e.preventDefault();

      const data = {
        crop_type: document.getElementById('cropType').value,
        ndvi_value: parseFloat(document.getElementById('ndvi').value),
        soil_moisture: parseFloat(document.getElementById('soilMoisture').value),
        temperature: parseFloat(document.getElementById('temperature').value),
        humidity: parseFloat(document.getElementById('humidity').value),
      };

      try {
        const response = await fetch('http://127.0.0.1:5000/api/recommendations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });

        const result = await response.json();

        document.getElementById('cropHealth').textContent = result.crop_recommendation || "Not available";
        document.getElementById('waterUsage').textContent = result.water_usage || "Not available";
        document.getElementById('pesticideRec').textContent = result.pesticide_recommendation || "Not available";
        document.getElementById('results').style.display = 'block';
} catch (err) {
        alert('Error fetching recommendations.');
        console.error(err);
      }
    });
  </script>
</body>
</html>
.App {
    text-align: center;
    padding: 2rem;
    font-family: Arial, sans-serif;
  }
  
  input {
    margin: 0.5rem;
    padding: 0.5rem;
  }
  
  button {
    padding: 0.5rem 1rem;
  }
  
  .results {
    margin-top: 2rem;
    background: #f0f8ff;
    padding: 1rem;
    border-radius: 8px;
  }
import { useState, useEffect } from 'react';
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000'
});
// Add to api.js
api.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = Bearer ${token};
    }
    return config;
  });
export function useAPI(endpoint) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get(endpoint);
        setData(response.data);
      } catch (err) {
        setError(err);
} finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [endpoint]);

  return { data, loading, error };
}

export default api;
import React, { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useAPI } from '../../services/api';

mapboxgl.accessToken = 'YOUR_MAPBOX_TOKEN';

export default function FieldHealthMap() {
  const mapContainer = useRef(null);
  const { data: fields } = useAPI('/api/fields');
  
  useEffect(() => {
    if (!fields) return;
    
    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/satellite-v9',
      center: [fields[0].longitude, fields[0].latitude],
      zoom: 14
    });

    fields.forEach(field => {
      new mapboxgl.Marker()
        .setLngLat([field.longitude, field.latitude])
.setPopup(new mapboxgl.Popup().setHTML(`
          <h3>${field.name}</h3>
          <p>Health: ${field.healthScore}%</p>
          <p>Crop: ${field.cropType}</p>
        `))
        .addTo(map);
    });

    return () => map.remove();
  }, [fields]);

  return (
    <div className="card">
      <div className="card-header">
        <h4 className="card-title">Field Health Map</h4>
      </div>
      <div className="card-body">
        <div ref={mapContainer} style={{ height: '500px', width: '100%' }} />
      </div>
    </div>
  );
}
import React from 'react';
import { Grid } from '@material-ui/core';
import FieldHealthMap from '../components/Dashboard/FieldHealthMap';
import WeatherWidget from '../components/Dashboard/WeatherWidget';
import IrrigationRecommendations from '../components/Dashboard/IrrigationRecommendations';

export default function Dashboard() {
  return (
    <div className="content">
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <FieldHealthMap />
        </Grid>
        <Grid item xs={12} md={4}>
          <WeatherWidget />
        </Grid>
        <Grid item xs={12}>
          <IrrigationRecommendations />
        </Grid>
      </Grid>
    </div>
  );
}
import { useState, useEffect } from 'react';
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000'
});
// Add to api.js
api.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = Bearer ${token};
    }
    return config;
  });
export function useAPI(endpoint) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get(endpoint);
        setData(response.data);
      } catch (err) {
        setError(err);
      } finally {
setLoading(false);
      }
    };

    fetchData();
  }, [endpoint]);

  return { data, loading, error };
}

export default api;
