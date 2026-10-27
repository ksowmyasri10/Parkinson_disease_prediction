from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import numpy as np
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'H3ll0_P4rk1ns0n_2026_V2'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

# --- DATABASE & LOGIN SETUP ---
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- MODEL LOADING ---
# Ensure 'rf_clf.pkl' is in the same folder as app.py
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'rf_clf.pkl')
model = None
try:
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    print("✅ SUCCESS: Model loaded successfully.")
except Exception as e:
    print(f"❌ ERROR: Failed to load model: {e}")

# --- AUTH ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password. Please try again.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists!')
            return redirect(url_for('signup'))
        new_user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- NAVIGATION ROUTES (Fixed BuildErrors) ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about-us')
def about():
    return render_template('about-us.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/visualisations')
@login_required
def visualisations():
    return render_template('visualisations.html')

@app.route('/counter')
def counter():
    return render_template('counter.html')

@app.route('/parkinson')
@login_required
def parkinson():
    return render_template('parkinson.html')

# --- PREDICTION LOGIC ---

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if model is None:
        return render_template('result.html', result="Error", risk_level="Model not found on server.")

    feature_names = [
        'MDVPFo', 'MDVPFhi', 'MDVPFlo', 'JitterPerc', 'JitterAbs', 'MDVPRAP',
        'MDVPPPQ', 'JitterDDP', 'MDVPShimmer', 'ShimmerAPQ3', 'ShimmerAPQ5', 
        'MDVPApQ', 'ShimmerAPQ', 'ShimmerDDA', 'NHR', 'HNR', 'RPDE', 'DFA', 
        'spread1', 'spread2', 'D2', 'PPE'
    ]

    try:
        input_data = []
        for name in feature_names:
            val = request.form.get(name)
            if val is None:
                return render_template('result.html', result="Error", risk_level=f"Missing input field: {name}")
            input_data.append(float(val))

        final_features = np.array([input_data])
        prediction = model.predict(final_features)[0]
        
        # Risk probability
        risk_prob = model.predict_proba(final_features)[0][1] * 100
        risk_percentage = f"{risk_prob:.2f}"

        if prediction == 1:
            result = "Positive"
            risk_level = "High" if risk_prob > 75 else "Medium" if risk_prob > 50 else "Low"
        else:
            result = "Negative"
            risk_level = "Low"

        return render_template('result.html', result=result, risk_percentage=risk_percentage, risk_level=risk_level)

    except ValueError:
        return render_template('result.html', result="Error", risk_level="Numerical input error. Check your values.")
    except Exception as e:
        return render_template('result.html', result="Error", risk_level=str(e))

if __name__ == '__main__':
    app.run(debug=True)