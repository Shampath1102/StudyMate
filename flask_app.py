import os
from datetime import datetime, timedelta  # Add timedelta to the import

from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text

# Define available branches
BRANCHES = ['Computer Science', 'Electronics', 'Mechanical', 'Civil', 'Chemical', 'Electrical']
# Initialize Flask App
app = Flask(__name__)
csrf = CSRFProtect(app)  # Initialize CSRF protection
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Ensure Upload Folder Exists
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Import Models AFTER initializing Flask app
from models import db, User, StudyMaterial, Discussion, Comment, Rating, Like, Category, Bookmark, QuestionPaper, AnswerKey, Badge, PointsHistory

# ✅ Link `db` with `app`
db.init_app(app)

# Ensure tables exist
# Update the create_all() section
with app.app_context():
    db.create_all()
    
    # Optional: Create default categories if they don't exist
    default_categories = ['Notes', 'Assignments', 'Past Papers', 'Reference Materials']
    for cat_name in default_categories:
        if not Category.query.filter_by(name=cat_name).first():
            category = Category(name=cat_name)
            db.session.add(category)
    db.session.commit()

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Define Routes
@app.route('/')
def home():
    return render_template('index.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')

# Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        branch = request.form['branch']  # Get branch from form

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('signup'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('login'))

        # Create new user
        new_user = User(username=username, email=email, password=hashed_password, branch=branch)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# Dashboard Page
from sqlalchemy import func, extract

def get_leaderboard(timeframe='all-time', branch='all'):
    base_query = db.session.query(User)
    
    # Apply branch filter first if specified
    if branch != 'all':
        base_query = base_query.filter(User.branch == branch)
    
    if timeframe == 'weekly':
        # Get points from the last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        points_query = db.session.query(
            PointsHistory.user_id,
            func.sum(PointsHistory.points).label('total_points')
        ).filter(
            PointsHistory.timestamp >= seven_days_ago
        ).group_by(PointsHistory.user_id)
        
        # Join with points subquery
        points_subquery = points_query.subquery()
        users = base_query.outerjoin(
            points_subquery,
            User.id == points_subquery.c.user_id
        ).order_by(points_subquery.c.total_points.desc().nullslast()).limit(10).all()
        
    elif timeframe == 'monthly':
        # Get points from the current month
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        points_query = db.session.query(
            PointsHistory.user_id,
            func.sum(PointsHistory.points).label('total_points')
        ).filter(
            PointsHistory.timestamp >= current_month
        ).group_by(PointsHistory.user_id)
        
        # Join with points subquery
        points_subquery = points_query.subquery()
        users = base_query.outerjoin(
            points_subquery,
            User.id == points_subquery.c.user_id
        ).order_by(points_subquery.c.total_points.desc().nullslast()).limit(10).all()
        
    else:  # all-time
        users = base_query.order_by(User.points.desc()).limit(10).all()
    
    return users

@app.route('/dashboard')
@login_required
def dashboard():
    # Get recent activities (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Get user's recent activities
    recent_materials = StudyMaterial.query.filter(
        StudyMaterial.branch == current_user.branch,
        StudyMaterial.upload_date >= thirty_days_ago
    ).order_by(StudyMaterial.upload_date.desc()).limit(5).all()
    
    recent_discussions = Discussion.query.filter(
        Discussion.branch == current_user.branch,
        Discussion.timestamp >= thirty_days_ago
    ).order_by(Discussion.timestamp.desc()).limit(5).all()
    
    points_history = PointsHistory.query.filter(
        PointsHistory.user_id == current_user.id,
        PointsHistory.timestamp >= thirty_days_ago
    ).order_by(PointsHistory.timestamp.desc()).limit(5).all()
    
    bookmarks = Bookmark.query.filter(
        Bookmark.user_id == current_user.id,
        Bookmark.created_at >= thirty_days_ago
    ).order_by(Bookmark.created_at.desc()).limit(5).all()
    
    # Get user's total points and badges
    user_badges = current_user.badges
    total_points = current_user.points
    
    # Get leaderboard data
    leaderboard = get_leaderboard()
    
    return render_template('dashboard.html',
                         user=current_user,
                         recent_materials=recent_materials,
                         recent_discussions=recent_discussions,
                         points_history=points_history,
                         bookmarks=bookmarks,
                         badges=user_badges,
                         total_points=total_points,
                         leaderboard=leaderboard,
                         branches=BRANCHES,
                         StudyMaterial=StudyMaterial,
                         Discussion=Discussion,
                         QuestionPaper=QuestionPaper)

