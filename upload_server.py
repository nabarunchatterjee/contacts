from flask import Flask,render_template,request
from wtforms import Form, TextField, FileField, validators
from werkzeug import secure_filename
import os
import redis
import csv
import ast
import uuid

ALLOWED_EXTENSIONS = set(['csv'])

rserv = redis.Redis('localhost')

app = Flask(__name__)


def allowed_file(filename):
    return '.' in filename and \
               filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


class UploadForm(Form):
    filename = TextField('Contacts File', [validators.required()])
    image = FileField('Browse')

class SearchForm(Form):
    contact = TextField('Enter Name/Phone Number')

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

@app.route('/search', methods=['GET','POST'])
def search():
    result_list = []
    s_form = SearchForm(request.form)
    form = UploadForm()
    if request.method == 'GET':
        return render_template('index.html', s_form = s_form,form = form )
    
    search_results = search_contact(s_form.contact.data)
    message = str(len(search_results)) + ' contact(s) found'
    if len(search_results):
        return render_template('index.html', s_form = s_form,form = form , results = search_results, message = message )
    else:
        return render_template('index.html', s_form = s_form,form = form , message = message )

@app.route('/update', methods=['GET','POST'])
def update():
    message = ''
    print request.form
    s_form = SearchForm()
    form = UploadForm()
    r_form = Form(request.form)
    if request.method == 'POST':
        message = 'Contact(s) updated'
        print 'Contact(s) updated'
        if request.form['Update'] == 'Update':
            update_records(request.form)
        else:
            delete_records(request.form)
    return render_template('index.html', s_form = s_form,form = form ,message = message )

def update_records(r_form):
    keys = []
    for field in r_form:
        if r_form[field] == 'on':
            keys.append(field)
    for key in keys:
        new_record = {}
        for field in r_form:
            print field
            if field != key and field != 'Update':
                record_name = field.split('-')[0]
                fieldname = field.split('-')[1]
                if  record_name == key :
                    new_record[fieldname] = r_form[field]
        old_record = rserv.get(key)
        print key
        print old_record
        old_record = ast.literal_eval(old_record)
        if (old_record['Name'] != new_record['Name']) or ( old_record['Mobile1'] != new_record['Mobile1']):
            delete_key(key)
            name = "_".join(new_record['Name'].split())
            update_key( name + '_' + new_record['Mobile1'], new_record)
        else:
            for attr,val in old_record.iteritems():
                if attr != 'Name' or attr != 'Mobile1':
                    if val != new_record[attr]:
                        rserv.delete(attr)
            rserv.set(key,new_record)

def delete_key(key):
    rec = ast.literal_eval(rserv.get(key))
    for attr,value in rec.iteritems():
        if attr != 'Name':
            rserv.delete(value)
    rserv.delete(key)

def update_key(key,value):
    rserv.set(key,value)
    for attr,val in value.iteritems():
        if attr != 'Name':
            rserv.set(val,key)

def delete_records(form):
    keys = []
    for field in form:
        if form[field] == 'on':
            keys.append(field)
    for key in keys:
        delete_key(key)
    
                
def save_to_redis(fh):
    rserv = redis.Redis('localhost')
    contacts_data = csv.reader(fh)
    for contact in contacts_data:
        name = "_".join(contact[0].split())
        key = '_'.join([name,contact[3]])
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
        print key
        rserv.set(key,value)
        value = {}
        for ph_num in contact[1:]:
            if ph_num:
                rserv.set(ph_num,key)

def search_contact(search_string):
    rserv = redis.Redis('localhost')
    results = []
    try:
        number = int(search_string)
        key = rserv.keys(search_string)
        if key:
            rec_key = rserv.get(key[0])
            results.append((rec_key,ast.literal_eval(rserv.get(rec_key))))
        return results
    except ValueError:
        search_string += '*'
        keys = rserv.keys(search_string)
        for key in keys:
            result = ast.literal_eval(rserv.get(key))
            results.append((key,result))
#        print results
#        print results[0][0]
        return results


if __name__ == "__main__":
#    app.run(host='0.0.0.0')
    app.run(debug=True)
