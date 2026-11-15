MEMORA - Personalised Memory Books
IS2108 Pair Project, AY2026/27 Semester 1

GROUP DETAILS
Group:          PP45
Group leader:   Lee Yi Cheng Austin, A0322742L, e1525649@u.nus.edu
Member:         Li Jiapeng Gavin, A0276014L, e1129766@u.nus.edu
Demo video:     https://youtu.be/M7uoNTZEhIA

OVERVIEW
MEMORA is a B2C web shop that turns customers' photos into personalised memory books,
delivered as a PDF (Digital) or as a printed book in a gift box (Print + Digital).
Customers choose a cover style and photo package, check out with a demo payment, upload
photos with captions, review the studio's PDF, request one free revision, approve the
design and track delivery. Staff use a custom studio panel (not the Django admin) to run
production, deliver PDFs, ship orders, and manage the catalogue, gift-box inventory,
customer records and reviews.

Machine learning: a gradient boosting regression model (scikit-learn) predicts how many
photos a customer's story will have from their occasion and people tags, group size and
number of days. The configurator uses the prediction to recommend a photo package.

REQUIREMENTS
Python 3.14 (developed and tested on Python 3.14.7, Windows 11).
All packages are listed in requirements.txt.

SETUP (run these from this folder, the one containing readme.txt)
1. Create and activate a virtual environment
     Windows:      python -m venv .venv
                   .venv\Scripts\activate
     macOS/Linux:  python3 -m venv .venv
                   source .venv/bin/activate
2. Install the packages
     pip install -r requirements.txt
3. Go to the Django project folder (the one containing manage.py)
     cd SharedMemoir/sharedmemoir
4. Create the database
     python manage.py migrate
5. Load the catalogue and demo data (customers, orders at every stage, photos, PDFs)
     python manage.py seed_demo
6. Start the server
     python manage.py runserver
7. Open http://127.0.0.1:8000/

To rebuild the demo data from scratch at any time:
     python manage.py seed_demo --reset

DEMO ACCOUNTS (password for all: Memora2026!)
  studio   Staff account: opens the Studio panel at /staff/
  alice    Customer: completed, printing, in production and cancelled orders
  ben      Customer: a PDF waiting for approval (Marathon Weekend)
  chloe    Customer: a revision in progress (Grandma's 80th)
  dev      Customer: a revised PDF waiting for approval (Dragon Boat Season)
  emma     Customer: a shipped order to confirm (Our Wedding Day)
  frank    Deactivated customer: login is refused
You can also register a new customer account from the site.

MAIN PAGES
  /                  Home
  /shop/             Cover styles and package prices
  /configure/<slug>/ Customise a book (with ML package recommendation)
  /bag/, /checkout/  Bag and demo checkout
  /orders/           My orders (customer)
  /staff/            Studio panel: dashboard, orders, catalogue, customers, reviews

MACHINE LEARNING FILES (SharedMemoir/sharedmemoir/shop/ml/)
  generate_data.py    Creates the synthetic training data (past_orders.csv)
  train_model.py      Trains and compares three models; saves the best as photo_model.joblib
  photo_model.joblib  The saved model loaded by shop/recommender.py
To retrain (from the folder containing manage.py):
     python shop/ml/generate_data.py
     python shop/ml/train_model.py

NOTES
- Payments are simulated. No real payment is taken and no card details are collected.
- DEBUG is True so that uploaded photos and PDFs are served by the development server.
- The database (db.sqlite3) and uploaded files (media/) are not included; steps 4-5 create them.