@app.route('/get_leaderboard')
def get_leaderboard_data():
    timeframe = request.args.get('timeframe', 'all-time')
    branch = request.args.get('branch', 'all')
    
    users = get_leaderboard(timeframe, branch)
    leaderboard_data = [{
        'username': user.username,
        'points': user.points,
        'branch': user.branch
    } for user in users]
    
    return jsonify(leaderboard_data)

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

# Upload Study Material
# Add this near the top with other constants
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Add this near other constants
BRANCHES = ['Computer Science', 'Electronics', 'Mechanical', 'Civil', 'General']

@app.route('/study-material')
@login_required
def study_material():
    branch_filter = request.args.get('branch', '')
    search_query = request.args.get('search', '')
    material_type_filter = request.args.get('material_type', '')
    format_filter = request.args.get('format', '')

    query = StudyMaterial.query

    if branch_filter:
        query = query.filter(StudyMaterial.branch == branch_filter)
    if material_type_filter:
        query = query.filter(StudyMaterial.material_type == material_type_filter)
    if format_filter:
        query = query.filter(StudyMaterial.filename.like(f'%.{format_filter}'))
    if search_query:
        query = query.filter(StudyMaterial.title.ilike(f'%{search_query}%'))

    materials = query.order_by(StudyMaterial.upload_date.desc()).all()
    return render_template('study-material.html', 
                         materials=materials, 
                         branches=BRANCHES,
                         current_branch=branch_filter,
                         current_type=material_type_filter,
                         current_format=format_filter,
                         search_query=search_query)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash("No file uploaded", "danger")
        return redirect(url_for('study_material'))

    file = request.files['file']
    material_type = request.form.get('material_type')

    if file.filename == '' or not material_type:
        flash("Please provide both file and material type", "danger")
        return redirect(url_for('study_material'))

    if not allowed_file(file.filename):
        flash("File type not allowed", "danger")
        return redirect(url_for('study_material'))

    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

    new_material = StudyMaterial(
        title=file.filename,
        filename=unique_filename,
        material_type=material_type,
        branch=request.form.get('branch', 'General'),
        user_id=current_user.id,
        upload_date=datetime.utcnow()
    )
    db.session.add(new_material)
    
    # Add points for uploading study material
    points_history = PointsHistory(user_id=current_user.id,
        points=5,
        action='Uploaded study material')
    current_user.points += 5
    db.session.add(points_history)
    db.session.commit()

    flash("File uploaded successfully!", "success")
    return redirect(url_for('study_material'))

# Download Study Material
@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Bookmark Routes
@app.route('/bookmarks')
@login_required
def bookmarks():
    content_type = request.args.get('content_type', '')
    folder = request.args.get('folder', '')
    search = request.args.get('search', '')
    
    # Base query
    query = Bookmark.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if content_type:
        query = query.filter_by(content_type=content_type)
    if folder:
        query = query.filter_by(folder=folder)
    
    # Get all bookmarks
    bookmarks = query.order_by(Bookmark.created_at.desc()).all()
    
    # Get unique folders for filter dropdown
    folders = db.session.query(Bookmark.folder).filter(
        Bookmark.user_id == current_user.id,
        Bookmark.folder != ''
    ).distinct().all()
    folders = [f[0] for f in folders if f[0]]
    
    # Process bookmarks to add content details
    processed_bookmarks = []
    for bookmark in bookmarks:
        bookmark_data = {
            'id': bookmark.id,
            'content_type': bookmark.content_type,
            'tags': bookmark.tags,
            'folder': bookmark.folder,
            'created_at': bookmark.created_at,
            'title': '',
            'content_url': ''
        }
        
        # Get content details based on type
        if bookmark.content_type == 'study_material':
            material = StudyMaterial.query.get(bookmark.content_id)
            if material:
                bookmark_data['title'] = material.title
                bookmark_data['content_url'] = url_for('study_material')
        elif bookmark.content_type == 'discussion':
            discussion = Discussion.query.get(bookmark.content_id)
            if discussion:
                bookmark_data['title'] = discussion.title
                bookmark_data['content_url'] = url_for('discussions')
        elif bookmark.content_type == 'question_paper':
            paper = QuestionPaper.query.get(bookmark.content_id)
            if paper:
                bookmark_data['title'] = paper.subject
                bookmark_data['content_url'] = url_for('question_papers')
        
        if search.lower() in bookmark_data['title'].lower():
            processed_bookmarks.append(bookmark_data)
    
    return render_template('bookmarks.html', bookmarks=processed_bookmarks, folders=folders)

