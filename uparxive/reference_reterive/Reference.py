
import re
from lxml import etree
from typing import List, Optional
import argparse
from dataclasses import dataclass
import dataclasses
from dateutil import parser
from fuzzywuzzy import fuzz
import unidecode
import re
import unidecode
from fuzzywuzzy import fuzz
import os,json
from nameparser import HumanName
from typing import Dict
import numpy as np

from typing import Any
#--------------------------------------------------#
def read_jsonl(path):
    if os.path.exists(path):
        with open(path,'r') as f:
            out = json.load(f)
    else:
        out=[]
    return out
def read_linefile(path):
    if os.path.exists(path):
        with open(path,'r') as f:
            out = [t.strip() for t in f]
    else:
        out = []
    return out
def save_jsonl(path, data):
    with open(path,'w') as f:
        json.dump(data, f)
def save_linefile(path, data):
    with open(path,'w') as f:
        for line in data:
            f.write(line+'\n')

def check_is_args(args):
    if dataclasses.is_dataclass(args):return True
    if isinstance(args, argparse.Namespace):return True
    return False

def get_print_namespace_tree(namespace, indent=0):
    result = ""
    namespace = vars(namespace) if check_is_args(namespace) else namespace
    for key, value in namespace.items():
        line = ' ' * indent
        if isinstance(value, dict) or check_is_args(value):
            line += key + "\n"
            line += get_print_namespace_tree(value, indent + 4)
        else:
            line += f"{key:30s} ---> {value}\n"
        result += line
    return result 

def print_namespace_tree(namespace):
    print(get_print_namespace_tree(namespace))

def update_weights_one( name, cand_str, ref_str, cand_set, ref_set,weight=1):
    cand = re.search('(?<!\d)\d+(?!\d)', str(cand_str))
    ref = re.search('(?<!\d)\d+(?!\d)', str(ref_str))
    if cand is not None and ref is not None:
        cand = cand.group(0)
        ref = ref.group(0)
        cand_set[name] = weight
        ref_set[name] = 0
        if cand == ref:
            ref_set[name] = weight
    else:
        cand_set[name] = weight/2
        ref_set[name] = 0
            
def extract_four_digit_number(input_string):
    pattern = r'\b\d{4}\b'  # \b is a word boundary, which ensures we are matching a standalone number
    match = re.search(pattern, input_string)
    if match:
        return match.group(0)  # Returns the matched 4-digit number as a string
    else:
        return None  # No match found

from collections.abc import MutableMapping
def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str ='.') -> MutableMapping:
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, UniqueID):
            v = v.to_dict()
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

@dataclass
class UniqueIDBase:
    doi: Optional[str] = None
    openalex: Optional[str] = None
    pubmed: Optional[str] = None
    semopenalex: Optional[str] = None
    arxiv: Optional[str] = None
    pmc: Optional[str] = None
    dblp: Optional[str] = None
    mag: Optional[str] = None
    pii: Optional[str] = None
    acl: Optional[str] = None
    
    def is_nan(self):
        return all([not bool(v) for v in self.__dict__.values()])
    
    def to_dict(self):
        return {k:v for k,v in vars(self).items() if v is not None}
    
