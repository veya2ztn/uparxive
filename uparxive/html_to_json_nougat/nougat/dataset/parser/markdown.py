"""
Copyright (c) Meta Platforms, Inc. and affiliates.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""
from typing import Iterable, List, Optional, Tuple
import re
from uuid import uuid4
from ..utils import normalize_tex
from .document import *
from .latexml_parser import _clean_html_whitespace
from unidecode import unidecode

SUPERSCRIPT_MAP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
figure_regex = re.compile(r"\[(FOOTNOTE|FIGURE|TABLE)(.*?)\](.*?)\[END\1\]", re.S)
conv = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\^{}",
    "\\": r"\textbackslash{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
}
regex = re.compile(
    "|".join(
        re.escape(str(key)) for key in sorted(conv.keys(), key=lambda item: -len(item))
    )
)


def remove_trailing_whitespace(parts: List[str]) -> None:
    """Removes whitespace elements in list inplace"""
    for s in reversed(parts):
        if s.rstrip() == "":
            del parts[-1]
        else:
            break


def remove_line_breaks(parts: List[str]):
    out = []
    for s in parts:
        out.append(s.replace("\n", " "))
    return out


def leading_trailing_whitespace(
    parts: List[str],
) -> Tuple[List[str], List[str], List[str]]:
    """splits the list into three parts. The first and last return elements are made up only of whitespace

    Args:
        parts (List[str]): List to split.

    Returns:
        Tuple[List[str],List[str],List[str]]: Splitted list
    """
    lead = []
    trail = []
    out_slice = [None, None]
    for i, s in enumerate(parts):
        if s.strip() == "":
            lead.append(s)
            out_slice[0] = i + 1
        else:
            break
    for i, s in enumerate(reversed(parts)):
        if s.strip() == "":
            trail.append(s)
            out_slice[1] = -1 - i
        else:
            break
    return lead, parts[slice(*out_slice)], trail[::-1]


def latex_escape(string: str) -> str:
    return regex.sub(lambda match: conv[match.group()], string)


def is_empty(content: List) -> bool:
    """Used to determine if a Section is empty"""
    empty = True
    for part in content:
        if isinstance(part,dict):
            empty = False
            break
        if  len(part.strip()):
            empty = False
            break
    return empty
    
def format_element(
    element: Element, keep_refs: bool = False, structured:bool = False, latex_env: bool = False
) -> List[str]:
    """
    Formats a given Element into a list of formatted strings.

    Args:
        element (Element): The element to be formatted.
        keep_refs (bool, optional): Whether to keep references in the formatting. Default is False.
        latex_env (bool, optional): Whether to use LaTeX environment formatting. Default is False.

    Returns:
        List[str]: A list of formatted strings representing the formatted element.
    """
    if isinstance(element, TextElement):
        if latex_env:
            return [latex_escape(element.content)]
        else:
            return [element.content]
    if isinstance(element, Bold):
        parts = format_children(element, keep_refs, structured=False, latex_env=latex_env)
        if element.find_parent(Algorithm) is not None:
            return parts
        lead, text, tail = leading_trailing_whitespace("".join(parts))
        return [*lead, "**", *remove_line_breaks(text), "**", *tail]
    if isinstance(element, Italic):
        parts = format_children(element, keep_refs, structured=False, latex_env=latex_env)
        if element.find_parent(Algorithm) is not None:
            return parts
        lead, text, tail = leading_trailing_whitespace("".join(parts))
        return [*lead, "_", *remove_line_breaks(text), "_", *tail]
    if isinstance(element, PlaintextMath):
        return format_children(element, keep_refs, structured=False) + ["\n"]
    if isinstance(element, Paragraph):
        children = format_children(element, keep_refs, structured=structured, latex_env=latex_env)+ ["\n\n"]
        if structured:
            return [{"Paragraph": children}]
        else:
            return children
    if isinstance(element, TableCell):
        parts = format_children(element, keep_refs, structured=False, latex_env=latex_env)
        remove_trailing_whitespace(parts)
        if element.multirow is not None:
            parts.insert(0, "\\multirow{%i}{*}{" % (element.multirow))
            parts.append("}")
        if element.multicolumn is not None:
            parts.insert(
                0, "\\multicolumn{%i}{%s}{" % (element.multicolumn, element.spec)
            )
            parts.append("}")
        return parts
    if isinstance(element, TableRow):
        parts = []
        if element.hline_above:
            parts.append(element.hline_above + "\n")
        parts.extend(
            remove_line_breaks(
                format_iterator(element.cells, keep_refs, structured=False, latex_env=latex_env, join=" & ")
            )
        )
        parts.append(r" \\")
        parts.append((" " + element.hline_below).rstrip())
        return parts
    if isinstance(element, Tabular):
        parts = [
            "\\begin{tabular}",
            "{%s}\n" % element.get_table_spec(),
        ]
        parts.extend(format_iterator(element.rows, keep_refs, structured=False, latex_env=True, join="\n"))
        parts.append("\n\\end{tabular}\n")
        return parts
    if isinstance(element, Table):
        parts = [
            "[TABLE%s]\n\\begin{table}\n"
            % (str(uuid4())[:5] if element.id is None else ":" + str(element.id))
        ]
        parts.extend(format_children(element, keep_refs, structured=False, latex_env=latex_env))
        caption_parts = format_element(element.caption, keep_refs, structured=False, latex_env=latex_env)
        remove_trailing_whitespace(caption_parts)
        parts.append("\\end{table}\n")
        if len(caption_parts) > 0:
            parts.extend(caption_parts + ["\n"])
        parts.append("[ENDTABLE]\n\n")
        if structured:
            return [{'Table':parts}]
        else:
            return parts
    if isinstance(element, Figure):
        parts = format_element(element.caption, keep_refs, structured=False)
        remove_trailing_whitespace(parts)
        return (
            [
                "[FIGURE%s]\n"
                % (str(uuid4())[:5] if element.id is None else ":" + str(element.id))
            ]
            + parts
            + ["\n[ENDFIGURE]\n\n"]
        )
    if isinstance(element, SectionHeader):
        parts = ["# "]
        if element.id:
            parts.append(f"{element.id.upper()} ")
        if element.header:
            header = format_element(element.header, keep_refs, structured=False)
        else:
            header = format_iterator(element.children, keep_refs, structured=False)
        _, title, _ = leading_trailing_whitespace("".join(header))
        parts.append(title)
        parts.append("\n\n")
        return parts
    if isinstance(element, Section):
        children_parts = format_children(element, keep_refs, structured=structured)
        if is_empty(children_parts):
            children_parts = []

        if element.header:
            parts = [f"\n\n{'#'*element.hnum} "]
            _, title, _ = leading_trailing_whitespace( "".join(format_element(element.header, keep_refs, structured=False)))
            parts.append(title)
            parts.append("\n\n")
            header_content  = parts
        else:
            header_content  = []
        if structured:
            return  [{"Section": {"header": header_content, "children": children_parts}}]
        else:
            return header_content + children_parts
    if isinstance(element, Footnote):
        if element.id is not None:
            foot = f"\n[FOOTNOTE:{element.id}]Footnote {element.id}: "
        else:
            foot = "\n[FOOTNOTE:%s]Footnote: " % (str(uuid4())[:5])
        
        return [foot] + format_children(element, keep_refs, structured=False) + ["[ENDFOOTNOTE]\n\n"]
    if isinstance(element, ListContainer):
        items = []
        for item in element.items:
            itempart = format_element(item, keep_refs, False)
            try:
                itempart = "".join(itempart).strip().replace("\n", " ")
                itempart = (item.label,itempart,)
            except:
                for aaa in itempart:
                    print(aaa)
                #print(itempart[0].keys())
                raise
            items.append(itempart)
        
        
        parts = ["\n"]
        indent = "  " * max(element.level - 1, 0)
        for i, (label, item) in enumerate(items, 1):
            if label:
                bullet = label
            else:
                bullet = f"{i}." if element.ordered else "*"
            parts.append(f"{indent}{bullet} {item}\n")
        parts.append("\n")
        return parts
    if isinstance(element, Equation):
        # equation comprises of multiple displaystyle TeX formulas and optional equation label
        parts = []
        for child in element.children:
            if isinstance(child, LatexMath):
                tex = normalize_tex(
                    "".join(format_element(child, keep_refs, structured=False)).strip(" \n"), inline=False
                )
                parts.append(tex)
            else:
                text = "".join(format_element(child, keep_refs, structured=False))
                if text:
                    parts.append(text)
        lead, eqs, tail = leading_trailing_whitespace(parts)
        s = " ".join(eqs).replace(r"\] \[", " ")
        return [*lead, s, *tail]
    if isinstance(element, EquationList):
        parts = ["\n"]
        items = element.equations
        items = ["".join(format_element(item, keep_refs, structured=False)).rstrip() for item in items]
        items = [item + "\n" for item in items if item]
        if items:
            parts.extend(items)
            parts.append("\n")
        return parts
    if isinstance(element, Algorithm):
        parts = []
        items = element.lines
        items = ["".join(format_element(item, keep_refs, structured=False)).rstrip() for item in items]
        if element.inline:
            items = [item for item in items if item]
        else:
            items = [item + "\n" for item in items if item]
        if items:
            prepend = "`" if element.inline else "\n```\n"
            parts.append(prepend)
            parts.extend(items)
            append = "`" if element.inline else "```\n\n"
            parts.append(append)
        return parts
    if isinstance(element, DefinitionList):
        parts = ["\n"]
        if element.header is not None:
            parts.extend(format_element(element.header, keep_refs, structured=False))
            parts.append("\n")
        items = [
            "".join(format_element(item, keep_refs, structured=False)).rstrip() for item in element.items
        ]
        items = [item + "\n" for item in items if item]
        if items:
            parts.extend(items)
            parts.append("\n")
        return parts
    if isinstance(element, Definition):
        parts = []
        if element.term is not None:
            term = (
                "".join(format_element(element.term, keep_refs, False)).rstrip(" \n\t:") + ": "
            )
            # maths in wiki might be inside a definition without a term
            if term.strip() != ":":
                parts.append(term)
        if element.definition is not None:
            definition = "".join(format_element(element.definition, keep_refs, False)).rstrip()
            parts.append(definition)
        if parts:
            parts.append("\n")
        return parts
    if isinstance(element, LatexMath):
        parts = []
        if not element.inline:
            parts.append("\n\n")
        parts.append(normalize_tex(element.code, element.inline).strip())
        if not element.inline:
            parts.append("\n\n")
        return parts
    if isinstance(element, (Superscript, Subscript)):
        content = element.plaintext
        if content.strip().isdigit():
            script_map = (
                SUBSCRIPT_MAP if isinstance(element, Subscript) else SUPERSCRIPT_MAP
            )
            return [content.translate(script_map)]
        else:
            return format_children(element, keep_refs, structured=False)
    if isinstance(element, InlineRef):
        parts = format_children(element, keep_refs, structured=False)
        return parts
    return format_children(element, keep_refs, structured=False, latex_env=latex_env)

def format_iterator(
    iterator: Iterable,
    keep_refs: bool = False,
    structured:bool = False,
    latex_env: bool = False,
    join: Optional[str] = None,
) -> List[str]:
    """
    The `format_iterator` function takes an iterator and formats its elements, optionally joining them with a specified string.

    :param iterator: The `iterator` parameter is an iterable object that contains the elements to be formatted. It could be a list, tuple, set, or any other iterable object
    :type iterator: Iterable
    :param keep_refs: The `keep_refs` parameter is a boolean flag that determines whether references to other elements should be preserved in the formatted output. If `keep_refs` is set to `True`, the references will be included in the output. If `keep_refs` is set to `False` (default), the, defaults to False
    :type keep_refs: bool (optional)
    :param latex_env: The `latex_env` parameter is a boolean flag that determines whether the output should be formatted as LaTeX code. If `latex_env` is set to `True`, the output will be formatted using LaTeX syntax. If `latex_env` is set to `False` (default), the output will be, defaults to False
    :type latex_env: bool (optional)
    :param join: The `join` parameter is an optional string that specifies the delimiter to be used when joining the formatted elements of the iterator into a single string. If `join` is provided, it will be inserted between each formatted element. If `join` is not provided, the formatted elements will be returned as
    :type join: Optional[str]
    :return: The function `format_iterator` returns a list of strings.
    """
    parts = []
    for child in iterator:
        parts.extend(format_element(child, keep_refs, structured, latex_env))
        if join is not None:
            parts.append(join)
    if join is not None:
        parts = parts[:-1]
    return parts


def format_children(
    element: Element, keep_refs: bool = False, structured:bool = False, latex_env: bool = False, collections=None,
) -> List[str]:
    if element is None:
        return []
    children = format_iterator(element.children, keep_refs, structured, latex_env)
    return children

def text_beautiful(text):
    text = text.replace("\xa0", " ")  # replace non-breakable spaces
    text = re.sub(r" $", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n[\t ]*$", "\n", text, flags=re.MULTILINE)
    text = re.sub(r"(?<!\n) {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).lstrip()
    
    return text

def get_good_content(parts:list):
    new_part = []
    last_part= []
    for part in parts:
        if isinstance(part,dict):
            if len(last_part)>0:
                new_part.append(text_beautiful("".join(last_part)))
                last_part = []
            
            new_dict_part = {}
            for key, val in part.items():
                if key == 'Section':
                    new_dict_part[key] = {'header':get_good_content(part[key]['header']),
                                          'children':get_good_content(part[key]['children'])}
                else:
                    new_dict_part[key] = get_good_content(val)
            new_part.append(new_dict_part)

        else:
            last_part.append(part)
    if last_part:
        new_part.append(text_beautiful("".join(last_part)))
    return new_part

def format_document(
    doc: Document, keep_refs: bool = False
) -> Tuple[str, Dict[str, str]]:
    """
    The `format_document` function takes a `doc` object of type `Document` and a boolean `keep_refs` as input and returns a tuple containing the formatted text of the document and a dictionary of figures found in the document.

    :param doc: The `doc` parameter is of type `Document`, which is presumably a custom class representing a document
    :type doc: Document
    :param keep_refs: The `keep_refs` parameter is a boolean flag that determines whether to keep references in the formatted document or not. If `keep_refs` is set to `True`, the references will be included in the formatted document. If `keep_refs` is set to `False`, the references will be excluded, defaults to False
    :type keep_refs: bool (optional)
    :return: The function `format_document` returns a tuple containing two elements: a formatted text document and a dictionary of figures.
    """
    parts = []

    if doc.title:
        parts.extend([*format_element(doc.title), "\n"])
    parts.append("\n")
    parts.extend(format_children(doc, keep_refs))
    text = "".join(parts)
    text = text_beautiful(text)
    figures = {unidecode(m[0] + m[1]): m[2].strip() for m in figure_regex.findall(text)}
    text = figure_regex.sub(
        r"[\1\2][END\1]",
        text,
    )
    return text, figures

def format_document_structure(
    doc: Document, keep_refs: bool = False
) -> Tuple[str, Dict[str, str]]:
    
    parts = []

    if doc.title:
        parts.extend([*format_element(doc.title), "\n"])
    parts.append("\n")
    parts.extend(format_children(doc, keep_refs, structured=True))
    parts = get_good_content(parts)
    
    return parts

