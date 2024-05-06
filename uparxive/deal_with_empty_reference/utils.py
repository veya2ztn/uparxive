import re
def extract_bib_files(tex_content):
    # Define the regular expression for the bibliography pattern
    bib_pattern = r'\\bibliography{([^}]+)}'
    
    # Search using the regular expression
    matches = re.findall(bib_pattern, tex_content)
    
    # matches is a list of all occurrences of the bib_pattern
    if matches:
        # Split the result to get individual bib files
        bib_files = [bib.strip() for bib in matches[0].split(',')]
        return bib_files
    else:
        return []
def get_directory_before_analysis(path):
    # Use a regular expression to match the path up to "analysis."
    match = re.search(r'^(.*/)(analysis\.[^/]*)/', path)
    if match:
        # Return the directory part of the path, excluding the "analysis.xxxxx" part
        return match.group(1).rstrip('/')
    else:
        # If no "analysis.xxxxx" part is found, return None or the original path
        return None
    
def bbl_file(bib_name):
    return bib_name+'.bbl' if not bib_name.endswith('.bbl') else bib_name
def bib_file(bib_name):
    return bib_name+'.bib' if not bib_name.endswith('.bib') else bib_name