@dataclass
class UniqueID(UniqueIDBase):

    def is_same(a:UniqueIDBase, b:UniqueIDBase):
        pool_a = a.to_dict()
        pool_b = b.to_dict()
        for key, val_a in pool_a.items():
            if key in pool_b:
                val_b = pool_b[key]
            else:
                nkey = UniqueID.unique_key(key)
                if nkey in pool_b:
                    val_b = pool_b[nkey]
                else:
                    continue
            if val_a == val_b:return True
        return  False

    @staticmethod
    def unique_key(key):
        key = key.lower().replace('unique_id','').replace('_',"").replace('externalids','').strip('.|-').strip()
        if key.endswith('id'): key = key[:-2]
        if key in ['pubmed', 'pm']:
            return 'pubmed'
        elif key in ['pubmedcentral', 'pmc']:
            return 'pmc'
        return key
    
    @staticmethod
    def format_unique_val(k, v):
        if k == 'openalex':
            v = v.replace('https://openalex.org/','')
        elif k == 'semopenalex':
            v = v.replace('https://semopenalex.org/work/','')
        elif k == 'pubmed':
            v = v.replace('https://pubmed.ncbi.nlm.nih.gov/','')
        else:
            v = v
        return v
            

    @staticmethod
    def from_dict(d:Dict[str,str]):
        accepted_keys = vars(UniqueIDBase())
        ids = {}
        first_level_key_pair = [[UniqueID.unique_key(origin_key), origin_key] for origin_key in d.keys()]
        for new_key, origin_key in first_level_key_pair:
            if new_key in accepted_keys:
                ids[new_key] = UniqueID.format_unique_val(new_key,d[origin_key])
        
        if 'ids' in d:
            ids = ids|UniqueID.from_dict(d['ids']).to_dict()

        if 'externalids' in d:
            ids = ids|UniqueID.from_dict(d['externalids']).to_dict()
        return UniqueID(**ids)
    
    def __repr__(self):
        info = "\n".join([f"   {key} |-> {val}" for key, val in self.to_dict().items() if val is not None])
        return f"Paper:\n{info}"   



@dataclass
class ReferenceBase:
    unique_id: Optional[UniqueID]
    title: Optional[str]
    author: Optional[str]
    journal: Optional[str]
    journal_volume: Optional[int]
    journal_page: Optional[int]
    year: Optional[int]
    publisher: Optional[str]
    content: Optional[str]
    def to_dict(self):
        return vars(self)
    
    def to_flatten_dict(self):
        out = flatten_dict(self.to_dict())
        
        return out
    
    
