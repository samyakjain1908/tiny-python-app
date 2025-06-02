from flask import Flask, jsonify, render_template, request
import requests
import os
from dotenv import load_dotenv

# Define API URL.
TRIVIA_URL = 'https://api.api-ninjas.com/v1/quotes'

# Load environment variables
load_dotenv()


app = Flask(__name__)

# Service 1: Home page
@app.route('/')
def home():
    return render_template('index.html')

# Service 2: Weather Service
@app.route('/weather', methods=['GET'])
def get_weather():
    city = request.args.get('city')
    state_code = request.args.get('state_code', '')
    country_code = request.args.get('country_code', '')
    api_key = os.getenv('OPENWEATHER_API_KEY')
    
    if not api_key:
        return jsonify({
            'error': 'Weather API key not configured',
            'status': 'error'
        }), 500
    
    try:
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
            return jsonify({
                'city': location_name,
                'temperature': weather_data['main']['temp'],
                'description': weather_data['weather'][0]['description'],
                'humidity': weather_data['main']['humidity'],
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Weather data not available',
                'status': 'error'
            }), weather_response.status_code
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

# Service 3: Quote Service
@app.route('/quote')
def get_quote():
    try:
        # Using API Ninjas Quotes API
        response = requests.get(
            TRIVIA_URL,
            headers={'X-Api-Key': '5Rj8e5dMU+Sa6zqzQzEWNg==SKafWBb5psM9xbwQ'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                quote_data = data[0]  # The API returns an array with a single quote object
                return jsonify({
                    'quote': quote_data.get('quote', ''),
                    'author': quote_data.get('author', 'Unknown'),
                    'category': quote_data.get('category', ''),
                    'status': 'success'
                })
            else:
                return jsonify({
                    'error': 'No quotes found',
                    'status': 'error'
                }), 404
        else:
            return jsonify({
                'error': f'Failed to fetch quote: {response.text}',
                'status': 'error',
                'status_code': response.status_code
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True)
