from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server
import cgi
import sqlite3
import os.path
import io
from datetime import datetime
# import scrape
import time

salat_zlava_map = { 1:0.3, 2:0.3, 3:0.3, 4:0.3,
                    5:0.5, 6: 0.5, 7:0.5, 8:0.6,
                    9:0.6, 10:0.6, 11:0.6, 12:0.6,
                    13:0.6, 14:0.6, 15:0.6, 16:0.6
                }
PRICE_MENU_SMALL = 4.5
PRICE_MENU_BIG = 5.5
salat_box_price = 0.33
salat_delivery_price = 0.66
salat_delivery_treshold = 20
if not os.path.exists ('salat.db3'):
    dbcon = sqlite3.connect ('salat.db3')
    cur = dbcon.cursor()
    cur.execute ("""CREATE TABLE SALAT (date integer not null, customer text not null, salat_id integer not null,salat_name text, type text not null,size text not null,dressing_id integer not null, dressing_name text not null,note text, soup text not null,price float not null,ip_address text not null);""")
    cur.execute ("""CREATE TABLE IF NOT EXISTS SALAT_MENU (ID INTEGER, NAME TEXT, PRICE_SMALL FLOAT,PRICE_BIG FLOAT, PRIMARY KEY (ID));""")
    cur.execute ("""CREATE TABLE IF NOT EXISTS DRESSING_MENU (ID INTEGER not null, NAME TEXT);""")
    cur.execute ("""CREATE TABLE IF NOT EXISTS SOUP_MENU (ID INTEGER not null, NAME TEXT);""")
    cur.execute ("""CREATE TABLE IF NOT EXISTS LOCK_ORDER (date integer not null, admin_ip_address not null, lock integer not null);""")
    cur.execute ("""CREATE TABLE IF NOT EXISTS POWER_USERS (admin_ip_address not null, admin_name text);""")
    dbcon.commit()
    # scrape.scrape_init(dbcon)
    cur.close()
else:
    dbcon = sqlite3.connect ('salat.db3')

assert os.path.exists ('salat_page.html')

with io.open ('salat_page.html', 'r', encoding='utf-8') as rf:
    template = rf.read()

def get_default_user_name(cur,ip):
    cur.execute(""" SELECT CUSTOMER FROM SALAT WHERE IP_ADDRESS=? ORDER BY DATE ASC""", (ip,))
    row = cur.fetchone()

    if not row:
        return ''
    else:
        return row[0]

def getSalatList(cur,type):
    salat_list = []
    cur.execute ("""SELECT SALAT_MENU.ID,SALAT_MENU.NAME,SALAT_MENU.PRICE_SMALL,SALAT_MENU.PRICE_BIG FROM SALAT_MENU WHERE SALAT_MENU.NAME IS NOT NULL""")
    records = cur.fetchall()
    salat_list_item = ''
    for row in records:
        if type == 0:
            salat_list.append((row[0],row[1],row[2],row[3]))
        elif type == 1:
            salat_list_item= "<option value='%s'>%s</option>"%(row[0],row[1])
            salat_list.append(salat_list_item)
    return salat_list

def getDressingList(cur,type):
    dressing_list=[]
    cur.execute ("""SELECT DRESSING_MENU.ID,DRESSING_MENU.NAME FROM DRESSING_MENU WHERE DRESSING_MENU.NAME IS NOT NULL""")
    records = cur.fetchall()
    dressing_list_item = ''
    for row in records:
        if type == 0:
            dressing_list.append((row[0],row[1]))
        elif type == 1:
            dressing_list_item= "<option value='%s'> %s </option>"%(row[0],row[1])
            dressing_list.append(dressing_list_item)
    return dressing_list

def getListedName(list,id):
    for row in list:
        if int(row[0]) == int(id):
            return  (row[1])
    return ""

def getListedItem(list,id):
    for row in list:
        if int(row[0]) == int(id):
            return  row
    return ""

def getSalatPrice(salatWithPrices,size,soup):
    if soup == "ziadna":
        price = salatWithPrices[2] if size == 'maly' else salatWithPrices[3]
    else:
        price = PRICE_MENU_SMALL if size == 'maly' else PRICE_MENU_BIG
    print 'returning '
    return price

def get_total_price(salatPrice):
    print 'Calculating total price:'
    salatCount= len(salatPrice)
    print 'SALAT count : %d' % salatCount

    totalPrice = 0
    idx = 0
    for x in salatPrice:
        print 'SALAT %d: %2.2f' % (idx, x)
        totalPrice += x
        idx += 1
    print 'Total price : {:2.2f}'.format(float(totalPrice))

    return totalPrice

