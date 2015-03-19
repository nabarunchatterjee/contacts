from flask import Flask,render_template,request
from wtforms import Form, TextField, FileField, validators
from werkzeug import secure_filename
import os
import redis
import csv
import ast

ALLOWED_EXTENSIONS = set(['csv'])


app = Flask(__name__)


def allowed_file(filename):
    return '.' in filename and \
               filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


class UploadForm(Form):
    filename = TextField('Contacts File', [validators.required()])
    image = FileField('Browse')

class SearchForm(Form):
    contact = TextField('Contacts Name/Phone Number', [validators.required()])

@app.route('/', methods=['POST', 'GET'])
def upload():
    message = ''
    form = UploadForm(request.form)
    s_form = SearchForm()
    if request.method == 'POST' :
        file_wrapper = request.files['image']
        if file_wrapper and allowed_file(file_wrapper.filename):
            filename = secure_filename(file_wrapper.filename)
            save_to_redis(file_wrapper)
            message = 'Contacts in file %s have been saved'%file_wrapper.filename
        else:
            message = "Please upload a csv file"
    return render_template('index.html', form = form,message = message, s_form = s_form)

@app.route('/search', methods=['POST'])
def search():
    result_list = []
    s_form = SearchForm(request.form)
    form = UploadForm()
    print search_contact(s_form.contact.data)
    search_results = search_contact(s_form.contact.data)
    return render_template('index.html', s_form = s_form,form = form , results = search_results )

def save_to_redis(fh):
    rserv = redis.Redis('localhost')
    contacts_data = csv.reader(fh)
    for contact in contacts_data:
        print contact        
        key = '_'.join([contact[0],contact[3]])
        print key
        value = {
            'Name' : contact[0],
            'Work_phone' : contact[1],
            'Home_phone' : contact[2],
            'Mobile1' : contact[3],
        }
        mob_index = 2
        if len(contact) > 4:
            for ph_num in contact[4:]:
                value['Mobile' + str(mob_index)] = ph_num
                mob_index += 1
        print value
        print rserv.set(key,value)
        value = {}
        for ph_num in contact[1:]:
            if ph_num:
                print rserv.set(ph_num,key)

def search_contact(search_string):
    rserv = redis.Redis('localhost')
    results = []
    try:
        number = int(search_string)
    except ValueError:
        search_string += '*'

    keys = rserv.keys(search_string + '*')
    for key in keys:
        result = ast.literal_eval(rserv.get(key))
        results.append(result)
    return results


if __name__ == "__main__":
#    app.run(host='0.0.0.0')
    app.run(debug=True)