@dataclass
class Reference(ReferenceBase):     
    
    @staticmethod
    def load_from_dict(pool):
        unique_id      = Reference.get_unique_id(pool)
        title          = Reference.resolve_list(Reference.get_title(pool))
        author         = Reference.get_author(pool)
        journal        = Reference.resolve_list(Reference.get_journal(pool))
        journal_volume = Reference.resolve_list(Reference.get_journal_volume(pool))
        journal_page   = Reference.resolve_list(Reference.get_journal_page(pool))
        year           = Reference.resolve_list(Reference.get_year(pool))
        publisher      = Reference.resolve_list(Reference.get_publisher(pool))
        content        = Reference.resolve_list(Reference.get_content(pool))

        return Reference(unique_id, title, author,  journal, journal_volume, journal_page, year, publisher, content)
    
    @staticmethod
    def resolve_list(string):
        while isinstance(string, list):
            if len(string) == 0:
                return None
            string = string[0]
            
        if isinstance(string,str):
            string = string.strip()
            if len(string) ==0 :
                string = None
        return string

    @staticmethod
    def get_unique_id(pool):
        ids = (pool.get('unique_id', None) or pool.get('externalids',None))
        
        if ids:
            if 'CorpusId' in ids:del ids['CorpusId']
            return UniqueID.from_dict(ids)
        
        ids = {}
        for key,val  in pool.items():
            if 'unique_id.' not in key and key not in ['doi', 'DOI', 'arxiv', 'arxiv_id']: continue
            key = key.replace('unique_id.','')
            ids[key] = val
        if ids:
            return UniqueID.from_dict(ids)
        
    @staticmethod
    def get_title(pool):
        title =  pool.get('title', None)
        title = Reference.resolve_list(title)
        if title and len(title.split()) <= 1 and len(title)<3: ### title should be more than two character. 
            title = None
        return title
    @staticmethod
    def format_a_human_name(given_name=None,family_name=None):
        if given_name and family_name:
            name = HumanName(" ".join([given_name, family_name]).strip(), initials_format="{first} {middle}")
            name = name.initials() + ' ' + name.last
        elif not given_name and family_name:
            name = family_name
        elif given_name and not family_name:
            
            if len(given_name.split()) == 1:
                name = given_name
            else:
                name = HumanName(full_name=given_name, initials_format="{first} {middle}")
                name = name.initials() + ' ' + name.last
        else:
            name = ""
        return name

    @staticmethod
    def get_author(pool):
        author = None
        if 'author' in pool and pool['author']:
            if isinstance(pool['author'], list):
                author = []
                for author_i in pool['author'][:3]:
                    if isinstance(author_i,dict):
                        given_name = (author_i.get("given", None) or 
                                      author_i.get("first", None) or 
                                      author_i.get('forename',None) or 
                                      author_i.get('name',None))
                        family_name= author_i.get("family", None) or author_i.get("last", None) or author_i.get('surname',None)
                        name = Reference.format_a_human_name(given_name=given_name,family_name=family_name )
                        if author_i.get('literal',None):
                            names = re.split(r'\s*,\s*|\s*and\s*', author_i['literal'])
                            author.extend(names)
                            continue
                    elif isinstance(author_i, str):
                        name = Reference.format_a_human_name(given_name=author_i,family_name=None )
                    else:
                        raise NotImplementedError
                    if name:
                        author.append(name)
                if len(author)==0 and len(pool['author'])>0:
                    if 'title' not in pool:
                        print(f"no author find for this pool {pool}")
                #author = ','.join(author)
            elif isinstance(pool['author'], dict):
                name = " ".join([pool['author'].get("given", ""), pool['author'].get("family", "")]).strip()
                name = Reference.format_a_human_name(given_name=name,family_name=None )
                author = [name]
            elif isinstance(pool['author'], str):
                name = Reference.format_a_human_name(given_name=pool['author'],family_name=None )
                author = [name]
            else:
                raise ValueError(f"Author type not supported: {type(pool['author'])} for {pool['author']}")
        if author is None and 'author.0' in pool:
            author = [pool[key] for key in ['author.0','author.1','author.2'] if key in pool]
        
        if 'authors' in pool and pool['authors']:
            author=[]
            if isinstance(pool['authors'],list):
                assert isinstance(pool['authors'][0],dict)
                for author_pool in pool['authors']:
                    author.append(Reference.format_a_human_name(given_name=author_pool['name'],family_name=None ))
            elif isinstance(pool['authors'],str):
                author.extend(pool['authors'].split(','))
            else:
                raise NotImplementedError(f"author type not supported {type(pool['authors'])}")
        
        if isinstance(author, list) and len(author) ==0 : author = None
        return author
       
    @staticmethod
    def get_journal(pool):
        journal = (pool.get('journal', None) or pool.get('jname', None) or 
                   pool.get('journal_name', None) or pool.get('container-title', None) or 
                   pool.get('j_name', None))
        if not journal and 'imprint' in pool and pool['imprint'] and 'journal' in pool['imprint']:
            journal = pool['imprint']['journal']
        journal = (journal or pool.get('publisher', None))
        if isinstance(journal, dict):
            journal = journal['name']
            

        return journal

    @staticmethod
    def get_journal_volume(pool):
        volume = (pool.get('volume', None) or pool.get('jvol', None) or 
                   pool.get('journal_volume', None) or 
                   pool.get('j_vol', None))
        if not volume and 'imprint' in pool and pool['imprint'] and 'volume' in pool['imprint']:
            volume = pool['imprint']['volume']
        if not volume:
            journal = (pool.get('journal', {}))
            if isinstance(journal, dict): volume = journal.get('volume', None)

        return volume
    
    @staticmethod
    def get_journal_page(pool):
        page = (pool.get('page', None) or pool.get('jpage', None) or 
                   pool.get('journal_page', None) or 
                   pool.get('j_page', None))
        if not page and 'imprint' in pool and pool['imprint'] and 'page' in pool['imprint']:
            page = pool['imprint']['page']
        if not page:
            journal = (pool.get('journal', {}))
            if isinstance(journal, dict): page = journal.get('pages', None)

        return page
    
    @staticmethod
    def get_year(pool):
        year =  (pool.get('year', None) or pool.get('date', None))
        if not year and 'issued' in pool and pool['issued'] and 'date-parts' in pool['issued']:
            date_part = pool['issued']['date-parts']
            while isinstance(date_part, list):
                date_part = date_part[0] 
            year = date_part
        if not year and 'imprint' in pool and pool['imprint'] and 'date' in pool['imprint']:
            date_part = pool['imprint']['date']
            while isinstance(date_part, list):
                date_part = date_part[0] 
            year = date_part

        if year:
            try:
                year = parser.parse(str(year)).year
            except:
                year = extract_four_digit_number(str(year))
        return year
    
    @staticmethod
    def get_publisher(pool):
        publisher = pool.get('publisher', None)
        if not publisher and 'imprint' in pool and pool['imprint'] and 'publisher' in pool['imprint']:
            publisher = pool['imprint']['publisher']
            publisher = publisher
        return publisher
    @staticmethod
    def get_content(pool):
        contents = []
        for key in ['content', 'short_content' , 'long_content']:
            content =  pool.get(key, None)
            if content:contents.append(content)
        if len(contents)==0:
            return None
        return contents

    @staticmethod
    def get_norm_attr(string):
        string = (string or "")
        string = str(string)
        return unidecode.unidecode(string).lower().strip()
    

    def addtition_information(old_ref:ReferenceBase, new_ref:ReferenceBase):
        #### firstly deal with None value
        old_pool = old_ref.to_dict()
        new_pool = new_ref.to_dict()
        total_key = vars(old_ref).keys()
        new_information = {}
        for key in total_key:
            if old_pool.get(key, None) is None and new_pool.get(key, None) is not None:
                new_information[key] = new_pool[key]
            elif old_pool.get(key, None) is not None and new_pool.get(key, None) is not None:
                continue
                if key in ['unique_id']:continue
                a = old_pool[key]
                b = new_pool[key]
                if key == 'journal':
                    a = a.lower()
                    b = b.lower()
                    if b not in a:
                        print(f"{key}: a={a} b={b}")
                else:
                    if a !=b :
                        print(f"{key}: a={a} b={b}")

        return new_information

    def __repr__(self):
        info = "\n".join([f"{key} |-> {val}" for key, val in self.to_dict().items() if val is not None])
        return f"Reference:\n{info}"     
          
        
