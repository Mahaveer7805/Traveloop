from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Trip, Stop, Activity, ChecklistItem, Note, Booking, Expense, Review
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackathon_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///traveloop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Initialize database
with app.app_context():
    db.create_all()

# ---- Auth Routes ----
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check your email and password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', 'error')
            return redirect(url_for('signup'))
            
        new_user = User(email=email, name=name, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user, remember=True)
        return redirect(url_for('dashboard'))
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---- Core App Routes ----
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    trips = Trip.query.filter_by(user_id=current_user.id).order_by(Trip.start_date).limit(3).all()
    # Dummy recommended destinations
    recommendations = [
        {"name": "Kyoto, Japan", "image": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?q=80&w=600&auto=format&fit=crop"},
        {"name": "Paris, France", "image": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?q=80&w=600&auto=format&fit=crop"},
        {"name": "Bali, Indonesia", "image": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?q=80&w=600&auto=format&fit=crop"}
    ]
    return render_template('dashboard.html', trips=trips, recommendations=recommendations)

@app.route('/trips')
@login_required
def my_trips():
    trips = Trip.query.filter_by(user_id=current_user.id).order_by(Trip.start_date).all()
    return render_template('my_trips.html', trips=trips)

@app.route('/trips/create', methods=['GET', 'POST'])
@login_required
def create_trip():
    if request.method == 'POST':
        name = request.form.get('name')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        description = request.form.get('description')
        
        new_trip = Trip(
            user_id=current_user.id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            description=description
        )
        db.session.add(new_trip)
        db.session.commit()
        return redirect(url_for('itinerary_builder', trip_id=new_trip.id))
        
    return render_template('create_trip.html')

@app.route('/trip/<int:trip_id>/builder', methods=['GET', 'POST'])
@login_required
def itinerary_builder(trip_id):
    trip = db.session.get(Trip, trip_id)
    if trip.user_id != current_user.id:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        city = request.form.get('city')
        start = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        order = request.form.get('order', 0)
        
        stop = Stop(trip_id=trip.id, city=city, start_date=start, end_date=end, order=order)
        db.session.add(stop)
        db.session.commit()
        return redirect(url_for('itinerary_builder', trip_id=trip.id))
        
    return render_template('itinerary_builder.html', trip=trip)

@app.route('/trip/<int:trip_id>')
@login_required
def itinerary_view(trip_id):
    trip = db.session.get(Trip, trip_id)
    if trip.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    return render_template('itinerary_view.html', trip=trip)

@app.route('/search/city')
@login_required
def city_search():
    query = request.args.get('q', '')
    # Dummy data for hackathon
    cities = []
    if query:
        cities = [
            {"id": 1, "name": "London", "country": "UK", "cost_index": "$$$", "popularity": "High"},
            {"id": 2, "name": "Tokyo", "country": "Japan", "cost_index": "$$$", "popularity": "Very High"},
            {"id": 3, "name": "Bangkok", "country": "Thailand", "cost_index": "$", "popularity": "High"}
        ]
    return render_template('city_search.html', cities=cities, query=query)

@app.route('/trip/<int:trip_id>/stop/<int:stop_id>/activities', methods=['GET', 'POST'])
@login_required
def activity_search(trip_id, stop_id):
    trip = db.session.get(Trip, trip_id)
    stop = db.session.get(Stop, stop_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        cost = float(request.form.get('cost', 0))
        duration = int(request.form.get('duration', 60))
        act_type = request.form.get('type')
        desc = request.form.get('description')
        
        act = Activity(stop_id=stop.id, name=name, cost=cost, duration=duration, type=act_type, description=desc)
        db.session.add(act)
        db.session.commit()
        return redirect(url_for('activity_search', trip_id=trip.id, stop_id=stop.id))
        
    return render_template('activity_search.html', trip=trip, stop=stop)

@app.route('/trip/<int:trip_id>/budget')
@login_required
def budget(trip_id):
    trip = db.session.get(Trip, trip_id)
    # Calculate costs
    total_cost = 0
    breakdown = {"Transport": 0, "Stay": 0, "Activity": 0, "Meal": 0}
    for stop in trip.stops:
        for act in stop.activities:
            total_cost += act.cost
            if act.type in breakdown:
                breakdown[act.type] += act.cost
            else:
                breakdown["Activity"] += act.cost
                
    return render_template('budget.html', trip=trip, total_cost=total_cost, breakdown=breakdown)

@app.route('/trip/<int:trip_id>/checklist', methods=['GET', 'POST'])
@login_required
def checklist(trip_id):
    trip = db.session.get(Trip, trip_id)
    
    if request.method == 'POST':
        if 'add' in request.form:
            item_name = request.form.get('item_name')
            category = request.form.get('category', 'General')
            new_item = ChecklistItem(trip_id=trip.id, item_name=item_name, category=category)
            db.session.add(new_item)
            db.session.commit()
        elif 'toggle' in request.form:
            item_id = request.form.get('item_id')
            item = db.session.get(ChecklistItem, item_id)
            if item:
                item.is_packed = not item.is_packed
                db.session.commit()
        return redirect(url_for('checklist', trip_id=trip.id))
        
    return render_template('checklist.html', trip=trip)

@app.route('/trip/<int:trip_id>/shared')
def shared_itinerary(trip_id):
    trip = db.session.get(Trip, trip_id)
    if not trip.is_public:
        return "This trip is not public", 403
    return render_template('shared_itinerary.html', trip=trip)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)

@app.route('/trip/<int:trip_id>/notes', methods=['GET', 'POST'])
@login_required
def notes(trip_id):
    trip = db.session.get(Trip, trip_id)
    if request.method == 'POST':
        content = request.form.get('content')
        note = Note(trip_id=trip.id, content=content)
        db.session.add(note)
        db.session.commit()
        return redirect(url_for('notes', trip_id=trip.id))
        
    return render_template('notes.html', trip=trip)

@app.route('/trip/<int:trip_id>/bookings', methods=['GET', 'POST'])
@login_required
def bookings(trip_id):
    trip = db.session.get(Trip, trip_id)
    if request.method == 'POST':
        b_type = request.form.get('booking_type')
        provider = request.form.get('provider')
        conf = request.form.get('confirmation_number')
        date_str = request.form.get('date')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        
        booking = Booking(trip_id=trip.id, booking_type=b_type, provider=provider, confirmation_number=conf, date=date_obj)
        db.session.add(booking)
        db.session.commit()
        return redirect(url_for('bookings', trip_id=trip.id))
    return render_template('bookings.html', trip=trip)

@app.route('/trip/<int:trip_id>/funds', methods=['GET', 'POST'])
@login_required
def funds(trip_id):
    trip = db.session.get(Trip, trip_id)
    if request.method == 'POST':
        title = request.form.get('title')
        amount = float(request.form.get('amount', 0))
        paid_by = request.form.get('paid_by')
        split_with = request.form.get('split_with')
        
        expense = Expense(trip_id=trip.id, title=title, amount=amount, paid_by=paid_by, split_with=split_with)
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('funds', trip_id=trip.id))
    return render_template('funds.html', trip=trip)

@app.route('/trip/<int:trip_id>/reviews', methods=['GET', 'POST'])
@login_required
def reviews(trip_id):
    trip = db.session.get(Trip, trip_id)
    if request.method == 'POST':
        title = request.form.get('title')
        rating = int(request.form.get('rating', 5))
        content = request.form.get('content')
        
        review = Review(trip_id=trip.id, title=title, rating=rating, content=content)
        db.session.add(review)
        db.session.commit()
        return redirect(url_for('reviews', trip_id=trip.id))
    return render_template('reviews.html', trip=trip)

@app.route('/admin')
@login_required
def admin():
    # In a real app, check if current_user is admin
    users = User.query.order_by(User.created_at.desc()).all()
    trips = Trip.query.all()
    stops = Stop.query.count()
    return render_template('admin.html', users=users, trips=trips, stops=stops)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
