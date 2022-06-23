import threading
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from datetime import datetime
import re
from random import seed
from random import randint
import base64
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
import shelve

# for Random usage
seed(1)

# encryption
salt = os.urandom(16)
kdf_user = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
    backend=default_backend()
)

#  Regex - will use to find the month out of the string in hebrew as well as in english
my_reg = re.compile(r'[א-תa-zA-Z]')  #

months = {'בינואר': 1, 'בפברואר': 2, 'במרץ': 3,
          'באפריל': 4, 'במאי': 5, 'ביוני': 6,
          'ביולי': 7, 'באוגוסט': 8, 'בספטמבר': 9,
          'באוקטובר': 10, 'בנובמבר': 11, 'בדצמבר': 12,
          'January': 1, 'February': 2, 'March': 3,
          'April': 4, 'May': 5, 'June': 6,
          'July': 7, 'August': 8, 'September': 9,
          'October': 10, 'November': 11, 'December': 12
          }


def open_fb(user_name, user_pass, driver):
    driver.minimize_window()
    driver.get("https://facebook.com")
    email_element = driver.find_element_by_id('email')
    email_element.send_keys(user_name)
    pass_element = driver.find_element_by_id('pass')
    pass_element.send_keys(user_pass)
    pass_element.submit()

    # checks if login was successes
    try:
        WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.ID, 'pass')))
        return False
    except StaleElementReferenceException:
        pass
    return True


def fb_scraper(phone_num):
    # Open driver
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(chrome_options=options)

    # open client info from data
    client = shelve.open(r'C:\MyPythonScripts\birthdayBot\client')
    user_name, user_pass, key = client[phone_num]
    f = Fernet(key)
    user_name = f.decrypt(user_name).decode()
    user_pass = f.decrypt(user_pass).decode()

    # Login to FB
    if open_fb(user_name, user_pass, driver) is False :
        return "לא הצלחתי להתחבר :("
    # scrapping information
    driver.get("https://www.facebook.com/events/birthdays/")
    import time
    time.sleep(1)
    birthdays = []
    i = j = 1
    flag = False
    while True:
        while True:
            try:
                try:
                    bday = driver.find_element_by_xpath(                                                        # j == box                    i == birthDay
                        f'/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[{j}]/div/div/div/div[2]/div[{i}]/div/div[2]/div[1]/div[1]/div[3]/span')
                except NoSuchElementException:
                    bday = None

                name = driver.find_element_by_xpath(                                                        # j == box                    i == UserName
                    f'/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[{j}]/div/div/div/div[2]/div[{i}]/div/div[2]/div[1]/div[1]/div[1]/a/h2/span')
                try:
                    age = driver.find_element_by_xpath(                                                       # j == box                    i == Age
                        f'/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[{j}]/div/div/div/div[2]/div[{i}]/div/div[2]/div/div[2]/span')

                    age = age.text
                except NoSuchElementException:
                    age = 'לא צוין'
                flag = True
                # birthdays today
                if bday is None:
                    birthdays.append(f'ל{name.text} יש יום הולדת היום! ({age})')

                # upcoming birthdays + passed
                else:
                    # using regular expression to deconstruct the string English or hebrew
                    date = str(bday.text).split(' ')
                    date = date[0] + date[1]
                    day = re.findall("\d", date)
                    day = ''.join(day)
                    month = my_reg.findall(date)
                    month = ''.join(month)
                    # checks if the date is already passed or not
                    if int(day) < datetime.now().day and months[month] == datetime.now().month:
                        birthdays.append(f'ל {name.text} היה יום הולדת ב:' + '\n' + f'{bday.text} ({age})')
                    elif int(day) > datetime.now().day and months[month] < datetime.now().month:
                        birthdays.append(f'ל {name.text} היה יום הולדת ב:' + '\n' + f'{bday.text} ({age})')
                    else:
                        birthdays.append(f'ל {name.text} יש יום הולדת ב:' + '\n' + f'{bday.text} ({age})')

                i += 1


            except NoSuchElementException:
                break
        j += 1
        i = 1

        #assumption: if there are 2 exceptions in a row that means there are no more elements left to scrap
        if flag is False:
            break
        flag = False

    # merging result to string
    result = ''
    result += '\n\n'.join(birthdays)
    driver.quit()
    return result