def decide_whether_add_the_ref_into_the_database(ref:Reference):
    if ref.title:return True
    if ref.author and ref.journal and ref.year: return True
    if ref.journal and (ref.journal_volume and ref.journal_page) and ref.year:return True
    return False        



def similarity_structured(candidate:Reference, ref:Reference):
    # weights for generalized jaccard similarity
    cand_set = {}
    str_set = {}

    # weights of volume
    if ref.journal_volume:update_weights_one('volume', candidate.journal_volume,ref.journal_volume, cand_set, str_set)
    
    if ref.journal_page:update_weights_one('page', candidate.journal_page, ref.journal_page, cand_set, str_set)
    
    # weights for year
    if ref.year:
        update_weights_one('year', candidate.year, ref.year, cand_set, str_set)
        if 'year' in str_set and str_set['year'] < 1 and candidate.year  and ref.year:
            year1 = int(candidate.year) ## some reference will refresh the year, thuse the year may large than origin
            year2 = int(ref.year)
            if ref.author is None and ref.title is None:
                str_set['year'] = int(year1==year2) 
            else:
                if abs(year1 - year2) < 2:
                    str_set['year'] = 1
                elif year1 > year2:
                    str_set['year'] = 1
            
    # weights for title
    if ref.title:
        a = Reference.get_norm_attr(candidate.title).lower()
        b = Reference.get_norm_attr(ref.title).lower()
        cand_set['title'] = 1
        str_set['title'] = fuzz.ratio(a, b) / 100

    # weights for container-title
    if ref.journal:
        b = Reference.get_norm_attr(ref.journal).lower()
        cand_set['ctitle'] = 1
        aa = Reference.get_norm_attr(candidate.journal).lower()
        score = fuzz.ratio(aa, b)
        for a in aa.split(','): 
            score = max(score, fuzz.ratio(a, b))
        str_set['ctitle'] = score/ 100

    # weights for volume-title
    if ref.journal_volume:
        a = Reference.get_norm_attr(candidate.journal_volume)
        b = Reference.get_norm_attr(ref.journal_volume)
        title_ratio = fuzz.ratio(a, b)
        
        a = Reference.get_norm_attr(candidate.journal)
        ctitle_ratio = fuzz.ratio(a, b)
        cand_set['vtitle'] = 1
        str_set['vtitle'] = max(title_ratio, ctitle_ratio) / 100

    # weights for author
    if ref.author:
        if candidate.author:
            cand_set['author'] = 1
            author_score = []
            for ref_author in ref.author:
                b = Reference.get_norm_attr(ref_author)
                scores = []
                for candidate_author in candidate.author:
                    a = Reference.get_norm_attr(candidate_author)
                    scores.append(fuzz.ratio(a, b)/ 100)
                author_score.append(np.max(scores))
                
            
            str_set['author'] = np.mean(author_score)
        else:
            cand_set['author'] = 0
            str_set['author']  = 0
    
    escape_score = 0
    can_content = candidate.content
    ref_content = ref.content
    if can_content and ref_content:
        if isinstance(can_content, str):can_content = can_content.split('|')
        if isinstance(ref_content, str):ref_content = ref_content.split('|')
        content_score = []
        for can_c in can_content:
            for ref_c in ref_content:
                content_score.append(fuzz.ratio(ref_c, can_c)/ 100)
        content_score = max(content_score)
        escape_score = content_score
    
    if 'title' in str_set and str_set['title']>=0.98:
        return 1
    if ref.title and candidate.title:
        if len(ref.title) > len(candidate.title):
            shorter_title = candidate.title.lower()
            longer_title  = ref.title.lower()
        else:
            shorter_title = ref.title.lower()
            longer_title  = candidate.title.lower()
        if longer_title.endswith(shorter_title) or longer_title.startswith(shorter_title):
            return 1
        return 0 ## title is different
    if ref.author and cand_set['author']:
        if str_set['author']<0.5:
            return escape_score
        
    support = 0
    for k, v in str_set.items():
        if k == 'year' and v > 0 and cand_set[k] > 0:
            support = support + 1
        if k == 'volume' and v == 1 and cand_set[k] > 0:
            support = support + 1
        if k == 'title' and v > 0.9:
            support = support + 1
        if k == 'ctitle' and v > 0.6:
            support = support + 1
        if k == 'vtitle' and v > 0.6:
            support = support + 1
        if k == 'author' and v > 0.9:
            support = support + 1
        if k == 'page' and v == 1 and cand_set[k] > 0:
            support = support + 1
    
    if ref.author is None and ref.title is None:
        ## then it must be a full journal ref, other wise it fails
        if ref.journal is not None and ref.journal_volume is not None and ref.journal_page is not None:
            pass
        else:
            return escape_score ## how do you identify it since no title and not journal?
    
    if support < 2:
        #print(f" fact check fail due to too less bingo={support}")
        return escape_score
    
    # generalized Jaccard similarity
    # print(cand_set)
    # print(str_set)
    num = sum([min(cand_set[n], str_set[n]) for n in cand_set.keys()])

    den = sum([max(cand_set[n], str_set[n]) for n in cand_set.keys()])
    
    if den == 0:
        return 1
    return num/den



if __name__ == '__main__':
    query_pool = {'author': 'R. B. Behunin,B. H. Hu',
    'jvol': '43',
    'jpage': '12001',
    'jname': 'Journal of Physics A: Mathematical and Theoretical',
    'year': '2010'}
    result_pool = {'externalids.DOI': '10.1088/1751-8113/43/1/012001',
    'externalids.ArXiv': '0907.3212',
    'title': 'Nonequilibrium Casimir–Polder force in non-stationary systems',
    'year': 2009,
    'jname': 'j phys math theor, journal of physics a, journal of physics a: mathematical and theoretical, j phys a',
    'jpages': '012001',
    'jvol': '43',
    'author': 'R. Behunin,B. Hu'}

    candidate = Reference.load_from_dict(result_pool)
    ref = Reference.load_from_dict(query_pool)

    print(candidate)
    print('======================')
    print(ref)
    print('======================')
    print(similarity_structured(candidate,ref))