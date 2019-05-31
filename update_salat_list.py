from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server
import sqlite3
import os.path
import io
from datetime import datetime
import scrape
import time

if os.path.exists ('salat.db3'):
    dbcon = sqlite3.connect ('salat.db3')
    cur = dbcon.cursor()
    cur.execute ("""DELETE FROM SALAT_MENU""")
    dbcon.commit()
    # scrape.scrape_init(dbcon)
    cur.close()
else:
    print 'Cannot find database !'
