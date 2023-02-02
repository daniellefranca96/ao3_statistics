from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import warnings
import pathlib


def get_request(url, retries):
    r = requests.get(url)
    
    if r.status_code != 200:
        retries.append(url)
    
    return r
    
def retry(retries, dados):
    for i in range(0, 3):
        urls = [x for x in retries]
        for url in urls:
            retries.remove(url)
            get_conteudo_pagina_por_url()
            
            
def error(message, close):
    print(message)
    if close:
        exit()
        
def save_retry(uri, retries):
    retries.add(uri)
    
def make_request(uri, retries, close):
    r = None
    
    try: 
        r = requests.get(uri) 
    except: 
        save_retry(uri)
        
    if r == None:
        error('ERROR: PROBLEM CONNECTING ON THE INTERNET', True)
    elif r.status_code == 200:
        print('Start processing...')
    elif r.status_code == 404:
        error('ERROR: USERNAME NOT FOUND', True)
    else:
        error('ERROR: PROBLEM CONNECTING ON THE INTERNET', True)
    return r


def get_total_paginas(username):
    uri = "https://archiveofourown.org/users/katerinaptrv/pseuds/#username/bookmarks".replace("#username", username)
    r = make_request(uri, [], False)
        
    soup = BeautifulSoup(r.text, "html.parser")
    nav = soup.find(title='pagination')
    pages = nav.find_all("li")
    pag = BeautifulSoup(str(pages[-2]), "html.parser")
    return int(pag.a.text)+1

def get_conteudo_pagina_por_url(url, dados, retries):
    r = make_request(url, retries, False)
    processa_conteudo_pagina(dados, r)

def get_conteudo_pagina(pagina, dados, retries):
    url = "https://archiveofourown.org/users/katerinaptrv/pseuds/katerinaptrv/bookmarks?page="+str(pagina)
    r = make_request(url, retries, False)
    processa_conteudo_pagina(dados, r)

def processa_conteudo_pagina(dados, request):    
    if request.status_code == 200:
        soup = BeautifulSoup(request.text, "html.parser")
        result = soup.find_all("li", attrs={"role":"article"})

        for res in result:
            get_dados_fanfic(res, dados)
        

def get_author(fanfic, dados):
    author = fanfic.find("a", attrs={"rel":"author"})
    if author != None:
        author_name = author.text
        if dados['author'].get(author_name) == None:
            dados['author'][author_name] = 1
        else:
            dados['author'][author_name] =  dados['author'][author_name] + 1

def get_titulo(fanfic):
    titulo = fanfic.find("h4", attrs={"class":"heading"})
    if titulo != None:
        if titulo.a != None:
            return titulo.a.text
    return None
    
def get_dados_fanfic(fanfic, dados):
    fanfic = BeautifulSoup(str(fanfic), "html.parser")
    titulo = get_titulo(fanfic)
    if titulo != None:
        print(titulo)
        dados['total_fanfics'] = dados['total_fanfics'] + 1
        words = get_total_words(fanfic, dados)
        get_author(fanfic, dados)
        get_datetime(fanfic, dados, words)
        get_ships(fanfic, dados)
        get_fandoms(fanfic, dados, words)
        get_tags(fanfic, dados)
    
    
def get_total_words(fanfic, dados):
    words = fanfic.find("dd", attrs={"class":"words"})
    c_words = 0
    if words != None:
        c_words = int(words.text.replace(',', ''))
        dados['total_words'] = dados['total_words'] + c_words
    print(c_words)
    return c_words

def get_datetime(fanfic, dados, c_words):
    data = fanfic.find_all("p", attrs={"class":"datetime"})
    date = BeautifulSoup(str(data), "html.parser")
    ano = date.text.split(' ')[2].replace(',', '')
        
    if dados['fanfics_per_year'].get(ano) == None:
        dados['fanfics_per_year'][ano] = 1
    else:
        dados['fanfics_per_year'][ano] =  dados['fanfics_per_year'][ano] + 1
        
                

def get_ships(fanfic, dados):
    rel = fanfic.find_all("li", attrs={"class":"relationships"})
    for r in rel:
        ship = r.find(class_="tag").get_text()
        if dados['ships'].get(ship) == None:
            dados['ships'][ship] = 1
        else:
            dados['ships'][ship] = dados['ships'][ship]+1
            
    
def get_tags(fanfic, dados):
    li_tags = fanfic.find_all(class_="freeforms")
    for l in li_tags:
        li = BeautifulSoup(str(l), "html.parser")
        tag = li.find(class_="tag").text
        if dados['tags'].get(tag) == None:
            dados['tags'][tag] = 1
        else:
            dados['tags'][tag] = dados['tags'][tag] + 1
        
    
