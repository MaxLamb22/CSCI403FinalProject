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
            cursor.execute("SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM steam ORDER BY appid")
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
                query = "SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM steam WHERE name ILIKE %s ORDER BY appid"
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
        last_page = request.referrer or url_for('home')
        # Get form data
        action = request.form.get('action')
        game_name = request.form.get("game_name")
        
        if game_name:
            search_pattern = f"%{game_name}%"
            searched = """
                    WITH searched AS (
                            SELECT name, release_date, price, positive_ratings, negative_ratings, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews
                            FROM steam 
                            WHERE name ILIKE %s
                    )"""
        
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SET search_path TO maxwell_lamb")

            if action == 'Count':
                if game_name:
                    cursor.execute(searched + "SELECT COUNT(*) FROM searched", [search_pattern])
                    count = cursor.fetchone()[0]
                    return render_template('result.html', 
                                     message=f"Total games found: {count}", last_page=last_page)
                else:
                    cursor.execute("SELECT COUNT(*) FROM steam")
                    count = cursor.fetchone()[0]
                    return render_template('result.html', 
                                     message=f"Total games in database: {count}", last_page=last_page)
            
            elif action == 'By Newest':
                if game_name:
                    cursor.execute(searched + "SELECT name, release_date, price, reviews FROM searched ORDER BY release_date DESC", [search_pattern])
                else:
                    cursor.execute("SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM steam ORDER BY release_date DESC")
                result = cursor.fetchall()
                if result:
                    return render_template('result.html', games=result, last_page=last_page)
                else:
                    return render_template('result.html', message="No games found", last_page=last_page)
            
            elif action == 'By Rating':
                if game_name:
                    search_pattern = f"%{game_name}%"
                    cursor.execute(searched + "SELECT name, release_date, price, reviews FROM searched ORDER BY reviews DESC", [search_pattern])
                else:
                    cursor.execute("SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM steam ORDER BY reviews DESC")
                result = cursor.fetchall()
                if result:
                    return render_template('result.html', games=result, last_page=last_page)
                else:
                    return render_template('result.html', message="No games found", last_page=last_page)
            
            elif action == 'By Price':
                if game_name:
                    search_pattern = f"%{game_name}%"
                    cursor.execute(searched + "SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM searched ORDER BY price", [search_pattern])
                else:
                    cursor.execute("SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM steam ORDER BY price")
                result = cursor.fetchall()
                if result:
                    return render_template('result.html', games=result, last_page=last_page)
                else:
                    return render_template('result.html', message="No games found", last_page=last_page)
            
            elif action == 'By Player Count':
                if game_name:
                    search_pattern = f"%{game_name}%"
                    cursor.execute(searched + "SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM searched ORDER BY owners DESC", [search_pattern])
                else:
                    cursor.execute("SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM steam ORDER BY owners DESC")
                result = cursor.fetchall()
                if result:
                    return render_template('result.html', games=result, last_page=last_page)
                else:
                    return render_template('result.html', message="No games found", last_page=last_page)
                
            elif action == 'By Name':
                if game_name:
                    search_pattern = f"%{game_name}%"
                    cursor.execute(searched + "SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM searched ORDER BY name", [search_pattern])
                else:
                    cursor.execute("SELECT name, release_date, price, ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2) AS reviews FROM steam ORDER BY name")
                result = cursor.fetchall()
                if result:
                    return render_template('result.html', games=result, last_page=last_page)
                else:
                    return render_template('result.html', message="No games found", last_page=last_page)
            
            else:
                return render_template('result.html', message="Unknown action", last_page=last_page)
    
    except pg8000.Error as e:
        flash(f"Database error: {str(e)}", "error")
        return redirect(url_for('home'))

@app.route("/modify", methods=['GET', 'POST'])
def modify():
    if request.method == 'POST':
        game_name = request.form.get('game_name', '').strip()
    else:
        game_name = request.args.get('game_name', '').strip()

    if not game_name:
        # Only flash if user POSTed an empty search
        if request.method == 'POST':
            flash("Please enter the name of a game", "warning")
        return render_template("modify.html", results=None, game_name=None)
    
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SET search_path TO maxwell_lamb")
            query = """
                SELECT name, positive_ratings, negative_ratings,
                       ROUND(((positive_ratings::float/(positive_ratings+negative_ratings))*100)::numeric, 2)
                       AS reviews
                FROM steam
                WHERE name ILIKE %s
                ORDER BY appid
            """
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

@app.route("/update_rating", methods=['POST'])
def update_rating():
    game_name = request.form.get("game_name")
    field = request.form.get("field")

    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SET search_path TO maxwell_lamb")

            if field == "positive_add":
                cursor.execute("""
                    UPDATE steam
                    SET positive_ratings = positive_ratings + 1
                    WHERE name = %s
                """, [game_name])

            elif field == "positive_remove":
                cursor.execute("""
                    UPDATE steam
                    SET positive_ratings = positive_ratings - 1
                    WHERE name = %s
                """, [game_name])

            elif field == "negative_add":
                cursor.execute("""
                    UPDATE steam
                    SET negative_ratings = negative_ratings + 1
                    WHERE name = %s
                """, [game_name])

            elif field == "negative_remove":
                cursor.execute("""
                    UPDATE steam
                    SET negative_ratings = negative_ratings - 1
                    WHERE name = %s
                """, [game_name])

            db.commit()

        flash(f"Updated {field.split("_")[0]} reviews for {game_name}.", "success")
        search_term = request.form.get("search_term", game_name)
        return redirect(url_for("modify", game_name=search_term))

    except pg8000.Error as e:
        flash(f"Database error: {str(e)}", "error")
        return redirect(url_for("modify"))

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)