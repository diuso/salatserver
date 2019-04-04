import io
import sqlite3
import urllib
import urllib2

#set proxy server handlers
def Setup_Proxy():
    proxy = urllib2.ProxyHandler({
        'http': 'proxycloud:80',
        'https': 'proxycloud:80'
    })
    opener = urllib2.build_opener(proxy)
    urllib2.install_opener(opener)
    print 'Proxy installed.'

def get_tags (content):
    tags = []
    i = 0
    while i < len (content):
        if content[i] == '<':
            tag_name = ''
            while i < len (content) and content[i] not in (' ', '>'):
                tag_name += content[i]
                i += 1
            while i < len (content) and content[i] not in ('>'):
                i += 1
            if i < len (content):
                i += 1
            tags.append (tag_name + '>')
        else:
            value = ''
            while i < len (content) and content[i] != '<':
                value += content[i]
                i += 1
            if value.strip():
                tags.append (value.strip())
    return tags

def scrape_salat (db,content):
    if (content.__len__() == 0 ) :
        print 'ERROR : No data for parsing !'
        return

    pos = 0
    while True:
        single = []
        tr_beg = content.find ('<tr ', pos)
        if tr_beg != -1:
            tr_end = content.find ('</tr>', tr_beg)
            if tr_end != -1:
                pos = tr_end + 5
                buf = content[tr_beg:tr_end + 5]
                inside_tr, inside_td = False, False
                for tag in get_tags (buf):
                    if tag == '<tr>':
                        inside_tr = True
                    elif inside_tr and tag == '</tr>':
                        inside_tr = False
                    elif inside_tr and tag == '<td>':
                        inside_td = True
                    elif inside_tr and inside_td and tag == '</td>':
                        inside_td = False
                    elif inside_td and tag[0] == '<':
                        pass # ignore tags inside td
                    elif inside_td and tag[0] != '<':
                        single.append(tag)
                if len (single) > 0 and single[0][0].isdigit() and single[0][-1] == '.':
                    if len (single) == 4:
                        name = single[2].replace ('&amp;', '&')
                        price = single[3][:-1]
                    elif len (single) == 5:
                        name = single[2] + ' ' + single[3]
                        name = name.replace ('&amp;', '&')
                        price = single[4][:-1]
                    cur = db.cursor()
                    cur.execute ("""INSERT INTO SALAT_MENU (ID, SIZEs, NAME, PRICE) VALUES (?, ?, ?, ?)""",
                                 (int(single[0][:-1]),
                                  single[1],
                                  name,
                                  price))
                    db.commit()
                    print (single)
                single = []
            else:
                print ('error: end tr')
                break
        else:
            break

def scrape_init(db):
    Setup_Proxy();
    salat_page =''
    with io.open ('salat.html', 'r', encoding='utf-8') as f:
        salat_page = f.read()


    scrape_salat (db,salat_page)
