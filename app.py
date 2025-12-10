import getpass
import pg8000 # type: ignore
import os
import json
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
            cursor.execute("SELECT name, release_date, price FROM steam ORDER BY appid")
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
            return render_template("search.html", result=None, game_name=None)
        
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("SET search_path TO maxwell_lamb")
                query = "SELECT name, release_date, price FROM steam WHERE name ILIKE %s ORDER BY appid"
                search_pattern = f"%{game_name}%"
                cursor.execute(query, [search_pattern])
                results = cursor.fetchall()
            
            if results:
                return render_template("search.html", results=results, game_name=game_name)
            else:
                flash(f"No game found with name: {game_name}", "info")
                return render_template("search.html", results=None, game_name=game_name)
        
        except pg8000.Error as e:
            flash(f"Database error: {str(e)}", "error")
            return render_template("search.html", results=None, game_name=None)
    
    return render_template("search.html", results=None, game_name=None)

@app.route("/result", methods=['POST'])
def result():
    """Process form data and display results"""
    try:
        # Get form data
        action = request.form.get('action')
        game_name = request.form.get("game_name")
        
        if game_name:
            search_pattern = f"%{game_name}%"
            searched = """
                WITH searched AS (
                            SELECT name, release_date, price, positive_ratings, negative_ratings
                            FROM steam 
                            WHERE name ILIKE %s
                        )"""
        
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SET search_path TO maxwell_lamb")

            if action == 'Count':
                if game_name:
                    cursor.execute(searched + "SELECT COUNT(*) FROM searched", [search_pattern])
                else:
                    cursor.execute("SELECT COUNT(*) FROM steam")
                count = cursor.fetchone()[0]
                return render_template('result.html', 
                                     message=f"Total games in database: {count}")
            
            elif action == 'By Newest':
                if game_name:
                    cursor.execute(searched + "SELECT * FROM searched ORDER BY release_date DESC", [search_pattern])
                else:
                    cursor.execute("SELECT name, release_date, price FROM steam ORDER BY release_date DESC")
                result = cursor.fetchall()
                if result:
                    return render_template('result.html',
                                         games=result)
                else:
                    return render_template('result.html', message="No games found")
            
            elif action == 'By Rating':
                if game_name:
                    search_pattern = f"%{game_name}%"
                    cursor.execute(searched + "SELECT name, release_date, price FROM searched ORDER BY (positive_ratings-negative_ratings) DESC", [search_pattern])
                else:
                    cursor.execute("SELECT name, release_date, price FROM steam ORDER BY (positive_ratings-negative_ratings) DESC")
                result = cursor.fetchall()
                if result:
                    return render_template('result.html',
                                         games=result)
                else:
                    return render_template('result.html', message="No games found")
            
            else:
                return render_template('result.html', message="Unknown action")
    
    except pg8000.Error as e:
        flash(f"Database error: {str(e)}", "error")
        return redirect(url_for('home'))

@app.route("/modify", methods=['GET', 'POST'])
def modify():
    """Search for a specific game"""
    if request.method == 'POST':
        game_name = request.form.get('game_name', '').strip()
        
        if not game_name:
            flash("Please enter the name of a game", "warning")
            return render_template("modify.html", result=None, game_name=None)
        
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("SET search_path TO maxwell_lamb")
                query = "SELECT name, release_date, price FROM steam WHERE name ILIKE %s ORDER BY appid"
                search_pattern = f"%{game_name}%"
                cursor.execute(query, [search_pattern])
                results = cursor.fetchall()
            
            if results:
                return render_template("modify.html", results=results, game_name=game_name)
            else:
                flash(f"No game found with name: {game_name}", "info")
                return render_template("modify.html", results=None, game_name=game_name)
        
        except pg8000.Error as e:
            flash(f"Database error: {str(e)}", "error")
            return render_template("modify.html", results=None, game_name=None)
    
    return render_template("modify.html", results=None, game_name=None)        

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)