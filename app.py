from flask import Flask, jsonify, render_template, request
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import base64
from prometheus_client import generate_latest, Counter, Histogram
import time

# Load environment variables from .env file
load_dotenv()


app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('flask_app_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('flask_app_request_latency_seconds', 'Request latency', ['endpoint'])
REQUEST_FAILURES = Counter('flask_app_request_failures_total', 'Total failed HTTP requests', ['endpoint'])

# Expose /metrics endpoint for Prometheus
@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

# Service 1: Home page
@app.route('/')
def home():
    start_time = time.time()
    try:
        response = render_template('index.html')
        status = 200
        return response
    except Exception as e:
        REQUEST_FAILURES.labels(endpoint='/').inc()
        status = 500
        raise e
    finally:
        REQUEST_COUNT.labels(method='GET', endpoint='/', http_status=status).inc()
        REQUEST_LATENCY.labels(endpoint='/').observe(time.time() - start_time)


# Service 2: Weather Service
@app.route('/weather', methods=['GET'])
def get_weather():
    start_time = time.time()
    status = 200
    try:
        city = request.args.get('city')
        state_code = request.args.get('state_code', '')
        country_code = request.args.get('country_code', '')
        api_key = os.getenv('OPENWEATHER_API_KEY')
        
        if not api_key:
            status = 500
            REQUEST_FAILURES.labels(endpoint='/weather').inc()
            return jsonify({
                'error': 'Weather API key not configured',
                'status': 'error'
            }), 500
        
        # First, get coordinates using geocoding API
        geo_url = f'http://api.openweathermap.org/geo/1.0/direct?q={city}'
        if state_code:
            geo_url += f',{state_code}'
        if country_code:
            geo_url += f',{country_code}'
        geo_url += f'&limit=1&appid={api_key}'
        geo_response = requests.get(geo_url)
        geo_data = geo_response.json()
        if not geo_data or not isinstance(geo_data, list) or not geo_data[0]:
            status = 404
            REQUEST_FAILURES.labels(endpoint='/weather').inc()
            return jsonify({
                'error': 'Location not found',
                'status': 'error'
            }), 404
            
        # Extract coordinates
        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']
        location_name = geo_data[0].get('name', city)
        
        # Now get weather data using coordinates
        weather_url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric'
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()
        
        if weather_response.status_code == 200:
            result = jsonify({
                'city': location_name,
                'temperature': weather_data['main']['temp'],
                'description': weather_data['weather'][0]['description'],
                'humidity': weather_data['main']['humidity'],
                'status': 'success'
            })
            status = 200
            return result
        else:
            status = weather_response.status_code
            REQUEST_FAILURES.labels(endpoint='/weather').inc()
            return jsonify({
                'error': 'Weather data not available',
                'status': 'error'
            }), weather_response.status_code
        
    except Exception as e:
        status = 500
        REQUEST_FAILURES.labels(endpoint='/weather').inc()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
    finally:
        REQUEST_COUNT.labels(method='GET', endpoint='/weather', http_status=status).inc()
        REQUEST_LATENCY.labels(endpoint='/weather').observe(time.time() - start_time)


# Service 3: Quote Service
@app.route('/quote')
def get_quote():
    start_time = time.time()
    status = 200
    try:
        api_key_base64 = os.getenv('API_NINJAS_QUOTES_KEY_BASE64')
        if not api_key_base64:
            status = 500
            REQUEST_FAILURES.labels(endpoint='/quote').inc()
            return jsonify({'error': 'Base64 encoded API key not found'}), 500
        try:
            api_key = base64.b64decode(api_key_base64).decode('utf-8')
        except Exception as e:
            status = 500
            REQUEST_FAILURES.labels(endpoint='/quote').inc()
            return jsonify({'error': f'Error decoding API key: {str(e)}'}), 500
        
        api_url = 'https://api.api-ninjas.com/v1/quotes'
        response = requests.get(api_url, headers={'X-Api-Key': api_key})
        
        if response.status_code == requests.codes.ok:
            result = jsonify({
                'quote': response.json()[0].get('quote', ''),
                'author': response.json()[0].get('author', 'Unknown'),
                'status': 'success'
            })
            status = 200
            return result
        else:
            status = response.status_code
            REQUEST_FAILURES.labels(endpoint='/quote').inc()
            return jsonify({
                'error': response.text,
                'status': 'error',
                'status_code': response.status_code
            }), response.status_code
        
    except Exception as e:
        status = 500
        REQUEST_FAILURES.labels(endpoint='/quote').inc()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
    finally:
        REQUEST_COUNT.labels(method='GET', endpoint='/quote', http_status=status).inc()
        REQUEST_LATENCY.labels(endpoint='/quote').observe(time.time() - start_time)


import threading
import logging

def background_service():
    while True:
        logging.info('Background service heartbeat: still running.')
        # Increment a Prometheus metric for background ticks
        if 'BACKGROUND_TICK' not in globals():
            global BACKGROUND_TICK
            BACKGROUND_TICK = Counter('background_service_ticks_total', 'Total ticks of the background service')
        BACKGROUND_TICK.inc()
        time.sleep(10)

if __name__ == '__main__':
    # Set up logging to stdout for Docker/Grafana visibility
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    # Start background service thread
    threading.Thread(target=background_service, daemon=True).start()
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True)