def get_fandoms(fanfic, dados, words):    
    fan = fanfic.find(class_="fandoms")
    fa = fan.find_all("a", attrs={"class":"tag"})
    for f in fa:
        be = BeautifulSoup(str(f), "html.parser")
        nome = re.sub('[^a-zA-Z0-9 ]', '', be.text)
        fandom = []
        if len(dados['fandoms']) > 0:
            fandom = [x for x in dados['fandoms'] if x['nome'] == nome]
        
        if len(fandom) == 0:
            dados['fandoms'].append({'nome':nome, 'fanfics': 1, 'wordCount':words})
        else:
            fandom = fandom[0]
            dados['fandoms'].remove(fandom)
            fandom['fanfics'] = fandom['fanfics']+1
            fandom['wordCount'] = fandom['wordCount']+words
            dados['fandoms'].append(fandom)
            
            
def get_export_excel(dados):
    status = pd.DataFrame(columns=['STATISTIC', 'TOTAL'])
    status = status.append({'STATISTIC':'WORD COUNT', 'TOTAL':dados['total_words']}, ignore_index=True)
    status = status.append({'STATISTIC':'FANFICS', 'TOTAL':dados['total_fanfics']}, ignore_index=True)
    #print(status)
    
    fandoms = pd.DataFrame(columns=['NAME', 'TOTAL FANFICS', 'TOTAL WORDS'])
    for fan in dados['fandoms']:
        fandoms = fandoms.append({'NAME': fan['nome'], 'TOTAL FANFICS':fan['fanfics'], 'TOTAL WORDS':fan['wordCount']}, ignore_index=True)
    fandoms = fandoms.sort_values(by=['TOTAL FANFICS'], ascending=False)
        
    ships = pd.DataFrame(columns=['SHIP', 'TOTAL FANFICS'])
    for ship in dados['ships']:
        if dados['ships'][ship] > 1:
            ships = ships.append({'SHIP':ship, 'TOTAL FANFICS':dados['ships'][ship]}, ignore_index=True)
    ships = ships.sort_values(by=['SHIP'], ascending=True)
    ships = ships.sort_values(by=['TOTAL FANFICS'], ascending=False)
    
    tags = pd.DataFrame(columns=['TAG', 'TOTAL FANFICS'])
    for tag in dados['tags']:
        tags = tags.append({'TAG':tag, 'TOTAL FANFICS': dados['tags'][tag]}, ignore_index=True)
    tags = tags.sort_values(by=['TOTAL FANFICS'], ascending=False)
    
    anos = pd.DataFrame(columns=['ANO', 'TOTAL FANFICS'])
    for ano in dados['fanfics_per_year']:
        anos = anos.append({'ANO':ano, 'TOTAL FANFICS': dados['fanfics_per_year'][ano]}, ignore_index=True)
    anos = anos.sort_values(by=['TOTAL FANFICS'], ascending=False)
    
    autores = pd.DataFrame(columns=['AUTOR', 'TOTAL FANFICS'])
    for author in dados['author']:
        autores = autores.append({'AUTOR':author, 'TOTAL FANFICS': dados['author'][author]}, ignore_index=True)
    autores = autores.sort_values(by=['TOTAL FANFICS'], ascending=False)
    
    nome_arquivo = str(pathlib.Path().absolute())+"\data.xlsx"    
        
    with pd.ExcelWriter(nome_arquivo) as writer:
        status.to_excel(writer, sheet_name="STATISTICS", index=False)
        fandoms.to_excel(writer, sheet_name="FANDOMS", index=False)
        ships.to_excel(writer, sheet_name="SHIPS", index=False)
        tags.to_excel(writer, sheet_name="TAGS", index=False)
        anos.to_excel(writer, sheet_name="ANOS", index=False)
        autores.to_excel(writer, sheet_name="AUTORES", index=False)
    return nome_arquivo    
        

warnings.simplefilter(action='ignore', category=FutureWarning)
dados = {'total_words': 0, 'fanfics_per_year':{}, 'fandoms':[], 'ships': {}, 'tags': {}, 'total_fanfics':0, 'author': {}}
retries = []

print('Write the username on ao3: ')
username = input()

total_paginas = get_total_paginas(username)

for x in range(2, total_paginas):
    get_conteudo_pagina(x, dados, retries)

retry(retries, dados)
arquivo = get_export_excel(dados)

print('File saved on '+arquivo)            
print("TOTAL WORD COUNT: "+str(dados['total_words']))
input("Press ENTER to exit")

