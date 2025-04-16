from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# ✅ Initialize `db` only here
db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=0)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)

    study_materials = db.relationship('StudyMaterial', backref='uploader', lazy=True, cascade="all, delete")
    discussions = db.relationship('Discussion', backref='author', lazy=True, cascade="all, delete")
    bookmarks = db.relationship('Bookmark', backref='user', lazy=True, cascade="all, delete")
    question_papers = db.relationship('QuestionPaper', backref='uploader', lazy=True, cascade="all, delete")
    answer_keys = db.relationship('AnswerKey', backref='uploader', lazy=True, cascade="all, delete")
    badges = db.relationship('Badge', secondary='user_badges', backref='users')

    def __repr__(self):
        return f"<User {self.username}>"

class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    material_type = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(50), nullable=False, default='General')  # Add this line
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"<StudyMaterial {self.title} uploaded by {self.user_id}>"

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    branch = db.Column(db.String(50), nullable=False, default='General')


    def __repr__(self):
        return f"<Discussion {self.title} by {self.user_id}>"

# Add these new models to your existing models.py file

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    
    user = db.relationship('User', backref='comments')
    discussion = db.relationship('Discussion', backref='comments')

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('study_material.id'), nullable=False)
    
    user = db.relationship('User', backref='ratings')
    material = db.relationship('StudyMaterial', backref='ratings')

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    target_type = db.Column(db.String(20), nullable=False)  # 'material' or 'discussion'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    user = db.relationship('User', backref='likes')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    study_materials = db.relationship('StudyMaterial', secondary='material_category', backref='categories')

# Association table for many-to-many relationship between StudyMaterial and Category
material_category = db.Table('material_category',
    db.Column('material_id', db.Integer, db.ForeignKey('study_material.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)  # 'study_material', 'discussion', 'question_paper'
    content_id = db.Column(db.Integer, nullable=False)
    tags = db.Column(db.String(200))  # Comma-separated tags
    folder = db.Column(db.String(100))  # Folder name for organization
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuestionPaper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)  # 'midterm', 'final'
    branch = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class AnswerKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_paper_id = db.Column(db.Integer, db.ForeignKey('question_paper.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    image_url = db.Column(db.String(200))
    points_required = db.Column(db.Integer, default=0)

user_badges = db.Table('user_badges',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'), primary_key=True),
    db.Column('earned_date', db.DateTime, default=datetime.utcnow)
)



class PointsHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='points_history')