def server_main(environ, start_response):
    ip_address = environ['REMOTE_ADDR']
    cur = dbcon.cursor()

    if len(environ['PATH_INFO']) > 1:
        filename = environ['PATH_INFO'][1:]
        if os.path.exists (filename):
            status = '200 OK'
            _, ext = os.path.splitext (filename)
            if ext == '.css':
                headers = [('Content-type', 'text/css;charset=utf-8')]
            elif ext == '.html':
                headers = [('Content-type', 'text/html;charset=utf-8')]
            else:
			    headers = [('Content-type', 'text/plain;charset=utf-8')]
            start_response (status, headers)
            with io.open (filename, 'r', encoding='utf-8') as rf:
                ret = rf.read()
            return [ret.encode ('utf-8'),]

    date = datetime.now().year * 10000 + datetime.now().month * 100 + datetime.now().day

    cur.execute ("""SELECT LOCK,ADMIN_IP_ADDRESS FROM LOCK_ORDER WHERE DATE = ?""", (date,))
    lock_data = cur.fetchone()

    orders_locked = 0
    order_admin_name = ''
    if lock_data :
        orders_locked = lock_data[0]
        print 'Finding admin with ip %s' % lock_data[1]
        cur.execute(""" SELECT ADMIN_NAME FROM POWER_USERS WHERE ADMIN_IP_ADDRESS=? """, (lock_data[1],))
        data = cur.fetchone()
        if data :
            order_admin_name = data[0]
            print 'Admin name is %s' % order_admin_name
    if environ['REQUEST_METHOD'].upper() == 'DELETE':
        delete_time = time.time()
        delete_env = environ.copy()
        delete_env['QUERY_STRING'] = ''
        form_type = environ['PATH_INFO']
        print form_type
        if form_type == '/cancelOrder':
            print 'cancel Order'
            print 'deleting'
            deleting = cgi.FieldStorage(
                fp=environ['wsgi.input'],
                environ=delete_env,
                keep_blank_values=True)
            customer = deleting["customerButton"].value.strip()[:30]
            cur.execute ("""DELETE FROM SALAT WHERE DATE=? AND CUSTOMER=? AND IP_ADDRESS=?""", (date, customer, ip_address))
    if environ['REQUEST_METHOD'].upper() == 'POST':
        post_time = time.time()
        post_env = environ.copy()
        post_env['QUERY_STRING'] = ''

        form_type = environ['PATH_INFO']
        print form_type

        if form_type =='/lock' :
            print 'lock order'
            if not lock_data:
                print 'Create order lock'
                cur.execute ("""INSERT INTO LOCK_ORDER (DATE, ADMIN_IP_ADDRESS, LOCK) VALUES (?,?,?)""", (date, ip_address, 1))
            else:
                print 'Update order lock'
                lock_flag = 1
                if orders_locked :
                    lock_flag = 0

                print 'Lock flag is %d' % lock_flag
                cur.execute ("""UPDATE LOCK_ORDER SET ADMIN_IP_ADDRESS=?, LOCK=? WHERE DATE=? """, (ip_address, lock_flag, date))

        if form_type =='/setOrderAdmin' :
            print 'set order admin'
            if not lock_data:
                print 'Create order lock info'
                cur.execute ("""INSERT INTO LOCK_ORDER (DATE, ADMIN_IP_ADDRESS, LOCK) VALUES (?,?,?)""", (date, ip_address, 0))
            else:
                print 'Update order lock info'
                lock_flag = orders_locked

                print 'Lock flag is %d' % lock_flag
                cur.execute ("""UPDATE LOCK_ORDER SET ADMIN_IP_ADDRESS=?, LOCK=? WHERE DATE=? """, (ip_address, lock_flag, date))

        if form_type =='/order' and not orders_locked:
            print 'order salat'
            post = cgi.FieldStorage(
                fp=environ['wsgi.input'],
                environ=post_env,
                keep_blank_values=True)

            customer = post["customer"].value.strip()[:30]
            salat_id = post["salat_id"].value.strip()
            type = post["typ"].value.strip()[:50]
            ssize = post["ssize"].value.strip()[:50]
            dressing_id = post["dressing_id"].value.strip()[:50]
            note = post["note"].value.strip()[:50]
            soup = post["soup"].value.strip()[:50]

            salat_list = getSalatList(cur,0)
            dressing_list = getDressingList(cur,0)
            salatWithPrices = getListedItem(salat_list,salat_id)
            salat = getListedName(salat_list,salat_id)
            dressing = getListedName(dressing_list,dressing_id)
            price = getSalatPrice(salatWithPrices,ssize,soup)

            #Check invalid chars
            invalid_chars = set(' /\<>')
            if any( (c in invalid_chars) for c in customer ) or any( (c in invalid_chars) for c in note ):
                print note
                print customer
                print "Invalid chars detected !"
                customer = ''
                salat = ''
                note = ''

            if customer != "" and salat == "":
                print 'deleting'
                cur.execute ("""DELETE FROM SALAT WHERE DATE=? AND CUSTOMER=? AND IP_ADDRESS=?""", (date, customer, ip_address))
            elif customer != "" and salat != "":
                cur.execute ("""SELECT CUSTOMER FROM SALAT WHERE DATE = ? AND CUSTOMER=? """, (date, customer))
                row = cur.fetchone()
                if row:
                    cur.execute ("""SELECT CUSTOMER FROM SALAT WHERE DATE = ? AND CUSTOMER=? AND IP_ADDRESS=? """, (date, customer, ip_address))
                    valid_update = cur.fetchone()

                    if valid_update:
                        print ('updating')
                        cur.execute ("""UPDATE SALAT SET SALAT_ID=?,SALAT_NAME=?,TYPE=?, SIZE=?,DRESSING_ID=?,DRESSING_NAME=?,NOTE=?,SOUP=?,PRICE=? WHERE DATE=? AND CUSTOMER=? """, (salat_id, salat,type,ssize,dressing_id,dressing,note,soup,price, date, customer))
                else:
                    print ('inserting')
                    cur.execute ("""INSERT INTO SALAT (DATE, CUSTOMER, SALAT_ID,SALAT_NAME,TYPE, SIZE,DRESSING_ID,DRESSING_NAME, NOTE, SOUP,PRICE,IP_ADDRESS) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (date, customer, salat_id, salat, type,ssize,dressing_id,dressing,note, soup,price,ip_address))
            else:
                pass # do nothing
        timer_res = time.time() - post_time
        print "POST TIMING %2.2f" % float(timer_res)

        dbcon.commit()
        cur.close()
        status = '301 Redirect'
        headers = [('Location', '/')]
        start_response(status, headers)
        return '<html><body>redirecting</body></html>'


    listing = []
    cur = dbcon.cursor()

    cur.execute(""" SELECT COUNT(*) FROM SALAT WHERE DATE = ? """, (date,))
    row = cur.fetchone()
    salat_count = row[0]

    cur.execute ("""SELECT SALAT.CUSTOMER, SALAT_NAME, TYPE,SIZE,DRESSING_NAME,SOUP,PRICE, CASE WHEN NOTE IS NULL THEN "" ELSE NOTE END FROM SALAT,SALAT_MENU WHERE DATE = ? AND CAST(SALAT.SALAT_ID as integer)=SALAT_MENU.ID""", (date,))
    salat_cena_zlava = 0.0;  ###salat_zlava_map.get(salat_count, 0.0)

    idx = 1
    salatPrices= []
    for row in cur:
        formattedprice = '{0:2.2f}'.format(row[6])
        cancelActionText = "<form class='form-inline' action='cancelOrder/"
        cancelActionText += row[0]
        cancelActionText += " method='DELETE'><div class='input-group'><span class='input-group-btn'><button type='submit' name='customerButton' class='btn btn-success' id='bt'>Zrus<i class='fa fa-angle-right'></i></button></span></div></form>"
        s =  "<tr><td>%d</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td><td>%s</td> <td>%s</td> <td>%s</td> <td> %s </td> </tr>" % (idx, row[0], row[1], row[2], row[3], row[4], row[5],row[7],formattedprice,cancelActionText)
        listing.append (s)
        if idx % 4 == 0 :
            s =  '<tr class="salat_group_separator"> <td></td> <td></td> <td></td> <td></td> <td></td> <td></td> <td></td><td></td> <td></td> </tr>'
            listing.append (s)
        idx += 1

    defaultUserName = get_default_user_name(cur, ip_address)
    print 'Default user name is %s' % defaultUserName

    status = '200 OK'
    headers = [('Content-type', 'text/html;charset=utf-8')]
    start_response(status, headers)
    salat_select_list = getSalatList(cur,1);
    dressing_select_list =getDressingList(cur,1)
    ret = template.replace('__date__', datetime.now().strftime("%d.%m.%Y")).replace('__list__', ''.join (listing)).replace('__defaultUserName__', ''.join(defaultUserName)).replace('__salat_list__',''.join(salat_select_list)).replace('__dressing_list__',''.join(dressing_select_list))

    # admin mode check
    admin_ip = environ['REMOTE_ADDR']
    print admin_ip

    cur.execute(""" SELECT COUNT(*) FROM POWER_USERS WHERE ADMIN_IP_ADDRESS = ? """, (admin_ip,))
    row = cur.fetchone()
    admin_mode = row[0]

    if not admin_mode :
        ret = ret.replace('__hideAdminClass__', "hide_class");
    else:
        print 'Admin mode active'

    # check orders lock
    if orders_locked :
        ret = ret.replace('__hideOrder__', "hide_class")

    else:
        ret = ret.replace('__ordersClosedInfo__', "hide_class");

    total_price_info = ""
    if admin_mode:
        totalPrice =  get_total_price(salatPrices)
        total_price_info = 'Cena objednávky :   {0:2.2f}  €'.format(float(totalPrice))

    order_info=""
    order_extra_info=""
    if order_admin_name!='' :
        order_info = 'Dnes salat objednáva %s. %s' % (order_admin_name, total_price_info)
        order_extra_info = 'Číslo zľavovej karty je 18'

    ret= ret.replace('__OrderAdminInfo__', order_info);
    ret= ret.replace('__OrdersAdminExtraInfo__', order_extra_info);

    return [ret.encode ('utf-8'),]

port = 3333
httpd = make_server('192.168.160.109', port, server_main)
print "Serving on port %d..." % port
httpd.serve_forever()
