from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exercise_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 輔助函數
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

db = SQLAlchemy(app)

# 運動數據參考表
EXERCISE_DATA = {
    '慢走(4公里/小時)': 3.5,
    '快走、健走(6.0公里/小時)': 5.5,
    '下樓梯': 3.2,
    '上樓梯': 8.4,
    '慢跑(8公里/小時)': 8.2,
    '快跑(12公里/小時)': 12.7,
    '快跑(16公里/小時)': 16.8,
    '騎腳踏車(一般速度，10公里/小時)': 4,
    '騎腳踏車(快，20公里/小時)': 8.4,
    '騎腳踏車(很快，30公里/小時)': 12.6,
    '拖地': 3.7,
    '園藝': 4.2,
    '使用工具製造或修理(如水電工)': 5.3,
    '耕種、牧場、漁業、林業': 7.4,
    '搬運重物': 8.4,
    '瑜珈': 3,
    '跳舞(慢)、元極舞': 3.1,
    '跳舞(快)、國際標準舞': 5.3,
    '飛盤': 3.2,
    '排球': 3.6,
    '保齡球': 3.6,
    '太極拳': 4.2,
    '乒乓球': 4.2,
    '棒壘球': 4.7,
    '高爾夫': 5,
    '溜直排輪': 5.1,
    '羽毛球': 5.1,
    '遊泳(慢)': 6.3,
    '遊泳(較快)': 10,
    '籃球(半場)': 6.3,
    '籃球(全場)': 8.3,
    '有氧舞蹈': 6.8,
    '網球': 6.6,
    '足球': 7.7,
    '跳繩(慢)': 8.4,
    '跳繩(快)': 12.6
}


