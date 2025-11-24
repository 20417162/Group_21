#!/usr/bin/env python
import os
from dotenv import load_dotenv
from app import create_app

load_dotenv()

app = create_app(os.environ.get('FLASK_ENV') or 'development')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
