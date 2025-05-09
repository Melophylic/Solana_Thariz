env\Scripts\activate
pip install -r requirements.txt
python3.9 manage.py collectstatic
# python3.9 manage.py create_superuser