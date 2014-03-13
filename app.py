# ## Meetupslides
# ## https://github.com/teraom/meetupslides
import time
import os
import json
import urlparse
from datetime import datetime, date
import random
from flask import Response

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import redis
import redisco
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import sendgrid

import settings
from models import *

from flask.ext.admin import Admin
from admin import *

import boto
from boto.dynamodb2.table import Table

from default_meetups import DEFAULT_MEETUPS

from redis_completion import RedisEngine


################################
####### init and CONFIG ########
################################


app = Flask(__name__)
app.config.from_object('settings.Config')
app.secret_key = app.config['APP_SECRET_KEY']
# admin = Admin(app, index_view=Dashboard)
admin = Admin(app, name='Meetup Slides Admin')
# admin.index_view = Dashboard

# Load from config
REDIS_HOST = app.config['REDIS_HOST']
REDIS_PORT = app.config['REDIS_PORT']
REDIS_DB = app.config['REDIS_DB']
AWS_KEY = app.config['AWS_KEY']
AWS_SECRET_KEY = app.config['AWS_SECRET_KEY']
BUCKET_NAME = app.config['BUCKET_NAME']
LOGOS_BUCKET_NAME = app.config['LOGOS_BUCKET_NAME']
SENDGRID_USERNAME = os.environ.get('SENDGRID_USERNAME', '')
SENDGRID_PASSWORD = os.environ.get('SENDGRID_PASSWORD', '')

redis_url = os.environ.get('REDISTOGO_URL', None)
if redis_url:
    redis_url = urlparse.urlparse(redis_url)
    redisco.connection_setup(host=redis_url.hostname, port=redis_url.port, db=0, password=redis_url.password)
    
    autocomplete_redis_client = redis.Redis(host=redis_url.hostname, port=redis_url.port, db=0, password=redis_url.password)
    autocomplete_engine = RedisEngine(autocomplete_redis_client)
else:
    redisco.connection_setup(host='localhost', port=6379, db=0)
    
    autocomplete_redis_client = redis.Redis(host='localhost', port=6379, db=0)
    autocomplete_engine = RedisEngine(autocomplete_redis_client)    

ALLOWED_EXTENSIONS = set(('txt', 'pdf', 'ppt', 'pptx', 'zip', 'tar', 'rar'))
ALLOWED_IMAGE_EXTENSIONS = set(('png', 'jpg'))

# Admin views
admin.add_view(Dashboard(name='Dashboard'))

################################
####### helper methods #########
################################

def allowed_file(filename, extensions):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in extensions


def secure_filename(filename):
    return filename


def upload_to_s3(filename, bucket_name, object_id, ext, object_prefix='object'):
    conn = S3Connection(AWS_KEY, AWS_SECRET_KEY)
    bucket = conn.get_bucket(bucket_name)
    k = Key(bucket)
    k.key = '{0}_{1}.{2}'.format(object_prefix, object_id, ext)
    # print 'key:', k.key
    k.set_contents_from_filename(filename)
    k.make_public()
    # print 'Done upload'
    filename = get_s3_filename(bucket_name, k.key)
    return filename


def get_s3_filename(bucket_name, key):
    return 'https://s3.amazonaws.com/{0}/{1}'.format(bucket_name, key)


@app.template_filter('convert_to_image_id')
def image_filter(meetup_id):
    return str(10000 + int(meetup_id) % 70)[-4:] + ".jpg"  # since there are around 70 images

@app.template_filter('convert_to_local_image')
def convert_to_local(meetup_logo):
    
    if meetup_logo:
        try:
            local_file = meetup_logo.split("/")[-1]                                                
            return local_file
        except Exception as e:
            print e

         

def get_validated_date(d):
    try:
        return datetime.strptime(d, '%m/%d/%Y')
    except:
        return date.today()


################################
####### All router methods #####
################################
'''
@app.route('/')
def index():
    posts = get_recent_posts()
    meetups = get_top_metups()
    return render_template('index.html', posts=posts, meetups=meetups)
'''

@app.route('/')
def index():
    return render_template('home.html')

# @app.route('/meetups')
# def meetups():
#    meetups = get_meetups()    
#    return render_template('meetups.html', meetups=meetups)


@app.route('/meetups')
def meetups():
    meetups = get_meetups()
    exposed_fields = ['id', 'website', 'city', 'name', 'slide_count', 'logo', 'homepage', 'desc']
    
    result = []
    
    for meetup in meetups:
        m = {}
        for exposed_field in exposed_fields:
            m[exposed_field] = getattr(meetup, exposed_field)
        result.append(m)
        
    return Response(json.dumps(result), mimetype='application/json')


