import sqlite3
import os
from bs4 import BeautifulSoup as Soup
import json, requests, re
import datetime

DB_FILE = 'data.sqlite'

rex = re.compile(r'\s+')
numb = re.compile(r'[^0-9]')
rdate = re.compile(r'[^a-z0-9]')
const = re.compile(r'[^a-z0-9\-]')

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute('drop table IF EXISTS data')
c.execute('create table data (birth_date,"+children","+constituency",contact_details,"+education",email,image,images,link,"+marital_status",name,memberOf,other_names,"+place_of_birth","+profession",source,"+spouse")')

def words2date(bdate):
    bdate = clean(rdate.sub(' ',bdate.lower()))
    if len(bdate)<2:
        return None
    bdate = bdate.replace('febuary','february')
    month = ['january','february','march','april','may','june','july','august','september','october','november','december']
    bdate = bdate.split(' ')
    date = datetime.date(int(bdate[2]),int(month.index(bdate[1])+1),int(numb.sub('',bdate[0])))
    return date.isoformat()

def text2int(textnum, numwords={}):
    if not numwords:
      units = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
      ]

      tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

      scales = ["hundred", "thousand", "million", "billion", "trillion"]

      numwords["and"] = (1, 0)
      for idx, word in enumerate(units):    numwords[word] = (1, idx)
      for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
      for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
            return 0

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0
    return result + current

def num(s):
    s = numb.sub(' ',s)
    s = clean(s)
    if s is None:
        return 0
    return int(s)

def clean(s):
    return rex.sub(' ',s).strip()

req = requests.get('http://delhiassembly.nic.in/aspfile/whos_who/VIthAssembly/listmembers_VIth_AssemblyWsW.htm')
soup = Soup(req.text,'html.parser')
for row in soup.find_all('tr'):
    member = {}
    if 'Sr. No.' in row.text: #skipping the first one
        continue
    
    cells = row.find_all('td')
    link = 'http://delhiassembly.nic.in/aspfile/whos_who/VIthAssembly/'+cells[1].find('a')['href']
    cls = []
    for cell in cells:
        cls.append(clean(cell.text))
    cells = cls
    
    det = requests.get(link)
    ds = Soup(det.text, 'html.parser')
    details = []
    for line in ds.find_all('tr'):
        text = str(line.text)
        if len(text.split(':'))<2:
            continue
        #some complication because of an extra ':'
        detail = clean(text.split(':')[1]) if 'Profession'not in text else clean(text.split(':')[2])
        details.append(detail)
        
    bdate = clean(details[6])
    member = {
    'other_names' : [
        {
            'name' : clean(cells[1]),
            'note' : 'Name with prefix'
         }
        ],
    'name' : clean(details[0]),
    'email' : clean(cells[6]),
    'birth_date' : words2date(bdate),
    'image' : 'http://delhiassembly.nic.in/aspfile/whos_who/VIthAssembly/WhosWho/'+ds.find('img')['src'],
    'images' : [{'url':'http://delhiassembly.nic.in/aspfile/whos_who/VIthAssembly/WhosWho/'+ds.find('img')['src']}],
    '+place_of_birth' : clean(details[7]),
    '+constituency' : {
        'name':clean(cells[5]).split('(')[0],
        'identifier':num(clean(cells[5]).split('(')[1]),
        'classification':'constituency',
        '+state':'Delhi'
        },
    'memberOf' : {
        'id':clean(cells[2]),
        'name':clean(details[2])
        },
    '+education' : [clean(details[8])],
    '+profession' : [clean(details[10])],
    '+marital_status' : True if 'married' in clean(details[12]).lower() else False,
    '+spouse' : clean(details[13]),
    '+children' : {
        'female':text2int(details[15].lower()),
        'male':text2int(details[16].lower())
        },
    'source' : 'delhiassembly.nic.in',
    'links' : [{'url':link,'note':'delhiassembly.nic.in'}]
    }
    contact_details = [
            {
                'type':'email',
                'label':'email',
                'value':clean(cells[6])
            },
            {
                'type':'address',
                'label':'Residential address',
                'value':clean(cells[3])
            }
        ]
    phones = clean(cells[4])
    for phone in phones.split(','):
        contact_details.append({
                'type':'phone',
                'label':'phone/mobile',
                'value':clean(phone)
            })
    member['contact_details']=contact_details
    print(json.dumps(member,sort_keys=True,indent=4))
    data = [
        member['birth_date'],
        json.dumps(member['+children'],sort_keys=True),
        json.dumps(member['+constituency'],sort_keys=True),
        json.dumps(member['contact_details'],sort_keys=True),
        json.dumps(member['+education'],sort_keys=True),
        member['email'],
        member['image'],
        json.dumps(member['images'],sort_keys=True),
        json.dumps(member['links'],sort_keys=True),
        json.dumps(member['+marital_status'],sort_keys=True),
        member['name'],
        json.dumps(member['memberOf'],sort_keys=True),
        json.dumps(member['other_names'],sort_keys=True),
        member['+place_of_birth'],
        json.dumps(member['+profession'],sort_keys=True),
        member['source'],
        member['+spouse']
        ]
    c.execute('insert into data values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',data)
conn.commit()
c.close()
