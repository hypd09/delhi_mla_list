# This is a template for a Python scraper on morph.io (https://morph.io)
# including some code snippets below that you should find helpful

import scraperwiki
# import lxml.html
#
# # Read in a page
# html = scraperwiki.scrape("http://foo.com")
#
# # Find something on the page using css selectors
# root = lxml.html.fromstring(html)
# root.cssselect("div[align='left']")
#
# # Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
#
# # An arbitrary query against the database
# scraperwiki.sql.select("* from data where 'name'='peter'")

# You don't have to do things with the ScraperWiki and lxml libraries.
# You can use whatever libraries you want: https://morph.io/documentation/python
# All that matters is that your final data is written to an SQLite database
# called "data.sqlite" in the current working directory which has at least a table
# called "data".

from bs4 import BeautifulSoup as Soup
import json, requests, re
import datetime

rex = re.compile(r'\s+')
numb = re.compile(r'[^0-9]')
rdate = re.compile(r'[^a-z0-9]')

def words2date(bdate):
    bdate = clean(rdate.sub(' ',bdate.lower()))
    month = ['january','february','march','april','may','june','july','august','september','october','november','december']
    bdate = bdate.split(' ')
    print(bdate)
    date = datetime.date(int(bdate[2]),int(month.index(bdate[1])),int(numb.sub('',bdate[0])))
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
          raise Exception("Illegal word: " + word)

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current

def num(s):
    s = numb.sub(' ',s)
    s = clean(s)
    if s is None or len(s)<3:
        return 0
    return text2int(s)

def clean(s):
    return rex.sub(' ',s).strip()

members = []
req = requests.get('http://delhiassembly.nic.in/aspfile/whos_who/VIthAssembly/listmembers_VIth_AssemblyWsW.htm')
soup = Soup(req.text,'html.parser')
members = []
for row in soup.find_all('tr'):
    member = {}
    if 'Sr. No.' in row.text: #skipping the first one
        continue
    
    cells = row.find_all('td')
    link = 'http://delhiassembly.nic.in/aspfile/whos_who/VIthAssembly/'+cells[1].find('a')['href']
    cls = []
    for c in cells:
        cls.append(clean(c.text))
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
    print(json.dumps(details,indent=4))
    print(json.dumps(cells,indent=4))
    bdate = clean(details[6])
    member = {
    'other_names' : [
        {
            'name' : clean(cells[0]),
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
        'identifier':clean(details[4].split(';')[1]),
        'classification':'constituency',
        '+state':'Delhi'
        },
    'org:memberOf' : {
        'id':clean(cells[2]),
        'name':clean(details[2])
        },
    '+education' : [clean(details[8])],
    '+profession' : [clean(details[10])],
    '+marital_status' : True if 'married' in clean(details[12]).lower() else False,
    '+spouse' : clean(details[13]),
    '+children' : {
        '+male':num(details[15].lower()),
        '+female':num(details[16].lower())
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
    members.append(member)
    print(json.dumps(member,indent=4,sort_keys=True))
scraperwiki.sqlite.save(unique_keys=['name'], data=members)
