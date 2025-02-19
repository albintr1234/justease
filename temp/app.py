from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
CORS(app)

# MongoDB setup
client = MongoClient('mongodb+srv://fiyonasaji:fiyonasaji@cluster0.x1tki.mongodb.net/legal_advisor?retryWrites=true&w=majority')
db = client['Just_Ease']
laws_collection = db['Cases']
users_collection = db['users']
contacts_collection = db['contacts']

# Your News API Key (Keep it private)
NEWS_API_KEY = "8bfe418c7d034af5b101ef0b5263b303"  
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Endpoint to fetch corporate law news
@app.route('/corporate-law-news', methods=['GET'])
def get_corporate_law_news():
    params = {
        'q': 'corporate law OR corporate court OR corporate rules OR corporate governance OR corporate advocate OR corporate compliance',
        'language': 'en',
        'sortBy': 'publishedAt',
        'pageSize': 10,  # Fetching only 10 articles
        'domains': 'thehindu.com, indiatoday.in, livemint.com, barandbench.com, theprint.in, economictimes.indiatimes.com, business-standard.com'
    }
    headers = {"X-Api-Key": NEWS_API_KEY}

    try:
        response = requests.get(NEWS_API_URL, params=params, headers=headers)
        response.raise_for_status()  # Handle HTTP errors
        data = response.json()

        if data.get("articles"):
            articles = [
                {
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "source": article["source"]["name"],
                    "publishedAt": article["publishedAt"]
                }
                for article in data["articles"]
            ]
            return jsonify({"corporate_law_news": articles})

        return jsonify({"error": "No corporate law-related news found"}), 404

    except requests.exceptions.HTTPError as http_err:
        return jsonify({"error": "HTTP error", "details": str(http_err)}), 401
    except requests.exceptions.RequestException as req_err:
        return jsonify({"error": "Failed to fetch news", "details": str(req_err)}), 500

# Signup route
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    if users_collection.find_one({"email": email}):
        return jsonify({"message": "Email already exists"}), 400

    hashed_password = generate_password_hash(password)
    user_data = {"firstname": firstname, "lastname": lastname,"email": email, "password": hashed_password}

    try:
        users_collection.insert_one(user_data)
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500

# Signin route
@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    print("Received data:", data)  # Debugging line

    if not data:
        return jsonify({"message": "No data received or invalid JSON"}), 400
    
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400
    
    user = users_collection.find_one({"email": email})
    userData = {"firstname": firstname, "lastname": lastname, "email": email}

    if user and check_password_hash(user['password'], password):
        return jsonify({"message": "Login successful", "user": userData}), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401
    
# Contact Form Submission
@app.route('/contact', methods=['POST'])
def contact():
    data = request.get_json()
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    email = data.get('email')
    phone = data.get('phone', '')  # Optional field
    message = data.get('message')

    if not first_name or not last_name or not email or not message:
        return jsonify({"message": "All required fields must be filled!"}), 400

    contact_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "message": message
    }

    try:
        contacts_collection.insert_one(contact_data)  # Store data in MongoDB
        return jsonify({"message": "Message sent successfully!"}), 201
    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500

# Fetch all laws with pagination
@app.route('/laws', methods=['GET'])
def get_all_laws():
    page = max(1, int(request.args.get('page', 1)))
    limit = max(1, int(request.args.get('limit', 10)))
    skip = (page - 1) * limit

    total_documents = laws_collection.count_documents({})
    total_pages = max(1, (total_documents + limit - 1) // limit)

    if page > total_pages:
        return jsonify({"error": "Page out of range", "total_pages": total_pages}), 400

    laws = list(laws_collection.find({}, {"_id": 0}).skip(skip).limit(limit))
    return jsonify({
        "laws": laws,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    })

@app.route('/laws/highcourt/<court_name>', methods=['GET'])
def get_laws_by_highcourt(court_name):
    page = max(1, int(request.args.get('page', 1)))
    limit = max(1, int(request.args.get('limit', 5)))
    skip = (page - 1) * limit

    total_documents = laws_collection.count_documents({"court_name": court_name + " High Court"})
    total_pages = max(1, (total_documents + limit - 1) // limit)

    if page > total_pages:
        return jsonify({"error": "Page out of range", "total_pages": total_pages}), 400

    laws = list(laws_collection.find({"court_name": court_name + " High Court"}, {"_id": 0}).skip(skip).limit(limit))

    if not laws:
        return jsonify({"error": f"No case files found for {court_name}"}), 404

    return jsonify({
        "laws": laws,
        "court_name": court_name,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    })
# Google Maps API Integration
GOOGLE_MAPS_API_KEY = "AIzaSyANSebl5DZm3EA6XlkL0w6FUJGzAwwFYeg"

def get_lat_lng_from_location(location):
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(geocode_url)
    if response.status_code != 200:
        return None

    geocode_data = response.json()
    if geocode_data['status'] == 'OK':
        lat = geocode_data['results'][0]['geometry']['location']['lat']
        lng = geocode_data['results'][0]['geometry']['location']['lng']
        return lat, lng
    return None

# Fetching all lawyers by location
@app.route('/find_lawyers_by_location', methods=['GET'])
def find_lawyers_by_location():
    location = request.args.get('location')
    if not location:
        return jsonify({'error': 'Location parameter is required.'}), 400

    lat_lng = get_lat_lng_from_location(location)
    if lat_lng is None:
        return jsonify({'error': 'Could not find coordinates for the location.'}), 400

    lat, lng = lat_lng
    return search_nearby_lawyers(lat, lng)

# Fetching all lawyers based on latitude and longitude
@app.route('/find_lawyers', methods=['GET'])
def find_lawyers():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    if not lat or not lng:
        return jsonify({'error': 'Latitude and Longitude parameters are required.'}), 400
    return search_nearby_lawyers(lat, lng)

def search_nearby_lawyers(lat, lng):
    search_radii = [5000, 10000, 15000, 25000, 50000]
    lawyers = []

    for radius in search_radii:
        places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius={radius}&keyword=corporate%20lawyer&key={GOOGLE_MAPS_API_KEY}"
        response = requests.get(places_url)

        if response.status_code != 200:
            return jsonify({'error': 'Google Places API request failed'}), 500

        places_response = response.json()

        if places_response.get('status') == 'OK':
            for place in places_response.get('results', []):
                place_id = place.get('place_id')
                details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,formatted_address,geometry,website&key={GOOGLE_MAPS_API_KEY}"
                details_response = requests.get(details_url).json()
                details = details_response.get('result', {})

                lawyer_info = {
                    'name': details.get('name', 'Unknown'),
                    'address': details.get('formatted_address', 'Address not available'),
                    'latitude': details['geometry']['location']['lat'],
                    'longitude': details['geometry']['location']['lng'],
                    'website': details.get('website', None)
                }
                lawyers.append(lawyer_info)

        if lawyers:
            break

    return jsonify({'lawyers': lawyers})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)