# check if the user is in the shelve file -> if he already sign up
def in_data(phone_num):
    client = shelve.open(r'C:\MyPythonScripts\birthdayBot\client')
    if phone_num not in client:
        client.close()
        return False
    client.close()
    return True


# sign up the user and store data in shelve file - only after the password and email were verified as correct
def sign_up(phone_num, text):
    user = text.splitlines()
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(chrome_options=options)

    # check if email and password are correct by login into fb
    try:
        result = open_fb(user[1], user[2], driver)
        if result is False:
            driver.close()
            return False
    except Exception:
        return None
    driver.close()
    user = [user[1].encode(), user[2].encode()]

    key = base64.urlsafe_b64encode(kdf_user.derive(user[1]))
    f = Fernet(key)

    user = [f.encrypt(user[0]), f.encrypt(user[1]), key]
    client = shelve.open(r'C:\MyPythonScripts\birthdayBot\client')
    client[phone_num] = user
    client.close()
    return True


app = Flask(__name__)


def message_result(number, client):
    message = client.messages.create(
        from_='whatsapp:+14155238886',
        body=fb_scraper(number),
        to=number
    )

#user menu method
@app.route('/whatsapp', methods=['POST', 'GET'])
def whatsapp():
    my_twilio = open(r'C:\MyPythonScripts\birthdayBot\my_twilio_account.txt')
    account_sid, auth_token = my_twilio.readlines()
    my_twilio.close()
    client = Client(account_sid, auth_token)
    number = request.form['From']
    message_body = request.form['Body']
    resp = MessagingResponse()

    text_back = " "
    if message_body.__contains__('ימי הולדת'):

        if in_data(number) is False:
            text_back = 'נתחבר זריז לפייס לפני?' + '\n' + 'הזן "הרשמה" עם מייל וסיסמא - הכל בשורות נפרדות',

        else:
            text_back = 'קבלתי, שב.י בנוח בעודי עושה את העבודה...'
            threading.Thread(target=message_result, args=(number, client)).start()

    elif message_body.__contains__('הרשמה'):

        if in_data(number) is True:
            text_back = 'את.ה כבר רשומ.ה יא מצחיקול.ית!'
        else:
            result = sign_up(number, message_body)
            if result is True:
                text_back = 'סגור! את.ה בפנים',
            if result is None:
                text_back = 'בטוח שהזנת נכון את הפרטים?'
            if result is False:
                text_back = 'אופס, כנראה מייל או סיסמא לא תקינים - נסה.י שוב'

    elif message_body.__contains__('נכון'):

        if randint(0, 1) == 0:
            text_back = 'אני מסכים איתך!'

        else:
            text_back = 'את.ה טועה ומטעה, חוצפן.ית!'

    elif message_body.__contains__('עובד'):
        text_back = 'בכל פקודת "ימי הולדת", בוט יתחבר לפייסבוק שלך, יחלץ משם את המידע וישלח לכאן.' + '\n' + 'דיי מגניב, לא?'

    elif message_body.__contains__('כן'):
        text_back = 'שמח שגם את.ה חושב.ת ככה'

    else:
        text_back = 'אהלן!, אני בוט-הולדת ואני כאן כדי לרענן את זכרונך' + '\n' + r'כל שעליך לעשות הוא לרשום: "ימי הולדת" ותקבל את רשימת האירועים מהפייסבוק שלך'

    client.messages.create(
        from_='whatsapp:+14155238886',
        body=text_back,
        to=number
    )
    return str(resp)


if __name__ == '__main__':
    app.run(port=5000, debug=True)
