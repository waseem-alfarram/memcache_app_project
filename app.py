from flask import Flask, render_template, request, flash
from flask_mysqldb import MySQL
from datetime import datetime
from werkzeug.utils import secure_filename
from cache import Cache
from time import perf_counter
from datetime import datetime, timedelta
import os, threading

UPLOAD_FOLDER = 'static/destination_images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


app = Flask(__name__)


app.config['MYSQL_HOST'] = 'memcache-database.cz0uhkdlsnct.us-east-1.rds.amazonaws.com'
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = '12345678'
app.config['MYSQL_DB'] = 'Memcache_Database'
app.secret_key = "my-secret-key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


mysql = MySQL(app)
cache = Cache(500, "random-replacement")
hitsNo = 0
missNo = 0
reqs = 0


def updateRecord():
    global hitsNo, missNo, reqs
    hitRate = 0
    missRate = 0
    if reqs !=0 :
        hitRate = (hitsNo/reqs)*100
        missRate = (missNo/reqs)*100

    with app.app_context():
        curr_Date = datetime.now()
        currentDate = curr_Date.strftime('%Y-%m-%d %H:%M:%S')
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO memory_statistics(memory_configuration_seq, items_no, items_size, requests_no, hits_no, miss_no, hit_rate, miss_rate, date_created) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (1, cache.length(), cache.size(), reqs, hitsNo, missNo, hitRate, missRate, currentDate))
        mysql.connection.commit()
        cursor.close()
    hitsNo = 0
    missNo = 0
    reqs = 0


def counter():
    t1_start = perf_counter()
    send = True
    while True:
        now = perf_counter()
        if (int(now)-int(t1_start)) % 5 == 0 and send:
            updateRecord()
            send = False
        elif (int(now)-int(t1_start)) % 5 != 0:
            send = True


t1 = threading.Thread(daemon=True, target=counter, args=())
t1.start()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=['POST', 'GET'])
@app.route("/add_image/", methods=['POST', 'GET'])
def add_image():
    if request.method == 'POST':
        my_key = request.form['key']
        name = request.files['name']
        if name and allowed_file(name.filename):
            filename = secure_filename(name.filename)
            name.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            img_size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT image_key FROM image")
            keys = cursor.fetchall()
            key_exist = 'false'
            for key in keys:
                if int(my_key) == int(key[0]):
                    key_exist = 'true'
                    break
            if key_exist == 'false':
                cursor.execute("INSERT INTO image(image_key, image_name, size) VALUES(%s, %s, %s)", (my_key, name.filename, img_size))
                flash('Image is successfully uploaded!')
            else:
                cursor.execute("SELECT image_name FROM image WHERE image_key=%s", [my_key])
                filename = cursor.fetchone()
                os.unlink(os.path.join(app.config['UPLOAD_FOLDER'], filename[0]))
                cursor.execute("DELETE FROM image WHERE image_key=%s", [my_key])
                cursor.execute("INSERT INTO image(image_key, image_name, size) VALUES(%s, %s, %s)", (my_key, name.filename, img_size))
                flash('Image is successfully updated!')
            mysql.connection.commit()
            cursor.close()
        else:
            flash('(png, jpg, jpeg, gif) files only!')
    return render_template("add_image.html")


@app.route("/show_image/", methods=['POST', 'GET'])
def show_image():
    global hitsNo, missNo, reqs
    reqs += 1
    img_src = '/static/temp.jpg'
    if request.method == 'POST':
        key = request.form['key']
        if key in cache.data:
            hitsNo += 1
            [src, ext] = cache.get(key)
            img_src = "data:image/+" + ext + ";base64," + src.decode()
        else:
            missNo += 1
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT image_name FROM image WHERE image_key = %s", [key])
            file = cursor.fetchone()
            mysql.connection.commit()
            cursor.close()
            if file:
                filename = secure_filename(file[0])
                cache.put(int(key), filename)
                img_src = '/' + os.path.join(app.config['UPLOAD_FOLDER'], filename)
                flash('Image is successfully retrieved!')
    return render_template("show_image.html", image_src = img_src)


@app.route("/show_keys/", methods=['POST', 'GET'])
def show_keys():
    if request.method == 'GET':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT image_key FROM image ORDER BY image_key ASC")
        keys = cursor.fetchall()
        for key in keys:
            flash(key[0])
        mysql.connection.commit()
        cursor.close()
    return render_template("show_keys.html")

@app.route("/", methods=['POST', 'GET'])
@app.route("/memory_configuration/", methods=['POST', 'GET'])
def memory_configuration():
    if request.method == 'POST':
        capacity = request.form['capacity']
        replacement_policy = request.form['replacement-policy']
        clear_cache = request.form['clear-cache']
        if clear_cache == 'yes':
            cache.clear()
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE memory_configuration SET capacity = %s, replacement_policy = %s, clear_cache = %s WHERE seq = 1", (capacity, replacement_policy, clear_cache))
        mysql.connection.commit()
        cursor.close()
        cache.refreshConfiguration(int(capacity), replacement_policy)
        flash('Memcache Configurations are set successfully!')
    return render_template("memory_configuration.html")


@app.route("/memory_statistics/")
def memory_statistics():
    beforeTenMins = str(datetime.now() - timedelta(minutes=10))
    beforeTenMins = beforeTenMins[:beforeTenMins.index('.')]
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM memory_statistics WHERE date_created > \'{a:s}\'"
    query = query.format(a = beforeTenMins)
    cursor.execute(query)
    statistics = cursor.fetchall()
    mysql.connection.commit()
    cursor.close()
    return render_template("memory_statistics.html", data = statistics)


app.run(host='0.0.0.0', port=5000, debug=True)