@app.route('/autocomplete/meetups', methods=['GET'])
def autocomplete_meetups():
    meetup_name = request.args.get('term', 'No Name')
    meetups = autocomplete_engine.search(meetup_name)
    
    result = []
    for meetup in meetups:
        d = json.loads(meetup)
        result.append({"id": d["id"], "label":d["name"], "value":d["name"]})
    
    if len(result) == 0:
        result = [{"id": 0, "label":"No results. Please contact us to add your meetup!", "value":"No results. Please contact us to add your meetup!"}]
    return Response(json.dumps(result), mimetype='application/json')
    
    

@app.route('/meetup/add', methods=['GET', 'POST'])
def meetup_add():
    if request.method == 'GET':
        return render_template('add_meetup.html')
    name = request.form.get('meetup_name', 'No Name')
    city = request.form.get('meetup_city', 'No City')
    desc = request.args.get('desc', '')
    website = request.args.get('website', '')
    ajax = request.form.get('ajax', 0)
    m = Meetup(name=name, city=city, desc=desc, website=website)
    saved = m.save()
    autocomplete_engine.store_json(m.id, m.name, {
                                                  "name":m.name + " - " + m.city,
                                                  "id":m.id
                                                })        
    logo = request.files['logo']
    if logo and allowed_file(logo.filename, ALLOWED_IMAGE_EXTENSIONS):
        filename = secure_filename(logo.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logo.save(filepath)
        ext = filename.rsplit('.', 1)[1]
        s3_filename = upload_to_s3(filepath, LOGOS_BUCKET_NAME, m.id, ext, object_prefix='logo')
        m.logo = s3_filename
        m.save()
    if not ajax:
        return redirect(url_for('meetup', meetup_id=m.id))
    # if this is an ajax call, return json response
    if saved:
        return jsonify(name=name, city=city, id=m.id)
    else:
        return jsonify(error=True)


@app.route('/meetup/<meetup_id>')
def meetup(meetup_id):
    meetup = get_meetup(meetup_id)
    posts = get_post_reverse(meetup_id)
    return render_template('new_meetup.html', meetup=meetup, posts=posts)


@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'GET':
        meetups = get_meetups()
        selected_meetup_id = request.args.get('meetup_id', 0)
        return render_template('add.html', meetups=meetups, selected_meetup_id=selected_meetup_id)
    title = request.form.get('title', 'No Title')
    desc = request.form.get('desc', 'No desc')
    author = request.form.get('author', 'A developer')
    user_id = request.form.get('user_id', 0)
    post_date = request.form.get('post_date')
    post_date = get_validated_date(post_date)
    meetup_id = int(request.form.get('meetup_id', 0))
    p = Post(title=title, desc=desc, user_id=user_id, meetup_id=meetup_id, author=author, post_date=post_date)
    saved = p.save()
    post_id = p.id
    # store s3 file path
    slides = request.files['slides']
    if slides and allowed_file(slides.filename, ALLOWED_EXTENSIONS):
        filename = secure_filename(slides.filename)
        # try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        slides.save(filepath)
        ext = filename.rsplit('.', 1)[1]
        s3_filename = upload_to_s3(filepath, BUCKET_NAME, post_id, ext, object_prefix='slide')
        os.remove(filepath)
        p.slides = [s3_filename]
        p.s3_filename = s3_filename
        p.save()
        # except Exception as e:
        #     print 'Exception'
    # print 'Post saved?', saved
    flash('Add new post.')
    return redirect(url_for('post', post_id=post_id))


@app.route('/post/<post_id>', methods=['GET', 'POST'])
def post(post_id):
    if request.method == 'GET':
        post = get_post(post_id)
        return render_template('post.html', post=post)
    # else  - POST
    # update_post()
    return render_template('post.html', post=post)


@app.route('/search')
def search():
    pass


@app.route('/user/<user_id>')
def user(user_id):
    pass


# TODO - research flask login
@app.route('/login')
def login():
    """docstring for login"""
    pass


@app.route('/logout')
def logout():
    """docstring for logout"""
    pass


@app.route('/register')
def register():
    """docstring for register"""
    pass


@app.route('/profile')
def profile():
    """docstring for profile"""
    pass


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'GET':
        return render_template('contact.html')
    name = request.form.get('name', None)
    email = request.form.get('email', None)
    subject = request.form.get('subject', None)
    content = request.form.get('content', None)
    m = Message(name=name, email=email, subject=subject, content=content)
    saved = m.save()
    if not saved:
        flash('Something went wrong! Could not send message.')
        return redirect(url_for('contact'))
    try:
        s = sendgrid.Sendgrid(SENDGRID_USERNAME, SENDGRID_PASSWORD, secure=True)
        message_body = ''
        fields = ['name', 'email', 'content']
        for f in fields:
            item = '{0}: {1}\n'.format(f, getattr(m, f))
            message_body += (item)
        message = sendgrid.Message("admin@meetupslides.com", subject, message_body,
            "<p>{0}</p>".format(message_body.replace('\n', '<br/>')))
        message.add_to("star@bharad.net", "Bharad bharad")
        s.web.send(message)
        flash('Thanks! We will get back to you shortly')
        return redirect(url_for('index'))
    except Exception as e:
        print 'Exception sending message:', e
        flash('Something went wrong! Could not send message.')
        return redirect(url_for('contact'))


@app.route('/about')
def about():
	return render_template('about.html')


@app.route('/jobs')
def jobs():
    jobs = get_jobs()
    return render_template('jobs.html')


def save_post(request):

    # Save all metadata associated with this file
    metadata = json.loads(request.form['metadata'])
    speaker_name = metadata["speaker_name"]
    presentation_title = metadata["presentation_title"]
    presentation_description = metadata["presentation_description"]
    presentation_date = metadata["presentation_date"]
    post_type = metadata["post_type"]
    meetup_id = int(metadata["meetup_id"])

    title = presentation_title
    desc = presentation_description
    author = speaker_name
    user_id = request.form.get('user_id', 0)
    post_date = get_validated_date(presentation_date)

    p = Post(title=title, desc=desc, user_id=user_id, meetup_id=meetup_id, author=author, post_date=post_date, post_type=post_type)
    p.save()
    post_id = p.id
    
    # Atleast one slide was saved.
    # OK to showcase this meetup in homepage
    m = get_meetup(meetup_id)
    m.homepage = True
    m.slide_count = get_slide_count(meetup_id)
    m.save()

    return p


@app.route('/add_slide', methods=['POST'])
def add_slide():            
    user_id = request.form.get('user_id', 0) # Dummy 
    
    post_url = request.form.get('post_url', None)
    speaker_name = request.form.get('speaker_name', None)
    presentation_title = request.form.get('presentation_title', None)
    presentation_description = request.form.get('presentation_description', None)
    presentation_date = get_validated_date(request.form.get('presentation_date', None))
    meetup_id = int(request.form.get('meetup_id', None))
    post_type = request.form.get('post_type', None)
    
    p = Post(title=presentation_title, desc=presentation_description, user_id=user_id, meetup_id=meetup_id, author=speaker_name, post_date=presentation_date, post_type=post_type, post_url=post_url)
    p.save()    
    
    return render_template('_posts.html', **{"posts": [p]})
    
    
@app.route('/file-upload', methods=['POST'])
def file_upload():        
    slides = request.files['file']
    if slides and allowed_file(slides.filename, ALLOWED_EXTENSIONS):
        filename = secure_filename(slides.filename)
        # try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        slides.save(filepath)
        ext = filename.rsplit('.', 1)[1]
        
        post = save_post(request)  # Save the post in redis after upload
        s3_filename = upload_to_s3(filepath, BUCKET_NAME, post.id, ext, object_prefix='slide')
        
        # Save the s3 file location to the post
        post.s3_filename = s3_filename
        post.type = "file"
        post.save() 
        
        os.remove(filepath)    
        
        return render_template('_posts.html', **{"posts": [post]})
    else:
        return jsonify(result=False)    
    
    
    '''
    conn = boto.dynamodb2.connect_to_region(
        'us-east-1',
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )   
    
    slides = Table('meetup_slides', connection=conn)
    slides.put_item(data={
     'speaker_name' : speaker_name,
     'presentation_title' : presentation_title,
     'presentation_description' : presentation_description,
     'timestamp' : str(datetime.now()) + str(random.random())
    })    
    '''
    
    return jsonify(result=True)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 0))
    
    # Prefill meetups with a get or create
    for meetup in DEFAULT_MEETUPS:        
        m = Meetup.objects.get_or_create(**meetup)
        m.save()
        autocomplete_engine.store_json(m.id, m.name, {
                                                      "name":m.name + " - " + m.city,
                                                      "id":m.id
                                                      })
        
    if port:
        app.debug = False
        app.run(host='0.0.0.0', port=port)
    else:
        app.debug = False
        app.run()

