#=================================================================================
# Course        : CS-UH 2214 Database Systems
# Name          : Programming Project 2
# Author        : Louis Kwak, Tewoflos Girmay
# Date Submitted: 07-May-2024
#=================================================================================




### Importations ###

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func, UniqueConstraint, CheckConstraint
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import base64
import collections




### Global constants ###

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DATABASE_URI = 'postgresql://postgres:faithhopelove@localhost/flicker2'




### Flask Application Set-Up ###

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# Configure the PostgreSQL database URI
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)




### SQLAlchemy Model Definitions ###

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    dob = db.Column(db.Date)
    hometown = db.Column(db.String(255))
    gender = db.Column(db.String(50))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    user_albums = db.relationship('Album', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='owner', lazy=True)
    friendships1 = db.relationship('FriendOf', backref='user1', lazy=True, foreign_keys='FriendOf.user_id1')
    friendships2 = db.relationship('FriendOf', backref='user2', lazy=True, foreign_keys='FriendOf.user_id2')
    likes = db.relationship('Like', backref='user', lazy=True)
    friends = db.relationship('User', secondary='friend_of', primaryjoin='User.user_id == FriendOf.user_id1', secondaryjoin='User.user_id == FriendOf.user_id2', backref='user_friends')
    contribution_score = db.Column(db.Integer, default=0)
    albums_of = db.relationship('Album', primaryjoin='User.user_id == Album.owner_id', backref='user_album')

class Album(db.Model):
    __tablename__ = 'albums'
    album_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    doc = db.Column(db.Date, nullable=False)
    photos_of = db.relationship('Photo', primaryjoin='Album.album_id == Photo.album_id', backref='album_photos')

    def delete_album(self):
        # Logic to delete the album and its associated photos
        photos = Photo.query.filter_by(album_id=self.album_id).all()
        for photo in photos:
            db.session.delete(photo)
        db.session.delete(self)
        db.session.commit()

class Photo(db.Model):
    __tablename__ = 'photos'
    photo_id = db.Column(db.Integer, primary_key=True)
    caption = db.Column(db.String(255))
    data = db.Column(db.String(255), nullable=False)  # Store the file location of the image
    album_id = db.Column(db.Integer, db.ForeignKey('albums.album_id'), nullable=False)
    album = db.relationship('Album', backref=db.backref('photos', lazy=True))
    tagged = db.relationship('TaggedWith', backref='photos', lazy=True)
    comments = db.relationship('Comment', backref='photos', lazy=True)
    likes = db.relationship('Like', backref='photos', lazy=True)
    photo_comments = db.relationship('Comment', backref='photo')  # Change the backref name
    tags = db.relationship('Tag', secondary='tagged_with', primaryjoin='Photo.photo_id == TaggedWith.photo_id', secondaryjoin='TaggedWith.tag_text == Tag.tag_text', backref='photo_tags')

    def delete_photo(self):
        # Perform deletion logic here
        db.session.delete(self)
        db.session.commit()

class Tag(db.Model):
    __tablename__ = 'tags'
    tag_text = db.Column(db.String(255), primary_key=True)

class TaggedWith(db.Model):
    __tablename__ = 'tagged_with'
    tagged_id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.photo_id'), nullable=False)
    tag_text = db.Column(db.String(255), db.ForeignKey('tags.tag_text'), nullable=False)
    __table_args__ = (
        UniqueConstraint('photo_id', 'tag_text'),
    )

class Comment(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(1000), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    dop = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.photo_id'), nullable=False)
    user = db.relationship('User', backref='user_comments', foreign_keys=[owner_id])

class FriendOf(db.Model):
    __tablename__ = 'friend_of'
    friendship_id = db.Column(db.Integer, primary_key=True)
    user_id1 = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    user_id2 = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id1', 'user_id2'),
        CheckConstraint('user_id1 <> user_id2'),
    )

class Like(db.Model):
    __tablename__ = 'likes'
    like_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.photo_id'), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'photo_id'),
    )



### Helper Functions ###

