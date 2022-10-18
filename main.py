# -*- coding: UTF-8 -*-
import os
from turtle import st
import cv2
import pytesseract
import re
from pdf2image import convert_from_path, convert_from_bytes
import requests
import getopt
import sys


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='|', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


def process_files(url, category, nummeration, db_id):
    # clear tmp and output folder
    for filename in os.listdir('./tmp'):
        os.remove('./tmp/' + filename)

    # for filename in os.listdir('./output'):
    #     os.remove('./output/' + filename)

    # download pdf
    print('Downloading data..')
    r = requests.get(url, allow_redirects=True)

    open('./tmp/questions.pdf', 'wb').write(r.content)

    # convert pdfs to img
    convert_from_path('./tmp/questions.pdf', output_folder='./tmp', fmt='jpeg')

    l = len(os.listdir('./tmp'))
    print('processing %s files..', l)
    printProgressBar(0, l, prefix='Progress:', suffix='Complete', length=50)
    p = 0
    i = int(db_id)

    for filename in os.listdir('./tmp'):
        q = open('./output/questions.sql', 'a')
        answerFile = open('./output/answers.sql', 'a')

        if filename == 'questions.pdf':
            continue
        printProgressBar(p + 1, l, prefix='Progress:',
                         suffix='Complete', length=50)

        # open image file
        img = cv2.imread('./tmp/' + filename)
        img = img[350:(img.shape[0] - 80), 250:img.shape[1]]

        result = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 1))
        remove_horizontal = cv2.morphologyEx(
            thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        cnts = cv2.findContours(
            remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            cv2.drawContours(result, [c], -1, (255, 255, 255), 5)
        img = result

        # vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
        # remove_vertical = cv2.morphologyEx(
        #     thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        # cnts = cv2.findContours(
        #     remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        # for c in cnts:
        #     cv2.drawContours(result, [c], -1, (255, 255, 255), 5)

        # cv2.imshow('image', result)
        # cv2.waitKey(0)

        # set tesseract dir
        # pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

        ###############################################################################

        # process with tesseract
        custom_config = r'--oem 3 --psm 6'
        t = pytesseract.image_to_string(img, config=custom_config, lang='deu')
        # print(t)
        # define pattern
        pattern = re.compile(
            r"(?:^|\n)([0-9]{4})(.*?(?:.(?=\n[0-9]{4})|$))", re.DOTALL)

        q_pattern = re.compile(
            r"(?:^|\n)([0-9]{4})(.*?(?:.(?=.ntwort)|$))", re.DOTALL)
        a_pattern = re.compile(
            r"(?:\n[0-9]\s|wort\s[0-9])(.*?(?:.(?=\n[0-9])|$))", re.DOTALL)
        aa_pattern = re.compile(r"(\]|\||X\s|x\s|\]\s)", re.DOTALL)

        j = int(nummeration)

        # extract questions and answers
        for match in re.finditer(pattern, t):
            # print(match.group(0))
            # print('-----------------')
            print(i)
            q_match = re.search(q_pattern, match.group(0))
            question_text = q_match.group(0).strip()[4:].strip()
            question_number = q_match.group(0).strip()[0:4].strip()
            print(question_number + ': ' + question_text)
            a_match = re.search(a_pattern, match.group(0))
            # print("A:" + a_match.group(0))
            q.write('INSERT INTO `questions` (`id`, `number`, `text`, `category_id`, `created_at`, `updated_at`, `old`) VALUES (' +
                    str(i) + ', ' + question_number + ', "' + question_text + '", ' + str(category) + ', NULL, NULL, 0);\n')

            for answer in re.finditer(a_pattern, match.group(0)):
                # print(answer.group(1))
                start = 0
                for _answer in re.finditer(aa_pattern, answer.group(1)):
                    [a, b] = _answer.span()
                    if b > start:
                        start = b
                if _answer:
                    # print(answer.group(1))
                    answer_text = answer.group(1)[start:].strip()
                    if answer_text != '':
                        answer_answer = (answer.group(1)[:start].find(
                            'X') > -1) | (answer.group(1)[:start].find('x') > -1)
                        print(str(answer_answer) +
                              ' || ' + answer_text)
                        answerFile.write('INSERT INTO `answers` (`id`, `question_id`, `text`, `answer`, `created_at`, `updated_at`) VALUES (NULL, ' +
                                         str(i) + ', "' + answer_text + '", ' + str(int(answer_answer == True)) + ', NULL, NULL);\n')

            i += 1
            j += 1
        # cv2.imshow('image', img)
        # cv2.waitKey(0)
        ###############################################################################
        p += 1
        q.close()
        answerFile.close()
        # clear tmp and output folder
    for filename in os.listdir('./tmp'):
        os.remove('./tmp/' + filename)

    # for filename in os.listdir('./output'):
    #     os.remove('./output/' + filename)
    exit()


def main(argv):
    # for filename in os.listdir('./tmp'):
    #     img = cv2.imread('./tmp/' + filename)
    #     img = img[350:(img.shape[0] - 80), 250:img.shape[1]]
    #     cv2.imshow('image', img)
    #     cv2.waitKey(0)
    # exit()

    url = ''
    category = 0
    nummeration = 0
    db_id = 0
    try:
        opts, args = getopt.getopt(
            argv, 'hu:c:n:d:', ['url=', 'category=', 'nummeration=', 'db_id='])
        print('sad')
    except getopt.GetoptError:
        print('main.py -u <url> -c <category> -n <nummeration> -d <db_id>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('main.py -u <url> -c <category> -n <nummeration> -d <db_id>')
            sys.exit()
        elif opt in ("-u", "--url"):
            url = arg
        elif opt in ("-c", "--category"):
            category = arg
        elif opt in ("-n", "--nummeration"):
            nummeration = arg
        elif opt in ("-d", "--db_id"):
            db_id = arg
    process_files(url, category, nummeration, db_id)


if __name__ == "__main__":
    main(sys.argv[1:])
