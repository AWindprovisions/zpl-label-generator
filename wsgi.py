import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.main import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)