# Checks for allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Retrieves the current user object/tuple
def get_current_user():
    # Assuming you store user_id in the session after logging in
    user_id = session.get('user_id')
    if user_id:
        # Retrieve the user object from the database based on user_id
        return User.query.get(user_id)
    else:
        return None  # No user is currently logged in

# Encodes photos
def encode(photos):
    encoded_photos = []
    for photo in photos:
        encoded_data = base64.b64encode(photo.data).decode('utf-8')
        comments = Comment.query.filter_by(photo_id=photo.photo_id).all()
        encoded_comments = []
        for comment in comments:
            encoded_comment = {
                'text': comment.text,
                'owner_id': comment.owner_id
            }
            encoded_comments.append(encoded_comment)
        
        # Get the number of likes for the photo
        like_count = len(photo.likes)
        
        # Get the names of users who liked the photo
        liked_users = [like.user.first_name for like in photo.likes]
        
        encoded_photo = {
            'photo_id': photo.photo_id,
            'caption': photo.caption,
            'data': encoded_data,
            'comments': encoded_comments,
            'tags': photo.tags,
            'like_count': like_count,
            'liked_users': liked_users
        }
        encoded_photos.append(encoded_photo)
    return encoded_photos




### Route Definitions ###

# First screen displayed upon launching the app
@app.route('/')
def index():
    session['user_id'] = None
    return render_template('index.html')

# First screen displayed upon logging in
@app.route('/dashboard')
def dashboard():
    current_user = get_current_user()
    if current_user:
        top_contributors = None #Default as None, in case there are no other users
        # Fetch photos uploaded by other users
        other_users = User.query.filter(User.user_id != current_user.user_id).all()
        other_users_photos = []
        for user in other_users:
            other_users_photos.extend(user.albums.owner_id)  # Change 'albums' to 'user_albums'
            top_contributors = User.query.order_by(User.contribution_score.desc()).limit(10).all()
        
        results = db.session.query(TaggedWith.tag_text, func.count(TaggedWith.tag_text)).\
            group_by(TaggedWith.tag_text).\
            order_by(func.count(TaggedWith.tag_text).desc()).limit(5).all()
        top_tags = []
        for tuple in results:
            top_tags.append(tuple[0])

        return render_template('dashboard.html', user=current_user, photos=other_users_photos, top_contributors=top_contributors, top_tags=top_tags)
    else:
        return redirect(url_for('log_in'))
    


## 1. User Management ##


# (a) Becoming a registered user #

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        if 'email' not in data or 'password' not in data or 'first_name' not in data or 'last_name' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'User already exists with this email'}), 409
        new_user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            password=data['password'],
            dob=datetime.strptime(data['dob'], '%Y-%m-%d') if data.get('dob') else None,
            hometown=data.get('hometown'),
            gender=data.get('gender')
        )
        db.session.add(new_user)
        db.session.commit()
        return render_template('welcome.html', first_name=new_user.first_name, last_name=new_user.last_name)
    return render_template('register.html')

@app.route('/log_in', methods=['GET', 'POST'])
def log_in():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.user_id
            return redirect(url_for('dashboard'))
        else:
            return render_template('log_in.html', error="Invalid email or password.")
    return render_template('log_in.html')


# (b) Adding and listing friends #

@app.route('/add_friend', methods=['GET', 'POST'])
def add_friend():
    if request.method == 'POST':
        friend_email = request.form['friend_email']
        friend = User.query.filter_by(email=friend_email).first()
        if friend:
            current_user = get_current_user()
            if friend == current_user:
                return render_template('add_friend_failure.html', message='You want to be friends with yourself?')
            elif friend not in current_user.friends:
                current_user.friends.append(friend)
                db.session.commit()
                return render_template('add_friend_success.html', friend=friend)
            else:
                return render_template('add_friend_failure.html', message='They are already friends with you.')
        else:
            return render_template('add_friend_failure.html', message='User not found')
    return render_template('add_friend.html')

@app.route('/rmv_friend', methods=['GET', 'POST'])
def rmv_friend():
    if request.method == 'POST':
        current_user = get_current_user()
        friend_email = request.form['friend_email']
        friend = User.query.filter_by(email=friend_email).first()
        if friend and (friend in current_user.friends):
            current_user.friends.remove(friend)
            db.session.commit()
            return render_template('rmv_friend_success.html', friend=friend)
        else:
            return render_template('rmv_friend_failure.html')
    return render_template('rmv_friend.html')

