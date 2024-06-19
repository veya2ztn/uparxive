### CopyRight: https://github.com/KatagiriSo/rd_expand_newcommand_in_latex/blob/main/rd_expand_newcommand_in_latex.py

import sys

"""
rd_expand_newcommand_in_latex.py
copyrigth 2023 KatagiriSo
This software is released under the MIT License, see LICENSE.
If you use this software, I would be grateful if you could refer to the following.
"""

# read file
def readFile(path):
    with open(path) as f:
        return f.read()

# input file path from args
def readArgFile():
    args = sys.argv
    if len(args) != 2:
        print('invalid args')
        sys.exit()
    return readFile(args[1])

# write text to file
def writeFile(path, text):
    with open(path, mode='w') as f:
        f.write(text)

# get first left bracket index
def findFirstBracket(text:str, left:str) -> int:
    return text.find(left)

# get last right bracket index
def findLastBracket(text:str, left:str, right:str) -> int:
    if (text.find(left) == -1):
        return -1
    index = 0
    leftCount = 0
    while True:
        target = text[index]
        if target == left:
            leftCount += 1
        elif target == right:
            leftCount -= 1
            if leftCount == 0:
                return index
        if index == len(text) - 1:
            return -1
        
        if leftCount < 0:
            return -1
        index += 1

# get text in bracket
def textInBracket(text: str, left:str, right:str) -> str:
    index = 0
    while True:
        target = text[index]
        if target == left:
            break
        if target == " ":
            index += 1
            continue
        return ""

    return text[index + 1: findLastBracket(text, left, right)]

def textInBracket_curly(text: str) -> str:
    return textInBracket(text, "{", "}")

def textInBracket_square(text: str) -> str:
    return textInBracket(text, "[", "]")

def textInBracket_paren(text: str) -> str:
    return textInBracket(text, "(", ")")

class Newcommand:
    def __init__(self, name: str, param: str, display: str):
        self.name = name
        self.param = param
        self.display = display

    def apply(self, inputTexts: list[str]) -> str:
        # change #1 #2 #3 to inputTexts
        display = self.display
        for i, inputText in enumerate(inputTexts):
            display = display.replace('#' + str(i + 1), inputText)
        return display    

def deleteComment(text: str) -> str:
    while True:
        index = text.find("%")
        if index == -1:
            break
        index2 = text.find("\n", index)
        if index2 == -1:
            index2 = len(text)
        text = text[:index] + text[index2:]
    return text

def getNewCommands(text: str) -> list[Newcommand]:
    text = deleteComment(text)
    commands = []
    while True:
        # \newcommand{command}[num]{text}
        commandText = "\\newcommand"
        commandTextIndex = text.find(commandText)
        if commandTextIndex == -1:
            break
        text = text[commandTextIndex + len(commandText):]
        # name
        name = textInBracket_curly(text)
        text = text[len(name) + 2:]
        # param
        param = textInBracket_square(text)
        if param == "":
            param = 0
        else:
            text = text[len(param) + 2:]
  
        # display
        display = textInBracket_curly(text)
        text = text[len(display) + 2:]
        commands.append(Newcommand(name, param, display))

    return commands    

# split text to defText and body
def splitTextBeginDocument(text: str) -> tuple[str, str]:
    index = text.find("\\begin{document}")
    if index == -1:
        return [text, ""]
    index2 = text.find("\\end{document}")
    if index2 == -1:
        return [text, ""]
    return [text[:index], text[index:index2 + len("\\end{document}")]]

def applayNewCommand(text: str, command: Newcommand) -> str:
    index = 0
    output = ""
    if command.param == 0:
        while True:
            index = text.find(command.name, index)
            if index == -1:
                break
            postCommandChr = text[index + len(command.name)]
            if postCommandChr.isalpha() or postCommandChr.isdigit():
                index += 1
                continue

            output += text[:index]
            output += command.display
            index += len(command.name)
            text = text[index:]
            index = 0
    else:
        while True:
            index = text.find(command.name, index)
            if index == -1:
                break
            postCommandChr = text[index + len(command.name)]
            if postCommandChr.isalpha() or postCommandChr.isdigit():
                index += 1
                continue
            # get parma_num
            param_num = command.param
            # get {} in command
            inputTexts = []
            # next step 
            startIndex = index
            index += len(command.name)
            if text[index] != "{":
                #print("{ is not exist", command.name, text[index:])
                index += 1
                continue
            index_end = index
            for i in range(int(param_num)):
                inputText = textInBracket_curly(text[index_end:])
                inputTexts.append(inputText)
                index_end += len(inputText) + 2


            # apply
            output += text[:startIndex]
            output += command.apply(inputTexts)
            text = text[index_end:]
            index = 0

    output += text
    return output
  


        

       
def applyNewCommands(text: str, commands: list[Newcommand]) -> str:
    # command.name sort for lognest
    commands.sort(key=lambda x: len(x.name), reverse=True)
    for command in commands:
        text = applayNewCommand(text, command)
    return text



def testFindLastBracket():
    text = "{b{c}d}e"
    print(findLastBracket(text, "{", "}"), 6)
    text = "{b{c}d"
    print(findLastBracket(text, "{", "}"), -1)
    text = "{b{c}d}e{f{g}h}i"
    print(findLastBracket(text, "{", "}"), 6)

def testTextInBracket():
    text = "{b{c}d}e"
    print(textInBracket_curly(text), "b{c}d")
    text = "{b{c}d"
    print(textInBracket_curly(text), "")
    text = "{b{c}d}e{f{g}h}i"
    print(textInBracket_curly(text), "b{c}d")
    text = "[23]d"
    print(textInBracket_square(text), "23")
    text = "{ge}s"
    print(textInBracket_square(text), "")

def testNewCommands(text: str):
    commands = getNewCommands(text)
    for command in commands:
        print("name", command.name)
        print("param", command.param)
        print("display", command.display)

def testApplyNewCommands(text: str):
    commands = getNewCommands(text)
    text = applyNewCommands(text, commands)
    print(text)

def testApplyNewCommands2():
    text = readArgFile()
    defText, body = splitTextBeginDocument(text)
    commands = getNewCommands(defText)
    testLaTex = """
\\be{
S = \\int^t_{t_0} dt\\ L(t) \\\\
= \\sum^N_{i=1} L(t_i) \\ep \\\\
\\ep = t_{i+1} - t_i \\\\
= \\sum^N_{i=1} \\{ \\f{1}{2} m ( \\f{q_i - q_{i-1}}{\ep} )^2 - V(q_i)  \\} \\ep \\\\
where\\ q_i := q(t_i)
}
"""
    result = applyNewCommands(testLaTex, commands)
    print(result)

def test():
    text = readArgFile()
    # testFindLastBracket()
    # testTextInBracket()
    testNewCommands(text)
    # testApplyNewCommands(text)
    testApplyNewCommands2()

# main
def main():
    text = readArgFile()
    defText, body = splitTextBeginDocument(text)
    commands = getNewCommands(defText)
    text = applyNewCommands(body, commands)
    print(defText + text)

if __name__ == "__main__":
    main()
  

