import os
import cv2 
import pytesseract
import re
from pdf2image import convert_from_path, convert_from_bytes
import requests
import getopt
import sys

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
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
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def process_files(url, category, nummeration, db_id):
    # clear tmp and output folder
    for filename in os.listdir('./tmp'):
        os.remove('./tmp/' + filename)

    for filename in os.listdir('./output'):
        os.remove('./output/' + filename)   

    # download pdf
    print('Downloading data..')
    r = requests.get(url, allow_redirects=True)

    open('./tmp/questions.pdf', 'wb').write(r.content)

    #convert pdfs to img
    convert_from_path('./tmp/questions.pdf', output_folder='./tmp', fmt='jpeg')

    l = len(os.listdir('./tmp'))
    print('processing %s files..', l)
    printProgressBar(0, l, prefix = 'Progress:', suffix = 'Complete', length = 50)
    p = 0
    # process files
    for filename in os.listdir('./tmp'):
        q = open('./output/questions.sql', 'a')
        a = open('./output/answers.sql', 'a')

        if filename == 'questions.pdf':
            continue
        printProgressBar(p + 1, l, prefix = 'Progress:', suffix = 'Complete', length = 50)

        # open image file
        img = cv2.imread('./tmp/' + filename)

        # set tesseract dir
        pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

        # process with tesseract
        custom_config = r'--oem 3 --psm 6'
        t = pytesseract.image_to_string(img, config=custom_config, lang='deu')

        #define pattern
        pattern = re.compile(r"(?<=Richtige Antwort)(.*?)(?=Gültig Y)", re.DOTALL)

        q_pattern = re.compile(r"(?<=Frage )(.*?)(?=Antwort [0-9])", re.DOTALL)
        a_pattern = re.compile(r"(?<=Antwort [0-9] )(.*?)(?=Antwort [0-9]|\Z)", re.DOTALL)


        i = int(db_id)
        j = int(nummeration)

        # extract questions and answers
        for match in re.finditer(pattern, t):
            q_match = re.search(q_pattern, match.group(0))
            q.write('INSERT INTO `questions` (`id`, `number`, `text`, `category_id`, `created_at`, `updated_at`, `old`) VALUES (' + str(i) + ', ' + str(j) + ', "' + q_match.group(0).strip() +'", ' + str(nummeration) + ', NULL, NULL, 0);\n')
            for answer in re.finditer(a_pattern, match.group(0)):
                answer = answer.group(0).split('|')
                if len(answer) > 1:
                    a.write('INSERT INTO `answers` (`id`, `question_id`, `text`, `answer`, `created_at`, `updated_at`) VALUES (NULL, ' + str(i) + ', "' + answer[0].strip() +'", 0, NULL, NULL);\n')
                else:
                    a.write('INSERT INTO `answers` (`id`, `question_id`, `text`, `answer`, `created_at`, `updated_at`) VALUES (NULL, ' + str(i) + ', "' + answer[0].strip() +'", 1, NULL, NULL);\n')
            i += 1
            j += 1
        
        p += 1
        q.close()
        a.close()
        # clear tmp and output folder
    for filename in os.listdir('./tmp'):
        os.remove('./tmp/' + filename)

    for filename in os.listdir('./output'):
        os.remove('./output/' + filename)  
    exit()

def main(argv):
   url = ''
   category = 0
   nummeration = 0
   db_id = 0
   try:
      opts, args = getopt.getopt(argv,'hu:c:n:d:',['url=','category=','nummeration=','db_id='])
   except getopt.GetoptError:
      print ('main.py -u <url> -c <category> -n <nummeration> -d <db_id>')
      sys.exit(2) 
   for opt, arg in opts:
      if opt == '-h':
         print ('main.py -u <url> -c <category> -n <nummeration> -d <db_id>')
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