@app.route('/search_friends', methods=['GET', 'POST'])
def search_friends():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            return render_template('search_friends_result.html', user=user)
        else:
            return render_template('search_friends_result.html', user=None, message="User not found.")
    return render_template('search_friends.html')

@app.route('/list_friends')
def list_friends():
    current_user = get_current_user()
    if current_user:
        friends = current_user.friends
        if friends:
            return render_template('list_friends.html', friends=friends)
        else:
            return  render_template('list_friends.html', friends=None, message='You seem lonely at the moment... ;(')
    else:
        return redirect(url_for('log_in'))


# (c) User activity #
#     - Monitored by User.contribution_score attribute & displayed on dashboard



## 2. Album and Photo Management ##


# (a) Photo and Album Browsing #

@app.route('/browse_photos')
def browse_photos():
    photos = Photo.query.all()
    encoded_photos = encode(photos)
    return render_template('browse_photos.html', photos=encoded_photos)

@app.route('/my_albums')
def my_albums():
    current_user = get_current_user()
    filt_cond = Album.owner_id == current_user.user_id
    albums = db.session.query(Album).filter(filt_cond).all()
    return render_template('my_albums.html', albums=albums)

@app.route('/view_album/<int:album_id>', methods=['POST'])
def view_album(album_id):
    filt_cond = Photo.album_id == album_id
    photos = db.session.query(Photo).filter(filt_cond).all()
    encoded_photos = encode(photos)
    return render_template('view_album.html', photos=encoded_photos, album_id=album_id)


# (b) Photo and Album Creation #

