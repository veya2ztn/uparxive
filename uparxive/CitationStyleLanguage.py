from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON
from citeproc_styles import get_style_filepath
from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON
from citeproc_styles import get_style_filepath
from dataclasses import dataclass
import re
from typing import Dict,Any, Optional,List
 
@dataclass
class CitationStyleLanguage:
    issued: Optional[Any]
    author: Optional[List[dict]]
    title: Optional[str]
    container_title: Optional[str]
    volume: Optional[int]
    #year: Optional[int]
    page: Optional[str]
    type: Optional[str]
        
    def to_dict(self):
        out =  vars(self).copy()
        container_title = out.pop('container_title')
        out['container-title']=container_title
        return out
    
    def is_nan(self):
        return all([v is None for v in self.__dict__.values()])
    
    
    
    
    
    @staticmethod
    def get_issued(d):
        issued = d.get('issued',None)
        if not issued:
            year = CitationStyleLanguage.get_year(d)
            if year:
                return {'date-parts':[[year]]}
            return None
        if issued.get('date-parts',None):return None
        thelist = issued['date-parts']
        while isinstance(thelist,list):
            thelist = thelist[0]
        if thelist is None:
            return None
        return issued
    
    @staticmethod
    def get_author(d):
        author =  d.get('author',None)
        if author:
            should_author = []
            for a in author:
                if isinstance(a,dict):
                    if 'given' not in a and 'family' not in a:
                        if 'name' in a:
                            should_author.append({'given': "", 'family':a['name']})

                    elif 'given' in a and 'family' not in a:
                        should_author.append({'given': "", 'family':a['given']})
                    elif 'family' in a and 'given' not in a:
                        should_author.append(a|{'given':""})
                    else:
                        should_author.append({'given': a['given'], 'family':a['family']})
                elif isinstance(a,str):
                    splited_name = a.split()
                    if len(splited_name)==1:
                        given = ""
                        family= splited_name[0]
                    else:
                        given = " ".join(splited_name[:-1])
                        family = splited_name[-1]
                    should_author.append({'given': given, 'family':family})
            if len(should_author) ==0:
                should_author = None
            return should_author
        else:
            return None

    
    @staticmethod
    def get_title(d):
        return d.get('title',None)
    
    @staticmethod
    def get_container_title(d):
        journal_object =  d.get('container-title',None) or d.get('container_title',None) or d.get('journal',None) or d.get('booktitle')
        if isinstance(journal_object, dict):
            journal_name = journal_object['name']
        else:
            journal_name = journal_object
        if journal_name is not None:
            assert isinstance(journal_name, str ), f"journal_name is not a string, but {journal_name} for {d}"
        return journal_name
    
    @staticmethod
    def get_volume(d):
        volumn =  d.get('volume',None) or d.get('journal_volume',None)
        if not volumn and d.get('journal',None):
            volumn = d['journal'].get('volume',None)
        
        return volumn
    @staticmethod
    def get_year(d):
        return d.get('year',None)
    
    @staticmethod
    def get_page(d):
        page =  d.get('page',None) or d.get('journal_page',None)
        if not page and d.get('journal',None):
            page = d['journal'].get('number',None) or d['journal'].get('page',None)
        return page
    @staticmethod
    def get_type(d):
        ### you must have a type.
        return d.get('type',None) or d.get('publicationtypes',None) or "Article"

    @staticmethod
    def from_dict(d:Dict[str,str]):
        return CitationStyleLanguage(**{
            'issued': CitationStyleLanguage.get_issued(d),
            'author': CitationStyleLanguage.get_author(d),
            'title' : CitationStyleLanguage.resolve_list(CitationStyleLanguage.get_title(d)),
            'volume': CitationStyleLanguage.get_volume(d),
            #'year'  : CitationStyleLanguage.get_year(d),
            'page'  : CitationStyleLanguage.get_page(d),
            'type'  : CitationStyleLanguage.resolve_list(CitationStyleLanguage.get_type(d)),
            'container_title':CitationStyleLanguage.resolve_list(CitationStyleLanguage.get_container_title(d)),

        })
    @staticmethod
    def resolve_list(string):
        while isinstance(string, list):
            string = string[0]
        if isinstance(string,str):
            string = string.strip()
            if len(string) ==0 :
                string = None
        return string
    def __repr__(self):
        info = "\n".join([f"   {key} |-> {val}" for key, val in self.to_dict().items() if val is not None])
        return f"CSL:\n{info}"   
    
    @staticmethod
    def format_reference(style_name, bib_source):
        # Load the CSL style
        if 'id' not in bib_source: 
            bib_source ['id'] = 'temp'
            now_id = 'temp'
        else:
            now_id = bib_source['id']
        bib_json = CiteProcJSON([bib_source])
        #print(bib_json)
        style_path = get_style_filepath(style_name.lower())
        style = CitationStylesStyle(style_path)

        # Create the bibliography, passing the formatter for plain text output
        bibliography = CitationStylesBibliography(style, bib_json, formatter.plain)
        # The citation key of your entry
        citation = Citation([CitationItem(now_id)])
        bibliography.register(citation)

        # Generate the formatted bibliography entry
        return bibliography.bibliography()[0]
        
    def is_good_for_citation(self):
        if self.is_nan():return False
        if self.author is None:return False
        if self.container_title is not None and (
            self.author or (self.volume is not None and self.page is not None)
            ):return True
        return False
    
    def to_citation(self, size='short'):
        bib_json = self.to_dict()
        if size == 'short':
            if bib_json.get('title',None):
                bib_json.pop('title')
        
        ### for ieee render, when there are more than 3 authors, the `and` connection will lose one space, thus we add there to avoid
        if bib_json.get('author',None):
            for author_pool in bib_json['author']:
                if 'family' in author_pool:author_pool['family'] += " "
        
        bib_source = {k:v for k,v in bib_json.items() if v is not None}
        out = CitationStyleLanguage.format_reference('ieee', bib_source)
        out = re.sub(r'\s+', ' ', out[3:]).lstrip('. ') ### remove multi-space and remove the first 
        return out
    
     