import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",   # add password later if needed
        database="lung_cancer_db",
        cursorclass=pymysql.cursors.DictCursor
    )