@app.route('/create_album', methods=['POST'])
def create_album():
    album_name = request.form.get('album_name')
        
    # Check if the album exists
    if album_name:
        current_user = get_current_user()
        album = Album.query.filter_by(owner_id=current_user.user_id).\
            filter_by(name=album_name).first()
        if album:
            return jsonify({'error': 'Album already exists'}), 400
        else:
            album = Album(name=album_name, owner_id=current_user.user_id, doc=datetime.now())
            db.session.add(album)
            db.session.commit()
            return jsonify({'success': 'Album created successfully'}), 200
    else:
        return jsonify({'error': 'Album name not provided'}), 400

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    photo_file = request.files['photo']
    if photo_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if photo_file and allowed_file(photo_file.filename):
        filename = secure_filename(photo_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo_file.save(filepath)
        
        # Read the binary data of the file
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Get other form data
        caption = request.form.get('caption')
        album_name = request.form.get('album_name')
        tags = request.form.get('tags')
        
        # Check if the album exists
        if album_name:
            current_user = get_current_user()
            album = Album.query.filter_by(owner_id=current_user.user_id).\
                filter_by(name=album_name).first()
            # If album doesn't exist, create one
            if not album:
                album = Album(name=album_name, owner_id=current_user.user_id, doc=datetime.now())
                db.session.add(album)
                db.session.commit()
            
            album_id = album.album_id
        else:
            return jsonify({'error': 'Album name not provided'}), 400

        # Create a new photo record in the database
        new_photo = Photo(
            caption=caption,
            data=data,
            album_id=album_id
        )
        
        db.session.add(new_photo)
        db.session.commit()

        if tags:
            tags_list = tags.split(' ')
            for t_pre in tags_list:
                t = t_pre.lower()
                tag = Tag.query.filter_by(tag_text=t).first()
                if not tag:
                    new_tag = Tag(tag_text=t)
                    db.session.add(new_tag)
                    db.session.commit()
                    tag = new_tag
                new_photo.tags.append(tag)
                db.session.commit()
                db.session.commit()
            
        user = get_current_user()   #adding contribution score
        if user:
            user.contribution_score += 1
            db.session.commit()
        return jsonify({'success': 'Photo uploaded successfully'}), 200
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/delete_album/<int:album_id>', methods=['POST'])
def delete_album(album_id):
    album = Album.query.get(album_id)
    if album:
        current_user = get_current_user()
        if current_user:
            if current_user.user_id == album.owner_id:
                # Delete associated photos
                Photo.query.filter_by(album_id=album_id).delete()
                # Commit the deletion
                db.session.commit()
                # Finally, delete the album
                db.session.delete(album)
                db.session.commit()
                return redirect(url_for('my_albums'))
            else:
                return jsonify({'error': 'You are not authorized to delete this album'}), 403
        else:
            return redirect(url_for('log_in'))
    return jsonify({'error': 'Album not found'}), 404

@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
def delete_photo(photo_id):
    # Retrieve the photo with the given photo_id
    photo = Photo.query.get(photo_id)
    album = photo.album_id
    # Check if the photo exists
    if photo:
        current_user = get_current_user()

        # Check if the current user is authorized to delete the photo
        if current_user.user_id == photo.album.owner_id:
            # Delete associated likes
            Like.query.filter_by(photo_id=photo_id).delete()
            # Delete associated tagged_with's
            TaggedWith.query.filter_by(photo_id=photo_id).delete()
            # Delete the photo from the database
            db.session.delete(photo)
            db.session.commit()
            # Redirect the user to the browse_photos route after successful deletion
            return redirect(url_for('my_albums'))
        else:
            # Return a 403 Forbidden error if the user is not authorized to delete the photo
            return jsonify({'error': 'You are not authorized to delete this photo'}), 403
    else:
        # Return a 404 Not Found error if the photo with the provided photo_id does not exist
        return jsonify({'error': 'Photo not found'}), 404


## 3. Tag Management ##


# (a) Viewing Your Photos by Tag Name & (b) Viewing All Photos by Tag Name #

@app.route('/view_by_tag_my')
def view_by_tag_my():
    current_user = get_current_user()
    filt_cond = Album.owner_id == current_user.user_id
    join_cond1 = Tag.tag_text == TaggedWith.tag_text
    join_cond2 = TaggedWith.photo_id == Photo.photo_id
    join_cond3 = Photo.album_id == Album.album_id
    result = db.session.query(Tag, TaggedWith, Photo, Album).\
        join(TaggedWith, join_cond1).join(Photo, join_cond2).join(Album, join_cond3).\
        filter(filt_cond).all()
    
    tags = []
    for tuple in result:
        if tuple[0] not in tags:
            tags.append(tuple[0])
    return render_template('view_by_tag_my.html', tags=tags)

@app.route('/view_by_tag_all')
def view_by_tag_all():
    tags = Tag.query.all()
    return render_template('view_by_tag_all.html', tags=tags)

@app.route('/view_by_tag/<string:tag_text>/<int:view_all>', methods=['POST'])
def view_by_tag(tag_text, view_all):
    if tag_text:
        filt_cond1 = TaggedWith.tag_text == tag_text
        join_cond1 = TaggedWith.photo_id == Photo.photo_id
        
        if view_all == 1:
            result = db.session.query(TaggedWith, Photo).\
                join(Photo, join_cond1).\
                filter(filt_cond1).all()
        else:
            current_user = get_current_user()
            filt_cond2 = Album.owner_id == current_user.user_id
            join_cond2 = Photo.album_id == Album.album_id
            result = db.session.query(TaggedWith, Photo, Album).\
                join(Photo, join_cond1).join(Album, join_cond2).\
                filter(filt_cond1).filter(filt_cond2).all()
        
        photos = []
        for tuple in result:
            photos.append(tuple[1])
        
        encoded_photos = encode(photos)
        return render_template('search_by_tag_result.html', photos=encoded_photos, message='Photos Tagged With \'%s\'' %(tag_text))
    return redirect(url_for('dashboard'))


# (c) Viewing the Most Popular Tags #
#     - Displayed on dashboard with buttons


# (d) Photo Search #

@app.route('/search_by_tag', methods=['GET', 'POST'])
def search_by_tag():
    if request.method == 'POST':
        tags = request.form.get('tags')
        tags_list = tags.split(' ')
        tags_encoded = []
        for tag in tags_list:
            tag = Tag.query.get(tag)
            if not tag: return render_template('search_by_tag_result.html', photos=None, message='One or more nonexistent tag(s) included.')
            else: tags_encoded.append(tag)

        photos = Photo.query.all()
        photos_pre = []
        for photo in photos:
            tags_present = True #Flag that checks whether the photo contains all the tags
            for tag in tags_encoded:
                if tag not in photo.tags:
                    tags_present = False
                    break
            if tags_present: photos_pre.append(photo)
        encoded_photos = encode(photos_pre)
        if encoded_photos: return render_template('search_by_tag_result.html', photos=encoded_photos, message='Photos Found')
        else: return render_template('search_by_tag_result.html', photos=None, message='No Such Photos Found')
    return render_template('search_by_tag.html')



## 4. Comments ##


# (a) Post Comments #

@app.route('/add_comment/<int:photo_id>/<string:page_name>', methods=['GET', 'POST'])
def add_comment(photo_id, page_name):
    text = request.form.get('comment')
    if text:
        photo = Photo.query.get(photo_id)
        if photo:
            filt_cond = Photo.photo_id == photo_id
            join_cond = Album.album_id == Photo.album_id
            result = db.session.query(Album, Photo).\
                join(Photo, join_cond).\
                filter(filt_cond).first()
            
            current_user = get_current_user()
            if current_user:
                user_id = current_user.user_id
            else:
                user_id = None
            
            if user_id == result[0].owner_id:
                return jsonify({'error': 'You cannot comment on your own photo.'}), 400
            
            new_comment = Comment(text=text, owner_id=user_id, dop=datetime.now(), photo_id=photo_id)
            db.session.add(new_comment)
            db.session.commit()
            # Increment contribution score only if the comment was left by a registered user
            if current_user:
                current_user.contribution_score += 1
                db.session.commit()
    if page_name == 'browse': return redirect(url_for('browse_photos'))
    else: return redirect(url_for('my_albums'))


# (b) Like Functionality #

@app.route('/add_like/<int:photo_id>', methods=['POST'])
def add_like(photo_id):
    current_user = get_current_user()
    if current_user:
        photo = Photo.query.get(photo_id)
        if photo:
            if current_user not in photo.likes:  
                # Add a like for the current user to the photo
                new_like = Like(user_id=current_user.user_id, photo_id=photo_id)
                db.session.add(new_like)
                db.session.commit()

                # Get updated like count
                like_count = len(photo.likes)

                # Get the names of users who liked the photo
                liked_users = [like.user.first_name for like in photo.likes]

                # Return JSON response with updated like count and liked users
                return jsonify({'success': 'Like added successfully', 'like_count': like_count, 'liked_users': liked_users}), 200
            else:
                return jsonify({'error': 'You have already liked this photo.'}), 400
        else:
            return jsonify({'error': 'Photo not found.'}), 404
    else:
        return jsonify({'error': 'You must be logged in to like a photo.'}), 401


# (c) Search on Comments #

@app.route('/search_comments', methods=['POST'])
def search_comments():
    query = request.form.get('query')

    # Query the database to find users with comments matching the query
    search_results = db.session.query(User, func.count(Comment.comment_id)).\
        join(Comment, User.user_id == Comment.owner_id).\
        filter(Comment.text.ilike(f'%{query}%')).\
        group_by(User).\
        order_by(func.count(Comment.comment_id).desc()).all()

    # Fetch all photos for rendering the browse_photos template
    photos = Photo.query.all()
    encoded_photos = encode(photos)

    return render_template('browse_photos.html', photos=encoded_photos, search_results=search_results)



## 5. Recommendations ##


# (a) Friend Recommendation #

@app.route('/rec_friends')
def rec_friends():
    current_user = get_current_user()
    if current_user:
        # Find friends of friends
        fofs = {}
        for friend in current_user.friends:
            for fof in friend.friends:
                if fof.user_id != current_user.user_id and fof not in current_user.friends:
                    if fof in fofs:
                        fofs[fof] += 1
                    else:
                        fofs[fof] = 1
        if fofs:
            fofs_sorted = []
            fofs_len = len(fofs)
            appearances = 1
            for i in range(fofs_len):
                while appearances not in fofs.values():
                    appearances += 1
                fof = list(fofs.keys())[list(fofs.values()).index(appearances)]
                fofs_sorted.insert(0, fof)
                fofs.pop(fof)
            return render_template('rec_friends.html', fofs=fofs_sorted)    
        else:
            return render_template('rec_friends.html', fofs=None, message = 'No recommended users at the moment')
    else:
        return redirect(url_for('log_in'))


# (b) 'You-May-Also-Like' Functionality #

@app.route('/you_may_also_like')
def you_may_also_like():
    current_user = get_current_user()
    if current_user:
        tags = {}
        filt_cond = Album.owner_id == current_user.user_id
        join_cond = Album.album_id == Photo.album_id
        result = db.session.query(Album, Photo).\
            join(Photo, join_cond).\
            filter(filt_cond).all()
        for tuple in result:
            for tag in tuple[1].tags:
                if tag in tags:
                    tags[tag] += 1
                else:
                    tags[tag] = 1 
        if tags:
            tags_sorted = []
            tags_len = len(tags)
            appearances = 1
            for i in range(tags_len):
                while appearances not in tags.values():
                    appearances += 1
                tag = list(tags.keys())[list(tags.values()).index(appearances)]
                tags_sorted.insert(0, tag)
                tags.pop(tag)
                if len(tags_sorted) == 5: break
            
            #Finding recommendations from others' photos
            filt_cond = Album.owner_id != current_user.user_id
            join_cond = Album.album_id == Photo.album_id
            others = db.session.query(Album, Photo).\
                join(Photo, join_cond).\
                filter(filt_cond).all()
            
            if others:
                photos_filtered = {}
                for tag in tags_sorted:
                    for tuple in others:
                        photo = tuple[1]
                        if tag in photo.tags:
                            if photo in photos_filtered:
                                photos_filtered[photo] += 1
                            else:
                                photos_filtered[photo] = 1
                
                if photos_filtered:
                    photos_sorted = []
                    is_full = False #whether photos_sorted reached its maximum capacity (10)
                    photos_len = len(photos_filtered)
                    appearances = max(list(photos_filtered.values()))
                    for i in range(photos_len):
                        print('now:', appearances, 'on', photos_filtered)
                        #Number of photos with the same number of matched tags
                        ties = collections.Counter(photos_filtered.values())[appearances]

                        if ties > 1: #Then we should sort the photos that tie w.r.t. concision
                            tie_photos = []
                            for i in range(ties):
                                photo = list(photos_filtered.keys())[list(photos_filtered.values()).index(appearances)]
                                if len(tie_photos) > 0:
                                    for match in tie_photos:
                                        if len(photo.tags) < len(match.tags):
                                            tie_photos.insert(tie_photos.index(match), photo)
                                            popped = photos_filtered.pop(photo)
                                            break
                                        elif match == tie_photos[-1]:
                                            tie_photos.append(photo)
                                            popped = photos_filtered.pop(photo)
                                else:
                                    tie_photos.append(photo)
                                    popped = photos_filtered.pop(photo)
                            
                            for photo in tie_photos:
                                photos_sorted.append(photo)
                                if len(photos_sorted) == 5:
                                    is_full = True
                                    break
                        
                        if ties == 1: #Then simply insert the photo to the front
                            photo = list(photos_filtered.keys())[list(photos_filtered.values()).index(appearances)]
                            photos_sorted.append(photo)
                            popped = photos_filtered.pop(photo)
                            if len(photos_sorted) == 5:
                                is_full = True
                                break

                        if is_full: break

                        appearances -= 1
                    encoded_photos = encode(photos_sorted)
                    return render_template('you_may_also_like.html', rec_photos=encoded_photos)
                else:
                    return render_template('you_may_also_like.html', rec_photos=None, message = 'No recommended photos at the moment')     
            else:
                return render_template('you_may_also_like.html', rec_photos=None, message = 'No recommended photos at the moment') 
        else:
            return render_template('you_may_also_like.html', rec_photos=None, message = 'No recommended photos at the moment')
    else:
        return redirect(url_for('log_in'))




if __name__ == '__main__':
    app.run(debug=True)