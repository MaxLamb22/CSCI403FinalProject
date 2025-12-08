import getpass
import pg8000
import os
from flask import Flask, render_template, request, flash, redirect, url_for
from contextlib import contextmanager
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

load_dotenv()

# Database credentials - in production, use environment variables
DB_CREDENTIALS = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'host': os.getenv('DB_HOST')
}

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = pg8000.connect(**DB_CREDENTIALS)
        yield conn
    except pg8000.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

@app.route("/")
def home():
    """Home page - display all games"""
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SET search_path TO maxwell_lamb")
            cursor.execute("SELECT name, release_date, price FROM steam ORDER BY name")
            games = cursor.fetchall()
        
        return render_template("index.html", games=games)
    except pg8000.Error as e:
        flash(f"Database error: {str(e)}", "error")
        return render_template("index.html", games=[])
    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "error")
        return render_template("index.html", games=[])

@app.route("/search", methods=['GET', 'POST'])
def search():
    """Search for a specific game"""
    if request.method == 'POST':
        game_name = request.form.get('game_name', '').strip()
        
        if not game_name:
            flash("Please enter the name of a game", "warning")
            return render_template("search.html", result=None)
        
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                query = "SELECT name, release_date, price FROM steam WHERE name = %s"
                cursor.execute(query, [game_name])
                result = cursor.fetchone()
            
            if result:
                return render_template("search.html", result={
                    'name': result[0],
                    'release_date': result[1],
                    'reviews': result[2]
                })
            else:
                flash(f"No game found with name: {game_name}", "info")
                return render_template("search.html", result=None)
        
        except pg8000.Error as e:
            flash(f"Database error: {str(e)}", "error")
            return render_template("search.html", result=None)
    
    return render_template("search.html", result=None)

@app.route("/result", methods=['POST'])
def result():
    """Process form data and display results"""
    try:
        # Get form data
        action = request.form.get('action')
        
        with get_db_connection() as db:
            cursor = db.cursor()
            
            if action == 'count':
                cursor.execute("SELECT COUNT(*) FROM steam")
                count = cursor.fetchone()[0]
                return render_template('result.html', 
                                     message=f"Total games in database: {count}")
            
            elif action == 'oldest':
                cursor.execute("SELECT name, release_date, price FROM steam ORDER BY release_date DESC LIMIT 1")
                result = cursor.fetchone()
                if result:
                    return render_template('result.html',
                                         message=f"Newest game: {result[0]} ({result[1]}, {result[2]})")
                else:
                    return render_template('result.html', message="No games found")
            
            else:
                return render_template('result.html', message="Unknown action")
    
    except pg8000.Error as e:
        flash(f"Database error: {str(e)}", "error")
        return redirect(url_for('home'))

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)