# 資料庫模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 關聯
    exercise_records = db.relationship('ExerciseRecord', backref='user', lazy=True)
    goals = db.relationship('Goal', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ExerciseRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_type = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # 分鐘
    heart_rate = db.Column(db.Integer)  # bpm
    intensity = db.Column(db.String(20), nullable=False)  # 低/中/高
    notes = db.Column(db.Text)
    calories = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal_type = db.Column(db.String(50), nullable=False)  # calories/duration/frequency
    goal_value = db.Column(db.Integer, nullable=False)
    period = db.Column(db.String(20), nullable=False)  # daily/weekly/monthly
    name = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# 輔助函數
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def calculate_calories(exercise_type, duration, weight):
    """計算消耗的熱量"""
    if exercise_type in EXERCISE_DATA:
        calorie_rate = EXERCISE_DATA[exercise_type]
        return round(calorie_rate * weight * (duration / 60))
    return 0


def get_period_start(period):
    """獲取時期的開始日期"""
    now = datetime.now()
    if period == 'daily':
        return datetime(now.year, now.month, now.day)
    elif period == 'weekly':
        return now - timedelta(days=now.weekday())
    elif period == 'monthly':
        return datetime(now.year, now.month, 1)
    return now


# 路由
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_weight'] = user.weight
            flash('登入成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('帳號或密碼錯誤', 'error')

    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        weight = float(request.form['weight'])

        if User.query.filter_by(username=username).first():
            flash('帳號已存在', 'error')
            return render_template('auth/login.html')

        user = User(username=username, weight=weight)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('註冊成功！請登入', 'success')
        return render_template('auth/login.html')

    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('已登出', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    # 調試：打印模板目錄以及文件前幾行
    print("模板目錄：", app.template_folder)
    path = os.path.join(app.root_path, app.template_folder, 'dashboard.html')
    print("實際讀取：", path)
    with open(path, encoding='utf-8') as f:
        print(f.read()[:200], "…")

    user = User.query.get(session['user_id'])

    # 今日統計
    today_utc = datetime.utcnow().date()
    start = datetime.combine(today_utc, datetime.min.time())
    end = start + timedelta(days=1)
    today_records = ExerciseRecord.query.filter(
        ExerciseRecord.user_id == user.id,
        ExerciseRecord.created_at >= start,
        ExerciseRecord.created_at < end
    ).all()

    today_stats = {
        'exercises': len(today_records),
        'calories': sum(record.calories for record in today_records),
        'duration': sum(record.duration for record in today_records)
    }

    # 完成的目標數
    completed_goals = Goal.query.filter_by(
        user_id=user.id,
        completed=True
    ).count()

    # 最近運動記錄
    recent_records = ExerciseRecord.query.filter_by(
        user_id=user.id
    ).order_by(ExerciseRecord.created_at.desc()).limit(5).all()

    return render_template('dashboard.html',
                         today_stats=today_stats,
                         completed_goals=completed_goals,
                         recent_records=recent_records)

@app.route('/record', methods=['GET', 'POST'])
@login_required
def record_exercise():
    if request.method == 'POST':
        user = User.query.get(session['user_id'])

        exercise_type = request.form['exercise_type']
        duration = int(request.form['duration'])
        heart_rate = request.form.get('heart_rate')
        intensity = request.form['intensity']
        notes = request.form.get('notes', '')

        calories = calculate_calories(exercise_type, duration, user.weight)

        record = ExerciseRecord(
            user_id=user.id,
            exercise_type=exercise_type,
            duration=duration,
            heart_rate=int(heart_rate) if heart_rate else None,
            intensity=intensity,
            notes=notes,
            calories=calories
        )

        db.session.add(record)
        db.session.commit()

        # 檢查目標進度
        check_goal_progress(user.id)

        flash('運動記錄已儲存！', 'success')
        return redirect(url_for('record_exercise'))

    return render_template('record.html', exercise_types=list(EXERCISE_DATA.keys()))

@app.route('/analytics')
@login_required
def analytics():
    user_id = session['user_id']

    # 獲取所有記錄並轉換為字典格式
    records = ExerciseRecord.query.filter_by(user_id=user_id).order_by(ExerciseRecord.created_at.desc()).all()

    # 將記錄轉換為字典格式供前端使用
    records_data = []
    for record in records:
        record_dict = {
            'id': record.id,
            'exercise_type': record.exercise_type,
            'duration': record.duration,
            'heart_rate': record.heart_rate,
            'intensity': record.intensity,
            'notes': record.notes,
            'calories': record.calories,
            'created_at': record.created_at.isoformat()
        }
        records_data.append(record_dict)

    # 運動類型統計
    exercise_type_stats = {}
    for record in records:
        if record.exercise_type in exercise_type_stats:
            exercise_type_stats[record.exercise_type] += 1
        else:
            exercise_type_stats[record.exercise_type] = 1

    return render_template('analytics.html',
                         records=records,
                         records_data=records_data,
                         exercise_type_stats=exercise_type_stats)

@app.route('/goals', methods=['GET', 'POST'])
@login_required
def goals():
    if request.method == 'POST':
        goal = Goal(
            user_id=session['user_id'],
            goal_type=request.form['goal_type'],
            goal_value=int(request.form['goal_value']),
            period=request.form['period'],
            name=request.form['name']
        )

        db.session.add(goal)
        db.session.commit()

        flash('目標已新增！', 'success')
        return redirect(url_for('goals'))

    user_goals = Goal.query.filter_by(user_id=session['user_id']).all()

    # 將目標轉換為字典格式並計算進度
    goals_data = []
    for goal in user_goals:
        progress = calculate_goal_progress(goal)
        goal_dict = {
            'id': goal.id,
            'name': goal.name,
            'goal_type': goal.goal_type,
            'goal_value': goal.goal_value,
            'period': goal.period,
            'completed': goal.completed,
            'progress': progress,
            'created_at': goal.created_at.isoformat()
        }
        goals_data.append(goal_dict)

    return render_template('goals.html', goals=goals_data, raw_goals=user_goals)

@app.route('/social')
@login_required
def social():
    # 所有用戶（除了當前用戶）
    users = User.query.filter(User.id != session['user_id']).all()

    # 當前用戶的好友
    friendships = Friendship.query.filter_by(user_id=session['user_id']).all()
    friend_ids = [f.friend_id for f in friendships]
    friends = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []

    # 排行榜
    leaderboard = []
    all_users = User.query.all()
    for user in all_users:
        total_calories = db.session.query(func.sum(ExerciseRecord.calories)).filter_by(
            user_id=user.id
        ).scalar() or 0
        total_exercises = ExerciseRecord.query.filter_by(user_id=user.id).count()

        leaderboard.append({
            'user': user,
            'total_calories': int(total_calories),
            'total_exercises': total_exercises
        })

    leaderboard.sort(key=lambda x: x['total_calories'], reverse=True)

    return render_template('social.html',
                         users=users,
                         friends=friends,
                         leaderboard=leaderboard)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.weight = float(request.form['weight'])
        session['user_weight'] = user.weight  # 更新 session 中的體重
        db.session.commit()
        flash('個人資料已更新', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/delete_goal/<int:goal_id>', methods=['POST'])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=session['user_id']).first()
    if goal:
        db.session.delete(goal)
        db.session.commit()
        flash('目標已刪除', 'info')
    else:
        flash('找不到該目標', 'error')
    return redirect(url_for('goals'))


@app.route('/api/trend_data')
@login_required
def api_trend_data():
    user_id = session['user_id']
    # 拉出過去 7 天的所有紀錄
    since = datetime.utcnow() - timedelta(days=6)
    records = ExerciseRecord.query.filter(
        ExerciseRecord.user_id == user_id,
        ExerciseRecord.created_at >= since
    ).all()

    # 按日期累計
    grouped = {}
    for r in records:
        d = r.created_at.date()
        grouped.setdefault(d, {'calories':0, 'duration':0})
        grouped[d]['calories'] += r.calories
        grouped[d]['duration'] += r.duration

    data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        stats = grouped.get(day, {'calories':0, 'duration':0})
        data.append({
            'date':     day.strftime('%m/%d'),
            'calories': stats['calories'],
            'duration': stats['duration']
        })
    return jsonify(data)


@app.route('/api/exercise_type_data')
@login_required
def api_exercise_type_data():
    """獲取運動類型分布數據"""
    user_id = session['user_id']

    records = ExerciseRecord.query.filter_by(user_id=user_id).all()

    type_stats = {}
    for record in records:
        if record.exercise_type in type_stats:
            type_stats[record.exercise_type] += 1
        else:
            type_stats[record.exercise_type] = 1

    return jsonify({
        'labels': list(type_stats.keys()),
        'data': list(type_stats.values())
    })

@app.route('/api/add_friend/<int:friend_id>')
@login_required
def add_friend(friend_id):
    friendship = Friendship(
        user_id=session['user_id'],
        friend_id=friend_id
    )

    db.session.add(friendship)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/remove_friend/<int:friend_id>')
@login_required
def remove_friend(friend_id):
    friendship = Friendship.query.filter_by(
        user_id=session['user_id'],
        friend_id=friend_id
    ).first()

    if friendship:
        db.session.delete(friendship)
        db.session.commit()

    return jsonify({'success': True})

@app.route('/api/search_users')
@login_required
def api_search_users():
    """搜尋用戶API"""
    search_term = request.args.get('q', '').lower()

    if not search_term:
        return jsonify([])

    users = User.query.filter(
        User.username.contains(search_term),
        User.id != session['user_id']
    ).limit(10).all()

    # 獲取當前用戶的好友列表
    friendships = Friendship.query.filter_by(user_id=session['user_id']).all()
    friend_ids = [f.friend_id for f in friendships]

    result = []
    for user in users:
        result.append({
            'id': user.id,
            'username': user.username,
            'created_at': user.created_at.strftime('%Y/%m/%d'),
            'is_friend': user.id in friend_ids
        })

    return jsonify(result)

@app.route('/api/analytics_data')
@login_required
def api_analytics_data():
    """獲取分析圖表數據"""
    period = request.args.get('period', 'month')
    user_id = session['user_id']

    # 根據期間決定天數
    if period == 'week':
        days = 7
    elif period == 'year':
        days = 365
    else:
        days = 30

    data = []
    for i in range(days - 1, -1, -1):
        date = datetime.now().date() - timedelta(days=i)

        day_records = ExerciseRecord.query.filter(
            ExerciseRecord.user_id == user_id,
            func.date(ExerciseRecord.created_at) == date
        ).all()

        calories = sum(record.calories for record in day_records)
        duration = sum(record.duration for record in day_records)

        data.append({
            'date': date.strftime('%m/%d'),
            'calories': calories,
            'duration': duration
        })

    return jsonify(data)


def calculate_goal_progress(goal):
    # 取出週期起始日（python date）
    start_date = get_period_start(goal.period).date()
    # 只比對日期，避免時間落差
    records = ExerciseRecord.query.filter(
        ExerciseRecord.user_id == goal.user_id,
        db.func.date(ExerciseRecord.created_at) >= start_date
    ).all()

    if goal.goal_type == 'calories':
        current_value = sum(record.calories for record in records)
    elif goal.goal_type == 'duration':
        current_value = sum(record.duration for record in records)
    elif goal.goal_type == 'frequency':
        current_value = len(records)
    else:
        current_value = 0

    progress = (current_value / goal.goal_value) * 100
    return min(progress, 100)

def check_goal_progress(user_id):
    """檢查並更新目標進度"""
    goals = Goal.query.filter_by(user_id=user_id, completed=False).all()

    for goal in goals:
        progress = calculate_goal_progress(goal)
        if progress >= 100:
            goal.completed = True
            db.session.commit()

# 模板上下文處理器
@app.context_processor
def inject_helpers():
    def get_goal_description(goal):
        type_names = {
            'calories': '熱量消耗',
            'duration': '運動時間',
            'frequency': '運動次數'
        }
        period_names = {
            'daily': '每日',
            'weekly': '每週',
            'monthly': '每月'
        }
        units = {
            'calories': '大卡',
            'duration': '分鐘',
            'frequency': '次'
        }
        return (
            f"{period_names.get(goal.period, '')}"
            f"{type_names.get(goal.goal_type, '')}："
            f"{goal.goal_value}{units.get(goal.goal_type, '')}"
        )

    def get_user_stats(user_id):
        records = ExerciseRecord.query.filter_by(user_id=user_id).all()
        total_calories = sum(r.calories for r in records)
        total_exercises = len(records)
        return {
            'total_calories': total_calories,
            'total_exercises': total_exercises
        }

    def calculate_goal_progress_template(goal):
        """給模板中用的進度計算"""
        return calculate_goal_progress(goal)

    # 一定要和上面同縮排 level，放在函數內部
    return {
        'get_goal_description': get_goal_description,
        'get_user_stats': get_user_stats,
        'calculate_goal_progress': calculate_goal_progress_template,
        'moment': datetime
    }


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)