@app.route('/bookmark/<content_type>/<int:content_id>', methods=['POST'])
@login_required
def add_bookmark(content_type, content_id):
    tags = request.form.get('tags', '')
    folder = request.form.get('folder', '')
    
    bookmark = Bookmark(user_id=current_user.id,
                       content_type=content_type,
                       content_id=content_id,
                       tags=tags,
                       folder=folder)
    db.session.add(bookmark)
    db.session.commit()
    
    flash('Bookmark added successfully!', 'success')
    return redirect(request.referrer)

@app.route('/remove_bookmark/<int:bookmark_id>', methods=['POST'])
@login_required
def remove_bookmark(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)
    if bookmark.user_id != current_user.id:
        flash('Unauthorized action!', 'danger')
        return redirect(url_for('bookmarks'))
    
    db.session.delete(bookmark)
    db.session.commit()
    flash('Bookmark removed successfully!', 'success')
    return redirect(url_for('bookmarks'))

# Question Paper Routes
@app.route('/question-papers')
@login_required
def question_papers():
    branch_filter = request.args.get('branch', '')
    exam_type_filter = request.args.get('exam_type', '')
    search_query = request.args.get('search', '')
    
    query = QuestionPaper.query
    
    if branch_filter:
        query = query.filter(QuestionPaper.branch == branch_filter)
    if exam_type_filter:
        query = query.filter(QuestionPaper.exam_type == exam_type_filter)
    if search_query:
        query = query.filter(QuestionPaper.subject.ilike(f'%{search_query}%'))
    
    papers = query.order_by(QuestionPaper.upload_date.desc()).all()
    return render_template('question-papers.html', papers=papers, branches=BRANCHES)

@app.route('/upload-question-paper', methods=['POST'])
@login_required
def upload_question_paper():
    if 'file' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('question_papers'))
        
    file = request.files['file']
    subject = request.form.get('subject')
    exam_type = request.form.get('exam_type')
    branch = request.form.get('branch')
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('question_papers'))
        
    if not allowed_file(file.filename):
        flash('File type not allowed', 'danger')
        return redirect(url_for('question_papers'))
        
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    paper = QuestionPaper(subject=subject,
                         exam_type=exam_type,
                         branch=branch,
                         filename=filename,
                         user_id=current_user.id)
    db.session.add(paper)
    
    # Add points for uploading question paper
    points_history = PointsHistory(user_id=current_user.id,
                                 points=10,
                                 action='Uploaded Question Paper')
    current_user.points += 10
    db.session.add(points_history)
    db.session.commit()
    
    flash('Question paper uploaded successfully!', 'success')
    return redirect(url_for('question_papers'))

# Answer Key Routes
@app.route('/upload-answer-key/<int:paper_id>', methods=['POST'])
@login_required
def upload_answer_key(paper_id):
    if 'file' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('question_papers'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('question_papers'))
        
    if not allowed_file(file.filename):
        flash('File type not allowed', 'danger')
        return redirect(url_for('question_papers'))
        
    filename = f"answer_key_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    answer_key = AnswerKey(question_paper_id=paper_id,
                          filename=filename,
                          user_id=current_user.id)
    db.session.add(answer_key)
    
    # Add points for uploading answer key
    points_history = PointsHistory(user_id=current_user.id,
                                 points=15,
                                 action='Uploaded Answer Key')
    current_user.points += 15
    db.session.add(points_history)
    db.session.commit()
    
    flash('Answer key uploaded successfully!', 'success')
    return redirect(url_for('question_papers'))

