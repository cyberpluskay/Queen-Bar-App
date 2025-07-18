
HOW TO RUN - Queen Bar App
 (Backup from ~/Documents/Queen)  OR from whereever the app folder is located.



##  First Time Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

Set environment variables:
   export FLASK_APP=app.py
   export FLASK_ENV=development
For a clean database
# Initialize the database
python init_db.py  # <-- or flask db upgrade


3. Run the app:
   flask run

4. Access it in your browser:
   http://127.0.0.1:5000