# Discussions Page
@app.route('/discussions', methods=['GET'])
@login_required
def discussions():
    branch_filter = request.args.get('branch', '')
    search_query = request.args.get('search', '')

    query = Discussion.query

    if branch_filter:
        query = query.filter(Discussion.branch == branch_filter)
    if search_query:
        query = query.filter(
            (Discussion.title.ilike(f'%{search_query}%')) |
            (Discussion.message.ilike(f'%{search_query}%'))
        )

    discussions = query.order_by(Discussion.timestamp.desc()).all()
    return render_template('discussions.html', 
                         discussions=discussions,
                         branches=BRANCHES,
                         current_branch=branch_filter,
                         search_query=search_query)


@app.route('/post_discussion', methods=['POST'])
@login_required
def post_discussion():
    title = request.form.get('title')
    message = request.form.get('message')

    if not title or not message:
        flash("Title and message cannot be empty!", "danger")
        return redirect(url_for('discussions'))

    new_discussion = Discussion(
        title=title,
        message=message,
        branch=request.form.get('branch', 'General'),
        user_id=current_user.id,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_discussion)
    
    # Add points for creating discussion
    points_history = PointsHistory(user_id=current_user.id,
                                 points=2,
                                 action='Created Discussion')
    current_user.points += 2
    db.session.add(points_history)
    db.session.commit()
    
    flash("Discussion posted successfully!", "success")
    return redirect(url_for('discussions'))

# Profile Page
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username')
        current_user.email = request.form.get('email')
        
        if request.form.get('new_password'):
            if bcrypt.check_password_hash(current_user.password, request.form.get('current_password')):
                current_user.password = bcrypt.generate_password_hash(
                    request.form.get('new_password')).decode('utf-8')
                flash('Password updated successfully!', 'success')
            else:
                flash('Current password is incorrect!', 'danger')
                
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=current_user)

# Search functionality
@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    
    materials = StudyMaterial.query.filter(
        StudyMaterial.title.ilike(f'%{query}%')
    ).all()
    
    discussions = Discussion.query.filter(
        Discussion.title.ilike(f'%{query}%') | 
        Discussion.message.ilike(f'%{query}%')
    ).all()
    
    return render_template('search.html', 
                         materials=materials, 
                         discussions=discussions, 
                         query=query)

# Add comment to discussion
@app.route('/add_comment/<int:discussion_id>', methods=['POST'])
@login_required
def add_comment(discussion_id):
    content = request.form.get('content')
    if not content:
        flash('Comment cannot be empty!', 'danger')
        return redirect(url_for('discussions'))
        
    new_comment = Comment(
        content=content,
        timestamp=datetime.utcnow(),
        user_id=current_user.id,
        discussion_id=discussion_id
    )
    db.session.add(new_comment)
    
    # Add points for commenting
    points_history = PointsHistory(user_id=current_user.id,
                                 points=1,
                                 action='Posted Comment')
    current_user.points += 1
    db.session.add(points_history)
    db.session.commit()
    
    flash('Comment added successfully!', 'success')
    return redirect(url_for('discussions'))
    content = request.form.get('content')
    if content:
        new_comment = Comment(
            content=content,
            user_id=current_user.id,
            discussion_id=discussion_id,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    return redirect(url_for('discussions'))

# Rate study material
@app.route('/rate/<int:material_id>', methods=['POST'])
@login_required
def rate_material(material_id):
    rating = request.form.get('rating', type=int)
    if rating and 1 <= rating <= 5:
        existing_rating = Rating.query.filter_by(
            user_id=current_user.id,
            material_id=material_id
        ).first()
        
        if existing_rating:
            existing_rating.value = rating
        else:
            new_rating = Rating(
                user_id=current_user.id,
                material_id=material_id,
                value=rating
            )
            db.session.add(new_rating)
            
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/toggle_like/<int:material_id>', methods=['POST'])
@login_required
def toggle_like(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    like = Like.query.filter_by(user_id=current_user.id, material_id=material_id).first()
    
    if like:
        db.session.delete(like)
        liked = False
    else:
        like = Like(user_id=current_user.id, material_id=material_id)
        db.session.add(like)
        liked = True
    
    db.session.commit()
    return jsonify({'liked': liked, 'likes': material.like_count})

# Run Flask App
if __name__ == '__main__':
    app.run(debug=True)
